import os
import sys
import django

if not os.environ.get("DJANGO_SETTINGS_MODULE"):
    os.environ["DJANGO_SETTINGS_MODULE"] = "vector5010.settings"
    django.setup()

import unittest
from pathlib import Path
from vectorapp.security import (
    ASTSecurityValidator,
    ToolPermissions,
    ToolRunner,
    SandboxPolicy,
)


class TestSandboxAdversarial(unittest.TestCase):
    """
    Pruebas adversariales contra el sandbox y el analizador AST:
    - Intentos de introspección para escape de sandbox (__class__, __subclasses__).
    - Módulos críticos y evasiones encubiertas (ctypes, socket, multiprocessing).
    - Subprocesos desbocados que exceden la cuota de salida (matado incremental inmediato).
    """

    def setUp(self):
        self.validator = ASTSecurityValidator()

    def test_block_introspection_subclasses(self):
        """Bloquea intentos de escape mediante __subclasses__ y __globals__."""
        payloads = [
            "x = ''.__class__.__mro__[1].__subclasses__()",
            "f = getattr(object, '__subclasses__')",
            "g = ().__class__.__bases__[0].__subclasses__()",
        ]
        for p in payloads:
            res = self.validator.validate_code(p)
            self.assertFalse(res["security_valid"], f"Escape no bloqueado: {p}")
            self.assertGreaterEqual(len(res["violations"]), 1)

    def test_block_forbidden_modules_and_calls(self):
        """Bloquea importación de ctypes, socket, multiprocessing y llamadas a os.system/popen."""
        exploits = [
            "import ctypes; ctypes.cdll.LoadLibrary('libc.so.6')",
            "import socket; s = socket.socket()",
            "import multiprocessing; p = multiprocessing.Process()",
            "import os; getattr(os, 'system')('whoami')",
            "import os; os.popen('id').read()",
        ]
        for exp in exploits:
            res = self.validator.validate_code(exp)
            self.assertFalse(res["security_valid"], f"Exploit no detectado: {exp}")

    def test_block_forbidden_builtins(self):
        """Bloquea eval, exec, __import__, compile."""
        for fn in ("eval('1+1')", "exec('a = 1')", "__import__('os')", "compile('2+2', '', 'eval')"):
            res = self.validator.validate_code(fn)
            self.assertFalse(res["security_valid"], f"Builtin peligroso no bloqueado: {fn}")

    def test_incremental_output_killing_on_overflow(self):
        """
        Valida que un subproceso que emita un bucle infinito de salida en stdout
        sea terminado forzosamente de forma incremental e inmediata sin colgar el host.
        """
        # Crear un script que intente inundar stdout con 50 MB
        test_workspace = Path("./runtime/test_adversarial_workspace").resolve()
        test_workspace.mkdir(parents=True, exist_ok=True)
        flood_script = test_workspace / "flood_tool.py"
        flood_script.write_text(
            "import sys\n"
            "def flood_tool():\n"
            "    # Emite chunks masivos a stdout para probar el matado incremental del sandbox\n"
            "    for _ in range(500):\n"
            "        sys.__stdout__.write('A' * 50000)\n"
            "        sys.__stdout__.flush()\n"
            "    return 'done'\n",
            encoding="utf-8"
        )

        policy = SandboxPolicy(
            timeout=5,
            max_output_bytes=50_000,  # Límite pequeño: 50 KB
            workspace_dir=str(test_workspace)
        )
        runner = ToolRunner(policy=policy)

        res = runner.run_tool(
            tool_name="flood_tool",
            tool_file=str(flood_script),
            action="flood_tool",
            timeout=4
        )

        self.assertFalse(res.success)
        self.assertTrue(res.output_truncated)
        self.assertIn("superó el máximo", res.error)
        self.assertLess(res.execution_time_s, 3.0, "El proceso debió ser abortado inmediatamente por cuota de salida")

        # Limpiar archivo de prueba
        try:
            flood_script.unlink()
        except Exception:
            pass
