"""
Excepciones de seguridad especializadas para VECTOR 2026.
"""

class VectorSecurityError(Exception):
    """Excepción base para violaciones de seguridad en Vector."""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

class ASTSecurityViolation(VectorSecurityError):
    """Lanzada cuando el validador AST detecta código prohibido o peligroso."""
    pass

class PathTraversalViolation(VectorSecurityError):
    """Lanzada cuando una operación de archivo intenta escapar del workspace autorizado."""
    pass

class ToolPermissionViolation(VectorSecurityError):
    """Lanzada cuando una herramienta intenta realizar acciones que exceden sus permisos."""
    pass

class ZipBombViolation(VectorSecurityError):
    """Lanzada cuando un archivo ZIP excede cuotas de seguridad o ratios sospechosos."""
    pass

class ResourceLimitExceeded(VectorSecurityError):
    """Lanzada cuando la ejecución de una herramienta excede límites de tiempo o memoria/salida."""
    pass

class ToolExecutionError(VectorSecurityError):
    """Lanzada cuando ocurre un error irrecuperable en el sandbox de ejecución."""
    pass
