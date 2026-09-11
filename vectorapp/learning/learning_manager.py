"""
Gestor de Aprendizaje Autónomo Soberano para Vector (Fase P2).
Coordina el aprendizaje continuo y adaptativo en 5 subsistemas especializados:
1. MemoryLearning: Adquisición y consolidación de recuerdos vectoriales.
2. GraphLearning: Asociación hebbiana y refuerzo de aristas tipadas en la red neuronal.
3. PreferenceLearning: Extracción de preferencias explícitas por interlocutor.
4. FeedbackLearning: Calibración basada en retroalimentación y correcciones de respuesta.
5. ModelTraining: CONGELADO / DESACTIVADO por diseño de seguridad soberana.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from vectorapp.memory import MemoryItem, MemoryType, NumpyMemoryBackend
from vectorapp.neural_network import semantic_network, SemanticRelationType

logger = logging.getLogger(__name__)


class ModelTrainingSubsystem:
    """
    Controlador de pesos del modelo base.
    POR DISEÑO Y SEGURIDAD ARQUITECTÓNICA: Los pesos base de los modelos LLM (GGUF)
    están CONGELADOS en tiempo de ejecución. No se permite modificación de pesos neuronales
    en caliente para evitar deriva catastrófica y degradación del comportamiento del sistema.
    """
    is_frozen: bool = True

    @classmethod
    def train_base_model(cls, *args, **kwargs):
        raise RuntimeError(
            "Entrenamiento en caliente de pesos base deshabilitado por política de soberanía y seguridad. "
            "El aprendizaje en Vector se realiza a través de memoria episódica, grafos semánticos y preferencias."
        )


class MemoryLearning:
    """Consolidación y aprendizaje de recuerdos a largo plazo."""

    def __init__(self, backend: Optional[NumpyMemoryBackend] = None):
        self.backend = backend or NumpyMemoryBackend()

    def _compute_vector(self, text: str) -> Optional[List[float]]:
        try:
            from vectorapp.embeddings import _EMBEDDINGS
            v = _EMBEDDINGS.embed_query(text[:300])
            if v and len(v) == 768:
                return [float(x) for x in v]
        except Exception:
            pass
        return None

    def learn_fact(self, content: str, importance: float = 0.8, user_name: str = "", session_id: str = "") -> str:
        vec = self._compute_vector(content)
        item = MemoryItem(
            id="",
            content=content,
            vector=vec,
            memory_type=MemoryType.SEMANTIC,
            importance=importance,
            confidence=0.95,
            user_name=user_name,
            session_id=session_id,
        )
        return self.backend.add(item)

    def learn_episode(self, question: str, answer: str, user_name: str = "", session_id: str = "") -> str:
        snippet = f"Q: {question}\nA: {answer[:400]}"
        vec = self._compute_vector(snippet)
        item = MemoryItem(
            id="",
            content=snippet,
            vector=vec,
            memory_type=MemoryType.EPISODIC,
            importance=0.5,
            confidence=0.9,
            user_name=user_name,
            session_id=session_id,
        )
        return self.backend.add(item)


class GraphLearning:
    """Refuerzo asociativo y conexiones sinápticas en la red semántica."""

    @staticmethod
    def associate_concepts(
        source_id: str,
        target_id: str,
        relation_type: SemanticRelationType = SemanticRelationType.RELATED_TO,
        initial_strength: float = 0.6
    ):
        with semantic_network.lock:
            n1 = semantic_network.neurons.get(source_id)
            n2 = semantic_network.neurons.get(target_id)
            if n1 and n2:
                n1.connect_typed(target_id, relation_type, initial_strength)
                semantic_network.mark_dirty()

    @staticmethod
    def reinforce_path(neuron_ids: List[str], amount: float = 0.1):
        with semantic_network.lock:
            for i in range(len(neuron_ids) - 1):
                n1 = semantic_network.neurons.get(neuron_ids[i])
                if n1:
                    n1.strengthen_connection(neuron_ids[i + 1], amount)
            semantic_network.mark_dirty()


class PreferenceLearning:
    """Aprende y almacena preferencias explícitas del interlocutor."""

    def __init__(self):
        self.preferences: Dict[str, Dict[str, Any]] = {}

    def record_preference(self, user_name: str, key: str, value: Any):
        u = (user_name or "default").lower().strip()
        if u not in self.preferences:
            self.preferences[u] = {}
        self.preferences[u][key] = {
            "value": value,
            "updated_at": datetime.now().isoformat()
        }

    def get_preferences(self, user_name: str) -> Dict[str, Any]:
        u = (user_name or "default").lower().strip()
        return self.preferences.get(u, {})


class FeedbackLearning:
    """Ajusta la calibración y el comportamiento según retroalimentación."""

    def __init__(self):
        self.feedback_log: List[Dict[str, Any]] = []

    def record_feedback(self, query: str, was_helpful: bool, feedback_text: Optional[str] = None):
        self.feedback_log.append({
            "query": query,
            "was_helpful": was_helpful,
            "feedback_text": feedback_text or "",
            "timestamp": datetime.now().isoformat()
        })


class LearningManager:
    """
    Fachada centralizada de aprendizaje soberano para Vector.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(LearningManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        self.memory_learning = MemoryLearning()
        self.graph_learning = GraphLearning()
        self.preference_learning = PreferenceLearning()
        self.feedback_learning = FeedbackLearning()
        self.model_training = ModelTrainingSubsystem()

    def get_status(self) -> Dict[str, Any]:
        return {
            "model_training_status": "FROZEN_SECURE",
            "active_memories": self.memory_learning.backend.count(),
            "recorded_feedbacks": len(self.feedback_learning.feedback_log),
            "users_with_preferences": len(self.preference_learning.preferences),
            "status": "OPERATIONAL"
        }


learning_manager = LearningManager()
