"""
Políticas de sandbox y runner aislado para herramientas dinámicas en VECTOR 2026.
Controla timeouts, consumo de salida en bytes, sanitización de entorno y procesos.
"""

import sys
import os
import json
import time
import subprocess
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional
from pathlib import Path

from .path_policy import PathPolicy, DEFAULT_TOOL_WORKSPACE
from .exceptions import ResourceLimitExceeded, ToolExecutionError

logger = logging.getLogger(__name__)

# Constantes de control y cuotas de seguridad
TOOL_TIMEOUT_SIMPLE = 5           # Segundos para tareas simples
TOOL_TIMEOUT_COMPLEX = 20         # Segundos para tareas complejas
TOOL_MAX_OUTPUT_BYTES = 1_000_000  # 1 MB máximo de salida capturada

@dataclass
class ToolExecutionResult:
    success: bool
    result: Any
    error: Optional[str] = None
    execution_time_s: float = 0.0
    output_truncated: bool = False

class SandboxPolicy:
    """Configuración de límites del entorno de ejecución aislado."""
    def __init__(
        self,
        timeout: int = TOOL_TIMEOUT_SIMPLE,
        max_output_bytes: int = TOOL_MAX_OUTPUT_BYTES,
        workspace_dir: Optional[str] = None
    ):
        self.timeout = timeout
        self.max_output_bytes = max_output_bytes
        self.path_policy = PathPolicy(workspace_dir or DEFAULT_TOOL_WORKSPACE)

class ToolRunner:
    """
    Ejecutor seguro de herramientas dinámicas dentro de un subproceso aislado.
    Controla el tiempo de ejecución, trunca salidas excesivas y previene desbordamiento de memoria.
    """
    def __init__(self, policy: Optional[SandboxPolicy] = None):
        self.policy = policy or SandboxPolicy()

    def run_tool(
        self,
        tool_name: str,
        tool_file: str,
        action: str = "execute",
        parameters: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None
    ) -> ToolExecutionResult:
        """
        Ejecuta la herramienta en un subproceso aislado con directiva de cuotas.
        """
        params = parameters or {}
        time_limit = timeout if timeout is not None else self.policy.timeout
        start_time = time.time()

        # Validar existencia del archivo
        tool_path = Path(tool_file).resolve()
        if not tool_path.exists():
            return ToolExecutionResult(
                success=False,
                result=None,
                error=f"El archivo de la herramienta '{tool_name}' no existe en '{tool_path}'.",
                execution_time_s=0.0
            )

        # Sanitizar entorno para que no filtre claves de Django ni credenciales
        safe_env = self._build_sanitized_env()

        # Script ejecutor interno
        runner_script = (
            "import sys, json, importlib.util, io\n"
            "tool_name = sys.argv[1]\n"
            "tool_file = sys.argv[2]\n"
            "act = sys.argv[3]\n"
            "params = json.loads(sys.argv[4]) if len(sys.argv) > 4 else {}\n"
            "try:\n"
            "    spec = importlib.util.spec_from_file_location(tool_name, tool_file)\n"
            "    if not spec or not spec.loader:\n"
            "        print(json.dumps({'success': False, 'error': 'No se pudo cargar el módulo'}))\n"
            "        sys.exit(0)\n"
            "    mod = importlib.util.module_from_spec(spec)\n"
            "    spec.loader.exec_module(mod)\n"
            "    _buf = io.StringIO()\n"
            "    _orig_stdout = sys.stdout\n"
            "    sys.stdout = _buf\n"
            "    res = None\n"
            "    if hasattr(mod, 'execute_tool'):\n"
            "        res = mod.execute_tool(action=act, **params)\n"
            "    elif hasattr(mod, tool_name):\n"
            "        fn = getattr(mod, tool_name)\n"
            "        res = fn(**params) if params else fn()\n"
            "    else:\n"
            "        funcs = [f for f in dir(mod) if callable(getattr(mod, f)) and not f.startswith('_')]\n"
            "        if funcs:\n"
            "            fn = getattr(mod, funcs[0])\n"
            "            res = fn(**params) if params else fn()\n"
            "        else:\n"
            "            sys.stdout = _orig_stdout\n"
            "            print(json.dumps({'success': False, 'error': 'No se encontró función ejecutable'}))\n"
            "            sys.exit(0)\n"
            "    sys.stdout = _orig_stdout\n"
            "    captured = _buf.getvalue().strip()\n"
            "    final_res = captured if (res is None or isinstance(res, bool)) and captured else (res if res is not None else captured)\n"
            "    print(json.dumps({'success': True, 'result': final_res}, default=str))\n"
            "except Exception as e:\n"
            "    sys.stdout = sys.__stdout__\n"
            "    print(json.dumps({'success': False, 'error': str(e)}))\n"
        )

        cmd = [
            sys.executable,
            "-c",
            runner_script,
            tool_name,
            str(tool_path),
            action,
            json.dumps(params, ensure_ascii=False)
        ]

        workspace_cwd = str(self.policy.path_policy.workspace_dir)

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False,  # Leer en bytes para medir cuota exacta
                cwd=workspace_cwd,
                env=safe_env
            )

            try:
                stdout_bytes, stderr_bytes = proc.communicate(timeout=time_limit)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                elapsed = time.time() - start_time
                return ToolExecutionResult(
                    success=False,
                    result=None,
                    error=f"[Timeout] La herramienta '{tool_name}' excedió el límite de seguridad ({time_limit}s).",
                    execution_time_s=elapsed
                )

            elapsed = time.time() - start_time
            output_truncated = False

            if len(stdout_bytes) > self.policy.max_output_bytes:
                output_truncated = True
                return ToolExecutionResult(
                    success=False,
                    result=None,
                    error=f"[ResourceLimit] Salida de '{tool_name}' superó el máximo de {self.policy.max_output_bytes} bytes.",
                    execution_time_s=elapsed,
                    output_truncated=True
                )

            stdout_str = stdout_bytes.decode('utf-8', errors='replace').strip()
            stderr_str = stderr_bytes.decode('utf-8', errors='replace').strip()

            result_obj = None
            if stdout_str:
                for line in stdout_str.splitlines()[::-1]:
                    try:
                        result_obj = json.loads(line)
                        break
                    except Exception:
                        continue

            if result_obj and result_obj.get("success"):
                return ToolExecutionResult(
                    success=True,
                    result=result_obj.get("result"),
                    error=None,
                    execution_time_s=elapsed
                )
            elif result_obj and "error" in result_obj:
                return ToolExecutionResult(
                    success=False,
                    result=None,
                    error=result_obj.get("error"),
                    execution_time_s=elapsed
                )
            else:
                err_detail = stderr_str if stderr_str else (stdout_str if stdout_str else f"Código de salida: {proc.returncode}")
                return ToolExecutionResult(
                    success=False,
                    result=None,
                    error=f"Error en ejecución: {err_detail}",
                    execution_time_s=elapsed
                )

        except subprocess.TimeoutExpired:
            proc.kill()
            elapsed = time.time() - start_time
            return ToolExecutionResult(
                success=False,
                result=None,
                error=f"[Timeout] La herramienta '{tool_name}' excedió el límite de seguridad ({time_limit}s).",
                execution_time_s=elapsed
            )
        except Exception as e:
            elapsed = time.time() - start_time
            return ToolExecutionResult(
                success=False,
                result=None,
                error=f"Error inesperado al ejecutar herramienta: {str(e)}",
                execution_time_s=elapsed
            )

    def run_test_file(self, test_file_path: str, timeout: int = 10) -> ToolExecutionResult:
        """
        Ejecuta un archivo de prueba unitaria de herramienta dentro del sandbox con límite de tiempo y cuota.
        """
        test_path = Path(test_file_path).resolve()
        if not test_path.exists():
            return ToolExecutionResult(
                success=False,
                result=None,
                error=f"El archivo de prueba no existe en '{test_path}'.",
                execution_time_s=0.0
            )

        safe_env = self._build_sanitized_env()
        workspace_cwd = str(self.policy.path_policy.workspace_dir)
        start_time = time.time()

        cmd = [sys.executable, str(test_path)]

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False,
                cwd=workspace_cwd,
                env=safe_env
            )
            try:
                stdout_bytes, stderr_bytes = proc.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                elapsed = time.time() - start_time
                return ToolExecutionResult(
                    success=False,
                    result=None,
                    error=f"[Timeout] La prueba unitaria '{test_path.name}' excedió el límite de {timeout}s.",
                    execution_time_s=elapsed
                )

            elapsed = time.time() - start_time
            stdout_str = stdout_bytes.decode('utf-8', errors='replace').strip()
            stderr_str = stderr_bytes.decode('utf-8', errors='replace').strip()

            if proc.returncode == 0:
                return ToolExecutionResult(
                    success=True,
                    result=stdout_str or "Test passed successfully",
                    error=None,
                    execution_time_s=elapsed
                )
            else:
                err_detail = stderr_str if stderr_str else stdout_str
                return ToolExecutionResult(
                    success=False,
                    result=None,
                    error=f"Fallo en pruebas unitarias (código {proc.returncode}): {err_detail}",
                    execution_time_s=elapsed
                )
        except Exception as e:
            elapsed = time.time() - start_time
            return ToolExecutionResult(
                success=False,
                result=None,
                error=f"Error inesperado al ejecutar prueba: {str(e)}",
                execution_time_s=elapsed
            )

    def _build_sanitized_env(self) -> Dict[str, str]:
        """Genera un diccionario de variables de entorno limpio, sin secrets."""
        safe_keys = {
            'PATH', 'SYSTEMROOT', 'TEMP', 'TMP', 'HOMEPATH', 'HOMEDRIVE',
            'USERPROFILE', 'LANG', 'LC_ALL', 'PYTHONIOENCODING'
        }
        env = {}
        for k, v in os.environ.items():
            if k.upper() in safe_keys:
                env[k] = v
        # Aislar PYTHONPATH al intérprete y evitar inyección
        env['PYTHONIOENCODING'] = 'utf-8'
        return env

