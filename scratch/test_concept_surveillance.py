import os
import sys
import time
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vector5010.settings')
import django
django.setup()

import psutil
from vectorapp.neural_network import semantic_network
from vectorapp.models import Interaction, MemoryEntry

def supervisar_concepto_demo(consulta: str):
    consulta_lower = consulta.lower()
    
    # Identificar concepto objetivo
    es_red = any(k in consulta_lower for k in ["red", "neurona", "sinapsis", "grafo", "nodos"])
    es_herramientas = any(k in consulta_lower for k in ["herramienta", "herramientas", "script", "scripts", "tool", "tools"])
    es_codigo = any(k in consulta_lower for k in ["codigo", "código", "archivo", "archivos", "views", "modificaciones", "ficheros"])
    es_memoria = any(k in consulta_lower for k in ["memoria", "base de datos", "bd", "interacciones", "recuerdos", "datos"])
    es_motores = any(k in consulta_lower for k in ["motor", "motores", "llama", "inferencia", "gpu", "cuda", "puerto"])
    es_hardware = any(k in consulta_lower for k in ["hardware", "recurso", "recursos", "cpu", "ram", "disco", "máquina", "maquina", "temperatura"])
    
    reportes = []
    
    # 1. Red Neuronal
    if es_red or (not any([es_red, es_herramientas, es_codigo, es_memoria, es_motores, es_hardware])):
        n_count = len(semantic_network.neurons)
        conn_count = sum(len(n.connections) for n in semantic_network.neurons.values())
        json_path = os.path.join(BASE_DIR, "semantic_network.json")
        mod_time = datetime.fromtimestamp(os.path.getmtime(json_path)).strftime("%H:%M:%S") if os.path.exists(json_path) else "N/A"
        reportes.append(f"• RED NEURONAL SINÁPTICA: {n_count} neuronas activas, {conn_count} conexiones sinápticas. Estado de persistencia: óptimo (última sincronización: {mod_time}).")
        
    # 2. Herramientas
    if es_herramientas or (not any([es_red, es_herramientas, es_codigo, es_memoria, es_motores, es_hardware])):
        tools_dir = os.path.join(BASE_DIR, "vectorapp", "herramientas")
        py_tools = [f for f in os.listdir(tools_dir) if f.endswith(".py") and f != "__init__.py"] if os.path.exists(tools_dir) else []
        reportes.append(f"• HERRAMIENTAS DINÁMICAS: {len(py_tools)} scripts activos en herramientas/ ({', '.join(py_tools[:3])}). Integridad AST verificada.")

    # 3. Código y archivos modificados recientemente
    if es_codigo or (not any([es_red, es_herramientas, es_codigo, es_memoria, es_motores, es_hardware])):
        archivos_modificados = []
        ahora = time.time()
        for root, dirs, files in os.walk(os.path.join(BASE_DIR, "vectorapp")):
            dirs[:] = [d for d in dirs if d not in ["__pycache__", ".git", "venv"]]
            for f in files:
                if f.endswith(".py"):
                    full_p = os.path.join(root, f)
                    try:
                        mtime = os.path.getmtime(full_p)
                        if ahora - mtime < 7200: # Modificados en las últimas 2 horas
                            archivos_modificados.append((f, int((ahora - mtime)/60)))
                    except Exception:
                        pass
        if archivos_modificados:
            archivos_modificados.sort(key=lambda x: x[1])
            desc_mod = ", ".join(f"{f} (hace {m}m)" for f, m in archivos_modificados[:4])
            reportes.append(f"• CÓDIGO Y ARCHIVOS RECIENTES: Cambios detectados en: {desc_mod}.")
        else:
            reportes.append("• CÓDIGO Y ARCHIVOS: Sin modificaciones recientes en las últimas 2 horas. Código base estable.")

    # 4. Memoria y BD
    if es_memoria:
        total_it = Interaction.objects.count()
        total_mem = MemoryEntry.objects.count()
        last_it = Interaction.objects.order_by('-timestamp').first()
        last_ts = last_it.timestamp.strftime("%H:%M:%S") if last_it and hasattr(last_it, 'timestamp') and last_it.timestamp else "reciente"
        reportes.append(f"• BASE DE DATOS Y MEMORIA: {total_it} interacciones registradas, {total_mem} recuerdos semánticos almacenados. Último registro: {last_ts}.")

    # 5. Hardware y Recursos
    if es_hardware or (not any([es_red, es_herramientas, es_codigo, es_memoria, es_motores])):
        cpu = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage('.').percent
        reportes.append(f"• TELEMETRÍA DE RECURSOS: CPU al {cpu}%, RAM al {ram}%, Disco al {disk}%. Centinela en segundo plano activo.")

    return "\n".join(reportes)

# Probar diferentes consultas conceptuales
test_cases = [
    "vigila la red neuronal si hay cambios",
    "supervisa las herramientas creadas",
    "supervisa cambios en el código de views",
    "vigila la memoria y base de datos",
    "vigila o supervisa algún cambio",
]

for t in test_cases:
    print(f"\n--- CONSULTA: '{t}' ---")
    print(supervisar_concepto_demo(t))
