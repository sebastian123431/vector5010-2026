"""
Pruebas automatizadas para el Pipeline de Razonamiento Cognitivo (Fase P2).
Valida CognitivePlanner, PlanExecutor, CognitiveCritic, CognitiveVerifier y ReasoningEngine.
"""

import unittest
from vectorapp.cognition import (
    CognitivePlanner, PlanExecutor, CognitiveCritic,
    CognitiveVerifier, ReasoningEngine, StepStatus
)


class TestCognitionPipelineP2(unittest.TestCase):

    def test_planner_zip_project_analysis(self):
        """Valida que metas de análisis de proyectos generen planes intensivos con dependencias."""
        plan = CognitivePlanner.create_plan("analizar proyecto zip completo con ast")
        self.assertEqual(plan.estimated_complexity, "intensive")
        self.assertGreaterEqual(len(plan.steps), 3)
        self.assertIn(1, plan.steps[1].dependencies)

    def test_executor_dependencies_and_dry_run(self):
        """Valida que PlanExecutor respete dependencias y complete dry-runs."""
        plan = CognitivePlanner.create_plan("investigar sobre meteorología en chile")
        executor = PlanExecutor()
        res = executor.execute_plan(plan, dry_run=True)
        self.assertTrue(res["success"])
        self.assertEqual(res["completed_count"], len(plan.steps))
        self.assertTrue(all(s.status == StepStatus.COMPLETED for s in plan.steps))

    def test_critic_flags_self_greeting(self):
        """Valida que el crítico penalice auto-saludos absurdos ('Hola Vector')."""
        bad_response = "Hola Vector, hoy vamos a revisar el sistema."
        eval_res = CognitiveCritic.evaluate_response(bad_response, interlocutor="Sebastian")
        self.assertFalse(eval_res.passed)
        self.assertLess(eval_res.score, 0.70)
        self.assertTrue(any("se saludó a sí mismo" in f for f in eval_res.feedback))

    def test_critic_flags_unbalanced_code_blocks(self):
        """Valida que el crítico detecte bloques de código sin cerrar."""
        bad_code_response = "Aquí está tu código:\n```python\nprint('hello')\n"
        eval_res = CognitiveCritic.evaluate_response(bad_code_response, interlocutor="Sebastian")
        self.assertTrue(any("desbalanceados" in f for f in eval_res.feedback))

    def test_verifier_safety_destructive_commands(self):
        """Valida que el verificador detecte y bloquee comandos destructivos."""
        safe_res = CognitiveVerifier.verify_safety("calcular la probabilidad de lluvia")
        self.assertTrue(safe_res["safe"])

        danger_res = CognitiveVerifier.verify_safety("ejecutar rm -rf / en el servidor")
        self.assertFalse(danger_res["safe"])
        self.assertGreaterEqual(len(danger_res["violations"]), 1)

    def test_reasoning_engine_full_loop(self):
        """Valida el ciclo de razonamiento completo."""
        engine = ReasoningEngine()
        result = engine.reason(
            query="analizar el archivo de configuración del proyecto",
            interlocutor="Sebastian",
            draft_response="He analizado el archivo de configuración y los parámetros son correctos."
        )
        self.assertTrue(result["success"])
        self.assertTrue(result["approved"])
        self.assertIn("plan", result)
        self.assertIn("critic", result)


if __name__ == "__main__":
    unittest.main()
