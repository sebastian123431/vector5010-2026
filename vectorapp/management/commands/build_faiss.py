import os
from django.core.management.base import BaseCommand
from vectorapp.embeddings import get_vectorstore

class Command(BaseCommand):
    help = "Construye o reconstituye el índice FAISS en memoria/"

    def handle(self, *args, **options):
        # Forzamos la creación (allow_deserialization=False regenerará)
        _ = get_vectorstore(allow_deserialization=False)
        self.stdout.write(self.style.SUCCESS(
            f"Índice FAISS creado/cargado en '{os.path.join(os.path.dirname(__file__), '..', '..', 'memoria')}'"
        ))