import os
import django

if not os.environ.get("DJANGO_SETTINGS_MODULE"):
    os.environ["DJANGO_SETTINGS_MODULE"] = "vector5010.settings"
    django.setup()

from django.test import TestCase
from vectorapp.models import Interaction, MemoryEntry


class TestSessionIsolationP1(TestCase):

    def setUp(self):
        self.sid_a = "test-session-isolated-a"
        self.sid_b = "test-session-isolated-b"
        Interaction.objects.filter(session_id__in=[self.sid_a, self.sid_b]).delete()

    def tearDown(self):
        Interaction.objects.filter(session_id__in=[self.sid_a, self.sid_b]).delete()

    def test_interaction_session_isolation(self):
        """Valida que consultas filtradas por session_id devuelvan estrictamente su propio contexto."""
        Interaction.objects.create(
            session_id=self.sid_a,
            user_name="Sebastian",
            question="Pregunta de sesión A",
            answer="Respuesta A"
        )
        Interaction.objects.create(
            session_id=self.sid_b,
            user_name="Invitado",
            question="Pregunta de sesión B",
            answer="Respuesta B"
        )

        qs_a = Interaction.objects.filter(session_id=self.sid_a)
        qs_b = Interaction.objects.filter(session_id=self.sid_b)

        self.assertEqual(qs_a.count(), 1)
        self.assertEqual(qs_a.first().question, "Pregunta de sesión A")
        self.assertEqual(qs_b.count(), 1)
        self.assertEqual(qs_b.first().question, "Pregunta de sesión B")

    def test_interaction_user_filtering(self):
        """Valida que el historial por usuario mantenga aislamiento estricto."""
        Interaction.objects.create(
            session_id=self.sid_a,
            user_name="Sebastian_Test_Isolated",
            question="Pregunta Seba",
            answer="Resp Seba"
        )
        Interaction.objects.create(
            session_id=self.sid_b,
            user_name="Millaray_Test_Isolated",
            question="Pregunta Milla",
            answer="Resp Milla"
        )

        qs_seba = Interaction.objects.filter(user_name__iexact="sebastian_test_isolated")
        qs_milla = Interaction.objects.filter(user_name__iexact="millaray_test_isolated")

        self.assertEqual(qs_seba.count(), 1)
        self.assertEqual(qs_seba.first().user_name, "Sebastian_Test_Isolated")
        self.assertEqual(qs_milla.count(), 1)
        self.assertEqual(qs_milla.first().user_name, "Millaray_Test_Isolated")
