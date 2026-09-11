"""
Pruebas para la Fase P3: Autonomía Controlada - Niveles de Herramientas y Auto-Testing.
"""

import os
import shutil
import unittest
from vectorapp.dynamic_tools_generator import DynamicToolGenerator, ToolLevel
from vectorapp.security import ToolPermissions


class TestToolAutonomyP3(unittest.TestCase):
    """Pruebas unitarias para la jerarquía de herramientas dinámicas y auto-validación con pruebas."""

    def setUp(self):
        self.generator = DynamicToolGenerator()
        self.cleanup_tools = []

    def tearDown(self):
        for tool_name in self.cleanup_tools:
            try:
                self.generator.delete_tool(tool_name)
            except Exception:
                pass
            test_path = os.path.join(self.generator.tests_path, f"test_{tool_name}.py")
            if os.path.exists(test_path):
                try:
                    os.remove(test_path)
                except Exception:
                    pass

    def test_tool_level_enum(self):
        """Valida que los niveles de herramientas estén definidos correctamente."""
        self.assertEqual(ToolLevel.LEVEL_A.value, "level_a")
        self.assertEqual(ToolLevel.LEVEL_B.value, "level_b")
        self.assertEqual(ToolLevel.LEVEL_C.value, "level_c")

    def test_infer_tool_level(self):
        """Verifica la inferencia automática del nivel de autonomía según el código y categoría."""
        # Nivel A: Adaptación
        self.assertEqual(
            self.generator.infer_tool_level("def run(): pass", category="general", is_adaptation=True),
            ToolLevel.LEVEL_A
        )

        # Nivel B: Plantilla estructurada de cálculo
        calc_template_code = "def execute_tool(action='calculate', **kwargs):\n    return kwargs"
        self.assertEqual(
            self.generator.infer_tool_level(calc_template_code, category="calculations"),
            ToolLevel.LEVEL_B
        )

        # Nivel C: Código personalizado
        custom_code = "def custom_pipeline(data):\n    return [x * 2 for x in data]"
        self.assertEqual(
            self.generator.infer_tool_level(custom_code, category="general"),
            ToolLevel.LEVEL_C
        )

    def test_generate_tool_unit_test(self):
        """Verifica la generación de código de prueba unitaria para una herramienta."""
        tool_code = "def sumar(a=1, b=2):\n    return a + b"
        test_script = self.generator.generate_tool_unit_test("sumar", tool_code, "calculations")

        self.assertIn("import unittest", test_script)
        self.assertIn("class Test_sumar(unittest.TestCase):", test_script)
        self.assertIn("test_01_module_integrity", test_script)
        self.assertIn("test_02_execution_smoke", test_script)

    def test_create_and_validate_tool_with_auto_test_success(self):
        """Verifica que una herramienta válida genere su test unitario, lo pase y se registre."""
        tool_name = "test_autonomy_multiplier"
        self.cleanup_tools.append(tool_name)

        tool_code = """
def test_autonomy_multiplier(x=2, y=3):
    return x * y
"""
        res = self.generator.create_and_validate_tool(
            tool_name=tool_name,
            code=tool_code,
            description="Herramienta de prueba unitaria para multiplicación",
            tool_level=ToolLevel.LEVEL_C
        )

        self.assertTrue(res.get("success"), f"Fallo al crear herramienta: {res.get('error')}")
        self.assertEqual(res.get("test_status"), "passed")
        self.assertEqual(res.get("tool_level"), "level_c")

        # Verificar que el archivo de test existe en disco
        test_file = os.path.join(self.generator.tests_path, f"test_{tool_name}.py")
        self.assertTrue(os.path.exists(test_file))

        # Verificar que la herramienta está activa en el registro
        tool_info = self.generator.get_tool_info(tool_name)
        self.assertIsNotNone(tool_info)
        self.assertEqual(tool_info.get("test_status"), "passed")

        # Probar ejecución funcional en sandbox
        exec_res = self.generator.execute_tool(tool_name, {"x": 4, "y": 5})
        self.assertEqual(exec_res, 20)

    def test_create_and_validate_tool_rollback_on_broken_test(self):
        """Verifica que si la herramienta falla su prueba de humo, se aplique rollback completo."""
        tool_name = "test_broken_tool"
        self.cleanup_tools.append(tool_name)

        # Código que pasa AST estático pero falla al ejecutarse (división por cero obligatoria)
        broken_code = """
def test_broken_tool():
    return 1 / 0
"""
        res = self.generator.create_and_validate_tool(
            tool_name=tool_name,
            code=broken_code,
            description="Herramienta con fallo en tiempo de ejecución"
        )

        self.assertFalse(res.get("success"))
        self.assertEqual(res.get("test_status"), "failed")

        # Verificar que el archivo de la herramienta fue eliminado por rollback
        tool_file = os.path.join(self.generator.tools_path, f"{tool_name}.py")
        self.assertFalse(os.path.exists(tool_file))

        # Verificar que no quedó registrada en created_tools
        self.assertNotIn(tool_name, self.generator.created_tools)
