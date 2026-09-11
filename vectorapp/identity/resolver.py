"""
Resolvedor de identidad para Vector 2026.
Procesa señales multimodales y lingüísticas, descartando falsos positivos
e integrando prioridades epistemológicas de forma rigurosa.
"""

import re
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from .models import IdentitySource, IdentityStatus, IdentityState
from .signals import IdentitySignal

# Palabras comunes en español que jamás deben interpretarse como nombres propios
PALABRAS_NO_NOMBRE = {
    'nuevo', 'nueva', 'chileno', 'chilena', 'de', 'un', 'una', 'el', 'la', 'los', 'las',
    'amigo', 'amiga', 'estudiante', 'programador', 'desarrollador', 'humano', 'persona',
    'hombre', 'mujer', 'usuario', 'invitado', 'invitada', 'aqui', 'aquí', 'aca', 'acá',
    'yo', 'tu', 'tú', 'él', 'ella', 'ellos', 'ellas', 'nosotros', 'vector', 'jarvis',
    'ia', 'bot', 'quien', 'quién', 'alguien', 'nadie', 'muy', 'tan', 'mas', 'más', 'bien',
    'mal', 'listo', 'lista', 'seguro', 'segura', 'feliz', 'triste', 'chile', 'vicuña', 'vicuna',
    'para', 'por', 'con', 'sin', 'sobre', 'tras', 'hacia', 'desde', 'hasta', 'que', 'qué',
    'porque', 'como', 'cómo', 'cuando', 'cuándo', 'donde', 'dónde', 'pero', 'aunque', 'sino',
    'asi', 'así', 'solo', 'sólo', 'tambien', 'también', 'ahora', 'ya', 'luego', 'despues',
    'después', 'hoy', 'mañana', 'ayer', 'esto', 'eso', 'aquello', 'algo', 'nada', 'todo',
    'avisarte', 'decirte', 'preguntarte', 'saludarte', 'conversar', 'hablar', 'inteligente',
    'creador', 'dueño', 'asistente', 'modelo', 'sistema', 'computadora', 'servidor', 'codigo',
    'código', 'desarrollo', 'ingeniero', 'profesor', 'alumno', 'cliente', 'jefe', 'capaz'
}

# Patrones que denotan hipótesis, condicionales o menciones de terceros (FALSOS POSITIVOS)
PATRONES_FALSO_POSITIVO = [
    r'\bsi\s+(?:yo\s+)?fuera\b',                                      # "si yo fuera Juan"
    r'\bimagina\s+que\s+(?:yo\s+)?soy\b',                             # "imagina que soy Juan"
    r'\bhaz\s+(?:de\s+cuenta|como)\s+que\s+(?:yo\s+)?soy\b',           # "haz de cuenta que soy Juan"
    r'\bsupongamos\s+que\s+(?:yo\s+)?soy\b',                          # "supongamos que soy Juan"
    r'\b(?:me\s+dijo|dice|contó|mencionó|habló)\s+que\b',             # "X me dijo que..."
    r'\b(?:le\s+dije|le\s+comenté|le\s+escribí)\s+a\b',               # "le dije a X que..."
    r'\bcon\s+([a-záéíóúñ]+)\s+(?:hablamos|fuimos|estuvimos)\b',      # "con Juan hablamos"
    r'\bde\s+parte\s+de\b',                                           # "de parte de X"
]


class IdentityResolver:
    """
    Motor de resolución de señales de identidad multimodal.
    Aplica pesos epistemológicos estrictos y previene sobreescrituras silenciosas.
    """

    # Umbrales mínimos de confianza por canal
    THRESHOLD_EXPLICIT_TEXT = 0.90
    THRESHOLD_CONFIRMED_PROFILE = 0.85
    THRESHOLD_FACE = 0.85
    THRESHOLD_VOICE = 0.80
    THRESHOLD_SESSION = 0.60
    THRESHOLD_INFERENCE = 0.40

    @classmethod
    def resolve_from_text(cls, text: str) -> Optional[IdentitySignal]:
        """Alias conveniente para extract_explicit_text_identity."""
        return cls.extract_explicit_text_identity(text)

    @classmethod
    def extract_explicit_text_identity(cls, text: str) -> Optional[IdentitySignal]:
        """
        Analiza el texto del usuario para detectar auto-identificaciones explícitas.
        Aplica filtros rigurosos para descartar oraciones condicionales, hipotéticas o menciones de terceros.
        """
        if not text or not text.strip():
            return None

        clean_text = text.strip()
        lower_text = clean_text.lower()

        # 1. Comprobar patrones de falso positivo (condicionales, citas a terceros, hipotéticos)
        for pattern in PATRONES_FALSO_POSITIVO:
            if re.search(pattern, lower_text, re.IGNORECASE):
                return None

        # Descartar si el nombre es precedido por preposiciones que indiquen tercero ("de Juan", "a Juan", "con Juan")
        # Excepto si la frase es explícitamente "aquí habla X" o "acá X"
        if re.search(r'\b(?:de|a|hacia|con|para|sobre)\s+([a-záéíóúñA-ZÁÉÍÓÚÑ]{2,20})\s+(?:me\s+dijo|dice|vendrá|viene|está)', lower_text):
            return None

        # 2. Patrones directos y naturales de auto-presentación
        # Ej: "soy Juan", "hola Vector soy Juan", "Vector, habla Juan", "ahora soy Juan", "soy el Seba"
        candidate = None

        # Patrón A: "soy [el/la] X", "hola soy [el/la] X", "ahora soy X"
        m_soy = re.search(
            r'(?:^|\b)(?:hola|buenas|hey|oye|olle|saludos)?\s*(?:,\s*)?(?:vector\s*,\s*)?(?:ahora\s+)?(?:yo\s+)?soy\s+(?:el\s+|la\s+)?([a-záéíóúñA-ZÁÉÍÓÚÑ]{2,20})\b',
            clean_text,
            re.IGNORECASE
        )
        if m_soy:
            candidate = m_soy.group(1).strip()

        # Patrón B: "me llamo X", "mi nombre es X", "puedes llamarme X", "dime X"
        if not candidate:
            m_llamo = re.search(
                r'(?:^|\b)(?:me\s+llamo|mi\s+nombre\s+es|puedes\s+llamarme|dime)\s+(?:el\s+|la\s+)?([a-záéíóúñA-ZÁÉÍÓÚÑ]{2,20})\b',
                clean_text,
                re.IGNORECASE
            )
            if m_llamo:
                candidate = m_llamo.group(1).strip()

        # Patrón C: "Vector, habla X", "aquí habla X", "te habla X"
        if not candidate:
            m_habla = re.search(
                r'(?:^|\b)(?:vector\s*,\s*)?(?:aquí|aqui|acá|aca|te)\s+habla\s+(?:el\s+|la\s+)?([a-záéíóúñA-ZÁÉÍÓÚÑ]{2,20})\b',
                clean_text,
                re.IGNORECASE
            )
            if m_habla:
                candidate = m_habla.group(1).strip()

        if candidate:
            cand_lower = candidate.lower()
            if cand_lower not in PALABRAS_NO_NOMBRE and len(cand_lower) >= 2:
                # Normalizar display name respetando la identidad declarada por el usuario
                display = candidate.capitalize()

                return IdentitySignal(
                    candidate=display,
                    confidence=1.0,
                    source=IdentitySource.EXPLICIT_TEXT,
                    metadata={"raw_match": candidate, "rule": "explicit_text_regex"}
                )

        return None

    @classmethod
    def resolve_identity(
        cls,
        current_state: Optional[IdentityState],
        signals: List[IdentitySignal],
        session_id: str = ""
    ) -> Tuple[IdentityState, bool]:
        """
        Combina las señales entrantes con el estado actual aplicando precedencia epistemológica:
        1. Identificación explícita en texto (confianza 1.0)
        2. Perfil confirmado (confianza ~0.95)
        3. Reconocimiento facial confiable (confianza >= 0.85)
        4. Reconocimiento de voz confiable (confianza >= 0.80)
        5. Sesión previa
        6. Inferencia contextual débil

        Retorna:
            (nuevo_estado, hubo_cambio_de_interlocutor)
        """
        if not signals and current_state:
            if current_state.status in (IdentityStatus.DECLARED, IdentityStatus.RECOGNIZED):
                state_turn = IdentityState(
                    identity_id=current_state.identity_id,
                    display_name=current_state.display_name,
                    confidence=current_state.confidence,
                    source=IdentitySource.SESSION_HISTORY,
                    status=IdentityStatus.RECOGNIZED,
                    session_id=current_state.session_id or session_id,
                    detected_at=current_state.detected_at,
                    metadata=dict(current_state.metadata)
                )
                return state_turn, False
            return current_state, False

        # Si no hay estado previo, iniciar desconocido
        active_state = current_state or IdentityState.create_unknown(session_id=session_id)

        # Separar señales por canal
        explicit_signals = [s for s in signals if s.source == IdentitySource.EXPLICIT_TEXT and s.confidence >= cls.THRESHOLD_EXPLICIT_TEXT]
        profile_signals = [s for s in signals if s.source == IdentitySource.CONFIRMED_PROFILE and s.confidence >= cls.THRESHOLD_CONFIRMED_PROFILE]
        face_signals = [s for s in signals if s.source == IdentitySource.FACE and s.confidence >= cls.THRESHOLD_FACE]
        voice_signals = [s for s in signals if s.source == IdentitySource.VOICE and s.confidence >= cls.THRESHOLD_VOICE]
        session_signals = [s for s in signals if s.source == IdentitySource.SESSION_HISTORY and s.confidence >= cls.THRESHOLD_SESSION]
        weak_signals = [s for s in signals if s.source == IdentitySource.CONTEXTUAL_INFERENCE and s.confidence >= cls.THRESHOLD_INFERENCE]

        # 1. MÁXIMA PRIORIDAD: Señal explícita en texto ("Soy Juan")
        if explicit_signals:
            top_sig = max(explicit_signals, key=lambda s: s.confidence)
            norm_id = top_sig.candidate.lower()
            is_new = (active_state.identity_id != norm_id) or (active_state.status == IdentityStatus.UNKNOWN)

            meta = {"promoted_from": "explicit_text"}
            # Verificar si hay señales biométricas contrarias débiles (< 0.85) o fuertes
            contrary_biometrics = [
                s for s in signals
                if s.source in (IdentitySource.FACE, IdentitySource.VOICE) and s.candidate.lower() != norm_id
            ]
            if contrary_biometrics:
                meta["contrary_biometrics_suppressed"] = [b.candidate for b in contrary_biometrics]

            new_state = IdentityState(
                identity_id=norm_id,
                display_name=top_sig.candidate,
                confidence=top_sig.confidence,
                source=IdentitySource.EXPLICIT_TEXT,
                status=IdentityStatus.DECLARED,
                session_id=session_id or active_state.session_id,
                detected_at=datetime.now().isoformat(),
                metadata=meta
            )
            return new_state, is_new

        # 2. PRIORIDAD 2: Perfil confirmado
        if profile_signals:
            top_sig = max(profile_signals, key=lambda s: s.confidence)
            norm_id = top_sig.candidate.lower()
            is_new = (active_state.identity_id != norm_id)

            new_state = IdentityState(
                identity_id=norm_id,
                display_name=top_sig.candidate,
                confidence=top_sig.confidence,
                source=IdentitySource.CONFIRMED_PROFILE,
                status=IdentityStatus.RECOGNIZED,
                session_id=session_id or active_state.session_id,
                detected_at=datetime.now().isoformat(),
                metadata={"promoted_from": "confirmed_profile"}
            )
            return new_state, is_new

        # 3. VERIFICACIÓN MULTIMODAL CONJUNTA (Visión + Voz)
        if face_signals and voice_signals:
            top_face = max(face_signals, key=lambda s: s.confidence)
            top_voice = max(voice_signals, key=lambda s: s.confidence)

            # Caso conflicto multimodal directo: Face dice X pero Voice dice Y
            if top_face.candidate.lower() != top_voice.candidate.lower():
                ambiguous_state = IdentityState(
                    identity_id="ambiguous_conflict",
                    display_name=f"Ambiguo ({top_face.candidate}/{top_voice.candidate})",
                    confidence=round((top_face.confidence + top_voice.confidence) / 2, 2),
                    source=IdentitySource.UNKNOWN,
                    status=IdentityStatus.AMBIGUOUS,
                    session_id=session_id or active_state.session_id,
                    metadata={
                        "conflict": "multimodal_divergence",
                        "face_candidate": top_face.candidate,
                        "face_confidence": top_face.confidence,
                        "voice_candidate": top_voice.candidate,
                        "voice_confidence": top_voice.confidence
                    }
                )
                return ambiguous_state, False

            # Caso consenso multimodal: Face y Voice coinciden en el mismo interlocutor
            norm_id = top_face.candidate.lower()
            is_new = (active_state.identity_id != norm_id)
            reinforced_conf = min(1.0, max(top_face.confidence, top_voice.confidence) + 0.05)
            new_state = IdentityState(
                identity_id=norm_id,
                display_name=top_face.candidate,
                confidence=reinforced_conf,
                source=IdentitySource.FACE,
                status=IdentityStatus.RECOGNIZED,
                session_id=session_id or active_state.session_id,
                metadata={"reinforced_by": "multimodal_face_and_voice"}
            )
            return new_state, is_new

        # 4. PRIORIDAD 3: Visión individual de alta confianza
        if face_signals:
            top_sig = max(face_signals, key=lambda s: s.confidence)
            norm_id = top_sig.candidate.lower()
            # Una señal facial NO debe reemplazar silenciosamente una declaración explícita reciente de otra persona
            if active_state.status == IdentityStatus.DECLARED and active_state.identity_id != norm_id:
                ambiguous_state = IdentityState(
                    identity_id=active_state.identity_id,
                    display_name=active_state.display_name,
                    confidence=active_state.confidence,
                    source=active_state.source,
                    status=IdentityStatus.AMBIGUOUS,
                    session_id=session_id or active_state.session_id,
                    metadata={"conflict": f"Face candidate '{top_sig.candidate}' ({top_sig.confidence}) conflicts with declared '{active_state.display_name}'"}
                )
                return ambiguous_state, False

            is_new = (active_state.identity_id != norm_id)
            new_state = IdentityState(
                identity_id=norm_id,
                display_name=top_sig.candidate,
                confidence=top_sig.confidence,
                source=IdentitySource.FACE,
                status=IdentityStatus.RECOGNIZED,
                session_id=session_id or active_state.session_id,
                metadata={"promoted_from": "face"}
            )
            return new_state, is_new

        # 4. PRIORIDAD 4: Reconocimiento de voz
        if voice_signals:
            top_sig = max(voice_signals, key=lambda s: s.confidence)
            norm_id = top_sig.candidate.lower()
            if active_state.status == IdentityStatus.DECLARED and active_state.identity_id != norm_id:
                ambiguous_state = IdentityState(
                    identity_id=active_state.identity_id,
                    display_name=active_state.display_name,
                    confidence=active_state.confidence,
                    source=active_state.source,
                    status=IdentityStatus.AMBIGUOUS,
                    session_id=session_id or active_state.session_id,
                    metadata={"conflict": f"Voice candidate '{top_sig.candidate}' conflicts with declared '{active_state.display_name}'"}
                )
                return ambiguous_state, False

            is_new = (active_state.identity_id != norm_id)
            new_state = IdentityState(
                identity_id=norm_id,
                display_name=top_sig.candidate,
                confidence=top_sig.confidence,
                source=IdentitySource.VOICE,
                status=IdentityStatus.RECOGNIZED,
                session_id=session_id or active_state.session_id
            )
            return new_state, is_new

        # 5. PRIORIDAD 5: Continuidad de sesión anterior
        if active_state.status in (IdentityStatus.DECLARED, IdentityStatus.RECOGNIZED):
            # Mantener la identidad existente firmemente a través de los turnos siguientes
            return active_state, False

        if session_signals:
            top_sig = max(session_signals, key=lambda s: s.confidence)
            norm_id = top_sig.candidate.lower()
            new_state = IdentityState(
                identity_id=norm_id,
                display_name=top_sig.candidate,
                confidence=top_sig.confidence,
                source=IdentitySource.SESSION_HISTORY,
                status=IdentityStatus.INFERRED,
                session_id=session_id or active_state.session_id
            )
            return new_state, True

        # 6. PRIORIDAD 6: Inferencia contextual débil (solo si no hay nadie)
        if weak_signals and active_state.status == IdentityStatus.UNKNOWN:
            top_sig = max(weak_signals, key=lambda s: s.confidence)
            norm_id = top_sig.candidate.lower()
            new_state = IdentityState(
                identity_id=norm_id,
                display_name=top_sig.candidate,
                confidence=top_sig.confidence,
                source=IdentitySource.CONTEXTUAL_INFERENCE,
                status=IdentityStatus.INFERRED,
                session_id=session_id or active_state.session_id
            )
            return new_state, True

        return active_state, False
