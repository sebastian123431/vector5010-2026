import numpy as np
from django.db import models
from django.contrib.auth import get_user_model
from typing import Optional, List

User = get_user_model()

class MemoryEntry(models.Model):
    """
    Fragmento de memoria a largo plazo (hechos, metas, lecciones).
    Almacena su embedding vectorial Nomic en formato binario para búsquedas matriciales ultrarrápidas (<1ms).
    """
    objects     = models.Manager()
    user        = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    content     = models.TextField()
    created_at  = models.DateTimeField(auto_now_add=True)
    entry_type  = models.CharField(
        max_length=20,
        choices=[
            ('fact',          'Hecho'),
            ('goal',          'Meta'),
            ('lesson',        'Lección'),
            ('learning',      'Aprendizaje'),
            ('pattern',       'Patrón'),
            ('tool_creation', 'Herramienta'),
            ('important',     'Importante'),
            ('visual_identity', 'Identidad Visual'),
        ],
        default='fact'
    )
    # Embedding denso (768 floats en float32 = 3072 bytes)
    vector      = models.BinaryField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def set_vector(self, arr) -> None:
        """Serializa un array de numpy a bytes binarios."""
        if arr is not None:
            a = np.array(arr, dtype=np.float32)
            norm = np.linalg.norm(a)
            if norm > 1e-6:
                a /= norm
            setattr(self, 'vector', a.tobytes())

    def get_vector(self) -> Optional[np.ndarray]:
        """Deserializa el vector binario a un array de numpy float32 normalizado."""
        raw_vec = getattr(self, 'vector', None)
        if raw_vec:
            return np.frombuffer(bytes(raw_vec), dtype=np.float32)
        return None

    def save(self, *args, **kwargs):
        """Auto-calcula y persiste el vector semántico denso si aún no se ha generado."""
        raw_vec = getattr(self, 'vector', None)
        content_str = str(getattr(self, 'content', '') or '')
        if not raw_vec and content_str:
            try:
                from .embeddings import _EMBEDDINGS
                vec = _EMBEDDINGS.embed_query(content_str[:300])
                self.set_vector(vec)
            except Exception:
                pass
        super().save(*args, **kwargs)

    @classmethod
    def recall(cls, query: str, top_k: int = 5) -> List['MemoryEntry']:
        """
        Búsqueda semántica ultrarrápida (<1ms) utilizando multiplicación matricial NumPy
        sobre los vectores Nomic cacheados en SQLite, con fallback de generación perezosa.
        """
        entries = list(cls.objects.all()[:200])
        if not entries:
            return []

        # 1. Coincidencia textual directa
        lower_q = query.lower()
        exact = [e for e in entries if lower_q in e.content.lower()]
        if exact:
            return exact[:top_k]

        # 2. Búsqueda semántica matricial
        try:
            from .embeddings import _EMBEDDINGS
            q_raw = _EMBEDDINGS.embed_query(query)
            q_vec = np.array(q_raw, dtype=np.float32)
            q_norm = np.linalg.norm(q_vec)
            if q_norm > 1e-6:
                q_vec /= q_norm

            matrix_rows = []
            valid_entries = []

            for e in entries:
                v = e.get_vector()
                if v is None or len(v) != 768:
                    # Generación perezosa y guardado del vector faltante
                    try:
                        v_raw = _EMBEDDINGS.embed_query(e.content[:300])
                        e.set_vector(v_raw)
                        e.save(update_fields=['vector'])
                        v = e.get_vector()
                    except Exception:
                        continue
                if v is not None and len(v) == 768:
                    matrix_rows.append(v)
                    valid_entries.append(e)

            if matrix_rows:
                matrix = np.vstack(matrix_rows)  # shape: (N, 768)
                scores = np.dot(matrix, q_vec)   # shape: (N,)
                top_indices = np.argsort(scores)[::-1][:top_k]
                return [valid_entries[i] for i in top_indices if scores[i] > 0.40]

        except Exception:
            pass

        return entries[:top_k]


class Interaction(models.Model):
    """
    Guarda cada pregunta/respuesta para memoria episódica, contexto y estadísticas.
    Cuenta con índices B-Tree en timestamp y compuestos para consultas cronológicas inmediatas.
    """
    objects      = models.Manager()
    user         = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    question     = models.TextField()
    answer       = models.TextField()
    timestamp    = models.DateTimeField(auto_now_add=True, db_index=True)
    session_id   = models.CharField(max_length=64, db_index=True, default='', blank=True)
    user_name    = models.CharField(max_length=100, db_index=True, default='', blank=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['session_id', '-timestamp']),
            models.Index(fields=['user_name', '-timestamp']),
        ]