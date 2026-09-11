import os
import django

if not os.environ.get("DJANGO_SETTINGS_MODULE"):
    os.environ["DJANGO_SETTINGS_MODULE"] = "vector5010.settings"
    django.setup()

import unittest
from unittest.mock import MagicMock
from rest_framework.test import APIRequestFactory

from vectorapp.security.user_profile import (
    UserRole, UserProfile, resolve_user_profile,
    creator_only, dangerous_endpoint, state_change_endpoint, read_only_endpoint
)


class TestUserProfilesP1(unittest.TestCase):

    def setUp(self):
        self.factory = APIRequestFactory()

    def test_resolve_creator_profile(self):
        """Valida que alias de Sebastian se resuelvan como Creador con permisos totales."""
        for alias in ("sebastian", "Seba", "SEBASTIÁN", "sebitas", "creador"):
            profile = resolve_user_profile(user_name=alias)
            self.assertEqual(profile.role, UserRole.CREATOR)
            self.assertTrue(profile.is_creator)
            self.assertTrue(profile.can_create_tools)
            self.assertTrue(profile.can_reset_network)
            self.assertTrue(profile.can_prune_network)

    def test_resolve_trusted_user_profile(self):
        """Valida que alias de Millaray se resuelvan como Usuario de Confianza."""
        for alias in ("millaray", "Milla", "LA MILLA"):
            profile = resolve_user_profile(user_name=alias)
            self.assertEqual(profile.role, UserRole.TRUSTED_USER)
            self.assertFalse(profile.is_creator)
            self.assertTrue(profile.is_trusted)
            self.assertFalse(profile.can_reset_network)

    def test_resolve_guest_profile(self):
        """Valida que nombres desconocidos o vacíos se resuelvan como Invitado."""
        profile = resolve_user_profile(user_name="Carlos")
        self.assertEqual(profile.role, UserRole.GUEST)
        self.assertFalse(profile.is_creator)
        self.assertFalse(profile.can_create_tools)
        self.assertFalse(profile.can_reset_network)

    def test_creator_only_decorator_allows_creator(self):
        """Valida que @creator_only permita el acceso a Sebastian."""
        @creator_only
        def dummy_view(request):
            return MagicMock(status_code=200)

        request = self.factory.post("/api/dummy/", {"user_name": "Sebastian"}, format="json")
        request.user = MagicMock(is_authenticated=False)
        response = dummy_view(request)
        self.assertEqual(response.status_code, 200)

    def test_creator_only_decorator_blocks_guest(self):
        """Valida que @creator_only bloquee con 403 a usuarios no creadores."""
        @creator_only
        def dummy_view(request):
            return MagicMock(status_code=200)

        request = self.factory.post("/api/dummy/", {"user_name": "Carlos"}, format="json")
        request.user = MagicMock(is_authenticated=False)
        response = dummy_view(request)
        self.assertEqual(response.status_code, 403)
        self.assertIn("error", response.data)

    def test_dangerous_endpoint_decorator_blocks_guest(self):
        """Valida que @dangerous_endpoint impida acciones destructivas a invitados."""
        @dangerous_endpoint
        def danger_view(request):
            return MagicMock(status_code=200)

        request = self.factory.post("/api/danger/", {"user_name": "invitado"}, format="json")
        request.user = MagicMock(is_authenticated=False)
        response = danger_view(request)
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
