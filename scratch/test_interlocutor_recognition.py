import os
import sys
import django

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vector5010.settings')
django.setup()

from vectorapp.views import detectar_nombre_presentacion, preparar_contexto_vector
from vectorapp.query_optimizer import query_optimizer

def test_detectar_nombre_presentacion():
    print("=== TEST 1: Detección de Nombre en Presentaciones Naturales ===")
    casos = [
        ("olle me llamo seba", "Seba"),
        ("hola soy juana", "Juana"),
        ("hola soy millaray", "Millaray"),
        ("soy miguel en si", "Miguel"),
        ("hola, me llamo Carlos", "Carlos"),
        ("te habla Daniel", "Daniel"),
        ("mi nombre es Sofia", "Sofia"),
        # Casos que NO deben ser nombres (stopwords)
        ("hola soy nuevo", None),
        ("soy un amigo", None),
        ("soy de santiago", None),
        ("me llamo para avisarte", None),
        ("hola vector como estas", None),
    ]

    for texto, esperado in casos:
        resultado = detectar_nombre_presentacion(texto)
        if esperado is None:
            assert resultado is None, f"Fallo en '{texto}': esperado None, obtenido '{resultado}'"
            print(f"  [PASS] '{texto}' -> Correctamente rechazado (no es nombre personal)")
        else:
            assert resultado is not None and resultado.lower() == esperado.lower(), (
                f"Fallo en '{texto}': esperado '{esperado}', obtenido '{resultado}'"
            )
            print(f"  [PASS] '{texto}' -> '{resultado}' (esperado '{esperado}')")

def test_preparar_contexto_interlocutor():
    print("\n=== TEST 2: Contexto y System Prompt por Interlocutor ===")
    
    # Caso 1: Juana pregunta quién es
    sys_juana, hist_juana, msg_juana = preparar_contexto_vector(
        "¿quién soy yo?",
        nombre_cliente="Juana"
    )
    assert "Juana" in sys_juana, "El system_prompt debe incluir a Juana"
    assert "NUNCA la/lo llames Seba ni Sebastian" in sys_juana, "Debe instruir no llamar Sebastian a Juana"
    assert "Tú eres Juana" in sys_juana, "La respuesta sobre identidad debe nombrar a Juana"
    print("  [PASS] Juana: system_prompt configurado correctamente con su identidad.")

    # Caso 2: Sebastian pregunta quién es
    sys_seba, hist_seba, msg_seba = preparar_contexto_vector(
        "¿quién soy?",
        nombre_cliente="Sebastian"
    )
    assert "Sebastian Espíndola" in sys_seba, "El system_prompt debe reconocer al creador Sebastian"
    assert "Tú eres Seba (Sebastian Espíndola), mi creador" in sys_seba, "La identidad debe indicar creador"
    print("  [PASS] Sebastian: system_prompt reconoce al creador.")

    # Caso 3: Millaray se presenta directamente
    sys_milla, _, _ = preparar_contexto_vector(
        "hola soy millaray",
        nombre_cliente=None # Debe detectarlo en el mensaje
    )
    assert "Millaray" in sys_milla, "Debe autodetectar a Millaray desde el texto"
    assert "DIRECTIVA PRIORITARIA DE PRESENTACIÓN Y BIENVENIDA" in sys_milla
    print("  [PASS] Autodetección en preparar_contexto_vector: 'hola soy millaray' -> Millaray en contexto")

def test_query_optimizer_personalizacion():
    print("\n=== TEST 3: Saludos y Caché en query_optimizer ===")
    
    # Saludo simple para Sebastian
    resp_seba = query_optimizer.get_simple_response("hola", user_name="Sebastian")
    assert resp_seba and "Sebastian" in resp_seba, f"Esperado saludo a Sebastian, obtenido: {resp_seba}"
    print(f"  [PASS] Saludo Sebastian: '{resp_seba}'")

    # Saludo simple para Juana
    resp_juana = query_optimizer.get_simple_response("hola", user_name="Juana")
    assert resp_juana and "Juana" in resp_juana and "Sebastian" not in resp_juana, (
        f"Esperado saludo a Juana sin mencionar a Sebastian, obtenido: {resp_juana}"
    )
    print(f"  [PASS] Saludo Juana: '{resp_juana}'")

    # Presentación natural directa ('soy seba', 'soy millaray')
    resp_soy_seba = query_optimizer.get_simple_response("soy seba", user_name="")
    assert resp_soy_seba and "Seba" in resp_soy_seba, f"Fallo 'soy seba': {resp_soy_seba}"
    print(f"  [PASS] 'soy seba' -> '{resp_soy_seba}'")

    resp_soy_milla = query_optimizer.get_simple_response("soy millaray", user_name="")
    assert resp_soy_milla and "Millaray" in resp_soy_milla, f"Fallo 'soy millaray': {resp_soy_milla}"
    print(f"  [PASS] 'soy millaray' -> '{resp_soy_milla}'")

    # Preguntas de identidad directas ('¿quién soy?', 'cómo me llamo')
    resp_id_seba = query_optimizer.get_simple_response("¿quién soy?", user_name="Seba")
    assert resp_id_seba and "creador" in resp_id_seba.lower(), f"Fallo id Seba: {resp_id_seba}"
    print(f"  [PASS] Seba pregunta '¿quién soy?': '{resp_id_seba}'")

    resp_id_milla = query_optimizer.get_simple_response("¿cómo me llamo?", user_name="Millaray")
    assert resp_id_milla and "Millaray" in resp_id_milla, f"Fallo id Millaray: {resp_id_milla}"
    print(f"  [PASS] Millaray pregunta '¿cómo me llamo?': '{resp_id_milla}'")

    resp_id_anon = query_optimizer.get_simple_response("¿quién soy?", user_name="")
    assert resp_id_anon and "Aún no me has dicho tu nombre" in resp_id_anon, f"Fallo id anon: {resp_id_anon}"
    print(f"  [PASS] Usuario anónimo pregunta '¿quién soy?': '{resp_id_anon}'")

    # Saludo con tarea compleja pasa a LLM
    resp_tarea = query_optimizer.get_simple_response("soy millaray y necesito resolver esta ecuación diferencial", user_name="")
    assert resp_tarea is None, "Presentación con tarea compleja debe pasar a LLM"
    print("  [PASS] 'soy millaray y necesito resolver...' -> Pasa a LLM (None)")

    # Caché aislado por usuario (usando consulta estática que sí califica para caché)
    query_optimizer.cache_response("que es una variable", "Una variable almacena datos para Seba", user_name="Sebastian")
    query_optimizer.cache_response("que es una variable", "Una variable almacena datos para Juana", user_name="Juana")

    cache_seba = query_optimizer.get_cached_response("que es una variable", user_name="Sebastian")
    cache_juana = query_optimizer.get_cached_response("que es una variable", user_name="Juana")

    assert cache_seba == "Una variable almacena datos para Seba", f"Fallo cache Seba: {cache_seba}"
    assert cache_juana == "Una variable almacena datos para Juana", f"Fallo cache Juana: {cache_juana}"
    print("  [PASS] Caché aislado: las respuestas cacheadas no se cruzan entre usuarios.")

if __name__ == "__main__":
    print("Iniciando validación integral de interlocutores para Vector...")
    test_detectar_nombre_presentacion()
    test_preparar_contexto_interlocutor()
    test_query_optimizer_personalizacion()
    print("\nTODOS LOS TESTS PASARON EXITOSAMENTE (5/5).")
