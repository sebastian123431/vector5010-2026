"""
Pruebas automatizadas para el Subsistema de Memoria Vectorial y Puntuación Compuesta (Fase P2).
Valida backends NumPy/FAISS, CompositeMemoryScorer, decaimiento temporal y filtrado por sesión.
"""

import unittest
import numpy as np
from datetime import datetime, timedelta

from vectorapp.memory import (
    MemoryType, MemoryItem, CompositeMemoryScorer,
    NumpyMemoryBackend, FaissMemoryBackend
)


class TestMemorySystemP2(unittest.TestCase):

    def setUp(self):
        self.scorer = CompositeMemoryScorer()
        self.backend = NumpyMemoryBackend(scorer=self.scorer)

    def test_composite_scorer_similarity_dominant(self):
        """Valida que la similitud semántica tenga un peso preponderante en el ranking."""
        now = datetime.now()
        item1 = MemoryItem(id="1", content="Python Django", importance=0.5, confidence=0.8, created_at=now, last_accessed=now)
        item2 = MemoryItem(id="2", content="Receta de cocina", importance=0.5, confidence=0.8, created_at=now, last_accessed=now)

        score_high_sim = self.scorer.score(item1, similarity=0.95, now=now)
        score_low_sim = self.scorer.score(item2, similarity=0.20, now=now)

        self.assertGreater(score_high_sim, score_low_sim)
        self.assertGreaterEqual(score_high_sim, 0.60)

    def test_composite_scorer_recency_decay(self):
        """Valida que recuerdos antiguos sufran decaimiento exponencial frente a recuerdos recientes."""
        now = datetime.now()
        recent = MemoryItem(id="r", content="Reciente", importance=0.5, last_accessed=now)
        old = MemoryItem(id="o", content="Antiguo", importance=0.5, last_accessed=now - timedelta(days=10))

        score_recent = self.scorer.score(recent, similarity=0.8, now=now)
        score_old = self.scorer.score(old, similarity=0.8, now=now)

        self.assertGreater(score_recent, score_old)

    def test_numpy_backend_add_and_search(self):
        """Valida adición y búsqueda vectorial con producto punto matricial."""
        v1 = np.zeros(768, dtype=np.float32)
        v1[0] = 1.0  # Vector eje X
        v2 = np.zeros(768, dtype=np.float32)
        v2[1] = 1.0  # Vector eje Y

        self.backend.add(MemoryItem(id="item-x", content="Concepto Eje X", vector=v1, importance=0.8))
        self.backend.add(MemoryItem(id="item-y", content="Concepto Eje Y", vector=v2, importance=0.8))

        # Buscar con consulta cercana al eje X
        q = np.zeros(768, dtype=np.float32)
        q[0] = 0.95
        q[1] = 0.05

        results = self.backend.search(query_vector=q, top_k=1)
        self.assertEqual(len(results), 1)
        top_item, top_score = results[0]
        self.assertEqual(top_item.id, "item-x")
        self.assertGreater(top_score, 0.5)

    def test_numpy_backend_session_and_type_filters(self):
        """Valida que los filtros de tipo de memoria y sesión aíslen los resultados."""
        v = np.ones(768, dtype=np.float32)

        self.backend.add(MemoryItem(id="m1", content="Episodio Sesión A", memory_type=MemoryType.EPISODIC, session_id="ses-A", vector=v))
        self.backend.add(MemoryItem(id="m2", content="Técnico Sesión B", memory_type=MemoryType.TECHNICAL, session_id="ses-B", vector=v))

        res_filtered_type = self.backend.search(query_vector=v, filter_type=MemoryType.TECHNICAL)
        self.assertEqual(len(res_filtered_type), 1)
        self.assertEqual(res_filtered_type[0][0].id, "m2")

        res_filtered_ses = self.backend.search(query_vector=v, session_id="ses-A")
        self.assertEqual(len(res_filtered_ses), 1)
        self.assertEqual(res_filtered_ses[0][0].id, "m1")

    def test_faiss_backend_fallback(self):
        """Valida que FaissMemoryBackend opere transparentemente con o sin librería nativa."""
        faiss_backend = FaissMemoryBackend(dimension=768)
        v = np.ones(768, dtype=np.float32)
        faiss_backend.add(MemoryItem(id="f1", content="Prueba FAISS", vector=v))

        res = faiss_backend.search(query_vector=v, top_k=1)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0][0].id, "f1")


if __name__ == "__main__":
    unittest.main()
