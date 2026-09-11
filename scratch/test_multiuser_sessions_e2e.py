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
from vectorapp.views import interactuar_stream

def make_session_request(factory, path, data, session_dict=None):
    request = factory.post(
        path,
        data=json.dumps(data),
        content_type='application/json'
    )
    middleware = SessionMiddleware(lambda r: None)
    middleware.process_request(request)
    if session_dict:
        for k, v in session_dict.items():
            request.session[k] = v
    request.session.save()
    return request

def test_multiuser_e2e_sessions():
    print("=== TEST E2E: Sesiones de Navegador Aisladas para Amigos e Invitados ===")
    factory = RequestFactory()

    # 1. Amiga 'Juana' se conecta desde su celular / notebook
    juana_session = {}
    req_juana_1 = make_session_request(
        factory, 
        '/api/chat/stream/',
        {'mensaje': 'hola soy juana', 'nombre_cliente': 'Invitado'},
        juana_session
    )
    resp_juana_1 = interactuar_stream(req_juana_1)
    assert resp_juana_1.status_code == 200, f"Error HTTP {resp_juana_1.status_code}"
    
    # Consumir stream para verificar payload
    content_juana_1 = b"".join(list(resp_juana_1.streaming_content)).decode('utf-8')
    assert '"user_name": "Juana"' in content_juana_1, f"No se envió user_name Juana en SSE: {content_juana_1}"
    print("  [PASS] 1. 'hola soy juana' -> SSE transmite user_name: 'Juana'")
    
    # La sesión de Juana ahora tiene registrado 'Juana'
    assert req_juana_1.session.get('user_name') == 'Juana', "La sesión de Django debe guardar Juana"
    print("  [PASS] 2. Sesión HTTP de Juana guardó 'user_name': 'Juana'")

    # Siguiente pregunta de Juana: '¿quién soy?'
    req_juana_2 = make_session_request(
        factory,
        '/api/chat/stream/',
        {'mensaje': '¿quién soy yo?', 'nombre_cliente': 'Juana'},
        dict(req_juana_1.session)
    )
    resp_juana_2 = interactuar_stream(req_juana_2)
    assert resp_juana_2.status_code == 200
    content_juana_2 = b"".join(list(resp_juana_2.streaming_content)).decode('utf-8')
    assert "Juana" in content_juana_2, f"Vector no reconoció a Juana: {content_juana_2}"
    assert "creador" not in content_juana_2.lower() or "amiga" in content_juana_2.lower(), "Juana no debe ser tratada como creadora"
    print(f"  [PASS] 3. Juana pregunta '¿quién soy yo?' -> Vector responde reconociéndola como Juana")

    # 2. Sebastian en paralelo en su propia sesión
    seba_session = {}
    req_seba = make_session_request(
        factory,
        '/api/chat/stream/',
        {'mensaje': 'olle me llamo seba', 'nombre_cliente': 'Sebastian'},
        seba_session
    )
    resp_seba = interactuar_stream(req_seba)
    content_seba = b"".join(list(resp_seba.streaming_content)).decode('utf-8')
    assert '"user_name": "Sebastian"' in content_seba or '"user_name": "Seba"' in content_seba
    print("  [PASS] 4. 'olle me llamo seba' -> Vector reconoce a Sebastian")

    # 3. Millaray en paralelo
    milla_session = {}
    req_milla = make_session_request(
        factory,
        '/api/chat/stream/',
        {'mensaje': 'hola soy millaray', 'nombre_cliente': 'Invitado'},
        milla_session
    )
    resp_milla = interactuar_stream(req_milla)
    content_milla = b"".join(list(resp_milla.streaming_content)).decode('utf-8')
    assert '"user_name": "Millaray"' in content_milla
    print("  [PASS] 5. 'hola soy millaray' -> Vector reconoce a Millaray")

    print("\nTODAS LAS PRUEBAS DE SESIONES MULTIUSUARIO PASARON EXITOSAMENTE.")

if __name__ == "__main__":
    test_multiuser_e2e_sessions()
