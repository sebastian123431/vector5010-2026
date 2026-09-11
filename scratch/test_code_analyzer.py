import os
import sys
import zipfile
import io

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vector5010.settings')
import django
django.setup()

from vectorapp.code_analyzer import ProjectCodeAnalyzer

# 1. Crear un ZIP en memoria con archivos de prueba (uno con error de sintaxis y otro correcto)
zip_buffer = io.BytesIO()
with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
    # Archivo correcto
    zf.writestr("app/calculadora.py", """
class Calculadora:
    def sumar(self, a, b):
        return a + b
    
    def dividir(self, a, b):
        try:
            return a / b
        except:
            pass
""")
    # Archivo con error de sintaxis deliberado
    zf.writestr("app/servicio.py", """
def procesar_datos(lista):
    if len(lista) > 0
        return True
""")
    # Archivo JSON
    zf.writestr("config.json", '{"nombre": "test", "version": "1.0"}')

zip_buffer.seek(0)

print("=== INICIANDO TEST DEL ANALIZADOR DE CÓDIGO ===")
analyzer = ProjectCodeAnalyzer()
extracted = analyzer.extract_zip(zip_buffer, project_name="test_proyecto_demo")
print(f"[OK] Extraídos {extracted['extracted_count']} archivos a: {extracted['project_dir']}")

diagnosis = analyzer.diagnose_project(extracted["project_dir"])
print(f"[OK] Total archivos analizados: {diagnosis['total_files']}, Líneas: {diagnosis['total_lines']}")
print(f"[OK] Errores de sintaxis detectados: {len(diagnosis['syntax_errors'])}")
for err in diagnosis['syntax_errors']:
    print(f"   -> {err['file']}:{err['line']} => {err['message']}")
print(f"[OK] Advertencias detectadas: {len(diagnosis['warnings'])}")

analyzer.index_semantics("test_proyecto_demo", diagnosis)
print("[OK] Indexación semántica completada en red sináptica.")

report = analyzer.generate_markdown_report("test_proyecto_demo", diagnosis)
print("\n--- INFORME GENERADO ---\n")
print(report[:400] + "...\n")
