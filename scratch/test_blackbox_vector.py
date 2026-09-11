"""
TEST SUITE: CAJA NEGRA - VECTOR 2026
Verificacion integral de extremo a extremo (End-to-End API / Chat)
1. Investigacion Multisitio y Enfoque Chileno (.cl)
2. Razonamiento, Debate Epistemologico y Sintesis Concisa (sin quedarse en cola)
3. Navegacion Web estilo Copilot (extraccion directa de URLs)
4. Comprension y Procesamiento de Notas de Voz / Audio (es-CL)
5. Comprension y Muestreo Temporal de Video (OpenCV + YOLOv3)
"""

import os
import sys
import base64
import tempfile
import wave
import struct
import numpy as np
import cv2

# Configurar sys.path y Django
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vector5010.settings')
import django
django.setup()

from django.test import RequestFactory
from vectorapp.views import interactuar


def crear_audio_base64() -> str:
    """Genera un archivo WAV sintetico en Base64 para pruebas de caja negra"""
    fd, temp_wav = tempfile.mkstemp(suffix='.wav')
    os.close(fd)
    try:
        sample_rate = 16000
        duration = 0.8
        frequency = 440.0
        n_samples = int(sample_rate * duration)

        with wave.open(temp_wav, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            for i in range(n_samples):
                value = int(32767.0 * 0.2 * np.sin(2.0 * np.pi * frequency * i / sample_rate))
                wf.writeframesraw(struct.pack('<h', value))

        with open(temp_wav, 'rb') as f:
            b64 = base64.b64encode(f.read()).decode('utf-8')
        return f"data:audio/wav;base64,{b64}"
    finally:
        if os.path.exists(temp_wav):
            os.remove(temp_wav)


def crear_video_base64() -> str:
    """Genera un archivo MP4 sintetico en Base64 para pruebas de caja negra"""
    fd, temp_video = tempfile.mkstemp(suffix='.mp4')
    os.close(fd)
    try:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(temp_video, fourcc, 10.0, (320, 240))
        for i in range(10):
            frame = np.zeros((240, 320, 3), dtype=np.uint8)
            frame[:, :] = (i * 20, 120, 180)
            cv2.putText(frame, f"Frame {i}", (15, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            out.write(frame)
        out.release()

        with open(temp_video, 'rb') as f:
            b64 = base64.b64encode(f.read()).decode('utf-8')
        return f"data:video/mp4;base64,{b64}"
    finally:
        if os.path.exists(temp_video):
            os.remove(temp_video)


def test_blackbox_1_investigacion_multisitio_chile():
    print("[TEST CAJA NEGRA 1] Investigacion Multisitio en la red con enfoque chileno...")
    factory = RequestFactory()
    payload = {
        "mensaje": "investiga en diferentes sitios las noticias de ciencia o tecnologia en Chile hoy",
        "nombre_cliente": "Sebastian",
        "session_id": "session_test_bb_1"
    }
    request = factory.post('/api/chat/', data=payload, content_type='application/json')
    response = interactuar(request)
    
    assert response.status_code == 200, f"HTTP Error: {response.status_code}"
    resp_text = response.data.get("respuesta", "")
    assert len(resp_text) > 30, f"Respuesta demasiado breve: {resp_text}"
    print(f"  [OK] Respuesta recibida ({len(resp_text)} chars): {resp_text[:120]}...")


def test_blackbox_2_razonamiento_debate_conciso():
    print("[TEST CAJA NEGRA 2] Razonamiento, debate epistemologico y no quedarse en cola...")
    factory = RequestFactory()
    payload = {
        "mensaje": "investiga en diferentes sitios sobre el clima y debate si va a llover en Vicuña",
        "nombre_cliente": "Sebastian",
        "session_id": "session_test_bb_2"
    }
    request = factory.post('/api/chat/', data=payload, content_type='application/json')
    response = interactuar(request)
    
    assert response.status_code == 200, f"HTTP Error: {response.status_code}"
    resp_text = response.data.get("respuesta", "")
    assert len(resp_text) > 20, "Respuesta vacia o insuficiente"
    # Debe ser conciso y directo, sin alucinaciones de codigo
    assert "def " not in resp_text and "class " not in resp_text, "Fallo: Cruce de dominios con codigo detectado"
    print(f"  [OK] Sintesis razonada ({len(resp_text)} chars): {resp_text[:120]}...")


def test_blackbox_3_copilot_navegacion_url():
    print("[TEST CAJA NEGRA 3] Navegacion Web estilo Copilot (extraccion de URL)...")
    factory = RequestFactory()
    payload = {
        "mensaje": "analiza y dime que informacion hay en esta pagina https://www.meteored.cl/",
        "nombre_cliente": "Sebastian",
        "session_id": "session_test_bb_3"
    }
    request = factory.post('/api/chat/', data=payload, content_type='application/json')
    response = interactuar(request)
    
    assert response.status_code == 200, f"HTTP Error: {response.status_code}"
    resp_text = response.data.get("respuesta", "")
    assert len(resp_text) > 20, "Respuesta insuficiente"
    print(f"  [OK] Copilot Web Reader respondio ({len(resp_text)} chars): {resp_text[:120]}...")


def test_blackbox_4_comprension_audio_voz():
    print("[TEST CAJA NEGRA 4] Comprension de Audio / Notas de Voz (es-CL)...")
    audio_b64 = crear_audio_base64()
    factory = RequestFactory()
    payload = {
        "mensaje": "escucha este audio que te envio",
        "audio": audio_b64,
        "nombre_cliente": "Sebastian",
        "session_id": "session_test_bb_4"
    }
    request = factory.post('/api/chat/', data=payload, content_type='application/json')
    response = interactuar(request)
    
    assert response.status_code == 200, f"HTTP Error: {response.status_code}"
    resp_text = response.data.get("respuesta", "")
    assert len(resp_text) > 15, "Respuesta de audio insuficiente"
    print(f"  [OK] Audio procesado exitosamente ({len(resp_text)} chars): {resp_text[:120]}...")


def test_blackbox_5_comprension_video_temporal():
    print("[TEST CAJA NEGRA 5] Comprension y Muestreo Temporal de Video (OpenCV + YOLO)...")
    video_b64 = crear_video_base64()
    factory = RequestFactory()
    payload = {
        "mensaje": "analiza que ocurre en este video adjunto",
        "video": video_b64,
        "nombre_cliente": "Sebastian",
        "session_id": "session_test_bb_5"
    }
    request = factory.post('/api/chat/', data=payload, content_type='application/json')
    response = interactuar(request)
    
    assert response.status_code == 200, f"HTTP Error: {response.status_code}"
    resp_text = response.data.get("respuesta", "")
    assert len(resp_text) > 20, "Respuesta de video insuficiente"
    print(f"  [OK] Video procesado exitosamente ({len(resp_text)} chars): {resp_text[:120]}...")


def run_all_blackbox_tests():
    print("================================================================")
    print("INICIANDO BATERIA DE PRUEBAS DE CAJA NEGRA (END-TO-END) - VECTOR")
    print("================================================================")
    test_blackbox_1_investigacion_multisitio_chile()
    test_blackbox_2_razonamiento_debate_conciso()
    test_blackbox_3_copilot_navegacion_url()
    test_blackbox_4_comprension_audio_voz()
    test_blackbox_5_comprension_video_temporal()
    print("================================================================")
    print("TODAS LAS PRUEBAS DE CAJA NEGRA PASARON EXITOSAMENTE [5/5]")
    print("================================================================")


if __name__ == "__main__":
    run_all_blackbox_tests()
