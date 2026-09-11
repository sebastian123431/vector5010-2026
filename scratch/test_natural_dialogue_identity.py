import os
import sys
import django
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vector5010.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from vectorapp.views import interactuar_stream, interactuar
from vectorapp.models import Interaction

def make_session_req(factory, path, data, session_dict=None):
    req = factory.post(path, data=json.dumps(data), content_type='application/json')
    middleware = SessionMiddleware(lambda r: None)
    middleware.process_request(req)
    if session_dict:
        for k, v in session_dict.items():
            req.session[k] = v
    req.session.save()
    return req

def get_stream_response(resp):
    chunks = list(resp.streaming_content)
    full = ""
    for ch in chunks:
        line = ch.decode('utf-8')
        for sub in line.split('\n'):
            if sub.startswith('data: '):
                try:
                    payload = json.loads(sub[6:])
                    if 'token' in payload:
                        full += payload['token']
                    elif 'full_response' in payload:
                        return payload['full_response']
                except Exception:
                    pass
    return full

def test_natural_flow():
    print("=== TEST FLUJO NATURAL DE IDENTIDAD DIALOGADA ===")
    factory = RequestFactory()

    # SESIÓN 1: Usuario entra anónimo
    s1 = {}
    print("\n--- SESION 1 (Anónimo -> Seba) ---")
    req1 = make_session_req(factory, '/api/chat/stream/', {'mensaje': '¿quién soy?'}, s1)
    res1 = interactuar_stream(req1)
    ans1 = get_stream_response(res1)
    print(f"User: '¿quién soy?'\nVector: '{ans1}'")
    assert "aún no me has dicho tu nombre" in ans1.lower() or "como te llamas" in ans1.lower(), f"Fallo anónimo: {ans1}"
    assert "seba" in ans1.lower() and "millaray" in ans1.lower()

    # Usuario responde 'soy seba'
    req2 = make_session_req(factory, '/api/chat/stream/', {'mensaje': 'soy seba'}, dict(req1.session))
    res2 = interactuar_stream(req2)
    ans2 = get_stream_response(res2)
    print(f"\nUser: 'soy seba'\nVector: '{ans2}'")
    assert "seba" in ans2.lower() and "creador" in ans2.lower(), f"Fallo saludo Seba: {ans2}"

    # Ahora usuario pregunta '¿quién soy?'
    req3 = make_session_req(factory, '/api/chat/stream/', {'mensaje': '¿quién soy?'}, dict(req2.session))
    res3 = interactuar_stream(req3)
    ans3 = get_stream_response(res3)
    print(f"\nUser: '¿quién soy?'\nVector: '{ans3}'")
    assert "seba" in ans3.lower() and "creador" in ans3.lower(), f"Fallo confirmación Seba: {ans3}"

    # SESIÓN 2: Amiga Millaray
    s2 = {}
    print("\n--- SESION 2 (Millaray) ---")
    req_m1 = make_session_req(factory, '/api/chat/stream/', {'mensaje': 'soy millaray'}, s2)
    res_m1 = interactuar_stream(req_m1)
    ans_m1 = get_stream_response(res_m1)
    print(f"User: 'soy millaray'\nVector: '{ans_m1}'")
    assert "millaray" in ans_m1.lower(), f"Fallo saludo Millaray: {ans_m1}"
    assert "creador" not in ans_m1.lower(), f"Millaray no debe ser llamada creador: {ans_m1}"

    # Millaray pregunta '¿cómo me llamo?'
    req_m2 = make_session_req(factory, '/api/chat/stream/', {'mensaje': '¿cómo me llamo?'}, dict(req_m1.session))
    res_m2 = interactuar_stream(req_m2)
    ans_m2 = get_stream_response(res_m2)
    print(f"\nUser: '¿cómo me llamo?'\nVector: '{ans_m2}'")
    assert "millaray" in ans_m2.lower(), f"Fallo nombre Millaray: {ans_m2}"
    assert "sebastian espíndola, mi creador" not in ans_m2.lower(), f"No debe decir que Millaray es Sebastian: {ans_m2}"

    # SESIÓN 3: Presentación directa de una sola palabra
    s3 = {}
    print("\n--- SESION 3 (Directa de una sola palabra: 'millaray') ---")
    req_d1 = make_session_req(factory, '/api/chat/stream/', {'mensaje': 'millaray'}, s3)
    res_d1 = interactuar_stream(req_d1)
    ans_d1 = get_stream_response(res_d1)
    print(f"User: 'millaray'\nVector: '{ans_d1}'")
    assert "millaray" in ans_d1.lower()

    req_d2 = make_session_req(factory, '/api/chat/stream/', {'mensaje': 'quien soy'}, dict(req_d1.session))
    res_d2 = interactuar_stream(req_d2)
    ans_d2 = get_stream_response(res_d2)
    print(f"\nUser: 'quien soy'\nVector: '{ans_d2}'")
    assert "millaray" in ans_d2.lower()

    print("\n¡TODAS LAS PRUEBAS DE DIÁLOGO NATURAL PASARON CON ÉXITO ROTUNDO!")

if __name__ == "__main__":
    test_natural_flow()
