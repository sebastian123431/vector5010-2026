"""
Tests automatizados para validar los benchmarks reales de Razonamiento y Memoria (Fase P5).
Verifica:
- Causal reasoning sin evaluar prompt de entrada.
- Cálculo de métricas reales de recuperación (P@K, R@K, MRR) sobre resultados reales de MemoryManager.
- Tasa de fuga entre identidades estrictamente 0.0 (cross_identity_leak_rate == 0.0).
- Reconstrucción y recall de FAISS tras simulación de reinicio.
"""

from django.test import TestCase
from vectorapp.benchmarks.runner import BenchmarkRunner


class TestRealBenchmarksP5(TestCase):
    """Validación de benchmarks rigurosos del sistema sin listas hardcodeadas ni trampas de prompt."""

    def setUp(self):
        self.runner = BenchmarkRunner()

    def test_reasoning_benchmark_suite(self):
        """Benchmark de razonamiento debe pasar 100% evaluando planes reales."""
        res = self.runner.run_reasoning_benchmarks()
        self.assertEqual(res["category"], "reasoning")
        self.assertEqual(res["passed"], res["total"])
        self.assertEqual(res["accuracy"], 100.0)

    def test_memory_real_benchmark_metrics_and_zero_leak(self):
        """Benchmark de memoria real debe medir P@K, R@K, MRR y leak rate == 0."""
        res = self.runner.run_memory_benchmarks()
        self.assertEqual(res["category"], "memory")
        self.assertEqual(res["passed"], res["total"])
        self.assertEqual(res["accuracy"], 100.0)

        metrics = res["metrics"]
        self.assertEqual(metrics.get("cross_identity_leak_rate"), 0.0)
        self.assertGreater(metrics.get("precision_at_k", 0.0), 0.0)
        self.assertGreater(metrics.get("mrr", 0.0), 0.0)
        self.assertGreaterEqual(metrics.get("faiss_bootstrap_loaded", 0), 1)
