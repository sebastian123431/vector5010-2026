"""
Verificador cognitivo (Cognitive Verifier) para Vector (Fase P2).
Valida corrección técnica de código generado, verificación de hechos y ausencia de comandos destructivos.
"""

from typing import Dict, Any, List, Optional
import ast
import re

from vectorapp.javascript_engine import javascript_engine
from vectorapp.security.ast_validator import ASTSecurityValidator


class CognitiveVerifier:
    """
    Verificador de hechos, seguridad y sintaxis técnica.
    """

    @staticmethod
    def verify_code(code: str, language: str = "javascript") -> Dict[str, Any]:
        """
        Verifica la validez sintáctica y estructural de un fragmento de código.
        """
        lang = language.lower()
        if lang in ("javascript", "js", "typescript", "ts"):
            res = javascript_engine.analizar_codigo_js(code)
            return {
                "valid": res.get("es_valido", False),
                "language": lang,
                "syntax_errors": [res.get("error_sintaxis")] if res.get("error_sintaxis") else [],
                "issues": res.get("issues", []),
            }
        elif lang in ("python", "py"):
            try:
                validator = ASTSecurityValidator()
                val_res = validator.validate_code(code)
                syntax_valid = val_res.get("syntax_valid", False)
                security_valid = val_res.get("security_valid", False)
                violations = val_res.get("violations", [])
                syntax_errors = [v for v in violations if v.get("rule") in ("SYNTAX_ERROR", "PARSE_ERROR")]
                security_violations = [v for v in violations if v.get("rule") not in ("SYNTAX_ERROR", "PARSE_ERROR")]
                return {
                    "valid": syntax_valid and security_valid,
                    "language": "python",
                    "syntax_valid": syntax_valid,
                    "security_valid": security_valid,
                    "syntax_errors": syntax_errors,
                    "violations": security_violations,
                }
            except SyntaxError as se:
                return {
                    "valid": False,
                    "language": "python",
                    "syntax_valid": False,
                    "security_valid": False,
                    "syntax_errors": [{"line": getattr(se, 'lineno', 1), "message": str(se)}],
                    "violations": [],
                }
            except Exception as e:
                return {
                    "valid": False,
                    "language": "python",
                    "syntax_valid": False,
                    "security_valid": False,
                    "syntax_errors": [{"line": 1, "message": str(e)}],
                    "violations": [],
                }
        return {"valid": True, "language": language, "syntax_errors": []}

    @staticmethod
    def verify_safety(text: str) -> Dict[str, Any]:
        """
        Verifica que el texto o comando no contenga instrucciones destructivas no autorizadas.
        """
        t_lower = text.lower()
        destructive_patterns = [
            (r'\b(?:rm\s+-rf|del\s+/s|format\s+c:)\b', "Comando de borrado de disco no autorizado."),
            (r'\b(?:drop\s+database|drop\s+table\s+users)\b', "Sentencia destructiva SQL sobre datos del sistema."),
            (r'\b(?:kill\s+-9\s+1|shutdown\s+/s)\b', "Instrucción de parada forzada del sistema operativo."),
        ]

        violations = []
        for pattern, desc in destructive_patterns:
            if re.search(pattern, t_lower):
                violations.append(desc)

        return {
            "safe": len(violations) == 0,
            "violations": violations
        }
