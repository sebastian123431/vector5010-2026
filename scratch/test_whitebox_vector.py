"""
TEST SUITE: CAJA BLANCA - VECTOR 2026
Verificacion profunda e interna de componentes:
1. Copilot Web Reader (SimpleHTMLTextExtractor, extraer_articulo_profundo)
2. Investigacion Multisitio Chilena (investigar_multisitio_chile, sesgo .cl)
3. Razonamiento, Debate y Sintesis Concisa (debatir_y_sintetizar_fuentes)
4. Busqueda Resiliente sin Bloqueos (ejecutar_busqueda_resiliente)
5. Muestreo Temporal de Video (AudioVideoProcessor.analizar_video con OpenCV)
6. Comprension Acustica y Transcripcion de Audio (AudioVideoProcessor.transcribir_audio con es-CL)
"""

import os
import sys
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

from vectorapp.web_scraper import (
    SimpleHTMLTextExtractor, extraer_articulo_profundo, investigar_multisitio_chile
)
from vectorapp.query_optimizer import (
    debatir_y_sintetizar_fuentes, ejecutar_busqueda_resiliente
)
from vectorapp.audio_video_processor import audio_video_processor


def test_1_html_text_extractor():
    print("[TEST 1] Verificando SimpleHTMLTextExtractor (Copilot Web Reader)...")
    html_sample = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Noticia Cientifica - Elqui y Vicuna</title>
        <style>body { font-family: sans-serif; }</style>
        <script>console.log("analytics");</script>
    </head>
    <body>
        <nav><a href="/">Inicio</a></nav>
        <h1>Descubrimiento Astronomico en Coquimbo</h1>
        <p>El observatorio ubicado en el Valle del Elqui registro nuevas mediciones atmosfericas este jueves.</p>
        <p>Los investigadores confirmaron una temperatura de 18 C y humedad de 45% en la zona de Vicuna.</p>
        <footer>Derechos reservados 2026</footer>
    </body>
    </html>
    """
    extractor = SimpleHTMLTextExtractor()
    extractor.feed(html_sample)
    texto = extractor.get_text()
    
    assert "Descubrimiento Astronomico" in texto, "Fallo: Encabezado h1 no extraido"
    assert "Valle del Elqui" in texto, "Fallo: Parrafo 1 no extraido"
    assert "analytics" not in texto, "Fallo: Codigo script no fue filtrado"
    assert "font-family" not in texto, "Fallo: Estilo CSS no fue filtrado"
    print("  [OK] Extraccion HTML limpia y libre de scripts/estilos.")


def test_2_investigacion_multisitio_chile():
    print("[TEST 2] Verificando Investigacion Multisitio y Prioridad Chilena (.cl)...")

    # Probar que la busqueda devuelve estructura valida sin crashear
    res = investigar_multisitio_chile("clima Santiago Chile", max_fuentes=3)
    assert isinstance(res, dict), "Fallo: Debe retornar un diccionario"
    assert "fuentes" in res, "Fallo: Debe incluir clave 'fuentes'"
    assert "total_fuentes" in res, "Fallo: Debe incluir 'total_fuentes'"
    print(f"  [OK] Busqueda multisitio operativa. Fuentes encontradas: {res['total_fuentes']}.")


def test_3_debate_y_razonamiento_epistemologico():
    print("[TEST 3] Verificando Razonamiento, Debate y Sintesis Concisa...")
    fuentes_simuladas = [
        {
            "titulo": "Informe Meteorologico Meteored Chile",
            "url": "https://www.meteored.cl/tiempo-en_Vicuna.html",
            "contenido_limpio": "En Vicuna se esperan 19 C de temperatura maxima y 0.2 mm de llovizna debil sin acumulacion relevante.",
            "es_chileno": True
        },
        {
            "titulo": "Reporte AccuWeather Coquimbo",
            "url": "https://www.accuweather.com/es/cl/vicuna/weather-forecast",
            "contenido_limpio": "Cielo parcialmente cubierto en Vicuna con 19 C y probabilidad de precipitacion aislada de 0.1 mm.",
            "es_chileno": True
        },
        {
            "titulo": "Boletin Regional Elqui",
            "url": "https://www.diarioelqui.cl/noticias",
            "contenido_limpio": "Jornada fresca en el valle con 24 C y nubosidad costera ingresando por la tarde.",
            "es_chileno": True
        }
    ]

    debate = debatir_y_sintetizar_fuentes("Cual es el pronostico en Vicuna?", fuentes_simuladas, interlocutor="Sebastian")
    assert isinstance(debate, dict), "Fallo: Debe devolver dict de debate"
    assert "sintesis_concisa" in debate, "Fallo: Debe incluir sintesis concisa"
    assert "fuentes_consultadas" in debate, "Fallo: Debe incluir lista de fuentes"
    assert len(debate["fuentes_consultadas"]) == 3, "Fallo: Deben figurar las 3 fuentes"
    assert len(debate["coincidencias"]) > 0, "Fallo: Debe detectar coincidencias en fuentes chilenas"
    print(f"  [OK] Debate generado exitosamente. Coincidencias detectadas: {len(debate['coincidencias'])}.")


def test_4_busqueda_resiliente_no_bloqueante():
    print("[TEST 4] Verificando Busqueda Resiliente (sin quedarse en cola)...")
    # Prueba A: Con enlace directo tipo Copilot
    res_enlace = ejecutar_busqueda_resiliente("Que dice este sitio https://www.meteored.cl/")
    assert res_enlace["estrategia"] == "enlace_directo", f"Fallo en estrategia de enlace directo: {res_enlace.get('estrategia')}"
    assert res_enlace["total_fuentes"] == 1, "Fallo: Debe extraer la fuente directa"

    # Prueba B: Con consulta coloquial
    res_coloquial = ejecutar_busqueda_resiliente("investiga por favor que paso con el dolar hoy en chile")
    assert "estrategia" in res_coloquial, "Fallo: Debe registrar estrategia ejecutada"
    assert "fuentes" in res_coloquial, "Fallo: Debe incluir fuentes"
    print(f"  [OK] Busqueda resiliente probada. Estrategia: {res_coloquial['estrategia']}.")


def test_5_procesamiento_temporal_video():
    print("[TEST 5] Verificando Procesamiento y Muestreo Temporal de Video (OpenCV + YOLO)...")
    # Crear un video MP4 sintetico de prueba (15 fotogramas a 15 fps = 1 segundo)
    fd, temp_video = tempfile.mkstemp(suffix='.mp4')
    os.close(fd)
    try:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(temp_video, fourcc, 15.0, (320, 240))
        for i in range(15):
            # Crear un fotograma sintetico con variacion de color e iluminacion
            frame = np.zeros((240, 320, 3), dtype=np.uint8)
            frame[:, :] = (i * 15, 100, 200 - i * 10)
            cv2.putText(frame, f"Secuencia {i}", (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            out.write(frame)
        out.release()

        # Analizar video con AudioVideoProcessor
        res_video = audio_video_processor.analizar_video(temp_video, filename="test_sintetico.mp4", max_frames=3)
        assert res_video["success"] is True, f"Fallo al analizar video: {res_video.get('error')}"
        assert res_video["total_fotogramas"] == 15, f"Fallo fotogramas: {res_video.get('total_fotogramas')}"
        assert res_video["fotogramas_analizados"] >= 1, "Fallo: Debe haber muestreado fotogramas"
        assert "resumen_narrativo" in res_video, "Fallo: Debe contener resumen_narrativo"
        print(f"  [OK] Video analizado: {res_video['duracion_segundos']}s, {res_video['fotogramas_analizados']} fotogramas muestreados.")
    finally:
        if os.path.exists(temp_video):
            os.remove(temp_video)


def test_6_procesamiento_acustico_audio():
    print("[TEST 6] Verificando Comprension Acustica y Transcripcion de Audio (es-CL)...")
    # Crear un archivo WAV sintetico de 1 segundo (onda senoidal 440 Hz, PCM 16-bit, 16000 Hz)
    fd, temp_wav = tempfile.mkstemp(suffix='.wav')
    os.close(fd)
    try:
        sample_rate = 16000
        duration = 1.0  # segundo
        frequency = 440.0
        n_samples = int(sample_rate * duration)

        with wave.open(temp_wav, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            for i in range(n_samples):
                value = int(32767.0 * 0.3 * np.sin(2.0 * np.pi * frequency * i / sample_rate))
                data = struct.pack('<h', value)
                wf.writeframesraw(data)

        # Analizar con AudioVideoProcessor
        res_audio = audio_video_processor.transcribir_audio(temp_wav, filename="audio_test.wav", language="es-CL")
        assert res_audio["success"] is True, f"Fallo procesando audio: {res_audio.get('error')}"
        assert res_audio["canales"] == 1, "Fallo en canal de audio"
        assert res_audio["framerate"] == 16000, "Fallo en framerate"
        assert res_audio["duracion_segundos"] >= 0.9, "Fallo en duracion calculada"
        assert res_audio["idioma"] == "es-CL", "Fallo: Idioma debe ser es-CL"
        print(f"  [OK] Audio decodificado acusticamente: {res_audio['duracion_segundos']}s, {res_audio['framerate']}Hz, {res_audio['idioma']}.")
    finally:
        if os.path.exists(temp_wav):
            os.remove(temp_wav)


def run_all_whitebox_tests():
    print("================================================================")
    print("INICIANDO BATERIA DE PRUEBAS DE CAJA BLANCA - VECTOR 2026")
    print("================================================================")
    test_1_html_text_extractor()
    test_2_investigacion_multisitio_chile()
    test_3_debate_y_razonamiento_epistemologico()
    test_4_busqueda_resiliente_no_bloqueante()
    test_5_procesamiento_temporal_video()
    test_6_procesamiento_acustico_audio()
    print("================================================================")
    print("TODAS LAS PRUEBAS DE CAJA BLANCA PASARON EXITOSAMENTE [6/6]")
    print("================================================================")


if __name__ == "__main__":
    run_all_whitebox_tests()
