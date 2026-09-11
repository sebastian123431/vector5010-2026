"""
Módulo de seguridad de VECTOR 2026.
Proporciona validación AST, sandboxing, políticas de ruta, permisos de herramientas,
manejo de límites y políticas de acción imparciales (sin autorización basada en personas).
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
from .action_policy import (
    require_action_confirmation,
    dangerous_endpoint,
    high_impact_action,
    state_change_endpoint,
    read_only_endpoint,
    pending_action_manager,
    PendingActionManager,
    canonicalize_action_parameters,
)
from .user_profile import (
    UserProfile,
    resolve_user_profile,
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
    "require_action_confirmation",
    "dangerous_endpoint",
    "high_impact_action",
    "state_change_endpoint",
    "read_only_endpoint",
    "pending_action_manager",
    "PendingActionManager",
    "canonicalize_action_parameters",
    "UserProfile",
    "resolve_user_profile",
]
