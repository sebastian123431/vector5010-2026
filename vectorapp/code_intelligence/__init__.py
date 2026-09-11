"""
Subsistema de Inteligencia Estructural de Código (AST) para Vector.
Exporta analizadores de JavaScript y TypeScript, modelos AST y reglas de seguridad.
"""

from .ast_models import (
    ASTNodeInfo, FunctionInfo, ClassInfo, ImportInfo,
    SecurityFinding, FindingSeverity, ComplexityMetrics, NodeKind
)
from .security_rules import (
    SecurityRuleChecker, TaintAnalysisEngine,
    UNTRUSTED_SOURCES, DOM_XSS_SINKS, CODE_EXEC_SINKS, REDIRECT_SINKS
)
from .javascript_parser import TreeSitterJSParser
from .typescript_parser import TreeSitterTSParser

__all__ = [
    "ASTNodeInfo",
    "FunctionInfo",
    "ClassInfo",
    "ImportInfo",
    "SecurityFinding",
    "FindingSeverity",
    "ComplexityMetrics",
    "NodeKind",
    "SecurityRuleChecker",
    "TaintAnalysisEngine",
    "UNTRUSTED_SOURCES",
    "DOM_XSS_SINKS",
    "CODE_EXEC_SINKS",
    "REDIRECT_SINKS",
    "TreeSitterJSParser",
    "TreeSitterTSParser",
]
