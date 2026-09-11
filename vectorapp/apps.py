import logging
import os
from django.apps import AppConfig

from django.db.backends.signals import connection_created

logger = logging.getLogger(__name__)

def configure_sqlite_pragmas(sender, connection, **kwargs):
    """Configura SQLite en modo WAL y optimiza rendimiento y concurrencia."""
    if connection.vendor == 'sqlite':
        try:
            with connection.cursor() as cursor:
                cursor.execute("PRAGMA journal_mode = WAL;")
                cursor.execute("PRAGMA busy_timeout = 5000;")
                cursor.execute("PRAGMA synchronous = NORMAL;")
                cursor.execute("PRAGMA cache_size = -64000;")
        except Exception as e:
            logger.warning(f"[VectorApp] Error configurando PRAGMAs de SQLite: {e}")

class VectorAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'  # type: ignore
    name = 'vectorapp'

    def ready(self):
        # Conectar optimizaciones de SQLite en cada conexión
        connection_created.connect(configure_sqlite_pragmas)

        # Evitar doble ejecución en reloader de Django
        if os.environ.get('RUN_MAIN') == 'true' or not os.environ.get('DJANGO_SETTINGS_MODULE'):
            try:
                from .local_engine import VectorLocalEngine
                VectorLocalEngine.ensure_engines()
                logger.info("[VectorApp] Motores locales de inferencia y embeddings verificados.")
            except Exception as e:
                logger.warning(f"[VectorApp] Aviso al iniciar motores locales: {e}")

        # Bootstrap de memoria vectorial (FAISS/NumPy) desde base de datos relacional
        import sys
        if 'test' not in sys.argv:
            try:
                from .memory import memory_manager
                memory_manager.bootstrap()
            except Exception as e_boot:
                logger.debug(f"[VectorApp] Aviso en bootstrap de memoria: {e_boot}")