import os
import sys
import uuid

sys.path.insert(0, os.path.abspath("."))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vector5010.settings")
import django
django.setup()

from vectorapp.models import Interaction
from vectorapp.views import preparar_contexto_vector

def main():
    sess_1 = f"chat_project_{uuid.uuid4().hex[:6]}"
    sess_2 = f"chat_weather_{uuid.uuid4().hex[:6]}"

    print(f"--- PASO 1: Conversación en Sesión 1 ({sess_1}) sobre refactorización ---")
    Interaction.objects.create(
        question="vamos a refactorizar el servicio de autenticación con JWT",
        answer="Entendido Sebastian, podemos estructurar una clase TokenManager.",
        session_id=sess_1,
        user_name="Sebastian"
    )
    Interaction.objects.create(
        question="agrega expiración de 15 minutos al access token",
        answer="Configurado timedelta(minutes=15) para el access token.",
        session_id=sess_1,
        user_name="Sebastian"
    )

    print(f"\n--- PASO 2: Nueva conversación en Sesión 2 ({sess_2}) sobre el Valle de Elqui ---")
    Interaction.objects.create(
        question="cómo está el cielo en vicuña hoy para mirar las estrellas?",
        answer="El cielo en Vicuña se encuentra parcialmente despejado con excelente visibilidad.",
        session_id=sess_2,
        user_name="Juana"
    )

    print("\n--- PASO 3: Construcción de contexto para pregunta en Sesión 2 ---")
    sys_prompt_2, turns_2, clean_msg_2 = preparar_contexto_vector(
        mensaje="y a qué hora se oculta el sol?",
        nombre_cliente="Juana",
        session_id=sess_2
    )
    print("Turnos en contexto de Sesión 2:", len(turns_2))
    turns_text_2 = " ".join(t['content'] for t in turns_2).lower()
    assert "jwt" not in turns_text_2, "Fallo: Sesión 2 contiene JWT de Sesión 1!"
    assert "autenticación" not in turns_text_2, "Fallo: Sesión 2 contiene autenticación de Sesión 1!"
    print(">>> Contexto de Sesión 2 verificado: Cero contaminación de Sesión 1")

    print(f"\n--- PASO 4: Reanudar Sesión 1 ({sess_1}) volviendo al punto de inicio ---")
    sys_prompt_1, turns_1, clean_msg_1 = preparar_contexto_vector(
        mensaje="ahora agrega el refresh token de 7 días",
        nombre_cliente="Sebastian",
        session_id=sess_1
    )
    print("Turnos recuperados en Sesión 1:", len(turns_1))
    turns_text_1 = " ".join(t['content'] for t in turns_1).lower()
    assert "jwt" in turns_text_1, "Fallo: Sesión 1 no recuperó el contexto de JWT!"
    assert "vicuña" not in turns_text_1, "Fallo: Sesión 1 contiene Vicuña de Sesión 2!"
    assert "estrellas" not in turns_text_1, "Fallo: Sesión 1 contiene estrellas de Sesión 2!"
    print(">>> Sesión 1 reanudada al punto exacto: Continuidad 100% preservada sin mezclar peras con manzanas")

    print("\n=======================================================")
    print(">>> PRUEBA E2E DE RESUMEN Y AISLAMIENTO APROBADA AL 100%! <<<")
    print("=======================================================")

if __name__ == "__main__":
    main()
