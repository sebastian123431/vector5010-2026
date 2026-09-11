"""
Perfil de interlocutor neutral y compatibilidad arquitectónica para Vector 2026.
La identidad de una persona representa contexto cognitivo/conversacional,
completamente separada de la autorización de seguridad.
"""

from dataclasses import dataclass, field
from typing import Optional, Any, Dict
from .action_policy import (
    require_action_confirmation,
    dangerous_endpoint,
    creator_only,
    state_change_endpoint,
    read_only_endpoint,
)


@dataclass
class UserProfile:
    """Perfil neutral de interlocutor para contexto conversacional (sin roles de autorización)."""
    identifier: str
    display_name: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "identifier": self.identifier,
            "display_name": self.display_name,
            "metadata": self.metadata
        }


def resolve_user_profile(
    user_obj: Optional[Any] = None,
    user_name: Optional[str] = None,
    session: Optional[Any] = None
) -> UserProfile:
    """
    Resuelve el perfil neutral del interlocutor para fines exclusivamente contextuales y de saludo.
    No concede ni revoca permisos de sistema en base al nombre.
    """
    raw_name = ""
    if user_name:
        raw_name = str(user_name).strip()
    elif session and hasattr(session, "get") and session.get("current_interlocutor_name"):
        raw_name = str(session.get("current_interlocutor_name")).strip()
    elif session and hasattr(session, "get") and session.get("user_name"):
        raw_name = str(session.get("user_name")).strip()
    elif user_obj and getattr(user_obj, "is_authenticated", False):
        raw_name = getattr(user_obj, "username", "")

    display = raw_name.capitalize() if raw_name else "Interlocutor"
    identifier = raw_name.lower().strip() if raw_name else "interlocutor"

    return UserProfile(
        identifier=identifier,
        display_name=display,
        metadata={"source": "contextual_profile"}
    )
