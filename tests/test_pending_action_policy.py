"""
Tests de seguridad para PendingAction y confirmación imparcial de operaciones de alto impacto (Fase P4).
Verifica:
- Ligadura estricta de token UUID con action_type y parámetros (SHA-256).
- Rechazo de parameter mismatch (token creado para tool A usado en tool B).
- Rechazo de replay attack (token de un solo uso consumido).
- Rechazo de expiración por TTL.
"""

import time
from django.test import SimpleTestCase
from vectorapp.security.action_policy import (
    PendingActionManager,
    canonicalize_action_parameters,
)


class TestPendingActionParametersP4(SimpleTestCase):
    """Pruebas de verificación de seguridad para tokens de acción pendiente y parámetros canónicos."""

    def setUp(self):
        self.mgr = PendingActionManager(default_ttl_seconds=60)

    def test_canonicalize_action_parameters_filters_confirmation_tokens(self):
        """canonicalize_action_parameters debe excluir claves de bypass/confirmación y ordenar claves."""
        class MockRequest:
            GET = {"page": "1"}
            data = {
                "tool_name": "custom_scraper",
                "pending_action_id": "999-uuid",
                "confirm": True,
                "force": "yes",
                "timeout": 30
            }
            body = b""

        canonical = canonicalize_action_parameters(MockRequest(), kwargs={"env": "prod"})
        self.assertIn("tool_name", canonical)
        self.assertIn("env", canonical)
        self.assertIn("page", canonical)
        self.assertIn("timeout", canonical)
        # Claves excluidas
        self.assertNotIn("pending_action_id", canonical)
        self.assertNotIn("confirm", canonical)
        self.assertNotIn("force", canonical)
        # Claves ordenadas canónicamente
        self.assertEqual(list(canonical.keys()), sorted(canonical.keys()))

    def test_pending_action_parameter_mismatch_denied(self):
        """Un token creado para tool A DEBE ser denegado si se intenta aplicar sobre tool B."""
        params_a = {"tool_name": "delete_tool_A"}
        params_b = {"tool_name": "delete_tool_B"}

        token = self.mgr.create_pending_action(
            action_type="delete_dynamic_tool",
            parameters=params_a,
            endpoint="/api/tools/delete/"
        )

        # 1. Intentar validar sobre tool B -> DENIED (Parameter Mismatch)
        valid_b, err_b = self.mgr.validate_and_consume(
            token,
            action_type="delete_dynamic_tool",
            parameters=params_b,
            endpoint="/api/tools/delete/"
        )
        self.assertFalse(valid_b)
        self.assertIn("mismatch", err_b.lower())

        # 2. El token NO fue consumido por el fallo, debe seguir siendo válido para tool A
        valid_a, err_a = self.mgr.validate_and_consume(
            token,
            action_type="delete_dynamic_tool",
            parameters=params_a,
            endpoint="/api/tools/delete/"
        )
        self.assertTrue(valid_a)
        self.assertIsNone(err_a)

    def test_pending_action_replay_attack_denied(self):
        """Un token de acción ya consumido no puede volver a ejecutarse (Replay Attack)."""
        params = {"operation": "purge_logs"}
        token = self.mgr.create_pending_action(action_type="maintenance", parameters=params)

        # Primer uso -> ALLOWED
        ok1, _ = self.mgr.validate_and_consume(token, action_type="maintenance", parameters=params)
        self.assertTrue(ok1)

        # Segundo uso idéntico -> DENIED
        ok2, err2 = self.mgr.validate_and_consume(token, action_type="maintenance", parameters=params)
        self.assertFalse(ok2)
        self.assertTrue(any(w in err2.lower() for w in ("consumida", "ejecutada", "no encontrada")))

    def test_pending_action_expired_token_denied(self):
        """Un token con TTL expirado debe ser rechazado inmediatamente."""
        token = self.mgr.create_pending_action(
            action_type="quick_action",
            parameters={"id": 1},
            ttl_seconds=1
        )
        time.sleep(1.1)
        valid, err = self.mgr.validate_and_consume(token, action_type="quick_action", parameters={"id": 1})
        self.assertFalse(valid)
        self.assertIn("expirado", err.lower())
