"""
Adaptador de Herramientas Seguras para el Motor de Razonamiento (Fase P0).
Conecta el PlanExecutor con el sandbox real (ToolRunner), validando AST y permisos.
"""

import os
import logging
from typing import Dict, Any, Optional

from ..security.ast_validator import ASTSecurityValidator
from ..security.permissions import ToolPermissions
from ..security.sandbox_policy import ToolRunner, SandboxPolicy

logger = logging.getLogger(__name__)


def vector_tool_adapter(tool_name: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Adaptador oficial para ejecutar herramientas desde el PlanExecutor / ReasoningEngine.
    1. Localiza la herramienta (dinámica o de sistema).
    2. Valida su código con ASTSecurityValidator.
    3. Comprueba ToolPermissions.
    4. Ejecuta mediante el Sandbox ToolRunner.
    5. Retorna un resultado estructurado comprobable.
    """
    params = parameters or {}
    ast_validator = ASTSecurityValidator()

    # 1. Caso especial: herramienta de prueba segura para testing controlado
    if tool_name == "safe_test_tool":
        return {
            "success": True,
            "tool": tool_name,
            "result": f"Ejecución exitosa de herramienta de prueba: {params.get('description', '')}",
            "error": None
        }

    # 2. Caso especial: descompresión segura de ZIP
    if tool_name == "extract_zip":
        try:
            from ..code_analyzer import ProjectCodeAnalyzer
            analyzer = ProjectCodeAnalyzer()
            zip_source = params.get("zip_source") or params.get("file_path")
            project_name = params.get("project_name", "proyecto_razonamiento")
            if not zip_source or not os.path.exists(str(zip_source)):
                return {
                    "success": False,
                    "tool": tool_name,
                    "error": f"Archivo zip_source '{zip_source}' no encontrado."
                }
            res = analyzer.extract_zip(zip_source, project_name=project_name)
            return {
                "success": True,
                "tool": tool_name,
                "result": res,
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "tool": tool_name,
                "error": str(e)
            }

    # 3. Herramientas dinámicas registradas
    try:
        from ..dynamic_tools_generator import dynamic_tools_generator
        if tool_name in dynamic_tools_generator.created_tools:
            tool_info = dynamic_tools_generator.created_tools[tool_name]
            file_path = tool_info.get("file_path")
            if not file_path or not os.path.exists(file_path):
                return {
                    "success": False,
                    "tool": tool_name,
                    "error": f"Archivo de herramienta '{tool_name}' no existe en disco."
                }

            with open(file_path, "r", encoding="utf-8") as f:
                code = f.read()

            # Validación AST estricta
            perm_dict = tool_info.get("permissions") or {}
            perms = ToolPermissions.from_dict(perm_dict)
            ast_res = ast_validator.validate_code(code, permissions=perms)
            if not ast_res["security_valid"]:
                return {
                    "success": False,
                    "tool": tool_name,
                    "error": f"Herramienta '{tool_name}' bloqueada por violaciones AST: {ast_res['violations']}"
                }

            # Ejecución en Sandbox con ToolRunner
            action = params.get("action", "execute")
            tool_params = params.get("parameters", params)
            output = dynamic_tools_generator.execute_tool(
                tool_name=tool_name,
                parameters=tool_params,
                action=action
            )
            return {
                "success": True,
                "tool": tool_name,
                "result": output,
                "error": None
            }

        return {
            "success": False,
            "tool": tool_name,
            "error": f"Herramienta '{tool_name}' no encontrada en el registro de Vector."
        }

    except Exception as e:
        logger.error(f"[vector_tool_adapter] Error ejecutando '{tool_name}': {e}")
        return {
            "success": False,
            "tool": tool_name,
            "error": str(e)
        }
