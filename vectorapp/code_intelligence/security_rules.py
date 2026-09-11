"""
Reglas de seguridad y análisis de flujo de datos (Taint Analysis) para JavaScript y TypeScript.
Detecta vulnerabilidades estáticas y rastrea fuentes no confiables (Sources) hacia sumideros peligrosos (Sinks).
"""

from typing import List, Dict, Set, Any, Optional
import re
from .ast_models import SecurityFinding, FindingSeverity


# Fuentes no confiables conocidas en JavaScript/TypeScript (Sources)
UNTRUSTED_SOURCES: Set[str] = {
    "location.search",
    "location.hash",
    "location.href",
    "window.name",
    "document.URL",
    "document.documentURI",
    "document.referrer",
    "document.cookie",
    "localStorage.getItem",
    "sessionStorage.getItem",
    "req.query",
    "req.body",
    "req.params",
    "req.headers",
    "params",
}

# Sumideros peligrosos (Sinks) y sus categorías
DOM_XSS_SINKS: Set[str] = {
    "innerHTML",
    "outerHTML",
    "document.write",
    "document.writeln",
    "insertAdjacentHTML",
}

CODE_EXEC_SINKS: Set[str] = {
    "eval",
    "Function",
}

REDIRECT_SINKS: Set[str] = {
    "location.href",
    "location.replace",
    "location.assign",
    "window.open",
}


class TaintAnalysisEngine:
    """
    Motor de análisis de flujo de información (Taint Tracking).
    Rastrea identificadores que reciben datos de fuentes no confiables (Sources)
    y verifica si alcanzan puntos de ejecución sensibles (Sinks) sin sanitización.
    """

    def __init__(self):
        self.tainted_variables: Dict[str, str] = {}  # var_name -> source_name

    def register_source(self, var_name: str, source_description: str):
        self.tainted_variables[var_name] = source_description

    def propagate(self, target_var: str, source_expr: str):
        for tainted, origin in list(self.tainted_variables.items()):
            if tainted in source_expr:
                self.tainted_variables[target_var] = origin

    def is_tainted(self, expr: str) -> Optional[str]:
        for tainted, origin in self.tainted_variables.items():
            pattern = rf"\b{re.escape(tainted)}\b"
            if re.search(pattern, expr):
                return origin
        return None


class SecurityRuleChecker:
    """
    Evaluador de reglas de seguridad sobre AST y flujo de código JavaScript/TypeScript.
    """

    @staticmethod
    def check_eval_and_code_injection(node_text: str, line: int, col: int) -> Optional[SecurityFinding]:
        """Detecta llamadas a eval() o new Function()."""
        if re.search(r"\b(eval)\s*\(", node_text):
            return SecurityFinding(
                rule_id="JS-SEC-001",
                title="Ejecución de Código Arbitrario (eval)",
                description="Uso directo de 'eval()' detectado. Permite la ejecución de código dinámico sin restricciones.",
                severity=FindingSeverity.CRITICAL,
                confidence=0.98,
                line=line,
                column=col,
                code_snippet=node_text[:120],
                recommendation="Evitar 'eval()'. Utilizar deserialización JSON segura (JSON.parse) o lógica explícita.",
                cwe_id="CWE-95",
                sink="eval",
            )
        if re.search(r"\bnew\s+Function\s*\(", node_text):
            return SecurityFinding(
                rule_id="JS-SEC-002",
                title="Constructor Dinámico de Funciones",
                description="Uso de 'new Function()' detectado. Crea un contexto de ejecución dinámico similar a eval.",
                severity=FindingSeverity.HIGH,
                confidence=0.95,
                line=line,
                column=col,
                code_snippet=node_text[:120],
                recommendation="Declarar funciones estándar en lugar de construir funciones a partir de cadenas.",
                cwe_id="CWE-95",
                sink="Function",
            )
        return None

    @staticmethod
    def check_dom_xss(member_prop: str, value_expr: str, line: int, col: int, taint_origin: Optional[str] = None) -> Optional[SecurityFinding]:
        """Detecta asignaciones directas a propiedades DOM peligrosas (innerHTML, outerHTML)."""
        if member_prop in DOM_XSS_SINKS:
            severity = FindingSeverity.CRITICAL if taint_origin else FindingSeverity.HIGH
            desc = (
                f"Asignación a '{member_prop}' con datos provenientes de '{taint_origin}'."
                if taint_origin
                else f"Asignación potencialmente insegura a '{member_prop}' que puede causar Cross-Site Scripting (XSS)."
            )
            return SecurityFinding(
                rule_id="JS-SEC-003",
                title="Vulnerabilidad DOM XSS",
                description=desc,
                severity=severity,
                confidence=0.95 if taint_origin else 0.85,
                line=line,
                column=col,
                code_snippet=f"{member_prop} = {value_expr}"[:120],
                recommendation="Utilizar 'textContent', 'innerText' o una biblioteca de sanitización como DOMPurify.",
                cwe_id="CWE-79",
                source=taint_origin,
                sink=member_prop,
            )
        return None

    @staticmethod
    def check_prototype_pollution(expr: str, line: int, col: int) -> Optional[SecurityFinding]:
        """Detecta manipulaciones riesgosas de prototipos (__proto__, prototype)."""
        if "__proto__" in expr or "constructor.prototype" in expr:
            return SecurityFinding(
                rule_id="JS-SEC-004",
                title="Riesgo de Prototype Pollution",
                description="Acceso o mutación directa de '__proto__' o 'constructor.prototype'. Puede comprometer la integridad de todos los objetos en runtime.",
                severity=FindingSeverity.HIGH,
                confidence=0.90,
                line=line,
                column=col,
                code_snippet=expr[:120],
                recommendation="Utilizar Object.create(null) para mapas libres de prototipo o Map/Set estructurados.",
                cwe_id="CWE-1321",
            )
        return None

    @staticmethod
    def check_weak_equality(operator: str, line: int, col: int, snippet: str) -> Optional[SecurityFinding]:
        """Detecta operadores de igualdad débil ('==' o '!=')."""
        if operator in ("==", "!="):
            return SecurityFinding(
                rule_id="JS-QUAL-001",
                title="Uso de Igualdad Débil",
                description=f"Operador de igualdad débil '{operator}' detectado. Conlleva coerción de tipos impredecible.",
                severity=FindingSeverity.LOW,
                confidence=1.0,
                line=line,
                column=col,
                code_snippet=snippet[:80],
                recommendation=f"Reemplazar por '{'===' if operator == '==' else '!=='}' para garantizar igualdad estricta.",
                cwe_id="CWE-480",
            )
        return None

    @staticmethod
    def check_var_hoisting(name: str, line: int, col: int, snippet: str) -> Optional[SecurityFinding]:
        """Detecta declaraciones 'var' sujetas a elevación (hoisting)."""
        return SecurityFinding(
            rule_id="JS-QUAL-002",
            title="Declaración Obsoleta 'var'",
            description=f"Uso de 'var' para declarar '{name}'. No posee ámbito de bloque y genera efectos colaterales de hoisting.",
            severity=FindingSeverity.INFO,
            confidence=1.0,
            line=line,
            column=col,
            code_snippet=snippet[:80],
            recommendation="Migrar a 'const' (preferido) o 'let'.",
        )
