"""
Gestor central de Identidad Cognitiva para Vector 2026.
Administra el interlocutor actual por sesión, coordina la conmutación de contexto
y mantiene la persistencia entre turnos conversacionales.
"""

import threading
import logging
from typing import Dict, Optional, List, Tuple, Any
from .models import IdentitySource, IdentityStatus, IdentityState
from .signals import IdentitySignal
from .resolver import IdentityResolver

logger = logging.getLogger(__name__)


class IdentityManager:
    """
    Gestor singleton de identidad conversacional.
    Garantiza que la identidad sea tratada exclusivamente como contexto cognitivo,
    aislando recuerdos y preferencias por persona sin mezclar permisos de sistema.
    """

    def __init__(self):
        self._sessions: Dict[str, IdentityState] = {}
        self._lock = threading.Lock()

    def get_interlocutor(self, session_id: str = "", session_dict: Optional[Dict[str, Any]] = None) -> IdentityState:
        """
        Retorna el interlocutor activo para la sesión especificada.
        Busca en memoria interna y sincroniza con la sesión de Django si existe.
        """
        with self._lock:
            if session_id and session_id in self._sessions:
                return self._sessions[session_id]

        # Intentar restaurar desde session_dict de Django
        if session_dict is not None:
            saved_id = session_dict.get("current_interlocutor_id")
            saved_name = session_dict.get("current_interlocutor_name")
            if saved_id and saved_name:
                restored = IdentityState(
                    identity_id=saved_id,
                    display_name=saved_name,
                    confidence=float(session_dict.get("current_interlocutor_confidence", 0.9)),
                    source=IdentitySource.SESSION_HISTORY,
                    status=IdentityStatus.DECLARED,
                    session_id=session_id
                )
                with self._lock:
                    if session_id:
                        self._sessions[session_id] = restored
                return restored

        return IdentityState.create_unknown(session_id=session_id)

    def process_message(
        self,
        message: Optional[str] = None,
        session_id: str = "",
        session_dict: Optional[Dict[str, Any]] = None,
        context_hints: Optional[Dict[str, Any]] = None,
        external_signals: Optional[List[IdentitySignal]] = None,
        text: Optional[str] = None
    ) -> IdentityState:
        """
        Procesa un mensaje entrante extrayendo evidencias y resolviendo la identidad.
        Actualiza el interlocutor actual y sincroniza con session_dict si hubo cambio o afirmación.

        Retorna SIEMPRE:
            IdentityState (con .was_changed para detectar conmutación de interlocutor)
        """
        query_text = message if message is not None else (text or "")
        current_state = self.get_interlocutor(session_id=session_id, session_dict=session_dict)
        signals: List[IdentitySignal] = []

        # 1. Extraer señal explícita del texto ("Soy Juan")
        text_sig = IdentityResolver.extract_explicit_text_identity(query_text)
        if text_sig:
            text_sig.session_id = session_id
            signals.append(text_sig)

        # 2. Señales contextuales desde context_hints si se proporcionan y no hay texto explícito
        if context_hints and not text_sig:
            hint_name = context_hints.get("nombre_cliente") or context_hints.get("usuario_first_name")
            if hint_name and str(hint_name).strip():
                signals.append(IdentitySignal(
                    candidate=str(hint_name).strip().capitalize(),
                    confidence=0.70,
                    source=IdentitySource.CONTEXTUAL_INFERENCE,
                    session_id=session_id,
                    metadata={"source_hint": "context_hints"}
                ))

        # 3. Agregar señales externas provistas (ej: visión, voz, perfil)
        if external_signals:
            signals.extend(external_signals)

        # 4. Resolver estado mediante IdentityResolver
        new_state, changed = IdentityResolver.resolve_identity(
            current_state=current_state,
            signals=signals,
            session_id=session_id
        )

        # 5. Persistir en memoria interna y sincronizar con session de Django
        with self._lock:
            if session_id:
                self._sessions[session_id] = new_state

        if session_dict is not None and (changed or new_state.status != IdentityStatus.UNKNOWN):
            session_dict["current_interlocutor_id"] = new_state.identity_id
            session_dict["current_interlocutor_name"] = new_state.display_name
            session_dict["current_interlocutor_confidence"] = new_state.confidence
            session_dict["current_interlocutor_status"] = new_state.status.value
            # Retrocompatibilidad con plantillas existentes que leen user_name
            session_dict["user_name"] = new_state.display_name
            session_dict["user_name_explicit"] = (new_state.status == IdentityStatus.DECLARED)
            if hasattr(session_dict, "modified"):
                session_dict.modified = True

        if changed:
            logger.info(
                f"[IdentityManager] Interlocutor conmutado en sesión '{session_id}': "
                f"'{current_state.display_name}' -> '{new_state.display_name}' "
                f"(fuente: {new_state.source.value}, confianza: {new_state.confidence})"
            )

        new_state.was_changed = changed
        return new_state

    def set_interlocutor(
        self,
        identity_id: str,
        display_name: str,
        session_id: str = "",
        session_dict: Optional[Dict[str, Any]] = None,
        source: IdentitySource = IdentitySource.EXPLICIT_TEXT,
        confidence: float = 1.0
    ) -> IdentityState:
        """Asigna explícitamente el interlocutor activo para una sesión."""
        new_state = IdentityState(
            identity_id=identity_id.lower().strip(),
            display_name=display_name.strip(),
            confidence=confidence,
            source=source,
            status=IdentityStatus.DECLARED,
            session_id=session_id
        )
        with self._lock:
            if session_id:
                self._sessions[session_id] = new_state

        if session_dict is not None:
            session_dict["current_interlocutor_id"] = new_state.identity_id
            session_dict["current_interlocutor_name"] = new_state.display_name
            session_dict["current_interlocutor_confidence"] = new_state.confidence
            session_dict["current_interlocutor_status"] = new_state.status.value
            session_dict["user_name"] = new_state.display_name
            session_dict["user_name_explicit"] = True
            if hasattr(session_dict, "modified"):
                session_dict.modified = True

        return new_state

    def clear_interlocutor(self, session_id: str = "", session_dict: Optional[Dict[str, Any]] = None):
        """Restablece el estado de identidad a desconocido en la sesión indicada."""
        with self._lock:
            if session_id and session_id in self._sessions:
                del self._sessions[session_id]

        if session_dict is not None:
            for k in ("current_interlocutor_id", "current_interlocutor_name", "current_interlocutor_confidence", "current_interlocutor_status", "user_name", "user_name_explicit"):
                if k in session_dict:
                    del session_dict[k]
            if hasattr(session_dict, "modified"):
                session_dict.modified = True


# Instancia singleton para acceso transversal en la arquitectura
identity_manager = IdentityManager()
