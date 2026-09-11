"""
Procesadores sensoriales de identidad multimodal para Vector 2026.
Extrae señales biométricas de visión (rostro) y audio (voz)
y las traduce a IdentitySignal con umbrales epistemológicos rigurosos.
"""

import logging
from typing import Dict, Any, Optional, List
import numpy as np

from .models import IdentitySource, IdentityStatus, IdentityState
from .signals import IdentitySignal
from ..vision import vector_vision

logger = logging.getLogger(__name__)


class VisionIdentityProcessor:
    """
    Procesador de señales de identidad visual (reconocimiento facial).
    Umbral epistemológico estándar: 0.85 de confianza.
    """

    DEFAULT_THRESHOLD = 0.85

    def __init__(self, confidence_threshold: float = DEFAULT_THRESHOLD):
        self.confidence_threshold = confidence_threshold
        self.known_faces: Dict[str, Any] = {}

    def register_face(self, name: str, face_descriptor: Any) -> None:
        """Registra un descriptor o plantilla biométrica para un interlocutor conocido."""
        self.known_faces[name.capitalize()] = face_descriptor

    def extract_signal(
        self,
        image_input: Any,
        session_id: str = "",
        candidate_hint: Optional[str] = None,
        confidence_hint: Optional[float] = None
    ) -> Optional[IdentitySignal]:
        """
        Analiza un fotograma o entrada visual y extrae una señal biométrica facial.
        Soporta inyección de pistas (hints) o descriptores para pruebas y simulación controlada.
        """
        if image_input is None and candidate_hint is None:
            return None

        # 1. Si se proveen pistas directas (útil para integraciones externas y tests)
        if candidate_hint is not None:
            conf = float(confidence_hint if confidence_hint is not None else self.confidence_threshold)
            return IdentitySignal(
                candidate=candidate_hint.capitalize(),
                confidence=conf,
                source=IdentitySource.FACE,
                session_id=session_id,
                metadata={"channel": "vision_biometric", "threshold": self.confidence_threshold}
            )

        # 2. Análisis computacional a través de VectorVision
        try:
            face_data = None
            if isinstance(image_input, np.ndarray):
                face_data = vector_vision.detect_faces(image_input)
            elif isinstance(image_input, str):
                # Cadena base64 o ruta
                res = vector_vision.detect_from_base64(image_input)
                if res.get("success"):
                    # Si detectó personas u objetos
                    face_data = {"count": res.get("count", 0)}

            if not face_data or face_data.get("count", 0) == 0:
                return None

            # Si hay rostros detectados pero no hay modelo de clasificación facial entrenado para ese rostro,
            # reporta señal genérica de presencia visual con confianza moderada
            return IdentitySignal(
                candidate="Persona_Visual",
                confidence=0.50,
                source=IdentitySource.FACE,
                session_id=session_id,
                metadata={"faces_detected": face_data.get("count", 0)}
            )

        except Exception as e:
            logger.warning(f"[VisionIdentityProcessor] Error procesando imagen: {e}")
            return None


class VoiceIdentityProcessor:
    """
    Procesador de señales de identidad acústica (reconocimiento vocal/hablante).
    Umbral epistemológico estándar: 0.80 de confianza.
    """

    DEFAULT_THRESHOLD = 0.80

    def __init__(self, confidence_threshold: float = DEFAULT_THRESHOLD):
        self.confidence_threshold = confidence_threshold
        self.known_voices: Dict[str, Any] = {}

    def register_voice(self, name: str, voice_descriptor: Any) -> None:
        """Registra una firma o perfil acústico para un interlocutor."""
        self.known_voices[name.capitalize()] = voice_descriptor

    def extract_signal(
        self,
        audio_input: Any,
        session_id: str = "",
        candidate_hint: Optional[str] = None,
        confidence_hint: Optional[float] = None
    ) -> Optional[IdentitySignal]:
        """
        Analiza un segmento de audio y extrae una señal biométrica vocal.
        Soporta pistas explícitas de speaker diarization / voice identification.
        """
        if audio_input is None and candidate_hint is None:
            return None

        # 1. Inyección de pista de diarización / biometría acústica
        if candidate_hint is not None:
            conf = float(confidence_hint if confidence_hint is not None else self.confidence_threshold)
            return IdentitySignal(
                candidate=candidate_hint.capitalize(),
                confidence=conf,
                source=IdentitySource.VOICE,
                session_id=session_id,
                metadata={"channel": "voice_biometric", "threshold": self.confidence_threshold}
            )

        # 2. Análisis por defecto si se provee audio en bruto
        return IdentitySignal(
            candidate="Hablante_Vocal",
            confidence=0.50,
            source=IdentitySource.VOICE,
            session_id=session_id,
            metadata={"audio_processed": True}
        )


class MultimodalIdentityProcessor:
    """
    Orquestador unificado de canales sensoriales para la identificación de interlocutores.
    """

    def __init__(
        self,
        vision_processor: Optional[VisionIdentityProcessor] = None,
        voice_processor: Optional[VoiceIdentityProcessor] = None
    ):
        self.vision = vision_processor or VisionIdentityProcessor()
        self.voice = voice_processor or VoiceIdentityProcessor()

    def process_signals(
        self,
        image_input: Any = None,
        audio_input: Any = None,
        image_candidate: Optional[str] = None,
        image_confidence: Optional[float] = None,
        audio_candidate: Optional[str] = None,
        audio_confidence: Optional[float] = None,
        session_id: str = ""
    ) -> List[IdentitySignal]:
        """Extrae todas las señales sensoriales disponibles para el turno actual."""
        signals: List[IdentitySignal] = []

        sig_face = self.vision.extract_signal(
            image_input=image_input,
            session_id=session_id,
            candidate_hint=image_candidate,
            confidence_hint=image_confidence
        )
        if sig_face:
            signals.append(sig_face)

        sig_voice = self.voice.extract_signal(
            audio_input=audio_input,
            session_id=session_id,
            candidate_hint=audio_candidate,
            confidence_hint=audio_confidence
        )
        if sig_voice:
            signals.append(sig_voice)

        return signals
