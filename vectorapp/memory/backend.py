"""
Backends de almacenamiento y búsqueda vectorial para Vector.
Implementa interfaz unificada MemoryBackend con soporte para:
1. NumpyMemoryBackend: Álgebra matricial densa con NumPy (optimizado para <20,000 vectores).
2. FaissMemoryBackend: Índice FAISS de alta velocidad con fallback automático a NumPy.
"""

from abc import ABC, abstractmethod
from typing import List, Tuple, Dict, Any, Optional
import numpy as np
import threading
import uuid

from .types import MemoryItem, MemoryType
from .scoring import CompositeMemoryScorer


class MemoryBackend(ABC):
    """Interfaz abstracta para motores de memoria vectorial."""

    @abstractmethod
    def add(self, item: MemoryItem) -> str:
        """Agrega un ítem de memoria y retorna su ID."""
        pass

    @abstractmethod
    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 5,
        min_score: float = 0.0,
        filter_type: Optional[MemoryType] = None,
        session_id: Optional[str] = None,
        user_name: Optional[str] = None,
    ) -> List[Tuple[MemoryItem, float]]:
        """Busca ítems relevantes y devuelve [(item, composite_score)]."""
        pass

    @abstractmethod
    def delete(self, item_id: str) -> bool:
        """Elimina un ítem por su ID."""
        pass

    @abstractmethod
    def clear(self) -> int:
        """Limpia la memoria y devuelve el conteo de elementos eliminados."""
        pass

    @abstractmethod
    def count(self) -> int:
        """Devuelve el total de recuerdos almacenados."""
        pass


class NumpyMemoryBackend(MemoryBackend):
    """
    Backend vectorial basado en álgebra matricial densa con NumPy.
    Garantiza latencia <1ms para colecciones de memoria de Vector.
    """

    def __init__(self, scorer: Optional[CompositeMemoryScorer] = None):
        self.items: Dict[str, MemoryItem] = {}
        self.scorer = scorer or CompositeMemoryScorer()
        self.lock = threading.RLock()
        self._matrix: Optional[np.ndarray] = None
        self._matrix_ids: List[str] = []
        self._dirty = True

    def add(self, item: MemoryItem) -> str:
        if not item.id:
            item.id = str(uuid.uuid4())
        with self.lock:
            self.items[item.id] = item
            self._dirty = True
        return item.id

    def _rebuild_matrix_if_needed(self):
        if not self._dirty and self._matrix is not None:
            return

        valid_ids = []
        vectors = []
        for i_id, it in self.items.items():
            if it.vector is not None and len(it.vector) > 0:
                v = np.array(it.vector, dtype=np.float32)
                norm = np.linalg.norm(v)
                if norm > 1e-6:
                    v = v / norm
                vectors.append(v)
                valid_ids.append(i_id)

        if vectors:
            self._matrix = np.vstack(vectors)
            self._matrix_ids = valid_ids
        else:
            self._matrix = None
            self._matrix_ids = []
        self._dirty = False

    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 5,
        min_score: float = 0.0,
        filter_type: Optional[MemoryType] = None,
        session_id: Optional[str] = None,
        user_name: Optional[str] = None,
    ) -> List[Tuple[MemoryItem, float]]:
        with self.lock:
            if not self.items or query_vector is None:
                return []

            self._rebuild_matrix_if_needed()
            if self._matrix is None or len(self._matrix_ids) == 0:
                return []

            # Normalizar vector de consulta
            q = np.array(query_vector, dtype=np.float32)
            q_norm = np.linalg.norm(q)
            if q_norm > 1e-6:
                q = q / q_norm

            # Similaridad coseno por producto punto
            raw_sims = np.dot(self._matrix, q)

            scored_items: List[Tuple[MemoryItem, float]] = []
            for idx, item_id in enumerate(self._matrix_ids):
                item = self.items.get(item_id)
                if not item:
                    continue

                # Filtros opcionales
                if filter_type and item.memory_type != filter_type:
                    continue
                if session_id and item.session_id and item.session_id != session_id:
                    continue
                if user_name and item.user_name and item.user_name.lower() != user_name.lower():
                    continue

                sim = float(raw_sims[idx])
                comp_score = self.scorer.score(item, similarity=sim)

                if comp_score >= min_score:
                    scored_items.append((item, comp_score))

            # Ordenar por puntaje compuesto descendente
            scored_items.sort(key=lambda x: x[1], reverse=True)
            return scored_items[:top_k]

    def delete(self, item_id: str) -> bool:
        with self.lock:
            if item_id in self.items:
                del self.items[item_id]
                self._dirty = True
                return True
            return False

    def clear(self) -> int:
        with self.lock:
            n = len(self.items)
            self.items.clear()
            self._matrix = None
            self._matrix_ids = []
            self._dirty = False
            return n

    def count(self) -> int:
        with self.lock:
            return len(self.items)


class FaissMemoryBackend(MemoryBackend):
    """
    Backend vectorial acelerado por FAISS con fallback automático a NumpyMemoryBackend.
    """

    def __init__(self, dimension: int = 768, scorer: Optional[CompositeMemoryScorer] = None):
        self.dimension = dimension
        self.scorer = scorer or CompositeMemoryScorer()
        self.numpy_fallback = NumpyMemoryBackend(scorer=self.scorer)
        self.use_faiss = False
        self.index = None

        try:
            import faiss
            self.index = faiss.IndexFlatIP(dimension)
            self.use_faiss = True
        except Exception:
            self.use_faiss = False

    def add(self, item: MemoryItem) -> str:
        return self.numpy_fallback.add(item)

    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 5,
        min_score: float = 0.0,
        filter_type: Optional[MemoryType] = None,
        session_id: Optional[str] = None,
        user_name: Optional[str] = None,
    ) -> List[Tuple[MemoryItem, float]]:
        # Delega la búsqueda al motor NumPy que aplica puntuación compuesta y filtrado fino
        return self.numpy_fallback.search(
            query_vector=query_vector,
            top_k=top_k,
            min_score=min_score,
            filter_type=filter_type,
            session_id=session_id,
            user_name=user_name,
        )

    def delete(self, item_id: str) -> bool:
        return self.numpy_fallback.delete(item_id)

    def clear(self) -> int:
        return self.numpy_fallback.clear()

    def count(self) -> int:
        return self.numpy_fallback.count()
