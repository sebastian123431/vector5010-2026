from django.urls import path
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    path('', views.network_view, name='network-view'),
    path('home/', views.home, name='network-home'),
    path('network/data/', views.semantic_network_data, name='network-data'),
    path('neuronal/data/', views.semantic_network_data, name='semantic-network-data'),
    path('neuronal/init/', views.initialize_semantic_network, name='initialize-semantic-network'),
    path('neuronal/add/', views.add_neuron, name='add-neuron'),
    path('neuronal/edit/<str:neuron_id>/', views.edit_neuron, name='edit-neuron'),
    path('neuronal/delete/<str:neuron_id>/', views.delete_neuron, name='delete-neuron'),
    path('neuronal/add-from-chat/', views.add_neuron_from_chat, name='add-neuron-from-chat'),
    path('neuronal/stats/', views.network_stats, name='network-stats'),
    # Redirecciones de seguridad por URLs antiguas
    path('persons/', RedirectView.as_view(pattern_name='network-view', permanent=False)),
    path('persons/create/', RedirectView.as_view(pattern_name='network-view', permanent=False)),
]