"""
Gestión centralizada de roles, perfiles de usuario y permisos de acceso para Vector 2026.
Elimina comprobaciones dispersas (hardcoded) y garantiza control de acceso uniforme.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Any, Dict, List
from functools import wraps
from rest_framework.response import Response


class UserRole(str, Enum):
    CREATOR = "creator"           # Sebastian Espíndola (Creador soberano)
    TRUSTED_USER = "trusted_user" # Amigos cercanos / autorizados (Millaray, etc.)
    GUEST = "guest"               # Invitados, conexiones externas o nuevos usuarios


CREATOR_ALIASES = {
    "sebastian", "seba", "sebastián", "sebitas", "creador",
    "sebastian espindola", "sebastián espíndola", "el seba", "el sebastian"
}

TRUSTED_ALIASES = {
    "millaray", "milla", "la milla", "la millaray"
}


@dataclass
class UserProfile:
    """Perfil centralizado de permisos y contexto del interlocutor."""
    identifier: str
    display_name: str
    role: UserRole
    can_execute_tools: bool = True
    can_create_tools: bool = False
    can_delete_tools: bool = False
    can_reset_network: bool = False
    can_prune_network: bool = False
    can_upload_projects: bool = False
    can_access_sentinel: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_creator(self) -> bool:
        return self.role == UserRole.CREATOR

    @property
    def is_trusted(self) -> bool:
        return self.role in (UserRole.CREATOR, UserRole.TRUSTED_USER)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "identifier": self.identifier,
            "display_name": self.display_name,
            "role": self.role.value,
            "is_creator": self.is_creator,
            "is_trusted": self.is_trusted,
            "permissions": {
                "can_execute_tools": self.can_execute_tools,
                "can_create_tools": self.can_create_tools,
                "can_delete_tools": self.can_delete_tools,
                "can_reset_network": self.can_reset_network,
                "can_prune_network": self.can_prune_network,
                "can_upload_projects": self.can_upload_projects,
                "can_access_sentinel": self.can_access_sentinel,
            }
        }


def resolve_user_profile(
    user_obj: Optional[Any] = None,
    user_name: Optional[str] = None,
    session: Optional[Any] = None
) -> UserProfile:
    """
    Resuelve el perfil de usuario único a partir de las fuentes disponibles:
    1. Objeto User autenticado de Django.
    2. Nombre provisto en sesión o payload.
    """
    raw_name = ""
    if user_name:
        raw_name = str(user_name).strip()
    elif session and hasattr(session, "get") and session.get("user_name"):
        raw_name = str(session.get("user_name")).strip()
    elif user_obj and getattr(user_obj, "is_authenticated", False):
        raw_name = getattr(user_obj, "username", "")

    norm_name = raw_name.lower().strip()

    # 1. Creador Soberano
    if norm_name in CREATOR_ALIASES:
        return UserProfile(
            identifier=norm_name or "sebastian",
            display_name="Seba",
            role=UserRole.CREATOR,
            can_execute_tools=True,
            can_create_tools=True,
            can_delete_tools=True,
            can_reset_network=True,
            can_prune_network=True,
            can_upload_projects=True,
            can_access_sentinel=True,
        )

    # 2. Usuario de Confianza
    if norm_name in TRUSTED_ALIASES:
        return UserProfile(
            identifier=norm_name,
            display_name="Millaray",
            role=UserRole.TRUSTED_USER,
            can_execute_tools=True,
            can_create_tools=False,
            can_delete_tools=False,
            can_reset_network=False,
            can_prune_network=False,
            can_upload_projects=True,
            can_access_sentinel=True,
        )

    # 3. Invitado / Nuevo Usuario
    display = raw_name.capitalize() if raw_name else "Invitado"
    return UserProfile(
        identifier=norm_name or "guest",
        display_name=display,
        role=UserRole.GUEST,
        can_execute_tools=True,
        can_create_tools=False,
        can_delete_tools=False,
        can_reset_network=False,
        can_prune_network=False,
        can_upload_projects=False,
        can_access_sentinel=True,
    )


# =====================================================================
# DECORADORES DE ACCESO Y SEGURIDAD PARA ENDPOINTS DE DJANGO / DRF
# =====================================================================

import json

def _extract_param(request, key: str) -> Optional[str]:
    """Extrae un parámetro de consulta o cuerpo tanto de DRF Request como de WSGIRequest estándar."""
    if hasattr(request, "data") and isinstance(request.data, dict):
        val = request.data.get(key)
        if val:
            return str(val)
    if hasattr(request, "POST") and request.POST:
        val = request.POST.get(key)
        if val:
            return str(val)
    if hasattr(request, "GET") and request.GET:
        val = request.GET.get(key)
        if val:
            return str(val)
    if hasattr(request, "body") and request.body:
        try:
            parsed = json.loads(request.body.decode("utf-8"))
            if isinstance(parsed, dict):
                val = parsed.get(key)
                if val:
                    return str(val)
        except Exception:
            pass
    return None


def creator_only(view_func):
    """
    Restringe la invocación del endpoint exclusivamente al Creador (Sebastian).
    Retorna HTTP 403 Forbidden si el usuario no es el creador.
    """
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        u_name = _extract_param(request, "user_name") or _extract_param(request, "nombre") or ""
        session = getattr(request, "session", None)
        profile = resolve_user_profile(user_obj=getattr(request, "user", None), user_name=u_name, session=session)

        if not profile.is_creator:
            return Response(
                {
                    "error": "Acceso restringido: Esta operación está reservada exclusivamente para Sebastian (creador de Vector).",
                    "user_role": profile.role.value
                },
                status=403
            )
        request.user_profile = profile
        return view_func(request, *args, **kwargs)
    return wrapped


def dangerous_endpoint(view_func):
    """
    Protege endpoints destructivos (resets, podas o eliminación de herramientas)
    garantizando que solo usuarios autorizados (creador) puedan ejecutarlos.
    """
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        u_name = _extract_param(request, "user_name") or _extract_param(request, "nombre") or ""
        session = getattr(request, "session", None)
        profile = resolve_user_profile(user_obj=getattr(request, "user", None), user_name=u_name, session=session)

        if not profile.is_creator:
            return Response(
                {
                    "error": "Operación peligrosa bloqueada: no posee privilegios administrativos suficientes.",
                    "required_role": UserRole.CREATOR.value,
                    "current_role": profile.role.value
                },
                status=403
            )
        request.user_profile = profile
        return view_func(request, *args, **kwargs)
    return wrapped


def state_change_endpoint(view_func):
    """
    Inyecta y valida el perfil de usuario en endpoints que mutan el estado del sistema.
    """
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        u_name = _extract_param(request, "user_name") or _extract_param(request, "nombre") or ""
        session = getattr(request, "session", None)
        profile = resolve_user_profile(user_obj=getattr(request, "user", None), user_name=u_name, session=session)
        request.user_profile = profile
        return view_func(request, *args, **kwargs)
    return wrapped


def read_only_endpoint(view_func):
    """
    Asegura que las peticiones a endpoints de sólo lectura no ejecuten mutaciones no deseadas.
    """
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            return Response({"error": "Método HTTP no permitido en endpoint de sólo lectura."}, status=405)
        return view_func(request, *args, **kwargs)
    return wrapped
