"""
Puntuación compuesta de memoria (Composite Memory Scoring).
Calcula la relevancia multidimensional combinando:
1. Similitud semántica vectorial (cosine similarity).
2. Importancia cognitiva asignada.
3. Recencia con decaimiento temporal exponencial.
4. Frecuencia de acceso acumulativa (escala logarítmica).
5. Confianza epistemológica del hecho.
"""

import math
from datetime import datetime
from typing import Dict, Any, Optional
from .types import MemoryItem


class CompositeMemoryScorer:
    """
    Evaluador de relevancia compuesta para recuperación en memoria a largo plazo.
    """

    def __init__(
        self,
        weight_similarity: float = 0.40,
        weight_importance: float = 0.25,
        weight_recency: float = 0.15,
        weight_frequency: float = 0.10,
        weight_confidence: float = 0.10,
        half_life_hours: float = 72.0,  # Tiempo en horas para que la recencia caiga al 50%
    ):
        self.w_sim = weight_similarity
        self.w_imp = weight_importance
        self.w_rec = weight_recency
        self.w_freq = weight_frequency
        self.w_conf = weight_confidence
        self.half_life_hours = max(1.0, half_life_hours)
        self.decay_lambda = math.log(2) / self.half_life_hours

    def calculate_recency_score(self, reference_time: datetime, now: Optional[datetime] = None) -> float:
        """Decaimiento exponencial de recencia basado en vida media."""
        if now is None:
            now = datetime.now()
        delta_hours = max(0.0, (now - reference_time).total_seconds() / 3600.0)
        return math.exp(-self.decay_lambda * delta_hours)

    def calculate_frequency_score(self, access_count: int) -> float:
        """Puntuación de frecuencia normalizada en escala logarítmica [0.0, 1.0]."""
        return min(1.0, math.log(1 + max(0, access_count)) / math.log(21))  # 20 accesos = 1.0

    def score(
        self,
        item: MemoryItem,
        similarity: float,
        now: Optional[datetime] = None
    ) -> float:
        """
        Calcula el puntaje de relevancia global del ítem de memoria.
        """
        sim = max(0.0, min(1.0, similarity))
        imp = max(0.0, min(1.0, item.importance))
        rec = self.calculate_recency_score(item.last_accessed, now=now)
        freq = self.calculate_frequency_score(item.access_count)
        conf = max(0.0, min(1.0, item.confidence))

        composite = (
            (self.w_sim * sim) +
            (self.w_imp * imp) +
            (self.w_rec * rec) +
            (self.w_freq * freq) +
            (self.w_conf * conf)
        )
        return round(max(0.0, min(1.0, composite)), 4)

    def compute_score(
        self,
        similarity: float,
        importance: float = 0.5,
        age_hours: float = 0.0,
        access_count: int = 1,
        confidence: float = 1.0
    ) -> float:
        """Calcula el puntaje directamente a partir de valores numéricos de componentes."""
        sim = max(0.0, min(1.0, similarity))
        imp = max(0.0, min(1.0, importance))
        rec = math.exp(-self.decay_lambda * max(0.0, age_hours))
        freq = self.calculate_frequency_score(access_count)
        conf = max(0.0, min(1.0, confidence))
        composite = (
            (self.w_sim * sim) +
            (self.w_imp * imp) +
            (self.w_rec * rec) +
            (self.w_freq * freq) +
            (self.w_conf * conf)
        )
        return round(max(0.0, min(1.0, composite)), 4)

