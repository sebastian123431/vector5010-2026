"""
Políticas de seguridad imparciales basadas en acciones para Vector 2026.
Elimina la autorización basada en personas, nombres o roles humanos.
Todas las acciones de alto impacto requieren confirmación explícita de la acción
mediante 'confirm: true' o 'pending_action_id' válido y de un solo uso.
"""

import uuid
import json
import time
import hashlib
import logging
import threading
from functools import wraps
from dataclasses import dataclass, field
from typing import Optional, Any, Callable, Dict, Tuple
from rest_framework.response import Response

logger = logging.getLogger(__name__)


@dataclass
class PendingAction:
    """Acción de alto impacto pendiente de confirmación de un solo uso."""
    action_id: str
    action_type: str
    parameters_hash: str
    created_at: float
    expires_at: float
    consumed: bool = False


class PendingActionManager:
    """
    Gestor de acciones pendientes que requieren confirmación criptográfica o UUID.
    Garantiza que una confirmación esté ligada a una acción concreta y sea de un solo uso (consumed=True).
    """

    def __init__(self, default_ttl_seconds: int = 300, ttl_seconds: Optional[int] = None):
        self.default_ttl = ttl_seconds if ttl_seconds is not None else default_ttl_seconds
        self._actions: Dict[str, PendingAction] = {}
        self._lock = threading.Lock()

    def create_pending_action(
        self,
        action_type: str,
        parameters: Optional[Dict[str, Any]] = None,
        ttl_seconds: Optional[int] = None
    ) -> str:
        """Registra una acción pendiente y retorna su UUID."""
        ttl = ttl_seconds or self.default_ttl
        action_id = str(uuid.uuid4())
        now = time.time()
        p_bytes = json.dumps(parameters or {}, sort_keys=True).encode("utf-8")
        p_hash = hashlib.sha256(p_bytes).hexdigest()

        action = PendingAction(
            action_id=action_id,
            action_type=action_type,
            parameters_hash=p_hash,
            created_at=now,
            expires_at=now + ttl,
            consumed=False
        )

        with self._lock:
            # Purgar expiradas
            expired = [aid for aid, a in self._actions.items() if a.expires_at < now or a.consumed]
            for aid in expired:
                del self._actions[aid]

            self._actions[action_id] = action

        return action_id

    def create_action(
        self,
        action_type: str,
        parameters: Optional[Dict[str, Any]] = None,
        ttl_seconds: Optional[int] = None
    ) -> str:
        """Alias conveniente para create_pending_action."""
        return self.create_pending_action(action_type, parameters, ttl_seconds)

    def validate_and_consume(
        self,
        action_id: str,
        action_type: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Valida exhaustivamente y consume una acción pendiente.
        Retorna (is_valid, error_message).
        """
        if not action_id:
            return False, "action_id no proporcionado"

        now = time.time()
        with self._lock:
            action = self._actions.get(action_id)
            if not action:
                return False, f"Acción '{action_id}' no encontrada o ya fue ejecutada (consumed=True)"

            if action.consumed:
                return False, f"La acción '{action_id}' ya fue ejecutada previamente"

            if action.expires_at < now:
                del self._actions[action_id]
                return False, f"La acción '{action_id}' ha expirado"

            if action_type and action.action_type != action_type:
                return False, f"Discordancia de tipo de acción: esperada '{action_type}', recibida '{action.action_type}'"

            if parameters is not None:
                p_bytes = json.dumps(parameters, sort_keys=True).encode("utf-8")
                p_hash = hashlib.sha256(p_bytes).hexdigest()
                if action.parameters_hash != p_hash:
                    return False, "Los parámetros de la acción confirmada no coinciden con los registrados"

            action.consumed = True
            del self._actions[action_id]
            return True, None

    def verify_and_consume(
        self,
        action_id: str,
        action_type: Optional[str] = None
    ) -> bool:
        """Verifica y consume un token de acción pendiente en una sola operación atómica."""
        valid, _ = self.validate_and_consume(action_id, action_type=action_type)
        return valid


# Instancia global de acciones pendientes
pending_action_manager = PendingActionManager()


def _extract_pending_action_id(request: Any) -> Optional[str]:
    """Extrae el ID de acción pendiente de la petición."""
    # 1. Cabecera HTTP
    header_val = getattr(request, "headers", {}).get("X-Pending-Action-Id") or getattr(request, "META", {}).get("HTTP_X_PENDING_ACTION_ID")
    if header_val:
        return str(header_val).strip()

    # 2. request.data (DRF)
    if hasattr(request, "data") and isinstance(request.data, dict):
        val = request.data.get("pending_action_id") or request.data.get("action_id")
        if val:
            return str(val).strip()

    # 3. request.POST (Django standard)
    if hasattr(request, "POST") and isinstance(request.POST, dict):
        val = request.POST.get("pending_action_id") or request.POST.get("action_id")
        if val:
            return str(val).strip()

    # 4. request.GET
    if hasattr(request, "GET") and isinstance(request.GET, dict):
        val = request.GET.get("pending_action_id") or request.GET.get("action_id")
        if val:
            return str(val).strip()

    # 5. request.body (JSON raw fallback)
    if hasattr(request, "body") and request.body:
        try:
            body_dict = json.loads(request.body)
            if isinstance(body_dict, dict):
                val = body_dict.get("pending_action_id") or body_dict.get("action_id")
                if val:
                    return str(val).strip()
        except Exception:
            pass

    return None


def _is_action_confirmed(request: Any, action_name: str) -> bool:
    """
    Verifica si la petición incluye confirmación explícita o un pending_action_id válido.
    """
    # 1. Verificar si viene con pending_action_id válido
    pending_id = _extract_pending_action_id(request)
    if pending_id:
        if pending_action_manager.verify_and_consume(pending_id, action_type=action_name):
            return True

    # 2. Cabecera HTTP directa
    header_val = getattr(request, "headers", {}).get("X-Action-Confirmed") or getattr(request, "META", {}).get("HTTP_X_ACTION_CONFIRMED")
    if header_val and str(header_val).lower() in ("true", "1", "yes"):
        return True

    # 3. request.data (DRF)
    if hasattr(request, "data") and isinstance(request.data, dict):
        for key in ("confirm", "confirm_action", "confirmed", "force"):
            val = request.data.get(key)
            if val is True or str(val).lower() in ("true", "1", "yes"):
                return True

    # 4. request.POST (Django standard)
    if hasattr(request, "POST") and isinstance(request.POST, dict):
        for key in ("confirm", "confirm_action", "confirmed", "force"):
            val = request.POST.get(key)
            if val is True or str(val).lower() in ("true", "1", "yes"):
                return True

    # 5. request.GET / query params
    if hasattr(request, "GET") and isinstance(request.GET, dict):
        for key in ("confirm", "confirm_action", "confirmed", "force"):
            val = request.GET.get(key)
            if val is True or str(val).lower() in ("true", "1", "yes"):
                return True

    # 6. request.body (JSON raw fallback)
    if hasattr(request, "body") and request.body:
        try:
            body_dict = json.loads(request.body)
            if isinstance(body_dict, dict):
                for key in ("confirm", "confirm_action", "confirmed", "force"):
                    val = body_dict.get(key)
                    if val is True or str(val).lower() in ("true", "1", "yes"):
                        return True
        except Exception:
            pass

    return False


def require_action_confirmation(action_name: str = "acción crítica"):
    """
    Decorador para endpoints y operaciones destructivas o de alto impacto.
    Exige confirmación explícita de la acción de forma completamente imparcial.
    Genera un pending_action_id de un solo uso para flujos interactivos.
    """
    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def _wrapped(request: Any, *args, **kwargs) -> Any:
            if not _is_action_confirmed(request, action_name):
                logger.warning(f"[ActionPolicy] Acción '{action_name}' bloqueada: requiere confirmación explícita.")
                # Generar pending_action_id ligado a esta acción
                pending_id = pending_action_manager.create_pending_action(action_type=action_name)
                return Response(
                    {
                        "success": False,
                        "requires_confirmation": True,
                        "action": action_name,
                        "pending_action_id": pending_id,
                        "message": (
                            f"La operación '{action_name}' es de alto impacto en el sistema y requiere "
                            f"confirmación explícita. Para proceder, envíe 'confirm': true o "
                            f"'pending_action_id': '{pending_id}' en el cuerpo de la solicitud."
                        )
                    },
                    status=400
                )
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


# Alias y decoradores imparciales (sin semántica de persona/rol)
dangerous_endpoint = require_action_confirmation("operación destructiva de sistema")
high_impact_action = require_action_confirmation("operación de alto impacto administrativo")


def state_change_endpoint(view_func: Callable) -> Callable:
    """Decorador para endpoints que mutan estado del sistema."""
    @wraps(view_func)
    def _wrapped(request: Any, *args, **kwargs) -> Any:
        return view_func(request, *args, **kwargs)
    return _wrapped


def read_only_endpoint(view_func: Callable) -> Callable:
    """Decorador para endpoints de sólo lectura."""
    @wraps(view_func)
    def _wrapped(request: Any, *args, **kwargs) -> Any:
        return view_func(request, *args, **kwargs)
    return _wrapped
