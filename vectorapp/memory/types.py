"""
Tipos de datos y definiciones de memoria para el subsistema de memoria vectorial de Vector.
Soporta tipos episódicos, semánticos, procedimentales, preferencias, técnicos y visuales.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
import numpy as np


class MemoryType(str, Enum):
    """Categorías de memoria cognitiva en Vector."""
    EPISODIC = "episodic"         # Conversaciones, eventos temporales, interacciones pasadas
    SEMANTIC = "semantic"         # Hechos permanentes, conocimiento conceptual
    PROCEDURAL = "procedural"     # Procedimientos paso a paso, recetas de resolución
    PREFERENCE = "preference"     # Preferencias de Sebastian y de los usuarios
    TECHNICAL = "technical"       # Especificaciones de código, arquitectura, herramientas
    VISUAL = "visual"             # Percepción visual, fotogramas, biometría facial


@dataclass
class MemoryItem:
    """Unidad fundamental de recuerdo con vector semántico y metadatos de puntuación."""
    id: str
    content: str
    memory_type: MemoryType = MemoryType.SEMANTIC
    vector: Optional[np.ndarray] = None
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 1
    importance: float = 0.5       # 0.0 a 1.0
    confidence: float = 0.8       # 0.0 a 1.0
    session_id: str = ""
    user_name: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type.value,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "access_count": self.access_count,
            "importance": self.importance,
            "confidence": self.confidence,
            "session_id": self.session_id,
            "user_name": self.user_name,
            "metadata": self.metadata,
        }
        if self.vector is not None:
            d["vector_dim"] = len(self.vector)
        return d
