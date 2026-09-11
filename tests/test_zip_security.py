"""
Pruebas unitarias para la protección contra Zip Bombs y Zip Slip en VECTOR 2026.
"""

import unittest
import tempfile
import os
import zipfile
import io

from vectorapp.code_analyzer import ProjectCodeAnalyzer
from vectorapp.security.exceptions import ZipBombViolation

class TestZipSecurity(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.analyzer = ProjectCodeAnalyzer(workspace_dir=self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_safe_zip_extraction(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as zf:
            zf.writestr('app/main.py', 'print("Hola mundo")')
            zf.writestr('app/utils.py', 'def helper(): return True')
        buf.seek(0)

        result = self.analyzer.extract_zip(buf, project_name="proyecto_seguro")
        self.assertEqual(result['extracted_count'], 2)
        self.assertTrue(os.path.exists(result['project_dir']))

    def test_zip_slip_protection(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as zf:
            zf.writestr('../../evil.txt', 'malicious content')
            zf.writestr('safe.py', 'print("safe")')
        buf.seek(0)

        result = self.analyzer.extract_zip(buf, project_name="proyecto_slip")
        # El archivo con Zip Slip no debe ser extraído
        self.assertEqual(result['extracted_count'], 1)
        self.assertFalse(os.path.exists(os.path.join(self.temp_dir.name, 'evil.txt')))

    def test_zip_bomb_excessive_files_rejected(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as zf:
            for i in range(5005):  # Supera MAX_ZIP_FILES = 5000
                zf.writestr(f"file_{i}.txt", "data")
        buf.seek(0)

        with self.assertRaises(ZipBombViolation):
            self.analyzer.extract_zip(buf, project_name="proyecto_bomb_files")

        # Verificar que el directorio se limpió (rollback)
        target_dir = os.path.join(self.temp_dir.name, "proyecto_bomb_files")
        self.assertFalse(os.path.exists(target_dir))

    def test_zip_bomb_depth_rejected(self):
        buf = io.BytesIO()
        deep_path = "/".join([f"d{i}" for i in range(20)]) + "/file.py"  # 20 niveles > MAX_DIRECTORY_DEPTH (15)
        with zipfile.ZipFile(buf, 'w') as zf:
            zf.writestr(deep_path, 'print("too deep")')
        buf.seek(0)

        with self.assertRaises(ZipBombViolation):
            self.analyzer.extract_zip(buf, project_name="proyecto_deep")

        target_dir = os.path.join(self.temp_dir.name, "proyecto_deep")
        self.assertFalse(os.path.exists(target_dir))

if __name__ == '__main__':
    unittest.main()
