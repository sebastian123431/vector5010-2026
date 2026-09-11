"""
VECTOR 2026 // Motor de Inteligencia, Análisis, Codificación y Reparación de JavaScript
Proporciona capacidades de nivel experto para:
1. Análisis Léxico, Sintáctico y Estructural de JavaScript (ES6+ / Node.js / TypeScript).
2. Detección de Errores de Sintaxis, Paréntesis/Llaves Desbalanceadas y Delimitadores Rotos.
3. Auditoría de Seguridad (XSS, eval, Prototype Pollution) y Anti-Patrones (var, ==, unhandled Promises).
4. Motor de Auto-Reparación y Refactorización Inteligente de Código JavaScript.
5. Generación de Módulos y Arquitecturas JavaScript Modernas y Seguras.
6. Integración Híbrida: Nivel 1 (Quick Scanner Regex <2ms) y Nivel 2 (Tree-sitter AST & Taint Analysis).
"""

import re
import os
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Intentar cargar el subsistema de AST Tree-sitter
try:
    from .code_intelligence import TreeSitterJSParser, TreeSitterTSParser
    TREE_SITTER_AVAILABLE = True
except Exception as e:
    logger.warning(f"[JavaScriptEngine] Tree-sitter no disponible ({e}), operando en modo heurístico.")
    TREE_SITTER_AVAILABLE = False


class QuickScanner:
    """
    Escáner de nivel 1: Análisis ultra-rápido por expresiones regulares y pila léxica (<2ms).
    Especializado en verificación de delimitadores y escaneo preliminar.
    """

    def __init__(self):
        self.keywords = {
            'await', 'break', 'case', 'catch', 'class', 'const', 'continue', 'debugger',
            'default', 'delete', 'do', 'else', 'export', 'extends', 'finally', 'for',
            'function', 'if', 'import', 'in', 'instanceof', 'new', 'return', 'super',
            'switch', 'this', 'throw', 'try', 'typeof', 'var', 'void', 'while', 'with',
            'yield', 'let', 'static', 'enum', 'interface', 'package', 'implements'
        }

    def verificar_balance_delimitadores(self, code: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Verifica el balance estricto de paréntesis (), corchetes [] y llaves {},
        así como el cierre de comillas ('', "", ``) y comentarios (/* */).
        Retorna (es_valido, detalle_error).
        """
        stack = []
        mapping = {')': '(', ']': '[', '}': '{'}
        
        lines = code.splitlines()
        in_multiline_comment = False
        in_string = None  # None, "'", '"', '`'
        escape = False

        for line_num, line in enumerate(lines, start=1):
            col = 0
            while col < len(line):
                char = line[col]

                # 1. Manejo de comentarios multilínea
                if in_multiline_comment:
                    if col + 1 < len(line) and line[col:col+2] == '*/':
                        in_multiline_comment = False
                        col += 2
                        continue
                    col += 1
                    continue

                # 2. Manejo de strings
                if in_string:
                    if escape:
                        escape = False
                    elif char == '\\':
                        escape = True
                    elif char == in_string:
                        in_string = None
                    col += 1
                    continue

                # 3. Detección de inicio de comentarios
                if col + 1 < len(line) and line[col:col+2] == '//':
                    break
                if col + 1 < len(line) and line[col:col+2] == '/*':
                    in_multiline_comment = True
                    col += 2
                    continue

                # 4. Detección de strings
                if char in ("'", '"', '`'):
                    in_string = char
                    escape = False
                    col += 1
                    continue

                # 5. Delimitadores de apertura
                if char in ('(', '[', '{'):
                    stack.append((char, line_num, col + 1))
                # 6. Delimitadores de cierre
                elif char in (')', ']', '}'):
                    if not stack:
                        return False, {
                            "tipo": "cierre_huerfano",
                            "linea": line_num,
                            "columna": col + 1,
                            "caracter": char,
                            "mensaje": f"Se encontró '{char}' de cierre en línea {line_num}, col {col + 1} sin apertura correspondiente."
                        }
                    top_char, top_line, top_col = stack.pop()
                    expected = mapping[char]
                    if top_char != expected:
                        return False, {
                            "tipo": "desbalance",
                            "linea": line_num,
                            "columna": col + 1,
                            "caracter": char,
                            "esperado": expected,
                            "apertura_linea": top_line,
                            "apertura_col": top_col,
                            "mensaje": f"Discrepancia en línea {line_num}: se cerró con '{char}' pero se esperaba cerrar '{top_char}' abierto en línea {top_line}."
                        }

                col += 1

        if in_multiline_comment:
            return False, {
                "tipo": "comentario_abierto",
                "linea": len(lines),
                "columna": 1,
                "mensaje": "Comentario de bloque '/*' no fue cerrado con '*/'."
            }

        if in_string and in_string != '`':
            return False, {
                "tipo": "string_sin_cerrar",
                "linea": len(lines),
                "columna": 1,
                "mensaje": f"Cadena de texto delimitada por {in_string} no fue cerrada al final del archivo."
            }

        if stack:
            top_char, top_line, top_col = stack[-1]
            cierre_esperado = { '(': ')', '[': ']', '{': '}' }.get(top_char, '')
            return False, {
                "tipo": "apertura_sin_cerrar",
                "linea": top_line,
                "columna": top_col,
                "caracter": top_char,
                "esperado": cierre_esperado,
                "pendientes": len(stack),
                "mensaje": f"Delimitador '{top_char}' abierto en línea {top_line}, col {top_col} nunca fue cerrado (falta '{cierre_esperado}')."
            }

        return True, None

    def scan_regex(self, code: str, filename: str = "script.js") -> Dict[str, Any]:
        """Escaneo heurístico basado en patrones regex."""
        lines = code.splitlines()
        total_lines = len(lines)
        code_lines = len([l for l in lines if l.strip() and not l.strip().startswith("//")])
        comment_lines = total_lines - code_lines

        es_valido, error_sintaxis = self.verificar_balance_delimitadores(code)

        # Extracción de funciones
        functions = []
        for m in re.finditer(r'(?:async\s+)?function(?:\s*\*)?\s*([a-zA-Z0-9_$]+)\s*\(([^)]*)\)', code):
            fn_name = m.group(1)
            raw_args = m.group(2).strip()
            args = [a.strip().split('=')[0].strip() for a in raw_args.split(',') if a.strip()]
            line_idx = code[:m.start()].count('\n') + 1
            functions.append({
                "nombre": fn_name,
                "tipo": "declaracion",
                "linea": line_idx,
                "parametros": args,
                "is_async": 'async' in m.group(0),
                "is_generator": '*' in m.group(0)
            })

        for m in re.finditer(r'(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*=\s*(async\s*)?(?:\(([^)]*)\)|([a-zA-Z0-9_$]+))\s*=>', code):
            fn_name = m.group(1)
            is_async = bool(m.group(2))
            raw_args = m.group(3) or m.group(4) or ""
            args = [a.strip().split('=')[0].strip() for a in raw_args.split(',') if a.strip()]
            line_idx = code[:m.start()].count('\n') + 1
            if fn_name not in [f["nombre"] for f in functions]:
                functions.append({
                    "nombre": fn_name,
                    "tipo": "arrow",
                    "linea": line_idx,
                    "parametros": args,
                    "is_async": is_async,
                    "is_generator": False
                })

        for m in re.finditer(r'^\s*(?:async\s+)?(?:static\s+)?(?:get\s+|set\s+)?([a-zA-Z0-9_$]+)\s*\(([^)]*)\)\s*\{', code, re.MULTILINE):
            fn_name = m.group(1)
            if fn_name not in self.keywords and fn_name not in ('if', 'for', 'while', 'switch', 'catch'):
                raw_args = m.group(2).strip()
                args = [a.strip().split('=')[0].strip() for a in raw_args.split(',') if a.strip()]
                line_idx = code[:m.start()].count('\n') + 1
                if fn_name not in [f["nombre"] for f in functions]:
                    functions.append({
                        "nombre": fn_name,
                        "tipo": "metodo",
                        "linea": line_idx,
                        "parametros": args,
                        "is_async": 'async' in m.group(0),
                        "is_generator": False
                    })

        # Clases
        classes = []
        for m in re.finditer(r'class\s+([a-zA-Z0-9_$]+)(?:\s+extends\s+([a-zA-Z0-9_$]+))?', code):
            cls_name = m.group(1)
            extends = m.group(2) or None
            line_idx = code[:m.start()].count('\n') + 1
            classes.append({
                "nombre": cls_name,
                "hereda_de": extends,
                "linea": line_idx
            })

        # Imports y Exports
        imports = []
        for m in re.finditer(r'import\s+(?:(?:\{([^}]+)\}|\*\s+as\s+([a-zA-Z0-9_$]+)|([a-zA-Z0-9_$]+))\s+from\s+)?[\'"]([^\'"]+)[\'"]', code):
            pkg = m.group(4)
            items = m.group(1) or m.group(2) or m.group(3) or ""
            imports.append(f"{pkg} ({items.strip()})" if items.strip() else pkg)

        for m in re.finditer(r'(?:const|let|var)\s+(?:\{([^}]+)\}|([a-zA-Z0-9_$]+))\s*=\s*require\([\'"]([^\'"]+)[\'"]\)', code):
            pkg = m.group(3)
            named = m.group(1) or m.group(2) or ""
            imports.append(f"require('{pkg}') [{named.strip()}]")

        exports = []
        for m in re.finditer(r'export\s+(?:default\s+)?(?:class|function|const|let|var)?\s*([a-zA-Z0-9_$]+)?', code):
            exp = m.group(1) or "default"
            exports.append(exp)
        for m in re.finditer(r'module\.exports\s*=\s*([a-zA-Z0-9_$]+|\{[^}]+\})', code):
            exports.append(f"module.exports ({m.group(1)[:30]})")

        # Anti-patrones y vulnerabilidades
        issues = []
        var_matches = list(re.finditer(r'\bvar\s+([a-zA-Z0-9_$]+)', code))
        if var_matches:
            ejemplos = ", ".join([v.group(1) for v in var_matches[:3]])
            issues.append(f"Uso de 'var' ({len(var_matches)} veces, ej: {ejemplos}). Recomendado migrar a 'const' o 'let'.")

        debil_matches = list(re.finditer(r'([^=!<>])([=!]=)([^=])', code))
        if debil_matches:
            issues.append(f"Uso de igualdad débil ('==' o '!=') detectado {len(debil_matches)} veces. Utilizar siempre '===' o '!=='.")

        dom_unsafe = list(re.finditer(r'document\.(?:getElementById|querySelector)\([\'"][^\'"]+[\'"]\)\.([a-zA-Z0-9_$]+)', code))
        if dom_unsafe:
            prop = dom_unsafe[0].group(1)
            issues.append(f"Acceso directo inseguro a propiedades del DOM (ej: `.{prop}`) sin comprobar null-guard.")

        inner_html = list(re.finditer(r'\.innerHTML\s*=', code))
        if inner_html:
            issues.append(f"Asignación a '.innerHTML' detectada ({len(inner_html)} veces). Puede generar vulnerabilidad de Cross-Site Scripting (XSS).")

        eval_matches = list(re.finditer(r'\b(eval|new\s+Function)\s*\(', code))
        if eval_matches:
            issues.append("Uso de 'eval()' o 'new Function()' detectado. Peligro crítico de ejecución de código arbitrario.")

        for f in functions:
            if f["is_async"]:
                fn_snippet = code[code.find(f["nombre"]):code.find(f["nombre"]) + 400]
                if 'await' not in fn_snippet and 'return' in fn_snippet:
                    issues.append(f"Función async '{f['nombre']}' no parece utilizar 'await'.")

        consoles = list(re.finditer(r'console\.(?:log|warn|error)\(', code))
        if len(consoles) > 5:
            issues.append(f"Presencia de {len(consoles)} sentencias console.* residuales.")

        return {
            "success": True,
            "filename": filename,
            "total_lines": total_lines,
            "code_lines": code_lines,
            "comment_lines": comment_lines,
            "es_valido": es_valido,
            "error_sintaxis": error_sintaxis,
            "funciones": functions,
            "clases": classes,
            "imports": list(dict.fromkeys(imports))[:12],
            "exports": list(dict.fromkeys(exports))[:8],
            "issues": issues,
            "mode": "quick"
        }


class JavaScriptEngine:
    """
    Motor especializado en ingeniería de software para JavaScript.
    Integra Nivel 1 (Quick Scanner) y Nivel 2 (Tree-sitter AST & Taint Analysis).
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(JavaScriptEngine, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        self.quick_scanner = QuickScanner()
        self.js_parser = None
        self.ts_parser = None
        if TREE_SITTER_AVAILABLE:
            try:
                self.js_parser = TreeSitterJSParser()
                self.ts_parser = TreeSitterTSParser()
            except Exception as e:
                logger.error(f"[JavaScriptEngine] Error instanciando parsers Tree-sitter: {e}")

    def verificar_balance_delimitadores(self, code: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Verificación rápida de delimitadores por pila."""
        return self.quick_scanner.verificar_balance_delimitadores(code)

    def analyze_javascript(self, code: str, filename: str = "script.js", mode: str = "auto") -> Dict[str, Any]:
        """
        Análisis unificado de JavaScript/TypeScript.
        - mode='auto': Utiliza Tree-sitter si está disponible, fusionando con balance de delimitadores.
        - mode='quick': Utiliza QuickScanner puramente regex (<2ms).
        - mode='deep': Fuerza análisis de AST completo y flujo de taint.
        """
        is_ts = filename.endswith(".ts") or filename.endswith(".tsx")

        if mode == "quick" or (not TREE_SITTER_AVAILABLE and mode != "deep"):
            return self.quick_scanner.scan_regex(code, filename)

        # Análisis profundo mediante Tree-sitter
        try:
            parser = self.ts_parser if (is_ts and self.ts_parser) else self.js_parser
            if not parser:
                return self.quick_scanner.scan_regex(code, filename)

            ts_res = parser.parse(code, filename)
            valido_delimiters, err_delimiters = self.quick_scanner.verificar_balance_delimitadores(code)

            # Extraer lista de issues y recomendaciones a partir de findings de seguridad
            issues = []
            for f in ts_res.get("security_findings", []):
                issues.append(f"[{f['severity'].upper()}] {f['title']}: {f['description']} (L{f['line']}). {f['recommendation']}")

            if ts_res.get("has_syntax_errors") and not err_delimiters and ts_res.get("syntax_errors"):
                primer_err = ts_res["syntax_errors"][0]
                err_delimiters = {
                    "tipo": "error_ast_sintaxis",
                    "linea": primer_err["line"],
                    "columna": primer_err["column"],
                    "mensaje": primer_err["message"]
                }

            es_valido = valido_delimiters and not ts_res.get("has_syntax_errors")

            # Combinar funciones
            funciones_formateadas = [
                {
                    "nombre": f["nombre"],
                    "tipo": f.get("tipo", "funcion"),
                    "linea": f["linea"],
                    "parametros": f.get("parametros", []),
                    "is_async": f.get("is_async", False),
                    "is_generator": f.get("is_generator", False)
                }
                for f in ts_res.get("functions", [])
            ]

            metrics = ts_res.get("metrics", {})

            return {
                "success": True,
                "filename": filename,
                "total_lines": metrics.get("total_lines", len(code.splitlines())),
                "code_lines": metrics.get("code_lines", 0),
                "comment_lines": metrics.get("comment_lines", 0),
                "es_valido": es_valido,
                "error_sintaxis": err_delimiters,
                "funciones": funciones_formateadas,
                "clases": ts_res.get("classes", []),
                "interfaces": ts_res.get("interfaces", []),
                "type_aliases": ts_res.get("type_aliases", []),
                "enums": ts_res.get("enums", []),
                "imports": ts_res.get("imports", [])[:12],
                "exports": ts_res.get("exports", [])[:8],
                "issues": issues,
                "complexity_metrics": metrics,
                "security_findings": ts_res.get("security_findings", []),
                "ast_available": True,
                "mode": "deep"
            }

        except Exception as e:
            logger.error(f"[JavaScriptEngine] Error en Tree-sitter parser: {e}. Fallback a QuickScanner.")
            return self.quick_scanner.scan_regex(code, filename)

    def analizar_codigo_js(self, code: str, filename: str = "script.js") -> Dict[str, Any]:
        """Método de retrocompatibilidad estricta para el sistema existente."""
        return self.analyze_javascript(code, filename=filename, mode="auto")

    def reparar_codigo_js(self, code: str, error_desc: Optional[str] = None) -> Dict[str, Any]:
        """
        Auto-repara problemas sintácticos y anti-patrones en código JavaScript:
        - Cierra llaves, paréntesis y corchetes faltantes.
        - Cierra strings y template literals no terminados.
        - Corrige accesos al DOM riesgosos con Optional Chaining (?.).
        - Actualiza 'var' por 'let' de forma segura.
        - Reemplaza operadores de igualdad débil por estrictos.
        """
        repaired = code
        cambios = []

        # 1. Resolver desbalance de delimitadores
        valido, err = self.verificar_balance_delimitadores(repaired)
        if not valido and err:
            tipo = err.get("tipo")
            if tipo == "apertura_sin_cerrar":
                stack = []
                mapping = {')': '(', ']': '[', '}': '{'}
                inverse = {'(': ')', '[': ']', '{': '}'}
                for char in repaired:
                    if char in inverse:
                        stack.append(char)
                    elif char in mapping:
                        if stack and stack[-1] == mapping[char]:
                            stack.pop()

                if stack:
                    cierres = "".join([inverse[c] for c in reversed(stack)])
                    repaired = repaired.rstrip() + "\n" + cierres + "\n"
                    cambios.append(f"Se balancearon y cerraron {len(stack)} bloques/delimitadores faltantes al final del script: `{cierres}`.")

            elif tipo == "string_sin_cerrar":
                repaired = repaired.rstrip() + "'\n"
                cambios.append("Se cerró la comilla de string pendiente.")

            elif tipo == "comentario_abierto":
                repaired = repaired.rstrip() + " */\n"
                cambios.append("Se cerró el bloque de comentario con '*/'.")

        # 2. Modernizar 'var' a 'let'
        var_count = len(re.findall(r'\bvar\s+', repaired))
        if var_count > 0:
            repaired = re.sub(r'\bvar\s+', 'let ', repaired)
            cambios.append(f"Se actualizaron {var_count} declaraciones 'var' a 'let' para garantizar alcance de bloque.")

        # 3. Igualdad estricta (reemplazar == con === cuidando no romper !== ni ===)
        debil_eq = len(re.findall(r'(?<=[^\s=!<>])\s*==\s*(?=[^\s=])', repaired))
        if debil_eq > 0:
            repaired = re.sub(r'(?<=[^\s=!<>])\s*==\s*(?=[^\s=])', ' === ', repaired)
            cambios.append(f"Se corrigieron {debil_eq} operadores de igualdad débil ('==') a estricta ('===').")

        # 4. Null-guards con Optional Chaining (?.) en accesos DOM comunes
        dom_pattern = r'(document\.(?:getElementById|querySelector)\([\'"][^\'"]+[\'"]\))\s*\.\s*([a-zA-Z0-9_$]+)'
        if re.search(dom_pattern, repaired):
            repaired = re.sub(dom_pattern, r'\1?.\2', repaired)
            cambios.append("Se añadió encadenamiento opcional (`?.`) en llamadas a elementos del DOM.")

        # Validar nuevamente tras la reparación
        valido_final, err_final = self.verificar_balance_delimitadores(repaired)

        return {
            "success": True,
            "codigo_original": code,
            "codigo_reparado": repaired,
            "cambios_aplicados": cambios,
            "es_valido": valido_final,
            "error_remanente": err_final.get("mensaje") if err_final else None
        }

    def generar_reporte_tecnico(self, analisis: Dict[str, Any], reparacion: Optional[Dict[str, Any]] = None) -> str:
        """
        Produce un informe estructurado de alta ingeniería para ser inyectado en el prompt de Vector.
        """
        fn = analisis.get("filename", "script.js")
        total = analisis.get("total_lines", 0)
        code_l = analisis.get("code_lines", 0)
        comm_l = analisis.get("comment_lines", 0)
        es_val = analisis.get("es_valido", True)
        err = analisis.get("error_sintaxis")

        status_str = "[SINTAXIS JS VÁLIDA]" if es_val else "[ERROR CRÍTICO DE SINTAXIS JS]"
        err_str = f"\n- DETALLE DEL ERROR SINTÁCTICO: {err['mensaje']}" if err else ""

        funcs = analisis.get("funciones", [])
        funcs_str = ", ".join([f"{f['nombre']}({', '.join(f.get('parametros', [])[:3])})" for f in funcs[:8]]) or "Ninguna función detectada"

        classes = analisis.get("clases", [])
        cls_str = ", ".join([f"{c['nombre']}" + (f" extends {c['hereda_de']}" if c.get('hereda_de') else "") for c in classes[:5]]) or "Ninguna clase detectada"

        imports = analisis.get("imports", [])
        imp_str = ", ".join(imports[:6]) or "Sin módulos externos requeridos"

        issues = analisis.get("issues", [])
        issues_str = "\n".join([f"  - {i}" for i in issues]) if issues else "  - Sin vulnerabilidades ni anti-patrones evidentes."

        metrics = analisis.get("complexity_metrics", {})
        metrics_str = ""
        if metrics:
            metrics_str = (
                f"- Métricas AST: Complejidad ciclomática = {metrics.get('cyclomatic_complexity', 1)}, "
                f"Profundidad máxima = {metrics.get('max_nesting_depth', 0)}\n"
            )

        reparacion_str = ""
        if reparacion and reparacion.get("cambios_aplicados"):
            cambios_bullets = "\n".join([f"  * {c}" for c in reparacion["cambios_aplicados"]])
            reparacion_str = (
                f"\nPROPUESTA DE AUTO-REPARACIÓN JAVASCRIPT DISPONIBLE:\n"
                f"{cambios_bullets}\n"
                f"Estado tras auto-reparación: {'[CORREGIDO Y OPERATIVO]' if reparacion.get('es_valido') else '[REQUIERE REFACTORIZACIÓN ADICIONAL]'}\n"
            )

        reporte = (
            f"=== ANÁLISIS TÉCNICO PROFUNDO DE JAVASCRIPT (ECMAScript ES6+) ===\n"
            f"- Archivo: {fn} ({total} líneas totales, {code_l} líneas de código, {comm_l} comentarios)\n"
            f"- Estado de compilación / parsing: {status_str}{err_str}\n"
            f"{metrics_str}"
            f"- Clases detectadas ({len(classes)}): {cls_str}\n"
            f"- Funciones detectadas ({len(funcs)}): {funcs_str}\n"
            f"- Dependencias e importaciones: {imp_str}\n"
            f"- Diagnóstico de calidad, seguridad y anti-patrones:\n{issues_str}\n"
            f"{reparacion_str}"
        )
        return reporte


# Instancia Singleton Global
javascript_engine = JavaScriptEngine()
