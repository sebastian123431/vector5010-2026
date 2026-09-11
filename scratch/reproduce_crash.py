import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vector5010.settings')
django.setup()

import traceback
from vectorapp.views import preparar_contexto_vector, interactuar_stream
from rest_framework.test import APIRequestFactory

factory = APIRequestFactory()

turn1_msg = "dime el tiempo en vicuña osea el clima"
turn1_resp = "vicuna osea el clima: +13°C, Lluvia localizada en las cercanías (Humedad: 77%, Viento: ↘13km/h)"

turn2_msg = "cual es la posibilidad de lluva en vicuña centro?"
historial = [
    {"role": "user", "content": turn1_msg},
    {"role": "assistant", "content": turn1_resp}
]

print("1. Probando preparar_contexto_vector...")
try:
    sys_prompt, history_turns, clean_msg = preparar_contexto_vector(
        mensaje=turn2_msg,
        session=None,
        imagen_input="",
        usuario=None,
        historial_input=historial,
        archivo_adjunto=None
    )
    print("preparar_contexto_vector EXITO:")
    print("clean_msg:", clean_msg)
    print("history_turns:", history_turns)
    print("sys_prompt snippet:", sys_prompt[:300])
except Exception as e:
    print("ERROR en preparar_contexto_vector:")
    traceback.print_exc()

print("\n2. Probando interactuar_stream...")
try:
    req = factory.post('/api/chat/stream/', {
        "mensaje": turn2_msg,
        "imagen": "",
        "historial": historial,
        "archivo": None
    }, format='json')

    response = interactuar_stream(req)
    print("Status code:", getattr(response, "status_code", None))
    print("Streaming content type:", getattr(response, "get", lambda k: None)("Content-Type"))

    print("Consumiendo tokens del generador...")
    for chunk in response.streaming_content:
        chunk_str = chunk.decode('utf-8') if isinstance(chunk, bytes) else str(chunk)
        print("CHUNK:", chunk_str[:80])
        if "done" in chunk_str:
            break
except Exception as e:
    print("ERROR en interactuar_stream:")
    traceback.print_exc()
