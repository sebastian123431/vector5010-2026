"""
Subsistema de Identidad Cognitiva y Contextual de Vector 2026.
Separa estrictamente la identidad conversacional de la autorización de seguridad.
"""

from .models import IdentitySource, IdentityStatus, IdentityState
from .signals import IdentitySignal
from .resolver import IdentityResolver
from .manager import IdentityManager, identity_manager
from .multimodal import VisionIdentityProcessor, VoiceIdentityProcessor, MultimodalIdentityProcessor

__all__ = [
    "IdentitySource",
    "IdentityStatus",
    "IdentityState",
    "IdentitySignal",
    "IdentityResolver",
    "IdentityManager",
    "identity_manager",
    "VisionIdentityProcessor",
    "VoiceIdentityProcessor",
    "MultimodalIdentityProcessor",
]

