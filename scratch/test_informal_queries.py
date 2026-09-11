import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vector5010.settings')
import django
django.setup()

from vectorapp.views import preparar_contexto_vector

test_queries = [
    "veeme el tiempo",
    "como me llamo",
    "que recuerdas",
    "necesito tu ayuda ayuadmr",
    "vigila o supervisa algun cambio",
]

print("=== VERIFICACIÓN DE CONSULTAS INFORMALES EN VECTOR ===")
for q in test_queries:
    system_prompt, history_turns, mensaje_limpio = preparar_contexto_vector(q)
    print(f"\n--- CONSULTA: '{q}' ---")
    print(f"Turnos de historial transmitidos: {len(history_turns)}")
    
    if "DATOS METEOROLÓGICOS EN TIEMPO REAL" in system_prompt:
        print(" -> [OK] Clima en tiempo real inyectado correctamente.")
    if "CONSULTA DE IDENTIDAD DEL USUARIO" in system_prompt:
        print(" -> [OK] Identidad de Sebastian inyectada correctamente.")
    if "TELEMETRÍA DE VIGILANCIA Y SUPERVISIÓN EN VIVO" in system_prompt:
        print(" -> [OK] Centinela y telemetría de vigilancia inyectada correctamente.")
    if "DISPOSICIÓN Y DIAGNÓSTICO J.A.R.V.I.S." in system_prompt:
        print(" -> [OK] Disposición de ayuda y diagnóstico J.A.R.V.I.S. inyectada.")
    if "DIRECTIVA DE MEMORIA ASOCIATIVA" in system_prompt or "Recuerdos asociados" in system_prompt:
        print(" -> [OK] Memoria asociativa e interacciones previas recuperadas.")
