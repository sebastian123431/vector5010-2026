"""
URL configuration for vector5010 project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include  # Agrega include para montar las rutas de redes
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from vectorapp.views import (
    interactuar,
    interactuar_stream,
    neural_network_status,
    neural_network_train,
    neural_network_prune,
    neural_network_metrics,
    neural_network_backup,
    neural_network_reset,
    list_dynamic_tools,
    create_dynamic_tool,
    execute_dynamic_tool,
    delete_dynamic_tool,
    dynamic_tools_history,
    suggest_tool_improvements,
    dynamic_tools_reuse_stats,
    suggest_tool_reuse,
    adapt_existing_tool_endpoint,
    vision_detect,
    sentinel_status,
    cognitive_thoughts,
    analizar_proyecto_zip,
    estado_proyecto_actual,
    cerrar_proyecto_actual,
    optimizer_stats,
    optimizer_clear_cache,
    obtener_historial_consultas,
    listar_sesiones_chat,
    limpiar_sesion_chat,
    weather_locate_endpoint
)

urlpatterns = [
    path('', RedirectView.as_view(url='/redes/', permanent=False), name='root_redirect'),
    path('admin/', admin.site.urls),
    path("api/chat/", interactuar, name="interactuar"),
    path("api/chat/stream/", interactuar_stream, name="interactuar_stream"),
    path("api/chat/historial/", obtener_historial_consultas, name="obtener_historial_consultas"),
    path("api/chat/sesiones/", listar_sesiones_chat, name="listar_sesiones_chat"),
    path("api/chat/nueva_sesion/", limpiar_sesion_chat, name="limpiar_sesion_chat"),
    path("api/weather/locate/", weather_locate_endpoint, name="weather_locate_endpoint"),
    path("api/codigo/analizar_zip/", analizar_proyecto_zip, name="analizar_proyecto_zip"),
    path("api/codigo/estado_proyecto/", estado_proyecto_actual, name="estado_proyecto_actual"),
    path("api/codigo/cerrar_proyecto/", cerrar_proyecto_actual, name="cerrar_proyecto_actual"),
    path("api/optimizer/stats/", optimizer_stats, name="optimizer_stats"),
    path("api/optimizer/clear_cache/", optimizer_clear_cache, name="optimizer_clear_cache"),
    path("api/vision/detect/", vision_detect, name="vision_detect"),
    path("api/sentinel/status/", sentinel_status, name="sentinel_status"),
    path("api/neural/thoughts/", cognitive_thoughts, name="cognitive_thoughts"),

    
    # Endpoints de Red Neuronal
    path("api/neural/status/", neural_network_status, name="neural_network_status"),
    path("api/neural/train/", neural_network_train, name="neural_network_train"),
    path("api/neural/prune/", neural_network_prune, name="neural_network_prune"),
    path("api/neural/metrics/", neural_network_metrics, name="neural_network_metrics"),
    path("api/neural/backup/", neural_network_backup, name="neural_network_backup"),
    path("api/neural/reset/", neural_network_reset, name="neural_network_reset"),
    
    # Endpoints de Herramientas Dinámicas
    path("api/tools/", list_dynamic_tools, name="list_dynamic_tools"),
    path("api/tools/create/", create_dynamic_tool, name="create_dynamic_tool"),
    path("api/tools/execute/", execute_dynamic_tool, name="execute_dynamic_tool"),
    path("api/tools/delete/<str:tool_name>/", delete_dynamic_tool, name="delete_dynamic_tool"),
    path("api/tools/history/", dynamic_tools_history, name="dynamic_tools_history"),
    path("api/tools/suggestions/", suggest_tool_improvements, name="suggest_tool_improvements"),
    path("api/tools/reuse-stats/", dynamic_tools_reuse_stats, name="dynamic_tools_reuse_stats"),
    path("api/tools/suggest-reuse/", suggest_tool_reuse, name="suggest_tool_reuse"),
    path("api/tools/adapt/", adapt_existing_tool_endpoint, name="adapt_existing_tool"),

    path('redes/', include('network.urls')),  # Monta la aplicación de redes semánticas
    path('', include('network.urls')),        # Compatibilidad para llamadas AJAX directas (/network/data/, /ajax/...)
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
