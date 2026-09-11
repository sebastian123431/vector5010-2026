import os
import django

if not os.environ.get("DJANGO_SETTINGS_MODULE"):
    os.environ["DJANGO_SETTINGS_MODULE"] = "vector5010.settings"
    django.setup()

import unittest
from vectorapp.identity import IdentityManager, IdentityState, IdentityStatus, IdentitySource


class TestIdentityContractP0(unittest.TestCase):
    """
    Pruebas obligatorias del contrato único de IdentityManager.process_message:
    - Retorna siempre IdentityState (no una tupla).
    - was_changed indica conmutación.
    - Flujo conversacional real de turnos.
    - Rechazo de falsos positivos ("Juan me dijo...").
    """

    def setUp(self):
        self.mgr = IdentityManager()

    def test_single_contract_returns_identity_state_not_tuple(self):
        """Verifica que el valor retornado sea estrictamente IdentityState y no desempaquetable como tupla."""
        sess_id = "contract_sess_01"
        state = self.mgr.process_message(message="Hola Vector soy Juan", session_id=sess_id)

        self.assertIsInstance(state, IdentityState)
        self.assertEqual(state.display_name, "Juan")
        self.assertTrue(state.was_changed)

        # Verificar que NO es iterable / no se desempaqueta como tupla (previene regresiones a (state, changed))
        with self.assertRaises(TypeError):
            a, b = state

    def test_conversation_turn_flow_and_was_changed(self):
        """
        Ejecuta el escenario obligatorio de turnos:
        1. 'Hola Vector soy Juan' -> display_name='Juan', was_changed=True
        2. '¿Cómo estás?' -> display_name='Juan', was_changed=False
        3. 'Hola Vector soy Seba' -> display_name='Seba', was_changed=True
        4. 'Juan me dijo...' -> NO debe cambiar identidad (sigue Seba, was_changed=False)
        """
        sess_id = "contract_sess_turn_flow"

        # Turno 1: Juan se presenta
        s1 = self.mgr.process_message(message="Hola Vector soy Juan", session_id=sess_id)
        self.assertEqual(s1.display_name, "Juan")
        self.assertTrue(s1.was_changed)

        # Turno 2: Mensaje ordinario sin cambio
        s2 = self.mgr.process_message(message="¿Cómo estás?", session_id=sess_id)
        self.assertEqual(s2.display_name, "Juan")
        self.assertFalse(s2.was_changed)

        # Turno 3: Conmutación explícita a Seba
        s3 = self.mgr.process_message(message="Hola Vector soy Seba", session_id=sess_id)
        self.assertEqual(s3.display_name, "Seba")
        self.assertTrue(s3.was_changed)

        # Turno 4: Mención de tercero 'Juan me dijo que revisara el código'
        s4 = self.mgr.process_message(message="Juan me dijo que revisara el código", session_id=sess_id)
        self.assertEqual(s4.display_name, "Seba")
        self.assertFalse(s4.was_changed)

    def test_parameter_compatibility(self):
        """Acepta message, session_id, session_dict, context_hints, external_signals."""
        session_dict = {}
        s = self.mgr.process_message(
            message="Hola soy Carlos",
            session_id="param_sess",
            session_dict=session_dict,
            context_hints={"hint": "test"},
            external_signals=None
        )
        self.assertEqual(s.display_name, "Carlos")
        self.assertEqual(session_dict.get("current_interlocutor_name"), "Carlos")
