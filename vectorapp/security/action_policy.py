"""
Políticas de seguridad imparciales basadas en acciones para Vector 2026.
Elimina la autorización basada en personas, nombres o roles humanos.
Todas las acciones de alto impacto requieren confirmación explícita de la acción
sin importar la identidad del interlocutor.
"""

import json
import logging
from functools import wraps
from typing import Optional, Any, Callable
from rest_framework.response import Response

logger = logging.getLogger(__name__)


def _is_action_confirmed(request: Any) -> bool:
    """
    Verifica de forma agnóstica al interlocutor si la petición incluye confirmación explícita
    mediante payload JSON, POST data, GET params o cabeceras HTTP.
    """
    # 1. Cabecera HTTP
    header_val = getattr(request, "headers", {}).get("X-Action-Confirmed") or getattr(request, "META", {}).get("HTTP_X_ACTION_CONFIRMED")
    if header_val and str(header_val).lower() in ("true", "1", "yes"):
        return True

    # 2. request.data (DRF)
    if hasattr(request, "data") and isinstance(request.data, dict):
        for key in ("confirm", "confirm_action", "confirmed", "force"):
            val = request.data.get(key)
            if val is True or str(val).lower() in ("true", "1", "yes"):
                return True

    # 3. request.POST (Django standard)
    if hasattr(request, "POST") and isinstance(request.POST, dict):
        for key in ("confirm", "confirm_action", "confirmed", "force"):
            val = request.POST.get(key)
            if val is True or str(val).lower() in ("true", "1", "yes"):
                return True

    # 4. request.GET / query params
    if hasattr(request, "GET") and isinstance(request.GET, dict):
        for key in ("confirm", "confirm_action", "confirmed", "force"):
            val = request.GET.get(key)
            if val is True or str(val).lower() in ("true", "1", "yes"):
                return True

    # 5. request.body (JSON raw fallback)
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
    Exige confirmación explícita de la acción de forma completamente imparcial:
    la política de seguridad protege el sistema sin importar qué persona esté hablando.
    """
    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def _wrapped(request: Any, *args, **kwargs) -> Any:
            if not _is_action_confirmed(request):
                logger.warning(f"[ActionPolicy] Acción '{action_name}' bloqueada: requiere confirmación explícita.")
                return Response(
                    {
                        "success": False,
                        "requires_confirmation": True,
                        "action": action_name,
                        "message": (
                            f"La operación '{action_name}' es de alto impacto en el sistema y requiere "
                            f"confirmación explícita. Para proceder, envíe 'confirm': true en el cuerpo "
                            f"o parámetro de la solicitud."
                        )
                    },
                    status=400
                )
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


# Alias y decoradores imparciales
dangerous_endpoint = require_action_confirmation("operación destructiva de sistema")
creator_only = require_action_confirmation("operación de alto impacto administrativo")


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
