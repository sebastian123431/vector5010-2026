"""
Señales de identidad multimodal para Vector 2026.
Permite canalizar evidencias de texto, visión, voz, sesión o perfil hacia el IdentityResolver.
"""

from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, Any
from .models import IdentitySource


@dataclass
class IdentitySignal:
    """Evidencia individual de identidad generada por un canal perceptivo o contextual."""
    candidate: str                                # Nombre o candidato identificado (ej: "Juan", "Seba")
    confidence: float                             # Grado de certeza epistemológica [0.0, 1.0]
    source: IdentitySource                        # Canal emisor de la señal
    session_id: str = ""                          # ID de sesión asociado
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate": self.candidate,
            "confidence": round(float(self.confidence), 4),
            "source": self.source.value if isinstance(self.source, IdentitySource) else str(self.source),
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }
