"""
Política de confinamiento de rutas (Path Policy) para VECTOR 2026.
Garantiza que toda operación de archivos de herramientas dinámicas permanezca
estrictamente confinada dentro del workspace autorizado (previene Path Traversal).
"""

import os
import re
from pathlib import Path
from typing import Union, Optional
from .exceptions import PathTraversalViolation

# Directorio base del workspace aislado de herramientas
DEFAULT_TOOL_WORKSPACE = os.path.abspath(
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "tool_workspace")
)

class PathPolicy:
    """
    Controlador de acceso a sistema de archivos con confinamiento estricto.
    """
    def __init__(self, workspace_dir: Optional[str] = None):
        self.workspace_dir = Path(workspace_dir or DEFAULT_TOOL_WORKSPACE).resolve()
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

    def resolve_safe_path(self, user_path: Union[str, Path], allow_nonexistent: bool = True) -> Path:
        """
        Resuelve canónicamente user_path y verifica que resida dentro del workspace autorizado.
        Si la ruta intenta escapar o contiene patrones maliciosos, lanza PathTraversalViolation.
        """
        if not user_path:
            raise PathTraversalViolation("La ruta de archivo no puede estar vacía.")

        str_path = str(user_path).strip()
        
        # Detección de caracteres nulos (Null byte injection)
        if "\0" in str_path:
            raise PathTraversalViolation("Ruta inválida: detección de byte nulo.")

        # Si se pasa una ruta relativa o un nombre simple, se ancla al workspace
        p = Path(str_path)
        if not p.is_absolute():
            candidate = (self.workspace_dir / p).resolve()
        else:
            candidate = p.resolve()

        # Validación estricta de pertenencia al workspace
        try:
            is_inside = candidate.is_relative_to(self.workspace_dir)
        except AttributeError:
            # Fallback para versiones antiguas de Python si aplicara
            try:
                candidate.relative_to(self.workspace_dir)
                is_inside = True
            except ValueError:
                is_inside = False

        if not is_inside:
            raise PathTraversalViolation(
                f"Acceso denegado: La ruta '{str_path}' escapa del workspace autorizado '{self.workspace_dir}'."
            )

        if not allow_nonexistent and not candidate.exists():
            raise FileNotFoundError(f"El archivo '{candidate}' no existe dentro del workspace.")

        return candidate

    def is_safe_path(self, user_path: Union[str, Path]) -> bool:
        """Verifica de forma booleana si una ruta es segura sin lanzar excepciones."""
        try:
            self.resolve_safe_path(user_path)
            return True
        except Exception:
            return False

    @staticmethod
    def sanitize_tool_name(tool_name: str) -> str:
        """
        Sanitiza el nombre de un archivo de herramienta para impedir secuencias relativas
        o caracteres especiales del sistema operativo.
        """
        if not tool_name or not isinstance(tool_name, str):
            raise PathTraversalViolation("Nombre de herramienta inválido o vacío.")

        clean_name = tool_name.strip()
        # Permitir solo identificadores alfanuméricos seguros y guiones bajos
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", clean_name):
            raise PathTraversalViolation(
                f"Nombre de herramienta inválido: '{tool_name}'. Debe coincidir con '^[a-zA-Z_][a-zA-Z0-9_]*$'."
            )

        return clean_name
