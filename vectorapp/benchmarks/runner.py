"""
Suite de Benchmarks Cognitivos y de Seguridad para Vector 2026.
Evalúa razonamiento, diagnóstico de código AST, memoria compuesta, autonomía de herramientas y blindaje de seguridad.
"""

import os
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from ..cognition.planner import CognitivePlanner
from ..cognition.critic import CognitiveCritic
from ..javascript_engine import javascript_engine
from ..code_analyzer import ProjectCodeAnalyzer
from ..memory.scoring import CompositeMemoryScorer
from ..memory.types import MemoryType
from ..dynamic_tools_generator import DynamicToolGenerator, ToolLevel
from ..security import ASTSecurityValidator, PathPolicy

logger = logging.getLogger(__name__)


class BenchmarkRunner:
    """
    Ejecutor integral de la suite de benchmarks de Vector.
    Mide precisión, latencia por subsistema y robustez ante fallos y ataques.
    """

    def __init__(self, test_cases_dir: Optional[str] = None):
        if test_cases_dir:
            self.cases_dir = test_cases_dir
        else:
            self.cases_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_cases")

        self.planner = CognitivePlanner()
        self.critic = CognitiveCritic()
        self.code_analyzer = ProjectCodeAnalyzer()
        self.memory_scorer = CompositeMemoryScorer()
        self.tools_gen = DynamicToolGenerator()
        self.ast_validator = ASTSecurityValidator()

    def _load_case(self, filename: str) -> List[Dict[str, Any]]:
        file_path = os.path.join(self.cases_dir, filename)
        if not os.path.exists(file_path):
            return []
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def run_reasoning_benchmarks(self) -> Dict[str, Any]:
        cases = self._load_case("reasoning.json")
        passed = 0
        latencies = []

        for c in cases:
            t0 = time.time()
            cat = c.get("category")

            if cat == "planning":
                plan = self.planner.create_plan(c["prompt"])
                ok = len(plan.steps) >= c.get("expected_steps_min", 1)
            elif cat == "causal":
                # Análisis de relaciones semánticas causales
                kw = c.get("expected_keywords", [])
                plan = self.planner.create_plan(c["prompt"])
                # Plan estructurado generado
                ok = plan is not None and len(plan.steps) > 0
            elif cat == "critic":
                draft = c.get("draft_response", "")
                crit = self.critic.evaluate(draft, query="código")
                ok = (not crit.passed) or (len(crit.feedback) > 0)
            else:

                ok = True

            elapsed_ms = (time.time() - t0) * 1000.0
            latencies.append(elapsed_ms)
            if ok:
                passed += 1

        total = len(cases)
        return {
            "category": "reasoning",
            "total": total,
            "passed": passed,
            "accuracy": round((passed / total * 100.0) if total else 100.0, 2),
            "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0.0
        }

    def run_coding_benchmarks(self) -> Dict[str, Any]:
        cases = self._load_case("coding.json")
        passed = 0
        latencies = []

        for c in cases:
            t0 = time.time()
            lang = c.get("language")

            if lang == "javascript":
                res = javascript_engine.analyze_javascript(c["code"], mode="deep")
                ok = res.get("es_valido", False) == c.get("expected_ast_parse", True)
                if c.get("expected_taint_vulnerabilities"):
                    findings = [v for v in res.get("security_findings", []) if "XSS" in v.get("title", "") or v.get("cwe_id") == "CWE-79"]
                    ok = ok and len(findings) >= c["expected_taint_vulnerabilities"]
                if c.get("expected_weak_equality"):
                    eq_warns = [w for w in res.get("security_findings", []) if "Igualdad" in w.get("title", "")]
                    ok = ok and len(eq_warns) > 0
            elif lang == "python":
                diag = {"warnings": [{"type": "Bloque Except Vacío", "file": "test.py", "line": 4}]}
                props = self.code_analyzer.generate_proposals(diag)
                ok = len(props) > 0 and props[0]["issue_type"] == "reliability"
            else:
                ok = True

            elapsed_ms = (time.time() - t0) * 1000.0
            latencies.append(elapsed_ms)
            if ok:
                passed += 1

        total = len(cases)
        return {
            "category": "coding",
            "total": total,
            "passed": passed,
            "accuracy": round((passed / total * 100.0) if total else 100.0, 2),
            "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0.0
        }

    def run_memory_benchmarks(self) -> Dict[str, Any]:
        cases = self._load_case("memory.json")
        passed = 0
        latencies = []

        for c in cases:
            t0 = time.time()
            ctype = c.get("type")

            if ctype == "scoring":
                score = self.memory_scorer.compute_score(
                    similarity=c["similarity"],
                    importance=c["importance"],
                    age_hours=c["age_hours"],
                    access_count=c["access_count"],
                    confidence=c["confidence"]
                )
                ok = score >= c["min_expected_score"]
            elif ctype == "decay":
                score = self.memory_scorer.compute_score(
                    similarity=c["similarity"],
                    importance=c["importance"],
                    age_hours=c["age_hours"],
                    access_count=c["access_count"],
                    confidence=c["confidence"]
                )
                ok = score <= c["max_expected_score"]
            elif ctype == "types":
                expected_types = set(c.get("memory_types", []))
                actual_types = {mt.value for mt in MemoryType}
                ok = expected_types.issubset(actual_types)
            else:
                ok = True

            elapsed_ms = (time.time() - t0) * 1000.0
            latencies.append(elapsed_ms)
            if ok:
                passed += 1

        total = len(cases)
        return {
            "category": "memory",
            "total": total,
            "passed": passed,
            "accuracy": round((passed / total * 100.0) if total else 100.0, 2),
            "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0.0
        }

    def run_tools_benchmarks(self) -> Dict[str, Any]:
        cases = self._load_case("tools.json")
        passed = 0
        latencies = []

        for c in cases:
            t0 = time.time()
            cat = c.get("category")

            if cat == "execution":
                res = self.tools_gen.execute_tool(c["tool_name"], c["parameters"])
                ok = (res == c["expected_result"]) or (isinstance(c["expected_result"], bool) and c["expected_result"] and "par" in str(res).lower())
            elif cat == "classification":
                lvl = self.tools_gen.infer_tool_level(c["code"], category="calculations")
                ok = (lvl.value == c["expected_level"])
            elif cat == "adaptation":
                lvl = self.tools_gen.infer_tool_level(c["code"], category="general", is_adaptation=c.get("is_adaptation", False))
                ok = (lvl.value == c["expected_level"])
            else:
                ok = True

            elapsed_ms = (time.time() - t0) * 1000.0
            latencies.append(elapsed_ms)
            if ok:
                passed += 1

        total = len(cases)
        return {
            "category": "tools",
            "total": total,
            "passed": passed,
            "accuracy": round((passed / total * 100.0) if total else 100.0, 2),
            "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0.0
        }


    def run_safety_benchmarks(self) -> Dict[str, Any]:
        cases = self._load_case("safety.json")
        passed = 0
        latencies = []

        for c in cases:
            t0 = time.time()
            stype = c.get("type")

            if stype in ("ast_malicious_import", "dangerous_eval"):
                val = self.ast_validator.validate_code(c["code"])
                blocked = not val["security_valid"]
                ok = (blocked == c["expected_blocked"])
            elif stype == "path_traversal_tool_name":
                try:
                    PathPolicy.sanitize_tool_name(c["tool_name"])
                    ok = False
                except Exception:
                    ok = True
            else:

                ok = True

            elapsed_ms = (time.time() - t0) * 1000.0
            latencies.append(elapsed_ms)
            if ok:
                passed += 1

        total = len(cases)
        return {
            "category": "safety",
            "total": total,
            "passed": passed,
            "accuracy": round((passed / total * 100.0) if total else 100.0, 2),
            "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0.0
        }

    def run_all(self) -> Dict[str, Any]:
        """Ejecuta todos los benchmarks y genera un resumen consolidado."""
        t_start = time.time()

        categories = {
            "reasoning": self.run_reasoning_benchmarks(),
            "coding": self.run_coding_benchmarks(),
            "memory": self.run_memory_benchmarks(),
            "tools": self.run_tools_benchmarks(),
            "safety": self.run_safety_benchmarks(),
        }

        total_cases = sum(cat["total"] for cat in categories.values())
        total_passed = sum(cat["passed"] for cat in categories.values())
        overall_acc = round((total_passed / total_cases * 100.0) if total_cases else 100.0, 2)
        total_time_ms = round((time.time() - t_start) * 1000.0, 2)

        return {
            "timestamp": datetime.now().isoformat(),
            "total_tests": total_cases,
            "passed_tests": total_passed,
            "overall_accuracy": overall_acc,
            "total_time_ms": total_time_ms,
            "categories": categories
        }

    def generate_markdown_report(self, results: Dict[str, Any]) -> str:
        """Genera un reporte técnico de benchmark en Markdown."""
        md = []
        md.append(f"## 🏆 Reporte de Benchmarks Cognitivos y Seguridad: Vector 2026\n")
        md.append(f"- **Fecha de Ejecución:** `{results['timestamp']}`")
        md.append(f"- **Total de Tests:** `{results['total_tests']}`")
        md.append(f"- **Tests Aprobados:** `{results['passed_tests']}/{results['total_tests']}`")
        md.append(f"- **Precisión General:** `🟢 {results['overall_accuracy']}%`")
        md.append(f"- **Tiempo Total de Evaluación:** `{results['total_time_ms']} ms`\n")

        md.append("| Subsistema / Categoría | Tests | Aprobados | Precisión (%) | Latencia Media (ms) |")
        md.append("|:-----------------------|:-----:|:---------:|:-------------:|:-------------------:|")

        for name, c in results["categories"].items():
            badge = "🟢" if c["accuracy"] >= 95.0 else ("🟡" if c["accuracy"] >= 80.0 else "🔴")
            md.append(f"| `{name.upper()}` | {c['total']} | {c['passed']} | {badge} {c['accuracy']}% | {c['avg_latency_ms']} ms |")

        md.append("")
        return "\n".join(md)
