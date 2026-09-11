"""
Subsistema de Memoria Vectorial Avanzada para Vector 2026.
Proporciona modelos tipados, puntuación compuesta multidimensional y backends NumPy/FAISS.
"""

from .types import MemoryType, MemoryItem
from .scoring import CompositeMemoryScorer
from .backend import MemoryBackend, NumpyMemoryBackend, FaissMemoryBackend
from .manager import MemoryManager, memory_manager

__all__ = [
    "MemoryType",
    "MemoryItem",
    "CompositeMemoryScorer",
    "MemoryBackend",
    "NumpyMemoryBackend",
    "FaissMemoryBackend",
    "MemoryManager",
    "memory_manager",
]
