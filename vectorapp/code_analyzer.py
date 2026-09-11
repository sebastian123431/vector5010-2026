"""
Motor de Aprendizaje Profundo y Diagnóstico de Código para Vector.
Permite descomprimir archivos ZIP de proyectos, analizar sintaxis y arquitectura con AST,
detectar errores y cuellos de botella, e indexar el conocimiento en la memoria de Vector.
"""

import os
import sys
import zipfile
import ast
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

from .local_engine import VectorLocalEngine
from .neural_network import semantic_network

# Extensiones de código analizadas
CODE_EXTENSIONS = {
    '.py': 'Python',
    '.js': 'JavaScript',
    '.ts': 'TypeScript',
    '.html': 'HTML',
    '.css': 'CSS',
    '.json': 'JSON',
    '.sql': 'SQL',
    '.md': 'Markdown',
    '.txt': 'Texto Plano',
}

# Carpetas y archivos a ignorar para análisis limpio
IGNORED_DIRS = {
    '__pycache__', '.git', '.svn', '.hg', 'venv', '.venv', 'env',
    'node_modules', '.idea', '.vscode', 'dist', 'build', '.pytest_cache',
    '.mypy_cache', 'migrations'
}

IGNORED_EXTENSIONS = {
    '.pyc', '.pyo', '.exe', '.dll', '.so', '.dylib', '.png', '.jpg',
    '.jpeg', '.gif', '.ico', '.pdf', '.zip', '.tar', '.gz', '.db', '.sqlite3'
}


class ProjectCodeAnalyzer:
    """
    Analizador profundo de código fuente capaz de descomprimir proyectos ZIP,
    auditar calidad con AST, mapear relaciones e indexar la base de código.
    """

    def __init__(self, workspace_dir: Optional[str] = None):
        if not workspace_dir:
            base_app = os.path.dirname(os.path.abspath(__file__))
            workspace_dir = os.path.join(base_app, "workspace", "proyectos")
        self.workspace_dir = workspace_dir
        os.makedirs(self.workspace_dir, exist_ok=True)

    def extract_zip(self, zip_source, project_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Descomprime de forma segura un archivo ZIP protegiendo contra Zip-Slip.
        Retorna la ruta del proyecto extraído y metadatos básicos.
        """
        if not project_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            project_name = f"proyecto_{timestamp}"

        target_dir = os.path.join(self.workspace_dir, project_name)
        os.makedirs(target_dir, exist_ok=True)

        extracted_files = []
        
        with zipfile.ZipFile(zip_source, 'r') as zf:
            for member in zf.infolist():
                filename = member.filename
                
                # Protección estricta Zip Slip (evitar path traversal)
                target_path = os.path.abspath(os.path.join(target_dir, filename))
                if not target_path.startswith(os.path.abspath(target_dir)):
                    continue # Saltar archivo sospechoso fuera del target

                # Ignorar carpetas y archivos binarios pesados
                parts = filename.replace('\\', '/').split('/')
                if any(p in IGNORED_DIRS for p in parts):
                    continue
                ext = os.path.splitext(filename)[1].lower()
                if ext in IGNORED_EXTENSIONS:
                    continue

                if member.is_dir():
                    os.makedirs(target_path, exist_ok=True)
                else:
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)
                    with zf.open(member) as source, open(target_path, "wb") as target:
                        target.write(source.read())
                    extracted_files.append(target_path)

        return {
            "project_name": project_name,
            "project_dir": target_dir,
            "extracted_count": len(extracted_files),
            "files": extracted_files
        }

    def diagnose_project(self, project_dir: str) -> Dict[str, Any]:
        """
        Ejecuta un diagnóstico profundo sobre el árbol de archivos extraído:
        - Validación estática AST en Python (errores de sintaxis exactos).
        - Extracción de clases, funciones y llamadas a dependencias.
        - Detección de patrones de riesgo (except vacíos, eval/exec).
        - Conteo de líneas de código y estadísticas por lenguaje.
        """
        resumen = {
            "total_files": 0,
            "total_lines": 0,
            "languages": {},
            "syntax_errors": [],
            "warnings": [],
            "functions": [],
            "classes": [],
            "imports": set(),
            "structure": []
        }

        for root, dirs, files in os.walk(project_dir):
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
            rel_dir = os.path.relpath(root, project_dir)
            if rel_dir == '.':
                rel_dir = ''

            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in IGNORED_EXTENSIONS:
                    continue

                full_path = os.path.join(root, file)
                rel_path = os.path.join(rel_dir, file).replace('\\', '/')
                lang = CODE_EXTENSIONS.get(ext, "Otro")

                resumen["total_files"] += 1
                resumen["languages"][lang] = resumen["languages"].get(lang, 0) + 1

                try:
                    with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                        content = f.read()
                except Exception as e:
                    resumen["warnings"].append({
                        "file": rel_path,
                        "line": 1,
                        "type": "Lectura",
                        "message": f"No se pudo leer el archivo: {e}"
                    })
                    continue

                lines = content.splitlines()
                resumen["total_lines"] += len(lines)
                resumen["structure"].append({"file": rel_path, "lines": len(lines), "lang": lang})

                # Análisis específico para archivos Python
                if ext == '.py':
                    self._analyze_python_ast(rel_path, content, resumen)
                elif ext == '.json':
                    try:
                        json.loads(content)
                    except Exception as je:
                        resumen["syntax_errors"].append({
                            "file": rel_path,
                            "archivo": rel_path,
                            "line": getattr(je, 'lineno', 1),
                            "linea": getattr(je, 'lineno', 1),
                            "type": "Error de Sintaxis JSON",
                            "tipo": "Error de Sintaxis JSON",
                            "message": str(je),
                            "mensaje": str(je)
                        })

        resumen["imports"] = sorted(list(resumen["imports"]))
        return resumen

    def _analyze_python_ast(self, rel_path: str, code: str, resumen: Dict[str, Any]):
        """Analiza la estructura sintáctica de un script Python usando AST."""
        try:
            tree = ast.parse(code, filename=rel_path)
        except SyntaxError as se:
            resumen["syntax_errors"].append({
                "file": rel_path,
                "archivo": rel_path,
                "line": se.lineno or 1,
                "linea": se.lineno or 1,
                "col": se.offset or 1,
                "type": "SyntaxError",
                "tipo": "SyntaxError",
                "message": se.msg,
                "mensaje": se.msg,
                "snippet": se.text.strip() if se.text else ""
            })
            return
        except Exception as e:
            resumen["syntax_errors"].append({
                "file": rel_path,
                "archivo": rel_path,
                "line": 1,
                "linea": 1,
                "col": 1,
                "type": "Error Parse AST",
                "tipo": "Error Parse AST",
                "message": str(e),
                "mensaje": str(e)
            })
            return

        # Recorrer nodos AST
        for node in ast.walk(tree):
            # Clases
            if isinstance(node, ast.ClassDef):
                resumen["classes"].append({
                    "name": node.name,
                    "file": rel_path,
                    "line": node.lineno
                })
            # Funciones
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                resumen["functions"].append({
                    "name": node.name,
                    "file": rel_path,
                    "line": node.lineno,
                    "is_async": isinstance(node, ast.AsyncFunctionDef)
                })
            # Importaciones
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    resumen["imports"].add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    resumen["imports"].add(node.module.split('.')[0])
            # Advertencias de calidad: except vacíos
            elif isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    resumen["warnings"].append({
                        "file": rel_path,
                        "archivo": rel_path,
                        "line": node.lineno,
                        "linea": node.lineno,
                        "type": "Bloque Except Vacío",
                        "tipo": "Bloque Except Vacío",
                        "message": "Captura silenciosa de excepciones generales ('except:') que puede ocultar fallos graves.",
                        "mensaje": "Captura silenciosa de excepciones generales ('except:') que puede ocultar fallos graves."
                    })
            # Advertencias de seguridad: llamadas a eval() o exec()
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in ['eval', 'exec']:
                    resumen["warnings"].append({
                        "file": rel_path,
                        "archivo": rel_path,
                        "line": node.lineno,
                        "linea": node.lineno,
                        "type": "Riesgo de Seguridad",
                        "tipo": "Riesgo de Seguridad",
                        "message": f"Uso potencialmente inseguro de {node.func.id}() para ejecutar código dinámico.",
                        "mensaje": f"Uso potencialmente inseguro de {node.func.id}() para ejecutar código dinámico."
                    })

    def index_semantics(self, project_name: str, diagnosis: Dict[str, Any]):
        """
        Indexa la estructura y conceptos del proyecto en la red sináptica semántica
        de Vector para que pueda razonar sobre él en consultas posteriores.
        """
        try:
            # 1. Registrar concepto central del proyecto en el grafo sináptico
            total_f = diagnosis["total_files"]
            total_l = diagnosis["total_lines"]
            langs = ", ".join(f"{k} ({v})" for k, v in diagnosis["languages"].items())
            
            summary_concept = f"PROYECTO '{project_name}': {total_f} archivos, {total_l} líneas. Lenguajes: {langs}."
            semantic_network.add_memory(summary_concept, "code_project")

            # 2. Registrar funciones y clases clave
            for c in diagnosis["classes"][:10]:
                semantic_network.add_memory(
                    f"Clase '{c['name']}' definida en {c['file']}:{c['line']}",
                    "code_class"
                )
            for fn in diagnosis["functions"][:15]:
                semantic_network.add_memory(
                    f"Función '{fn['name']}' definida en {fn['file']}:{fn['line']}",
                    "code_function"
                )

            # 3. Registrar errores detectados si los hay
            for err in diagnosis["syntax_errors"][:5]:
                semantic_network.add_memory(
                    f"FALLO_SINTAXIS en {err['file']}:{err['line']} -> {err['message']}",
                    "code_error"
                )
        except Exception as e:
            print(f"[ProjectCodeAnalyzer] Error en indexación semántica: {e}")

    def generate_markdown_report(self, project_name: str, diagnosis: Dict[str, Any]) -> str:
        """Construye un informe técnico en formato Markdown con el diagnóstico completo."""
        langs_str = ", ".join(f"{k} ({v})" for k, v in diagnosis["languages"].items()) or "No detectado"
        err_count = len(diagnosis["syntax_errors"])
        warn_count = len(diagnosis["warnings"])
        status_badge = "🟢 CÓDIGO ESTABLE (Sin errores sintácticos)" if err_count == 0 else f"🔴 CRÍTICO ({err_count} errores de sintaxis detectados)"

        md = []
        md.append(f"## 📦 Diagnóstico Técnico Profundo: `{project_name}`\n")
        md.append(f"**Estado General:** {status_badge}\n")
        md.append(f"- **Archivos analizados:** {diagnosis['total_files']}")
        md.append(f"- **Líneas de código totales:** {diagnosis['total_lines']}")
        md.append(f"- **Lenguajes:** {langs_str}")
        md.append(f"- **Módulos / Librerías requeridas:** {', '.join(diagnosis['imports'][:10]) or 'Ninguna externa'}")
        md.append(f"- **Estructura:** {len(diagnosis['classes'])} clases y {len(diagnosis['functions'])} funciones mapeadas.\n")

        # Sección de Errores de Sintaxis
        if err_count > 0:
            md.append("### 🚨 Errores Críticos de Sintaxis Detectados:\n")
            for i, err in enumerate(diagnosis["syntax_errors"], 1):
                snippet = f"\n  > Código: `{err['snippet']}`" if err.get('snippet') else ""
                md.append(f"{i}. **{err['file']}** (Línea {err['line']}, Col {err.get('col', 1)}):")
                md.append(f"   - **{err['type']}**: `{err['message']}`{snippet}\n")
        else:
            md.append("### ✅ Validación de Sintaxis: Aprobada\n")
            md.append("Todos los archivos Python y JSON cumplen con la sintaxis del lenguaje sin errores de compilación AST.\n")

        # Sección de Advertencias
        if warn_count > 0:
            md.append("### ⚠️ Advertencias de Calidad y Buenas Prácticas:\n")
            for i, w in enumerate(diagnosis["warnings"][:8], 1):
                md.append(f"{i}. **{w['file']}** (Línea {w['line']}) - *{w['type']}*: {w['message']}")
            md.append("")

        # Funciones y Clases Principales
        if diagnosis["classes"] or diagnosis["functions"]:
            md.append("### 🧠 Mapeo de Arquitectura y Componentes Clave:\n")
            if diagnosis["classes"]:
                cl_names = ", ".join(f"`{c['name']}` ({c['file']})" for c in diagnosis["classes"][:6])
                md.append(f"- **Clases Principales:** {cl_names}")
            if diagnosis["functions"]:
                fn_names = ", ".join(f"`{f['name']}()` ({f['file']})" for f in diagnosis["functions"][:8])
                md.append(f"- **Funciones Principales:** {fn_names}")
            md.append("")

        md.append("---")
        md.append("💡 **Modo Copiloto Activo:** El proyecto ha sido asimilado en mi red sináptica. Puedes hacerme preguntas directamente sobre cualquiera de estos archivos, pedirme que repare los errores detectados o refactorizar cualquier función.")

        return "\n".join(md)
