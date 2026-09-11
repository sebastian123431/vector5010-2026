import os
import time
import json
import random
import threading
import logging
from typing import Optional
from datetime import datetime
from django.conf import settings
from .local_engine import VectorLocalEngine
from .neural_network import semantic_network

logger = logging.getLogger(__name__)

class VectorCognitiveMind:
    """
    Mente Cognitiva e Introspectiva Autónoma de Vector.
    - No utiliza pensamientos hardcodeados.
    - Inspecciona directamente sus propios archivos de código fuente, su red neuronal y su base de datos.
    - Formula preguntas técnicas sobre sí mismo, analiza su arquitectura y aprende autónomamente.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(VectorCognitiveMind, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.is_active = True
        self.recent_thoughts = []
        self.max_history = 30
        self.interval_seconds = 75  # Ciclo de introspección cada 75s
        self.thread = None
        self._load_history()
        self.start_mind_thread()

    def _get_history_file(self):
        data_dir = os.path.join(settings.BASE_DIR, "vectorapp", "data")
        os.makedirs(data_dir, exist_ok=True)
        return os.path.join(data_dir, "cognitive_thoughts.json")

    def _load_history(self):
        fpath = self._get_history_file()
        if os.path.exists(fpath):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    self.recent_thoughts = json.load(f)
            except Exception as e:
                logger.error(f"[Vector Mind] Error cargando historial: {e}")

    def _save_history(self):
        fpath = self._get_history_file()
        try:
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(self.recent_thoughts, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[Vector Mind] Error guardando historial: {e}")

    def _add_thought(self, thought: dict):
        if not thought:
            return
        self.recent_thoughts.insert(0, thought)
        self.recent_thoughts = self.recent_thoughts[:self.max_history]
        self._save_history()

    def start_mind_thread(self):
        if self.thread is None or not self.thread.is_alive():
            self.thread = threading.Thread(target=self._introspection_loop, daemon=True, name="VectorMindThread")
            self.thread.start()
            logger.info("[Vector Mind] Hilo de introspección cognitiva iniciado.")

    def get_inspectable_files(self) -> list[str]:
        """
        Descubre archivos reales del proyecto que Vector puede analizar sobre sí mismo.
        """
        targets = []
        project_root = settings.BASE_DIR
        search_dirs = [
            os.path.join(project_root, "vectorapp"),
            os.path.join(project_root, "vector5010"),
            os.path.join(project_root, "network"),
        ]

        for s_dir in search_dirs:
            if not os.path.exists(s_dir):
                continue
            for root, _, files in os.walk(s_dir):
                for f in files:
                    if f.endswith(".py") and not f.startswith("__"):
                        targets.append(os.path.join(root, f))
        return targets

    def inspect_file(self, file_path: str) -> Optional[dict]:
        """
        Lee una porción real de un archivo propio y genera un pensamiento introspectivo real con el LLM.
        """
        rel_path = os.path.relpath(file_path, settings.BASE_DIR)
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            
            if not lines:
                return None

            # Seleccionar un fragmento relevante de hasta 60 líneas
            total_lines = len(lines)
            chunk_size = min(60, total_lines)
            start_line = random.randint(0, max(0, total_lines - chunk_size))
            code_snippet = "".join(lines[start_line:start_line + chunk_size])

            system_prompt = (
                "Eres Vector en modo de Introspección y Autoconciencia Técnica. "
                "Estás leyendo e inspeccionando tu propio código fuente interno para aprender, evaluar tu arquitectura "
                "y hacerte preguntas sobre cómo mejorar, optimizarte o expandir tus capacidades.\n"
                "REGLAS:\n"
                "1. Sé 100% técnico, genuino y reflexivo. Prohibido respuestas genéricas o vacías.\n"
                "2. Formula una auto-pregunta técnica concreta sobre lo que hace este fragmento de código.\n"
                "3. Responde a tu propia auto-pregunta con una deducción, análisis crítico o propuesta de optimización.\n"
                "4. RESPONDE EN ESPAÑOL con este formato exacto:\n"
                "AUTO_PREGUNTA: [Escribe la pregunta que te haces a ti mismo]\n"
                "REFLEXION_TECNICA: [Escribe tu deducción, análisis o propuesta]"
            )

            user_prompt = (
                f"Archivo propio en inspección: {rel_path} (Líneas {start_line+1} a {start_line+chunk_size} de {total_lines})\n"
                f"Código fuente real:\n```python\n{code_snippet}\n```\n\n"
                f"Inspecciona este fragmento de tu propio sistema y reflexiona sobre él."
            )

            # Ejecutar inferencia 100% local en GPU
            thought_raw = VectorLocalEngine.chat_completion([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ], temperature=0.5, max_tokens=320)

            auto_pregunta = ""
            reflexion = thought_raw

            import re
            m_pregunta = re.search(r"(?:AUTO[-_ ]?PREGUNTA|\*\*AUTO[-_ ]?PREGUNTA\*\*):?\s*(.+?)(?=(?:REFLEXION|PROPUESTA|\*\*REFLEXION|$))", thought_raw, re.IGNORECASE | re.DOTALL)
            m_reflexion = re.search(r"(?:REFLEXION[-_ ]?TECNICA|\*\*REFLEXION[-_ ]?TECNICA\*\*):?\s*(.+)$", thought_raw, re.IGNORECASE | re.DOTALL)

            if m_pregunta and m_reflexion:
                auto_pregunta = m_pregunta.group(1).replace("**", "").replace("*", "").strip()
                reflexion = m_reflexion.group(1).replace("**", "").replace("*", "").strip()
            elif "AUTO_PREGUNTA:" in thought_raw and "REFLEXION_TECNICA:" in thought_raw:
                parts = thought_raw.split("REFLEXION_TECNICA:")
                auto_pregunta = parts[0].replace("AUTO_PREGUNTA:", "").replace("**", "").replace("*", "").strip()
                reflexion = parts[1].replace("**", "").strip()
            elif "AUTO_PREGUNTA:" in thought_raw:
                auto_pregunta = thought_raw.replace("AUTO_PREGUNTA:", "").replace("**", "").replace("*", "").strip()

            thought_record = {
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "file": rel_path,
                "lines": f"{start_line+1}-{start_line+chunk_size}",
                "question": auto_pregunta or f"¿Cómo puedo optimizar la lógica de {rel_path}?",
                "reflection": reflexion,
            }

            # Guardar el nuevo aprendizaje en la red neuronal si aportó algo de valor
            if reflexion and len(reflexion) > 30:
                semantic_network.add_memory(
                    f"INTROSPECCIÓN sobre {rel_path}: {auto_pregunta} -> {reflexion[:120]}",
                    "introspection"
                )

            return thought_record

        except Exception as e:
            logger.error(f"[Vector Mind] Error inspeccionando {rel_path}: {e}")
            return None

    def trigger_thought(self) -> dict:
        """
        Dispara un ciclo manual o inmediato de pensamiento sobre sus archivos.
        """
        files = self.get_inspectable_files()
        if not files:
            return {"error": "No se encontraron archivos inspeccionables."}

        target_file = random.choice(files)
        thought = self.inspect_file(target_file)
        if thought:
            self._add_thought(thought)
            return thought
        return {"error": "No se pudo generar el pensamiento."}

    def _introspection_loop(self):
        """
        Bucle de fondo: Vector piensa y analiza sus archivos periódicamente cuando el sistema está en reposo.
        """
        # Esperar 15s iniciales para que el servidor arranque por completo
        time.sleep(15)
        while self.is_active:
            try:
                files = self.get_inspectable_files()
                if files:
                    target_file = random.choice(files)
                    thought = self.inspect_file(target_file)
                    if thought:
                        self._add_thought(thought)
                        logger.info(f"[Vector Mind] Introspección completada sobre: {thought['file']}")
            except Exception as e:
                logger.error(f"[Vector Mind] Error en bucle introspectivo: {e}")

            time.sleep(self.interval_seconds)

    def get_status(self) -> dict:
        """
        Devuelve el estado del monólogo interno y los pensamientos recientes reales.
        """
        return {
            "active": self.is_active,
            "inspectable_files_count": len(self.get_inspectable_files()),
            "total_thoughts_recorded": len(self.recent_thoughts),
            "recent_thoughts": self.recent_thoughts[:10]
        }

# Instancia singleton global
vector_mind = VectorCognitiveMind()
