import os
import django

if not os.environ.get("DJANGO_SETTINGS_MODULE"):
    os.environ["DJANGO_SETTINGS_MODULE"] = "vector5010.settings"
    django.setup()

import unittest
import numpy as np
from django.test import TestCase

from vectorapp.memory import (
    MemoryManager,
    NumpyMemoryBackend,
    FaissMemoryBackend,
    MemoryItem,
    MemoryType,
)
from vectorapp.models import MemoryEntry
from vectorapp.learning import GraphLearning
from vectorapp.neural_network import semantic_network, SemanticRelationType


class TestMemoryManagerP2(TestCase):
    """
    Pruebas integrales de la Fase P2:
    - Fachada unificada MemoryManager.
    - FaissMemoryBackend y soporte IndexFlatIP.
    - Eliminación del límite rígido [:200] en MemoryEntry.recall.
    - GraphLearning con semantic_network.mark_dirty().
    """

    def setUp(self):
        self.mgr = MemoryManager(use_faiss=False)  # backend determinista en entorno de prueba
        MemoryEntry.objects.all().delete()

    def test_store_and_recall_memory(self):
        """Valida almacenamiento y recuperación unificada a través de MemoryManager."""
        mid = self.mgr.store(
            content="El núcleo de Vector corre en GPU RTX 3050 Ti con CUDA.",
            memory_type=MemoryType.SEMANTIC,
            importance=0.9,
            user_name="Diego",
            session_id="sess_diego_1"
        )
        self.assertTrue(bool(mid))

        # Recuperar
        recalled = self.mgr.recall(
            query="¿Qué GPU usa Vector?",
            top_k=3,
            user_name="Diego",
            session_id="sess_diego_1"
        )
        self.assertGreaterEqual(len(recalled), 1)
        self.assertIn("RTX 3050", recalled[0]["content"])

    def test_memory_stats(self):
        """Valida que stats() entregue el conteo consolidado de la memoria."""
        self.mgr.store("Hecho de prueba para estadísticas", user_name="Carlos")
        stats = self.mgr.stats()
        self.assertIn("backend_count", stats)
        self.assertIn("db_entries_count", stats)
        self.assertIn("semantic_network_neurons", stats)
        self.assertGreaterEqual(stats["db_entries_count"], 1)

    def test_memory_prune(self):
        """Valida que prune() elimine elementos de baja importancia."""
        # Agregar ítem importante
        self.mgr.store("Dato crítico de alta relevancia", importance=0.95)
        # Agregar ítem efímero de baja importancia directamente al backend
        low_item = MemoryItem(
            id="low_1",
            content="Dato temporal descartable",
            importance=0.05
        )
        self.mgr.backend.add(low_item)

        initial_count = self.mgr.backend.count()
        pruned = self.mgr.prune(min_importance=0.2)
        self.assertGreaterEqual(pruned, 1)
        self.assertEqual(self.mgr.backend.count(), initial_count - pruned)

    def test_memory_entry_recall_without_200_limit(self):
        """Valida que MemoryEntry.recall funcione sobre colecciones completas sin tope rígido en 200."""
        entries = []
        for i in range(250):
            entries.append(MemoryEntry(
                content=f"Registro sintético de memoria número {i}",
                entry_type="fact"
            ))
        MemoryEntry.objects.bulk_create(entries)

        # Buscar un término presente en el registro 245
        found = MemoryEntry.recall(query="número 245", top_k=5)
        self.assertGreaterEqual(len(found), 1)
        self.assertIn("número 245", found[0].content)

    def test_graph_learning_mark_dirty(self):
        """Valida que GraphLearning invoque mark_dirty() en semantic_network sin errores."""
        # Asegurar que existan al menos 2 neuronas para conectar
        semantic_network.add_memory("Neurona A de prueba", "test")
        semantic_network.add_memory("Neurona B de prueba", "test")
        n_ids = list(semantic_network.neurons.keys())
        self.assertGreaterEqual(len(n_ids), 2)

        id1, id2 = n_ids[0], n_ids[1]
        GraphLearning.associate_concepts(id1, id2, relation_type=SemanticRelationType.RELATED_TO)
        self.assertTrue(semantic_network._dirty)

        GraphLearning.reinforce_path([id1, id2], amount=0.05)
        self.assertTrue(semantic_network._matrix_dirty)

    def test_faiss_backend_initialization_and_search(self):
        """Valida que FaissMemoryBackend opere correctamente y degrade con elegancia."""
        faiss_backend = FaissMemoryBackend(dimension=768)
        dummy_vec = [0.1] * 768
        item = MemoryItem(
            id="faiss_test_1",
            content="Recuerdo indexado en FAISS",
            vector=dummy_vec,
            importance=0.8
        )
        item_id = faiss_backend.add(item)
        self.assertEqual(item_id, "faiss_test_1")

        query_v = np.array(dummy_vec, dtype=np.float32)
        results = faiss_backend.search(query_v, top_k=1)
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0][0].content, "Recuerdo indexado en FAISS")
