import os
import cv2
import numpy as np
import base64
import re
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

class VectorVision:
    """
    Sistema de visión por computadora de Vector basado en YOLOv3 y OpenCV.
    Permite detectar personas, objetos del entorno y describir lo que ve en tiempo real.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(VectorVision, cls).__new__(cls)
        return cls._instance

    def __init__(self, base_dir: Optional[str] = None):
        if hasattr(self, '_initialized') and self._initialized:
            return

        if base_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        self.yolo_dir = os.path.join(base_dir, 'yolo')
        self.cfg_path = os.path.join(self.yolo_dir, 'yolov3.cfg')
        self.weights_path = os.path.join(self.yolo_dir, 'yolov3.weights')
        self.names_path = os.path.join(self.yolo_dir, 'coco.names')

        self.classes = []
        self.net = None
        self.output_layers = []
        self.face_cascade = None
        self._load_model()
        self._initialized = True

    def _load_model(self):
        try:
            if os.path.exists(self.names_path):
                with open(self.names_path, 'r', encoding='utf-8') as f:
                    self.classes = [line.strip() for line in f.readlines()]
            else:
                self.classes = ["persona", "objeto"]

            if os.path.exists(self.cfg_path) and os.path.exists(self.weights_path):
                self.net = cv2.dnn.readNetFromDarknet(self.cfg_path, self.weights_path)
                self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
                self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

                layer_names = self.net.getLayerNames()
                self.output_layers = [layer_names[i - 1] for i in self.net.getUnconnectedOutLayers()]
                print("[Vector Visión] Red YOLOv3 inicializada con éxito.")
            else:
                print(f"[Vector Visión] Archivos de YOLO no encontrados en: {self.yolo_dir}")
        except Exception as e:
            print(f"[Vector Visión] Error cargando YOLO: {e}")
            self.net = None

        # Cargar clasificador Haar Cascade para detección facial biométrica
        try:
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            if os.path.exists(cascade_path):
                self.face_cascade = cv2.CascadeClassifier(cascade_path)
                print("[Vector Visión] Clasificador biométrico facial (Haar Cascade) activo.")
            else:
                self.face_cascade = None
        except Exception as e:
            print(f"[Vector Visión] Error cargando clasificador facial: {e}")
            self.face_cascade = None

    def detect_from_image(self, image_np: np.ndarray, confidence_threshold: float = 0.5) -> Dict[str, Any]:
        """
        Procesa una imagen numpy (BGR) y devuelve los objetos detectados con sus cajas.
        """
        if self.net is None:
            return {"error": "Modelo de visión no disponible", "detections": [], "summary": "Visión desconectada"}

        height, width, _ = image_np.shape
        # Crear blob para YOLO (416x416)
        blob = cv2.dnn.blobFromImage(image_np, 1 / 255.0, (416, 416), swapRB=True, crop=False)
        self.net.setInput(blob)
        outs = self.net.forward(self.output_layers)

        class_ids = []
        confidences = []
        boxes = []

        for out in outs:
            for detection in out:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                if confidence > confidence_threshold:
                    center_x = int(detection[0] * width)
                    center_y = int(detection[1] * height)
                    w = int(detection[2] * width)
                    h = int(detection[3] * height)
                    x = int(center_x - w / 2)
                    y = int(center_y - h / 2)

                    boxes.append([x, y, w, h])
                    confidences.append(float(confidence))
                    class_ids.append(class_id)

        indexes = cv2.dnn.NMSBoxes(boxes, confidences, confidence_threshold, 0.4)

        # Diccionario de traducción al español para COCO
        translations = {
            'person': 'persona', 'bicycle': 'bicicleta', 'car': 'auto', 'motorbike': 'motocicleta',
            'aeroplane': 'avión', 'bus': 'autobús', 'train': 'tren', 'truck': 'camión', 'boat': 'barco',
            'traffic light': 'semáforo', 'stop sign': 'señal de pare', 'bench': 'banco', 'bird': 'pájaro',
            'cat': 'gato', 'dog': 'perro', 'horse': 'caballo', 'sheep': 'oveja', 'cow': 'vaca',
            'backpack': 'mochila', 'umbrella': 'paraguas', 'handbag': 'bolso', 'tie': 'corbata',
            'suitcase': 'maleta', 'bottle': 'botella', 'cup': 'taza', 'fork': 'tenedor', 'knife': 'cuchillo',
            'spoon': 'cuchara', 'bowl': 'tazón', 'banana': 'plátano', 'apple': 'manzana', 'sandwich': 'sándwich',
            'chair': 'silla', 'sofa': 'sofá', 'pottedplant': 'planta', 'bed': 'cama', 'diningtable': 'mesa',
            'tvmonitor': 'pantalla/TV', 'laptop': 'laptop/computadora', 'mouse': 'mouse', 'remote': 'control remoto',
            'keyboard': 'teclado', 'cell phone': 'teléfono celular', 'book': 'libro', 'clock': 'reloj'
        }

        detected_items = []
        counts = {}

        if len(indexes) > 0:
            flat_indexes = np.array(indexes).flatten()
            for i in flat_indexes:
                label = self.classes[class_ids[i]] if class_ids[i] < len(self.classes) else "objeto"
                es_label = translations.get(label, label)
                counts[es_label] = counts.get(es_label, 0) + 1
                detected_items.append({
                    "label": es_label,
                    "confidence": round(confidences[i], 2),
                    "box": boxes[i]
                })

        if detected_items:
            summary_parts = [f"{cnt} {lbl}" if cnt == 1 else f"{cnt} {lbl}s" for lbl, cnt in counts.items()]
            summary = "Veo en este momento: " + ", ".join(summary_parts) + "."
        else:
            summary = "No detecto personas ni objetos reconocibles en este ángulo."

        return {
            "success": True,
            "count": len(detected_items),
            "detections": detected_items,
            "summary": summary
        }

    def detect_from_base64(self, base64_str: str) -> Dict[str, Any]:
        """
        Decodifica un fotograma en Base64 (enviado desde la cámara del navegador) y ejecuta detección.
        """
        try:
            if "," in base64_str:
                base64_str = base64_str.split(",")[1]

            img_bytes = base64.b64decode(base64_str)
            nparr = np.frombuffer(img_bytes, np.uint8)
            img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if img_np is None:
                return {"error": "No se pudo decodificar la imagen", "summary": "Error de imagen"}

            return self.detect_from_image(img_np)
        except Exception as e:
            return {"error": str(e), "summary": f"Error procesando visión: {e}"}

    def detect_faces(self, image_np: np.ndarray) -> Dict[str, Any]:
        """
        Detecta rostros humanos en la imagen mediante Haar Cascades de OpenCV.
        Devuelve el conteo de rostros, cajas delimitadoras y posición en el encuadre.
        """
        if self.face_cascade is None or self.face_cascade.empty():
            return {"count": 0, "faces": [], "summary": "Clasificador facial no disponible"}

        try:
            gray = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)
            height, width = gray.shape
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(28, 28)
            )

            face_list = []
            for (x, y, w, h) in faces:
                rel_area = round(((w * h) / (width * height)) * 100, 1)
                cx = x + w / 2
                pos_h = "centro"
                if cx < width * 0.35:
                    pos_h = "lateral izquierdo"
                elif cx > width * 0.65:
                    pos_h = "lateral derecho"

                plano = "primer plano" if rel_area > 12 else ("plano medio" if rel_area > 4 else "plano lejano")
                face_list.append({
                    "box": [int(x), int(y), int(w), int(h)],
                    "area_pct": rel_area,
                    "posicion": pos_h,
                    "plano": plano
                })

            count = len(face_list)
            if count == 1:
                f0 = face_list[0]
                summary = f"1 rostro detectado en {f0['posicion']} ({f0['plano']}, ocupa {f0['area_pct']}% del encuadre)"
            elif count > 1:
                summary = f"{count} rostros detectados en el encuadre"
            else:
                summary = "Ningún rostro frontal detectado con claridad"

            return {
                "count": count,
                "faces": face_list,
                "summary": summary
            }
        except Exception as e:
            return {"count": 0, "faces": [], "summary": f"Error detectando rostros: {e}"}

    def analyze_visual_attributes(self, image_np: np.ndarray) -> Dict[str, Any]:
        """
        Analiza características técnicas fotográficas: dimensiones, orientación,
        nivel de luminosidad, contraste, nitidez y paleta de colores dominante.
        """
        try:
            height, width, channels = image_np.shape
            ratio = width / height if height > 0 else 1.0

            if ratio < 0.85:
                orientacion = "vertical (formato retrato)"
            elif ratio > 1.25:
                orientacion = "horizontal (formato apaisado)"
            else:
                orientacion = "cuadrada o proporción balanceada"

            gray = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)
            mean_brightness = float(np.mean(gray))
            contrast = float(np.std(gray))

            # Nitidez mediante varianza laplaciana
            laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            if laplacian_var > 250:
                nitidez = "alta nitidez y definición clara"
            elif laplacian_var > 70:
                nitidez = "nitidez media estándar"
            else:
                nitidez = "enfoque suave o baja definición"

            # Interpretación de luminosidad
            if mean_brightness < 60:
                iluminacion = f"tenue o baja luminosidad (brillo: {round(mean_brightness, 1)}/255)"
            elif mean_brightness < 115:
                iluminacion = f"iluminación de interior o moderada (brillo: {round(mean_brightness, 1)}/255)"
            elif mean_brightness < 190:
                iluminacion = f"buena iluminación / luz natural balanceada (brillo: {round(mean_brightness, 1)}/255)"
            else:
                iluminacion = f"alta luminosidad o luz intensa (brillo: {round(mean_brightness, 1)}/255)"

            # Tonalidad dominante
            b_avg = float(np.mean(image_np[:, :, 0]))
            g_avg = float(np.mean(image_np[:, :, 1]))
            r_avg = float(np.mean(image_np[:, :, 2]))
            if r_avg > b_avg + 15 and r_avg > g_avg + 5:
                tonos = "tonalidades cálidas (rojos, cobrizos o dorados)"
            elif b_avg > r_avg + 15:
                tonos = "tonalidades frías o azuladas"
            elif g_avg > r_avg + 10 and g_avg > b_avg + 10:
                tonos = "tonalidades verdosas o naturales"
            else:
                tonos = "tonos neutros y equilibrados"

            return {
                "width": width,
                "height": height,
                "orientacion": orientacion,
                "brillo": round(mean_brightness, 1),
                "iluminacion": iluminacion,
                "contraste": round(contrast, 1),
                "nitidez": nitidez,
                "tonos": tonos
            }
        except Exception as e:
            return {
                "width": 0, "height": 0,
                "orientacion": "desconocida",
                "iluminacion": "no calculada",
                "nitidez": "estándar",
                "tonos": "no determinados",
                "error": str(e)
            }

    def comprehensive_photo_analysis(self, image_input: Any) -> Dict[str, Any]:
        """
        Ejecuta un diagnóstico visual exhaustivo combinando:
        1. Atributos fotográficos técnicos (resolución, orientación, luminosidad, nitidez, tonos).
        2. Biometría facial con Haar Cascades (rostros, posición y plano).
        3. Red neuronal profunda YOLOv3 (detección de personas, vestimenta y objetos).
        Genera un reporte estructurado y en texto natural listo para el prompt de Vector.
        """
        img_np = None
        if isinstance(image_input, str):
            if "," in image_input:
                image_input = image_input.split(",")[1]
            try:
                img_bytes = base64.b64decode(image_input)
                nparr = np.frombuffer(img_bytes, np.uint8)
                img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            except Exception as e:
                return {"success": False, "error": f"Fallo al decodificar imagen: {e}", "summary": "Error de imagen"}
        elif isinstance(image_input, np.ndarray):
            img_np = image_input

        if img_np is None:
            return {"success": False, "error": "Imagen no válida o vacía", "summary": "Imagen vacía"}

        # 1. Atributos visuales y fotográficos
        attribs = self.analyze_visual_attributes(img_np)
        
        # 2. Detección de rostros
        faces = self.detect_faces(img_np)

        # 3. Detección de objetos y personas con YOLOv3
        yolo_res = self.detect_from_image(img_np)

        # Construcción de síntesis descriptiva profesional J.A.R.V.I.S.
        partes = []
        w, h = attribs.get("width", 0), attribs.get("height", 0)
        partes.append(f"Fotografía {attribs.get('orientacion', 'estándar')} de {w}x{h} px con {attribs.get('iluminacion', 'iluminación estándar')} y {attribs.get('nitidez', 'enfoque estándar')}")

        if faces.get("count", 0) > 0:
            partes.append(faces.get("summary"))
        else:
            partes.append("sin rostros frontales identificables")

        if yolo_res.get("count", 0) > 0:
            summary_clean = yolo_res.get("summary", "").replace("Veo en este momento: ", "").rstrip(".")
            partes.append(f"elementos reconocidos por YOLOv3: {summary_clean}")

        partes.append(f"paleta dominante: {attribs.get('tonos')}")

        resumen_completo = ". ".join(partes) + "."

        return {
            "success": True,
            "attributes": attribs,
            "faces": faces,
            "yolo": yolo_res,
            "summary": resumen_completo,
            "technical_report": (
                f"- Resolución y orientación: {w}x{h} px, {attribs.get('orientacion')}\n"
                f"- Rostros detectados: {faces.get('count', 0)} ({faces.get('summary')})\n"
                f"- Objetos / personas (YOLOv3): {yolo_res.get('summary')}\n"
                f"- Iluminación: {attribs.get('iluminacion')}, Nitidez: {attribs.get('nitidez')}\n"
                f"- Paleta de color: {attribs.get('tonos')}"
            )
        }

    def save_user_photo(self, base64_str: str, user_name: str, base_media_dir: Optional[str] = None) -> Tuple[str, str]:
        """
        Almacena la fotografía del usuario en el disco dentro de media/user_photos/
        Retorna una tupla (ruta_absoluta, url_relativa_media).
        """
        if "," in base64_str:
            base64_str = base64_str.split(",")[1]

        if base_media_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            base_media_dir = os.path.join(base_dir, "media", "user_photos")

        os.makedirs(base_media_dir, exist_ok=True)

        clean_user = re.sub(r'[^a-zA-Z0-9_-]', '_', (user_name or "usuario").lower()).strip('_')
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"foto_{clean_user}_{timestamp_str}.jpg"
        abs_path = os.path.join(base_media_dir, filename)
        rel_url = f"/media/user_photos/{filename}"

        img_bytes = base64.b64decode(base64_str)
        with open(abs_path, "wb") as f:
            f.write(img_bytes)

        return abs_path, rel_url

# Instancia singleton accesible para el proyecto
vector_vision = VectorVision()
