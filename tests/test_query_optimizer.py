"""
Pruebas automatizadas para el Optimizador de Consultas y Enrutador Híbrido (Fase P1).
Valida clasificación semántica de intención, cálculo de complejidad continua,
enrutamiento por niveles (Tier 0 fast path y Tier 1 semántico) y aislamiento de caché.
"""

import unittest
from vectorapp.query_optimizer import (
    query_optimizer, QueryComplexity, IntentCategory, QueryRouteResult
)


class TestQueryOptimizerP1(unittest.TestCase):

    def setUp(self):
        self.optimizer = query_optimizer
        self.optimizer.clear_cache()

    def test_tier0_fast_path_greetings(self):
        """Valida que saludos estándar se resuelvan en Tier 0 con respuesta inmediata."""
        res = self.optimizer.route_query("hola", user_name="Sebastian")
        self.assertEqual(res.tier, 0)
        self.assertEqual(res.route, IntentCategory.CASUAL)
        self.assertEqual(res.complexity, QueryComplexity.SIMPLE)
        self.assertLessEqual(res.complexity_score, 0.20)
        self.assertIsNotNone(res.fast_response)
        self.assertIn("Sebastian", res.fast_response)

    def test_tier0_creator_identity_check(self):
        """Valida que preguntas de identidad se resuelvan con precisión en Tier 0."""
        res = self.optimizer.route_query("¿quién soy?", user_name="Sebastian")
        self.assertEqual(res.tier, 0)
        self.assertIsNotNone(res.fast_response)
        self.assertIn("mi creador", res.fast_response)

    def test_intent_classification_coding(self):
        """Valida que consultas técnicas se clasifiquen como CODING."""
        intent, conf = self.optimizer.classify_intent("cómo refactorizar esta función de javascript con ast")
        self.assertEqual(intent, IntentCategory.CODING)
        self.assertGreaterEqual(conf, 0.70)

    def test_intent_classification_project_analysis(self):
        """Valida que solicitudes de análisis de ZIP se clasifiquen como PROJECT_ANALYSIS."""
        intent, conf = self.optimizer.classify_intent("analizar proyecto zip y diagnosticar errores")
        self.assertEqual(intent, IntentCategory.PROJECT_ANALYSIS)
        self.assertGreaterEqual(conf, 0.85)

    def test_intent_classification_tool_creation(self):
        """Valida que creación de herramientas se clasifique como TOOL_CREATION."""
        intent, conf = self.optimizer.classify_intent("crear una herramienta para calcular promedios")
        self.assertEqual(intent, IntentCategory.TOOL_CREATION)

    def test_intent_classification_database(self):
        """Valida que consultas de bases de datos se clasifiquen como DATABASE."""
        intent, conf = self.optimizer.classify_intent("hacer un query sql a la tabla de usuarios")
        self.assertEqual(intent, IntentCategory.DATABASE)

    def test_complexity_score_gradation(self):
        """Valida la escala continua de complejidad: simple < moderate < complex < intensive."""
        simple_score = self.optimizer.calculate_complexity_score("gracias")
        mod_score = self.optimizer.calculate_complexity_score("cuál es el clima en vicuña")
        complex_score = self.optimizer.calculate_complexity_score("escribir código para un parser ast en python")
        intensive_score = self.optimizer.calculate_complexity_score("diagnosticar proyecto zip completo con ast masivo y poda de red neuronal")

        self.assertLessEqual(simple_score, 0.25)
        self.assertGreater(mod_score, simple_score)
        self.assertGreater(complex_score, mod_score)
        self.assertGreater(intensive_score, complex_score)
        self.assertGreaterEqual(intensive_score, 0.75)

    def test_route_query_tier1_processing_config(self):
        """Valida que Tier 1 devuelva la configuración de procesamiento adecuada."""
        res = self.optimizer.route_query("analizar código de un script javascript")
        self.assertEqual(res.tier, 1)
        self.assertIn(res.complexity, (QueryComplexity.COMPLEX, QueryComplexity.INTENSIVE))
        self.assertIn("max_tokens", res.suggested_config)
        self.assertGreaterEqual(res.suggested_config["max_tokens"], 450)

    def test_cache_user_isolation(self):
        """Valida que la caché aísle respuestas según el interlocutor."""
        self.optimizer.cache_response("cómo estás", "Bien, Seba", user_name="Sebastian")
        self.optimizer.cache_response("cómo estás", "Bien, Milla", user_name="Millaray")

        seba_cached = self.optimizer.get_cached_response("cómo estás", user_name="Sebastian")
        milla_cached = self.optimizer.get_cached_response("cómo estás", user_name="Millaray")

        self.assertEqual(seba_cached, "Bien, Seba")
        self.assertEqual(milla_cached, "Bien, Milla")


if __name__ == "__main__":
    unittest.main()
