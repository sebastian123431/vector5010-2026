"""
Pruebas para la Fase P3: Autonomía Controlada - Analizador de Código y Grafo de Impacto.
"""

import os
import unittest
from vectorapp.code_analyzer import (
    CallGraph,
    ProposalType,
    ImprovementProposal,
    ProjectCodeAnalyzer
)


class TestCodeAnalyzerP3(unittest.TestCase):
    """Pruebas unitarias para las capacidades de análisis de impacto y propuestas."""

    def setUp(self):
        self.call_graph = CallGraph()
        self.analyzer = ProjectCodeAnalyzer()

    def test_call_graph_direct_calls(self):
        """Verifica el registro bidireccional entre caller y callee."""
        self.call_graph.add_call("controller_view", "process_order", "views.py")
        self.call_graph.add_call("process_order", "calculate_tax", "services.py")

        self.assertIn("process_order", self.call_graph.callees["controller_view"])
        self.assertIn("controller_view", self.call_graph.callers["process_order"])
        self.assertIn("process_order", self.call_graph.callers["calculate_tax"])

    def test_call_graph_impact_analysis(self):
        """Verifica el cálculo recursivo del radio de impacto ante modificaciones."""
        self.call_graph.add_call("view_a", "helper_func", "views.py")
        self.call_graph.add_call("view_b", "helper_func", "views.py")
        self.call_graph.add_call("helper_func", "low_level_util", "utils.py")

        # Si modificamos low_level_util, debe impactar helper_func, view_a y view_b
        impact = self.call_graph.impact_analysis("low_level_util")
        self.assertEqual(impact["target"], "low_level_util")
        self.assertIn("helper_func", impact["direct_callers"])
        self.assertIn("view_a", impact["total_impacted_callers"])
        self.assertIn("view_b", impact["total_impacted_callers"])
        self.assertIn("views.py", impact["impacted_files"])

    def test_module_dependencies_tracking(self):
        """Verifica el registro de dependencias entre módulos."""
        self.call_graph.add_dependency("vectorapp.views", "vectorapp.code_analyzer")
        self.call_graph.add_dependency("vectorapp.views", "vectorapp.query_optimizer")

        deps = self.call_graph.module_deps["vectorapp.views"]
        self.assertIn("vectorapp.code_analyzer", deps)
        self.assertIn("vectorapp.query_optimizer", deps)

    def test_improvement_proposals_generation(self):
        """Verifica la generación de propuestas estructuradas basadas en diagnósticos AST."""
        fake_diagnosis = {
            "warnings": [
                {
                    "file": "legacy/module.py",
                    "line": 42,
                    "type": "Bloque Except Vacío",
                    "message": "Captura silenciosa de excepciones generales ('except:') que puede ocultar fallos graves."
                },
                {
                    "file": "legacy/unsafe.py",
                    "line": 105,
                    "type": "Riesgo de Seguridad",
                    "message": "Uso potencialmente inseguro de eval() para ejecutar código dinámico."
                }
            ]
        }

        proposals = self.analyzer.generate_proposals(fake_diagnosis)
        self.assertEqual(len(proposals), 2)

        # Propuesta 1: Reliability para except vacío
        p1 = proposals[0]
        self.assertEqual(p1["issue_type"], ProposalType.RELIABILITY.value)
        self.assertIn("legacy/module.py", p1["target_file"])
        self.assertIn("except Exception", p1["diff_preview"])

        # Propuesta 2: Security para eval
        p2 = proposals[1]
        self.assertEqual(p2["issue_type"], ProposalType.SECURITY.value)
        self.assertIn("legacy/unsafe.py", p2["target_file"])
        self.assertIn("eval", p2["diff_preview"])

    def test_improvement_proposal_serialization(self):
        """Valida que la dataclass ImprovementProposal se serialice correctamente a dict."""
        prop = ImprovementProposal(
            proposal_id="PROP-999",
            target_file="test.py",
            target_symbol="calculate_risk",
            issue_type=ProposalType.PERFORMANCE,
            description="Optimizar algoritmo O(n^2)",
            diff_preview="+ pass"
        )
        d = prop.to_dict()
        self.assertEqual(d["proposal_id"], "PROP-999")
        self.assertEqual(d["issue_type"], "performance")
        self.assertEqual(d["status"], "pending_review")
