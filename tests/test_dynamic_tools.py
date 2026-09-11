"""
Pruebas de integración para DynamicToolGenerator con seguridad AST en VECTOR 2026.
"""

import unittest
import tempfile
import os
import shutil
from pathlib import Path

from vectorapp.dynamic_tools_generator import DynamicToolGenerator

class TestDynamicToolsSecurityLifecycle(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.generator = DynamicToolGenerator(tools_directory=self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_create_safe_tool_succeeds(self):
        code = """
def execute_tool(action="sumar", **kwargs):
    x = kwargs.get('x', 0)
    y = kwargs.get('y', 0)
    return x + y
"""
        res = self.generator.create_and_validate_tool(
            tool_name="sumar_numeros",
            code=code,
            description="Herramienta matemática para sumar dos números"
        )
        self.assertTrue(res['success'])
        self.assertIn("sumar_numeros", self.generator.created_tools)
        
        # Ejecutar la herramienta recién creada
        exec_res = self.generator.execute_tool("sumar_numeros", {'x': 15, 'y': 25})
        self.assertEqual(exec_res, 40)

    def test_create_dangerous_tool_rejected_by_ast(self):
        code = """
import os
def execute_tool(**kwargs):
    os.system('dir')
    return "hacked"
"""
        res = self.generator.create_and_validate_tool(
            tool_name="bad_os_tool",
            code=code,
            description="Herramienta maliciosa"
        )
        self.assertFalse(res['success'])
        self.assertIn("Violación de seguridad AST", res['error'])
        self.assertNotIn("bad_os_tool", self.generator.created_tools)
        # El archivo no debe existir en disco
        tool_file = Path(self.temp_dir.name) / "bad_os_tool.py"
        self.assertFalse(tool_file.exists())

    def test_create_tool_path_traversal_name_rejected(self):
        code = "def execute_tool(**kwargs): return 'ok'"
        res = self.generator.create_and_validate_tool(
            tool_name="../../escape_tool",
            code=code,
            description="Intento de path traversal en nombre"
        )
        self.assertFalse(res['success'])
        self.assertIn("inválido", res['error'])
        self.assertNotIn("../../escape_tool", self.generator.created_tools)

if __name__ == '__main__':
    unittest.main()
