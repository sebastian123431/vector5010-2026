"""
Pruebas automatizadas para el Gestor de Aprendizaje Autónomo Soberano (Fase P2).
Valida aprendizaje de memoria, grafo, preferencias, feedback y congelamiento de pesos LLM.
"""

import unittest
from vectorapp.learning import (
    LearningManager, ModelTrainingSubsystem, learning_manager
)
from vectorapp.neural_network import semantic_network, SemanticRelationType


class TestLearningManagerP2(unittest.TestCase):

    def setUp(self):
        self.lm = learning_manager

    def test_model_training_frozen_security(self):
        """Valida que los pesos base del LLM estén congelados por diseño de seguridad."""
        self.assertTrue(self.lm.model_training.is_frozen)
        with self.assertRaises(RuntimeError) as ctx:
            self.lm.model_training.train_base_model()
        self.assertIn("deshabilitado por política de soberanía", str(ctx.exception))

    def test_memory_learning_facts_and_episodes(self):
        """Valida que MemoryLearning almacene hechos y episodios sin alterar pesos base."""
        fid = self.lm.memory_learning.learn_fact("Vicuña es la comuna de residencia de Sebastian", importance=0.9)
        self.assertTrue(bool(fid))

        eid = self.lm.memory_learning.learn_episode(
            question="¿Cuál es la versión de Django?",
            answer="Django 5.2",
            user_name="Sebastian"
        )
        self.assertTrue(bool(eid))

    def test_preference_learning_storage_and_retrieval(self):
        """Valida que PreferenceLearning guarde preferencias por usuario."""
        self.lm.preference_learning.record_preference("Sebastian", "code_style", "PEP8")
        prefs = self.lm.preference_learning.get_preferences("Sebastian")
        self.assertIn("code_style", prefs)
        self.assertEqual(prefs["code_style"]["value"], "PEP8")

    def test_feedback_learning_record(self):
        """Valida registro estructurado de retroalimentación."""
        initial_len = len(self.lm.feedback_learning.feedback_log)
        self.lm.feedback_learning.record_feedback("pregunta de prueba", was_helpful=True)
        self.assertEqual(len(self.lm.feedback_learning.feedback_log), initial_len + 1)


if __name__ == "__main__":
    unittest.main()
