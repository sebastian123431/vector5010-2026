import os
import sys
import io
import zipfile
import json
import django

# Set up Django environment
sys.path.insert(0, r"d:\escritorio\vector5010 2026")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vector5010.settings")
django.setup()

from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from vectorapp.views import analizar_proyecto_zip, estado_proyecto_actual, preparar_contexto_vector
from django.core.files.uploadedfile import SimpleUploadedFile

def run_test():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    print("=== TEST E2E: Diagnostico de Codigo ZIP & Contexto de Vector ===")
    
    # 1. Crear un ZIP en memoria con un proyecto de prueba
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Archivo 1: servicio con error de sintaxis intencional
        zf.writestr("mi_proyecto/servicio.py", "def calcular_total(a, b)\n    return a + b\n")
        # Archivo 2: modelo valido
        zf.writestr("mi_proyecto/modelo.py", "class Usuario:\n    def __init__(self, nombre):\n        self.nombre = nombre\n\n    def saludar(self):\n        return f'Hola {self.nombre}'\n")
        # Archivo 3: utilidades con warning
        zf.writestr("mi_proyecto/utils.py", "def procesar(datos):\n    try:\n        return len(datos)\n    except:\n        return 0\n")
    
    zip_buffer.seek(0)
    uploaded_file = SimpleUploadedFile("mi_proyecto.zip", zip_buffer.read(), content_type="application/zip")
    
    # 2. Simular peticion POST a /api/codigo/analizar_zip/
    factory = RequestFactory()
    request = factory.post("/api/codigo/analizar_zip/", {"archivo_zip": uploaded_file})
    
    # Añadir sesion
    middleware = SessionMiddleware(lambda req: None)
    middleware.process_request(request)
    request.session.save()
    
    response = analizar_proyecto_zip(request)
    response.render()
    print(f"Status Code: {response.status_code}")
    res_data = json.loads(response.content)
    
    assert res_data.get("success") is True, f"Error en respuesta: {res_data}"
    print(f"Proyecto analizado: {res_data['proyecto']}")
    print(f"Archivos analizados: {res_data['metricas']['archivos_totales']}")
    print(f"Lineas de codigo: {res_data['metricas']['lineas_totales']}")
    print(f"Estado diagnostico: {res_data['diagnostico']['estado']}")
    print(f"Errores encontrados: {len(res_data['diagnostico']['errores'])}")
    print(f"Advertencias: {len(res_data['diagnostico']['advertencias'])}")
    
    # Verificar que el error de sintaxis fue detectado
    assert len(res_data['diagnostico']['errores']) > 0, "No se detecto el error de sintaxis"
    err = res_data['diagnostico']['errores'][0]
    print(f"Detalle del error detectado: {err['archivo']} (Linea {err.get('linea')}): {err['mensaje']}")
    
    # 3. Probar GET /api/codigo/estado_proyecto/
    req_status = factory.get("/api/codigo/estado_proyecto/")
    req_status.session = request.session
    res_status = estado_proyecto_actual(req_status)
    res_status.render()
    status_data = json.loads(res_status.content)
    print(f"Estado de proyecto en sesion: {status_data['activo']} - {status_data.get('proyecto', {}).get('nombre')}")
    assert status_data['activo'] is True
    
    # 4. Probar inyeccion de contexto en preparar_contexto_vector
    system_prompt, _, _ = preparar_contexto_vector("¿Que errores tiene mi codigo y como los soluciono?", request)
    assert "PROYECTO DE CODIGO CARGADO EN MEMORIA" in system_prompt or "PROYECTO DE CÓDIGO CARGADO EN MEMORIA" in system_prompt, "El contexto del proyecto no se inyecto en el prompt de Vector"
    assert "mi_proyecto" in system_prompt, "El nombre del proyecto no aparece en el prompt"
    print("Inyeccion de contexto en Vector verificada exitosamente:")
    print("--- Fragmento de Prompt Inyectado ---")
    for line in system_prompt.split("\n"):
        if "PROYECTO" in line or "servicio.py" in line or "calcular_total" in line:
            print(f"  > {line}")
            
    print("\nTODOS LOS TESTS E2E PASARON CORRECTAMENTE.")

if __name__ == "__main__":
    run_test()
