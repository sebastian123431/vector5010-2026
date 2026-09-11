"""
Módulo de seguridad de VECTOR 2026.
Proporciona validación AST, sandboxing, políticas de ruta, permisos de herramientas y manejo de límites.
"""

from .exceptions import (
    VectorSecurityError,
    ASTSecurityViolation,
    PathTraversalViolation,
    ToolPermissionViolation,
    ZipBombViolation,
    ResourceLimitExceeded,
    ToolExecutionError,
)
from .permissions import ToolPermissions
from .path_policy import PathPolicy, DEFAULT_TOOL_WORKSPACE
from .ast_validator import ASTSecurityValidator
from .sandbox_policy import (
    SandboxPolicy,
    ToolRunner,
    ToolExecutionResult,
    TOOL_TIMEOUT_SIMPLE,
    TOOL_TIMEOUT_COMPLEX,
    TOOL_MAX_OUTPUT_BYTES,
)
from .user_profile import (
    UserProfile,
    UserRole,
    resolve_user_profile,
    creator_only,
    dangerous_endpoint,
    state_change_endpoint,
    read_only_endpoint,
)

__all__ = [
    "VectorSecurityError",
    "ASTSecurityViolation",
    "PathTraversalViolation",
    "ToolPermissionViolation",
    "ZipBombViolation",
    "ResourceLimitExceeded",
    "ToolExecutionError",
    "ToolPermissions",
    "PathPolicy",
    "DEFAULT_TOOL_WORKSPACE",
    "ASTSecurityValidator",
    "SandboxPolicy",
    "ToolRunner",
    "ToolExecutionResult",
    "TOOL_TIMEOUT_SIMPLE",
    "TOOL_TIMEOUT_COMPLEX",
    "TOOL_MAX_OUTPUT_BYTES",
    "UserProfile",
    "UserRole",
    "resolve_user_profile",
    "creator_only",
    "dangerous_endpoint",
    "state_change_endpoint",
    "read_only_endpoint",
]

