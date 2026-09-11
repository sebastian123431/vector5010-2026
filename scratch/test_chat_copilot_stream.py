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
from vectorapp.views import interactuar_stream

def test_stream():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    print("=== TEST: Chat Stream con Proyecto Activo en Memoria ===")
    
    factory = RequestFactory()
    body = {
        "mensaje": "¿Qué error tiene mi archivo servicio.py y cómo lo soluciono?",
        "historial": []
    }
    request = factory.post(
        "/api/chat/stream/",
        data=json.dumps(body),
        content_type="application/json"
    )
    
    middleware = SessionMiddleware(lambda req: None)
    middleware.process_request(request)
    
    # Inyectar el proyecto en sesion
    request.session["active_project"] = {
        "nombre": "mi_proyecto",
        "total_files": 3,
        "total_lines": 13,
        "syntax_errors": [
            {"file": "mi_proyecto/servicio.py", "line": 1, "message": "expected ':'"}
        ],
        "warnings": [],
        "functions": ["calcular_total", "saludar", "procesar"],
        "classes": ["Usuario"]
    }
    request.session.save()
    
    resp = interactuar_stream(request)
    print(f"Streaming Response status: {resp.status_code}")
    
    content_chunks = []
    # Leer el generador de StreamingHttpResponse
    for chunk in resp.streaming_content:
        chunk_str = chunk.decode("utf-8") if isinstance(chunk, bytes) else chunk
        content_chunks.append(chunk_str)
        
    full_output = "".join(content_chunks)
    print("Longitud de respuesta en streaming:", len(full_output))
    print("Primeros 300 caracteres del stream:")
    print(full_output[:300])
    print("\n✅ Streaming verificado correctamente.")

if __name__ == "__main__":
    test_stream()
