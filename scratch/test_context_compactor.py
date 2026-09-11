import os
import sys
import json
import django
import requests

# Configurar entorno Django
sys.path.insert(0, r"d:\escritorio\vector5010 2026")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vector5010.settings")
django.setup()

from vectorapp.context_compactor import ContextCompactor
from vectorapp.neural_network import semantic_network
from vectorapp.views import preparar_contexto_vector

def test_compactor_logic():
    print("=== TEST 1: Lógica de Compactación y Extracción Semántica ===")
    
    # 4 turnos: no debe compactar aún
    short_turns = [
        {"role": "user", "content": "Hola Vector"},
        {"role": "assistant", "content": "Hola Sebastian, en qué puedo colaborar?"},
        {"role": "user", "content": "Necesito optimizar mi script.py"},
        {"role": "assistant", "content": "Perfecto, podemos revisar la función calcular()"}
    ]
    assert not ContextCompactor.should_compact(short_turns), "4 turnos no deberían activar compactación"
    
    # 8 turnos: debe activar compactación
    long_turns = short_turns + [
        {"role": "user", "content": "Agreguemos aceleración con numpy al cálculo"},
        {"role": "assistant", "content": "He integrado numpy.mean() para reducir la latencia."},
        {"role": "user", "content": "Excelente, ahora conectemos con la base de datos"},
        {"role": "assistant", "content": "Conexión establecida con PostgreSQL mediante pool."},
    ]
    assert ContextCompactor.should_compact(long_turns), "8 turnos deben activar compactación"

    capsule, recent = ContextCompactor.compact_conversation_history(long_turns, session={}, semantic_network=semantic_network)
    
    print("\n--- Cápsula Generada ---")
    print(capsule)
    print(f"\nTurnos recientes preservados: {len(recent)} de {len(long_turns)}")
    
    assert "CAPSULA DE CONTEXTO CONVERSACIONAL CONSOLIDADO" in capsule, "Debe contener el encabezado de cápsula"
    assert len(recent) == ContextCompactor.TURNOS_RECIENTES_PRESERVADOS, f"Debe preservar exactamente {ContextCompactor.TURNOS_RECIENTES_PRESERVADOS} turnos recientes"
    assert "script.py" in capsule or "numpy" in capsule, "Debe extraer entidades técnicas del hilo antiguo"
    print("[OK] Test 1: Lógica de compactación superada exitosamente.")

def test_neural_synapse_assimilation():
    print("\n=== TEST 2: Asimilación en Red Neuronal Sináptica ===")
    initial_neurons = len(semantic_network.neurons)
    
    turns = [
        {"role": "user", "content": "Analicemos el microservicio de pagos en vicuña"},
        {"role": "assistant", "content": "Revisando arquitectura con CUDA y django."},
        {"role": "user", "content": "Hagamos un benchmark de latencia"},
        {"role": "assistant", "content": "Latencia actual 24ms con GPU."},
        {"role": "user", "content": "Guarda este hito de optimización"},
        {"role": "assistant", "content": "Guardado en registro."},
        {"role": "user", "content": "Continuemos con el siguiente paso"},
        {"role": "assistant", "content": "Listo para continuar."}
    ]
    
    capsule, recent = ContextCompactor.compact_conversation_history(turns, session={}, semantic_network=semantic_network)
    
    # Verificar que el recuerdo se asimiló en la red
    recuerdos_conversacion = [n for n in semantic_network.neurons.values() if n.concept_type == "conversation_synapse"]
    print(f"Neuronas de sinapsis conversacional en la red: {len(recuerdos_conversacion)}")
    assert len(recuerdos_conversacion) > 0, "Debe existir al menos una neurona de sinapsis conversacional"
    print("[OK] Test 2: Asimilación sináptica en red neuronal verificada exitosamente.")

def test_context_injection():
    print("\n=== TEST 3: Inyección en preparar_contexto_vector ===")
    history_mock = [
        {"role": "user", "content": f"Paso {i}: revisando módulo_{i}.py"} 
        if i % 2 == 1 else 
        {"role": "assistant", "content": f"Respuesta {i}: procesado módulo_{i}.py"}
        for i in range(1, 9)
    ]
    
    sys_prompt, history_turns, msg_clean = preparar_contexto_vector(
        mensaje="¿Cuál fue el primer módulo que revisamos?",
        historial_input=history_mock,
        cliente_ubicacion="Vicuña, Chile"
    )
    
    print(f"Turnos en history_turns: {len(history_turns)} (originalmente eran 8)")
    assert "CAPSULA DE CONTEXTO CONVERSACIONAL CONSOLIDADO" in sys_prompt, "El system_prompt debe contener la cápsula compactada"
    assert len(history_turns) <= 6, f"history_turns debe estar reducido ({len(history_turns)} <= 6)"
    print("[OK] Test 3: Inyección de cápsula compactada en prompt de sistema verificada exitosamente.")

def test_live_streaming_compaction():
    print("\n=== TEST 4: Streaming SSE en vivo con Historial Largo ===")
    url = "http://192.168.1.83:8000/api/chat/stream/"
    
    history_payload = [
        {"role": "user", "content": "Quiero crear un calculador de física en physics.py"},
        {"role": "assistant", "content": "Entendido Sebastian, diseñemos la clase Gravitacional en physics.py."},
        {"role": "user", "content": "Añade constantes de gravitación universal"},
        {"role": "assistant", "content": "Constante G = 6.674e-11 agregada."},
        {"role": "user", "content": "Perfecto, mantengamos eso como base."},
        {"role": "assistant", "content": "Base guardada y validada."},
        {"role": "user", "content": "¿Qué constantes habíamos definido antes?"},
        {"role": "assistant", "content": "Habíamos definido la constante gravitacional G."}
    ]
    
    payload = {
        "mensaje": "Resume brevemente lo que veníamos trabajando en physics.py y qué constante usamos.",
        "historial": history_payload,
        "cliente_hora": "17:40:00",
        "cliente_fecha": "jueves, 10 de septiembre de 2026",
        "cliente_timezone": "America/Santiago",
        "cliente_ubicacion": "Vicuña, Región de Coquimbo, Chile"
    }

    try:
        response = requests.post(url, json=payload, stream=True, timeout=25)
        assert response.status_code == 200, f"Error HTTP {response.status_code}"

        accumulated_text = ""
        for line in response.iter_lines():
            if line:
                decoded = line.decode('utf-8')
                if decoded.startswith("data: "):
                    try:
                        data = json.loads(decoded[6:])
                        if "token" in data:
                            accumulated_text += data["token"]
                        elif "full_response" in data:
                            accumulated_text = data["full_response"]
                    except Exception:
                        pass
        
        print("\n--- Respuesta de Vector con Historial Compactado ---")
        print(accumulated_text[:500] + "...")
        assert accumulated_text, "Debe generar respuesta en streaming"
        assert "physics" in accumulated_text.lower() or "gravit" in accumulated_text.lower() or "constante" in accumulated_text.lower(), "Debe recordar el contexto compactado de physics.py"
        print("[OK] Test 4: Endpoint en vivo con compactación verificado exitosamente.")
    except Exception as e:
        print(f"[WARN] Error en Test 4: {e}")
        raise e

if __name__ == "__main__":
    test_compactor_logic()
    test_neural_synapse_assimilation()
    test_context_injection()
    test_live_streaming_compaction()
    print("\n=======================================================")
    print("TODAS LAS PRUEBAS DE COMPACTACION PASARON EXITOSAMENTE!")
    print("=======================================================")
