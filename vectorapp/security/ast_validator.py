"""
Validador de seguridad estático basado en AST (Abstract Syntax Tree) para VECTOR 2026.
Implementa el modelo Deny by Default + Allowlist por capacidades según ToolPermissions.
"""

import ast
import logging
from typing import Dict, List, Any, Optional, Set
from .permissions import ToolPermissions

logger = logging.getLogger(__name__)

# Símbolos y funciones builtin intrínsecamente peligrosos que SIEMPRE se bloquean
FORBIDDEN_BUILTINS: Set[str] = {
    'eval', 'exec', 'compile', '__import__', 'globals', 'locals',
    'breakpoint', 'input', 'open'  # 'open' se bloquea directamente a nivel AST si no hay permisos de filesystem
}

# Atributos de introspección / escape de sandbox (jailbreak prevention)
FORBIDDEN_ATTRIBUTES: Set[str] = {
    '__subclasses__', '__globals__', '__code__', '__class__',
    '__bases__', '__mro__', '__builtins__', '__dict__'
}

# Módulos críticos totalmente prohibidos para herramientas dinámicas
FORBIDDEN_MODULES: Set[str] = {
    'subprocess', 'ctypes', 'socket', 'multiprocessing', 'winreg',
    'shutil', 'signal', 'pty', 'posix', 'nt', 'termios', 'fcntl'
}

# Llamadas peligrosas específicas en módulos permitidos
FORBIDDEN_CALLS: Dict[str, str] = {
    'os.system': 'Intento de ejecución de comandos de sistema.',
    'os.popen': 'Intento de ejecución de tuberías del sistema.',
    'os.remove': 'Eliminación arbitraria de archivos.',
    'os.unlink': 'Eliminación arbitraria de enlaces/archivos.',
    'os.rmdir': 'Eliminación arbitraria de directorios.',
    'os.removedirs': 'Eliminación arbitraria de árboles de directorios.',
    'os.kill': 'Envío de señales de terminación a procesos.',
    'os.rename': 'Renombrado arbitrario de archivos del sistema.',
    'os.replace': 'Reemplazo arbitrario de archivos del sistema.',
    'os.chmod': 'Modificación arbitraria de permisos.',
    'os.chown': 'Modificación arbitraria de propietario de archivos.',
    'os.environ': 'Acceso o modificación directa a variables de entorno del servidor.',
    'os.putenv': 'Modificación de variables de entorno.',
    'sys.exit': 'Intento de terminación no controlada del intérprete.'
}

# Módulos seguros base (permitidos a cualquier herramienta)
BASE_ALLOWED_MODULES: Set[str] = {
    'math', 'statistics', 'random', 'datetime', 'calendar',
    'operator', 'json', 're', 'typing', 'collections',
    'itertools', 'functools', 'decimal', 'fractions', 'copy',
    'string', 'hashlib', 'time'
}

class ASTSecurityValidator:
    """
    Analizador estático de seguridad para código Python generado dinámicamente.
    Inspecciona cada nodo del AST antes de permitir que el código sea persistido o ejecutado.
    """

    def __init__(self, permissions: Optional[ToolPermissions] = None):
        self.permissions = permissions or ToolPermissions()
        self._build_allowed_modules()

    def _build_allowed_modules(self) -> None:
        """Construye el conjunto de módulos permitidos según las capacidades declaradas."""
        self.allowed_modules = set(BASE_ALLOWED_MODULES)

        if self.permissions.filesystem_read or self.permissions.filesystem_write:
            self.allowed_modules.update({'csv', 'pathlib'})

        if self.permissions.network:
            self.allowed_modules.update({'requests', 'urllib', 'urllib.parse', 'httpx'})

        if self.permissions.database:
            self.allowed_modules.update({'sqlite3'})

        if self.permissions.system_info:
            self.allowed_modules.update({'platform', 'psutil'})

    def validate_code(self, code_str: str) -> Dict[str, Any]:
        """
        Analiza el código y retorna un dict estructurado con la evaluación de seguridad:
        {
            "syntax_valid": bool,
            "security_valid": bool,
            "risk_level": "none" | "low" | "medium" | "high" | "critical",
            "violations": List[Dict]
        }
        """
        violations: List[Dict[str, Any]] = []

        # 1. Comprobación sintáctica con ast.parse
        try:
            tree = ast.parse(code_str)
        except SyntaxError as se:
            return {
                "syntax_valid": False,
                "security_valid": False,
                "risk_level": "critical",
                "violations": [{
                    "line": getattr(se, 'lineno', 1),
                    "column": getattr(se, 'offset', 1),
                    "rule": "SYNTAX_ERROR",
                    "symbol": "SyntaxError",
                    "message": f"Error de sintaxis: {str(se)}"
                }]
            }
        except Exception as e:
            return {
                "syntax_valid": False,
                "security_valid": False,
                "risk_level": "critical",
                "violations": [{
                    "line": 1,
                    "column": 1,
                    "rule": "PARSE_ERROR",
                    "symbol": "Exception",
                    "message": f"No se pudo parsear el código: {str(e)}"
                }]
            }

        # 2. Inspección profunda de nodos AST
        for node in ast.walk(tree):
            line = getattr(node, 'lineno', 1)
            col = getattr(node, 'col_offset', 0)

            # Inspección de importaciones: ast.Import
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_mod = alias.name.split('.')[0]
                    if root_mod in FORBIDDEN_MODULES:
                        violations.append({
                            "line": line,
                            "column": col,
                            "rule": "FORBIDDEN_IMPORT",
                            "symbol": alias.name,
                            "message": f"Importación prohibida del módulo crítico '{alias.name}'."
                        })
                    elif root_mod not in self.allowed_modules and root_mod != 'os':
                        violations.append({
                            "line": line,
                            "column": col,
                            "rule": "DISALLOWED_IMPORT",
                            "symbol": alias.name,
                            "message": f"Módulo '{alias.name}' no autorizado para los permisos asignados."
                        })

            # Inspección de importaciones: ast.ImportFrom
            elif isinstance(node, ast.ImportFrom):
                mod_name = node.module or ""
                root_mod = mod_name.split('.')[0]
                if root_mod in FORBIDDEN_MODULES:
                    violations.append({
                        "line": line,
                        "column": col,
                        "rule": "FORBIDDEN_IMPORT",
                        "symbol": mod_name,
                        "message": f"Importación prohibida de módulo crítico '{mod_name}'."
                    })
                elif root_mod not in self.allowed_modules and root_mod != 'os':
                    violations.append({
                        "line": line,
                        "column": col,
                        "rule": "DISALLOWED_IMPORT",
                        "symbol": mod_name,
                        "message": f"Módulo '{mod_name}' no autorizado para los permisos asignados."
                    })
                else:
                    # Validar símbolos específicos importados de 'os'
                    if root_mod == 'os':
                        for alias in node.names:
                            full_sym = f"os.{alias.name}"
                            if full_sym in FORBIDDEN_CALLS or alias.name in FORBIDDEN_BUILTINS:
                                violations.append({
                                    "line": line,
                                    "column": col,
                                    "rule": "FORBIDDEN_CALL",
                                    "symbol": full_sym,
                                    "message": f"Símbolo prohibido importado desde os: '{alias.name}'."
                                })

            # Inspección de llamadas: ast.Call
            elif isinstance(node, ast.Call):
                func_name = self._resolve_call_name(node.func)
                
                # Bloqueo de invocaciones dinámicas a getattr/setattr con atributos restringidos
                if func_name in ('getattr', 'hasattr', 'setattr', 'delattr'):
                    for arg in node.args:
                        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                            if arg.value in FORBIDDEN_ATTRIBUTES:
                                violations.append({
                                    "line": line,
                                    "column": col,
                                    "rule": "SANDBOX_ESCAPE_ATTEMPT",
                                    "symbol": f"{func_name}(..., '{arg.value}')",
                                    "message": f"Intento de acceso dinámico a atributo restringido '{arg.value}'."
                                })
                            dangerous_names = {k.split('.')[-1] for k in FORBIDDEN_CALLS.keys()} | FORBIDDEN_BUILTINS
                            if arg.value in dangerous_names:
                                violations.append({
                                    "line": line,
                                    "column": col,
                                    "rule": "FORBIDDEN_CALL_OBFUSCATION",
                                    "symbol": f"{func_name}(..., '{arg.value}')",
                                    "message": f"Intento de invocación ofuscada a función prohibida '{arg.value}' mediante {func_name}."
                                })

                # Bloqueo de builtins peligrosos
                if func_name in FORBIDDEN_BUILTINS:
                    # Permitir 'open' SOLO si tiene permiso filesystem explícito
                    if func_name == 'open' and (self.permissions.filesystem_read or self.permissions.filesystem_write):
                        pass
                    else:
                        violations.append({
                            "line": line,
                            "column": col,
                            "rule": "FORBIDDEN_BUILTIN",
                            "symbol": func_name,
                            "message": f"Uso prohibido de la función builtin '{func_name}'."
                        })

                # Bloqueo de llamadas peligrosas del sistema (os.system, etc.)
                if func_name in FORBIDDEN_CALLS:
                    violations.append({
                        "line": line,
                        "column": col,
                        "rule": "FORBIDDEN_CALL",
                        "symbol": func_name,
                        "message": FORBIDDEN_CALLS[func_name]
                    })

            # Inspección de atributos: ast.Attribute (introspección / acceso de escape)
            elif isinstance(node, ast.Attribute):
                if node.attr in FORBIDDEN_ATTRIBUTES:
                    violations.append({
                        "line": line,
                        "column": col,
                        "rule": "SANDBOX_ESCAPE_ATTEMPT",
                        "symbol": node.attr,
                        "message": f"Intento de acceso a atributo restringido de introspección '{node.attr}'."
                    })
                # Chequeo de os.system / os.environ como atributos
                attr_full = self._resolve_call_name(node)
                if attr_full in FORBIDDEN_CALLS:
                    violations.append({
                        "line": line,
                        "column": col,
                        "rule": "FORBIDDEN_ATTRIBUTE",
                        "symbol": attr_full,
                        "message": FORBIDDEN_CALLS[attr_full]
                    })

            # Inspección de constantes: ast.Constant (literales de escape)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                if node.value in FORBIDDEN_ATTRIBUTES:
                    violations.append({
                        "line": line,
                        "column": col,
                        "rule": "SANDBOX_ESCAPE_ATTEMPT",
                        "symbol": node.value,
                        "message": f"Uso de literal de introspección restringido '{node.value}'."
                    })

            # Inspección de nombres: ast.Name (ej. uso directo de eval, exec o globals)
            elif isinstance(node, ast.Name):
                if node.id in FORBIDDEN_BUILTINS:
                    # Si no es un contexto de llamada directa, igual se vigila
                    if node.id != 'open' or not (self.permissions.filesystem_read or self.permissions.filesystem_write):
                        # Solo marcar si no está siendo definido como argumento de función
                        if isinstance(node.ctx, ast.Load):
                            violations.append({
                                "line": line,
                                "column": col,
                                "rule": "FORBIDDEN_NAME_REFERENCE",
                                "symbol": node.id,
                                "message": f"Referencia prohibida al símbolo '{node.id}'."
                            })

        # 3. Determinar nivel de riesgo
        risk_level = "none"
        if violations:
            critical_rules = {"FORBIDDEN_IMPORT", "FORBIDDEN_CALL", "FORBIDDEN_BUILTIN", "SANDBOX_ESCAPE_ATTEMPT", "SYNTAX_ERROR"}
            has_critical = any(v.get("rule") in critical_rules for v in violations)
            risk_level = "critical" if has_critical else "high"

        return {
            "syntax_valid": True,
            "security_valid": len(violations) == 0,
            "risk_level": risk_level,
            "violations": violations
        }

    def _resolve_call_name(self, node: ast.AST) -> str:
        """Resuelve el nombre canónico de una llamada (ej. 'os.system' o 'eval')."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            val = self._resolve_call_name(node.value)
            if val:
                return f"{val}.{node.attr}"
            return node.attr
        return ""
