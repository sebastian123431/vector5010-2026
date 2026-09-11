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
    IdentityResolver,
)


class TestIdentityManager(unittest.TestCase):
    """Pruebas exhaustivas del subsistema IdentityManager y IdentityResolver."""

    def setUp(self):
        self.mgr = IdentityManager()
        self.resolver = IdentityResolver()

    def test_explicit_text_identification(self):
        """Reconoce presentaciones directas de nombres legítimos."""
        cases = [
            ("Hola, soy Juan", "Juan"),
            ("Me llamo Sebastian", "Sebastian"),
            ("Mi nombre es Millaray", "Millaray"),
            ("soy Pedro", "Pedro"),
            ("buenas, soy Carlos Espíndola", "Carlos"),
        ]
        for text, expected in cases:
            state = self.mgr.process_message(text, session_id="test_sess_1")
            self.assertEqual(state.display_name.lower(), expected.lower())
            self.assertEqual(state.status, IdentityStatus.DECLARED)
            self.assertEqual(state.source, IdentitySource.EXPLICIT_TEXT)

    def test_multi_turn_persistence(self):
        """Mantiene la identidad del interlocutor a lo largo de múltiples turnos en la sesión."""
        sess_id = "test_persistence_sess"
        # Turno 1: Se presenta como Juan
        s1 = self.mgr.process_message("Hola Vector, soy Juan", session_id=sess_id)
        self.assertEqual(s1.display_name, "Juan")

        # Turno 2: Pregunta técnica sin decir su nombre
        s2 = self.mgr.process_message("¿Cómo optimizo esta función?", session_id=sess_id)
        self.assertEqual(s2.display_name, "Juan")
        self.assertEqual(s2.status, IdentityStatus.RECOGNIZED)
        self.assertEqual(s2.source, IdentitySource.SESSION_HISTORY)

        # Turno 3: Saludo casual
        s3 = self.mgr.process_message("Buenas noches", session_id=sess_id)
        self.assertEqual(s3.display_name, "Juan")

    def test_rejection_of_conditionals_and_hypotheticals(self):
        """Rechaza estrictamente falsos positivos por condicionales o supuestos."""
        false_positives = [
            "si yo fuera Juan resolvería esto con un bucle",
            "imagina que soy Pedro y dame un consejo",
            "supongamos que soy Seba",
            "si fuera Millaray te diría lo mismo",
            "actúa como si yo fuera Alberto",
        ]
        for phrase in false_positives:
            signal = self.resolver.resolve_from_text(phrase)
            self.assertIsNone(signal, f"Falso positivo detectado indebidamente en: '{phrase}'")

    def test_rejection_of_third_party_mentions(self):
        """Rechaza menciones de terceros o citas."""
        third_party_phrases = [
            "Seba me dijo que viniera a probar esto",
            "Juan me comentó sobre el proyecto",
            "Mi amigo Pedro me recomendó Vector",
            "Ayer hablé con Millaray sobre la red",
            "El creador de Python es Guido",
        ]
        for phrase in third_party_phrases:
            signal = self.resolver.resolve_from_text(phrase)
            self.assertIsNone(signal, f"Tercero reconocido falsamente en: '{phrase}'")

    def test_rejection_of_stop_words_as_names(self):
        """Rechaza palabras de parada o sustantivos comunes luego de 'soy'."""
        common_words = [
            "soy nuevo aquí",
            "soy desarrollador de software",
            "soy programador",
            "soy estudiante",
            "soy usuario del sistema",
            "soy quien te escribe",
            "soy un robot",
            "soy capaz de resolverlo",
        ]
        for phrase in common_words:
            signal = self.resolver.resolve_from_text(phrase)
            self.assertIsNone(signal, f"Sustantivo común tomado como nombre en: '{phrase}'")

    def test_session_dict_synchronization(self):
        """Verifica sincronización automática bidireccional con el diccionario de sesión de Django."""
        session_dict = {}
        s = self.mgr.process_message("Soy Diego", session_id="sess_sync", session_dict=session_dict)
        self.assertEqual(s.display_name, "Diego")
        self.assertEqual(session_dict.get("current_interlocutor_name"), "Diego")
        self.assertEqual(session_dict.get("user_name"), "Diego")

        # Nuevo turno usando la misma sesión sin especificar session_id en manager
        s2 = self.mgr.process_message("¿Qué hora es?", session_dict=session_dict)
        self.assertEqual(s2.display_name, "Diego")
