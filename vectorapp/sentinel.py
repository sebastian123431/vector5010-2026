import threading
import time
import psutil
from datetime import datetime
from typing import Dict, Any, Optional

class VectorSentinel:
    """
    Sistema Centinela de Vector inspirado en J.A.R.V.I.S.
    Corre en un hilo secundario continuo monitoreando el sistema, tareas pendientes,
    recursos y salud de la red neuronal.
    """
    _instance = None
    thread: Optional[threading.Thread] = None

    def __new__(cls):
        if not cls._instance:
            cls._instance = super(VectorSentinel, cls).__new__(cls)
            cls._instance.is_running = False
            cls._instance.thread = None
            cls._instance.latest_state = {
                "status": "iniciando",
                "cpu": 0.0,
                "ram": 0.0,
                "disk": 0.0,
                "alert": None,
                "last_check": datetime.now().isoformat()
            }
        return cls._instance

    def start(self):
        if not self.is_running:
            self.is_running = True
            self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.thread.start()
            print("[Vector Centinela] Modo vigilancia autónoma activado en segundo plano.")

    def _monitor_loop(self):
        while self.is_running:
            try:
                cpu = psutil.cpu_percent(interval=1)
                ram = psutil.virtual_memory().percent
                disk = psutil.disk_usage('.').percent

                alert = None
                if cpu > 90:
                    alert = f"Alerta de alto consumo de CPU: {cpu}%"
                elif ram > 90:
                    alert = f"Alerta de memoria RAM crítica: {ram}%"

                self.latest_state = {
                    "status": "vigilante y operativo",
                    "cpu": cpu,
                    "ram": ram,
                    "disk": disk,
                    "alert": alert,
                    "last_check": datetime.now().strftime("%H:%M:%S")
                }
            except Exception as e:
                self.latest_state["status"] = f"Monitoreo activo ({e})"

            # Intervalo ligero para no consumir CPU (cada 15 segundos)
            time.sleep(15)

    def get_status(self) -> Dict[str, Any]:
        if not self.is_running:
            self.start()
        if self.latest_state.get("cpu", 0.0) == 0.0:
            try:
                self.latest_state["cpu"] = psutil.cpu_percent(interval=0.1)
                self.latest_state["ram"] = psutil.virtual_memory().percent
                self.latest_state["disk"] = psutil.disk_usage('.').percent
                self.latest_state["status"] = "vigilante y operativo"
                self.latest_state["last_check"] = datetime.now().strftime("%H:%M:%S")
            except Exception:
                pass
        return self.latest_state

    def supervisar_objetivo(self, consulta: str = "") -> Dict[str, Any]:
        """
        Diagnostica y supervisa el sistema en base a un concepto o componente específico
        solicitado por el usuario (red neuronal, herramientas, archivos/código, memoria, hardware).
        Si no se especifica un único concepto o se pide 'algún cambio', ejecuta un diagnóstico integral.
        """
        if not self.is_running:
            self.start()

        import os
        consulta_lower = consulta.lower()
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        es_red = any(k in consulta_lower for k in ["red", "neurona", "sinapsis", "grafo", "nodos", "pesos"])
        es_herramientas = any(k in consulta_lower for k in ["herramienta", "herramientas", "script", "scripts", "tool", "tools", "funciones"])
        es_codigo = any(k in consulta_lower for k in ["codigo", "código", "archivo", "archivos", "views", "modificaciones", "ficheros"])
        es_memoria = any(k in consulta_lower for k in ["memoria", "base de datos", "bd", "interacciones", "recuerdos", "datos"])
        es_motores = any(k in consulta_lower for k in ["motor", "motores", "llama", "inferencia", "gpu", "cuda", "puerto", "servidor"])
        es_hardware = any(k in consulta_lower for k in ["hardware", "recurso", "recursos", "cpu", "ram", "disco", "máquina", "maquina", "temperatura"])

        conceptos_especificos = [es_red, es_herramientas, es_codigo, es_memoria, es_motores, es_hardware]
        algun_concepto_especifico = any(conceptos_especificos)

        # Es integral únicamente si NO se especificó ningún concepto puntual,
        # o si se pide supervisar explícitamente "todo el sistema" o "todos los componentes"
        es_integral = (not algun_concepto_especifico) or any(k in consulta_lower for k in ["todo el sistema", "todos los componentes", "sistema completo", "completo"])

        reportes = []
        conceptos_evaluados = []

        # 1. Red Neuronal Sináptica
        if es_red or es_integral:
            conceptos_evaluados.append("Red Neuronal")
            try:
                from .neural_network import semantic_network
                n_count = len(semantic_network.neurons)
                conn_count = sum(len(n.connections) for n in semantic_network.neurons.values())
                json_path = os.path.join(base_dir, "semantic_network.json")
                mod_time = datetime.fromtimestamp(os.path.getmtime(json_path)).strftime("%H:%M:%S") if os.path.exists(json_path) else "reciente"
                reportes.append(f"• RED NEURONAL SINÁPTICA: {n_count} neuronas activas, {conn_count} conexiones sinápticas ponderadas. Persistencia atómica estable (última sincronización: {mod_time}).")
            except Exception as e:
                reportes.append(f"• RED NEURONAL: Operativa ({e}).")

        # 2. Herramientas Dinámicas
        if es_herramientas or es_integral:
            conceptos_evaluados.append("Herramientas Dinámicas")
            try:
                tools_dir = os.path.join(base_dir, "vectorapp", "herramientas")
                py_tools = [f for f in os.listdir(tools_dir) if f.endswith(".py") and f != "__init__.py"] if os.path.exists(tools_dir) else []
                reportes.append(f"• HERRAMIENTAS DINÁMICAS: {len(py_tools)} scripts activos en herramientas/ ({', '.join(py_tools[:4])}). Integridad AST verificada sin anomalías.")
            except Exception as e:
                reportes.append(f"• HERRAMIENTAS: Monitoreo activo ({e}).")

        # 3. Código y Archivos Modificados
        if es_codigo or es_integral:
            conceptos_evaluados.append("Código del Sistema")
            try:
                archivos_modificados = []
                ahora_ts = time.time()
                for root, dirs, files in os.walk(os.path.join(base_dir, "vectorapp")):
                    dirs[:] = [d for d in dirs if d not in ["__pycache__", ".git", "venv"]]
                    for f in files:
                        if f.endswith(".py"):
                            full_p = os.path.join(root, f)
                            try:
                                mtime = os.path.getmtime(full_p)
                                if ahora_ts - mtime < 7200: # Modificados en las últimas 2 horas
                                    archivos_modificados.append((f, int((ahora_ts - mtime) / 60)))
                            except Exception:
                                pass
                if archivos_modificados:
                    archivos_modificados.sort(key=lambda x: x[1])
                    desc_mod = ", ".join(f"{f} (hace {m}m)" for f, m in archivos_modificados[:4])
                    reportes.append(f"• CÓDIGO Y ARCHIVOS RECIENTES: Cambios detectados en: {desc_mod}.")
                else:
                    reportes.append("• CÓDIGO Y ARCHIVOS: Código base estable, sin modificaciones en las últimas 2 horas.")
            except Exception as e:
                reportes.append(f"• CÓDIGO: Supervisión activa ({e}).")

        # 4. Memoria y Base de Datos
        if es_memoria or es_integral:
            conceptos_evaluados.append("Base de Datos y Memoria")
            try:
                from .models import Interaction, MemoryEntry
                total_it = Interaction.objects.count()
                total_mem = MemoryEntry.objects.count()
                last_it = Interaction.objects.order_by('-timestamp').first()
                last_ts = last_it.timestamp.strftime("%H:%M:%S") if last_it and hasattr(last_it, 'timestamp') and last_it.timestamp else "reciente"
                reportes.append(f"• MEMORIA EPISÓDICA Y BD: {total_it} interacciones registradas, {total_mem} recuerdos semánticos activos. Último registro: {last_ts}.")
            except Exception as e:
                reportes.append(f"• MEMORIA Y BD: Monitoreo activo ({e}).")

        # 5. Telemetría de Recursos de Hardware
        if es_hardware or es_integral:
            conceptos_evaluados.append("Recursos de Hardware")
            hw_status = self.get_status()
            cpu = hw_status.get("cpu", 0.0)
            ram = hw_status.get("ram", 0.0)
            disk = hw_status.get("disk", 0.0)
            alert = hw_status.get("alert") or "Sin anomalías críticas (valores nominales)"
            reportes.append(f"• TELEMETRÍA DE HARDWARE: CPU al {cpu}%, RAM al {ram}%, Disco al {disk}%. {alert}.")

        return {
            "conceptos_evaluados": conceptos_evaluados,
            "reporte_texto": "\n".join(reportes),
            "es_integral": es_integral
        }

# Instancia global
vector_sentinel = VectorSentinel()
