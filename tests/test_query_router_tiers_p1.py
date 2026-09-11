"""
Pruebas exhaustivas para el Query Router Tiers (Tier 0 regex, Tier 1 embeddings, Tier 2 Gemma).
Valida que las consultas ambiguas activen estrictamente Tier 2 según requerimiento P1.
"""

import unittest
from unittest.mock import patch
from vectorapp.query_optimizer import (
    query_optimizer, QueryComplexity, IntentCategory, QueryRouteResult
)
from vectorapp.local_engine import VectorLocalEngine


class TestQueryRouterTiersP1(unittest.TestCase):
    """
    Pruebas obligatorias del enrutador multinivel de consultas (Tier 0, 1 y 2).
    """

    def setUp(self):
        self.optimizer = query_optimizer
        self.optimizer.clear_cache()

    def test_tier0_exact_regex(self):
        """Tier 0 debe procesar saludos deterministas inmediatos."""
        res = self.optimizer.route_query("hola", user_name="Juan")
        self.assertEqual(res.tier, 0)
        self.assertEqual(res.route, IntentCategory.CASUAL)
        self.assertIsNotNone(res.fast_response)

    def test_tier1_clear_intent_embeddings(self):
        """Tier 1 debe clasificar consultas claras y no ambiguas."""
        res = self.optimizer.route_query("cómo refactorizar esta función de python con ast")
        self.assertEqual(res.tier, 1)
        self.assertEqual(res.route, IntentCategory.CODING)

        res_db = self.optimizer.route_query("ejecutar query sql select en sqlite base de datos")
        self.assertEqual(res_db.tier, 1)
        self.assertEqual(res_db.route, IntentCategory.DATABASE)

    def test_tier2_ambiguous_queries_must_use_tier_2(self):
        """
        Consultas ambiguas exigidas por la especificación:
        - 'mira esto'
        - 'revisa esto'
        - 'hazlo mejor'
        - 'acuérdate de esto'
        - 'esto está fallando'
        - 'busca qué ocurrió'
        Deben usar estrictamente Tier 2 (NO assertIn(tier, (1, 2))).
        """
        casos = [
            ("mira esto", IntentCategory.VISION),
            ("revisa esto", IntentCategory.CODING),
            ("hazlo mejor", IntentCategory.REASONING),
            ("acuérdate de esto", IntentCategory.MEMORY),
            ("esto está fallando", IntentCategory.CODING),
            ("busca qué ocurrió", IntentCategory.WEB),
        ]

        import re
        def mock_gemma_chat(messages, **kwargs):
            content = messages[0]["content"]
            match = re.search(r'Consulta:\s*"([^"]+)"', content)
            query_str = match.group(1).lower() if match else content.lower()
            if "mira esto" in query_str:
                return '{"route": "vision", "confidence": 0.88}'
            elif "revisa esto" in query_str:
                return '{"route": "coding", "confidence": 0.88}'
            elif "hazlo mejor" in query_str:
                return '{"route": "reasoning", "confidence": 0.85}'
            elif "acuérdate de esto" in query_str or "acuerdate de esto" in query_str:
                return '{"route": "memory", "confidence": 0.90}'
            elif "esto está fallando" in query_str or "esto esta fallando" in query_str:
                return '{"route": "coding", "confidence": 0.88}'
            elif "busca qué ocurrió" in query_str or "busca que ocurrio" in query_str:
                return '{"route": "web", "confidence": 0.87}'
            return '{"route": "reasoning", "confidence": 0.70}'

        with patch.object(VectorLocalEngine, "chat_completion", side_effect=mock_gemma_chat):
            for query, expected_intent in casos:
                with self.subTest(query=query):
                    res = self.optimizer.route_query(query)
                    # Debe exigirse estrictamente Tier 2
                    self.assertEqual(res.tier, 2, f"La consulta ambigua '{query}' debe ejecutarse en Tier 2.")
                    self.assertEqual(res.route, expected_intent, f"La consulta '{query}' debe resolver la intención {expected_intent}.")

    def test_tier2_gemma_json_parsing_and_fallback(self):
        """Valida que classify_tier2_gemma procese JSON estricto del LLM."""
        mock_gemma_response = '{"route": "coding", "confidence": 0.88}'
        with patch.object(VectorLocalEngine, "chat_completion", return_value=mock_gemma_response):
            cat, conf = self.optimizer.classify_tier2_gemma("revisa este script")
            self.assertEqual(cat, IntentCategory.CODING)
            self.assertEqual(conf, 0.88)

    def test_tier2_fallback_to_tier1_on_failure(self):
        """Si Tier 2 falla por completo, debe haber fallback ordenado a Tier 1."""
        with patch.object(self.optimizer, "classify_tier2_gemma", return_value=None):
            res = self.optimizer.route_query("escribir codigo python para una funcion")
            self.assertEqual(res.tier, 1)
            self.assertEqual(res.route, IntentCategory.CODING)


if __name__ == "__main__":
    unittest.main()
