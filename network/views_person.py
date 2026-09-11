from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView
from .models import Person
from .forms import PersonForm

class PersonCreateView(CreateView):
    model = Person
    template_name = 'network/person_form.html'
    success_url = reverse_lazy('person-list')
    form_class = PersonForm

class PersonListView(ListView):
    model = Person
    template_name = 'network/person_list.html'
    context_object_name = 'people'