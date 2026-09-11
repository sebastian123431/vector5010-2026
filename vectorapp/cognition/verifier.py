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
            "passed": len(violations) == 0,
            "violations": violations
        }

    @classmethod
    def verify_execution(
        cls,
        plan: Any,
        execution_result: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Verificación post-ejecución del plan cognitivo y sus herramientas:
        - Confirma completitud de pasos solicitados y dependencias.
        - Detecta errores en herramientas o fallos de ejecución.
        - Audita sintaxis y seguridad técnica sobre salidas generadas.
        """
        findings = []
        steps = getattr(plan, "steps", []) if hasattr(plan, "steps") else (plan.get("steps", []) if isinstance(plan, dict) else [])
        total_steps = len(steps)
        completed_count = execution_result.get("completed_count", 0)

        # 1. Comprobar estado de los pasos y herramientas ejecutadas
        failed_steps = []
        skipped_steps = []
        for s in steps:
            s_dict = s.to_dict() if hasattr(s, "to_dict") else (s if isinstance(s, dict) else {})
            status = s_dict.get("status")
            step_num = s_dict.get("step_number")
            tool = s_dict.get("required_tool")
            err = s_dict.get("error")

            if status in ("failed", "FAILED"):
                failed_steps.append({"step": step_num, "tool": tool, "error": err})
                findings.append(f"Paso {step_num} ({tool or 'cognitivo'}) falló: {err}")
            elif status in ("skipped", "SKIPPED"):
                skipped_steps.append({"step": step_num, "tool": tool, "reason": err})
                findings.append(f"Paso {step_num} omitido por dependencias no satisfechas.")

            # 2. Validación de código si el paso generó un script Python
            res = s_dict.get("result")
            if isinstance(res, str) and ("def " in res or "class " in res or "import " in res):
                code_check = cls.verify_code(res, language="python")
                if not code_check.get("valid", True):
                    findings.append(f"Paso {step_num} generó código Python con problemas sintácticos o de seguridad.")

        exec_success = bool(execution_result.get("success", False))
        passed = exec_success and (len(failed_steps) == 0) and (completed_count == total_steps if total_steps else True)

        return {
            "passed": passed,
            "success": passed,
            "total_steps": total_steps,
            "completed_steps": completed_count,
            "failed_steps": failed_steps,
            "skipped_steps": skipped_steps,
            "findings": findings
        }
