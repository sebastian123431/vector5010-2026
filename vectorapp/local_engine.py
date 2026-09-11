import os
import time
import atexit
import subprocess
import requests
from requests.adapters import HTTPAdapter
import logging
import threading
from collections import OrderedDict
from django.conf import settings

logger = logging.getLogger(__name__)

class VectorLocalEngine:
    """
    Gestor 100% Local y Autónomo de Inferencia de LLM y Embeddings.
    Ejecuta binarios C++ nativos compilados con aceleración NVIDIA CUDA (RTX 3050 Ti)
    sin depender de Ollama, servicios externos ni internet.
    """
    _chat_process = None
    _embed_process = None
    _chat_log_file = None
    _embed_log_file = None
    _session = None
    _session_lock = threading.Lock()
    _embedding_cache: OrderedDict[str, list[float]] = OrderedDict()
    _cache_lock = threading.Lock()
    _MAX_CACHE_SIZE = 2048

    @classmethod
    def get_session(cls) -> requests.Session:
        """Retorna una sesión HTTP con connection pooling y keep-alive hacia los motores locales."""
        if cls._session is None:
            with cls._session_lock:
                if cls._session is None:
                    session = requests.Session()
                    adapter = HTTPAdapter(pool_connections=15, pool_maxsize=30, max_retries=1)
                    session.mount("http://", adapter)
                    cls._session = session
        return cls._session

    @classmethod
    def _is_alive(cls, port: int) -> bool:
        try:
            r = cls.get_session().get(f"http://127.0.0.1:{port}/health", timeout=0.8)
            return r.status_code == 200
        except Exception:
            return False

    @classmethod
    def start_chat_engine(cls) -> bool:
        if cls._is_alive(settings.LOCAL_CHAT_PORT):
            return True

        bin_path = getattr(settings, "LOCAL_LLM_BIN", None)
        model_path = getattr(settings, "LOCAL_CHAT_MODEL", None)

        if not bin_path or not os.path.exists(bin_path):
            logger.error(f"Binario local no encontrado: {bin_path}")
            return False
        if not model_path or not os.path.exists(model_path):
            logger.error(f"Modelo GGUF de chat no encontrado: {model_path}")
            return False

        logs_dir = os.path.join(settings.BASE_DIR, "logs")
        os.makedirs(logs_dir, exist_ok=True)
        if cls._chat_log_file and not cls._chat_log_file.closed:
            cls._chat_log_file.close()
        cls._chat_log_file = open(os.path.join(logs_dir, "llama_chat.log"), "a", encoding="utf-8")

        cmd = [
            bin_path,
            "-m", model_path,
            "-ngl", "99",               # 100% capas a GPU CUDA
            "-c", "4096",               # Ventana de contexto
            "--port", str(settings.LOCAL_CHAT_PORT),
            "--host", "127.0.0.1",
            "-cb",                      # Continuous batching
        ]

        creation_flags = 0
        if os.name == 'nt':
            creation_flags = subprocess.CREATE_NO_WINDOW

        cls._chat_process = subprocess.Popen(
            cmd,
            stdout=cls._chat_log_file,
            stderr=cls._chat_log_file,
            creationflags=creation_flags
        )

        for _ in range(25):
            time.sleep(0.4)
            if cls._is_alive(settings.LOCAL_CHAT_PORT):
                logger.info(f"Motor de chat local iniciado con éxito en puerto {settings.LOCAL_CHAT_PORT}")
                return True

        logger.error(f"Tiempo de espera agotado al iniciar motor de chat en puerto {settings.LOCAL_CHAT_PORT}")
        if cls._chat_process:
            try:
                cls._chat_process.terminate()
            except Exception:
                pass
            cls._chat_process = None
        return False

    @classmethod
    def start_embed_engine(cls) -> bool:
        if cls._is_alive(settings.LOCAL_EMBED_PORT):
            return True

        bin_path = getattr(settings, "LOCAL_LLM_BIN", None)
        model_path = getattr(settings, "LOCAL_EMBED_MODEL", None)

        if not bin_path or not os.path.exists(bin_path):
            logger.error(f"Binario local no encontrado: {bin_path}")
            return False
        if not model_path or not os.path.exists(model_path):
            logger.error(f"Modelo GGUF de embeddings no encontrado: {model_path}")
            return False

        logs_dir = os.path.join(settings.BASE_DIR, "logs")
        os.makedirs(logs_dir, exist_ok=True)
        if cls._embed_log_file and not cls._embed_log_file.closed:
            cls._embed_log_file.close()
        cls._embed_log_file = open(os.path.join(logs_dir, "llama_embed.log"), "a", encoding="utf-8")

        cmd = [
            bin_path,
            "-m", model_path,
            "--embedding",
            "-ngl", "99",               # 100% capas a GPU CUDA
            "--port", str(settings.LOCAL_EMBED_PORT),
            "--host", "127.0.0.1",
        ]

        creation_flags = 0
        if os.name == 'nt':
            creation_flags = subprocess.CREATE_NO_WINDOW

        cls._embed_process = subprocess.Popen(
            cmd,
            stdout=cls._embed_log_file,
            stderr=cls._embed_log_file,
            creationflags=creation_flags
        )

        for _ in range(20):
            time.sleep(0.3)
            if cls._is_alive(settings.LOCAL_EMBED_PORT):
                logger.info(f"Motor de embeddings local iniciado con éxito en puerto {settings.LOCAL_EMBED_PORT}")
                return True

        logger.error(f"Tiempo de espera agotado al iniciar motor de embeddings en puerto {settings.LOCAL_EMBED_PORT}")
        if cls._embed_process:
            try:
                cls._embed_process.terminate()
            except Exception:
                pass
            cls._embed_process = None
        return False

    @classmethod
    def shutdown_engines(cls):
        """Detiene los procesos de inferencia local y cierra los archivos de log."""
        if cls._chat_process and cls._chat_process.poll() is None:
            try:
                cls._chat_process.terminate()
                cls._chat_process.wait(timeout=2)
            except Exception:
                try:
                    cls._chat_process.kill()
                except Exception:
                    pass
            cls._chat_process = None

        if cls._chat_log_file and not cls._chat_log_file.closed:
            try:
                cls._chat_log_file.close()
            except Exception:
                pass
            cls._chat_log_file = None

        if cls._embed_process and cls._embed_process.poll() is None:
            try:
                cls._embed_process.terminate()
                cls._embed_process.wait(timeout=2)
            except Exception:
                try:
                    cls._embed_process.kill()
                except Exception:
                    pass
            cls._embed_process = None

        if cls._embed_log_file and not cls._embed_log_file.closed:
            try:
                cls._embed_log_file.close()
            except Exception:
                pass
            cls._embed_log_file = None

        if cls._session:
            try:
                cls._session.close()
            except Exception:
                pass
            cls._session = None

    @classmethod
    def ensure_engines(cls):
        cls.start_chat_engine()
        cls.start_embed_engine()

    @classmethod
    def chat_completion(cls, messages: list, temperature: float = 0.3, max_tokens: int = 1024) -> str:
        """
        Envía mensajes al motor de chat local (OpenAI-compatible) y devuelve el texto
        usando conexión HTTP persistente Keep-Alive.
        """
        if not cls._is_alive(settings.LOCAL_CHAT_PORT):
            if not cls.start_chat_engine():
                raise RuntimeError("No se pudo iniciar el motor local de chat.")

        url = f"http://127.0.0.1:{settings.LOCAL_CHAT_PORT}/v1/chat/completions"
        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "repeat_penalty": 1.18,
            "presence_penalty": 0.2
        }

        last_err = None
        for intento in range(3):
            try:
                resp = cls.get_session().post(url, json=payload, timeout=60)
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            except Exception as e:
                last_err = e
                if intento < 2:
                    time.sleep(0.4 * (intento + 1))
        raise last_err or RuntimeError("Error desconocido en chat_completion")

    @classmethod
    def embed_documents(cls, texts: list[str]) -> list[list[float]]:
        """
        Calcula embeddings vectoriales de una lista de textos usando el motor GGUF local
        con conexión Keep-Alive y caché en RAM de alta velocidad.
        """
        if not cls._is_alive(settings.LOCAL_EMBED_PORT):
            if not cls.start_embed_engine():
                raise RuntimeError("No se pudo iniciar el motor local de embeddings.")

        url = f"http://127.0.0.1:{settings.LOCAL_EMBED_PORT}/v1/embeddings"
        session = cls.get_session()
        embeddings = []
        for text in texts:
            clean_text = (text or " ").strip()[:1500]
            if not clean_text:
                clean_text = " "

            with cls._cache_lock:
                if clean_text in cls._embedding_cache:
                    cls._embedding_cache.move_to_end(clean_text)
                    embeddings.append(cls._embedding_cache[clean_text])
                    continue

            try:
                resp = session.post(url, json={"input": clean_text}, timeout=20)
                resp.raise_for_status()
                res_data = resp.json()
                vec = res_data["data"][0]["embedding"]
                embeddings.append(vec)
                with cls._cache_lock:
                    if len(cls._embedding_cache) >= cls._MAX_CACHE_SIZE:
                        cls._embedding_cache.popitem(last=False)
                    cls._embedding_cache[clean_text] = vec
            except Exception as e:
                logger.warning(f"Fallo calculando embedding: {e}")
                embeddings.append([0.0] * 768)
        return embeddings

    @classmethod
    def embed_query(cls, text: str) -> list[float]:
        """
        Calcula el embedding de una sola consulta con caché LRU inmediato (<0.01ms en memoria).
        """
        clean_text = (text or " ").strip()[:1500]
        if not clean_text:
            clean_text = " "

        with cls._cache_lock:
            if clean_text in cls._embedding_cache:
                cls._embedding_cache.move_to_end(clean_text)
                return cls._embedding_cache[clean_text]

        res = cls.embed_documents([clean_text])[0]
        return res

# Registrar shutdown para limpiar procesos llama-server al detener o reiniciar Django
atexit.register(VectorLocalEngine.shutdown_engines)

from typing import List, Optional, Any
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.outputs import ChatResult, ChatGeneration

class LocalChatLLM(BaseChatModel):
    """
    Motor de Chat 100% Local compatible con LangChain y LangGraph.
    Conecta directamente con VectorLocalEngine (llama-server CUDA C++).
    """
    temperature: float = 0.3
    max_tokens: int = 1024

    @property
    def _llm_type(self) -> str:
        return "vector_local_llm"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any
    ) -> ChatResult:
        formatted = []
        for m in messages:
            content = getattr(m, "content", str(m))
            role = "user"
            type_str = getattr(m, "type", "").lower()
            cls_name = m.__class__.__name__
            if "system" in type_str or cls_name == "SystemMessage":
                role = "system"
            elif "ai" in type_str or "assistant" in type_str or cls_name == "AIMessage":
                role = "assistant"
            formatted.append({"role": role, "content": content})

        reply_text = VectorLocalEngine.chat_completion(
            formatted,
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens)
        )
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=reply_text))])

    def predict_messages(self, messages: List[BaseMessage], stop: Optional[List[str]] = None, **kwargs: Any) -> BaseMessage:
        return self.invoke(messages, stop=stop, **kwargs)


