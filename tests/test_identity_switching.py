import os
import django

if not os.environ.get("DJANGO_SETTINGS_MODULE"):
    os.environ["DJANGO_SETTINGS_MODULE"] = "vector5010.settings"
    django.setup()

import unittest
from vectorapp.identity import (
    IdentityManager,
    IdentityStatus,
    IdentitySource,
)


class TestIdentitySwitching(unittest.TestCase):
    """Pruebas para el cambio dinámico y explícito de identidad en tiempo de ejecución."""

    def setUp(self):
        self.mgr = IdentityManager()

    def test_dynamic_identity_switch_in_session(self):
        """
        Verifica el caso de uso donde una persona usa la terminal y luego otra se presenta:
        1. 'Hola, soy Juan' -> Juan
        2. '¿Cuál es mi nombre?' -> Juan
        3. 'Ahora soy Seba' -> Seba
        4. '¿Quién soy?' -> Seba
        5. 'Hola, soy Millaray' -> Millaray
        """
        sess = "session_switch_101"
        s_dict = {}

        # 1. Juan
        r1 = self.mgr.process_message("Hola, soy Juan", session_id=sess, session_dict=s_dict)
        self.assertEqual(r1.display_name, "Juan")
        self.assertEqual(r1.source, IdentitySource.EXPLICIT_TEXT)

        # 2. Persistencia de Juan
        r2 = self.mgr.process_message("¿Recuerdas mi nombre?", session_id=sess, session_dict=s_dict)
        self.assertEqual(r2.display_name, "Juan")
        self.assertEqual(r2.source, IdentitySource.SESSION_HISTORY)

        # 3. Cambio a Seba
        r3 = self.mgr.process_message("Ahora soy Seba", session_id=sess, session_dict=s_dict)
        self.assertEqual(r3.display_name, "Seba")
        self.assertEqual(r3.source, IdentitySource.EXPLICIT_TEXT)

        # 4. Persistencia de Seba
        r4 = self.mgr.process_message("Dame un resumen del sistema", session_id=sess, session_dict=s_dict)
        self.assertEqual(r4.display_name, "Seba")

        # 5. Cambio a Millaray
        r5 = self.mgr.process_message("Hola, soy Millaray", session_id=sess, session_dict=s_dict)
        self.assertEqual(r5.display_name, "Millaray")
        self.assertEqual(r5.source, IdentitySource.EXPLICIT_TEXT)

        # 6. Persistencia de Millaray
        r6 = self.mgr.process_message("Gracias Vector", session_id=sess, session_dict=s_dict)
        self.assertEqual(r6.display_name, "Millaray")

    def test_clear_interlocutor(self):
        """Verifica que el borrado de sesión resetee el interlocutor a UNKNOWN."""
        sess = "session_clear_102"
        s_dict = {}
        self.mgr.process_message("Soy Roberto", session_id=sess, session_dict=s_dict)
        self.assertEqual(self.mgr.get_interlocutor(sess).display_name, "Roberto")

        self.mgr.clear_interlocutor(sess, s_dict)
        state_after = self.mgr.get_interlocutor(sess)
        self.assertEqual(state_after.status, IdentityStatus.UNKNOWN)
        self.assertEqual(state_after.display_name, "Interlocutor")
        self.assertNotIn("current_interlocutor_name", s_dict)
