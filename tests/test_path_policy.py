"""
Pruebas unitarias para PathPolicy en VECTOR 2026.
"""

import unittest
from pathlib import Path
from vectorapp.security.path_policy import PathPolicy
from vectorapp.security.exceptions import PathTraversalViolation

class TestPathPolicy(unittest.TestCase):
    def setUp(self):
        self.policy = PathPolicy()

    def test_safe_path_inside_workspace(self):
        resolved = self.policy.resolve_safe_path("data.txt")
        self.assertTrue(resolved.is_relative_to(self.policy.workspace_dir))
        self.assertEqual(resolved.name, "data.txt")

    def test_blocks_parent_traversal(self):
        with self.assertRaises(PathTraversalViolation):
            self.policy.resolve_safe_path("../../secret.py")

    def test_blocks_absolute_drive_traversal(self):
        with self.assertRaises(PathTraversalViolation):
            self.policy.resolve_safe_path("C:\\Windows\\System32\\calc.exe")

    def test_blocks_null_byte(self):
        with self.assertRaises(PathTraversalViolation):
            self.policy.resolve_safe_path("archivo.txt\0.exe")

    def test_sanitize_valid_tool_name(self):
        self.assertEqual(PathPolicy.sanitize_tool_name("mi_herramienta_1"), "mi_herramienta_1")
        self.assertEqual(PathPolicy.sanitize_tool_name("calcular_stats"), "calcular_stats")

    def test_sanitize_tool_name_rejects_traversal(self):
        with self.assertRaises(PathTraversalViolation):
            PathPolicy.sanitize_tool_name("../../bad_tool")

    def test_sanitize_tool_name_rejects_special_chars(self):
        with self.assertRaises(PathTraversalViolation):
            PathPolicy.sanitize_tool_name("tool;rm -rf")

if __name__ == '__main__':
    unittest.main()
