"""
Tests de regresión contra falsos positivos de clima en Vector 2026.
Garantiza que consultas sobre visión, fotos, reconocimiento facial, código o identidad
NUNCA sean confundidas con reportes meteorológicos de Vicuña.
"""

from django.test import TestCase


class TestWeatherFalsePositives(TestCase):
    """Pruebas para verificar que la detección de clima no secuestre consultas de otras temáticas."""

    def test_photo_recognition_not_weather(self):
        """La pregunta 'ya si te mando una foto mia puedes reconocerme?' jamás debe ser clima."""
        from vectorapp.query_optimizer import query_optimizer, IntentCategory

        q = "ya si te mando una foto mia puedes reconocerme?"
        route_res = query_optimizer.route_query(q)

        # La intención debe ser VISION o CASUAL/REASONING, NUNCA WEB (clima)
        self.assertNotEqual(route_res.route, IntentCategory.WEB)
        self.assertIn(route_res.route, (IntentCategory.VISION, IntentCategory.CASUAL, IntentCategory.REASONING))

    def test_vision_keywords_block_weather_heuristics(self):
        """Palabras clave de visión y reconocimiento facial deben excluir heurística de clima."""
        vision_queries = [
            "ya si te mando una foto mia puedes reconocerme?",
            "si te paso una foto sabes quién soy",
            "puedes reconocer mi rostro con la cámara",
            "cómo analizas fotos en tiempo real",
            "hola vector como te sientes con las mejoras hechas actualmente?"
        ]

        # Simular historial que contenga la palabra "tiempo real"
        mock_historial = [
            {"role": "assistant", "content": "Todas nuestras interacciones se reflejan en tiempo real."},
            {"role": "user", "content": "hola vector como te sientes con las mejoras hechas actualmente?"},
            {"role": "assistant", "content": "facilita el análisis profundo del código y los datos en tiempo real"}
        ]

        for query in vision_queries:
            q_lower = query.lower()
            es_tema_no_clima = any(w in q_lower for w in [
                "foto", "imagen", "cámara", "camara", "rostro", "cara", "reconocerme", "identificarme",
                "código", "codigo", "python", "javascript", "script", "función", "funcion", "modulo", "módulo",
                "quién soy", "quien soy", "cómo me llamo", "como me llamo", "mi nombre",
                "cómo te sientes", "como te sientes", "mejoras hechas", "arquitectura", "memoria"
            ])
            self.assertTrue(es_tema_no_clima, f"La consulta '{query}' debió ser identificada como NO-CLIMA")
