"""
Inicialización del entorno de pruebas para VECTOR 2026.
Configura DJANGO_SETTINGS_MODULE para permitir la ejecución tanto con `manage.py test`
como con `python -m unittest discover tests`.
"""

import os
import django

if not os.environ.get("DJANGO_SETTINGS_MODULE"):
    os.environ["DJANGO_SETTINGS_MODULE"] = "vector5010.settings"
    try:
        django.setup()
    except Exception:
        pass
