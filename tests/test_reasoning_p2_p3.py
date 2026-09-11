"""
Tests unitarios y de integración para las Fases P2 y P3 de Vector 2026:
- Detección de fallos en herramientas (success=False -> FAILED).
- Propagación de input_data desde Context -> Planner -> Executor -> Tool.
- Separación de Pre-Execution Safety y Post-Execution Verifier.
- Evaluación contextual del Cognitive Critic ante fallos.
"""

from django.test import SimpleTestCase
from vectorapp.cognition.planner import CognitivePlanner, CognitivePlan, PlanStep, StepStatus
from vectorapp.cognition.executor import PlanExecutor
from vectorapp.cognition.verifier import CognitiveVerifier
from vectorapp.cognition.critic import CognitiveCritic
from vectorapp.cognition.reasoning_engine import ReasoningEngine, ReasoningMode


class TestReasoningP2P3(SimpleTestCase):
    """Pruebas de regresión para contratos de ejecución, propagación de datos y verificación."""

    def test_tool_failure_produces_failed_step_and_failed_execution(self):
        """Si la herramienta devuelve success=False, el paso DEBE marcarse FAILED, nunca COMPLETED."""
        def fake_failing_runner(tool_name: str, tool_input: dict):
            return {
                "success": False,
                "error": "Error intencional de tool para prueba",
                "result": None
            }

        executor = PlanExecutor(tool_runner=fake_failing_runner)
        step = PlanStep(
            step_number=1,
            title="Paso con tool que falla",
            description="Ejecuta tool que reporta fallo en resultado",
            required_tool="fake_tool"
        )
        plan = CognitivePlan(goal="probar fallo de tool", steps=[step])

        res = executor.execute_plan(plan, dry_run=False)

        # 1. El ejecutor debe marcar el paso como FAILED
        self.assertEqual(step.status, StepStatus.FAILED)
        self.assertFalse(res["success"])
        self.assertEqual(res["completed_count"], 0)
        self.assertIn("error intencional", step.error.lower())

    def test_context_input_data_propagation_to_tool(self):
        """Planner propaga file_path y parámetros del context al PlanStep y Executor lo entrega a la tool."""
        captured_calls = []

        def recording_runner(tool_name: str, tool_input: dict):
            captured_calls.append({"tool": tool_name, "input": tool_input})
            return {"success": True, "result": "OK"}

        engine = ReasoningEngine(tool_runner=recording_runner)
        ctx = {
            "file_path": "/tmp/test_project.zip",
            "project_name": "alpha_project"
        }

        res = engine.reason(
            query="analiza este proyecto ZIP",
            context=ctx,
            mode=ReasoningMode.EXECUTE
        )

        self.assertTrue(len(captured_calls) > 0)
        first_call = captured_calls[0]
        self.assertEqual(first_call["tool"], "extract_zip")
        self.assertEqual(first_call["input"].get("file_path"), "/tmp/test_project.zip")
        self.assertEqual(first_call["input"].get("project_name"), "alpha_project")

    def test_verifier_separates_pre_safety_and_post_execution(self):
        """ReasoningEngine debe reportar pre_safety y verification de manera independiente."""
        def mock_failing_runner(tool_name: str, tool_input: dict):
            return {"success": False, "error": "Acceso denegado a recurso"}

        engine = ReasoningEngine(tool_runner=mock_failing_runner)
        res = engine.reason(
            query="analiza este proyecto ZIP",
            context={"file_path": "/dummy/path.zip"},
            mode=ReasoningMode.EXECUTE
        )

        # Pre-safety es seguro (no es comando destructivo)
        self.assertTrue(res["pre_safety"]["safe"])
        # Pero la ejecución falló por la herramienta
        self.assertFalse(res["execution"]["success"])
        # Y la verificación post-ejecución detectó la falla
        self.assertFalse(res["verification"]["passed"])
        self.assertGreater(len(res["verification"]["failed_steps"]), 0)
        # Éxito general del motor debe ser False
        self.assertFalse(res["success"])

    def test_critic_penalizes_when_execution_fails(self):
        """CognitiveCritic debe penalizar la evaluación si la ejecución o verificación fallaron."""
        fake_exec_failed = {
            "success": False,
            "completed_count": 0,
            "total_steps": 2,
            "trace": [{"step": 1, "status": "failed", "error": "timeout"}]
        }
        fake_verification_failed = {
            "passed": False,
            "findings": ["Paso 1 falló por timeout."]
        }

        eval_res = CognitiveCritic.evaluate_response(
            response="He completado la tarea con éxito absoluto y sin problemas.",
            query="analizar archivo",
            interlocutor="Sebastian",
            execution=fake_exec_failed,
            verification=fake_verification_failed
        )

        self.assertFalse(eval_res.passed)
        self.assertLess(eval_res.score, 0.70)
        self.assertTrue(any("falló" in f.lower() for f in eval_res.feedback))
