# filepath: c:\Users\norti\redes\network\context_processors.py
from .models import Person

def people_in_menu(request):
    return {
        'people_in_menu': Person.objects.all()
    }