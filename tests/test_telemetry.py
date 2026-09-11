"""
Pruebas para la Fase P4: Telemetría y Observabilidad de Vector 2026.
"""

import unittest
from vectorapp.telemetry import TelemetryManager, QueryTelemetryRecord


class TestTelemetryManager(unittest.TestCase):
    """Pruebas unitarias para el gestor de telemetría y métricas operacionales."""

    def setUp(self):
        self.telemetry = TelemetryManager(max_buffer_size=10)
        self.telemetry.clear()

    def test_record_query_and_metrics_summary(self):
        """Verifica el registro de consultas y el cálculo de estadísticas agregadas."""
        self.telemetry.record_query(
            query_id="q1",
            interlocutor="Sebastian",
            intent="greeting",
            complexity_score=0.10,
            latency_ms=15.5,
            cache_hit=True,
            status="success"
        )
        self.telemetry.record_query(
            query_id="q2",
            interlocutor="Sebastian",
            intent="code_analysis",
            complexity_score=0.60,
            latency_ms=85.0,
            tools_invoked=["code_analyzer"],
            planner_steps=3,
            cache_hit=False,
            status="success"
        )

        summary = self.telemetry.get_metrics_summary()
        self.assertEqual(summary["total_queries"], 2)
        self.assertEqual(summary["cache_hit_rate"], 0.5)
        self.assertEqual(summary["intent_distribution"]["greeting"], 1)
        self.assertEqual(summary["intent_distribution"]["code_analysis"], 1)
        self.assertEqual(summary["complexity_distribution"]["simple"], 1)
        self.assertEqual(summary["complexity_distribution"]["complex"], 1)
        self.assertEqual(summary["total_tools_invoked"], 1)
        self.assertGreater(summary["avg_latency_ms"], 0)

    def test_circular_buffer_limit(self):
        """Verifica que el buffer mantenga la cuota máxima sin desbordar memoria."""
        for i in range(15):
            self.telemetry.record_query(
                query_id=f"q_{i}",
                interlocutor="user",
                intent="general",
                complexity_score=0.20,
                latency_ms=10.0
            )

        summary = self.telemetry.get_metrics_summary()
        self.assertEqual(summary["total_queries"], 10)  # Max buffer = 10

        recents = self.telemetry.get_recent_records(limit=5)
        self.assertEqual(len(recents), 5)
        # El más reciente debe ser q_14
        self.assertEqual(recents[0]["query_id"], "q_14")

    def test_empty_metrics_summary(self):
        """Valida que un buffer vacío no genere divisiones por cero."""
        summary = self.telemetry.get_metrics_summary()
        self.assertEqual(summary["total_queries"], 0)
        self.assertEqual(summary["avg_latency_ms"], 0.0)
        self.assertEqual(summary["cache_hit_rate"], 0.0)

    def test_clear_telemetry(self):
        """Valida el vaciado completo del buffer."""
        self.telemetry.record_query("q_temp", "user", "intent", 0.1, 5.0)
        self.assertEqual(len(self.telemetry.get_recent_records()), 1)
        self.telemetry.clear()
        self.assertEqual(len(self.telemetry.get_recent_records()), 0)

    def test_error_rate_calculation(self):
        """Valida el cálculo de tasa de error operativa."""
        self.telemetry.record_query("q_ok", "user", "search", 0.1, 10.0, status="success")
        self.telemetry.record_query("q_err", "user", "search", 0.1, 10.0, status="error", error_message="Fallo")
        summary = self.telemetry.get_metrics_summary()
        self.assertEqual(summary["error_rate"], 0.5)

    def test_query_record_serialization(self):
        """Valida la serialización de un QueryTelemetryRecord."""
        rec = QueryTelemetryRecord(
            query_id="qid_1",
            timestamp="2026-09-11T00:00:00",
            interlocutor="Sebastian",
            intent="code",
            complexity_score=0.45,
            latency_ms=120.5,
            tools_invoked=["js_parser"],
            status="success"
        )
        d = rec.to_dict()
        self.assertEqual(d["query_id"], "qid_1")
        self.assertEqual(d["tools_invoked"], ["js_parser"])

    def test_identity_and_sandbox_metrics(self):
        """Verifica el registro de fuentes de identidad, rutas y bloqueos de sandbox."""
        self.telemetry.record_query(
            query_id="q_secure",
            interlocutor="Juan",
            intent="system",
            complexity_score=0.85,
            latency_ms=45.0,
            identity_source="explicit_text",
            identity_confidence=1.0,
            route="tier_2_reasoning",
            sandbox_blocks=1
        )
        summary = self.telemetry.get_metrics_summary()
        self.assertEqual(summary["total_sandbox_blocks"], 1)
        self.assertEqual(summary["identity_source_distribution"]["explicit_text"], 1)
        self.assertEqual(summary["route_distribution"]["tier_2_reasoning"], 1)
        self.assertEqual(summary["complexity_distribution"]["intensive"], 1)


