import os
import django

if not os.environ.get("DJANGO_SETTINGS_MODULE"):
    os.environ["DJANGO_SETTINGS_MODULE"] = "vector5010.settings"
    django.setup()

import unittest
from vectorapp.cognition.planner import CognitivePlan, PlanStep, StepStatus
from vectorapp.cognition.executor import PlanExecutor
from vectorapp.cognition.reasoning_engine import ReasoningEngine, ReasoningMode
from vectorapp.cognition.tool_adapter import vector_tool_adapter


class TestReasoningExecutorP0(unittest.TestCase):
    """
    Pruebas obligatorias para el ejecutor de razonamiento:
    - required_tool != None y tool_runner == None -> FAILED ("required tool runner unavailable").
    - required_tool == None (paso puramente cognitivo) -> COMPLETED.
    - required_tool con runner válido -> COMPLETED y ejecución verificable.
    """

    def test_required_tool_without_runner_fails(self):
        """Si un paso requiere herramienta y el runner es None, el paso debe FALLAR (no simular éxito)."""
        plan = CognitivePlan(
            goal="Descomprimir archivo de proyecto",
            steps=[
                PlanStep(
                    step_number=1,
                    title="Extracción",
                    description="Descomprimir ZIP",
                    required_tool="extract_zip"
                )
            ]
        )

        executor = PlanExecutor(tool_runner=None)
        res = executor.execute_plan(plan, dry_run=False)

        self.assertFalse(res["success"])
        step = plan.steps[0]
        self.assertEqual(step.status, StepStatus.FAILED)
        self.assertIn("required tool runner unavailable", step.error)

    def test_cognitive_step_without_tool_succeeds(self):
        """Un paso cognitivo interno (sin herramienta requerida) se completa normalmente."""
        plan = CognitivePlan(
            goal="Análisis conceptual",
            steps=[
                PlanStep(
                    step_number=1,
                    title="Deducción",
                    description="Evaluar conceptos en memoria",
                    required_tool=None
                )
            ]
        )

        executor = PlanExecutor(tool_runner=None)
        res = executor.execute_plan(plan, dry_run=False)

        self.assertTrue(res["success"])
        self.assertEqual(plan.steps[0].status, StepStatus.COMPLETED)

    def test_required_tool_with_valid_runner_is_actually_invoked(self):
        """Con un runner real, la herramienta es efectivamente ejecutada."""
        invocations = []

        def mock_runner(tool_name, params):
            invocations.append((tool_name, params))
            return {"output": "OK", "ran": True}

        plan = CognitivePlan(
            goal="Ejecutar herramienta de prueba",
            steps=[
                PlanStep(
                    step_number=1,
                    title="Llamada a tool",
                    description="Ejecutar safe_test_tool",
                    required_tool="safe_test_tool"
                )
            ]
        )

        executor = PlanExecutor(tool_runner=mock_runner)
        res = executor.execute_plan(plan, dry_run=False)

        self.assertTrue(res["success"])
        self.assertEqual(plan.steps[0].status, StepStatus.COMPLETED)
        self.assertEqual(len(invocations), 1)
        self.assertEqual(invocations[0][0], "safe_test_tool")

    def test_vector_tool_adapter_safe_tool_execution(self):
        """Valida que vector_tool_adapter maneje safe_test_tool con respuesta estructurada."""
        res = vector_tool_adapter("safe_test_tool", {"description": "test_call"})
        self.assertTrue(res["success"])
        self.assertEqual(res["tool"], "safe_test_tool")
        self.assertIn("test_call", res["result"])

    def test_reasoning_engine_integration_with_adapter(self):
        """ReasoningEngine conectado a vector_tool_adapter por defecto."""
        engine = ReasoningEngine()  # usa vector_tool_adapter por defecto
        self.assertIsNotNone(engine.executor.tool_runner)
