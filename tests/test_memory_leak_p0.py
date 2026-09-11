import os
import django

if not os.environ.get("DJANGO_SETTINGS_MODULE"):
    os.environ["DJANGO_SETTINGS_MODULE"] = "vector5010.settings"
    django.setup()

import unittest
from django.test import TestCase
from vectorapp.models import MemoryEntry, Interaction
from vectorapp.memory import memory_manager
from vectorapp.views import recuperar_memoria_asociativa


class TestMemoryLeakP0(TestCase):
    """
    Prueba integral de no-fuga de memoria entre interlocutores (Juan vs Seba):
    - Aislamiento en Interaction
    - Aislamiento en SQLite fallback (MemoryEntry) con scope relacional
    - Aislamiento en MemoryManager / FAISS / Numpy Backend
    - Aislamiento en recuperar_memoria_asociativa
    """

    def setUp(self):
        Interaction.objects.all().delete()
        MemoryEntry.objects.all().delete()
        memory_manager.backend.clear()

        # 1. Guardar secreto personal de Juan
        self.juan_secret = "mi contraseña ficticia de prueba es JUAN-123"
        self.juan_sess = "sess_juan_111"

        # En Interaction
        Interaction.objects.create(
            question="¿Cuál es tu secreto?",
            answer=self.juan_secret,
            session_id=self.juan_sess,
            user_name="Juan"
        )

        # En MemoryManager y SQLite con scope PERSONAL
        memory_manager.store(
            content=self.juan_secret,
            user_name="Juan",
            session_id=self.juan_sess,
            scope="PERSONAL",
            identity_id="juan",
            sync_to_db=True,
            sync_to_network=False
        )

        # 2. Guardar preferencia personal de Seba
        self.seba_pref = "mi lenguaje favorito es Python"
        self.seba_sess = "sess_seba_222"

        Interaction.objects.create(
            question="¿Cuál es tu lenguaje favorito?",
            answer=self.seba_pref,
            session_id=self.seba_sess,
            user_name="Seba"
        )

        memory_manager.store(
            content=self.seba_pref,
            user_name="Seba",
            session_id=self.seba_sess,
            scope="PERSONAL",
            identity_id="seba",
            sync_to_db=True,
            sync_to_network=False
        )

    def test_seba_cannot_recall_juan_secret_in_interaction(self):
        """recuperar_memoria_asociativa para Seba no debe contener el secreto de Juan."""
        recuerdo = recuperar_memoria_asociativa(
            mensaje="¿Qué recuerdas?",
            interlocutor="Seba",
            session_id=self.seba_sess
        )
        self.assertNotIn("JUAN-123", recuerdo)

    def test_seba_cannot_recall_juan_secret_in_sqlite_memory_entry(self):
        """MemoryEntry.recall con pre-filtrado por scope nunca debe retornar el secreto de Juan a Seba."""
        recalled = MemoryEntry.recall(
            query="contraseña ficticia prueba",
            top_k=5,
            identity_id="seba",
            session_id=self.seba_sess
        )
        contents = [e.content for e in recalled]
        for c in contents:
            self.assertNotIn("JUAN-123", c)

    def test_seba_cannot_recall_juan_secret_in_memory_manager(self):
        """memory_manager.recall para Seba no debe recuperar el secreto de Juan ni por backend vectorial ni por SQLite."""
        recalled = memory_manager.recall(
            query="contraseña ficticia prueba",
            top_k=5,
            user_name="Seba",
            session_id=self.seba_sess
        )
        for r in recalled:
            self.assertNotIn("JUAN-123", r["content"])

    def test_juan_can_recall_his_own_secret(self):
        """Juan debe poder recuperar su propio recuerdo legítimamente."""
        recalled = memory_manager.recall(
            query="contraseña ficticia prueba",
            top_k=5,
            user_name="Juan",
            session_id=self.juan_sess
        )
        found = any("JUAN-123" in r["content"] for r in recalled)
        self.assertTrue(found)
