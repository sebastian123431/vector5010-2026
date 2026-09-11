import os
from django.conf import settings
from langchain_core.embeddings import Embeddings
try:
    from langchain_core.documents import Document
except ImportError:
    from langchain_classic.schema import Document

try:
    from langchain_community.vectorstores import FAISS
except ImportError:
    try:
        from langchain_community.vectorstores.faiss import FAISS
    except ImportError:
        FAISS = None
from .local_engine import VectorLocalEngine

# Directorio de datos de la app
data_dir = os.path.join(settings.BASE_DIR, "vectorapp", "data")
# Carpeta donde FAISS guardará su índice
MEMORIA_PATH = os.path.join(data_dir, "memoria_faiss")

class LocalVectorEmbeddings(Embeddings):
    """Embeddings 100% locales ejecutados por el motor de inferencia nativo GGUF sin Ollama."""
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return VectorLocalEngine.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        return VectorLocalEngine.embed_query(text)

# Instancia local de embeddings
_EMBEDDINGS = LocalVectorEmbeddings()


def get_vectorstore(allow_deserialization: bool = False):
    """
    Carga o crea un índice FAISS en MEMORIA_PATH.
    - Si allow_deserialization=True, permite deserializar el pickle existente.
    - Si el directorio está vacío o falla la carga, genera uno nuevo con un documento dummy.
    """
    # Asegura que exista el directorio de memoria
    os.makedirs(MEMORIA_PATH, exist_ok=True)

    if not FAISS or not Document:
        raise RuntimeError("FAISS o Document no están disponibles en el entorno.")

    # Si hay archivos previos, intenta cargar el índice desde disco
    if os.listdir(MEMORIA_PATH):
        try:
            return FAISS.load_local(
                MEMORIA_PATH,
                _EMBEDDINGS,
                allow_dangerous_deserialization=allow_deserialization
            )
        except Exception:
            # Si falla (o allow_deserialization=False), seguiremos a crear uno nuevo
            pass

    # Genera un índice nuevo con un documento dummy (reemplaza después con tus documentos reales)
    dummy = Document(page_content="")
    store = FAISS.from_documents([dummy], _EMBEDDINGS)
    store.save_local(MEMORIA_PATH)
    return store
