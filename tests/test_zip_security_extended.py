import os
import io
import zipfile
import django

if not os.environ.get("DJANGO_SETTINGS_MODULE"):
    os.environ["DJANGO_SETTINGS_MODULE"] = "vector5010.settings"
    django.setup()

import unittest
from vectorapp.code_analyzer import CodeAnalyzer
from vectorapp.security.exceptions import ZipBombViolation


class TestZipSecurityExtended(unittest.TestCase):
    """
    Pruebas exhaustivas para la seguridad de extracción de archivos ZIP:
    - Zip-Slip canónico y traversal.
    - Detección de Zip-Bombs por ratio y por tamaño comprimido acumulado.
    - Cuotas de profundidad de directorios y tamaño de archivos individuales.
    """

    def setUp(self):
        self.analyzer = CodeAnalyzer()

    def test_canonical_zip_slip_blocked(self):
        """Verifica que rutas con traversal (../..) no sean extraídas fuera del directorio de proyecto."""
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            zf.writestr("../../pwned.py", "print('malicious')")
            zf.writestr("valid_dir/safe.py", "print('safe')")

        zip_buf.seek(0)
        res = self.analyzer.extract_zip(zip_buf, project_name="test_slip_project")
        # safe.py debe estar extraído
        self.assertEqual(res["extracted_count"], 1)
        # El archivo malicioso no debe haberse creado fuera
        parent_bad = os.path.abspath(os.path.join(self.analyzer.workspace_dir, "pwned.py"))
        self.assertFalse(os.path.exists(parent_bad))

    def test_directory_depth_limit_enforced(self):
        """Bloquea archivos con más de 15 niveles de anidación."""
        deep_path = "/".join([f"lvl_{i}" for i in range(20)]) + "/deep_file.py"
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            zf.writestr(deep_path, "print('too deep')")

        zip_buf.seek(0)
        with self.assertRaises(ZipBombViolation):
            self.analyzer.extract_zip(zip_buf, project_name="test_deep_project")

    @unittest.mock.patch("vectorapp.code_analyzer.MAX_SINGLE_FILE_SIZE", 50)
    def test_single_file_size_limit_enforced(self):
        """Bloquea archivos individuales que exceden la cuota individual declarada."""
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            zf.writestr("large.txt", b"x" * 200)

        zip_buf.seek(0)
        with self.assertRaises(ZipBombViolation):
            self.analyzer.extract_zip(zip_buf, project_name="test_large_project")

    @unittest.mock.patch("vectorapp.code_analyzer.MAX_ZIP_COMPRESSED_SIZE", 50)
    def test_compressed_size_limit_enforced(self):
        """Verifica que un ZIP cuyo tamaño comprimido total exceda el límite sea rechazado."""
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            zf.writestr("huge_comp.bin", b"test" * 50)

        zip_buf.seek(0)
        with self.assertRaises(ZipBombViolation):
            self.analyzer.extract_zip(zip_buf, project_name="test_huge_comp")
