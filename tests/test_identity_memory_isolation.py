import os
import django

if not os.environ.get("DJANGO_SETTINGS_MODULE"):
    os.environ["DJANGO_SETTINGS_MODULE"] = "vector5010.settings"
    django.setup()

import unittest
from django.test import TestCase
from vectorapp.models import Interaction
from vectorapp.views import recuperar_memoria_asociativa


class TestIdentityMemoryIsolation(TestCase):
    """
    Verifica que la memoria episódica e interacciones previas no tengan fuga
    cruzada (cross-talk) entre interlocutores o sesiones independientes.
    """

    def setUp(self):
        Interaction.objects.all().delete()

        # Interacción confidencial de Juan
        Interaction.objects.create(
            user=None,
            question="¿Cuál es el secreto de la fórmula X?",
            answer="La fórmula X requiere titanio hiperacelerado al vacío.",
            session_id="session_juan_999",
            user_name="Juan"
        )

        # Interacción cotidiana de Pedro
        Interaction.objects.create(
            user=None,
            question="¿Qué opinas del clima?",
            answer="El clima en Vicuña es muy soleado.",
            session_id="session_pedro_888",
            user_name="Pedro"
        )

    def test_pedro_does_not_receive_juan_secrets(self):
        """Pedro pregunta qué recuerdas de lo que hablamos -> NO debe filtrarse la fórmula de Juan."""
        recuerdo_pedro = recuperar_memoria_asociativa(
            mensaje="¿Qué recuerdas de lo que charlamos sobre la fórmula?",
            interlocutor="Pedro",
            session_id="session_pedro_888"
        )
        self.assertNotIn("titanio hiperacelerado", recuerdo_pedro)

    def test_juan_retrieves_his_own_history(self):
        """Juan consulta retrospectivamente -> sí recupera sus recuerdos asociados."""
        recuerdo_juan = recuperar_memoria_asociativa(
            mensaje="¿Qué recuerdas de lo que hablamos sobre la fórmula?",
            interlocutor="Juan",
            session_id="session_juan_999"
        )
        self.assertTrue("fórmula" in recuerdo_juan or "titanio" in recuerdo_juan)
