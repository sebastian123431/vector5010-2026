"""
Pruebas unitarias para SandboxPolicy y ToolRunner en VECTOR 2026.
"""

import unittest
import tempfile
import os
from pathlib import Path

from vectorapp.security.sandbox_policy import ToolRunner, SandboxPolicy

class TestToolSandbox(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.policy = SandboxPolicy(timeout=2, max_output_bytes=5000, workspace_dir=self.temp_dir.name)
        self.runner = ToolRunner(self.policy)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_run_valid_tool(self):
        tool_code = """
def execute_tool(action="add", **kwargs):
    a = kwargs.get('a', 0)
    b = kwargs.get('b', 0)
    return a + b
"""
        tool_file = Path(self.temp_dir.name) / "tool_add.py"
        with open(tool_file, 'w', encoding='utf-8') as f:
            f.write(tool_code)

        result = self.runner.run_tool(
            tool_name="tool_add",
            tool_file=str(tool_file),
            parameters={'a': 10, 'b': 25}
        )
        self.assertTrue(result.success)
        self.assertEqual(result.result, 35)
        self.assertIsNone(result.error)

    def test_timeout_on_infinite_loop(self):
        tool_code = """
import time
def execute_tool(**kwargs):
    while True:
        time.sleep(0.1)
"""
        tool_file = Path(self.temp_dir.name) / "tool_loop.py"
        with open(tool_file, 'w', encoding='utf-8') as f:
            f.write(tool_code)

        result = self.runner.run_tool(
            tool_name="tool_loop",
            tool_file=str(tool_file),
            timeout=1  # 1 segundo de timeout
        )
        self.assertFalse(result.success)
        self.assertIn("Timeout", str(result.error))

    def test_output_limit_protection(self):
        tool_code = """
def execute_tool(**kwargs):
    return "A" * 10000
"""
        tool_file = Path(self.temp_dir.name) / "tool_flood.py"
        with open(tool_file, 'w', encoding='utf-8') as f:
            f.write(tool_code)

        result = self.runner.run_tool(
            tool_name="tool_flood",
            tool_file=str(tool_file)
        )
        # El límite es 5000 bytes, el resultado impreso supera los 10000 bytes
        self.assertFalse(result.success)
        self.assertTrue(result.output_truncated or "ResourceLimit" in str(result.error))

    def test_nonexistent_tool_file(self):
        result = self.runner.run_tool(
            tool_name="tool_fake",
            tool_file=os.path.join(self.temp_dir.name, "does_not_exist.py")
        )
        self.assertFalse(result.success)
        self.assertIn("no existe", str(result.error))

if __name__ == '__main__':
    unittest.main()
