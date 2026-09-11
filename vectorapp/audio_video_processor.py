"""
VECTOR 2026 // Procesador Sensorial de Audio y Video
Módulo especializado para la comprensión de voz, notas de audio y análisis de archivos de video.
Integra:
- Transcripción y comprensión de notas de voz en español chileno (es-CL) con SpeechRecognition.
- Muestreo temporal y análisis visual de secuencias de video con OpenCV y YOLOv3.
"""

import os
import io
import wave
import tempfile
import base64
import cv2
import numpy as np
from typing import Dict, Any, List, Optional
from .vision import vector_vision


class AudioVideoProcessor:
    """
    Procesador multimodal para audio y video.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(AudioVideoProcessor, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        self.supported_audio_exts = {'.wav', '.mp3', '.ogg', '.webm', '.m4a'}
        self.supported_video_exts = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}

    def es_audio(self, filename: str) -> bool:
        ext = os.path.splitext(filename.lower())[1]
        return ext in self.supported_audio_exts

    def es_video(self, filename: str) -> bool:
        ext = os.path.splitext(filename.lower())[1]
        return ext in self.supported_video_exts

    def transcribir_audio(self, audio_input: Any, filename: str = "audio.wav", language: str = "es-CL") -> Dict[str, Any]:
        """
        Transcribe y comprende un archivo de audio o nota de voz.
        Soporta rutas en disco, bytes binarios o Base64.
        Prioriza reconocimiento de español chileno (es-CL).
        """
        temp_file_path = None
        try:
            # 1. Resolver entrada a archivo en disco
            if isinstance(audio_input, str):
                if audio_input.startswith('data:audio') or ';base64,' in audio_input:
                    base64_data = audio_input.split(';base64,')[-1]
                    raw_bytes = base64.b64decode(base64_data)
                    fd, temp_file_path = tempfile.mkstemp(suffix='.wav')
                    os.close(fd)
                    with open(temp_file_path, 'wb') as f:
                        f.write(raw_bytes)
                    audio_path = temp_file_path
                elif os.path.isfile(audio_input):
                    audio_path = audio_input
                else:
                    try:
                        raw_bytes = base64.b64decode(audio_input)
                        fd, temp_file_path = tempfile.mkstemp(suffix='.wav')
                        os.close(fd)
                        with open(temp_file_path, 'wb') as f:
                            f.write(raw_bytes)
                        audio_path = temp_file_path
                    except Exception:
                        return {"success": False, "error": "Ruta de audio no válida o formato no reconocido."}
            elif isinstance(audio_input, (bytes, bytearray)):
                fd, temp_file_path = tempfile.mkstemp(suffix='.wav')
                os.close(fd)
                with open(temp_file_path, 'wb') as f:
                    f.write(audio_input)
                audio_path = temp_file_path
            else:
                return {"success": False, "error": "Tipo de entrada de audio no compatible."}

            # 2. Análisis de parámetros acústicos básicos (WAV)
            duracion_sec = 0.0
            canales = 1
            framerate = 16000
            try:
                with wave.open(audio_path, 'rb') as wf:
                    frames = wf.getnframes()
                    framerate = wf.getframerate()
                    canales = wf.getnchannels()
                    duracion_sec = round(frames / float(framerate), 2)
            except Exception:
                # Si no es un WAV estándar, calcular tamaño como aproximación
                tam_bytes = os.path.getsize(audio_path)
                duracion_sec = round(tam_bytes / 32000.0, 1)

            # 3. Transcripción con SpeechRecognition (es-CL)
            texto_transcrito = ""
            confianza = "alta"
            try:
                import speech_recognition as sr
                r = sr.Recognizer()
                with sr.AudioFile(audio_path) as source:
                    r.adjust_for_ambient_noise(source, duration=0.2)
                    audio_data = r.record(source)
                
                # Reconocimiento con soporte chileno
                texto_transcrito = r.recognize_google(audio_data, language=language)
            except sr.UnknownValueError:
                texto_transcrito = ""
                confianza = "sin voz audible clara"
            except sr.RequestError as req_err:
                texto_transcrito = ""
                confianza = f"servicio no disponible: {req_err}"
            except Exception as e:
                texto_transcrito = ""
                confianza = f"error de formato de audio: {e}"

            es_exitoso = bool(texto_transcrito.strip())
            resumen = (
                f"Mensaje de voz / audio analizado ({duracion_sec}s, {canales} canal(es)). "
                f"Transcripción (español chileno): \"{texto_transcrito}\""
                if es_exitoso
                else f"Audio analizado ({duracion_sec}s). No se identificó voz humana clara o comprensible ({confianza})."
            )

            return {
                "success": True,
                "tipo": "audio_voz",
                "filename": filename,
                "duracion_segundos": duracion_sec,
                "canales": canales,
                "framerate": framerate,
                "idioma": language,
                "transcripcion": texto_transcrito,
                "tiene_voz": es_exitoso,
                "confianza": confianza,
                "resumen": resumen
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Fallo al procesar audio: {str(e)}"
            }
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except Exception:
                    pass

    def analizar_video(self, video_input: Any, filename: str = "video.mp4", max_frames: int = 5) -> Dict[str, Any]:
        """
        Abre un archivo de video con OpenCV, muestrea fotogramas a lo largo de su duración,
        aplica detección de objetos YOLOv3 y biometría Haar Cascades, y redacta una narrativa temporal.
        """
        temp_file_path = None
        cap = None
        try:
            # 1. Resolver archivo de video a disco
            if isinstance(video_input, str):
                if video_input.startswith('data:video') or ';base64,' in video_input:
                    base64_data = video_input.split(';base64,')[-1]
                    raw_bytes = base64.b64decode(base64_data)
                    fd, temp_file_path = tempfile.mkstemp(suffix='.mp4')
                    os.close(fd)
                    with open(temp_file_path, 'wb') as f:
                        f.write(raw_bytes)
                    video_path = temp_file_path
                elif os.path.isfile(video_input):
                    video_path = video_input
                else:
                    try:
                        raw_bytes = base64.b64decode(video_input)
                        fd, temp_file_path = tempfile.mkstemp(suffix='.mp4')
                        os.close(fd)
                        with open(temp_file_path, 'wb') as f:
                            f.write(raw_bytes)
                        video_path = temp_file_path
                    except Exception:
                        return {"success": False, "error": "Ruta de video no válida."}
            elif isinstance(video_input, (bytes, bytearray)):
                fd, temp_file_path = tempfile.mkstemp(suffix='.mp4')
                os.close(fd)
                with open(temp_file_path, 'wb') as f:
                    f.write(video_input)
                video_path = temp_file_path
            else:
                return {"success": False, "error": "Tipo de entrada de video no compatible."}

            # 2. Abrir con OpenCV VideoCapture
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return {"success": False, "error": "No se pudo decodificar el flujo de video con OpenCV."}

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration_sec = round(total_frames / fps, 2) if total_frames > 0 and fps > 0 else 0.0

            if total_frames <= 0:
                # Video vacío o no legible
                return {"success": False, "error": "El video no contiene fotogramas legibles."}

            # 3. Muestrear fotogramas equiespaciados
            step = max(1, total_frames // max_frames)
            sampled_indices = [min(total_frames - 1, i * step) for i in range(max_frames)]
            # Asegurar unicidad
            sampled_indices = sorted(list(set(sampled_indices)))

            timeline_analysis = []
            all_detected_objects = set()
            total_faces_seen = 0

            for idx in sampled_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ret, frame = cap.read()
                if not ret or frame is None:
                    continue

                timestamp_sec = round(idx / fps, 1)
                mins = int(timestamp_sec // 60)
                secs = int(timestamp_sec % 60)
                time_str = f"{mins:02d}:{secs:02d}"

                # Analizar fotograma con el motor de visión
                analysis = vector_vision.comprehensive_photo_analysis(frame)
                yolo = analysis.get('yolo', {})
                faces = analysis.get('faces', {})
                tech = analysis.get('technical', {})

                obj_names = [d.get('class') for d in yolo.get('detections', [])]
                all_detected_objects.update(obj_names)
                face_count = faces.get('count', 0)
                total_faces_seen += face_count

                timeline_analysis.append({
                    "timestamp": time_str,
                    "segundo": timestamp_sec,
                    "rostros": face_count,
                    "objetos": obj_names,
                    "resumen_escena": yolo.get('summary', 'Escena despejada'),
                    "iluminacion": tech.get('iluminacion', 'normal')
                })

            # 4. Redactar narración cronológica del video
            narracion = []
            narracion.append(f"📹 Análisis Secuencial de Video: '{filename}' ({duration_sec}s, {width}x{height}px, {fps:.1f} FPS):")
            for step_item in timeline_analysis:
                objs_str = ", ".join(step_item['objetos']) if step_item['objetos'] else "sin objetos destacados"
                narracion.append(
                    f"- [{step_item['timestamp']}]: {step_item['resumen_escena']}. "
                    f"Rostros detectados: {step_item['rostros']}. Iluminación: {step_item['iluminacion']}."
                )

            resumen_global = " ".join(narracion)

            return {
                "success": True,
                "tipo": "video",
                "filename": filename,
                "duracion_segundos": duration_sec,
                "fps": round(fps, 1),
                "resolucion": f"{width}x{height}",
                "total_fotogramas": total_frames,
                "fotogramas_analizados": len(timeline_analysis),
                "objetos_globales": list(all_detected_objects),
                "rostros_detectados_total": total_faces_seen,
                "linea_de_tiempo": timeline_analysis,
                "resumen_narrativo": resumen_global
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Fallo al analizar video: {str(e)}"
            }
        finally:
            if cap:
                cap.release()
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except Exception:
                    pass


# Instancia Singleton Global
audio_video_processor = AudioVideoProcessor()
