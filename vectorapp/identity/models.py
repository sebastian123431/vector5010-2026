"""
Modelos de datos para el subsistema de Identidad Cognitiva de Vector 2026.
La identidad de una persona representa contexto conversacional y cognitivo,
completamente desacoplada de la autorización y de las políticas de seguridad.
"""

from enum import Enum
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional


class IdentitySource(str, Enum):
    """Fuentes de proveniencia de la identidad."""
    EXPLICIT_TEXT = "explicit_text"              # Declarado directamente en el texto por el usuario
    CONFIRMED_PROFILE = "confirmed_profile"      # Perfil confirmado por el usuario
    FACE = "face_recognition"                    # Reconocimiento facial
    VOICE = "voice_recognition"                  # Reconocimiento biométrico por voz
    SESSION_HISTORY = "session_history"          # Memoria persistida en la sesión actual
    CONTEXTUAL_INFERENCE = "contextual_inference"# Inferencia contextual débil
    UNKNOWN = "unknown"                          # No identificado


class IdentityStatus(str, Enum):
    """Nivel de certeza epistemológica de la identidad."""
    DECLARED = "declared"      # Auto-declarado explícitamente por el usuario
    RECOGNIZED = "recognized"  # Reconocido multimodalmente con alta confianza
    INFERRED = "inferred"      # Inferido por contexto o sesión previa
    AMBIGUOUS = "ambiguous"    # Señales conflictivas o divergentes
    UNKNOWN = "unknown"        # Interlocutor anónimo / desconocido


@dataclass
class IdentityState:
    """Estado activo del interlocutor en una conversación."""
    identity_id: str                              # Identificador normalizado (ej: "juan", "seba", "maria")
    display_name: str                             # Nombre visual para la conversación (ej: "Juan", "Seba")
    confidence: float = 1.0                       # Nivel de confianza epistemológica [0.0, 1.0]
    source: IdentitySource = IdentitySource.UNKNOWN
    status: IdentityStatus = IdentityStatus.UNKNOWN
    session_id: str = ""                          # ID de sesión asociado
    detected_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    was_changed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "identity_id": self.identity_id,
            "display_name": self.display_name,
            "confidence": round(float(self.confidence), 4),
            "source": self.source.value if isinstance(self.source, IdentitySource) else str(self.source),
            "status": self.status.value if isinstance(self.status, IdentityStatus) else str(self.status),
            "session_id": self.session_id,
            "detected_at": self.detected_at,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IdentityState':
        source_val = data.get("source", IdentitySource.UNKNOWN.value)
        try:
            source = IdentitySource(source_val)
        except ValueError:
            source = IdentitySource.UNKNOWN

        status_val = data.get("status", IdentityStatus.UNKNOWN.value)
        try:
            status = IdentityStatus(status_val)
        except ValueError:
            status = IdentityStatus.UNKNOWN

        return cls(
            identity_id=data.get("identity_id", "unknown"),
            display_name=data.get("display_name", "Interlocutor"),
            confidence=float(data.get("confidence", 0.5)),
            source=source,
            status=status,
            session_id=data.get("session_id", ""),
            detected_at=data.get("detected_at", datetime.now().isoformat()),
            metadata=data.get("metadata", {})
        )

    @classmethod
    def create_unknown(cls, session_id: str = "") -> 'IdentityState':
        """Genera un estado neutral para usuarios no identificados."""
        return cls(
            identity_id="interlocutor_anonimo",
            display_name="Interlocutor",
            confidence=0.0,
            source=IdentitySource.UNKNOWN,
            status=IdentityStatus.UNKNOWN,
            session_id=session_id
        )
