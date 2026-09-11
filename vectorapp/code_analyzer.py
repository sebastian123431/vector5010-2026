"""
Motor de Aprendizaje Profundo y Diagnóstico de Código para Vector.
Permite descomprimir archivos ZIP de proyectos, analizar sintaxis y arquitectura con AST,
detectar errores y cuellos de botella, e indexar el conocimiento en la memoria de Vector.
"""

import os
import sys
from pathlib import Path
import zipfile
import ast
import json
import time
import shutil
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict
from enum import Enum
from dataclasses import dataclass, field

from .local_engine import VectorLocalEngine
from .neural_network import semantic_network
from .security.exceptions import ZipBombViolation, PathTraversalViolation
from .javascript_engine import javascript_engine

logger = logging.getLogger(__name__)

# Límites de seguridad configurables para prevención de ZIP bombs
MAX_ZIP_FILES = 5000
MAX_ZIP_COMPRESSED_SIZE = 100 * 1024 * 1024      # 100 MB de archivo zip
MAX_ZIP_UNCOMPRESSED_SIZE = 500 * 1024 * 1024    # 500 MB descomprimidos en total
MAX_SINGLE_FILE_SIZE = 20 * 1024 * 1024          # 20 MB por archivo individual
MAX_DIRECTORY_DEPTH = 15                          # Máxima profundidad de carpetas
MAX_COMPRESSION_RATIO = 100.0                     # Ratio de compresión sospechoso
CHUNK_SIZE = 64 * 1024                           # 64 KB para lectura por chunks

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


class ProposalType(str, Enum):
    """Tipos de propuestas de mejora de código."""
    SECURITY = "security"
    PERFORMANCE = "performance"
    CODE_STYLE = "code_style"
    RELIABILITY = "reliability"
    DEAD_CODE = "dead_code"


@dataclass
class ImprovementProposal:
    """Propuesta estructurada de refactorización o mejora."""
    proposal_id: str
    target_file: str
    target_symbol: str
    issue_type: ProposalType
    description: str
    diff_preview: str = ""
    status: str = "pending_review"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "target_file": self.target_file,
            "target_symbol": self.target_symbol,
            "issue_type": self.issue_type.value,
            "description": self.description,
            "diff_preview": self.diff_preview,
            "status": self.status,
            "created_at": self.created_at
        }


class CallGraph:
    """
    Grafo de llamadas y dependencias de código entre funciones y módulos.
    Calcula callers, callees y realiza análisis de impacto.
    """
    def __init__(self):
        self.callers: Dict[str, Set[str]] = defaultdict(set)
        self.callees: Dict[str, Set[str]] = defaultdict(set)
        self.module_deps: Dict[str, Set[str]] = defaultdict(set)
        self.symbol_files: Dict[str, str] = {}

    def add_call(self, caller: str, callee: str, file_path: str = ""):
        self.callees[caller].add(callee)
        self.callers[callee].add(caller)
        if file_path:
            self.symbol_files[caller] = file_path
            if callee not in self.symbol_files:
                self.symbol_files[callee] = file_path

    def add_dependency(self, module: str, imported_module: str):
        self.module_deps[module].add(imported_module)

    def impact_analysis(self, symbol_or_module: str) -> Dict[str, Any]:
        """
        Calcula el radio de impacto de modificar un símbolo o módulo dado.
        """
        impacted_callers = set()
        to_visit = [symbol_or_module]
        visited = set()

        while to_visit:
            curr = to_visit.pop(0)
            if curr in visited:
                continue
            visited.add(curr)
            direct_callers = self.callers.get(curr, set())
            for c in direct_callers:
                impacted_callers.add(c)
                if c not in visited:
                    to_visit.append(c)

        impacted_files = {self.symbol_files.get(s, "") for s in impacted_callers if self.symbol_files.get(s)}

        return {
            "target": symbol_or_module,
            "direct_callers": sorted(list(self.callers.get(symbol_or_module, set()))),
            "total_impacted_callers": sorted(list(impacted_callers)),
            "impacted_files": sorted(list(impacted_files)),
            "impact_level": "high" if len(impacted_callers) > 5 else ("medium" if impacted_callers else "low")
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
        self.call_graph = CallGraph()

    def extract_zip(self, zip_source, project_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Descomprime de forma segura un archivo ZIP protegiendo contra Zip-Slip y Zip-Bombs.
        Aplica cuotas de archivos, tamaño acumulado, profundidad y ratio de compresión.
        Realiza lectura en chunks y rollback automático en caso de violación.
        """
        if not project_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            project_name = f"proyecto_{timestamp}"

        target_dir = os.path.join(self.workspace_dir, project_name)
        os.makedirs(target_dir, exist_ok=True)
        resolved_target_dir = Path(target_dir).resolve()

        # 0. Validación de tamaño comprimido previo si zip_source es una ruta en disco
        if isinstance(zip_source, (str, os.PathLike)) and os.path.exists(zip_source):
            comp_sz = os.path.getsize(zip_source)
            if comp_sz > MAX_ZIP_COMPRESSED_SIZE:
                raise ZipBombViolation(
                    f"El archivo ZIP ({comp_sz} bytes) excede la cuota de compresión ({MAX_ZIP_COMPRESSED_SIZE} bytes)."
                )

        extracted_files = []
        total_uncompressed_size = 0

        try:
            with zipfile.ZipFile(zip_source, 'r') as zf:
                members = zf.infolist()

                # 1. Validación de cantidad máxima de archivos y tamaño comprimido acumulado
                if len(members) > MAX_ZIP_FILES:
                    raise ZipBombViolation(
                        f"El archivo ZIP contiene {len(members)} entradas, excediendo el límite de {MAX_ZIP_FILES}."
                    )

                total_comp_decl = sum(m.compress_size for m in members)
                if total_comp_decl > MAX_ZIP_COMPRESSED_SIZE:
                    raise ZipBombViolation(
                        f"El tamaño comprimido declarado ({total_comp_decl} bytes) excede el límite de {MAX_ZIP_COMPRESSED_SIZE} bytes."
                    )

                for member in members:
                    filename = member.filename

                    # 2. Protección canónica Zip-Slip con Path.resolve e is_relative_to
                    candidate_path = Path(target_dir, filename).resolve()
                    if not candidate_path.is_relative_to(resolved_target_dir):
                        logger.warning(f"[ZipSecurity] Zip-Slip bloqueado para: {filename}")
                        continue
                    target_path = str(candidate_path)

                    # 3. Validación de profundidad de directorios
                    parts = filename.replace('\\', '/').strip('/').split('/')
                    if len(parts) > MAX_DIRECTORY_DEPTH:
                        raise ZipBombViolation(
                            f"Profundidad de directorio excesiva ({len(parts)} > {MAX_DIRECTORY_DEPTH}) en: {filename}"
                        )

                    # Ignorar carpetas y archivos binarios pesados
                    if any(p in IGNORED_DIRS for p in parts):
                        continue
                    ext = os.path.splitext(filename)[1].lower()
                    if ext in IGNORED_EXTENSIONS:
                        continue

                    # 4. Verificación de tamaño individual declarado en cabecera
                    if member.file_size > MAX_SINGLE_FILE_SIZE:
                        raise ZipBombViolation(
                            f"El archivo '{filename}' declara {member.file_size} bytes, excediendo el límite individual de {MAX_SINGLE_FILE_SIZE} bytes."
                        )

                    # 5. Verificación de ratio de compresión (detección temprana de Zip Bomb)
                    if member.compress_size > 0 and member.file_size > 1024 * 1024:
                        ratio = member.file_size / member.compress_size
                        if ratio > MAX_COMPRESSION_RATIO:
                            raise ZipBombViolation(
                                f"Ratio de compresión sospechoso ({ratio:.1f}x > {MAX_COMPRESSION_RATIO}x) en '{filename}'."
                            )

                    if member.is_dir():
                        os.makedirs(target_path, exist_ok=True)
                    else:
                        os.makedirs(os.path.dirname(target_path), exist_ok=True)
                        bytes_this_file = 0
                        with zf.open(member) as source, open(target_path, "wb") as target:
                            while True:
                                chunk = source.read(CHUNK_SIZE)
                                if not chunk:
                                    break
                                bytes_this_file += len(chunk)
                                total_uncompressed_size += len(chunk)

                                if bytes_this_file > MAX_SINGLE_FILE_SIZE:
                                    raise ZipBombViolation(
                                        f"El archivo '{filename}' superó el tamaño máximo individual ({MAX_SINGLE_FILE_SIZE} bytes) durante la extracción."
                                    )

                                if total_uncompressed_size > MAX_ZIP_UNCOMPRESSED_SIZE:
                                    raise ZipBombViolation(
                                        f"El tamaño total descomprimido superó la cuota de {MAX_ZIP_UNCOMPRESSED_SIZE // (1024*1024)} MB."
                                    )

                                target.write(chunk)

                        extracted_files.append(target_path)

            return {
                "project_name": project_name,
                "project_dir": target_dir,
                "extracted_count": len(extracted_files),
                "total_uncompressed_bytes": total_uncompressed_size,
                "files": extracted_files
            }

        except Exception as e:
            # Rollback: Limpiar residuos parciales en caso de violación o error
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir, ignore_errors=True)
            logger.error(f"[ZipSecurity] Error durante la extracción de '{project_name}': {e}")
            raise

    def diagnose_project(self, project_dir: str) -> Dict[str, Any]:
        """
        Ejecuta un diagnóstico profundo sobre el árbol de archivos extraído:
        - Validación estática AST en Python (errores de sintaxis exactos).
        - Extracción y análisis de código JavaScript y TypeScript con Tree-sitter.
        - Mapeo de llamadas y dependencias mediante CallGraph.
        - Generación de propuestas estructuradas de mejora (ImprovementProposal).
        - Detección de patrones de riesgo (except vacíos, eval/exec).
        - Conteo de líneas de código y estadísticas por lenguaje.
        """
        self.call_graph = CallGraph()
        resumen = {
            "total_files": 0,
            "total_lines": 0,
            "languages": {},
            "syntax_errors": [],
            "warnings": [],
            "functions": [],
            "classes": [],
            "imports": set(),
            "structure": [],
            "proposals": [],
            "call_graph_summary": {}
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
                elif ext in ('.js', '.ts', '.jsx', '.tsx'):
                    js_res = javascript_engine.analyze_javascript(content, filename=rel_path, mode="auto")
                    for fn in js_res.get("funciones", []):
                        resumen["functions"].append({
                            "name": fn["nombre"],
                            "file": rel_path,
                            "line": fn.get("linea", 1),
                            "lang": "JavaScript" if ext in ('.js', '.jsx') else "TypeScript"
                        })
                    for cls in js_res.get("clases", []):
                        resumen["classes"].append({
                            "name": cls["nombre"],
                            "file": rel_path,
                            "line": cls.get("linea", 1),
                            "lang": "JavaScript" if ext in ('.js', '.jsx') else "TypeScript"
                        })
                    for imp in js_res.get("imports", []):
                        clean_imp = imp.split()[0].strip("'\"")
                        resumen["imports"].add(clean_imp)
                        self.call_graph.add_dependency(rel_path, clean_imp)
                    for issue in js_res.get("issues", []):
                        resumen["warnings"].append({
                            "file": rel_path,
                            "archivo": rel_path,
                            "line": 1,
                            "type": "Calidad/Seguridad JS",
                            "message": issue,
                            "mensaje": issue
                        })
                    if not js_res.get("es_valido") and js_res.get("error_sintaxis"):
                        err = js_res["error_sintaxis"]
                        resumen["syntax_errors"].append({
                            "file": rel_path,
                            "archivo": rel_path,
                            "line": err.get("linea", 1),
                            "col": err.get("columna", 1),
                            "type": "SyntaxError JS",
                            "message": err.get("mensaje", "Error sintáctico JS")
                        })
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
        resumen["call_graph_summary"] = {
            "total_callers": len(self.call_graph.callers),
            "total_callees": len(self.call_graph.callees),
            "total_dependencies": len(self.call_graph.module_deps)
        }
        resumen["proposals"] = self.generate_proposals(resumen)
        return resumen

    def impact_analysis(self, symbol_or_module: str) -> Dict[str, Any]:
        """Calcula el impacto de modificar un símbolo o módulo."""
        return self.call_graph.impact_analysis(symbol_or_module)

    def generate_proposals(self, diagnosis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Genera propuestas de mejora y refactorización accionables."""
        proposals = []
        prop_idx = 1

        for w in diagnosis.get("warnings", []):
            w_type = w.get("type", "")
            f_path = w.get("file", "")
            line = w.get("line", 1)

            if "Except" in w_type:
                proposals.append(ImprovementProposal(
                    proposal_id=f"PROP-{prop_idx:03d}",
                    target_file=f_path,
                    target_symbol=f"L{line}",
                    issue_type=ProposalType.RELIABILITY,
                    description=f"Especificar tipo de excepción en {f_path}:{line} para evitar captura silenciosa indiscriminada.",
                    diff_preview=f"- except:\n+ except Exception as e:\n+     logger.error(f'Error: {{e}}')",
                ).to_dict())
                prop_idx += 1

            elif "Seguridad" in w_type or "eval" in w.get("message", "").lower():
                proposals.append(ImprovementProposal(
                    proposal_id=f"PROP-{prop_idx:03d}",
                    target_file=f_path,
                    target_symbol=f"L{line}",
                    issue_type=ProposalType.SECURITY,
                    description=f"Reemplazar ejecución de código dinámico en {f_path}:{line} por deserialización estructurada o AST seguro.",
                    diff_preview=f"- eval(data)\n+ json.loads(data)",
                ).to_dict())
                prop_idx += 1

        return proposals

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
                # Mapear llamadas dentro de esta función para el CallGraph
                for subnode in ast.walk(node):
                    if isinstance(subnode, ast.Call):
                        callee_name = ""
                        if isinstance(subnode.func, ast.Name):
                            callee_name = subnode.func.id
                        elif isinstance(subnode.func, ast.Attribute):
                            callee_name = subnode.func.attr
                        if callee_name:
                            self.call_graph.add_call(node.name, callee_name, file_path=rel_path)
            # Importaciones
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    mod = alias.name.split('.')[0]
                    resumen["imports"].add(mod)
                    self.call_graph.add_dependency(rel_path, mod)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    mod = node.module.split('.')[0]
                    resumen["imports"].add(mod)
                    self.call_graph.add_dependency(rel_path, mod)
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


# Alias de compatibilidad arquitectónica
CodeAnalyzer = ProjectCodeAnalyzer

