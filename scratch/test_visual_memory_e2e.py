import os
import sys
import base64
import cv2
import numpy as np

sys.path.insert(0, os.path.abspath("."))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vector5010.settings")
import django
django.setup()

from vectorapp.models import MemoryEntry
from vectorapp.views import preparar_contexto_vector

def generate_sample_face_b64():
    img = np.zeros((320, 240, 3), dtype=np.uint8)
    for y in range(320):
        img[y, :] = (120, 100, 80)
    cv2.circle(img, (120, 120), 45, (190, 210, 240), -1)
    cv2.circle(img, (105, 110), 5, (30, 20, 20), -1)
    cv2.circle(img, (135, 110), 5, (30, 20, 20), -1)
    cv2.ellipse(img, (120, 140), (15, 6), 0, 0, 180, (40, 40, 160), 2)
    _, buf = cv2.imencode('.jpg', img)
    return "data:image/jpeg;base64," + base64.b64encode(buf).decode('utf-8')

def test_scenario_a_photo_identification():
    print("\n--- ESCENARIO A: Adjuntar foto con 'mira este soy yo' ---")
    b64_img = generate_sample_face_b64()
    msg = "mira vector este soy yo"
    
    # Run preparar_contexto_vector with image and user Sebastian
    sys_prompt, turns, clean_msg = preparar_contexto_vector(
        mensaje=msg,
        imagen_input=b64_img,
        nombre_cliente="Sebastian"
    )

    print("¿Directiva de registro visual presente en system_prompt?:", "DIRECTIVA PRIORITARIA DE REGISTRO E IDENTIFICACIÓN VISUAL" in sys_prompt)
    assert "DIRECTIVA PRIORITARIA DE REGISTRO E IDENTIFICACIÓN VISUAL" in sys_prompt
    assert "DATOS DE VISIÓN POR COMPUTADORA EXTRAÍDOS DE LA FOTO" in sys_prompt
    assert "/media/user_photos/" in sys_prompt

    # Verify database entry created
    mem_entry = MemoryEntry.objects.filter(entry_type='visual_identity').order_by('-created_at').first()
    print("Última MemoryEntry creada:", mem_entry.id, mem_entry.content[:100] if mem_entry else "NINGUNA")
    assert mem_entry is not None
    assert "IDENTIDAD_VISUAL" in mem_entry.content
    assert "/media/user_photos/" in mem_entry.content
    print(">>> ESCENARIO A: APROBADO EXITOSAMENTE")

def test_scenario_b_recall_photo():
    print("\n--- ESCENARIO B: Consulta de recuerdo 'recuerdas mi foto y cómo me veo' ---")
    msg = "vector, recuerdas mi foto y cómo me veo?"
    
    sys_prompt, turns, clean_msg = preparar_contexto_vector(
        mensaje=msg,
        imagen_input="",
        nombre_cliente="Sebastian"
    )

    print("¿Directiva de recuerdo visual presente en system_prompt?:", "DIRECTIVA DE MEMORIA VISUAL REGISTRADA EN BASE DE DATOS" in sys_prompt)
    assert "DIRECTIVA DE MEMORIA VISUAL REGISTRADA EN BASE DE DATOS" in sys_prompt
    assert "TIENES REGISTRADA SU FOTOGRAFÍA EN TU BASE DE DATOS" in sys_prompt
    print(">>> ESCENARIO B: APROBADO EXITOSAMENTE")

def test_scenario_c_how_vector_sees_photos():
    print("\n--- ESCENARIO C: Pregunta de arquitectura 'cómo ves las fotos que te adjuntan' ---")
    msg = "vector, cómo ves las fotos que te adjuntan?"
    
    sys_prompt, turns, clean_msg = preparar_contexto_vector(
        mensaje=msg,
        imagen_input="",
        nombre_cliente="Sebastian"
    )

    print("¿Directiva de arquitectura visual presente?:", "DIRECTIVA SOBRE ARQUITECTURA Y ANÁLISIS DE FOTOS" in sys_prompt)
    assert "DIRECTIVA SOBRE ARQUITECTURA Y ANÁLISIS DE FOTOS" in sys_prompt
    assert "OpenCV & Haar Cascades" in sys_prompt
    assert "YOLOv3" in sys_prompt
    assert "MemoryEntry" in sys_prompt
    print(">>> ESCENARIO C: APROBADO EXITOSAMENTE")

def test_scenario_d_friend_identity():
    print("\n--- ESCENARIO D: Amiga (Juana) adjuntando foto 'mira soy yo juana' ---")
    b64_img = generate_sample_face_b64()
    msg = "mira vector soy yo juana esta es mi foto"
    
    sys_prompt, turns, clean_msg = preparar_contexto_vector(
        mensaje=msg,
        imagen_input=b64_img,
        nombre_cliente="Juana"
    )

    assert "DIRECTIVA PRIORITARIA DE REGISTRO E IDENTIFICACIÓN VISUAL" in sys_prompt
    assert "Juana te ha adjuntado una fotografía identificándose en ella" in sys_prompt
    assert "NUNCA la/lo llames Sebastian" in sys_prompt
    print(">>> ESCENARIO D: APROBADO EXITOSAMENTE (Juana identificada sin ser confundida con Sebastian)")

if __name__ == "__main__":
    test_scenario_a_photo_identification()
    test_scenario_b_recall_photo()
    test_scenario_c_how_vector_sees_photos()
    test_scenario_d_friend_identity()
    print("\n==========================================")
    print(">>> TODOS LOS ESCENARIOS E2E PASARON CON ÉXITO! <<<")
    print("==========================================")
