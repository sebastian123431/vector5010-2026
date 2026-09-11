import os
import sys
import json
import django
import requests

# Configurar entorno Django
sys.path.insert(0, r"d:\escritorio\vector5010 2026")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vector5010.settings")
django.setup()

from vectorapp.file_deep_analyzer import analyze_multiple_files, deep_inspect_file
from vectorapp.views import preparar_contexto_vector

def test_python_comparative_analysis():
    print("=== TEST 1: Análisis Comparativo de Scripts Python ===")
    file_v1 = {
        "name": "services_v1.py",
        "type": "text/x-python",
        "size": 250,
        "content": """import math

def calculate_average(items):
    return sum(items) / len(items) if items else 0

def deprecated_feature():
    print("This will be removed")
"""
    }

    file_v2 = {
        "name": "services_v2.py",
        "type": "text/x-python",
        "size": 380,
        "content": """import math
import numpy as np

class StatsCalculator:
    def __init__(self):
        self.data = []

def calculate_average(items):
    return sum(items) / len(items) if items else 0

def accelerated_calculation(items):
    return np.mean(items)
"""
    }

    report = analyze_multiple_files([file_v1, file_v2])
    print("\n--- Reporte Generado ---")
    print(report[:1200] + "...")

    # Aserciones
    assert "services_v1.py" in report, "services_v1.py debe estar en el reporte"
    assert "services_v2.py" in report, "services_v2.py debe estar en el reporte"
    assert "MATRIZ COMPARATIVA" in report, "Debe contener la sección de Matriz Comparativa"
    assert "calculate_average" in report, "Debe detectar función compartida calculate_average"
    assert "accelerated_calculation" in report, "Debe detectar función exclusiva accelerated_calculation"
    assert "StatsCalculator" in report, "Debe detectar clase nueva StatsCalculator"
    assert "numpy" in report, "Debe detectar nuevo import numpy"
    print("[OK] Test 1: Análisis comparativo Python superado exitosamente.")

def test_csv_comparative_analysis():
    print("\n=== TEST 2: Análisis Comparativo de Archivos CSV ===")
    csv_1 = {
        "name": "ventas_2025.csv",
        "type": "text/csv",
        "size": 150,
        "content": "id,sucursal,ventas\n1,Vicuña,15000\n2,La Serena,22000\n"
    }

    csv_2 = {
        "name": "ventas_2026.csv",
        "type": "text/csv",
        "size": 260,
        "content": "id,sucursal,ventas,margen,meta_anual\n1,Vicuña,18500,0.22,25000\n2,La Serena,26000,0.25,30000\n"
    }

    report = analyze_multiple_files([csv_1, csv_2])
    print("\n--- Reporte CSV ---")
    print(report)

    assert "ventas_2025.csv" in report
    assert "ventas_2026.csv" in report
    assert "margen" in report, "Debe detectar columna margen en nuevo CSV"
    assert "meta_anual" in report, "Debe detectar columna meta_anual en nuevo CSV"
    print("[OK] Test 2: Análisis comparativo CSV superado exitosamente.")

def test_context_preparation():
    print("\n=== TEST 3: Inyección de Contexto en preparar_contexto_vector ===")
    files = [
        {"name": "script_a.py", "content": "def foo(): pass", "size": 30},
        {"name": "script_b.py", "content": "def foo(): pass\ndef bar(): pass", "size": 60}
    ]
    
    system_prompt, history_turns, msg_clean = preparar_contexto_vector(
        mensaje="Compara estos dos scripts",
        archivo_adjunto=files,
        cliente_ubicacion="Vicuña, Chile"
    )
    
    assert "ARCHIVOS MÚLTIPLES ADJUNTOS" in system_prompt
    assert "MATRIZ COMPARATIVA" in system_prompt
    assert "DIRECTRICES DE OPERACIÓN" in system_prompt
    assert "13. ARCHIVOS Y CÓDIGO ADJUNTO" in system_prompt
    print("[OK] Test 3: Preparación de contexto con multi-archivos verificada exitosamente.")

def test_live_streaming_endpoint():
    print("\n=== TEST 4: Streaming SSE en vivo contra Django Server ===")
    url = "http://192.168.1.83:8000/api/chat/stream/"
    payload = {
        "mensaje": "Compara detalladamente script_a.py y script_b.py explicando qué función se agregó.",
        "archivos": [
            {"name": "script_a.py", "content": "def modulo_alfa():\n    return 42\n", "size": 40},
            {"name": "script_b.py", "content": "def modulo_alfa():\n    return 42\n\ndef modulo_beta():\n    return 'optimizado'\n", "size": 90}
        ],
        "cliente_hora": "17:00:00",
        "cliente_fecha": "jueves, 10 de septiembre de 2026",
        "cliente_timezone": "America/Santiago",
        "cliente_ubicacion": "Vicuña, Región de Coquimbo, Chile"
    }

    try:
        response = requests.post(url, json=payload, stream=True, timeout=25)
        print(f"Status HTTP: {response.status_code}")
        assert response.status_code == 200, f"Error HTTP {response.status_code}"

        accumulated_text = ""
        got_token = False
        for line in response.iter_lines():
            if line:
                decoded = line.decode('utf-8')
                if decoded.startswith("data: "):
                    try:
                        data = json.loads(decoded[6:])
                        if "token" in data:
                            accumulated_text += data["token"]
                            got_token = True
                        elif "full_response" in data:
                            accumulated_text = data["full_response"]
                    except Exception:
                        pass
        
        print("\n--- Respuesta de Vector en Streaming ---")
        print(accumulated_text[:500] + "...")
        assert got_token or accumulated_text, "Debe recibir tokens en streaming"
        assert "modulo_beta" in accumulated_text.lower() or "script_b" in accumulated_text.lower() or "beta" in accumulated_text.lower(), "La respuesta debe referenciar las diferencias de código"
        print("[OK] Test 4: Endpoint en vivo de streaming validado exitosamente.")
    except Exception as e:
        print(f"[WARN] Error en Test 4: {e}")
        raise e

if __name__ == "__main__":
    test_python_comparative_analysis()
    test_csv_comparative_analysis()
    test_context_preparation()
    test_live_streaming_endpoint()
    print("\n==========================================")
    print("TODAS LAS PRUEBAS AUTOMATIZADAS PASARON OK!")
    print("==========================================")
