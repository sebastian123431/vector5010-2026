"""
Parser AST y Analizador Estructural para JavaScript mediante Tree-sitter.
Proporciona extracción precisa de nodos AST, cálculo de complejidad ciclomática,
detección de errores de sintaxis y auditoría de seguridad en profundidad.
"""

from typing import Dict, Any, List, Optional, Tuple
import tree_sitter
import tree_sitter_javascript as tsjs

from .ast_models import (
    FunctionInfo, ClassInfo, ImportInfo, SecurityFinding, ComplexityMetrics,
    NodeKind, FindingSeverity
)
from .security_rules import (
    SecurityRuleChecker, TaintAnalysisEngine, UNTRUSTED_SOURCES
)


class TreeSitterJSParser:
    """
    Analizador estructural de JavaScript basado en Tree-sitter.
    Analiza código ECMAScript moderno con precisión a nivel de token y AST.
    """

    def __init__(self):
        self.language = tree_sitter.Language(tsjs.language())
        self.parser = tree_sitter.Parser(self.language)

    def parse(self, code: str, filename: str = "script.js") -> Dict[str, Any]:
        """
        Ejecuta el análisis estructural completo de código JavaScript.
        """
        code_bytes = bytes(code, "utf-8")
        tree = self.parser.parse(code_bytes)
        root = tree.root_node

        lines = code.splitlines()
        total_lines = len(lines)
        code_lines = len([l for l in lines if l.strip() and not l.strip().startswith("//")])
        comment_lines = total_lines - code_lines

        # Estructuras para recolectar
        functions: List[FunctionInfo] = []
        classes: List[ClassInfo] = []
        imports: List[ImportInfo] = []
        exports: List[str] = []
        syntax_errors: List[Dict[str, Any]] = []
        security_findings: List[SecurityFinding] = []

        taint_engine = TaintAnalysisEngine()
        cyclomatic_complexity = 1
        max_nesting_depth = 0

        # Recorrer el árbol con DFS
        def walk_node(node, current_depth: int = 0):
            nonlocal cyclomatic_complexity, max_nesting_depth
            if current_depth > max_nesting_depth:
                max_nesting_depth = current_depth

            node_type = node.type

            # 1. Errores de sintaxis
            if node_type == "ERROR" or node.is_missing:
                start_point = node.start_point
                syntax_errors.append({
                    "line": start_point[0] + 1,
                    "column": start_point[1] + 1,
                    "text": code_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")[:60],
                    "message": f"Error de sintaxis AST en línea {start_point[0] + 1}, columna {start_point[1] + 1}"
                })

            # 2. Ramificaciones (Complejidad ciclomática)
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

            # 3. Declaraciones de funciones
            if node_type == "function_declaration":
                fn_info = self._extract_function_info(node, code_bytes, is_method=False)
                if fn_info:
                    functions.append(fn_info)

            elif node_type == "arrow_function":
                fn_info = self._extract_arrow_function_info(node, code_bytes)
                if fn_info:
                    functions.append(fn_info)

            # 4. Declaraciones de clases
            elif node_type == "class_declaration":
                cls_info = self._extract_class_info(node, code_bytes)
                if cls_info:
                    classes.append(cls_info)

            # 5. Imports
            elif node_type == "import_statement":
                imp_info = self._extract_import_info(node, code_bytes)
                if imp_info:
                    imports.append(imp_info)

            # 6. Exports
            elif node_type in ("export_statement",):
                exp_text = code_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
                exports.append(exp_text[:50].strip())

            # 7. Asignaciones y flujo de taint
            elif node_type == "assignment_expression":
                left_node = node.child_by_field_name("left")
                right_node = node.child_by_field_name("right")
                if left_node and right_node:
                    left_text = code_bytes[left_node.start_byte:left_node.end_byte].decode("utf-8", errors="replace")
                    right_text = code_bytes[right_node.start_byte:right_node.end_byte].decode("utf-8", errors="replace")

                    # Verificar si la derecha es una fuente insegura
                    for src in UNTRUSTED_SOURCES:
                        if src in right_text:
                            taint_engine.register_source(left_text.strip(), src)
                            break
                    else:
                        taint_engine.propagate(left_text.strip(), right_text)

                    # Verificar si la izquierda es un sink (DOM XSS)
                    for sink in ("innerHTML", "outerHTML", "document.write", "insertAdjacentHTML"):
                        if sink in left_text:
                            taint_origin = taint_engine.is_tainted(right_text)
                            finding = SecurityRuleChecker.check_dom_xss(
                                sink, right_text, left_node.start_point[0] + 1, left_node.start_point[1] + 1, taint_origin
                            )
                            if finding:
                                security_findings.append(finding)

            # 7b. Declaraciones de variables y flujo de taint
            elif node_type == "variable_declarator":
                name_node = node.child_by_field_name("name")
                val_node = node.child_by_field_name("value")
                if name_node and val_node:
                    var_name = code_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace").strip()
                    val_text = code_bytes[val_node.start_byte:val_node.end_byte].decode("utf-8", errors="replace").strip()
                    for src in UNTRUSTED_SOURCES:
                        if src in val_text:
                            taint_engine.register_source(var_name, src)
                            break
                    else:
                        taint_engine.propagate(var_name, val_text)

            # 8. Comprobaciones de seguridad en expresiones
            elif node_type in ("call_expression", "new_expression"):
                call_text = code_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
                finding = SecurityRuleChecker.check_eval_and_code_injection(
                    call_text, node.start_point[0] + 1, node.start_point[1] + 1
                )
                if finding:
                    security_findings.append(finding)

            # 9. Prototype pollution
            elif node_type == "member_expression":
                mem_text = code_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
                finding = SecurityRuleChecker.check_prototype_pollution(
                    mem_text, node.start_point[0] + 1, node.start_point[1] + 1
                )
                if finding:
                    security_findings.append(finding)

            # 10. Igualdad débil
            elif node_type == "binary_expression":
                op_node = node.child_by_field_name("operator")
                if op_node:
                    op = code_bytes[op_node.start_byte:op_node.end_byte].decode("utf-8", errors="replace")
                    if op in ("==", "!="):
                        expr_text = code_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
                        finding = SecurityRuleChecker.check_weak_equality(
                            op, op_node.start_point[0] + 1, op_node.start_point[1] + 1, expr_text
                        )
                        if finding:
                            security_findings.append(finding)

            # 11. Declaraciones 'var'
            elif node_type == "variable_declaration":
                decl_text = code_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace").strip()
                if decl_text.startswith("var "):
                    finding = SecurityRuleChecker.check_var_hoisting(
                        decl_text[:30], node.start_point[0] + 1, node.start_point[1] + 1, decl_text
                    )
                    if finding:
                        security_findings.append(finding)

            # Continuar recorrido recursivo
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
            "has_syntax_errors": root.has_error or bool(syntax_errors),
            "syntax_errors": syntax_errors,
            "metrics": metrics.to_dict(),
            "functions": [
                {
                    "nombre": f.name,
                    "tipo": f.kind.value,
                    "linea": f.line,
                    "columna": f.column,
                    "parametros": f.parameters,
                    "is_async": f.is_async,
                    "is_generator": f.is_generator,
                }
                for f in functions
            ],
            "classes": [
                {
                    "nombre": c.name,
                    "hereda_de": c.heritage,
                    "linea": c.line,
                    "metodos": [m.name for m in c.methods],
                }
                for c in classes
            ],
            "imports": [
                f"{imp.source_module} ({', '.join(imp.imported_items)})" if imp.imported_items else imp.source_module
                for imp in imports
            ],
            "exports": exports,
            "security_findings": [f.to_dict() for f in security_findings],
        }

    def _extract_function_info(self, node, code_bytes: bytes, is_method: bool = False) -> Optional[FunctionInfo]:
        name_node = node.child_by_field_name("name")
        fn_name = code_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace") if name_node else "anonymous"

        params_node = node.child_by_field_name("parameters")
        params: List[str] = []
        if params_node:
            for child in params_node.children:
                if child.type in ("identifier", "formal_parameters", "assignment_pattern"):
                    p_text = code_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
                    if p_text not in ("(", ")", ","):
                        params.append(p_text.split("=")[0].strip())

        raw_text = code_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
        is_async = "async" in raw_text[:40]
        is_gen = "*" in raw_text[:40]

        return FunctionInfo(
            kind=NodeKind.METHOD_DEFINITION if is_method else NodeKind.FUNCTION_DECLARATION,
            name=fn_name,
            line=node.start_point[0] + 1,
            column=node.start_point[1] + 1,
            end_line=node.end_point[0] + 1,
            end_column=node.end_point[1] + 1,
            raw_text=raw_text[:200],
            parameters=params,
            is_async=is_async,
            is_generator=is_gen,
        )

    def _extract_arrow_function_info(self, node, code_bytes: bytes) -> Optional[FunctionInfo]:
        parent = node.parent
        fn_name = "anonymous"
        if parent and parent.type == "variable_declarator":
            name_node = parent.child_by_field_name("name")
            if name_node:
                fn_name = code_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")

        params_node = node.child_by_field_name("parameters")
        params: List[str] = []
        if params_node:
            for child in params_node.children:
                if child.type in ("identifier", "assignment_pattern"):
                    p_text = code_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
                    if p_text not in ("(", ")", ","):
                        params.append(p_text.split("=")[0].strip())

        raw_text = code_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
        is_async = "async" in raw_text[:30]

        return FunctionInfo(
            kind=NodeKind.ARROW_FUNCTION,
            name=fn_name,
            line=node.start_point[0] + 1,
            column=node.start_point[1] + 1,
            end_line=node.end_point[0] + 1,
            end_column=node.end_point[1] + 1,
            raw_text=raw_text[:200],
            parameters=params,
            is_async=is_async,
        )

    def _extract_class_info(self, node, code_bytes: bytes) -> Optional[ClassInfo]:
        name_node = node.child_by_field_name("name")
        cls_name = code_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace") if name_node else "AnonymousClass"

        heritage = None
        for child in node.children:
            if child.type == "class_heritage":
                heritage = code_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace").replace("extends", "").strip()

        methods: List[FunctionInfo] = []
        body_node = node.child_by_field_name("body")
        if body_node:
            for child in body_node.children:
                if child.type == "method_definition":
                    m_info = self._extract_function_info(child, code_bytes, is_method=True)
                    if m_info:
                        methods.append(m_info)

        return ClassInfo(
            kind=NodeKind.CLASS_DECLARATION,
            name=cls_name,
            line=node.start_point[0] + 1,
            column=node.start_point[1] + 1,
            end_line=node.end_point[0] + 1,
            end_column=node.end_point[1] + 1,
            heritage=heritage,
            methods=methods,
        )

    def _extract_import_info(self, node, code_bytes: bytes) -> Optional[ImportInfo]:
        source_node = node.child_by_field_name("source")
        source = code_bytes[source_node.start_byte:source_node.end_byte].decode("utf-8", errors="replace").strip("'\"") if source_node else ""

        items: List[str] = []
        for child in node.children:
            if child.type == "import_clause":
                clause_text = code_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
                items.append(clause_text.strip())

        return ImportInfo(
            kind=NodeKind.IMPORT_DECLARATION,
            name=source,
            line=node.start_point[0] + 1,
            column=node.start_point[1] + 1,
            end_line=node.end_point[0] + 1,
            end_column=node.end_point[1] + 1,
            source_module=source,
            imported_items=items,
        )
