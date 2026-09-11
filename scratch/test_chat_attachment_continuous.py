import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vector5010.settings')
django.setup()

from vectorapp.views import preparar_contexto_vector

def test_file_attachment_context():
    sample_file = {
        "name": "fibonacci.py",
        "size": 185,
        "type": "text/x-python",
        "content": "def fib(n):\n    if n <= 1: return n\n    return fib(n-1) + fib(n-2)\n\nprint([fib(i) for i in range(10)])\n"
    }

    # Turno 1: Usuario adjunta archivo y pregunta qué hace el código
    msg1 = "¿Puedes explicarme qué hace este script y cómo optimizarlo?"
    sys_prompt, history_turns, clean_msg = preparar_contexto_vector(
        mensaje=msg1,
        session=None,
        imagen_input="",
        usuario=None,
        historial_input=[],
        archivo_adjunto=sample_file
    )

    print("=== TEST 1: INYECCIÓN DE ARCHIVO ADJUNTO ===")
    assert "fibonacci.py" in sys_prompt, "El nombre del archivo debe estar en el system prompt"
    assert "def fib(n):" in sys_prompt, "El contenido del archivo debe estar en el system prompt"
    assert "python" in sys_prompt.lower(), "El lenguaje detectado debe ser Python"
    assert "DIRECTRICES DE OPERACIÓN J.A.R.V.I.S." in sys_prompt
    assert "13. ARCHIVOS Y CÓDIGO ADJUNTO" in sys_prompt
    print("[OK] Archivo adjunto inyectado correctamente en el contexto con directriz 13 y deteccion de lenguaje.")

    # Turno 2: Seguimiento continuo (como ChatGPT/Gemini)
    historial_continuo = [
        {"role": "user", "content": "¿Puedes explicarme qué hace este script y cómo optimizarlo? [Archivo adjunto: fibonacci.py]"},
        {"role": "assistant", "content": "El script calcula la serie de Fibonacci mediante recursión simple de complejidad O(2^n). Te recomiendo usar programación dinámica o memoización O(n)."}
    ]
    msg2 = "Genial, ¿y cómo quedaría con memoización usando functools.lru_cache?"
    sys_prompt2, history_turns2, clean_msg2 = preparar_contexto_vector(
        mensaje=msg2,
        session=None,
        imagen_input="",
        usuario=None,
        historial_input=historial_continuo,
        archivo_adjunto=None
    )

    print("\n=== TEST 2: HISTORIAL Y MEMORIA CONTINUA ===")
    assert len(history_turns2) == 2, f"Se esperaban 2 turnos en el historial, se encontraron {len(history_turns2)}"
    assert history_turns2[0]["role"] == "user"
    assert "fibonacci.py" in history_turns2[0]["content"]
    assert history_turns2[1]["role"] == "assistant"
    assert "lru_cache" in clean_msg2
    print("[OK] Memoria continua de dialogo preservada y estructurada correctamente para el motor de inferencia.")

if __name__ == "__main__":
    test_file_attachment_context()
    print("\n[EXITO] Todos los tests de contexto continuo y archivos adjuntos pasaron.")
