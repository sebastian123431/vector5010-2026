"""
Pruebas exhaustivas para:
1. Sanitización de project_name en extracción de ZIP (bloqueo de ../../escape).
2. Unificación de _run_bounded_process en ToolRunner (run_tool y run_test_file) con cuota incremental y timeout.
3. PendingActionManager (confirmación de acciones de alto impacto con UUID, consumo único y expiración).
"""

import unittest
import os
import sys
import tempfile
import time
from pathlib import Path

from vectorapp.code_analyzer import sanitize_project_name, ProjectCodeAnalyzer
from vectorapp.security.exceptions import PathTraversalViolation
from vectorapp.security.sandbox_policy import ToolRunner, SandboxSecurityPolicy
from vectorapp.security.action_policy import PendingActionManager


class TestSandboxAndProjectSanitizationP1(unittest.TestCase):

    def test_sanitize_project_name_valid(self):
        """Nombres seguros y alfanuméricos deben ser aceptados."""
        self.assertEqual(sanitize_project_name("mi_proyecto"), "mi_proyecto")
        self.assertEqual(sanitize_project_name("project-123_test"), "project-123_test")
        self.assertEqual(sanitize_project_name("SistemaV1"), "SistemaV1")

    def test_sanitize_project_name_traversal_attempts_fail(self):
        """Cualquier intento de path traversal debe lanzar PathTraversalViolation."""
        traversal_cases = [
            "../../escape",
            "../escape",
            "/etc/passwd",
            "C:\\Windows\\System32",
            "project/subfolder",
            "project\\subfolder",
            "test:name",
            "..",
            "foo/../bar",
            "test;rm -rf /",
        ]
        for bad_name in traversal_cases:
            with self.subTest(bad_name=bad_name):
                with self.assertRaises(PathTraversalViolation):
                    sanitize_project_name(bad_name)

    def test_extract_zip_with_traversal_project_name_raises(self):
        """extract_zip con project_name='../../escape' debe fallar."""
        analyzer = ProjectCodeAnalyzer()
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tf:
            tf_path = tf.name
        try:
            import zipfile
            with zipfile.ZipFile(tf_path, 'w') as zf:
                zf.writestr("test.txt", "contenido inocuo")
            
            with self.assertRaises(PathTraversalViolation):
                analyzer.extract_zip(tf_path, project_name="../../escape")
        finally:
            if os.path.exists(tf_path):
                os.remove(tf_path)

    def test_tool_runner_run_test_file_bounded_process(self):
        """run_test_file debe utilizar _run_bounded_process con cuota y timeout."""
        runner = ToolRunner()

        # 1. Prueba que pasa normalmente
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write("print('UNIT TEST PASS')\n")
            f_path = f.name
        try:
            res = runner.run_test_file(f_path, timeout=5)
            self.assertTrue(res.success)
            self.assertIn("UNIT TEST PASS", res.result)
        finally:
            if os.path.exists(f_path):
                os.remove(f_path)

        # 2. Prueba que produce un fallo (código de retorno != 0)
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write("import sys; sys.stderr.write('FAILURE'); sys.exit(1)\n")
            f_path = f.name
        try:
            res = runner.run_test_file(f_path, timeout=5)
            self.assertFalse(res.success)
            self.assertIn("Fallo en pruebas unitarias", res.error)
        finally:
            if os.path.exists(f_path):
                os.remove(f_path)

        # 3. Prueba que excede timeout
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write("import time; time.sleep(10)\n")
            f_path = f.name
        try:
            res = runner.run_test_file(f_path, timeout=1)
            self.assertFalse(res.success)
            self.assertIn("[Timeout]", res.error)
        finally:
            if os.path.exists(f_path):
                os.remove(f_path)

    def test_pending_action_manager_single_use_and_consumption(self):
        """Valida que una acción confirmada solo se pueda ejecutar UNA sola vez."""
        mgr = PendingActionManager(ttl_seconds=10)
        action_id = mgr.create_action("delete_tool", {"tool_name": "old_tool"})

        self.assertIsNotNone(action_id)
        # Validación correcta
        is_valid, err = mgr.validate_and_consume(action_id, "delete_tool", {"tool_name": "old_tool"})
        self.assertTrue(is_valid)
        self.assertIsNone(err)

        # Reintento: debe fallar porque consumed=True
        is_valid2, err2 = mgr.validate_and_consume(action_id, "delete_tool", {"tool_name": "old_tool"})
        self.assertFalse(is_valid2)
        self.assertIn("ya fue ejecutada", err2)

    def test_pending_action_manager_parameter_mismatch(self):
        """Si los parámetros difieren del hash registrado, la acción debe ser rechazada."""
        mgr = PendingActionManager(ttl_seconds=10)
        action_id = mgr.create_action("execute_query", {"query": "SELECT 1"})

        is_valid, err = mgr.validate_and_consume(action_id, "execute_query", {"query": "DROP TABLE users"})
        self.assertFalse(is_valid)
        self.assertIn("no coinciden", err)


if __name__ == "__main__":
    unittest.main()
