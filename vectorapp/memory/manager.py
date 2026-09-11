"""
Gestor unificado de memoria (MemoryManager) para Vector 2026.
Fachada central que orquesta:
- Backend vectorial de alta velocidad (FaissMemoryBackend con fallback a NumpyMemoryBackend).
- Persistencia relacional en base de datos SQLite (MemoryEntry).
- Red neuronal semántica asociativa (semantic_network).
- Aislamiento estricto de recuerdos por identidad de interlocutor y sesión.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple, Union
import numpy as np

from .types import MemoryItem, MemoryType
from .backend import MemoryBackend, NumpyMemoryBackend, FaissMemoryBackend
from .scoring import CompositeMemoryScorer

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    Fachada unificada del ecosistema mnemónico de Vector.
    """

    def __init__(
        self,
        backend: Optional[MemoryBackend] = None,
        dimension: int = 768,
        use_faiss: bool = True
    ):
        self.dimension = dimension
        self.scorer = CompositeMemoryScorer()
        if backend is not None:
            self.backend = backend
        else:
            self.backend = FaissMemoryBackend(dimension=dimension, scorer=self.scorer) if use_faiss else NumpyMemoryBackend(scorer=self.scorer)

    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Calcula el vector denso Nomic de 768 dimensiones si está disponible."""
        try:
            from vectorapp.embeddings import _EMBEDDINGS
            raw_vec = _EMBEDDINGS.embed_query(text[:300])
            if raw_vec and len(raw_vec) == self.dimension:
                return [float(x) for x in raw_vec]
        except Exception as e:
            logger.debug(f"[MemoryManager] Aviso generando embedding: {e}")
        return None

    def store(
        self,
        content: str,
        memory_type: Union[MemoryType, str] = MemoryType.SEMANTIC,
        importance: float = 0.5,
        user_name: Optional[str] = None,
        session_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        sync_to_db: bool = True,
        sync_to_network: bool = True,
        scope: Optional[str] = None,
        identity_id: Optional[str] = None
    ) -> str:
        """
        Almacena un recuerdo en el backend vectorial y sincroniza atómicamente con SQLite y la red neuronal.
        Aplica aislamiento por scope (GLOBAL, PERSONAL, SESSION, PROJECT).
        """
        if isinstance(memory_type, str):
            try:
                m_type = MemoryType(memory_type)
            except ValueError:
                m_type = MemoryType.SEMANTIC
        else:
            m_type = memory_type

        norm_identity = (identity_id or (user_name.lower().strip() if user_name else "")).strip()
        if scope is None:
            scope = "PERSONAL" if norm_identity else ("SESSION" if session_id else "GLOBAL")

        # 1. Calcular embedding
        vec = self._get_embedding(content)

        # 2. Crear MemoryItem y almacenar en backend vectorial
        item = MemoryItem(
            id="",
            content=content,
            vector=vec,
            memory_type=m_type,
            importance=importance,
            confidence=0.95,
            user_name=norm_identity or user_name,
            session_id=session_id,
            metadata={"tags": tags or [], "scope": scope, "identity_id": norm_identity}
        )
        item_id = self.backend.add(item)

        # 3. Sincronizar con MemoryEntry en base de datos con scope real
        if sync_to_db:
            try:
                from vectorapp.models import MemoryEntry
                db_type = "fact" if m_type == MemoryType.SEMANTIC else "learning"
                db_entry = MemoryEntry(
                    content=content,
                    entry_type=db_type,
                    identity_id=norm_identity,
                    session_id=session_id or "",
                    scope=scope,
                    importance=importance,
                    confidence=0.95
                )
                if vec:
                    db_entry.set_vector(vec)
                db_entry.save()
            except Exception as e_db:
                logger.debug(f"[MemoryManager] Aviso guardando en SQLite: {e_db}")

        # 4. Sincronizar con la Red Semántica si aplica (estrictamente restringido a memorias GLOBAL)
        if sync_to_network and scope == "GLOBAL":
            try:
                from vectorapp.neural_network import semantic_network
                tag_label = "fact" if m_type == MemoryType.SEMANTIC else "memory"
                semantic_network.add_memory(content[:150], tag_label)
            except Exception as e_net:
                logger.debug(f"[MemoryManager] Aviso guardando en red semántica: {e_net}")

        return item_id

    def recall(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
        filter_type: Optional[MemoryType] = None,
        user_name: Optional[str] = None,
        session_id: Optional[str] = None,
        identity_id: Optional[str] = None,
        scope: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Recupera recuerdos unificados consultando el backend vectorial, con filtrado estricto de identidad.
        """
        results = []
        norm_user = (identity_id or user_name or "").strip().lower()
        q_vec = self._get_embedding(query)

        if q_vec is not None:
            vec_arr = np.array(q_vec, dtype=np.float32)
            scored_items = self.backend.search(
                query_vector=vec_arr,
                top_k=top_k,
                min_score=min_score,
                filter_type=filter_type,
                session_id=session_id,
                user_name=user_name
            )
            for item, score in scored_items:
                results.append({
                    "id": item.id,
                    "content": item.content,
                    "score": round(score, 4),
                    "memory_type": item.memory_type.value,
                    "user_name": item.user_name,
                    "session_id": item.session_id,
                    "source": "vector_backend"
                })

        # Si hay pocos resultados o no hay embeddings, complementar con búsqueda relacional prefiltrada por scope
        if len(results) < top_k:
            try:
                from vectorapp.models import MemoryEntry
                db_entries = MemoryEntry.recall(
                    query=query,
                    top_k=top_k,
                    identity_id=user_name,
                    session_id=session_id
                )
                for entry in db_entries:
                    if not any(r["content"] == entry.content for r in results):
                        results.append({
                            "id": f"db_{entry.id}",
                            "content": entry.content,
                            "score": 0.70,
                            "memory_type": entry.entry_type,
                            "user_name": entry.identity_id or (user_name if entry.scope == "GLOBAL" else ""),
                            "session_id": entry.session_id or (session_id if entry.scope == "GLOBAL" else ""),
                            "scope": entry.scope,
                            "source": "sqlite_db"
                        })
            except Exception as e_rel:
                logger.debug(f"[MemoryManager] Aviso en recall relacional: {e_rel}")

        return results[:top_k]

    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 5,
        min_score: float = 0.0,
        filter_type: Optional[MemoryType] = None,
        session_id: Optional[str] = None,
        user_name: Optional[str] = None,
    ) -> List[Tuple[MemoryItem, float]]:
        """Búsqueda directa por vector."""
        return self.backend.search(
            query_vector=query_vector,
            top_k=top_k,
            min_score=min_score,
            filter_type=filter_type,
            session_id=session_id,
            user_name=user_name,
        )

    def prune(self, min_importance: float = 0.2) -> int:
        """Poda recuerdos que se encuentren por debajo del umbral de importancia."""
        pruned_count = 0
        if isinstance(self.backend, (NumpyMemoryBackend, FaissMemoryBackend)):
            target = getattr(self.backend, "numpy_fallback", self.backend)
            if hasattr(target, "items"):
                with target.lock:
                    to_delete = [
                        i_id for i_id, it in target.items.items()
                        if it.importance < min_importance
                    ]
                    for i_id in to_delete:
                        self.backend.delete(i_id)
                        pruned_count += 1
        return pruned_count

    def clear(self) -> int:
        """Limpia la memoria del backend."""
        return self.backend.clear()

    def stats(self) -> Dict[str, Any]:
        """Retorna estadísticas operativas completas del subsistema de memoria."""
        db_count = 0
        try:
            from vectorapp.models import MemoryEntry
            db_count = MemoryEntry.objects.count()
        except Exception:
            pass

        network_neurons = 0
        try:
            from vectorapp.neural_network import semantic_network
            network_neurons = len(semantic_network.neurons)
        except Exception:
            pass

        return {
            "backend_count": self.backend.count(),
            "backend_type": type(self.backend).__name__,
            "db_entries_count": db_count,
            "semantic_network_neurons": network_neurons,
            "dimension": self.dimension,
        }

    def get_active_backend(self) -> str:
        """Retorna el nombre descriptivo del backend activo ('faiss', 'numpy', etc.)."""
        if isinstance(self.backend, FaissMemoryBackend) and getattr(self.backend, "use_faiss", False):
            return "faiss"
        return "numpy"


memory_manager = MemoryManager()
