import os
import django

if not os.environ.get("DJANGO_SETTINGS_MODULE"):
    os.environ["DJANGO_SETTINGS_MODULE"] = "vector5010.settings"
    django.setup()

import unittest
from unittest.mock import MagicMock
from rest_framework.test import APIRequestFactory
from rest_framework.response import Response

from vectorapp.security.user_profile import (
    UserProfile, resolve_user_profile,
)
from vectorapp.security.action_policy import (
    require_action_confirmation,
    dangerous_endpoint,
    state_change_endpoint,
    read_only_endpoint,
)


class TestActionPolicyAndNeutralProfiles(unittest.TestCase):
    """
    Pruebas unitarias para la arquitectura de Seguridad Imparcial y Perfiles Neutrales.
    La identidad es solo contexto cognitivo; la autorización se basa en confirmación
    explícita de acción sin privilegios por nombre o persona.
    """

    def setUp(self):
        self.factory = APIRequestFactory()

    def test_neutral_profile_resolution(self):
        """Valida que cualquier nombre se resuelva a un perfil neutral sin roles de autorización."""
        for name in ("Sebastian", "Seba", "Millaray", "Carlos", "Invitado"):
            profile = resolve_user_profile(user_name=name)
            self.assertIsInstance(profile, UserProfile)
            self.assertEqual(profile.display_name, name.capitalize())
            # No existen atributos de autorización por persona
            self.assertFalse(hasattr(profile, "role"))
            self.assertFalse(hasattr(profile, "is_creator"))
            self.assertFalse(hasattr(profile, "can_create_tools"))
            self.assertFalse(hasattr(profile, "can_reset_network"))

    def test_empty_name_defaults_to_interlocutor(self):
        """Valida que sin nombre se asigne un perfil neutral genérico."""
        profile = resolve_user_profile(user_name="")
        self.assertEqual(profile.display_name, "Interlocutor")
        self.assertEqual(profile.identifier, "interlocutor")

    def test_dangerous_endpoint_rejects_without_confirmation(self):
        """
        Valida que un endpoint peligroso rechace con 400 a CUALQUIER usuario
        (incluso si envía 'user_name': 'Sebastian') si no incluye 'confirm': true.
        """
        @dangerous_endpoint
        def sample_destructive_view(request):
            return Response({"status": "executed"}, status=200)

        # Intento por "Sebastian" sin confirmación -> RECHAZADO 400
        req_seba = self.factory.post("/api/reset/", {"user_name": "Sebastian"}, format="json")
        res_seba = sample_destructive_view(req_seba)
        self.assertEqual(res_seba.status_code, 400)
        self.assertTrue(res_seba.data.get("requires_confirmation"))

        # Intento por "Carlos" sin confirmación -> RECHAZADO 400
        req_carlos = self.factory.post("/api/reset/", {"user_name": "Carlos"}, format="json")
        res_carlos = sample_destructive_view(req_carlos)
        self.assertEqual(res_carlos.status_code, 400)

    def test_dangerous_endpoint_allows_with_confirmation(self):
        """
        Valida que un endpoint peligroso permita la ejecución a CUALQUIER interlocutor
        siempre y cuando envíe explícitamente confirm: true.
        """
        @dangerous_endpoint
        def sample_destructive_view(request):
            return Response({"status": "executed"}, status=200)

        # Confirmado por "Carlos" -> PERMITIDO 200
        req_carlos = self.factory.post("/api/reset/", {"confirm": True, "user_name": "Carlos"}, format="json")
        res_carlos = sample_destructive_view(req_carlos)
        self.assertEqual(res_carlos.status_code, 200)
        self.assertEqual(res_carlos.data.get("status"), "executed")

        # Confirmado por "Sebastian" -> PERMITIDO 200
        req_seba = self.factory.post("/api/reset/", {"confirm": True, "user_name": "Sebastian"}, format="json")
        res_seba = sample_destructive_view(req_seba)
        self.assertEqual(res_seba.status_code, 200)

    def test_query_param_confirmation(self):
        """Valida que 'confirm=true' en query params sea reconocido (ej. para DELETE o GET)."""
        @dangerous_endpoint
        def sample_delete_view(request):
            return Response({"status": "deleted"}, status=200)

        req = self.factory.delete("/api/tools/mi_tool/?confirm=true")
        res = sample_delete_view(req)
        self.assertEqual(res.status_code, 200)

    def test_state_change_and_read_only_decorators(self):
        """Valida que los decoradores informativos mantengan el flujo normal."""
        @state_change_endpoint
        def mutate(request):
            return Response({"mutated": True})

        @read_only_endpoint
        def inspect(request):
            return Response({"inspected": True})

        req1 = self.factory.post("/api/mutate/", {})
        self.assertEqual(mutate(req1).status_code, 200)

        req2 = self.factory.get("/api/inspect/")
        self.assertEqual(inspect(req2).status_code, 200)
