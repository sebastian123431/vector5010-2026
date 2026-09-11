import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vector5010.settings')
import django
django.setup()

from vectorapp.views import LLM, preparar_contexto_vector, sanitizar_respuesta_vector
from langchain_core.messages import HumanMessage, SystemMessage

queries = [
    "como me llamo",
    "veeme el tiempo",
    "vigila o supervisa algun cambio",
    "necesito tu ayuda ayuadmr",
    "que recuerdas",
]

for q in queries:
    sys_p, history, msg_c = preparar_contexto_vector(q)
    messages = [SystemMessage(content=sys_p), HumanMessage(content=msg_c)]
    res = LLM.invoke(messages)
    clean = sanitizar_respuesta_vector(str(res.content))
    print(f"\n==========================================")
    print(f"User: '{q}'")
    print(f"Vector: {clean.strip()}")
