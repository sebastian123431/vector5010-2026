"""
Modelos de datos para el Análisis Estructural de Código (AST) en JavaScript y TypeScript.
Proporciona estructuras tipadas para nodos AST, métricas de complejidad y hallazgos de seguridad.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class FindingSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class NodeKind(str, Enum):
    FUNCTION_DECLARATION = "function_declaration"
    ARROW_FUNCTION = "arrow_function"
    CLASS_DECLARATION = "class_declaration"
    METHOD_DEFINITION = "method_definition"
    IMPORT_DECLARATION = "import_declaration"
    EXPORT_DECLARATION = "export_declaration"
    CALL_EXPRESSION = "call_expression"
    AWAIT_EXPRESSION = "await_expression"
    ASSIGNMENT_EXPRESSION = "assignment_expression"
    MEMBER_EXPRESSION = "member_expression"
    TRY_STATEMENT = "try_statement"
    CATCH_CLAUSE = "catch_clause"
    VARIABLE_DECLARATION = "variable_declaration"
    INTERFACE_DECLARATION = "interface_declaration"
    TYPE_ALIAS_DECLARATION = "type_alias_declaration"
    ENUM_DECLARATION = "enum_declaration"


@dataclass
class ASTNodeInfo:
    """Información base de un nodo AST detectado."""
    kind: NodeKind
    name: str
    line: int
    column: int
    end_line: int
    end_column: int
    raw_text: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FunctionInfo(ASTNodeInfo):
    """Información detallada de funciones y métodos."""
    parameters: List[str] = field(default_factory=list)
    is_async: bool = False
    is_generator: bool = False
    is_static: bool = False
    return_type: Optional[str] = None
    has_await: bool = False


@dataclass
class ClassInfo(ASTNodeInfo):
    """Información de clases ES6+ / TypeScript."""
    heritage: Optional[str] = None
    implements: List[str] = field(default_factory=list)
    methods: List[FunctionInfo] = field(default_factory=list)
    properties: List[str] = field(default_factory=list)


@dataclass
class ImportInfo(ASTNodeInfo):
    """Información de importaciones de módulos."""
    source_module: str = ""
    imported_items: List[str] = field(default_factory=list)
    is_default: bool = False
    is_namespace: bool = False


@dataclass
class SecurityFinding:
    """Hallazgo de seguridad o anti-patrón de código."""
    rule_id: str
    title: str
    description: str
    severity: FindingSeverity
    confidence: float  # 0.0 a 1.0
    line: int
    column: int
    code_snippet: str = ""
    recommendation: str = ""
    cwe_id: Optional[str] = None
    source: Optional[str] = None
    sink: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "confidence": self.confidence,
            "line": self.line,
            "column": self.column,
            "code_snippet": self.code_snippet,
            "recommendation": self.recommendation,
            "cwe_id": self.cwe_id,
            "source": self.source,
            "sink": self.sink,
        }


@dataclass
class ComplexityMetrics:
    """Métricas de complejidad de código."""
    total_lines: int = 0
    code_lines: int = 0
    comment_lines: int = 0
    cyclomatic_complexity: int = 1
    max_nesting_depth: int = 0
    function_count: int = 0
    class_count: int = 0
    import_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_lines": self.total_lines,
            "code_lines": self.code_lines,
            "comment_lines": self.comment_lines,
            "cyclomatic_complexity": self.cyclomatic_complexity,
            "max_nesting_depth": self.max_nesting_depth,
            "function_count": self.function_count,
            "class_count": self.class_count,
            "import_count": self.import_count,
        }
