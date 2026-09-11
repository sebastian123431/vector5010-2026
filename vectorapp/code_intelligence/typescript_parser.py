"""
Parser AST y Analizador Estructural para TypeScript mediante Tree-sitter.
Proporciona extracción de interfaces, tipos, enums, funciones tipadas y análisis de seguridad estático.
"""

from typing import Dict, Any, List, Optional
import tree_sitter
import tree_sitter_typescript as tsts

from .ast_models import (
    FunctionInfo, ClassInfo, ImportInfo, SecurityFinding, ComplexityMetrics,
    NodeKind, ASTNodeInfo
)
from .security_rules import (
    SecurityRuleChecker, TaintAnalysisEngine, UNTRUSTED_SOURCES
)


class TreeSitterTSParser:
    """
    Analizador estructural de TypeScript basado en Tree-sitter.
    Capaz de entender tipos estáticos, interfaces, enums y decoradores.
    """

    def __init__(self):
        self.language = tree_sitter.Language(tsts.language_typescript())
        self.parser = tree_sitter.Parser(self.language)

    def parse(self, code: str, filename: str = "script.ts") -> Dict[str, Any]:
        """
        Ejecuta el análisis estructural completo de código TypeScript.
        """
        code_bytes = bytes(code, "utf-8")
        tree = self.parser.parse(code_bytes)
        root = tree.root_node

        lines = code.splitlines()
        total_lines = len(lines)
        code_lines = len([l for l in lines if l.strip() and not l.strip().startswith("//")])
        comment_lines = total_lines - code_lines

        functions: List[FunctionInfo] = []
        classes: List[ClassInfo] = []
        interfaces: List[Dict[str, Any]] = []
        type_aliases: List[Dict[str, Any]] = []
        enums: List[Dict[str, Any]] = []
        imports: List[ImportInfo] = []
        exports: List[str] = []
        syntax_errors: List[Dict[str, Any]] = []
        security_findings: List[SecurityFinding] = []

        taint_engine = TaintAnalysisEngine()
        cyclomatic_complexity = 1
        max_nesting_depth = 0

        def walk_node(node, current_depth: int = 0):
            nonlocal cyclomatic_complexity, max_nesting_depth
            if current_depth > max_nesting_depth:
                max_nesting_depth = current_depth

            node_type = node.type

            # Errores de sintaxis
            if node_type == "ERROR" or node.is_missing:
                start_point = node.start_point
                syntax_errors.append({
                    "line": start_point[0] + 1,
                    "column": start_point[1] + 1,
                    "text": code_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")[:60],
                    "message": f"Error de sintaxis TypeScript en línea {start_point[0] + 1}, columna {start_point[1] + 1}"
                })

            # Complejidad ciclomática
            if node_type in (
                "if_statement", "for_statement", "for_in_statement",
                "while_statement", "do_statement", "switch_case",
                "catch_clause", "ternary_expression"
            ):
                cyclomatic_complexity += 1
            elif node_type == "binary_expression":
                op_node = node.child_by_field_name("operator")
                if op_node:
                    op = code_bytes[op_node.start_byte:op_node.end_byte].decode("utf-8", errors="replace")
                    if op in ("&&", "||", "??"):
                        cyclomatic_complexity += 1

            # Interfaces
            if node_type == "interface_declaration":
                name_node = node.child_by_field_name("name")
                if_name = code_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace") if name_node else "AnonymousInterface"
                interfaces.append({
                    "name": if_name,
                    "line": node.start_point[0] + 1,
                    "column": node.start_point[1] + 1,
                })

            # Type aliases
            elif node_type == "type_alias_declaration":
                name_node = node.child_by_field_name("name")
                t_name = code_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace") if name_node else "AnonymousType"
                type_aliases.append({
                    "name": t_name,
                    "line": node.start_point[0] + 1,
                })

            # Enums
            elif node_type == "enum_declaration":
                name_node = node.child_by_field_name("name")
                e_name = code_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace") if name_node else "AnonymousEnum"
                enums.append({
                    "name": e_name,
                    "line": node.start_point[0] + 1,
                })

            # Funciones
            elif node_type == "function_declaration":
                name_node = node.child_by_field_name("name")
                fn_name = code_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace") if name_node else "anonymous"
                raw_text = code_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
                functions.append(FunctionInfo(
                    kind=NodeKind.FUNCTION_DECLARATION,
                    name=fn_name,
                    line=node.start_point[0] + 1,
                    column=node.start_point[1] + 1,
                    end_line=node.end_point[0] + 1,
                    end_column=node.end_point[1] + 1,
                    raw_text=raw_text[:200],
                    is_async="async" in raw_text[:40],
                ))

            # Clases
            elif node_type == "class_declaration":
                name_node = node.child_by_field_name("name")
                c_name = code_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace") if name_node else "AnonymousClass"
                classes.append(ClassInfo(
                    kind=NodeKind.CLASS_DECLARATION,
                    name=c_name,
                    line=node.start_point[0] + 1,
                    column=node.start_point[1] + 1,
                    end_line=node.end_point[0] + 1,
                    end_column=node.end_point[1] + 1,
                ))

            # Imports
            elif node_type == "import_statement":
                source_node = node.child_by_field_name("source")
                source = code_bytes[source_node.start_byte:source_node.end_byte].decode("utf-8", errors="replace").strip("'\"") if source_node else ""
                imports.append(ImportInfo(
                    kind=NodeKind.IMPORT_DECLARATION,
                    name=source,
                    line=node.start_point[0] + 1,
                    column=node.start_point[1] + 1,
                    end_line=node.end_point[0] + 1,
                    end_column=node.end_point[1] + 1,
                    source_module=source,
                ))

            # Exports
            elif node_type in ("export_statement",):
                exp_text = code_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
                exports.append(exp_text[:50].strip())

            # Seguridad: eval / code injection
            elif node_type == "call_expression":
                call_text = code_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
                finding = SecurityRuleChecker.check_eval_and_code_injection(
                    call_text, node.start_point[0] + 1, node.start_point[1] + 1
                )
                if finding:
                    security_findings.append(finding)

            # Seguridad: DOM XSS
            elif node_type == "assignment_expression":
                left_node = node.child_by_field_name("left")
                right_node = node.child_by_field_name("right")
                if left_node and right_node:
                    left_text = code_bytes[left_node.start_byte:left_node.end_byte].decode("utf-8", errors="replace")
                    right_text = code_bytes[right_node.start_byte:right_node.end_byte].decode("utf-8", errors="replace")
                    for sink in ("innerHTML", "outerHTML", "document.write"):
                        if sink in left_text:
                            finding = SecurityRuleChecker.check_dom_xss(
                                sink, right_text, left_node.start_point[0] + 1, left_node.start_point[1] + 1
                            )
                            if finding:
                                security_findings.append(finding)

            # Recorrido recursivo
            for child in node.children:
                walk_node(child, current_depth + 1)

        walk_node(root, 0)

        metrics = ComplexityMetrics(
            total_lines=total_lines,
            code_lines=code_lines,
            comment_lines=comment_lines,
            cyclomatic_complexity=cyclomatic_complexity,
            max_nesting_depth=max_nesting_depth,
            function_count=len(functions),
            class_count=len(classes),
            import_count=len(imports),
        )

        return {
            "success": True,
            "filename": filename,
            "language": "typescript",
            "has_syntax_errors": root.has_error or bool(syntax_errors),
            "syntax_errors": syntax_errors,
            "metrics": metrics.to_dict(),
            "functions": [{"nombre": f.name, "linea": f.line} for f in functions],
            "classes": [{"nombre": c.name, "linea": c.line} for c in classes],
            "interfaces": interfaces,
            "type_aliases": type_aliases,
            "enums": enums,
            "imports": [imp.source_module for imp in imports],
            "exports": exports,
            "security_findings": [f.to_dict() for f in security_findings],
        }
