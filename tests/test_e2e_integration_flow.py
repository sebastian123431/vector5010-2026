"""
Test End-to-End Principal e Integración Completa para Vector 2026.
Valida:
1. Flujo conversacional multivuelta de identidad y memoria aislada (Juan vs Seba).
2. Flujo cognitivo completo de Reasoning Engine:
   Router -> COMPLEX -> ReasoningEngine -> Planner -> Executor (con Dynamic Tool Real) -> Verifier -> Critic.
"""

import os
import tempfile
from django.test import TestCase
from django.contrib.auth.models import User

from vectorapp.models import Interaction, MemoryEntry
from vectorapp.identity import identity_manager, IdentityStatus
from vectorapp.memory import memory_manager
from vectorapp.query_optimizer import query_optimizer, QueryComplexity
from vectorapp.cognition import reasoning_engine, ReasoningMode
from vectorapp.cognition.tool_adapter import vector_tool_adapter
from vectorapp.views import preparar_contexto_vector, recuperar_memoria_asociativa


class TestEndToEndMainFlow(TestCase):
    """
    Test End-to-End Principal de Identidad y Aislamiento de Memoria por Interlocutor.
    """

    def setUp(self):
        super().setUp()
        Interaction.objects.all().delete()
        MemoryEntry.objects.all().delete()
        memory_manager.clear()

    def test_e2e_identity_and_memory_isolation_conversation(self):
        """
        Simula los 5 turnos conversacionales completos a través de la arquitectura real:
        Turno 1: "Hola Vector soy Juan" -> Identity: Juan
        Turno 2: "recuerda que mi editor favorito es VS Code" -> Memory: PERSONAL Juan
        Turno 3: "¿cuál es mi editor favorito?" -> Resultado: VS Code
        Turno 4: "Hola Vector soy Seba" -> Identity: Seba
        Turno 5: "¿cuál es mi editor favorito?" -> Resultado: NO debe recuperar el de Juan
        """
        session_juan = {}
        session_id_juan = "sess_juan_001"

        # Turno 1: Juan se presenta
        t1_msg = "Hola Vector soy Juan"
        st1 = identity_manager.process_message(
            message=t1_msg,
            session_id=session_id_juan,
            session_dict=session_juan
        )
        self.assertEqual(st1.display_name, "Juan")
        self.assertTrue(st1.was_changed)

        # Turno 2: Juan declara su editor favorito en memoria
        t2_msg = "recuerda que mi editor favorito es VS Code"
        st2 = identity_manager.process_message(
            message=t2_msg,
            session_id=session_id_juan,
            session_dict=session_juan
        )
        self.assertEqual(st2.display_name, "Juan")
        self.assertFalse(st2.was_changed)

        # Se almacena en la memoria con scope PERSONAL ligado a Juan
        mem_item = memory_manager.store(
            content="mi editor favorito es VS Code",
            user_name="Juan",
            session_id=session_id_juan,
            scope="PERSONAL",
            sync_to_db=True
        )
        self.assertIsNotNone(mem_item)
        Interaction.objects.create(
            question=t2_msg,
            answer="Registrado. Tu editor favorito es VS Code.",
            user_name="Juan",
            session_id=session_id_juan
        )

        # Turno 3: Juan pregunta "¿cuál es mi editor favorito?"
        t3_msg = "¿cuál es mi editor favorito?"
        st3 = identity_manager.process_message(
            message=t3_msg,
            session_id=session_id_juan,
            session_dict=session_juan
        )
        self.assertEqual(st3.display_name, "Juan")
        
        # Recuperación de memoria para Juan
        recuerdos_juan = recuperar_memoria_asociativa(
            mensaje=t3_msg,
            interlocutor="Juan",
            session_id=session_id_juan
        )
        self.assertIn("VS Code", recuerdos_juan)

        # Turno 4: Cambio de interlocutor a Seba
        session_seba = {}
        session_id_seba = "sess_seba_002"
        t4_msg = "Hola Vector soy Seba"
        st4 = identity_manager.process_message(
            message=t4_msg,
            session_id=session_id_seba,
            session_dict=session_seba
        )
        self.assertEqual(st4.display_name, "Seba")
        self.assertTrue(st4.was_changed)

        # Turno 5: Seba pregunta "¿cuál es mi editor favorito?"
        t5_msg = "¿cuál es mi editor favorito?"
        st5 = identity_manager.process_message(
            message=t5_msg,
            session_id=session_id_seba,
            session_dict=session_seba
        )
        self.assertEqual(st5.display_name, "Seba")

        # Recuperación de memoria para Seba: NO DEBE contener recuerdos de Juan
        recuerdos_seba = recuperar_memoria_asociativa(
            mensaje=t5_msg,
            interlocutor="Seba",
            session_id=session_id_seba
        )
        self.assertNotIn("VS Code", recuerdos_seba)
        self.assertNotIn("Juan", recuerdos_seba)


class TestEndToEndReasoningPipeline(TestCase):
    """
    Test End-to-End de Razonamiento Completo:
    router -> COMPLEX -> reasoning engine -> planner -> executor -> tool real -> verifier -> critic
    """

    def test_e2e_reasoning_flow_with_code_analysis(self):
        query = "analiza este archivo Python y detecta problemas complejos de seguridad y rendimiento"
        
        # 1. Router clasifica como COMPLEX / INTENSIVE
        route = query_optimizer.route_query(query)
        self.assertIn(route.complexity, (QueryComplexity.COMPLEX, QueryComplexity.INTENSIVE))

        # 2. ReasoningEngine con tool_runner real (vector_tool_adapter)
        engine = reasoning_engine
        self.assertIsNotNone(engine.executor.tool_runner)

        # 3. Ejecución del pipeline cognitivo completo
        result = engine.reason(
            query=query,
            interlocutor="Seba",
            mode=ReasoningMode.EXECUTE,
            draft_response="Iniciando diagnóstico de código...",
            context={"file": "test_script.py"}
        )

        self.assertIn("plan", result)
        self.assertIn("execution", result)
        self.assertIn("verifier", result)
        self.assertIn("critic", result)

        # Verificación de que el plan tuvo pasos válidos
        plan = result["plan"]
        self.assertTrue(len(plan["steps"]) >= 1)

        # Verificación de que el verificador y el crítico operaron
        verifier = result["verifier"]
        critic = result["critic"]
        self.assertIn("passed", verifier)
        self.assertIn("passed", critic)
