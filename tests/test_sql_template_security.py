"""
Pruebas unitarias para la plantilla segura de base de datos SQL en VECTOR 2026.
"""

import unittest
import tempfile
import os
import json
from pathlib import Path

from vectorapp.dynamic_tools_generator import DynamicToolGenerator

class TestSQLTemplateSecurity(unittest.TestCase):
    def setUp(self):
        self.generator = DynamicToolGenerator()
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_database_template_rejects_sql_injection_table_name(self):
        code = self.generator._generate_database_tool_template({})
        tool_file = Path(self.temp_dir.name) / "tool_db.py"
        with open(tool_file, 'w', encoding='utf-8') as f:
            f.write(code)

        result = self.generator.sandbox_runner.run_tool(
            tool_name="tool_db",
            tool_file=str(tool_file),
            action="create_table",
            parameters={
                'table_name': 'usuarios; DROP TABLE test;',
                'columns': {'id': 'INTEGER PRIMARY KEY'}
            }
        )
        self.assertTrue(result.success)
        self.assertIn("Error: Nombre de tabla inválido", str(result.result))

    def test_database_template_executes_safe_filters(self):
        code = self.generator._generate_database_tool_template({})
        tool_file = Path(self.temp_dir.name) / "tool_db.py"
        with open(tool_file, 'w', encoding='utf-8') as f:
            f.write(code)

        import time
        db_file = f"test_{int(time.time() * 1000)}.db"

        # 1. Crear tabla legítima
        res_create = self.generator.sandbox_runner.run_tool(
            tool_name="tool_db",
            tool_file=str(tool_file),
            action="create_table",
            parameters={'db_path': db_file, 'table_name': 'personas', 'columns': {'id': 'INTEGER PRIMARY KEY', 'edad': 'INTEGER', 'nombre': 'TEXT'}}
        )
        self.assertTrue(res_create.success)
        self.assertIn("creada exitosamente", str(res_create.result))

        # 2. Insertar datos parametrizados
        res_insert1 = self.generator.sandbox_runner.run_tool(
            tool_name="tool_db",
            tool_file=str(tool_file),
            action="insert_data",
            parameters={'db_path': db_file, 'table_name': 'personas', 'data': {'edad': 25, 'nombre': 'Sebastian'}}
        )
        self.assertTrue(res_insert1.success)

        res_insert2 = self.generator.sandbox_runner.run_tool(
            tool_name="tool_db",
            tool_file=str(tool_file),
            action="insert_data",
            parameters={'db_path': db_file, 'table_name': 'personas', 'data': {'edad': 15, 'nombre': 'Menor'}}
        )
        self.assertTrue(res_insert2.success)

        # 3. Filtrar datos con operador estructurado
        res_select = self.generator.sandbox_runner.run_tool(
            tool_name="tool_db",
            tool_file=str(tool_file),
            action="select_data",
            parameters={'db_path': db_file, 'table_name': 'personas', 'filters': {'edad': {'operator': '>', 'value': 18}}}
        )
        self.assertTrue(res_select.success)
        data = res_select.result
        self.assertEqual(data.get('count'), 1)

    def test_database_template_rejects_unauthorized_operator(self):
        code = self.generator._generate_database_tool_template({})
        tool_file = Path(self.temp_dir.name) / "tool_db.py"
        with open(tool_file, 'w', encoding='utf-8') as f:
            f.write(code)

        db_file = os.path.join(self.temp_dir.name, "test.db")
        res = self.generator.sandbox_runner.run_tool(
            tool_name="tool_db",
            tool_file=str(tool_file),
            action="select_data",
            parameters={'db_path': db_file, 'table_name': 'personas', 'filters': {'edad': {'operator': 'EXEC', 'value': 18}}}
        )
        self.assertTrue(res.success)
        self.assertIn("Operador no permitido", str(res.result))

if __name__ == '__main__':
    unittest.main()
