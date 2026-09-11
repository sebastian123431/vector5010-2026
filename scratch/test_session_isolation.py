import os
import sys
import uuid
from django.test import RequestFactory

sys.path.insert(0, os.path.abspath("."))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vector5010.settings")
import django
django.setup()

from vectorapp.models import Interaction
from vectorapp.views import (
    interactuar,
    obtener_historial_consultas,
    listar_sesiones_chat,
    limpiar_sesion_chat
)

def main():
    factory = RequestFactory()
    
    session_a = f"sess_seba_{uuid.uuid4().hex[:8]}"
    session_b = f"sess_juana_{uuid.uuid4().hex[:8]}"

    print(f"=== TEST 1: Creación de interacciones en Sesión A ({session_a}) ===")
    Interaction.objects.create(
        question="cómo compilar un archivo cython?",
        answer="Para compilar con Cython, usa un archivo setup.py con cythonize.",
        session_id=session_a,
        user_name="Sebastian"
    )
    Interaction.objects.create(
        question="y cómo optimizo el bucle con cdef?",
        answer="Usa cdef int i para declarar variables de tipo C nativas.",
        session_id=session_a,
        user_name="Sebastian"
    )

    print(f"\n=== TEST 2: Creación de interacciones en Sesión B ({session_b}) ===")
    Interaction.objects.create(
        question="hola vector soy juana, qué lugares turísticos hay en el valle de elqui?",
        answer="Hola Juana, en el Valle de Elqui puedes visitar Vicuña, Paihuano y los observatorios astronómicos.",
        session_id=session_b,
        user_name="Juana"
    )

    print("\n=== TEST 3: Filtrado estricto de historial por session_id ===")
    # Historial de Sesión A
    req_a = factory.get(f"/api/chat/historial/?session_id={session_a}&orden=asc")
    resp_a = obtener_historial_consultas(req_a)
    hist_a = resp_a.data.get("historial", [])
    print(f"Turnos en Sesión A: {len(hist_a)}")
    for h in hist_a:
        print(f" - [{h['user_name']}] {h['pregunta']}")
        assert "valle de elqui" not in h['pregunta'].lower(), "Error: Sesión A contiene temas de Sesión B!"
        assert h['session_id'] == session_a
    assert len(hist_a) == 2

    # Historial de Sesión B
    req_b = factory.get(f"/api/chat/historial/?session_id={session_b}&orden=asc")
    resp_b = obtener_historial_consultas(req_b)
    hist_b = resp_b.data.get("historial", [])
    print(f"Turnos en Sesión B: {len(hist_b)}")
    for h in hist_b:
        print(f" - [{h['user_name']}] {h['pregunta']}")
        assert "cython" not in h['pregunta'].lower(), "Error: Sesión B contiene temas de Sesión A!"
        assert h['session_id'] == session_b
    assert len(hist_b) == 1

    print("\n=== TEST 4: Listar sesiones de chat (Estilo ChatGPT) ===")
    req_list = factory.get("/api/chat/sesiones/")
    resp_list = listar_sesiones_chat(req_list)
    sesiones = resp_list.data.get("sesiones", [])
    print(f"Total sesiones listadas: {len(sesiones)}")
    s_ids = [s['session_id'] for s in sesiones]
    assert session_a in s_ids, "Sesión A no encontrada en listar_sesiones_chat"
    assert session_b in s_ids, "Sesión B no encontrada en listar_sesiones_chat"
    
    # Comprobar datos de sesión A en la lista
    sess_a_item = next(s for s in sesiones if s['session_id'] == session_a)
    print("Item Sesión A:", sess_a_item)
    assert sess_a_item['mensajes_count'] == 2
    assert "cython" in sess_a_item['titulo'].lower()

    print("\n=== TEST 5: Limpiar sesión para nueva conversación ===")
    req_clean = factory.post("/api/chat/nueva_sesion/")
    # Simular middleware de sesión
    from django.contrib.sessions.backends.db import SessionStore
    req_clean.session = SessionStore()
    req_clean.session["chat_history"] = [("hola", "chao")]
    req_clean.session["resumen_conversacion_acumulado"] = "resumen viejo"
    resp_clean = limpiar_sesion_chat(req_clean)
    print("Respuesta limpiar sesión:", resp_clean.data)
    assert resp_clean.data.get("success") is True
    assert len(req_clean.session["chat_history"]) == 0
    assert req_clean.session["resumen_conversacion_acumulado"] == ""
    assert resp_clean.data.get("nueva_sesion_id") != ""

    print("\n>>> TODOS LOS TESTS DE AISLAMIENTO DE SESIONES PASARON CON ÉXITO! <<<")

if __name__ == "__main__":
    main()
