from django import forms
from .models import Person  # Importa directamente el modelo Person

class PersonForm(forms.ModelForm):
    class Meta:
        model = Person  # Usa el modelo importado directamente
        fields = ['name']