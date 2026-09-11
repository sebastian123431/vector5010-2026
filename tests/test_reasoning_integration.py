import os
import django

if not os.environ.get("DJANGO_SETTINGS_MODULE"):
    os.environ["DJANGO_SETTINGS_MODULE"] = "vector5010.settings"
    django.setup()

import unittest
from vectorapp.cognition import (
    CognitiveVerifier,
    ReasoningEngine,
    ReasoningMode,
    StepStatus,
)
from vectorapp.query_optimizer import query_optimizer, QueryComplexity, IntentCategory


class TestReasoningIntegrationP1(unittest.TestCase):
    """
    Pruebas exhaustivas para la Fase P1:
    - CognitiveVerifier con ASTSecurityValidator (Python y JS).
    - ReasoningEngine con modos PLAN_ONLY y EXECUTE.
    - Query Router multinivel (Tier 0, Tier 1, Tier 2).
    """

    def setUp(self):
        self.engine = ReasoningEngine()

    def test_verifier_python_valid(self):
        """Valida que código Python seguro y bien formado sea aprobado sin violaciones."""
        code = """
def calcular_area(radio: float) -> float:
    import math
    return math.pi * (radio ** 2)
"""
        res = CognitiveVerifier.verify_code(code, language="python")
        self.assertTrue(res["valid"])
        self.assertTrue(res["syntax_valid"])
        self.assertTrue(res["security_valid"])
        self.assertEqual(len(res["syntax_errors"]), 0)
        self.assertEqual(len(res["violations"]), 0)

    def test_verifier_python_syntax_error(self):
        """Valida que errores de sintaxis Python sean detectados con exactitud."""
        broken_code = "def f(x: return x"
        res = CognitiveVerifier.verify_code(broken_code, language="python")
        self.assertFalse(res["valid"])
        self.assertFalse(res["syntax_valid"])
        self.assertGreaterEqual(len(res["syntax_errors"]), 1)

    def test_verifier_python_security_violations(self):
        """Valida que llamadas y módulos prohibidos generen violaciones de seguridad."""
        exploits = [
            "import os; os.system('echo pwned')",
            "eval('2 + 2')",
            "exec('import sys')",
            "import subprocess; subprocess.run(['ls'])",
        ]
        for exploit in exploits:
            res = CognitiveVerifier.verify_code(exploit, language="python")
            self.assertFalse(res["valid"], f"Exploit no bloqueado: {exploit}")
            self.assertFalse(res["security_valid"])
            self.assertGreaterEqual(len(res["violations"]), 1)

    def test_verifier_javascript_valid_and_invalid(self):
        """Valida análisis sintáctico de JavaScript mediante javascript_engine."""
        good_js = "function add(a, b) { return a + b; }"
        res_good = CognitiveVerifier.verify_code(good_js, language="javascript")
        self.assertTrue(res_good["valid"])

        bad_js = "function add(a, b { return a + b; }"
        res_bad = CognitiveVerifier.verify_code(bad_js, language="javascript")
        self.assertFalse(res_bad["valid"])

    def test_reasoning_mode_plan_only(self):
        """Valida que PLAN_ONLY no ejecute acciones reales (dry_run)."""
        res = self.engine.reason(
            query="analizar proyecto zip con ast",
            interlocutor="Diego",
            mode=ReasoningMode.PLAN_ONLY
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["mode"], "plan_only")
        self.assertIn("plan", res)
        trace = res["execution"]["trace"]
        self.assertTrue(all(t.get("mode") == "dry_run" for t in trace if t.get("status") == "completed"))

    def test_reasoning_mode_execute(self):
        """Valida que EXECUTE corra los pasos supervisados y mida la latencia de cada uno."""
        res = self.engine.reason(
            query="diagnosticar y refactorizar modulo",
            interlocutor="Diego",
            mode=ReasoningMode.EXECUTE
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["mode"], "execute")
        steps = res["plan"]["steps"]
        self.assertGreater(len(steps), 0)
        # Latencia registrada en cada paso
        for step in steps:
            self.assertIn("latency_ms", step)

    def test_query_router_tiers(self):
        """Valida la clasificación por niveles Tier 0, Tier 1 y Tier 2."""
        # Tier 0: Fast path
        r0 = query_optimizer.route_query("hola")
        self.assertEqual(r0.tier, 0)
        self.assertEqual(r0.complexity, QueryComplexity.SIMPLE)

        # Tier 1: Intent normal
        r1 = query_optimizer.route_query("¿Cómo funciona la red neuronal semántica?")
        self.assertIn(r1.tier, (1, 2))

        # Tier 2: Ambigüedad con palabras técnicas
        r2 = query_optimizer.route_query("tengo un bug en el script y no sé si optimizar la variable")
        self.assertIn(r2.tier, (1, 2))
        self.assertIn(r2.route, (IntentCategory.CODING, IntentCategory.REASONING))
