"""
Pruebas automatizadas para el Motor de Inteligencia de JavaScript y TypeScript (Fase P1).
Valida parsing Tree-sitter, cálculo de complejidad ciclomática, análisis de flujo de taint,
detección de vulnerabilidades (XSS, eval, prototype pollution) y auto-reparación.
"""

import unittest
from vectorapp.javascript_engine import javascript_engine, QuickScanner
from vectorapp.code_intelligence import (
    TreeSitterJSParser, TreeSitterTSParser, SecurityRuleChecker, TaintAnalysisEngine
)


class TestJavaScriptEngineP1(unittest.TestCase):

    def setUp(self):
        self.engine = javascript_engine
        self.js_parser = TreeSitterJSParser()
        self.ts_parser = TreeSitterTSParser()

    def test_tree_sitter_js_parsing_complete(self):
        """Valida que Tree-sitter JS extraiga funciones, clases, imports y métricas."""
        code = """
        import { useState, useEffect } from 'react';

        class UserManager extends BaseManager {
            constructor(name) {
                this.name = name;
            }
            async fetchUserData(id) {
                const res = await api.get('/user/' + id);
                return res.data;
            }
        }

        const helperArrow = (x, y = 10) => {
            if (x > 0) {
                return x * y;
            }
            return 0;
        };
        """
        res = self.js_parser.parse(code, filename="user.js")
        self.assertTrue(res["success"])
        self.assertFalse(res["has_syntax_errors"])
        self.assertEqual(len(res["classes"]), 1)
        self.assertEqual(res["classes"][0]["nombre"], "UserManager")
        self.assertEqual(res["classes"][0]["hereda_de"], "BaseManager")
        self.assertGreaterEqual(len(res["functions"]), 1)
        self.assertGreaterEqual(len(res["imports"]), 1)
        self.assertGreaterEqual(res["metrics"]["cyclomatic_complexity"], 2)

    def test_tree_sitter_syntax_error_detection(self):
        """Verifica que errores de sintaxis reales sean detectados en el AST."""
        broken_code = "function broken(a, b { return a + ; }"
        res = self.js_parser.parse(broken_code, filename="broken.js")
        self.assertTrue(res["has_syntax_errors"])
        self.assertGreaterEqual(len(res["syntax_errors"]), 1)

    def test_tree_sitter_ts_interfaces_and_types(self):
        """Valida extracción de interfaces y alias de tipo en TypeScript."""
        ts_code = """
        interface UserProfile {
            id: number;
            username: string;
            role?: string;
        }

        type ID = string | number;

        enum Status {
            ACTIVE = 1,
            INACTIVE = 0
        }

        function getUser(id: ID): UserProfile {
            return { id: 1, username: 'test' };
        }
        """
        res = self.ts_parser.parse(ts_code, filename="user.ts")
        self.assertTrue(res["success"])
        self.assertEqual(len(res["interfaces"]), 1)
        self.assertEqual(res["interfaces"][0]["name"], "UserProfile")
        self.assertEqual(len(res["type_aliases"]), 1)
        self.assertEqual(res["type_aliases"][0]["name"], "ID")
        self.assertEqual(len(res["enums"]), 1)
        self.assertEqual(res["enums"][0]["name"], "Status")

    def test_dom_xss_and_taint_detection(self):
        """Verifica detección de DOM XSS mediante flujo de taint (source -> sink)."""
        xss_code = """
        const userQuery = location.search;
        const target = document.getElementById('output');
        target.innerHTML = userQuery;
        """
        res = self.js_parser.parse(xss_code, filename="xss.js")
        findings = res["security_findings"]
        xss_findings = [f for f in findings if f["rule_id"] == "JS-SEC-003"]
        self.assertGreaterEqual(len(xss_findings), 1)
        self.assertEqual(xss_findings[0]["severity"], "critical")
        self.assertIn("location.search", str(xss_findings[0].get("source")))

    def test_eval_code_injection_detection(self):
        """Verifica detección de llamadas críticas a eval() o new Function()."""
        code = "const calc = eval(userInput); const fn = new Function('a', 'return a * 2');"
        res = self.js_parser.parse(code, filename="eval.js")
        findings = res["security_findings"]
        rule_ids = [f["rule_id"] for f in findings]
        self.assertIn("JS-SEC-001", rule_ids)
        self.assertIn("JS-SEC-002", rule_ids)

    def test_prototype_pollution_detection(self):
        """Verifica detección de accesos a __proto__."""
        code = "obj.__proto__.polluted = true;"
        res = self.js_parser.parse(code, filename="pollution.js")
        findings = res["security_findings"]
        self.assertTrue(any(f["rule_id"] == "JS-SEC-004" for f in findings))

    def test_unified_analyze_javascript(self):
        """Valida que analyze_javascript devuelva métricas AST y mantenga retrocompatibilidad."""
        code = """
        function calculateTotal(items) {
            var total = 0;
            for (let i = 0; i < items.length; i++) {
                if (items[i].price == 0) continue;
                total += items[i].price;
            }
            return total;
        }
        """
        res = self.engine.analyze_javascript(code, filename="cart.js", mode="auto")
        self.assertTrue(res["success"])
        self.assertTrue(res["ast_available"])
        self.assertEqual(res["mode"], "deep")
        self.assertIn("complexity_metrics", res)
        self.assertGreaterEqual(res["complexity_metrics"]["cyclomatic_complexity"], 2)

    def test_repair_javascript_code(self):
        """Valida que el motor auto-repare delimitadores, var y operadores débiles."""
        broken = "function test() { var a = 1 == 2; document.getElementById('x').value;"
        res = self.engine.reparar_codigo_js(broken)
        self.assertTrue(res["success"])
        self.assertTrue(res["es_valido"])
        repaired = res["codigo_reparado"]
        self.assertIn("let a =", repaired)
        self.assertIn("===", repaired)
        self.assertIn("?.", repaired)

    def test_technical_report_generation(self):
        """Valida que generar_reporte_tecnico genere informe estructurado."""
        code = "function hello() { return 'world'; }"
        analysis = self.engine.analizar_codigo_js(code)
        report = self.engine.generar_reporte_tecnico(analysis)
        self.assertIn("ANÁLISIS TÉCNICO PROFUNDO DE JAVASCRIPT", report)
        self.assertIn("hello", report)


if __name__ == "__main__":
    unittest.main()
