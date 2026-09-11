import os
import sys
import json
import django

sys.path.insert(0, r"d:\escritorio\vector5010 2026")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vector5010.settings")
django.setup()

from django.test import RequestFactory
from vectorapp.query_optimizer import query_optimizer, QueryComplexity
from vectorapp.needs_manager import needs_manager
from vectorapp.views import preparar_contexto_vector, optimizer_stats

def run_tests():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    print("=== TEST: Optimizador de Consultas y Detección Informal ===")

    # 1. Test de Clasificación
    casos = [
        ("hola", QueryComplexity.SIMPLE),
        ("gracias", QueryComplexity.SIMPLE),
        ("veme el tiempo", QueryComplexity.MODERATE),
        ("clima vicuña", QueryComplexity.MODERATE),
        ("cómo me llamo", QueryComplexity.MODERATE),
        ("sabes con quién hablas", QueryComplexity.MODERATE),
        ("crear herramienta para calcular descuentos", QueryComplexity.COMPLEX),
        ("diagnóstico del proyecto zip en AST", QueryComplexity.INTENSIVE)
    ]

    for q, expected in casos:
        c = query_optimizer.classify_query(q)
        print(f"Query: '{q}' -> Complejidad: {c.value} (Esperado: {expected.value})")
        assert c == expected, f"Fallo de clasificación en '{q}': {c} != {expected}"

    # 2. Test de Respuestas Rápidas J.A.R.V.I.S.
    fast_h = query_optimizer.get_simple_response("hola")
    print(f"Respuesta rápida 'hola': '{fast_h}'")
    assert fast_h and "Sebastian" in fast_h

    # 3. Test de Contexto Clima Informal
    sys_prompt1, _, _ = preparar_contexto_vector("veme el tiempo")
    assert "DATOS METEOROLÓGICOS" in sys_prompt1, "No detectó 'veme el tiempo'"
    assert "Vicuña" in sys_prompt1, "No asignó Vicuña por defecto"
    print("✅ Detección informal 'veme el tiempo' -> Vicuña OK")

    sys_prompt2, _, _ = preparar_contexto_vector("clima la serena")
    assert "DATOS METEOROLÓGICOS" in sys_prompt2, "No detectó 'clima la serena'"
    assert "La Serena" in sys_prompt2, "No detectó 'La Serena'"
    print("✅ Detección directa 'clima la serena' OK")

    # 4. Test de Contexto Identidad
    sys_prompt3, _, _ = preparar_contexto_vector("sabes con quién hablas")
    assert "DIRECTIVA PRIORITARIA DE IDENTIDAD" in sys_prompt3, "No detectó 'sabes con quién hablas'"
    print("✅ Detección de identidad 'sabes con quién hablas' OK")

    # 5. Test de Endpoint de Telemetría
    factory = RequestFactory()
    req = factory.get("/api/optimizer/stats/")
    resp = optimizer_stats(req)
    resp.render()
    stats_data = json.loads(resp.content)
    print("Stats obtenidas:", json.dumps(stats_data, indent=2))
    assert "query_stats" in stats_data
    assert "needs" in stats_data
    assert "system_efficiency" in stats_data["needs"]
    print("✅ Endpoint /api/optimizer/stats/ OK")

    print("\n🎉 TODOS LOS TESTS DE OPTIMIZADOR Y CONSULTAS INFORMALES PASARON CON ÉXITO.")

if __name__ == "__main__":
    run_tests()
