"""
Módulo de Análisis Profundo de Archivos Adjuntos para Vector (Estilo ChatGPT / Code Interpreter).
Realiza una inspección técnica exhaustiva, granular y no superficial de archivos:
- Código fuente (Python, JS, TS, HTML, CSS, SQL, JSON, YAML): AST sintáctico, catálogo de funciones/clases, importaciones, complejidad, vulnerabilidades y errores de compilación.
- Datos tabulares (CSV, TSV): Esquema, columnas, tipos de datos, conteo de filas, valores nulos y resumen estadístico.
- Datos estructurados (JSON): Validación sintáctica, claves de nivel superior, profundidad y tipos.
- Logs y Documentación (TXT, LOG, MD): Jerarquía de secciones, alertas críticas, excepciones y advertencias.
"""

import ast
import csv
import io
import json
import os
import re
from typing import Dict, Any, List, Optional
from .javascript_engine import javascript_engine


def analyze_python_content(content: str, filename: str) -> Dict[str, Any]:
    lines = content.splitlines()
    total_lines = len(lines)
    non_empty_lines = len([l for l in lines if l.strip()])
    comment_lines = len([l for l in lines if l.strip().startswith("#")])
    
    syntax_error = None
    functions = []
    classes = []
    imports = []
    issues = []
    
    try:
        tree = ast.parse(content, filename=filename)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, getattr(ast, 'AsyncFunctionDef', ast.FunctionDef)):
                args_list = [a.arg for a in node.args.args]
                functions.append({
                    "name": node.name,
                    "line": node.lineno,
                    "args": args_list,
                    "is_async": isinstance(node, getattr(ast, 'AsyncFunctionDef', ()))
                })
            elif isinstance(node, ast.ClassDef):
                methods = [n.name for n in node.body if isinstance(n, (ast.FunctionDef, getattr(ast, 'AsyncFunctionDef', ())))]
                bases = []
                for b in node.bases:
                    if isinstance(b, ast.Name):
                        bases.append(b.id)
                    elif isinstance(b, ast.Attribute):
                        bases.append(b.attr)
                classes.append({
                    "name": node.name,
                    "line": node.lineno,
                    "methods": methods,
                    "bases": bases
                })
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                for alias in node.names:
                    imports.append(f"{mod}.{alias.name}" if mod else alias.name)
            elif isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    issues.append(f"Línea {node.lineno}: Bloque 'except:' desnudo sin capturar excepción específica (anti-patrón).")
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in ('eval', 'exec'):
                    issues.append(f"Línea {node.lineno}: Uso peligroso de '{node.func.id}()' que permite inyección arbitraria de código.")
    except SyntaxError as e:
        syntax_error = {
            "line": e.lineno or 1,
            "offset": e.offset or 0,
            "text": (e.text or "").strip(),
            "msg": str(e.msg)
        }
    except Exception as e:
        syntax_error = {"line": 1, "offset": 0, "text": "", "msg": str(e)}

    return {
        "type": "python",
        "total_lines": total_lines,
        "code_lines": non_empty_lines - comment_lines,
        "comment_lines": comment_lines,
        "syntax_error": syntax_error,
        "functions": functions,
        "classes": classes,
        "imports": list(dict.fromkeys(imports))[:15],
        "issues": issues
    }


def analyze_csv_content(content: str) -> Dict[str, Any]:
    lines = content.strip().splitlines()
    total_rows = len(lines)
    if not lines:
        return {"type": "csv", "total_rows": 0, "columns": [], "null_counts": {}, "sample_rows": []}
    
    # Detect delimiter
    sample = "\n".join(lines[:5])
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=',;\t|')
        delimiter = dialect.delimiter
    except Exception:
        delimiter = ',' if ',' in lines[0] else ';'

    reader = csv.reader(io.StringIO(content), delimiter=delimiter)
    rows = list(reader)
    if not rows:
        return {"type": "csv", "total_rows": 0, "columns": [], "null_counts": {}, "sample_rows": []}

    headers = [h.strip() for h in rows[0]]
    data_rows = rows[1:]
    num_data_rows = len(data_rows)
    
    # Analyze columns and null values
    null_counts = {h: 0 for h in headers}
    col_types = {h: set() for h in headers}
    
    for r in data_rows:
        for idx, val in enumerate(r):
            if idx < len(headers):
                h = headers[idx]
                v_clean = val.strip()
                if not v_clean:
                    null_counts[h] += 1
                else:
                    if v_clean.isdigit():
                        col_types[h].add("int")
                    elif re.match(r'^-?\d+(\.\d+)?$', v_clean):
                        col_types[h].add("float")
                    else:
                        col_types[h].add("str")

    type_summary = {}
    for h, ts in col_types.items():
        if not ts:
            type_summary[h] = "vacío"
        elif len(ts) == 1:
            type_summary[h] = list(ts)[0]
        else:
            type_summary[h] = "mixto (" + "/".join(ts) + ")"

    sample_preview = []
    for r in data_rows[:3]:
        sample_preview.append(dict(zip(headers, r[:len(headers)])))

    return {
        "type": "csv",
        "delimiter": delimiter,
        "total_rows": num_data_rows,
        "total_cols": len(headers),
        "headers": headers,
        "column_types": type_summary,
        "null_counts": null_counts,
        "sample_preview": sample_preview
    }


def analyze_json_content(content: str) -> Dict[str, Any]:
    try:
        data = json.loads(content)
        is_list = isinstance(data, list)
        is_dict = isinstance(data, dict)
        
        if is_dict:
            keys = list(data.keys())
            item_count = len(keys)
            types_per_key = {k: type(v).__name__ for k, v in list(data.items())[:12]}
            sample_keys = keys[:10]
        elif is_list:
            item_count = len(data)
            sample_keys = []
            types_per_key = {"list_length": item_count, "item_type": type(data[0]).__name__ if data else "empty"}
        else:
            item_count = 1
            sample_keys = []
            types_per_key = {"primitive": type(data).__name__}

        return {
            "type": "json",
            "valid": True,
            "structure": "Array" if is_list else ("Object" if is_dict else "Primitive"),
            "item_count": item_count,
            "keys": sample_keys,
            "types_per_key": types_per_key
        }
    except json.JSONDecodeError as e:
        return {
            "type": "json",
            "valid": False,
            "error": f"Línea {e.lineno}, Col {e.colno}: {e.msg}"
        }


def analyze_general_code(content: str, ext: str) -> Dict[str, Any]:
    lines = content.splitlines()
    total_lines = len(lines)
    
    # Detect functions, classes, exports via regex
    functions = []
    classes = []
    
    if ext in ('.js', '.ts', '.jsx', '.tsx'):
        # JS/TS functions & classes
        fn_matches = re.findall(r'(?:function\s+([a-zA-Z0-9_$]+)|const\s+([a-zA-Z0-9_$]+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>)', content)
        for m in fn_matches:
            name = m[0] or m[1]
            if name and name not in functions:
                functions.append(name)
        cls_matches = re.findall(r'class\s+([a-zA-Z0-9_$]+)', content)
        for c in cls_matches:
            if c not in classes:
                classes.append(c)
    elif ext in ('.html', '.htm'):
        # HTML tag analysis
        tags = set(re.findall(r'<([a-zA-Z0-9]+)', content))
        ids = re.findall(r'id=["\']([^"\']+)["\']', content)
        classes = re.findall(r'class=["\']([^"\']+)["\']', content)
        return {
            "type": "html",
            "total_lines": total_lines,
            "tags_count": len(tags),
            "ids_found": ids[:8],
            "classes_found": list(set(classes))[:8]
        }
    elif ext in ('.css', '.scss', '.sass'):
        selectors = re.findall(r'([.#]?[a-zA-Z0-9_-]+)\s*\{', content)
        return {
            "type": "css",
            "total_lines": total_lines,
            "rules_count": len(selectors),
            "selectors": selectors[:10]
        }
    elif ext in ('.sql',):
        tables = re.findall(r'(?:FROM|JOIN|TABLE|INTO)\s+([a-zA-Z0-9_.]+)', content, re.IGNORECASE)
        stmts = re.findall(r'\b(SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER)\b', content, re.IGNORECASE)
        return {
            "type": "sql",
            "total_lines": total_lines,
            "statements": [s.upper() for s in set(stmts)],
            "tables": list(set(tables))[:8]
        }

    return {
        "type": "code",
        "total_lines": total_lines,
        "functions": functions[:12],
        "classes": classes[:8]
    }


def analyze_log_or_text(content: str) -> Dict[str, Any]:
    lines = content.splitlines()
    total_lines = len(lines)
    
    errors = []
    warnings = []
    
    for idx, l in enumerate(lines[:500], start=1):
        l_upper = l.upper()
        if any(e in l_upper for e in ("ERROR", "CRITICAL", "EXCEPTION", "FATAL", "TRACEBACK", "FAILED")):
            errors.append(f"L{idx}: {l.strip()[:100]}")
        elif any(w in l_upper for w in ("WARN", "WARNING")):
            warnings.append(f"L{idx}: {l.strip()[:100]}")
            
    return {
        "type": "log_text",
        "total_lines": total_lines,
        "errors": errors[:6],
        "warnings": warnings[:5]
    }


def deep_inspect_file(filename: str, content: str, mime_type: str = "") -> str:
    """
    Ejecuta una inspección estructural profunda sobre el archivo adjunto y genera
    un informe técnico detallado (estilo ChatGPT Code Interpreter) para ser inyectado
    directamente en el System Prompt de Vector.
    """
    ext = os.path.splitext(filename)[1].lower()
    
    # 1. Ejecutar análisis especializado según extensión
    if ext == '.py':
        res = analyze_python_content(content, filename)
        status_sintaxis = "[ERROR SINTACTICO AST]" if res["syntax_error"] else "[SINTAXIS AST VALIDA]"
        
        funcs_str = ", ".join([f"{f['name']}({', '.join(f['args'][:3])})" for f in res["functions"][:8]]) or "Ninguna función detectada"
        classes_str = ", ".join([f"{c['name']} [Métodos: {', '.join(c['methods'][:4])}]" for c in res["classes"][:5]]) or "Ninguna clase detectada"
        imports_str = ", ".join(res["imports"]) or "Sin importaciones externas"
        
        error_detail = ""
        if res["syntax_error"]:
            err = res["syntax_error"]
            error_detail = f"\n- DETALLE DEL ERROR CRÍTICO: Línea {err['line']}, Columna {err['offset']}: '{err['msg']}'\n  Código erróneo: `{err['text']}`"
            
        issues_str = "\n".join([f"  - {i}" for i in res["issues"]]) if res["issues"] else "  - No se detectaron anti-patrones evidentes."

        report = (
            f"=== ANÁLISIS ESTRUCTURAL PROFUNDO DEL ARCHIVO PYTHON (Inspección AST) ===\n"
            f"- Archivo: {filename} ({res['total_lines']} líneas totales, {res['code_lines']} líneas de código puro, {res['comment_lines']} comentarios)\n"
            f"- Estado de compilación: {status_sintaxis}{error_detail}\n"
            f"- Clases detectadas ({len(res['classes'])}): {classes_str}\n"
            f"- Funciones detectadas ({len(res['functions'])}): {funcs_str}\n"
            f"- Módulos importados: {imports_str}\n"
            f"- Diagnóstico estático y anti-patrones:\n{issues_str}\n"
        )
        return report

    elif ext in ('.csv', '.tsv'):
        res = analyze_csv_content(content)
        headers_str = ", ".join(res["headers"][:10]) or "Sin encabezados detectados"
        types_str = ", ".join([f"{h}: {t}" for h, t in list(res["column_types"].items())[:8]])
        nulls_str = ", ".join([f"{h}: {n} nulos" for h, n in res["null_counts"].items() if n > 0]) or "0 valores nulos"
        
        sample_str = ""
        if res["sample_preview"]:
            sample_str = f"- Muestra inicial de datos:\n  " + "\n  ".join([str(r) for r in res["sample_preview"][:2]])

        report = (
            f"=== ANÁLISIS ESTRUCTURAL DE DATOS TABULARES (CSV/Dataset) ===\n"
            f"- Archivo: {filename} ({res['total_rows']} filas, {res['total_cols']} columnas, Delimitador: '{res.get('delimiter', ',')}')\n"
            f"- Columnas: {headers_str}\n"
            f"- Tipos de datos inferidos: {types_str}\n"
            f"- Valores faltantes / nulos: {nulls_str}\n"
            f"{sample_str}\n"
        )
        return report

    elif ext == '.json':
        res = analyze_json_content(content)
        if not res.get("valid"):
            report = (
                f"=== ANÁLISIS ESTRUCTURAL DE ARCHIVO JSON ===\n"
                f"- Archivo: {filename}\n"
                f"- Estado: [ERROR DE PARSEO JSON]: {res.get('error')}\n"
            )
        else:
            keys_str = ", ".join(res["keys"]) or "Sin claves principales"
            types_str = ", ".join([f"{k}: {t}" for k, t in list(res["types_per_key"].items())[:8]])
            report = (
                f"=== ANÁLISIS ESTRUCTURAL DE ARCHIVO JSON ===\n"
                f"- Archivo: {filename} (Estructura: {res['structure']}, {res['item_count']} elementos)\n"
                f"- Claves de nivel superior: {keys_str}\n"
                f"- Tipos de datos en nodos: {types_str}\n"
            )
        return report

    elif ext in ('.js', '.mjs', '.cjs', '.jsx', '.ts', '.tsx'):
        analisis = javascript_engine.analizar_codigo_js(content, filename)
        reparacion = None
        if not analisis.get("es_valido") or analisis.get("issues"):
            reparacion = javascript_engine.reparar_codigo_js(content)
        return javascript_engine.generar_reporte_tecnico(analisis, reparacion)

    elif ext in ('.html', '.css', '.scss', '.sass', '.sql'):
        res = analyze_general_code(content, ext)
        items = []
        if res.get("functions"):
            items.append(f"Funciones: {', '.join(res['functions'])}")
        if res.get("classes"):
            items.append(f"Clases: {', '.join(res['classes'])}")
        if res.get("tags_count"):
            items.append(f"{res['tags_count']} etiquetas HTML, IDs: {', '.join(res.get('ids_found', []))}")
        if res.get("selectors"):
            items.append(f"Reglas CSS: {', '.join(res.get('selectors', []))}")
        if res.get("statements"):
            items.append(f"Sentencias SQL: {', '.join(res.get('statements', []))}, Tablas: {', '.join(res.get('tables', []))}")
            
        details_str = "; ".join(items) if items else "Sin componentes declarativos principales."
        report = (
            f"=== ANÁLISIS ESTRUCTURAL DE CÓDIGO ({ext.upper()}) ===\n"
            f"- Archivo: {filename} ({res['total_lines']} líneas de código)\n"
            f"- Componentes detectados: {details_str}\n"
        )
        return report

    else:
        res = analyze_log_or_text(content)
        err_str = f"\n- Errores críticos detectados ({len(res['errors'])}):\n  " + "\n  ".join(res["errors"]) if res["errors"] else ""
        warn_str = f"\n- Advertencias detectadas ({len(res['warnings'])}):\n  " + "\n  ".join(res["warnings"]) if res["warnings"] else ""
        
        report = (
            f"=== ANÁLISIS DE TEXTO / LOG / DOCUMENTO ===\n"
            f"- Archivo: {filename} ({res['total_lines']} líneas)\n"
            f"{err_str}"
            f"{warn_str}\n"
        )
        return report


def analyze_multiple_files(files_list: List[Dict[str, Any]]) -> str:
    """
    Ejecuta el protocolo de análisis secuencial 1x1 y comparativa técnica cruzada:
    1. Fase 1: Inspecciona cada archivo individualmente mediante AST o parseo estructural.
    2. Fase 2: Si hay 2 o más archivos, genera una matriz comparativa cruzada de diferencias
       en funciones, clases, líneas, dependencias o esquemas.
    """
    if not files_list:
        return ""
    
    if len(files_list) == 1:
        f = files_list[0]
        return deep_inspect_file(
            f.get("name") or f.get("nombre") or "archivo.txt",
            str(f.get("content") or f.get("contenido") or ""),
            f.get("type") or f.get("tipo") or "text/plain"
        )

    # 1. Inspección 1x1 secuencial
    individual_reports = []
    py_analyses = {}
    csv_analyses = {}
    line_counts = {}

    for idx, f in enumerate(files_list, start=1):
        name = f.get("name") or f.get("nombre") or f"archivo_{idx}.txt"
        content = str(f.get("content") or f.get("contenido") or "")
        mime = f.get("type") or f.get("tipo") or "text/plain"
        ext = os.path.splitext(name)[1].lower()

        rep = deep_inspect_file(name, content, mime)
        individual_reports.append(f"--- [{idx}/{len(files_list)}] INSPECCIÓN INDIVIDUAL: {name} ---\n{rep}")

        lines = content.splitlines()
        line_counts[name] = len(lines)

        if ext == '.py':
            py_analyses[name] = analyze_python_content(content, name)
        elif ext in ('.csv', '.tsv'):
            csv_analyses[name] = analyze_csv_content(content)

    # 2. Matriz Comparativa Técnica Cruzada (si hay 2 o más archivos)
    comparative_sections = []

    # A. Comparativa de volumen
    vol_lines = []
    for name, lc in line_counts.items():
        vol_lines.append(f"  - {name}: {lc} líneas")
    comparative_sections.append(f"1. Comparativa de Volumen y Líneas:\n" + "\n".join(vol_lines))

    # B. Comparativa de scripts Python (si hay 2 o más scripts Python)
    if len(py_analyses) >= 2:
        py_names = list(py_analyses.keys())
        file_a, file_b = py_names[0], py_names[1]
        a_data, b_data = py_analyses[file_a], py_analyses[file_b]

        funcs_a = {fn["name"]: fn for fn in a_data.get("functions", [])}
        funcs_b = {fn["name"]: fn for fn in b_data.get("functions", [])}

        shared_funcs = sorted(list(set(funcs_a.keys()) & set(funcs_b.keys())))
        only_a = sorted(list(set(funcs_a.keys()) - set(funcs_b.keys())))
        only_b = sorted(list(set(funcs_b.keys()) - set(funcs_a.keys())))

        classes_a = set([c["name"] for c in a_data.get("classes", [])])
        classes_b = set([c["name"] for c in b_data.get("classes", [])])
        shared_classes = sorted(list(classes_a & classes_b))
        only_classes_a = sorted(list(classes_a - classes_b))
        only_classes_b = sorted(list(classes_b - classes_a))

        imports_a = set(a_data.get("imports", []))
        imports_b = set(b_data.get("imports", []))
        new_imports_b = sorted(list(imports_b - imports_a))

        delta_lines = line_counts.get(file_b, 0) - line_counts.get(file_a, 0)
        delta_str = f"+{delta_lines}" if delta_lines > 0 else str(delta_lines)

        py_comp = (
            f"2. Matriz Comparativa Python ({file_a} vs {file_b}):\n"
            f"  - Delta de líneas: {delta_str} líneas ({file_a}: {line_counts.get(file_a, 0)} -> {file_b}: {line_counts.get(file_b, 0)})\n"
            f"  - Funciones exclusivas en '{file_a}': {', '.join(only_a) if only_a else 'Ninguna'}\n"
            f"  - Funciones nuevas/exclusivas en '{file_b}': {', '.join(only_b) if only_b else 'Ninguna'}\n"
            f"  - Funciones presentes en ambos: {', '.join(shared_funcs) if shared_funcs else 'Ninguna'}\n"
            f"  - Clases comparadas: Compartidas: {', '.join(shared_classes) or '0'}, Exclusivas {file_a}: {', '.join(only_classes_a) or '0'}, Exclusivas {file_b}: {', '.join(only_classes_b) or '0'}\n"
            f"  - Módulos importados nuevos en '{file_b}': {', '.join(new_imports_b) if new_imports_b else 'Mismos módulos o ninguno nuevo'}"
        )
        comparative_sections.append(py_comp)

    # C. Comparativa de datos tabulares (CSV)
    elif len(csv_analyses) >= 2:
        csv_names = list(csv_analyses.keys())
        csv_a, csv_b = csv_names[0], csv_names[1]
        ca_data, cb_data = csv_analyses[csv_a], csv_analyses[csv_b]

        cols_a = set(ca_data.get("headers", []))
        cols_b = set(cb_data.get("headers", []))
        shared_cols = sorted(list(cols_a & cols_b))
        only_cols_a = sorted(list(cols_a - cols_b))
        only_cols_b = sorted(list(cols_b - cols_a))

        csv_comp = (
            f"2. Matriz Comparativa CSV ({csv_a} vs {csv_b}):\n"
            f"  - Filas: {csv_a} ({ca_data['total_rows']} filas) vs {csv_b} ({cb_data['total_rows']} filas)\n"
            f"  - Columnas compartidas: {', '.join(shared_cols) if shared_cols else 'Ninguna'}\n"
            f"  - Columnas exclusivas en '{csv_a}': {', '.join(only_cols_a) if only_cols_a else 'Ninguna'}\n"
            f"  - Columnas nuevas en '{csv_b}': {', '.join(only_cols_b) if only_cols_b else 'Ninguna'}"
        )
        comparative_sections.append(csv_comp)

    all_individual = "\n\n".join(individual_reports)
    all_comparative = "\n\n".join(comparative_sections)

    full_report = (
        f"=== REPORTE DE ANÁLISIS SECUENCIAL 1X1 Y COMPARATIVA TÉCNICA ({len(files_list)} ARCHIVOS) ===\n\n"
        f"{all_individual}\n\n"
        f"=== MATRIZ COMPARATIVA TÉCNICA CRUZADA ===\n"
        f"{all_comparative}\n"
    )
    return full_report
