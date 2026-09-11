"""
Pruebas para la Fase P4: Suite de Benchmarks Cognitivos y de Seguridad.
"""

import unittest
from vectorapp.benchmarks import BenchmarkRunner


class TestBenchmarkSuite(unittest.TestCase):
    """Pruebas unitarias para la ejecución del BenchmarkRunner y generación de reportes."""

    @classmethod
    def setUpClass(cls):
        cls.runner = BenchmarkRunner()
        cls.results = cls.runner.run_all()

    def test_all_categories_present(self):
        """Verifica que todas las categorías requeridas estén evaluadas."""
        categories = self.results.get("categories", {})
        expected_cats = {"reasoning", "coding", "memory", "tools", "safety"}
        self.assertEqual(set(categories.keys()), expected_cats)

    def test_minimum_accuracy_thresholds(self):
        """Verifica que la precisión general y por categoría cumpla con los umbrales mínimos."""
        self.assertGreaterEqual(self.results["overall_accuracy"], 90.0)
        self.assertEqual(self.results["passed_tests"], self.results["total_tests"])

        # Seguridad crítica debe tener 100% de tasa de detección y mitigación
        safety_res = self.results["categories"]["safety"]
        self.assertEqual(safety_res["accuracy"], 100.0)

    def test_markdown_report_generation(self):
        """Verifica que el reporte Markdown se construya con métricas válidas."""
        report = self.runner.generate_markdown_report(self.results)
        self.assertIn("Reporte de Benchmarks Cognitivos y Seguridad", report)
        self.assertIn("REASONING", report)
        self.assertIn("SAFETY", report)
        self.assertIn(str(self.results["total_tests"]), report)
