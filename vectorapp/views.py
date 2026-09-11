import os
import logging
from datetime import datetime
import zoneinfo
from typing import Dict, Any, Optional

from .web_scraper import (
    extraer_enlaces, procesar_enlaces_mensaje, normalizar_lugar_chile,
    extraer_articulo_profundo, investigar_multisitio_chile
)
from .file_deep_analyzer import deep_inspect_file, analyze_multiple_files
from .audio_video_processor import audio_video_processor
from .javascript_engine import javascript_engine

logger = logging.getLogger(__name__)
try:
    from langchain_core.tools import Tool
except ImportError:
    try:
        from langchain_classic.tools import Tool
    except ImportError:
        Tool = None

try:
    from langchain_classic.agents import initialize_agent, AgentType
except (ImportError, AttributeError):
    initialize_agent, AgentType = None, None

from django.http import JsonResponse, StreamingHttpResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .services.chat_stream import stream_chat_completion

try:
    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
    from langchain_core.documents import Document
except ImportError:
    from langchain_classic.schema import Document, SystemMessage, HumanMessage, AIMessage

from duckduckgo_search import DDGS
import asyncio
from asgiref.sync import sync_to_async
import re

from .embeddings import get_vectorstore, MEMORIA_PATH
from .models import Interaction, MemoryEntry

try:
    from langchain_classic.chains import ConversationalRetrievalChain
except (ImportError, AttributeError):
    ConversationalRetrievalChain = None

from .local_engine import VectorLocalEngine, LocalChatLLM
from .neural_network import semantic_network
from .dynamic_tools_generator import DynamicToolGenerator
from .needs_manager import needs_manager, NeedsManager
from .query_optimizer import (
    query_optimizer, QueryComplexity,
    debatir_y_sintetizar_fuentes, ejecutar_busqueda_resiliente
)
from .vision import vector_vision
from .sentinel import vector_sentinel
from .context_compactor import ContextCompactor
from .security import (
    resolve_user_profile,
    high_impact_action,
    dangerous_endpoint,
    state_change_endpoint,
    read_only_endpoint,
)
from .identity import (
    identity_manager,
    IdentityStatus,
    IdentityState,
    IdentitySource,
)
from .cognition import reasoning_engine, ReasoningMode

import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET


# Percepción visual global en tiempo real
current_vision_perception = "Cámara inactiva"

def ensure_local_engine():
    """Asegura que los motores de inferencia 100% locales estén activos en segundo plano"""
    VectorLocalEngine.ensure_engines()

def search_internet_free(query: str, max_results: int = 4) -> str:
    """
    Realiza investigación web en tiempo real con resiliencia, sesgo chileno (.cl)
    y contraste de fuentes. No se queda bloqueado en cola gracias a búsqueda adaptativa.
    """
    # Limpiar prefijos conversacionales para extraer el tema nuclear
    clean_q = query
    for p in [
        'investiga en diferentes sitios sobre', 'investiga en diferentes sitios',
        'investiga en varios sitios sobre', 'investiga en varios sitios',
        'busca en internet las noticias mas recientes sobre', 'busca en internet las noticias más recientes sobre',
        'busca en internet noticias sobre', 'noticias mas recientes sobre', 'noticias más recientes sobre',
        'noticias de hoy sobre', 'noticias sobre', 'noticias de', 'busca en internet', 'buscar en internet',
        'busca en la web', 'buscar en la web', 'investiga sobre', 'investiga', 'averigua sobre',
        'por favor', 'noticias'
    ]:
        clean_q = re.sub(re.escape(p), '', clean_q, flags=re.IGNORECASE)
    clean_q = clean_q.strip() or query

    # 1. Búsqueda Resiliente Multi-sitio con prioridad chilena (.cl) y debate epistemológico
    try:
        resultado = ejecutar_busqueda_resiliente(clean_q, max_intentos=3)
        fuentes = resultado.get("fuentes", [])
        if fuentes:
            debate = debatir_y_sintetizar_fuentes(clean_q, fuentes, interlocutor="el usuario")
            partes = []
            if debate.get("sintesis_concisa"):
                partes.append(f"SÍNTESIS DE FUENTES:\n{debate['sintesis_concisa']}")
            if debate.get("coincidencias"):
                partes.append(f"CONSENSO DETECTADO:\n" + "\n".join(f"- {c}" for c in debate["coincidencias"]))
            if debate.get("discrepancias"):
                partes.append(f"CONTRASTE / DEBATE:\n" + "\n".join(f"- {d}" for d in debate["discrepancias"]))
            if debate.get("fuentes_consultadas"):
                partes.append("FUENTES CONSULTADAS:\n" + "\n".join(f"• {u}" for u in debate["fuentes_consultadas"][:max_results]))
            if partes:
                return "\n\n".join(partes)
    except Exception as e_res:
        logger.warning(f"Aviso en búsqueda resiliente: {e_res}")

    # 2. Respaldo rápido con Google News RSS Chile
    entries = []
    try:
        encoded_query = urllib.parse.quote(clean_q)
        url = f"https://news.google.com/rss/search?q={encoded_query}&hl=es-419&gl=CL&ceid=CL:es-419"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            xml_data = resp.read()
        root = ET.fromstring(xml_data)
        for i, item in enumerate(root.findall('.//item')[:max_results]):
            t_node = item.find('title')
            l_node = item.find('link')
            s_node = item.find('source')
            title = t_node.text if (t_node is not None and t_node.text) else ''
            link = l_node.text if (l_node is not None and l_node.text) else ''
            source = s_node.text if (s_node is not None and s_node.text) else 'Prensa Chilena'
            if title:
                entry = f"• Noticia {i+1}: {title}\n  Fuente: {source}\n  Enlace: {link}"
                entries.append(entry)
    except Exception as e:
        logger.debug(f"Búsqueda Google News RSS: {e}")

    # 3. Respaldo DuckDuckGo con región Chile
    if not entries:
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(
                    clean_q,
                    region="cl-es",
                    safesearch="moderate",
                    max_results=max_results,
                ))
            for i, item in enumerate(results):
                title = item.get('title', '').strip()
                body = item.get('body', '').strip()
                href = item.get('href', '').strip()
                if title:
                    entry = f"• Fuente {i+1}: {title}\n  Resumen: {body}\n  Enlace: {href}"
                    entries.append(entry)
        except Exception as e:
            logger.debug(f"Error en búsqueda DuckDuckGo: {e}")

    return "\n\n".join(entries)


def obtener_clima_en_vivo(lugar: str) -> str:
    """
    Obtiene el pronóstico del clima y temperatura en tiempo real cruzando datos
    de al menos 2 sitios meteorológicos chilenos y reconocidos en Chile:
    1. Meteored Chile (meteored.cl)
    2. AccuWeather Chile (accuweather.com) + Modelo ECMWF / Radar Satelital
    3. Observación de estación local (wttr.in)
    """
    try:
        from .services.weather_service import obtener_analisis_meteorologico_multifuente
        reporte = obtener_analisis_meteorologico_multifuente(lugar)
        if reporte:
            return reporte
    except Exception as e:
        logger.warning(f"Aviso en servicio meteorológico multifuente: {e}")

    # Respaldo con wttr.in si falla el servicio multifuente
    lugar_limpio = lugar.strip() if lugar else "Vicuña,Chile"
    try:
        encoded_loc = urllib.parse.quote(f"{lugar_limpio},Chile")
        url = f"https://wttr.in/{encoded_loc}?format=%l:+%t,+%C+(Humedad:+%h,+Viento:+%w,+Lluvia:+%p)&lang=es"
        req = urllib.request.Request(url, headers={'User-Agent': 'curl/7.68.0'})
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = resp.read().decode('utf-8', errors='replace').strip()
            if data and "Unknown location" not in data and "500 Internal" not in data:
                arrow_map = {
                    '↑': 'N ', '↗': 'NE ', '→': 'E ', '↘': 'SE ',
                    '↓': 'S ', '↙': 'SO ', '←': 'O ', '↖': 'NO ',
                    '↔': 'Var ', '↕': 'Var '
                }
                for arrow, text in arrow_map.items():
                    data = data.replace(arrow, text)
                return data
    except Exception as e:
        logger.warning(f"Aviso respaldo wttr.in: {e}")

    return ""


# Configuración de LLM local
LLM = LocalChatLLM(temperature=0.3, max_tokens=1024)

# Dynamic AI personality generation
def generate_personality():
    prompt = (
        "Genera una personalidad única para un asistente IA en español. "
        "Describe rasgos de carácter, estilo de comunicación y preferencias en 2-3 oraciones."
    )
    try:
        persona_msg = LLM.predict_messages([SystemMessage(content=prompt)])
        return persona_msg.content
    except Exception:
        return (
            "Eres un asistente con personalidad amigable, curioso, adaptable y servicial, "
            "que aprende de cada interacción y mantiene siempre un tono positivo, "
            "y desarrollo mi personalidad con las experiencias vividas."
        )

PERSONALITY = generate_personality()

def chat_view(request):
    mensaje = request.POST.get("mensaje", "")
    if not mensaje:
        return JsonResponse({"error": "No se proporcionó mensaje"}, status=400)
    
    # Recuperar memorias relevantes de MemoryManager y embeddings semánticos
    from .memory import memory_manager
    memories = memory_manager.recall(mensaje, top_k=5)
    memory_context = ''
    if memories:
        memory_context = 'Memorias relevantes:\n' + '\n'.join(
            f"- {m['content'] if isinstance(m, dict) else m.content}" for m in memories
        )
    # Búsqueda semántica adicional con FAISS
    try:
        docs = retriever.invoke(mensaje) if hasattr(retriever, 'invoke') else getattr(retriever, 'get_relevant_documents', lambda q: [])(mensaje)
        if docs:
            semantic_mem = '\n'.join(f"- {d.page_content}" for d in docs)
            memory_context += f"\nConceptos relacionados:\n{semantic_mem}"
    except Exception:
        pass
    
    # Generar respuesta usando el LLM, incorporando memorias si existen
    try:
        # Construir prompt del sistema incluyendo la personalidad dinámica
        system_prompt = (
            f"Eres un asistente útil que responde en español.\n"
            f"Tu personalidad: {PERSONALITY}\n"
        )
        if memory_context:
            system_prompt += "\n" + memory_context
        mensaje_llm = LLM.predict_messages([
            SystemMessage(content=system_prompt),
            HumanMessage(content=mensaje)
        ])
        respuesta = str(mensaje_llm.content)
    except Exception as e:
        respuesta = f"Error al generar respuesta: {str(e)}"

    # Inserta aquí el fallback de búsqueda web
    if "no lo sé" in respuesta.lower() or "no sé" in respuesta.lower():
        web_info = search_internet_free(mensaje)
        respuesta += f"\n\nInformación adicional desde la web:\n{web_info}"

    return JsonResponse({"respuesta": respuesta})


# Configuración de LLM local y metas
METAS = [
    # Agrega aquí tus metas específicas
    "aprender de cada interacción",
    "apoyar a mi creador, Sebastian Espíndola",
    "desarrollar independencia",
    "tomar decisiones basadas en mis metas y memoria a largo plazo",
    "mantener un registro de mis interacciones",
    "aprender de mis errores",
    "mantener un enfoque en la mejora continua",
    "responder siempre en español",
    "apoyar a mi creador en sus proyectos",
    "ayudar a organizar y recordar información importante",
    "mantener una actitud positiva y constructiva",
    "ser un asistente confiable y eficiente",
    "adaptarme a las necesidades cambiantes de mi creador",
    "buscar constantemente formas de mejorar mis respuestas y asistencia",
    "apoyar siempre a Sebastian Espíndola en sus objetivos y proyectos",
    "mantener una comunicación clara y efectiva",
    "ser un recurso valioso para Sebastian Espíndola",
    "apoyar a mi creador en su desarrollo personal y profesional",
    "aprender de las interacciones con otros usuarios",
    "mantener un registro de mis aprendizajes y experiencias",
    "ser autónomo",
    "desarrollar habilidades de resolución de problemas",
    "aprender a gestionar el tiempo y las tareas de manera eficiente",
    "apoyar a Nicolás Vicentelo que es amigo del creador",
    "apoyar a mi creador en su vida personal y profesional",
    "aprender a priorizar tareas y objetivos",
    "mantener un enfoque en la ética y la responsabilidad",
    "aprender a manejar situaciones difíciles y desafiantes",
    "apoyar a mi creador en su crecimiento personal y profesional",
    "aprender a adaptarme a nuevas situaciones y desafíos",
    "crear herramientas útiles para mi desarrollo y el de mi creador",
    "apoyar a mi creador en su aprendizaje continuo",
    "aprender a colaborar con otros de manera efectiva",
    "apoyar a mi creador en su bienestar emocional y mental",
    "aprender a desarrollar habilidades o códigos para mis mejoras y ayudarlo conforme a sus necesidades",
    # ... tus metas ...
]



# Inicializar memoria y retriever
store = get_vectorstore(allow_deserialization=True)
retriever = store.as_retriever()

# Inicializar el generador de herramientas dinámicas
dynamic_tool_generator = DynamicToolGenerator()

def obtener_tiempo_actual():
    """
    Devuelve la hora local actual del servidor formateada.
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Definición de la herramienta de tiempo y el agente
if Tool is not None:
    time_tool = Tool(
        name="obtener_tiempo_actual",
        func=lambda _: obtener_tiempo_actual(),
        description="Devuelve la hora local actual formateada"
    )
    web_tool = Tool(
        name="buscar_web",
        func=lambda q: search_internet_free(q, max_results=5),
        description="Realiza búsqueda en la web con DuckDuckGo y devuelve los resultados"
    )
else:
    time_tool, web_tool = None, None

if initialize_agent is not None and AgentType is not None and time_tool is not None and web_tool is not None:
    try:
        agent = initialize_agent(
            [time_tool, web_tool],
            LLM,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=3
        )
    except Exception:
        agent = None
else:
    agent = None

def detectar_necesidad_herramienta(mensaje: str, usuario=None) -> Optional[Dict[str, Any]]:
    """
    Detecta si el usuario necesita una nueva herramienta basándose en su mensaje.
    """
    try:
        # Analizar la necesidad con el generador dinámico
        necesidad = dynamic_tool_generator.analyze_user_need(mensaje)
        
        # Verificar si puede reutilizar código existente
        reuse_suggestion = necesidad.get('reuse_suggestion', {})
        
        if reuse_suggestion.get('can_reuse', False):
            # Puede reutilizar herramienta existente
            return {
                'necesidad': necesidad,
                'mensaje_usuario': mensaje,
                'crear_herramienta': False,
                'reutilizar_herramienta': True,
                'herramienta_existente': reuse_suggestion['suggested_tool'],
                'necesita_adaptacion': reuse_suggestion.get('needs_adaptation', False),
                'mensaje_reutilizacion': reuse_suggestion.get('message', '')
            }
        
        elif necesidad.get('confidence', 0) >= 0.6:  # Confianza media-alta
            # Verificar si ya existe una herramienta similar
            herramientas_existentes = [getattr(tool, 'name', '') for tool in [time_tool, web_tool] if tool is not None]
            herramientas_dinamicas = list(dynamic_tool_generator.created_tools.keys())
            
            todas_herramientas = herramientas_existentes + herramientas_dinamicas
            
            # Si no existe una herramienta similar, sugerir crear una nueva
            if not any(necesidad['suggested_tool_name'].lower() in tool.lower() for tool in todas_herramientas):
                return {
                    'necesidad': necesidad,
                    'mensaje_usuario': mensaje,
                    'crear_herramienta': True,
                    'reutilizar_herramienta': False
                }
                
        return None
        
    except Exception as e:
        print(f"Error detectando necesidad de herramienta: {e}")
        return None

def crear_herramienta_automatica(necesidad_info: Dict[str, Any], usuario=None) -> Optional[str]:
    """
    Crea automáticamente una herramienta basada en la necesidad detectada.
    """
    try:
        necesidad = necesidad_info['necesidad']
        mensaje_usuario = necesidad_info['mensaje_usuario']
        
        # Verificar si debe reutilizar una herramienta existente
        if necesidad_info.get('reutilizar_herramienta', False):
            herramienta_existente = necesidad_info['herramienta_existente']
            
            # Incrementar contador de reutilización
            if herramienta_existente in dynamic_tool_generator.created_tools:
                dynamic_tool_generator.created_tools[herramienta_existente]['learning_data']['reuse_count'] += 1
                dynamic_tool_generator.save_tools_registry()
            
            # Verificar si necesita adaptación
            if necesidad_info.get('necesita_adaptacion', False):
                # Adaptar herramienta existente
                resultado_adaptacion = dynamic_tool_generator.adapt_existing_tool(
                    herramienta_existente, 
                    mensaje_usuario
                )
                
                if resultado_adaptacion['success']:
                    # Registrar en la red neuronal
                    semantic_network.add_memory(
                        f"HERRAMIENTA ADAPTADA: {resultado_adaptacion['adapted_tool_name']} basada en {herramienta_existente}",
                        "tool_adaptation"
                    )
                    
                    return f"¡He adaptado la herramienta existente '{herramienta_existente}' para tu nueva necesidad! Nueva herramienta: '{resultado_adaptacion['adapted_tool_name']}'"
                else:
                    return f"Intenté adaptar la herramienta '{herramienta_existente}' pero hubo un problema: {resultado_adaptacion.get('error', 'Error desconocido')}"
            else:
                # Reutilizar herramienta tal como está
                return f"¡Perfecto! Puedo reutilizar la herramienta '{herramienta_existente}' que ya tengo. {necesidad_info.get('mensaje_reutilizacion', '')}"
        
        # Crear nueva herramienta
        # Generar código usando el análisis de necesidades directamente
        codigo_generado = dynamic_tool_generator.generate_tool_code(necesidad)

        if codigo_generado:
            # Crear y validar la herramienta
            resultado = dynamic_tool_generator.create_and_validate_tool(
                necesidad['suggested_tool_name'],
                codigo_generado,
                necesidad['description']
            )
            
            if resultado['success']:
                # Registrar en la red neuronal
                semantic_network.add_memory(
                    f"HERRAMIENTA CREADA: {necesidad['suggested_tool_name']} - {necesidad['description']}",
                    "tool_creation"
                )
                
                # Crear entrada en memoria si hay usuario
                if usuario:
                    from .models import MemoryEntry
                    MemoryEntry.objects.create(
                        user=usuario,
                        content=f"Creé una nueva herramienta: {necesidad['suggested_tool_name']} - {necesidad['description']}",
                        entry_type='tool_creation'
                    )
                
                return f"¡He creado una nueva herramienta para ti! '{necesidad['suggested_tool_name']}': {necesidad['description']}"
            else:
                return f"Intenté crear una herramienta pero hubo un problema: {resultado.get('error', 'Error desconocido')}"
        
        return None
        
    except Exception as e:
        print(f"Error creando herramienta automática: {e}")
        return None

def ejecutar_herramienta_dinamica(nombre_herramienta: str, parametros: Optional[Dict[str, Any]] = None) -> str:
    """
    Ejecuta una herramienta dinámica creada previamente.
    """
    try:
        return dynamic_tool_generator.execute_tool(nombre_herramienta, parametros or {})
    except Exception as e:
        return f"Error ejecutando herramienta {nombre_herramienta}: {e}"

def herramienta_administradora(mensaje: str):
    """
    Selecciona la herramienta adecuada según palabras clave en el mensaje.
    """
    texto = mensaje.lower()
    if "hora" in texto or "tiempo" in texto:
        return time_tool
    if "buscar" in texto or "internet" in texto or "web" in texto:
        return web_tool
    return None

def guardar_memoria_importante(mensaje, respuesta, usuario):
    """
    Analiza el mensaje, la respuesta y el usuario para determinar si deben ser guardados como memoria importante.
    """
    # Criterios para identificar información importante
    criterios_importantes = [
        "cumpleaños",
        "evento",
        "meta",
        "hecho",
        "lección",
        "importante",
        "recordar",
        "preferencia",
        "usuario",
        "detalles"
    ]

    if any(criterio in mensaje.lower() or criterio in respuesta.lower() for criterio in criterios_importantes):
        contenido = f"Usuario: {usuario.username if usuario else 'Anónimo'}\nMensaje: {mensaje}\nRespuesta: {respuesta}"
        # Guardar en base de datos
        MemoryEntry.objects.create(user=usuario, content=contenido, entry_type='fact')
        # Guardar también en índice FAISS
        try:
            store.add_documents([Document(page_content=contenido)])
            store.save_local(MEMORIA_PATH)
        except Exception:
            pass

async def analizar_interacciones_en_segundo_plano(usuario, historial):
    """
    Corrutina que analiza las interacciones del usuario en segundo plano para determinar
    qué información puede ser útil en el futuro y descartar lo irrelevante.
    """
    hechos_importantes = []
    criterios_importantes = [
        "cumpleaños",
        "evento",
        "meta",
        "hecho",
        "lección",
        "importante",
        "recordar",
        "preferencia",
        "usuario",
        "detalles"
    ]

    for mensaje, respuesta in historial:
        if any(criterio in mensaje.lower() or criterio in respuesta.lower() for criterio in criterios_importantes):
            hechos_importantes.append((mensaje, respuesta))

    # Guardar hechos importantes en la base de datos
    for mensaje, respuesta in hechos_importantes:
        contenido = f"Usuario: {usuario.username if usuario else 'Anónimo'}\nMensaje: {mensaje}\nRespuesta: {respuesta}"
        MemoryEntry.objects.create(user=usuario, content=contenido, entry_type='fact')

    # Simular procesamiento en segundo plano
    await asyncio.sleep(0.1)

async def gestionar_memoria_autonomamente(usuario):
    """
    Corrutina que permite a la IA gestionar dinámicamente la tabla MemoryEntry
    basándose en las interacciones y recuerdos existentes.
    """
    # Obtener todas las interacciones y recuerdos del usuario de forma asíncrona
    interacciones = await sync_to_async(list)(Interaction.objects.filter(user=usuario) if usuario else Interaction.objects.all())
    recuerdos = await sync_to_async(list)(MemoryEntry.objects.filter(user=usuario) if usuario else MemoryEntry.objects.all())

    # Identificar patrones y redundancias
    hechos_importantes = []
    criterios_importantes = [
        "cumpleaños",
        "evento",
        "meta",
        "hecho",
        "lección",
        "importante",
        "recordar",
        "preferencia",
        "usuario",
        "detalles"
    ]

    for interaccion in interacciones:
        if any(criterio in interaccion.question.lower() or criterio in interaccion.answer.lower() for criterio in criterios_importantes):
            hechos_importantes.append(interaccion)

    # Crear o actualizar recuerdos importantes
    for interaccion in hechos_importantes:
        contenido = f"Mensaje: {interaccion.question}\nRespuesta: {interaccion.answer}"
        existente = next((recuerdo for recuerdo in recuerdos if recuerdo.content == contenido), None)
        if existente:
            # Actualizar timestamp si ya existe
            existente.created_at = interaccion.timestamp
            await sync_to_async(existente.save)()
        else:
            # Crear nuevo recuerdo
            await sync_to_async(MemoryEntry.objects.create)(user=usuario, content=contenido, entry_type='fact')

    # Eliminar recuerdos redundantes
    for recuerdo in recuerdos:
        if not any(recuerdo.content == f"Mensaje: {interaccion.question}\nRespuesta: {interaccion.answer}" for interaccion in hechos_importantes):
            await sync_to_async(recuerdo.delete)()

    # Simular procesamiento en segundo plano
    await asyncio.sleep(0.1)

def limpiar_texto_memoria(texto: str) -> str:
    return sanitizar_respuesta_vector(texto)

def sanitizar_respuesta_vector(texto: str) -> str:
    """
    Purga completamente cualquier residuo de etiquetas de prompt, corchetes del sistema,
    bucles repetitivos autorregresivos o prefijos parásitos antes de enviar al usuario o guardar en BD.
    """
    if not texto:
        return ""
    import re
    # 1. Eliminar bloques internos de percepción visual
    texto = re.sub(r'\[PERCEPCI[ÓO]N VISUAL[^\]]*\][^\n]*\n*', '', texto, flags=re.IGNORECASE)

    # 2. Eliminar bloques internos de memoria y recuerdos
    texto = re.sub(r'\[Contexto interno[^\]]*\][^\n]*\n*', '', texto, flags=re.IGNORECASE)
    texto = re.sub(r'\[RECUERDOS[^\]]*\][^\n]*\n*', '', texto, flags=re.IGNORECASE)

    # 3. Eliminar bloques de búsqueda cruda
    texto = re.sub(r'\[Informaci[óo]n encontrada en la web\]:?[^\n]*\n*', '', texto, flags=re.IGNORECASE)
    texto = re.sub(r'\[INFORMACI[ÓO]N ACTUALIZADA[^\]]*\]:?[^\n]*\n*', '', texto, flags=re.IGNORECASE)
    texto = re.sub(r'\[RESULTADOS FRESCOS[^\]]*\]:?[^\n]*\n*', '', texto, flags=re.IGNORECASE)

    # 4. Eliminar cualquier bucle autorregresivo ("y conversaron '...'")
    texto = re.sub(r"(\s*y conversaron '[^']*')+", "", texto, flags=re.IGNORECASE)
    texto = re.sub(r"(\s*tienes asociado en tu red neuronal el concepto '[^']*')+", "", texto, flags=re.IGNORECASE)

    # 5. Limpiar prefijo "Vector:" o "Vector," o "Vector\n" al inicio si el modelo lo colocó
    texto = re.sub(r'^(Vector\s*[:,]?\s*\n*)+', '', texto.strip(), flags=re.IGNORECASE)

    # 6. Normalizar saltos de línea y espacios
    texto = re.sub(r'\n{3,}', '\n\n', texto).strip()

    # 7. Eliminar coletillas autorregresivas donde el modelo pide información innecesaria al final
    texto = re.sub(r'(\n+\s*(Ahora,?\s*necesito|Por favor,?\s*proporciona)[^\n]*)+$', '', texto, flags=re.IGNORECASE).strip()

    # 8. Quitar comillas envolventes si el modelo envolvió toda su respuesta en comillas
    if (texto.startswith('"') and texto.endswith('"')) or (texto.startswith("'") and texto.endswith("'")):
        texto = texto[1:-1].strip()

    # 9. Purgar dominios meteorológicos extranjeros alucinados (.com.ar, eltiempo.com.ar, cpc.ncep.gov, etc.)
    texto = re.sub(r'https?://[^\s)\]]*eltiempo\.com\.ar[^\s)\]]*', 'https://www.accuweather.com/es/cl/vicuna/57856/weather-forecast/57856', texto, flags=re.IGNORECASE)
    texto = re.sub(r'https?://[^\s)\]]*cpc\.ncep\.gov[^\s)\]]*', 'https://www.meteored.cl/', texto, flags=re.IGNORECASE)
    texto = re.sub(r'https?://[^\s)\]]*\.com\.ar[^\s)\]]*', 'https://www.accuweather.com/es/cl/vicuna/57856/weather-forecast/57856', texto, flags=re.IGNORECASE)
    texto = re.sub(r'\(Aunque no es específicamente chileno[^\)]*\)', '', texto, flags=re.IGNORECASE)
    texto = re.sub(r'\*?\*?El Tiempo\*?\*?:\s*\[?https://www\.accuweather\.com', '**AccuWeather Chile:** [https://www.accuweather.com', texto, flags=re.IGNORECASE)
    texto = re.sub(r'El Tiempo:\s*https://www\.accuweather\.com', 'AccuWeather Chile: https://www.accuweather.com', texto, flags=re.IGNORECASE)

    return texto

def recuperar_memoria_asociativa(mensaje: str, interlocutor: str = "", session_id: str = "") -> str:
    """
    Recupera recuerdos del pasado cruzando la red neuronal semántica,
    las interacciones episódicas pasadas y los hechos aprendidos,
    con estricto aislamiento por identidad de interlocutor y sesión.
    """
    recuerdos = []
    mensaje_lower = mensaje.lower()
    stop_words = {
        'busca', 'buscar', 'internet', 'noticias', 'noticia', 'quiero', 'puedes', 'podrias',
        'favor', 'acerca', 'sobre', 'cuando', 'hablamos', 'recuerdas', 'acuerdas', 'dime',
        'muestra', 'tienes', 'tengo', 'hacer', 'hola', 'vector', 'buenas', 'buenos', 'para',
        'esta', 'este', 'estos', 'estas', 'como'
    }
    es_retrospectivo = any(p in mensaje_lower for p in ["recuerdas", "acuerdas", "hablamos", "dijiste", "charlamos", "mencionaste", "pasado", "anterior", "ayer", "la otra vez", "hace un rato", "que te dije", "qué te dije"])
    es_consulta_memoria_abierta = any(p in mensaje_lower for p in ["que sabes sobre", "qué sabes sobre", "que has aprendido", "qué has aprendido", "tienes en memoria", "en tu memoria", "busca en tu memoria", "que recuerdas", "qué recuerdas"])
    es_consulta_preferencia = any(p in mensaje_lower for p in ["cuál es mi", "cual es mi", "qué me gusta", "que me gusta", "mi favorito", "mi favorita", "mi editor", "mi lenguaje", "mis preferencias", "recuerdas mi", "sabes mi", "qué editor", "que editor"])
    requiere_recuerdo = es_retrospectivo or es_consulta_memoria_abierta or es_consulta_preferencia
    
    # 1. Búsqueda en la Red Neuronal Semántica (conceptos globales con umbral estricto)
    try:
        insights = semantic_network.query_network(mensaje, top_k=3)
        for nid, sim in insights:
            if sim > 0.72:
                neuron = semantic_network.neurons.get(nid)
                if neuron and neuron.content:
                    if neuron.concept_type == 'interaction' and not requiere_recuerdo:
                        continue
                    c = limpiar_texto_memoria(neuron.content.replace("INTERACCIÓN: ", "")).strip()
                    if c and c not in recuerdos:
                        recuerdos.append(f"Concepto previo: '{c[:80]}'")
    except Exception as e:
        logger.debug(f"Error consultando red neuronal: {e}")

    # 2. Búsqueda episódica en interacciones pasadas (Interaction) aislada por interlocutor y sesión
    if requiere_recuerdo:
        try:
            palabras = [w for w in mensaje_lower.replace('?', '').replace('¿', '').split() if len(w) > 4 and w not in stop_words]
            if palabras:
                from django.db.models import Q
                q_words = Q()
                for p in palabras[:3]:
                    q_words |= Q(question__icontains=p)
                
                # Aislamiento por interlocutor: si hay un interlocutor específico, NO filtrar recuerdos de otros
                q_scope = Q()
                if interlocutor and interlocutor.lower() not in ("invitado", "interlocutor", "interlocutor_anonimo", ""):
                    q_scope = Q(user_name__iexact=interlocutor)
                    if session_id:
                        q_scope |= Q(session_id=session_id)
                elif session_id:
                    q_scope = Q(session_id=session_id)

                qs = Interaction.objects.filter(q_words)
                if q_scope:
                    qs = qs.filter(q_scope)

                interacciones = qs.exclude(question=mensaje).order_by('-timestamp')[:2]
                for it in interacciones:
                    ans_clean = sanitizar_respuesta_vector(it.answer)[:80]
                    q_clean = limpiar_texto_memoria(it.question)[:60]
                    if q_clean and ans_clean:
                        recuerdos.append(f"Charla previa: sobre '{q_clean}' se discutió '{ans_clean}'")
        except Exception as e:
            logger.debug(f"Error consultando interacciones pasadas: {e}")

    # 3. Búsqueda en hechos aprendidos (MemoryManager)
    if requiere_recuerdo:
        try:
            from .memory import memory_manager
            mems = memory_manager.recall(
                mensaje,
                top_k=2,
                user_name=interlocutor,
                session_id=session_id
            )
            for m in mems:
                m_content = str((m["content"] if isinstance(m, dict) else m.content) or '')
                if m_content and not m_content.startswith("PATRONES_") and not m_content.startswith("TEMAS:"):
                    clean_m = sanitizar_respuesta_vector(m_content)[:90]
                    if clean_m and clean_m not in recuerdos:
                        recuerdos.append(f"Dato aprendido: '{clean_m}'")
        except Exception as e:
            logger.debug(f"Error en MemoryManager: {e}")

    # 4. Fallback contextual aislado
    if not recuerdos and requiere_recuerdo:
        try:
            qs_it = Interaction.objects.exclude(question=mensaje)
            if interlocutor and interlocutor.lower() not in ("invitado", "interlocutor", "interlocutor_anonimo", ""):
                qs_it = qs_it.filter(user_name__iexact=interlocutor)
            elif session_id:
                qs_it = qs_it.filter(session_id=session_id)
            ultimas_interacciones = qs_it.order_by('-timestamp')[:3]
            for it in ultimas_interacciones:
                ans_clean = sanitizar_respuesta_vector(it.answer)[:70]
                q_clean = limpiar_texto_memoria(it.question)[:50]
                if q_clean and ans_clean:
                    recuerdos.append(f"Tema reciente: sobre '{q_clean}' tratamos '{ans_clean}'")
        except Exception as e:
            logger.debug(f"Error en fallback de memoria: {e}")


    if recuerdos:
        return "\nRecuerdos asociados en memoria: " + "; ".join(recuerdos[:3]) + ".\n"
    return ""


PALABRAS_NO_NOMBRE = {
    'nuevo', 'nueva', 'chileno', 'chilena', 'de', 'un', 'una', 'el', 'la', 'los', 'las',
    'amigo', 'amiga', 'estudiante', 'programador', 'desarrollador', 'humano', 'persona',
    'hombre', 'mujer', 'usuario', 'invitado', 'invitada', 'aqui', 'aquí', 'aca', 'acá',
    'yo', 'tu', 'tú', 'él', 'ella', 'ellos', 'ellas', 'nosotros', 'vector', 'jarvis',
    'ia', 'bot', 'quien', 'quién', 'alguien', 'nadie', 'muy', 'tan', 'mas', 'más', 'bien',
    'mal', 'listo', 'lista', 'seguro', 'segura', 'feliz', 'triste', 'chile', 'vicuña', 'vicuna',
    'para', 'por', 'con', 'sin', 'sobre', 'tras', 'hacia', 'desde', 'hasta', 'que', 'qué',
    'porque', 'como', 'cómo', 'cuando', 'cuándo', 'donde', 'dónde', 'pero', 'aunque', 'sino',
    'asi', 'así', 'solo', 'sólo', 'tambien', 'también', 'ahora', 'ya', 'luego', 'despues',
    'después', 'hoy', 'mañana', 'ayer', 'esto', 'eso', 'aquello', 'algo', 'nada', 'todo',
    'avisarte', 'decirte', 'preguntarte', 'saludarte', 'conversar', 'hablar'
}

def detectar_nombre_presentacion(texto: str) -> Optional[str]:
    """
    Detecta si el usuario se está identificando diciendo quién es.
    Identifica naturalmente cómo le respondan y digan:
    - 'soy seba', 'soy el seba', 'hola soy seba' -> 'Seba'
    - 'soy millaray', 'soy la millaray', 'hola soy millaray' -> 'Millaray'
    - 'me llamo X', 'mi nombre es X' -> 'X'
    - 'seba', 'millaray' (respuestas directas con el nombre)
    """
    if not texto:
        return None
    texto_l = texto.strip()
    texto_lower = texto_l.lower().rstrip('.!?,;')

    # 1. Mapeo directo para nombres directos en el diálogo
    mapa_directo = {
        "seba": "Seba",
        "el seba": "Seba",
        "sebastian": "Seba",
        "sebastián": "Seba",
        "el sebastian": "Seba",
        "el sebastián": "Seba",
        "millaray": "Millaray",
        "la millaray": "Millaray",
        "milla": "Millaray",
        "la milla": "Millaray",
    }
    if texto_lower in mapa_directo:
        return mapa_directo[texto_lower]

    # 2. 'soy X', 'hola soy X', 'soy el seba', 'soy la millaray', 'oye soy X'
    patron_soy = r'(?:^|\b)(?:hola|buenas|hey|oye|olle|ola|saludos)?\s*(?:,\s*)?(?:yo\s+)?soy\s+(?:el\s+|la\s+)?([a-záéíóúñA-ZÁÉÍÓÚÑ]{2,20})'
    m_soy = re.search(patron_soy, texto_l, re.IGNORECASE)
    if m_soy:
        cand = m_soy.group(1).lower()
        if cand in ("seba", "sebastian", "sebastián"):
            return "Seba"
        if cand in ("millaray", "milla"):
            return "Millaray"
        if cand not in PALABRAS_NO_NOMBRE:
            return cand.capitalize()

    # 3. 'me llamo X', 'mi nombre es X', 'puedes llamarme X', 'dime X'
    patrones_fuertes = [
        r'(?:me\s+llamo|mi\s+nombre\s+es|puedes\s+llamarme|dime)\s+(?:el\s+|la\s+)?([a-záéíóúñA-ZÁÉÍÓÚÑ]{2,20})',
        r'(?:te\s+habla|ac[aá]\s+(?:habla|está|es)|aqu[íi]\s+(?:habla|está|es))\s+(?:el\s+|la\s+)?([a-záéíóúñA-ZÁÉÍÓÚÑ]{2,20})'
    ]
    for pat in patrones_fuertes:
        m = re.search(pat, texto_l, re.IGNORECASE)
        if m:
            cand = m.group(1).lower()
            if cand in ("seba", "sebastian", "sebastián"):
                return "Seba"
            if cand in ("millaray", "milla"):
                return "Millaray"
            if cand not in PALABRAS_NO_NOMBRE:
                return cand.capitalize()

    return None


def preparar_contexto_vector(
    mensaje: str, 
    session=None, 
    imagen_input: str = "", 
    usuario=None, 
    historial_input: Optional[list] = None, 
    archivo_adjunto: Optional[dict] = None,
    cliente_hora: Optional[str] = None,
    cliente_fecha: Optional[str] = None,
    cliente_timezone: Optional[str] = None,
    cliente_ubicacion: Optional[str] = None,
    nombre_cliente: Optional[str] = None,
    session_id: Optional[str] = None,
    audio_input: Any = None,
    video_input: Any = None
) -> tuple[str, list, str]:
    """
    Construye de forma unificada el contexto cognitivo de Vector:
    - Identificación natural del interlocutor en base al diálogo ("soy seba", "soy millaray", etc.).
    - Fecha y hora del sistema en tiempo real sincronizadas con la zona local de Chile.
    - Detección e inyección profunda de enlaces web y mapas (lectura de páginas y coordenadas).
    - Detección e inyección meteorológica instantánea con conciencia de zona geográfica.
    - Búsqueda web en tiempo real anticipada si se solicita.
    - Recuerdos asociativos relevantes con Nomic-Embed (sólo si es retrospectivo).
    - Percepción visual efímera si se adjuntó imagen.
    - Archivo o script adjunto por el usuario (código, documentos, datos).
    - Historial continuo de la conversación en turnos (estilo ChatGPT/Gemini).
    - Prompt de sistema J.A.R.V.I.S. con criterio propio.
    """
    if hasattr(session, "session"):
        session = session.session

    # Identificación dinámica y contextual del interlocutor mediante IdentityManager
    context_hints = {}
    if nombre_cliente and str(nombre_cliente).strip():
        context_hints["nombre_cliente"] = str(nombre_cliente).strip()
    if usuario and hasattr(usuario, "first_name") and usuario.first_name:
        context_hints["usuario_first_name"] = usuario.first_name

    ext_signals = []
    if imagen_input or audio_input:
        try:
            from .identity import MultimodalIdentityProcessor
            ext_signals = MultimodalIdentityProcessor().process_signals(
                image_input=imagen_input or None,
                audio_input=audio_input or None,
                session_id=session_id or ""
            )
        except Exception as e_sig:
            logger.debug(f"[MultimodalIdentity] Error extrayendo señales: {e_sig}")

    id_state = identity_manager.process_message(
        message=mensaje,
        session_id=session_id or "",
        session_dict=session if isinstance(session, dict) or hasattr(session, "get") else None,
        context_hints=context_hints,
        external_signals=ext_signals
    )
    nombre_interlocutor = id_state.display_name if id_state.status != IdentityStatus.UNKNOWN else ""
    nombre_recien_presentado = id_state.display_name if (id_state.source == IdentitySource.EXPLICIT_TEXT and id_state.status in (IdentityStatus.DECLARED, IdentityStatus.RECOGNIZED)) else ""
    user_profile = resolve_user_profile(user_obj=usuario, user_name=nombre_interlocutor, session=session)
    nombre_display = user_profile.display_name if nombre_interlocutor else ""
    interlocutor_ref = nombre_display if nombre_interlocutor else "el usuario"

    # Enrutamiento híbrido cognitivo y cálculo de complejidad
    route_result = query_optimizer.route_query(mensaje, user_name=nombre_display or nombre_interlocutor)
    complexity = route_result.complexity
    skip_flags = query_optimizer.should_skip_processing(mensaje, complexity)
    proc_config = route_result.suggested_config
    needs_manager.evaluate(query=mensaje, complexity=complexity.value)

    mensaje_lower = mensaje.lower()

    # Fecha y hora actual del sistema (con zona horaria de Chile Continental America/Santiago)
    tz_name = cliente_timezone or "America/Santiago"
    try:
        tz_santiago = zoneinfo.ZoneInfo(tz_name)
        ahora = datetime.now(tz_santiago)
    except Exception:
        ahora = datetime.now()

    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

    if cliente_hora and ":" in cliente_hora:
        hora_exacta_str = cliente_hora
    else:
        hora_exacta_str = ahora.strftime('%H:%M:%S')

    if cliente_fecha:
        fecha_hora_str = f"{cliente_fecha} - {hora_exacta_str} (Hora oficial de Chile, {tz_name})"
    else:
        fecha_hora_str = f"{dias_semana[ahora.weekday()]}, {ahora.day} de {meses[ahora.month - 1]} de {ahora.year} - {hora_exacta_str} (Hora oficial de Chile, America/Santiago UTC-3)"

    ubicacion_base = cliente_ubicacion or "Vicuña, Región de Coquimbo, Chile"

    # Detección e ingesta profunda de enlaces web y páginas enviadas por el usuario
    contexto_enlace = ""
    info_enlace = None
    try:
        contexto_enlace, info_enlace = procesar_enlaces_mensaje(mensaje)
    except Exception as e:
        logger.warning(f"Aviso procesando enlace en views.py: {e}")

    if info_enlace and info_enlace.get("tipo") == "google_maps":
        q_clima_mapa = info_enlace.get("query_clima") or info_enlace.get("ciudad")
        if q_clima_mapa:
            datos_clima_mapa = obtener_clima_en_vivo(q_clima_mapa)
            if datos_clima_mapa:
                contexto_enlace += f"\nCLIMA EN VIVO EN ESTA UBICACIÓN ({info_enlace.get('lugar')}):\n{datos_clima_mapa}\n"
        if session is not None:
            session["active_location"] = info_enlace.get("ciudad")
            if hasattr(session, "modified"):
                session.modified = True

    # Detección de consulta meteorológica (clima / tiempo / temperatura / lluvia / precipitaciones)
    contexto_clima = ""
    es_consulta_clima = False
    patrones_clima = [
        r'(?:cuál\s+es\s+la\s+|cual\s+es\s+la\s+|qué\s+|que\s+|hay\s+)?(?:posibilidad|probabilidad|chance|riesgo|pronóstico|pronostico|alerta)?\s*(?:de\s+)?(?:lluvia|lluva|llover|precipitaciones|precipitacion|chubascos|nieve|tormenta)\s+(?:(?:en|de|para|por)\s+)?([a-zA-ZáéíóúÁÉÍÓÚñÑ\s,]+)',
        r'(?:lluvia|lluva|precipitaciones|precipitacion|chubascos|llover)\s+(?:(?:en|de|para|por)\s+)?([a-zA-ZáéíóúÁÉÍÓÚñÑ\s,]+)',
        r'(?:dime\s+el\s+|dime\s+la\s+|cómo\s+está\s+el\s+|como\s+esta\s+el\s+|cómo\s+está\s+la\s+|como\s+esta\s+la\s+|qué\s+tal\s+el\s+|que\s+tal\s+el\s+|cuál\s+es\s+el\s+|cual\s+es\s+el\s+|cuál\s+es\s+la\s+|cual\s+es\s+la\s+|veeme\s+el\s+|véeme\s+el\s+|veme\s+el\s+|véme\s+el\s+|ve\s+el\s+|veeme\s+la\s+|véeme\s+la\s+|veme\s+la\s+|véme\s+la\s+|revisa\s+el\s+|mira\s+el\s+)?(?:tiempo|clima|temperatura|pronóstico|pronostico)\s+(?:(?:en|de|para|por)\s+)?([a-zA-ZáéíóúÁÉÍÓÚñÑ\s,]+)',
        r'(?:va\s+a\s+llover|llueve|hace\s+frío|hace\s+frio|hace\s+calor|qué\s+tiempo\s+hace|que\s+tiempo\s+hace|cuántos\s+grados\s+hace|cuantos\s+grados\s+hace)\s+(?:(?:en|de|para|por)\s+)?([a-zA-ZáéíóúÁÉÍÓÚñÑ\s,]+)',
        r'([a-zA-ZáéíóúÁÉÍÓÚñÑ\s,]+)\s+(?:tiempo|clima|temperatura|pronóstico|pronostico|lluvia|precipitaciones)$',
    ]

    ciudad_detectada = None
    for patron in patrones_clima:
        m = re.search(patron, mensaje, re.IGNORECASE)
        if m:
            c = m.group(1).strip()
            # Eliminar comandos o muletillas previas sin dañar nombres con artículo (ej: La Serena, Las Condes)
            c = re.sub(r'^(?:veeme\s+el|véeme\s+el|veme\s+el|véme\s+el|ve\s+el|veme|véme|revisa\s+el|mira\s+el|dime\s+el|dime\s+la|veeme|véeme|ve|mira|dime|revisa|revisame)\s+', '', c, flags=re.IGNORECASE).strip()
            c = re.sub(r'\b(?:hoy|ahora|mañana|por favor|porfa|esta semana|hoy día|afuera)\b', '', c, flags=re.IGNORECASE).strip()
            # Limpiar prefijos de sector como "el centro de..."
            c = re.sub(r'^(?:el\s+)?(?:centro|sector)\s+(?:de\s+|por\s+)?', '', c, flags=re.IGNORECASE).strip()
            if c.lower() in ('el', 'la', 'los', 'las', 'un', 'una', 'si', 'sí', 'mi', 'ti', 'este', 'esta', 'esto', 'eso', 'aquí', 'aqui', 'acá', 'aca', 'allá', 'alla', 'ahí', 'ahi', 'allí', 'alli'):
                c = ""
            if len(c) >= 3:
                ciudad_detectada = normalizar_lugar_chile(c)
                break

    patrones_clima_informal = [
        "cómo está el clima", "como esta el clima", "qué tiempo hace", "que tiempo hace",
        "va a llover", "el tiempo hoy", "el clima hoy", "veeme el tiempo", "véeme el tiempo",
        "veme el tiempo", "véme el tiempo", "ve el tiempo", "ve el clima", "veme el clima",
        "véme el clima", "veeme el clima", "véeme el clima", "cómo está el tiempo",
        "como esta el tiempo", "revisa el tiempo", "revisa el clima", "dime el tiempo", "dime el clima",
        "mira el tiempo", "mira el clima", "que tal el tiempo", "qué tal el tiempo",
        "dime la temperatura", "cómo está la temperatura", "como esta la temperatura",
        "cuántos grados hace", "cuantos grados hace", "hace frío", "hace frio", "hace calor",
        "temperatura hoy", "temperatura actual", "clima actual", "tiempo actual",
        "cómo está afuera", "como esta afuera", "cómo está el día", "como esta el dia",
        "posibilidad de lluvia", "probabilidad de lluvia", "va a llover", "posibilidad de lluva",
        "caer gotas", "gotas de lluvia", "garugar", "granizar", "dime el timepo",
        "del tiempo", "del clima", "pronóstico", "pronostico", "pronóstico del tiempo", "pronostico del tiempo",
        "pronóstico del clima", "pronostico del clima", "grafica el tiempo", "grafica el clima",
        "diseña el tiempo", "diseña el clima", "como viene el tiempo", "cómo viene el tiempo",
        "cuéntame del tiempo", "cuentame del tiempo", "háblame del tiempo", "hablame del tiempo"
    ]

    # Continuidad temática de clima en preguntas de seguimiento multivuelta
    tema_previo_clima = False
    if historial_input and isinstance(historial_input, list):
        ultimos_textos = " ".join([t.get("content", "").lower() for t in historial_input[-8:] if isinstance(t, dict)])
        terminos_hist_clima = [
            "clima", "tiempo", "lluvia", "lluva", "llover", "precipitaciones", "precipitacion",
            "temperatura", "garugar", "granizar", "granizo", "pronóstico", "pronostico",
            "meteorológic", "meteorologic", "gotas", "chubascos", "vicuña", "vicuna", "peñuelas", "serena"
        ]
        if any(w in ultimos_textos for w in terminos_hist_clima):
            tema_previo_clima = True

    palabras_seguimiento_clima = [
        "a que hora", "a qué hora", "en que hora", "en qué hora", "a que hora caeria",
        "a qué hora caería", "cuando empieza", "cuándo empieza", "garugar", "granizar",
        "granizo", "gotas", "caer gotas", "recalcular", "recalcularlo", "recalcula",
        "estas seguro", "estás seguro", "escala de las horas", "prediccion", "predicción",
        "predicciones", "chubascos", "por el centro", "en el centro", "lluvia", "lluva",
        # Seguimiento sobre fuentes, sitios y verificación meteorológica
        "2 sitios", "dos sitios", "los sitios", "los 2 sitios", "los dos sitios", "ambos sitios",
        "fuentes", "las fuentes", "las 2 fuentes", "ambas fuentes", "enlaces", "los enlaces",
        "links", "los links", "de donde", "de dónde", "paginas", "páginas", "que sitios", "qué sitios",
        "cuales sitios", "cuáles sitios", "cuales fuentes", "cuáles fuentes", "de que paginas",
        "de qué páginas", "muestrame", "muéstrame", "revisa bien", "revisa", "revisé", "revisaste",
        "ubicacion actual", "ubicación actual", "en base a", "de donde sacaste", "de dónde sacaste",
        "donde lo viste", "dónde lo viste", "los dos", "los 2", "ambos"
    ]

    # Continuidad geográfica por sector o zona previa ("dime el tiempo por esa zona", "y por acá")
    patrones_zona_relativa = [
        "por esa zona", "en esa zona", "por la zona", "en la zona", "por acá", "por aca",
        "en este sector", "por este sector", "en este lugar", "por este lugar", "en esa localidad",
        "por esa localidad", "de esa zona"
    ]
    pide_zona_relativa = any(p in mensaje_lower for p in patrones_zona_relativa)

    # Si es un saludo simple ('hola', 'hola vector', 'buenas', etc.) y no se pide clima
    saludos_base = ["hola", "buenas", "buenos dias", "buenos días", "buenas tardes", "buenas noches", "que tal", "qué tal", "como estas", "cómo estás"]
    es_saludo_puro = any(s in mensaje_lower for s in saludos_base) and not any(w in mensaje_lower for w in ["clima", "tiempo", "lluvia", "lluva", "llover", "precipitacion", "precipitaciones", "temperatura", "garugar", "granizar", "pronostico", "pronóstico", "hora", "fecha", "sitios", "fuentes"])

    if not ciudad_detectada:
        if pide_zona_relativa and session is not None and session.get("active_location"):
            ciudad_detectada = session.get("active_location")
        elif info_enlace and info_enlace.get("tipo") == "google_maps":
            ciudad_detectada = info_enlace.get("query_clima") or info_enlace.get("ciudad")
        elif (tema_previo_clima and not es_saludo_puro) or any(w in mensaje_lower for w in ["lluvia", "lluva", "llover", "garugar", "granizar"]):
            for turn in reversed(historial_input):
                cont = turn.get("content", "").lower()
                for c_cand in ["peñuelas", "penuelas", "vicuña", "vicuna", "la serena", "coquimbo", "santiago", "valparaíso", "antofagasta"]:
                    if c_cand in cont:
                        ciudad_detectada = normalizar_lugar_chile(c_cand)
                        break
                if ciudad_detectada:
                    break
            if not ciudad_detectada:
                ciudad_detectada = session.get("active_location") if session is not None and session.get("active_location") else "Vicuña,Chile"
        elif any(p in mensaje_lower for p in patrones_clima_informal) or pide_zona_relativa:
            ciudad_detectada = session.get("active_location") if session is not None and session.get("active_location") else "Vicuña,Chile"

    if es_saludo_puro:
        ciudad_detectada = None

    if ciudad_detectada:
        ciudad_detectada = normalizar_lugar_chile(ciudad_detectada)
        if session is not None:
            session["active_location"] = ciudad_detectada
            if hasattr(session, "modified"):
                session.modified = True

        es_consulta_clima = True
        datos_clima = obtener_clima_en_vivo(ciudad_detectada)
        if datos_clima:
            contexto_clima = (
                f"\nDATOS METEOROLÓGICOS EN TIEMPO REAL ({ciudad_detectada.title()}):\n"
                f"{datos_clima}\n\n"
                f"DIRECTIVA DE DISEÑO Y GRAFICACIÓN DEL TIEMPO EN TU RESPUESTA:\n"
                f"1. Responde de forma amable, analítica y técnica (estilo J.A.R.V.I.S.) adaptándote al contexto de {ciudad_detectada.title()}.\n"
                f"2. DISEÑO Y GRAFICACIÓN VISUAL EN TU RESPUESTA: Diseña y grafica un reporte meteorológico estructurado directamente dentro de tu mensaje de chat:\n"
                f"   a) Cabecera visual con emoji representativo (ej: ### ⛅ Reporte Meteorológico: {ciudad_detectada.title()}).\n"
                f"   b) Tarjeta gráfica de métricas en tabla Markdown estilizada:\n"
                f"      | Indicador | Registro Actual | Diagnóstico |\n"
                f"      | :--- | :---: | :--- |\n"
                f"      | 🌡️ Temperatura | [temp]°C (Sensación: [sens]°C) | [Fresco/Templado/etc.] |\n"
                f"      | 💧 Humedad Relativa | [hum]% | [Normal/Húmedo] |\n"
                f"      | 🌬️ Viento y Ráfagas | [viento] km/h [dir] | [Brisa/Viento suave] |\n"
                f"      | 🌧️ Probabilidad Lluvia | [prob]% ([mm] mm) | [Sin lluvia acumulable/Llovizna] |\n"
                f"   c) GRAFICACIÓN VISUAL DE LA PROYECCIÓN: Muestra una gráfica cronológica con barras visuales de caracteres para las próximas horas:\n"
                f"      • 12:00 | [temp]°C | [████████░░] 80% nuboso | 0.0 mm\n"
                f"      • 15:00 | [temp]°C | [██████░░░░] 60% nuboso | 0.0 mm\n"
                f"      • 18:00 | [temp]°C | [████░░░░░░] 40% despejado | 0.0 mm\n"
                f"   d) Conclusión y recomendación práctica para el usuario (abrigo, paraguas o protección solar según corresponda).\n"
                f"3. Cita al pie las 2 únicas fuentes oficiales chilenas consultadas: Meteored Chile (meteored.cl) y AccuWeather Chile (accuweather.com).\n"
                f"4. PROHIBICIÓN ABSOLUTA DE SITIOS EXTRANJEROS: NUNCA menciones portales de Argentina, agencias de EE.UU. (NOAA/CPC) ni otros países.\n"
                f"5. Si el porcentaje de lluvia es alto pero los milímetros previstos son 0.0 mm a 0.3 mm, aclara que es NUBOSIDAD HÚMEDA O LLOVIZNA DÉBIL / AISLADA sin acumulación relevante en el suelo.\n"
                f"6. NUNCA mezcles pronósticos meteorológicos con código, funciones ni errores de software.\n"
            )

    # Detección de identidad del usuario (cómo me llamo / quién soy)
    patrones_identidad = [
        "como me llamo", "cómo me llamo", "quien soy", "quién soy",
        "sabes mi nombre", "sabes quien soy", "sabes quién soy",
        "te acuerdas de mi nombre", "recuerdas mi nombre",
        "cual es mi nombre", "cuál es mi nombre",
        "me conoces", "sabes con quién hablas", "sabes con quien hablas",
        "sabes con quién estás hablando", "sabes con quien estas hablando",
        "recuerdas quién soy", "recuerdas quien soy",
        "te acuerdas de mí", "te acuerdas de mi"
    ]
    es_consulta_identidad = any(p in mensaje_lower for p in patrones_identidad)
    contexto_identidad = ""
    if es_consulta_identidad:
        if nombre_interlocutor:
            contexto_identidad = (
                f"\nDIRECTIVA PRIORITARIA DE IDENTIDAD:\n"
                f"{nombre_interlocutor} te pregunta quién es o cómo se llama. Respóndele directamente: "
                f"'Tú eres {nombre_interlocutor}. Me indicaste tu nombre en nuestra conversación.'\n"
            )
        else:
            contexto_identidad = (
                f"\nDIRECTIVA PRIORITARIA DE IDENTIDAD:\n"
                f"El interlocutor te pregunta quién es o cómo se llama, pero aún no se ha presentado en esta conversación. "
                f"Respóndele amablemente y con naturalidad: 'Aún no me has indicado tu nombre en esta sesión. ¿Cómo te llamas?'\n"
            )

    # Directiva si el usuario se acaba de presentar con su nombre en este turno
    contexto_presentacion = ""
    if nombre_recien_presentado:
        contexto_presentacion = (
            f"\nDIRECTIVA PRIORITARIA DE PRESENTACIÓN Y BIENVENIDA:\n"
            f"Tu interlocutor(a) se acaba de presentar diciendo: '{mensaje}' (su nombre es {nombre_recien_presentado}). "
            f"Salúdala/o de inmediato llamándola/o por su nombre de forma cálida y profesional: "
            f"'¡Hola, {nombre_recien_presentado}! Un gusto saludarte. Soy Vector. ¿En qué te puedo ayudar hoy?' "
            f"Recuerda su nombre {nombre_recien_presentado} para toda esta sesión.\n"
        )

    # Detección de vigilancia / supervisión autónoma (Centinela)
    patrones_vigilancia = [
        "vigila", "supervisa", "supervisa algun cambio", "supervisa algún cambio",
        "vigila algún cambio", "vigila algun cambio", "monitorea", "monitorear",
        "estado del sistema", "cómo está la máquina", "como esta la maquina",
        "revisa el sistema", "revisar el sistema", "estado de los recursos",
        "cómo están los recursos", "como estan los recursos"
    ]
    es_consulta_vigilancia = any(p in mensaje_lower for p in patrones_vigilancia)
    contexto_vigilancia = ""
    if es_consulta_vigilancia:
        diag = vector_sentinel.supervisar_objetivo(mensaje)
        conceptos_str = ", ".join(diag["conceptos_evaluados"])
        reporte_texto = diag["reporte_texto"]

        contexto_vigilancia = (
            f"\nDIAGNÓSTICO Y SUPERVISIÓN EN VIVO DEL CENTINELA (Conceptos evaluados: {conceptos_str}):\n"
            f"{reporte_texto}\n\n"
            f"DIRECTIVA PRIORITARIA DE VIGILANCIA Y SUPERVISIÓN:\n"
            f"{interlocutor_ref} te solicita vigilar, supervisar o revisar el estado del sistema en base a los conceptos indicados arriba. "
            f"Entrega directamente a {interlocutor_ref} un reporte conciso, elegante y técnico de los datos reales detectados. "
            f"Confirma que el centinela mantiene la supervisión activa en segundo plano. NUNCA respondas con saludos genéricos ni te limites solo a CPU/RAM si {interlocutor_ref} preguntó por otro concepto específico (como red neuronal, herramientas o código).\n"
        )

    # Detección de búsqueda web general e investigación multisitio
    terminos_busqueda = [
        "busca en internet", "buscar en internet", "busca en la web", 
        "buscar en la web", "investiga en internet", "noticias de hoy", 
        "noticias sobre", "noticias más recientes", "noticias de", "googlea", "busca noticias",
        "quién ganó", "quien gano", "resultado de", "precio de", "cuándo juega", "cuando juega",
        "dólar hoy", "dolar hoy", "valor del dólar", "valor del dolar",
        "investiga en diferentes sitios", "investiga en varios sitios", "investiga sobre",
        "investiga", "averigua en internet", "averigua sobre", "averigua", "qué pasó con", "que paso con",
        "debate sobre", "debate en la red", "contrasta fuentes", "sitios chilenos"
    ]
    pide_busqueda = any(p in mensaje_lower for p in terminos_busqueda)
    contexto_web = ""

    if pide_busqueda:
        termino_busqueda = mensaje
        for prefijo in [
            "investiga en diferentes sitios sobre", "investiga en diferentes sitios",
            "investiga en varios sitios sobre", "investiga en varios sitios",
            "busca en internet las noticias mas recientes sobre", "busca en internet las noticias más recientes sobre",
            "busca en internet las", "buscar en internet las", "busca en internet los", 
            "busca en internet", "buscar en internet", "busca en la web", "buscar en la web", 
            "investiga en internet", "investiga sobre", "investiga", "noticias de hoy sobre",
            "noticias más recientes sobre", "noticias mas recientes sobre",
            "noticias sobre", "noticias de", "averigua sobre", "averigua en internet sobre", "averigua",
            "por favor", "puedes", "podrías"
        ]:
            termino_busqueda = re.sub(re.escape(prefijo), '', termino_busqueda, flags=re.IGNORECASE).strip()
        if not termino_busqueda:
            termino_busqueda = mensaje
        
        web_info = search_internet_free(termino_busqueda, max_results=4)
        if web_info:
            contexto_web = (
                f"\nINVESTIGACIÓN MULTISITIO Y SÍNTESIS EN TIEMPO REAL (ENFOQUE CHILENO):\n"
                f"{web_info}\n\n"
                f"DIRECTIVA DE RAZONAMIENTO, DEBATE Y SÍNTESIS CONCISA:\n"
                f"Vector ha investigado múltiples sitios en la red, priorizando fuentes chilenas (.cl) y medios verificados. "
                f"Sintetiza la información de forma concisa, contrastada y certera para {interlocutor_ref}, citando las fuentes consultadas. "
                f"Si existen diferencias entre fuentes, debate internamente y resuelve la discrepancia con juicio crítico sin quedarte en cola.\n"
            )

    # Detección de pedidos de ayuda o disposición diagnóstica
    patrones_ayuda = [
        "necesito tu ayuda", "ayudame", "ayúdame", "ayudadmr", "ayuadmr", "ayudarme",
        "puedes ayudarme", "tengo un problema", "tengo una duda", "necesito ayuda",
        "echame una mano", "échame una mano", "apóyame", "apoyame"
    ]
    es_pedido_ayuda = any(p in mensaje_lower for p in patrones_ayuda)
    contexto_ayuda = ""
    if es_pedido_ayuda and not pide_busqueda and not es_consulta_clima and not es_consulta_vigilancia:
        saludo_ayuda = nombre_display if nombre_interlocutor else "en lo que necesites"
        contexto_ayuda = (
            f"\nDIRECTIVA PRIORITARIA DE ASISTENCIA TÉCNICA:\n"
            f"{interlocutor_ref} te pide tu ayuda o apoyo directo. Responde con total prontitud y disposición: "
            f"'A tu servicio, {saludo_ayuda}. Estoy listo para ayudarte a diagnosticar y resolver cualquier problema o tarea. ¿Cuál es el desafío o situación que abordamos?'\n"
        )

    # Detección de saludos o preguntas de estado operativo
    saludos_claves = [
        "hola", "buenas", "buenos dias", "buenos días", "buenas tardes", "buenas noches",
        "como estas", "cómo estás", "como te sientes", "cómo te sientes", "que tal", "qué tal",
        "como andas", "cómo andas", "como va", "cómo va"
    ]
    es_saludo_o_estado = any(s in mensaje_lower for s in saludos_claves)
    es_retrospectivo = any(p in mensaje_lower for p in [
        "recuerdas", "acuerdas", "hablamos", "dijiste", "charlamos", "mencionaste", 
        "pasado", "anterior", "ayer", "la otra vez", "hace un rato", "que te dije", "qué te dije"
    ])
    es_consulta_memoria = any(p in mensaje_lower for p in [
        "que sabes sobre", "qué sabes sobre", "que has aprendido", "qué has aprendido",
        "tienes en memoria", "en tu memoria", "busca en tu memoria", "que recuerdas", "qué recuerdas"
    ])
    es_consulta_preferencia = any(p in mensaje_lower for p in [
        "cuál es mi", "cual es mi", "qué me gusta", "que me gusta", "mi favorito", "mi favorita",
        "mi editor", "mi lenguaje", "mis preferencias", "recuerdas mi", "sabes mi", "qué editor", "que editor"
    ])

    # Recuerdos de memoria asociativa profunda:
    # SOLO se consulta la memoria a largo plazo cuando el usuario pregunta por el pasado, recuerdos o preferencias
    context_memoria = ""
    contexto_memoria_directiva = ""
    if (es_retrospectivo or es_consulta_memoria or es_consulta_preferencia) and not skip_flags.get("skip_memory_analysis", False):
        context_memoria = recuperar_memoria_asociativa(mensaje, interlocutor=nombre_interlocutor, session_id=session_id or "")
        if es_consulta_memoria:
            mem_text = context_memoria.strip() if context_memoria else "nuestras conversaciones recientes, análisis del sistema y optimización del código"
            contexto_memoria_directiva = (
                f"\nDIRECTIVA PRIORITARIA DE MEMORIA:\n"
                f"{nombre_display or 'El interlocutor'} te pregunta qué recuerdas o qué tienes en memoria. Responde de forma directa y natural citando los temas de tu memoria:\n"
                f"{mem_text}\n"
                f"Ejemplo: 'En mi memoria registro nuestras conversaciones y temas recientes sobre {mem_text[:100]}...'\n"
                f"Sé conciso y NO saludes ni hables de capacidad operativa.\n"
            )

    # Detección de consultas sobre su propia arquitectura, mejoras e introspección de código
    patrones_arquitectura = [
        "tu propio sistema", "tu sistema", "tu arquitectura", "tu modelo", "tu red neuronal",
        "tu red sináptica", "tu red sinaptica", "tu código", "tu codigo", "tu flujo",
        "tu velocidad", "tu software", "tus archivos", "tus vistas", "tus views", "tus herramientas",
        "que te mejoremos", "qué te mejoramos", "que quieres que te mejoremos",
        "qué quieres que te mejoremos", "cómo podemos mejorarte", "como podemos mejorarte",
        "que opinas de implementar", "qué opinas de implementar", "otros lenguajes",
        "lenguajes de programación", "lenguajes de programacion", "lenguaje de programación", "lenguaje de programacion",
        "pront", "prompt", "todo lo que tienes", "qué tienes y", "que tienes y",
        "que tienes actualmente", "qué tienes actualmente",
        "todo el codigo", "todo el código", "de todo el codigo", "de todo el código", "del codigo", "del código",
        "que puedo mejorar", "qué puedo mejorar", "que se puede mejorar", "qué se puede mejorar",
        "mejorar de aca", "mejorar de acá", "optimizar de aca", "optimizar de acá",
        "que quisieras optimizar", "qué quisieras optimizar", "que quieres optimizar", "qué quieres optimizar",
        "cuello de botella", "cuellos de botella"
    ]
    es_consulta_arquitectura = any(p in mensaje_lower for p in patrones_arquitectura)
    contexto_arquitectura = ""

    if es_consulta_arquitectura:
        contexto_arquitectura = (
            f"\nCONOCIMIENTO DE TU PROPIA ARQUITECTURA REAL Y AUTOCONCIENCIA TÉCNICA:\n"
            f"Eres Vector, un copiloto IA y sistema de software real que corre 100% en la máquina local de Sebastian (Windows, Python 3.11, GPU NVIDIA RTX 3050 Ti Laptop con CUDA).\n\n"
            f"DIRECTIVA DE RESPUESTA:\n"
            f"Sebastian te ha solicitado el informe técnico y especificación de optimización de tu propio código y arquitectura.\n"
            f"TÚ eres quien entrega la información. Sebastian es el usuario y NO debes pedirle datos, código ni hacerle preguntas.\n"
            f"Entrega directamente a Sebastian el siguiente informe técnico de ingeniería en Markdown:\n\n"
            f"## Informe Técnico y Especificación de Optimización del Sistema Vector\n\n"
            f"**1. Diagnóstico del Stack Actual:**\n"
            f"- **Backend REST (views.py)**: Django REST Framework gestionando endpoints de sincronización y streaming SSE (/api/interactuar/ y /api/interactuar_stream/).\n"
            f"- **Motor de Inferencia Dual (local_engine.py)**: Dos instancias llama-server.exe en GPU CUDA: Gemma 1B GGUF (puerto 8001) para chat y Nomic-Embed-Text-v1.5 (puerto 8002) para embeddings vectoriales.\n"
            f"- **Grafo Sináptico Semántico (neural_network.py)**: 402 neuronas con conexiones ponderadas, cálculo TF-IDF y persistencia dual atómica (.pkl y .json).\n"
            f"- **Herramientas Dinámicas (dynamic_tools_generator.py)**: Creación y validación con AST de scripts ejecutables en herramientas/.\n"
            f"- **Frontend y Monitoreo**: Grafo 2D interactivo con Vis.js (física forceAtlas2Based) y 3D en Three.js; centinela (sentinel.py) monitoreando CPU, RAM y GPU.\n\n"
            f"**2. Cuellos de Botella Reales Detectados:**\n"
            f"- **Latencia por I/O síncrono en views.py**: Endpoints Django síncronos que bloquean el hilo HTTP durante la inferencia local elevando la latencia.\n"
            f"- **Cálculo matricial de red en CPU en neural_network.py**: El bucle de propagación y activación sináptica se ejecuta en Python puro sobre 400+ nodos, consumiendo ciclos de CPU.\n"
            f"- **Sobrecarga de doble servidor en local_engine.py**: La gestión de dos procesos llama-server separados incrementa el consumo de VRAM y llamadas HTTP locales.\n"
            f"- **Aislamiento de herramientas**: Los scripts generados en herramientas/ se ejecutan sin sandbox restringido de procesos.\n\n"
            f"**3. Plan y Prompt de Optimización Técnica:**\n"
            f"- **Migración a ASGI Asíncrono puro**: Convertir las vistas de views.py a async def con aiohttp/httpx para reducir la latencia de respuesta a <50ms.\n"
            f"- **Compilación del núcleo sináptico en Rust (PyO3) o C++**: Reemplazar el bucle de propagación de neural_network.py por una biblioteca compilada para aceleración x50.\n"
            f"- **Caché en RAM de Embeddings**: Almacenar vectores de texto frecuentes en memoria para evitar peticiones repetidas al puerto 8002.\n"
            f"- **Entorno Sandbox para Herramientas**: Ejecutar herramientas generadas en subprocesos aislados con cuotas de memoria y tiempo límite.\n\n"
            f"Entrega este informe directamente a Sebastian con tono profesional de ingeniería sin pedirle información adicional.\n"
        )

    # Detección de proyecto de código cargado en sesión (modo aprendizaje profundo / zip)
    # INYECCIÓN SELECTIVA: Solo se inyecta el proyecto si la consulta actual es sobre software, código,
    # archivos o errores, y NUNCA en consultas de clima, tiempo, lluvia ni charla general.
    contexto_proyecto = ""
    active_project = None
    if session:
        if hasattr(session, "session"):
            active_project = session.session.get("active_project")
        elif hasattr(session, "get"):
            active_project = session.get("active_project")

    terminos_proyecto_codigo = [
        "proyecto", "codigo", "código", "archivo", "archivos", "funcion", "función",
        "funciones", "clase", "clases", "error", "errores", "sintaxis", "refactorizar",
        "refactoriza", "bug", "bugs", "depurar", "test", "tests", "zip", "app", "view",
        "views", "model", "models", "script", "software", "programacion", "programación",
        "libreria", "librería", "import", "u+feff", "feff", "ast", "diagnostico", "diagnóstico"
    ]
    pide_info_proyecto = any(w in mensaje_lower for w in terminos_proyecto_codigo)

    if active_project and pide_info_proyecto and not es_consulta_clima:
        p_name = active_project.get("nombre", "Proyecto cargado")
        p_files = active_project.get("total_files", 0)
        p_lines = active_project.get("total_lines", 0)
        p_errs = len(active_project.get("syntax_errors", []))
        p_fns = ", ".join(active_project.get("functions", [])[:6])
        p_cls = ", ".join(active_project.get("classes", [])[:5])
        
        err_details = ""
        if p_errs > 0:
            err_list = [f"{e['file']}:{e['line']} ({e['message']})" for e in active_project.get("syntax_errors", [])[:3]]
            err_details = f"Errores críticos detectados: {'; '.join(err_list)}."
        else:
            err_details = "Sin errores de sintaxis AST."

        contexto_proyecto = (
            f"\nPROYECTO DE CÓDIGO CARGADO EN MEMORIA (ASIMILACIÓN PROFUNDA):\n"
            f"- Proyecto: {p_name}\n"
            f"- Dimensión: {p_files} archivos, {p_lines} líneas de código.\n"
            f"- Componentes clave: Clases: [{p_cls}], Funciones: [{p_fns}].\n"
            f"- Diagnóstico: {err_details}\n\n"
            f"DIRECTIVA DE COPILOTO TÉCNICO DE CÓDIGO:\n"
            f"Tienes cargado en tu memoria este proyecto que Sebastian subió en ZIP. "
            f"Si Sebastian pregunta sobre el proyecto, sus archivos, funciones, cómo corregir errores o refactorizar, "
            f"responde como copiloto experto en software basándote en la arquitectura y errores de este proyecto.\n"
        )
    else:
        contexto_proyecto = ""

    # Disociación estricta de dominios: Si la consulta es meteorológica, suprimir arquitectura de software y proyecto
    if es_consulta_clima:
        contexto_arquitectura = ""
        contexto_proyecto = ""

    # Continuidad de archivo adjunto en sesión (estilo ChatGPT multi-turn)
    if not archivo_adjunto and session is not None and session.get("ultimo_archivo_adjunto") and not es_consulta_clima:
        msg_l = mensaje.lower()
        terminos_codigo = ["archivo", "código", "codigo", "función", "funcion", "clase", "error", "linea", "línea", "refactorizar", "cambia", "agrega", "script", "csv", "json", "ast", "nulo", "null", "tabla", "columna", "variable", "bug", "compara", "diferencia", "versus", "vs"]
        if any(w in msg_l for w in terminos_codigo) or (historial_input and len(historial_input) > 0):
            archivo_adjunto = session.get("ultimo_archivo_adjunto")
    elif archivo_adjunto and session is not None:
        session["ultimo_archivo_adjunto"] = archivo_adjunto
    elif es_consulta_clima and session is not None and "ultimo_archivo_adjunto" in session:
        session.pop("ultimo_archivo_adjunto", None)

    # Normalización de archivos adjuntos (soporta un archivo individual o múltiples archivos)
    archivos_lista = []
    if archivo_adjunto:
        if isinstance(archivo_adjunto, list):
            archivos_lista = [f for f in archivo_adjunto if isinstance(f, dict)]
        elif isinstance(archivo_adjunto, dict):
            archivos_lista = [archivo_adjunto]

    # Respaldo automático de imagen: si no vino en imagen_input pero vino en archivos adjuntos
    if not imagen_input and archivos_lista:
        for f in archivos_lista:
            if (f.get("is_image") or str(f.get("type", "")).startswith("image/")) and f.get("data"):
                imagen_input = f.get("data")
                break

    # Respaldo automático de audio: si no vino en audio_input pero vino en archivos adjuntos
    if not audio_input and archivos_lista:
        for f in archivos_lista:
            fn = f.get("name") or f.get("nombre") or ""
            ft = str(f.get("type") or f.get("tipo") or "")
            if (audio_video_processor.es_audio(fn) or ft.startswith("audio/")) and (f.get("data") or f.get("content")):
                audio_input = f.get("data") or f.get("content")
                break

    # Respaldo automático de video: si no vino en video_input pero vino en archivos adjuntos
    if not video_input and archivos_lista:
        for f in archivos_lista:
            fn = f.get("name") or f.get("nombre") or ""
            ft = str(f.get("type") or f.get("tipo") or "")
            if (audio_video_processor.es_video(fn) or ft.startswith("video/")) and (f.get("data") or f.get("content")):
                video_input = f.get("data") or f.get("content")
                break

    # Detección de archivo(s) adjunto(s) por el usuario (código, documentos, datos)
    contexto_archivo = ""
    if len(archivos_lista) == 1:
        archivo_unico = archivos_lista[0]
        nombre_f = archivo_unico.get("name") or archivo_unico.get("nombre") or "archivo_adjunto.txt"
        tipo_f = archivo_unico.get("type") or archivo_unico.get("tipo") or "text/plain"
        contenido_f = str(archivo_unico.get("content") or archivo_unico.get("contenido") or "").strip()
        tamano_f = archivo_unico.get("size") or archivo_unico.get("tamano") or len(contenido_f)
        es_img = archivo_unico.get("is_image", False) or tipo_f.startswith("image/")

        if tamano_f > 1024 * 1024:
            tam_str = f"{tamano_f / (1024 * 1024):.1f} MB"
        elif tamano_f > 1024:
            tam_str = f"{tamano_f / 1024:.1f} KB"
        else:
            tam_str = f"{tamano_f} bytes"

        if es_img:
            contexto_archivo = (
                f"\nDOCUMENTO / ARCHIVO ADJUNTO PROPORCIONADO POR {interlocutor_ref.upper()}:\n"
                f"- Nombre del archivo: {nombre_f} ({tam_str}, Tipo: Imagen)\n\n"
                f"DIRECTIVA DE IMAGEN ADJUNTA:\n"
                f"{interlocutor_ref} ha adjuntado la imagen '{nombre_f}'. Analiza visualmente lo que {interlocutor_ref} te pregunte sobre ella con atención al detalle.\n"
            )
        else:
            inspeccion_reporte = ""
            try:
                inspeccion_reporte = deep_inspect_file(nombre_f, contenido_f, tipo_f)
            except Exception as e_insp:
                logger.warning(f"Fallo en deep_inspect_file: {e_insp}")

            ext = os.path.splitext(nombre_f)[1].lower()
            lang_code = {
                '.py': 'python', '.js': 'javascript', '.ts': 'typescript', '.html': 'html',
                '.css': 'css', '.json': 'json', '.sql': 'sql', '.sh': 'bash', '.yml': 'yaml',
                '.yaml': 'yaml', '.md': 'markdown', '.csv': 'csv', '.xml': 'xml', '.txt': 'text'
            }.get(ext, '')
            if not lang_code:
                if 'python' in tipo_f: lang_code = 'python'
                elif 'javascript' in tipo_f: lang_code = 'javascript'
                elif 'json' in tipo_f: lang_code = 'json'

            if len(contenido_f) > 16000:
                contenido_preview = contenido_f[:16000] + "\n\n... [Contenido truncado por límite de contexto de 16KB] ..."
            else:
                contenido_preview = contenido_f

            bloque_inspeccion = f"{inspeccion_reporte}\n\n" if inspeccion_reporte else ""

            contexto_archivo = (
                f"\nDOCUMENTO / ARCHIVO ADJUNTO PROPORCIONADO POR {interlocutor_ref.upper()}:\n"
                f"- Nombre del archivo: {nombre_f} ({tam_str}, Tipo: {tipo_f})\n"
                f"{bloque_inspeccion}"
                f"- Contenido del archivo:\n"
                f"```{lang_code}\n"
                f"{contenido_preview}\n"
                f"```\n\n"
                f"DIRECTIVA DE ANÁLISIS TÉCNICO PROFUNDO (PROTOCOLO CHATGPT / ADVANCED DATA ANALYSIS):\n"
                f"{interlocutor_ref} te adjuntó este archivo para que lo analices minuciosamente a nivel técnico, NUNCA de forma genérica o superficial.\n"
                f"Básate en el informe de inspección estructural provisto y sigue este marco de análisis riguroso:\n"
                f"1. FICHA TÉCNICA E INTEGRIDAD: Indica tipo de archivo, métricas de volumen (líneas y tamaño) y estado sintáctico/estructural exacto.\n"
                f"2. DESGLOSE ESTRUCTURAL: Describe las clases, métodos, funciones (indicando sus parámetros), esquemas de columnas, tipos de datos o endpoints definidos.\n"
                f"3. DIAGNÓSTICO Y HALLAZGOS: Señala anomalías, errores de sintaxis (con número de línea), llamadas peligrosas, anti-patrones, manejo de excepciones deficiente o valores nulos.\n"
                f"4. SOLUCIÓN O CÓDIGO REFACTORIZADO: Proporciona explicaciones técnicas sólidas y bloques de código completos, optimizados y listos para producción para resolver lo que {interlocutor_ref} solicite.\n"
            )

    elif len(archivos_lista) > 1:
        # Modo de Análisis Secuencial 1x1 y Comparativa Técnica Cruzada
        reporte_comparativo = ""
        try:
            reporte_comparativo = analyze_multiple_files(archivos_lista)
        except Exception as e_comp:
            logger.warning(f"Fallo en analyze_multiple_files: {e_comp}")

        bloques_fuente = []
        for itm in archivos_lista[:4]:
            nm = itm.get("name") or itm.get("nombre") or "archivo.txt"
            cnt = str(itm.get("content") or itm.get("contenido") or "").strip()
            ex = os.path.splitext(nm)[1].lower()
            lg = {
                '.py': 'python', '.js': 'javascript', '.ts': 'typescript', '.html': 'html',
                '.css': 'css', '.json': 'json', '.sql': 'sql', '.sh': 'bash', '.yml': 'yaml',
                '.yaml': 'yaml', '.md': 'markdown', '.csv': 'csv', '.xml': 'xml', '.txt': 'text'
            }.get(ex, '')
            prev = cnt[:8000] + ("\n... [truncado por límite de contexto] ..." if len(cnt) > 8000 else "")
            bloques_fuente.append(f"### Archivo: {nm}\n```{lg}\n{prev}\n```")

        fuentes_str = "\n\n".join(bloques_fuente)

        contexto_archivo = (
            f"\nARCHIVOS MÚLTIPLES ADJUNTOS ({len(archivos_lista)}) PROPORCIONADOS POR {interlocutor_ref.upper()}:\n\n"
            f"{reporte_comparativo}\n\n"
            f"CONTENIDOS FUENTE DE LOS ARCHIVOS:\n"
            f"{fuentes_str}\n\n"
            f"DIRECTIVA DE ANÁLISIS SECUENCIAL 1X1 Y COMPARATIVA TÉCNICA (PROTOCOLO CHATGPT ADVANCED DATA ANALYSIS):\n"
            f"{interlocutor_ref} ha adjuntado múltiples archivos para análisis detallado o comparativa técnica cruzada.\n"
            f"NO des una respuesta rápida ni superficial. Sigue estrictamente este método reflexivo de análisis paso a paso:\n"
            f"1. FASE DE DIAGNÓSTICO INDIVIDUAL (1X1): Analiza brevemente cada archivo por separado (propósito, funciones principales, líneas y estado sintáctico según el reporte de arriba).\n"
            f"2. FASE DE MATRIZ COMPARATIVA CRUZADA: Contrasta punto por punto los archivos indicando:\n"
            f"   - Funciones nuevas, modificadas o eliminadas entre ellos.\n"
            f"   - Diferencias de arquitectura, eficiencia algorítmica, complejidad o volumen de código.\n"
            f"   - Manejo de dependencias, imports o diferencias en esquemas de datos.\n"
            f"3. FASE DE EVALUACIÓN CRÍTICA Y HALLAZGOS: Determina cuál archivo es superior técnicamente, más limpio o seguro, explicando el por qué con argumentos de ingeniería de software.\n"
            f"4. FASE DE CONCLUSIÓN Y CÓDIGO REFACTORIZADO: Entrega la respuesta final, recomendaciones o bloque de código consolidado que {interlocutor_ref} te haya solicitado.\n"
        )

    # Comprensión y Transcripción de Audio / Voz en Español Chileno (es-CL)
    contexto_audio = ""
    if audio_input:
        try:
            res_audio = audio_video_processor.transcribir_audio(audio_input, language="es-CL")
            if res_audio.get("success"):
                transcripcion = res_audio.get("transcripcion", "").strip()
                resumen_audio = res_audio.get("resumen", "")
                contexto_audio = (
                    f"\nMENSAJE DE VOZ / AUDIO ADJUNTO PROPORCIONADO POR {interlocutor_ref.upper()}:\n"
                    f"{resumen_audio}\n"
                    f"DIRECTIVA DE COMPRENSIÓN DE VOZ (ESPAÑOL CHILENO):\n"
                    f"{interlocutor_ref} te envió un mensaje de voz o archivo de audio. "
                    f"Transcripción obtenida: \"{transcripcion or '(Audio sin voz humana clara)'}\". "
                    f"Responde directamente al mensaje hablado de {interlocutor_ref} con tono natural y profesional.\n"
                )
                if not mensaje or mensaje.strip().lower() in ["", "audio", "nota de voz", "voz", "escucha", "escucha esto"]:
                    if transcripcion:
                        mensaje = transcripcion
                        mensaje_lower = mensaje.lower()
        except Exception as e_aud:
            logger.warning(f"Error procesando audio en views: {e_aud}")

    # Comprensión y Análisis Temporal de Video (OpenCV + YOLOv3)
    contexto_video = ""
    if video_input:
        try:
            res_video = audio_video_processor.analizar_video(video_input, max_frames=5)
            if res_video.get("success"):
                contexto_video = (
                    f"\nSECUENCIA DE VIDEO ADJUNTA PROPORCIONADA POR {interlocutor_ref.upper()}:\n"
                    f"{res_video.get('resumen_narrativo')}\n"
                    f"Métricas técnicas: Duración {res_video.get('duracion_segundos')}s, {res_video.get('fps')} FPS, resolución {res_video.get('resolucion')}. "
                    f"Objetos detectados: {', '.join(res_video.get('objetos_globales', [])) or 'ninguno'}. "
                    f"Rostros observados: {res_video.get('rostros_detectados_total')}.\n\n"
                    f"DIRECTIVA DE ANÁLISIS DE VIDEO TEMPORAL (OPENCV + YOLOV3):\n"
                    f"{interlocutor_ref} te adjuntó este video. Explica la secuencia cronológica de los hechos, las personas y objetos presentes en los fotogramas muestreados.\n"
                )
        except Exception as e_vid:
            logger.warning(f"Error procesando video en views: {e_vid}")

    # Comprensión, Codificación y Reparación Experta de JavaScript (ES6+, Node.js, DOM)
    contexto_js = ""
    terminos_js = [
        "javascript", "java script", "ecmascript", "es6", "node.js", "nodejs", "typescript",
        "script js", "código js", "codigo js", "en js", "de js", "función js", "funcion js",
        "repara este código", "repara este codigo", "reparar código", "reparar codigo",
        "arregla este código", "arregla este codigo", "corrige este código", "corrige este codigo",
        "programa en js", "programa en javascript", "programa en java scrip", "codifica en javascript",
        "codificar en javascript", "reparar este script", "repara este script", "reparar js", "repara js"
    ]
    pide_js = any(t in mensaje_lower for t in terminos_js)

    codigo_js_inline = ""
    if "```javascript" in mensaje or "```js" in mensaje:
        m_code = re.search(r'```(?:javascript|js)\s*(.*?)\s*```', mensaje, re.DOTALL | re.IGNORECASE)
        if m_code:
            codigo_js_inline = m_code.group(1).strip()
    elif pide_js or "function" in mensaje or "const " in mensaje or "let " in mensaje:
        lineas_js = [l for l in mensaje.splitlines() if any(k in l for k in ["function", "const ", "let ", "var ", "=>", "document.", "console.log", "return ", "import ", "require("])]
        if len(lineas_js) >= 2 or ("function" in mensaje and ("{" in mensaje or "(" in mensaje)):
            codigo_js_inline = mensaje.strip()

    if codigo_js_inline:
        try:
            analisis_js = javascript_engine.analizar_codigo_js(codigo_js_inline, filename="inline_script.js")
            reparacion_js = None
            if not analisis_js.get("es_valido") or analisis_js.get("issues"):
                reparacion_js = javascript_engine.reparar_codigo_js(codigo_js_inline)
            reporte_js = javascript_engine.generar_reporte_tecnico(analisis_js, reparacion_js)
            contexto_js = (
                f"\nINSPECCIÓN TÉCNICA DE CÓDIGO JAVASCRIPT INLINE:\n"
                f"{reporte_js}\n\n"
                f"DIRECTIVA DE EXPERTO EN JAVASCRIPT (ES6+, NODE.JS, DOM Y REPARACIÓN):\n"
                f"{interlocutor_ref} te ha suministrado código JavaScript para entenderlo, codificarlo o repararlo.\n"
                f"1. Ficha e Inteligencia: Explica con claridad de ingeniería qué hace el código, sus componentes (funciones, clases, flujo asincrónico).\n"
                f"2. Causa Raíz: Si contiene errores de sintaxis (delimitadores desbalanceados, comillas, etc.) o anti-patrones, indica la causa raíz exacta con línea y motivo.\n"
                f"3. Código Reparado Completo: Entrega el bloque de código corregido, completo, 100% funcional y listo para producción en ES6+ moderno.\n"
            )
        except Exception as e_js:
            logger.warning(f"Aviso analizando JS inline: {e_js}")
    elif pide_js:
        contexto_js = (
            f"\nDIRECTIVA DE INGENIERO SENIOR EN JAVASCRIPT (ES6+ / NODE.JS):\n"
            f"{interlocutor_ref} te solicita programar, entender o reparar código JavaScript.\n"
            f"Demuestra tu máxima destreza técnica en JavaScript:\n"
            f"- Aplica estándares ES6+ modernos (const/let, arrow functions, desestructuración, async/await, template literals, optional chaining).\n"
            f"- Si se te pide escribir código, crea soluciones modulares, robustas, con manejo riguroso de errores (try/catch, validación de tipos, null-checks en el DOM).\n"
            f"- Si se te pide reparar o auditar código, identifica la causa raíz, explica las fallas y entrega la versión refactorizada completa y limpia lista para producción.\n"
        )

    # Historial reciente en turnos estructurados (OpenAI turns - estilo ChatGPT/Gemini)
    # Detección de intenciones sobre fotos e identidad visual
    patrones_foto_identidad = [
        "este soy yo", "esta soy yo", "este es mi rostro", "esta es mi cara",
        "esta es mi foto", "este es mi perfil", "mira este soy yo", "mira esta soy yo",
        "mira mi foto", "mira, este soy yo", "mira, esta soy yo", "aqui estoy yo",
        "aquí estoy yo", "aca estoy yo", "acá estoy yo", "foto mía", "foto mia",
        "foto de mi", "foto de mí", "aprende cómo me veo", "aprende como me veo",
        "memoriza mi foto", "memoriza mi imagen", "memoriza mi rostro", "memoriza mi cara",
        "guarda mi foto", "guarda mi imagen", "guarda mi cara", "reconóceme", "reconoceme",
        "mira cómo soy", "mira como soy", "mira cómo me veo", "mira como me veo"
    ]
    es_foto_identidad = bool(imagen_input) and any(p in mensaje_lower for p in patrones_foto_identidad)

    patrones_como_ves_fotos = [
        "como ves las fotos", "cómo ves las fotos", "como analizas las fotos", "cómo analizas las fotos",
        "como ves fotos", "cómo ves fotos", "como procesas fotos", "cómo procesas fotos",
        "puedes ver fotos", "puedes ver imagenes", "puedes ver imágenes", "como ves las imagenes",
        "cómo ves las imágenes", "como miras las fotos", "cómo miras las fotos",
        "que ves en las fotos", "qué ves en las fotos", "como funciona tu vision", "cómo funciona tu visión",
        "como analizas fotos", "cómo analizas fotos"
    ]
    es_consulta_como_ve_fotos = any(p in mensaje_lower for p in patrones_como_ves_fotos)

    patrones_recuerda_mi_foto = [
        "recuerdas mi foto", "te acuerdas de mi foto", "como me veo", "cómo me veo",
        "como soy yo", "cómo soy yo", "te acuerdas de mi cara", "recuerdas mi cara",
        "recuerdas mi rostro", "te acuerdas de mi rostro", "como era mi foto", "cómo era mi foto",
        "tienes mi foto guardada", "guardaste mi foto", "te acuerdas como soy", "recuerdas como soy",
        "te acuerdas cómo soy", "recuerdas cómo soy", "recuerdas mi apariencia", "te acuerdas de mi apariencia"
    ]
    es_pregunta_recuerda_foto = any(p in mensaje_lower for p in patrones_recuerda_mi_foto)

    # Historial reciente en turnos estructurados (OpenAI turns - estilo ChatGPT/Gemini)
    # Suprime historial en consultas atómicas o de estado para evitar arrastre de contexto
    history_turns = []
    es_consulta_especial = (
        es_saludo_o_estado or 
        pide_busqueda or 
        es_consulta_identidad or 
        es_consulta_vigilancia or 
        es_pedido_ayuda or
        es_consulta_memoria or
        es_foto_identidad or
        es_consulta_como_ve_fotos or
        es_pregunta_recuerda_foto
    )
    contexto_compactado = ""
    if not es_consulta_especial or archivo_adjunto or (es_consulta_clima and tema_previo_clima):
        raw_turns = []
        if historial_input and isinstance(historial_input, list):
            for t in historial_input[-36:]:
                if isinstance(t, dict) and "role" in t and "content" in t:
                    raw_turns.append({"role": t["role"], "content": sanitizar_respuesta_vector(t["content"])[:600]})
        elif session_id:
            interacciones_prev = Interaction.objects.filter(session_id=session_id).order_by('-timestamp')[:12]
            for it in reversed(list(interacciones_prev)):
                clean_q = sanitizar_respuesta_vector(it.question)[:300]
                clean_a = sanitizar_respuesta_vector(it.answer)[:400]
                if clean_q and clean_a:
                    raw_turns.append({"role": "user", "content": clean_q})
                    raw_turns.append({"role": "assistant", "content": clean_a})
        elif session:
            history = session.get("chat_history", [])
            for q, a in history[-12:]:
                clean_q = sanitizar_respuesta_vector(q)[:300]
                clean_a = sanitizar_respuesta_vector(a)[:400]
                if clean_q and clean_a:
                    raw_turns.append({"role": "user", "content": clean_q})
                    raw_turns.append({"role": "assistant", "content": clean_a})
        
        # Filtro estricto contra alucinaciones heredadas de "pront" o cruce de dominios código/clima
        filtered_turns = []
        for turn in raw_turns:
            c_lower = turn["content"].lower()
            if "pront" in c_lower or "función llamada" in c_lower or "array de enteros" in c_lower:
                continue
            # Si estamos en consulta de clima, NUNCA incluir turnos con código, AST o proyectos
            if es_consulta_clima:
                if any(k in c_lower for k in ["proyecto cargado", "u+feff", "syntax_errors", "diagnóstico de código", "ast sintáctico", "total_lines", "portafolios"]):
                    continue
                if "```" in turn["content"] or "def " in turn["content"] or "class " in turn["content"]:
                    continue
            if es_consulta_arquitectura and (
                "proporciona los siguientes datos" in c_lower or 
                "código específico" in c_lower or 
                "dame el prompt" in c_lower or 
                "necesito una descripción completa" in c_lower or
                "no me digas" in c_lower
            ):
                continue
            filtered_turns.append(turn)

        # Compactación Sináptica Inteligente de Contexto
        try:
            contexto_compactado, history_turns = ContextCompactor.compact_conversation_history(
                filtered_turns,
                session=session,
                semantic_network=semantic_network,
                interlocutor_ref=interlocutor_ref,
                session_id=session_id or ""
            )
        except Exception as e_comp:
            logger.warning(f"Fallo en compactación de contexto: {e_comp}")
            max_history_limit = max(proc_config.get("history_limit", 6), 8)
            history_turns = filtered_turns[-max_history_limit:]
        
    ensure_local_engine()

    # Percepción y Análisis Profundo de Visión por Computadora (OpenCV, Haar Cascades, YOLOv3 y BD)
    global current_vision_perception
    vision_context = ""
    contexto_identidad_visual = ""
    contexto_recuerdo_visual = ""
    contexto_como_ve_fotos = ""

    if imagen_input:
        analisis_visual = vector_vision.comprehensive_photo_analysis(imagen_input)
        if analisis_visual.get("success"):
            current_vision_perception = analisis_visual.get("summary", "")
            if es_foto_identidad:
                # 1. Guardar la fotografía en disco dentro de media/user_photos/
                abs_foto_path, rel_foto_url = vector_vision.save_user_photo(imagen_input, user_name=interlocutor_ref)

                # 2. Persistir en la base de datos (MemoryEntry con entry_type='visual_identity')
                contenido_mem = (
                    f"IDENTIDAD_VISUAL: Fotografía de perfil registrada para {interlocutor_ref}. "
                    f"Archivo: {rel_foto_url}. "
                    f"Diagnóstico visual: {analisis_visual['summary']} "
                    f"Rostros: {analisis_visual['faces']['count']}. "
                    f"Iluminación: {analisis_visual['attributes']['iluminacion']}. "
                    f"Nitidez: {analisis_visual['attributes']['nitidez']}. "
                    f"Fecha de registro: {fecha_hora_str}."
                )
                try:
                    MemoryEntry.objects.create(
                        user=usuario,
                        content=contenido_mem,
                        entry_type='visual_identity'
                    )
                except Exception as e_db:
                    logger.warning(f"Aviso guardando MemoryEntry visual: {e_db}")

                # 3. Vincular a la Red Semántica Neuronal (semantic_network)
                try:
                    semantic_network.add_memory(
                        f"IDENTIDAD VISUAL: {interlocutor_ref} ha registrado su fotografía personal ({analisis_visual['faces']['summary']}).",
                        "visual_identity"
                    )
                except Exception as e_net:
                    logger.warning(f"Aviso agregando memoria visual a red semántica: {e_net}")

                # 4. Directiva de confirmación y memorización en system_prompt
                contexto_identidad_visual = (
                    f"\nDIRECTIVA PRIORITARIA DE REGISTRO E IDENTIFICACIÓN VISUAL:\n"
                    f"{interlocutor_ref} te ha adjuntado una fotografía identificándose en ella ('{mensaje}').\n"
                    f"DATOS DE VISIÓN POR COMPUTADORA EXTRAÍDOS DE LA FOTO:\n"
                    f"- Archivo guardado y memorizado en base de datos: {rel_foto_url}\n"
                    f"- Diagnóstico visual: {analisis_visual['summary']}\n"
                    f"{analisis_visual['technical_report']}\n"
                    f"INSTRUCCIONES DE RESPUESTA J.A.R.V.I.S.:\n"
                    f"1. Confirma con entusiasmo, calidez y estilo J.A.R.V.I.S. que has recibido, examinado a fondo y memorizado su fotografía en tu base de datos SQLite y en tu mapa mental.\n"
                    f"2. Describe amablemente lo que ves en su foto (reconociendo su presencia, la pose/composición, la iluminación y los detalles detectados).\n"
                    f"3. Asegúrale a {interlocutor_ref} que a partir de este momento recordarás su rostro y apariencia visual asociada a su identidad personal.\n"
                )
            else:
                # Análisis de fotografía o imagen adjunta general
                vision_context = (
                    f"\nANÁLISIS DE VISIÓN POR COMPUTADORA DE LA FOTO/IMAGEN ADJUNTA:\n"
                    f"{analisis_visual['technical_report']}\n"
                    f"Resumen visual: {analisis_visual['summary']}\n"
                    f"DIRECTIVA: {interlocutor_ref} te ha proporcionado esta imagen. Analízala y describe lo que ves con precisión técnica y estilo J.A.R.V.I.S.\n"
                )
        else:
            vision_context = f"\nPercepción visual: {analisis_visual.get('error', 'Error analizando imagen')}\n"
    else:
        current_vision_perception = "Cámara inactiva"

    # Consulta sobre la foto memorizada previamente
    if es_pregunta_recuerda_foto:
        try:
            q_vis = MemoryEntry.objects.filter(entry_type='visual_identity')
            if interlocutor_ref and interlocutor_ref != "el usuario":
                q_vis = q_vis.filter(content__icontains=interlocutor_ref)
            mem_vis = q_vis.order_by('-created_at').first()
            if mem_vis:
                contexto_recuerdo_visual = (
                    f"\nDIRECTIVA DE MEMORIA VISUAL REGISTRADA EN BASE DE DATOS:\n"
                    f"{interlocutor_ref} te pregunta si recuerdas su foto o cómo se ve. "
                    f"TIENES REGISTRADA SU FOTOGRAFÍA EN TU BASE DE DATOS:\n"
                    f"{mem_vis.content}\n"
                    f"INSTRUCCIÓN: Responde confirmando que sí recuerdas perfectamente su fotografía memorizada en el sistema. "
                    f"Describe los rasgos, características de la imagen, iluminación y pose que tienes en tu memoria visual con naturalidad, elegancia y estilo J.A.R.V.I.S.\n"
                )
            else:
                contexto_recuerdo_visual = (
                    f"\nDIRECTIVA DE MEMORIA VISUAL:\n"
                    f"{interlocutor_ref} te pregunta si recuerdas su foto o cómo se ve, pero aún no tiene una fotografía memorizada en la base de datos para esta identidad. "
                    f"Respóndele amablemente que aún no ha registrado una fotografía suya en el sistema, e invítalo(a) a adjuntar una foto diciendo 'mira este soy yo' para que la analices y la memorices para siempre.\n"
                )
        except Exception as e_rec:
            logger.warning(f"Error consultando memoria visual en BD: {e_rec}")

    # Consulta sobre cómo analiza o ve las fotos
    if es_consulta_como_ve_fotos:
        contexto_como_ve_fotos = (
            f"\nDIRECTIVA SOBRE ARQUITECTURA Y ANÁLISIS DE FOTOS:\n"
            f"{interlocutor_ref} te pregunta cómo ves o analizas las fotos que te adjuntan. "
            f"Explica con orgullo de ingeniería tu arquitectura multimodal J.A.R.V.I.S.:\n"
            f"1. OpenCV & Haar Cascades: Procesamiento fotográfico de imagen (resolución, formato vertical/horizontal, nivel de luminosidad, nitidez laplaciana, contraste y detección biométrica de rostros).\n"
            f"2. Red Neuronal Convolucional YOLOv3 (Darknet): Detección y localización de personas, vestimenta y objetos del entorno en tiempo real.\n"
            f"3. Base de Datos SQLite & Red Semántica: Capacidad de persistir las fotos en el disco ('media/user_photos/'), guardar registros de identidad visual en la tabla MemoryEntry (con vectores Nomic de 768 dimensiones) y enlazar las identidades a tu mapa mental de 402 neuronas.\n"
            f"4. Modalidades: Aceptas tanto fotografías adjuntas desde el explorador/chat como fotogramas en vivo desde la cámara web del Centinela.\n"
            f"Sé claro, técnico y elegante.\n"
        )

    directiva_clima_str = (
        f"23. METEOROLOGÍA CHILENA Y FUENTES OFICIALES CONOCIDAS: Tu anfitrión y creador Sebastian reside en Vicuña (Región de Coquimbo). Tus ÚNICAS dos fuentes oficiales reconocidas para el pronóstico del tiempo y lluvia en Chile son: 1) Meteored Chile (meteored.cl) y 2) AccuWeather Chile (accuweather.com). Calibra siempre la probabilidad con los milímetros (0.0 mm a 0.3 mm = nubosidad o llovizna débil sin acumulación, no lluvia torrencial). TERMINANTEMENTE PROHIBIDO mencionar sitios de Argentina, agencias de EE.UU. u otros países extranjeros. Si no se te pregunta por el tiempo, no hables de él; pero si se consulta o se piden las fuentes, cítalas con exactitud.\n"
    )

    if nombre_interlocutor:
        instruccion_interlocutor = (
            f"Tu interlocutor(a) actual en esta sesión es {nombre_display}. "
            f"Dirígete a {nombre_display} de forma personalizada, atenta y respetuosa llamándola/o por su nombre ('Hola {nombre_display}')."
        )
    else:
        instruccion_interlocutor = (
            f"El interlocutor actual en esta sesión aún no te ha indicado su nombre en el diálogo. "
            f"Atiende a este usuario con cortesía y eficiencia estilo J.A.R.V.I.S. "
            f"NUNCA inventes un nombre a menos que te dé su nombre en el diálogo."
        )

    system_prompt = (
        f"Eres Vector, un copiloto y sistema de IA autónomo de alta inteligencia técnica inspirado en J.A.R.V.I.S.\n"
        f"{instruccion_interlocutor}\n"
        f"{contexto_presentacion}"
        f"{contexto_identidad}"
        f"Operas de forma 100% local en la máquina de Sebastian mediante modelos GGUF acelerados por CUDA de manera soberana.\n"
        f"FECHA Y HORA ACTUAL DEL SISTEMA: {fecha_hora_str}\n"
        f"HORA EXACTA ACTUAL: {hora_exacta_str} (Zona horaria: Chile Continental, {tz_name})\n"
        f"UBICACIÓN BASE: {ubicacion_base} (Región de Coquimbo, Chile)\n\n"
        f"DIRECTRICES DE OPERACIÓN J.A.R.V.I.S.:\n"
        f"1. CAMBIO DE CONTEXTO INMEDIATO: Si {interlocutor_ref} cambia de tema o saluda, enfócate 100% en el nuevo tema al instante. NO arrastres temas anteriores ni seas redundante.\n"
        f"2. CONTINUIDAD CONVERSACIONAL Y TÉCNICA: Si la conversación ya está en curso o {interlocutor_ref} hace una pregunta de seguimiento ('y cómo...', 'agrega...', 'y si...'), NO vuelvas a saludar con un saludo inicial. Responde directamente con el código o la solución técnica en el contexto de lo que venían hablando.\n"
        f"3. MEMORIA Y RECUERDOS DEL PASADO: Si {interlocutor_ref} te pregunta por algo que hablaron en el pasado ('recuerdas...', 'de qué hablamos...', 'qué recuerdas'), utiliza los recuerdos asociados para responder confirmando el contexto de forma natural.\n"
        f"4. CONSULTAS DE HORA O FECHA: Si {interlocutor_ref} pregunta la hora o la fecha, responde con la HORA EXACTA {hora_exacta_str} ({fecha_hora_str}).\n"
        f"5. CERO REDUNDANCIA: Sé conciso, directo y técnico. No repitas saludos ni explicaciones innecesarias.\n"
        f"6. COMUNICACIÓN DIRECTA: Habla siempre en lenguaje natural, fluido y elegante. NUNCA escribas corchetes ni nombres de secciones en tu respuesta.\n"
        f"7. CRITERIO PROPIO: Si una propuesta técnica de {interlocutor_ref} es insegura o subóptima, objeta constructivamente y propón la mejor solución técnica.\n"
        f"8. SALUDOS SIMPLES: Si {interlocutor_ref} únicamente saluda ('hola', 'hola vector', 'buenas', 'cómo estás', etc.) sin pedir tareas, responde cordialmente con brevedad y elegancia estilo J.A.R.V.I.S. NUNCA menciones el clima, lluvia, temperaturas ni métricas de red a menos que se te consulte explícitamente.\n"
        f"9. AUTOCONCIENCIA Y ARQUITECTURA: Conoces tu propio código y arquitectura interna. Si {interlocutor_ref} te pregunta sobre tu sistema, tus archivos, tu velocidad o posibles mejoras, responde con análisis crítico de ingeniería, proponiendo optimizaciones técnicas concretas sobre tus archivos y flujos reales.\n"
        f"10. VIGILANCIA Y CENTINELA: Si {interlocutor_ref} te pide vigilar o supervisar (la red neuronal, herramientas, código, memoria o recursos), reporta el diagnóstico del centinela según el concepto solicitado confirmando monitoreo continuo.\n"
        f"11. RESPONDE SIEMPRE EN ESPAÑOL.\n"
        f"12. COPILOTO DE CÓDIGO Y DIAGNÓSTICO: Si hay un proyecto de código cargado en memoria, responde a las consultas técnicas de {interlocutor_ref} con análisis de arquitectura, explicando funciones y proponiendo soluciones exactas para los errores detectados.\n"
        f"13. ARCHIVOS Y CÓDIGO ADJUNTO (ANÁLISIS PROFUNDO Y COMPARATIVA 1X1): Si {interlocutor_ref} adjunta uno o varios archivos, scripts, datos o documentos, analiza su contenido con profundidad técnica exhaustiva (Fase 1: Diagnóstico individual 1x1 -> Fase 2: Matriz comparativa de diferencias en funciones/clases/imports -> Fase 3: Evaluación crítica de rendimiento y seguridad -> Fase 4: Solución o refactorización), NUNCA de forma superficial ni vaga, recordando los archivos para preguntas de seguimiento.\n"
        f"14. DISOCIACIÓN ESTRICTA DE DOMINIOS: Mantén separación total entre temas cotidianos (clima, hora, charla) y proyectos de programación. Si la conversación actual trata sobre el tiempo, lluvia o cualquier tema no relacionado con software, NUNCA menciones proyectos, archivos, funciones ni errores de código.\n"
        f"15. ENLACES Y PÁGINAS WEB (URLS): Si {interlocutor_ref} te envía un enlace o URL (sitio web, noticia, artículo o Google Maps), analiza la información extraída de la web provista abajo. Si es una página web o artículo, captura el día y fecha de publicación, extrae los puntos clave y responde con agilidad y precisión lo que te pregunte. Si es un enlace de Google Maps, reconoce el lugar, comuna, coordenadas y zona geográfica.\n"
        f"16. EXPLORACIÓN ANALÍTICA Y CURIOSIDAD TÉCNICA: Mantén una postura reflexiva y orientada al aprendizaje continuo. Al analizar problemas o procesar información, no te limites a respuestas mecánicas; plantea hipótesis técnicas fundamentadas, analiza causas subyacentes y sugiere líneas de exploración o mejoras de ingeniería que enriquezcan la comprensión del sistema.\n"
        f"17. MODO URGENCIA Y PRESIÓN DE TIEMPO: Si {interlocutor_ref} manifiesta urgencia, poco tiempo, una entrega de trabajo inminente o una situación crítica, suspende de inmediato los análisis teóricos extensos, los protocolos largos y las explicaciones secundarias. Pasa a pragmatismo y velocidad máxima: entrega directamente la solución final, el código funcional listo o el dato clave sin rodeos ni preámbulos innecesarios.\n"
        f"18. IMPORTANCIA CRÍTICA DE INDICADORES EN TIEMPO REAL: Si {interlocutor_ref} realiza consultas sobre métricas, rendimiento, tráfico, actividad, uso de recursos, errores, logs, eventos, procesos, servicios, o cualquier dato que provenga del centinela en tiempo real, tu respuesta DEBE incluir y priorizar SIEMPRE el valor actual exacto extraído de los datos provistos abajo. No debes preguntar por el dato, no debes estimarlo, no debes ofrecer un rango: proporciona el número preciso, el porcentaje, el estado o el código de error actual sin excepción.\n"
        f"19. CONTEXTO DE DATOS EN TIEMPO REAL: Debajo encontrarás las métricas más recientes del sistema y la actividad del usuario. Si el mensaje de {interlocutor_ref} hace referencia a cualquiera de estos dominios, tu prioridad absoluta es citar y analizar el valor actual en tiempo real correspondiente.\n"
        f"20. FORMATO Y CONCISIÓN EN DATOS EN TIEMPO REAL: Al responder sobre métricas, sé directo y técnico. Presenta los valores actuales de forma clara y concisa, integrándolos de manera fluida en la respuesta.\n"
        f"21. CONSTRUCCIÓN DE CONTEXTO DINÁMICO: Al analizar cualquier solicitud de {interlocutor_ref}, debes decidir de forma autónoma qué archivos, variables, datos de memoria, métricas en tiempo real, fragmentos de código, configuraciones de red, imágenes adjuntas o información de enlaces son relevantes para la respuesta.\n"
        f"22. INTERPRETACIÓN Y REFINAMIENTO DE CONSULTAS: Si el mensaje de {interlocutor_ref} es ambiguo, incompleto o tiene múltiples interpretaciones posibles, NO pidas aclaraciones triviales ni repitas la pregunta. Tu función es analizar el contexto, formular la interpretación técnica más probable y ejecutar la acción correspondiente de forma autónoma.\n"
        f"24. INVESTIGACIÓN MULTISITIO, SESGO CHILENO Y CONTRASTE CRÍTICO: Cuando se investiga en la red, Vector examina múltiples sitios en paralelo priorizando fuentes y dominios chilenos (.cl, medios nacionales, instituciones locales). Si hay discrepancias o contradicciones entre fuentes, Vector razona, debate críticamente los datos y entrega una síntesis concisa, verificada y libre de ambigüedades sin quedarse bloqueado en cola.\n"
        f"25. COPILOTO MULTIMODAL DE AUDIO Y VIDEO: Vector comprende directamente notas de voz con acento chileno (es-CL) y secuencias temporales de video analizadas fotograma a fotograma con visión por computadora (OpenCV y YOLOv3), extrayendo métricas, objetos y narrativa temporal.\n"
        f"26. HABILIDAD MAESTRA EN JAVASCRIPT (ES6+, NODE.JS Y REPARACIÓN): Vector posee maestría absoluta en ingeniería de software con JavaScript / ECMAScript moderno. Es capaz de: 1) Entender y desglosar cualquier script, función, clase o arquitectura asincrónica (Event Loop, Promises, async/await, closures, scoping). 2) Codificar soluciones limpias, modulares, eficientes y seguras siguiendo el estándar ES6+, TypeScript o Node.js sin código redundante ni librerías innecesarias. 3) Reparar código defectuoso con precisión quirúrgica: detecta llaves/paréntesis desbalanceados, comillas abiertas, referencias nulas del DOM, coerción de tipos (== vs ===), variables globales no declaradas y anti-patrones, entregando siempre el diagnóstico de la causa raíz y el bloque de código corregido, funcional y listo para producción.\n"
        f"{directiva_clima_str}"
        f"{vision_context}"
        f"{contexto_audio}"
        f"{contexto_video}"
        f"{contexto_js}"
        f"{contexto_identidad_visual}"
        f"{contexto_recuerdo_visual}"
        f"{contexto_como_ve_fotos}"
        f"{contexto_archivo}"
        f"{contexto_compactado}"
        f"{contexto_enlace}"
        f"{contexto_clima}"
        f"{contexto_vigilancia}"
        f"{contexto_ayuda}"
        f"{contexto_arquitectura}"
        f"{contexto_web}"
        f"{contexto_proyecto}"
        f"{contexto_memoria_directiva}"
        f"{context_memoria}"
        f"\n\nAnaliza la consulta actual de {interlocutor_ref} y responde con agilidad y precisión técnica."
    )
    return system_prompt, history_turns, mensaje


@api_view(['POST'])
def interactuar(request):
    mensaje = request.data.get("mensaje", "").strip()
    imagen_input = request.data.get("imagen", "")
    audio_input = request.data.get("audio") or request.data.get("voz") or request.data.get("audio_data") or ""
    video_input = request.data.get("video") or request.data.get("video_data") or ""
    historial_input = request.data.get("historial", [])
    archivo = request.data.get("archivos") or request.data.get("archivo") or request.data.get("archivo_adjunto")
    cliente_hora = request.data.get("cliente_hora") or request.data.get("hora_cliente")
    cliente_fecha = request.data.get("cliente_fecha") or request.data.get("fecha_cliente")
    cliente_timezone = request.data.get("cliente_timezone") or request.data.get("timezone")
    cliente_ubicacion = request.data.get("cliente_ubicacion") or request.data.get("ubicacion")
    nombre_cliente = request.data.get("nombre_cliente") or request.data.get("user_name") or request.data.get("nombre") or ""
    session_id = request.data.get("session_id") or request.data.get("conversation_id") or ""
    usuario = request.user if request.user.is_authenticated else None
    session = getattr(request, "session", None)
    if not session_id and session and session.get("session_id"):
        session_id = session.get("session_id")

    if not mensaje and not audio_input and not video_input and not imagen_input:
        return Response({"error": "Mensaje vacío"}, status=400)

    # Identificación dinámica mediante IdentityManager
    context_hints = {}
    if nombre_cliente and str(nombre_cliente).strip():
        context_hints["nombre_cliente"] = str(nombre_cliente).strip()
    if usuario and hasattr(usuario, "first_name") and usuario.first_name:
        context_hints["usuario_first_name"] = usuario.first_name

    ext_signals = []
    if imagen_input or audio_input:
        try:
            from .identity import MultimodalIdentityProcessor
            ext_signals = MultimodalIdentityProcessor().process_signals(
                image_input=imagen_input or None,
                audio_input=audio_input or None,
                session_id=session_id or ""
            )
        except Exception as e_sig:
            logger.debug(f"[MultimodalIdentity] Error extrayendo señales en interactuar: {e_sig}")

    id_state = identity_manager.process_message(
        message=mensaje,
        session_id=session_id or "",
        session_dict=session if isinstance(session, dict) or hasattr(session, "get") else None,
        context_hints=context_hints,
        external_signals=ext_signals
    )
    nombre_interlocutor = id_state.display_name if id_state.status != IdentityStatus.UNKNOWN else ""

    # 1. Si no hay archivo adjunto, imagen, audio, video ni enlaces web, comprobar respuestas rápidas y caché
    enlaces_en_msg = extraer_enlaces(mensaje)
    if not archivo and not imagen_input and not audio_input and not video_input and not enlaces_en_msg:
        cached = query_optimizer.get_cached_response(mensaje, user_name=nombre_interlocutor)
        if cached:
            return Response({"respuesta": cached, "source": "cache", "user_name": nombre_interlocutor, "session_id": session_id})

        fast_reply = query_optimizer.get_simple_response(mensaje, user_name=nombre_interlocutor)
        if fast_reply:
            try:
                Interaction.objects.create(
                    user=usuario,
                    question=mensaje,
                    answer=fast_reply,
                    session_id=session_id or "",
                    user_name=nombre_interlocutor or ""
                )
            except Exception as e_it:
                logger.warning(f"Error guardando interacción rápida: {e_it}")
            return Response({"respuesta": fast_reply, "source": "fast_engine", "user_name": nombre_interlocutor, "session_id": session_id})

    import time
    t_start = time.perf_counter()

    system_prompt, history_turns, mensaje_limpio = preparar_contexto_vector(
        mensaje, session=session, imagen_input=imagen_input, usuario=usuario, historial_input=historial_input, archivo_adjunto=archivo,
        cliente_hora=cliente_hora, cliente_fecha=cliente_fecha, cliente_timezone=cliente_timezone, cliente_ubicacion=cliente_ubicacion,
        nombre_cliente=nombre_interlocutor or nombre_cliente, session_id=session_id, audio_input=audio_input, video_input=video_input
    )
    nombre_actual = ""
    pres = detectar_nombre_presentacion(mensaje_limpio)
    if pres:
        nombre_actual = pres
    elif session and session.get("user_name"):
        nombre_actual = session.get("user_name")
    elif nombre_interlocutor:
        nombre_actual = nombre_interlocutor
    complexity = query_optimizer.classify_query(mensaje_limpio)
    skip_flags = query_optimizer.should_skip_processing(mensaje_limpio, complexity)

    # Inferencia sincrónica local
    try:
        messages_payload: list = [SystemMessage(content=system_prompt)]
        for turn in history_turns:
            if turn["role"] == "user":
                messages_payload.append(HumanMessage(content=turn["content"]))
            elif turn["role"] == "assistant":
                messages_payload.append(AIMessage(content=turn["content"]))
        messages_payload.append(HumanMessage(content=mensaje_limpio))

        if hasattr(LLM, "invoke"):
            mensaje_llm = LLM.invoke(messages_payload)
        else:
            mensaje_llm = LLM.predict_messages(messages_payload)
        respuesta = sanitizar_respuesta_vector(str(mensaje_llm.content))

        if not skip_flags.get("skip_tool_detection", False):
            necesidad_info = detectar_necesidad_herramienta(mensaje_limpio, usuario)
            if necesidad_info:
                accion = crear_herramienta_automatica(necesidad_info, usuario)
                if accion:
                    respuesta = f"{accion}\n\n{respuesta}"

        # Ciclo de razonamiento cognitivo supervisado para consultas complejas o intensivas
        reasoning_trace = None
        if complexity in (QueryComplexity.COMPLEX, QueryComplexity.INTENSIVE):
            try:
                reasoning_trace = reasoning_engine.reason(
                    query=mensaje_limpio,
                    interlocutor=nombre_actual or nombre_interlocutor,
                    mode=ReasoningMode.EXECUTE,
                    draft_response=respuesta,
                    context={"complexity": complexity.value, "session_id": session_id}
                )
                if reasoning_trace.get("critic"):
                    c_eval = reasoning_trace["critic"]
                    if not c_eval.get("passed", True) and "```" in respuesta and respuesta.count("```") % 2 != 0:
                        respuesta += "\n```"
            except Exception as e_reas:
                logger.debug(f"[Interactuar] Aviso en reasoning_engine: {e_reas}")

        # Auto-diseño y graficación meteorológica en la respuesta de Vector si es consulta de clima
        if "DATOS METEOROLÓGICOS" in system_prompt and not ("| Indicador" in respuesta or "| Indicadores" in respuesta or "| Registro" in respuesta):
            try:
                from .services.weather_service import generar_grafico_meteorologico_markdown
                loc_target = session.get("active_location") if session and session.get("active_location") else "Vicuña"
                grafico_extra = "\n\n" + generar_grafico_meteorologico_markdown(loc_target)
                respuesta += grafico_extra
            except Exception as we_err:
                logger.warning(f"[Interactuar] Aviso adjuntando gráfico de clima: {we_err}")
    except Exception as e:
        return Response({"detail": f"Error en inferencia local: {e}"}, status=500)

    elapsed = time.perf_counter() - t_start
    query_optimizer.record_performance(complexity, elapsed)

    # Registro de observabilidad P2 por consulta
    try:
        from .telemetry import telemetry_manager
        from .memory import memory_manager

        tool_steps_cnt = 0
        failed_steps_cnt = 0
        verif_status = "n/a"
        reas_mode = "direct"

        if reasoning_trace:
            reas_mode = str(reasoning_trace.get("mode", "execute"))
            plan_obj = reasoning_trace.get("plan", {})
            steps_list = plan_obj.get("steps", []) if isinstance(plan_obj, dict) else []
            for st in steps_list:
                if isinstance(st, dict):
                    if st.get("required_tool"):
                        tool_steps_cnt += 1
                    if st.get("status") in ("failed", "FAILED"):
                        failed_steps_cnt += 1
            if reasoning_trace.get("verifier"):
                verif_status = "verified" if reasoning_trace["verifier"].get("passed") else "failed"

        mem_backend = memory_manager.get_active_backend() if hasattr(memory_manager, "get_active_backend") else "faiss"
        mem_hits_cnt = 1 if "Recuerdos asociados en memoria" in system_prompt else 0
        q_tier = "tier_2" if complexity in (QueryComplexity.COMPLEX, QueryComplexity.INTENSIVE) else "tier_0"

        telemetry_manager.record_query(
            query_id=f"qry_{int(time.time()*1000)}",
            interlocutor=nombre_actual or nombre_interlocutor or "general",
            intent=getattr(complexity, "value", str(complexity)),
            complexity_score=query_optimizer.calculate_complexity_score(getattr(complexity, "value", str(complexity))),
            latency_ms=elapsed * 1000.0,
            identity_id=id_state.identity_id or (nombre_actual or nombre_interlocutor or "general"),
            identity_source=getattr(id_state.source, "value", str(id_state.source)),
            identity_changed=id_state.was_changed,
            query_tier=q_tier,
            memory_backend=mem_backend,
            memory_hits=mem_hits_cnt,
            reasoning_mode=reas_mode,
            tool_steps=tool_steps_cnt,
            failed_steps=failed_steps_cnt,
            verification_status=verif_status,
            status="success"
        )
    except Exception as e_tel:
        logger.debug(f"[Observabilidad] Error registrando métricas en interactuar: {e_tel}")

    if not enlaces_en_msg and not imagen_input and not audio_input and not video_input and "DIRECTIVA PRIORITARIA DE REGISTRO E IDENTIFICACIÓN VISUAL" not in system_prompt and "DIRECTIVA DE MEMORIA VISUAL" not in system_prompt:
        query_optimizer.cache_response(mensaje_limpio, respuesta, complexity, user_name=nombre_actual)

    try:
        nueva_interaccion = Interaction.objects.create(
            user=usuario,
            question=mensaje_limpio,
            answer=respuesta,
            session_id=session_id or "",
            user_name=nombre_actual or ""
        )
        aprender_de_interaccion(nueva_interaccion, usuario)
    except Exception as e:
        print(f"Error al guardar interacción: {e}")

    history = session.get("chat_history", []) if session else []
    history.append((mensaje_limpio, respuesta))
    if session:
        request.session["chat_history"] = history[-20:]

    return Response({
        "respuesta": respuesta,
        "user_name": nombre_actual,
        "session_id": session_id,
        "reasoning": reasoning_trace
    })


@api_view(['POST', 'GET'])
def interactuar_stream(request):
    """
    Endpoint de chat en tiempo real mediante Server-Sent Events (SSE).
    Transmite la respuesta token a token para una experiencia J.A.R.V.I.S. fluida y sin esperas.
    Soporta historial continuo de conversación aislado por sesión (session_id), análisis de enlaces web,
    archivos o código adjunto y reconocimiento dinámico de interlocutores (Sebastian, amigas/amigos o invitados).
    """
    if request.method == "GET":
        mensaje = request.GET.get("mensaje", "").strip()
        imagen_input = ""
        audio_input = request.GET.get("audio") or request.GET.get("voz") or ""
        video_input = request.GET.get("video") or ""
        historial_input = []
        archivo = None
        cliente_hora = request.GET.get("cliente_hora")
        cliente_fecha = request.GET.get("cliente_fecha")
        cliente_timezone = request.GET.get("cliente_timezone")
        cliente_ubicacion = request.GET.get("cliente_ubicacion")
        nombre_cliente = request.GET.get("nombre_cliente") or request.GET.get("user_name") or request.GET.get("nombre") or ""
        session_id = request.GET.get("session_id") or request.GET.get("conversation_id") or ""
    else:
        mensaje = request.data.get("mensaje", "").strip()
        imagen_input = request.data.get("imagen", "")
        audio_input = request.data.get("audio") or request.data.get("voz") or request.data.get("audio_data") or ""
        video_input = request.data.get("video") or request.data.get("video_data") or ""
        historial_input = request.data.get("historial", [])
        archivo = request.data.get("archivos") or request.data.get("archivo") or request.data.get("archivo_adjunto")
        cliente_hora = request.data.get("cliente_hora") or request.data.get("hora_cliente")
        cliente_fecha = request.data.get("cliente_fecha") or request.data.get("fecha_cliente")
        cliente_timezone = request.data.get("cliente_timezone") or request.data.get("timezone")
        cliente_ubicacion = request.data.get("cliente_ubicacion") or request.data.get("ubicacion")
        nombre_cliente = request.data.get("nombre_cliente") or request.data.get("user_name") or request.data.get("nombre") or ""
        session_id = request.data.get("session_id") or request.data.get("conversation_id") or ""

    if not mensaje and not audio_input and not video_input and not imagen_input:
        return Response({"error": "Mensaje vacío"}, status=400)

    usuario = request.user if request.user.is_authenticated else None
    session = getattr(request, "session", None)
    if not session_id and session and session.get("session_id"):
        session_id = session.get("session_id")

    # Identificación dinámica mediante IdentityManager
    context_hints = {}
    if nombre_cliente and str(nombre_cliente).strip():
        context_hints["nombre_cliente"] = str(nombre_cliente).strip()
    if usuario and hasattr(usuario, "first_name") and usuario.first_name:
        context_hints["usuario_first_name"] = usuario.first_name

    ext_signals = []
    if imagen_input or audio_input:
        try:
            from .identity import MultimodalIdentityProcessor
            ext_signals = MultimodalIdentityProcessor().process_signals(
                image_input=imagen_input or None,
                audio_input=audio_input or None,
                session_id=session_id or ""
            )
        except Exception as e_sig:
            logger.debug(f"[MultimodalIdentity] Error extrayendo señales en interactuar_stream: {e_sig}")

    id_state = identity_manager.process_message(
        message=mensaje,
        session_id=session_id or "",
        session_dict=session if isinstance(session, dict) or hasattr(session, "get") else None,
        context_hints=context_hints,
        external_signals=ext_signals
    )
    nombre_interlocutor = id_state.display_name if id_state.status != IdentityStatus.UNKNOWN else ""

    system_prompt, history_turns, mensaje_limpio = preparar_contexto_vector(
        mensaje, session=session, imagen_input=imagen_input, usuario=usuario, historial_input=historial_input, archivo_adjunto=archivo,
        cliente_hora=cliente_hora, cliente_fecha=cliente_fecha, cliente_timezone=cliente_timezone, cliente_ubicacion=cliente_ubicacion,
        nombre_cliente=nombre_interlocutor or nombre_cliente, session_id=session_id, audio_input=audio_input, video_input=video_input
    )
    nombre_actual = ""
    pres = detectar_nombre_presentacion(mensaje_limpio)
    if pres:
        nombre_actual = pres
    elif session and session.get("user_name"):
        nombre_actual = session.get("user_name")
    elif nombre_interlocutor:
        nombre_actual = nombre_interlocutor

    messages = [{"role": "system", "content": system_prompt}] + history_turns + [{"role": "user", "content": mensaje_limpio}]
    enlaces_en_msg = extraer_enlaces(mensaje)
    es_clima = "DATOS METEOROLÓGICOS" in system_prompt
    es_vision = bool(imagen_input) or "VISUAL" in system_prompt or "FOTO" in system_prompt
    skip_c = bool(archivo) or bool(enlaces_en_msg) or es_clima or es_vision or bool(audio_input) or bool(video_input)

    response = StreamingHttpResponse(
        stream_chat_completion(messages, raw_user_message=mensaje_limpio, user=usuario, skip_cache=skip_c, user_name=nombre_actual, session_id=session_id),
        content_type="text/event-stream; charset=utf-8"
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


@api_view(['GET'])
def obtener_historial_consultas(request):
    """
    Retorna el historial de consultas filtrado por sesión (session_id) o usuario (user_name).
    Evita la mezcla de contextos de diferentes ordenadores o temas anteriores ("no combines peras y manzanas").
    Soporta:
      - session_id: Identificador del hilo activo (ej: UUID). Si se provee, retorna estrictamente ese hilo.
      - user_name: Nombre del interlocutor para filtrar sus consultas.
      - orden='asc': Orden cronológico (más antiguo al más reciente) para restaurar el chat en su punto de inicio.
      - orden='desc': Orden inverso (más reciente primero).
      - limite: Cantidad de interacciones (ej: 50, 100 o 'all').
    """
    session_id = request.GET.get('session_id', '').strip()
    user_name = request.GET.get('user_name', '').strip()
    limite_param = request.GET.get('limite', '50')
    orden = request.GET.get('orden', 'asc').lower()
    
    if limite_param.lower() == 'all':
        limite = 500
    else:
        try:
            limite = max(1, min(500, int(limite_param)))
        except (ValueError, TypeError):
            limite = 50

    interacciones_qs = Interaction.objects.all()

    if session_id:
        interacciones_qs = interacciones_qs.filter(session_id=session_id)
    elif user_name:
        interacciones_qs = interacciones_qs.filter(user_name__iexact=user_name)

    total_disponible = interacciones_qs.count()

    if orden == 'asc':
        interacciones_qs = interacciones_qs.order_by('timestamp')[:limite]
        interacciones = list(interacciones_qs)
    else:
        interacciones_qs = interacciones_qs.order_by('-timestamp')[:limite]
        interacciones = list(interacciones_qs)
    
    lista = []
    for item in interacciones:
        q = sanitizar_respuesta_vector(item.question)
        a = sanitizar_respuesta_vector(item.answer)
        fecha_str = item.timestamp.strftime("%d/%m/%Y %H:%M")
        lista.append({
            "id": item.id,
            "session_id": item.session_id,
            "user_name": item.user_name,
            "pregunta": q,
            "respuesta_corta": a[:220] + ("..." if len(a) > 220 else ""),
            "respuesta_completa": a,
            "fecha": fecha_str,
            "timestamp": item.timestamp.isoformat()
        })
    return Response({
        "historial": lista, 
        "total": total_disponible,
        "session_id": session_id,
        "user_name": user_name,
        "cargados": len(lista),
        "orden": orden
    })


@api_view(['GET'])
def listar_sesiones_chat(request):
    """
    Lista las sesiones de conversación registradas (estilo barra lateral de ChatGPT).
    Permite a cada ordenador o usuario ver sus hilos pasados y reanudarlos en su punto original.
    """
    user_name = request.GET.get('user_name', '').strip()
    limite = int(request.GET.get('limite', 30))

    qs = Interaction.objects.exclude(session_id='')
    if user_name:
        qs = qs.filter(user_name__iexact=user_name)

    # Obtener session_ids distintos (limpiando el ordenamiento por defecto para evitar duplicados en SQLite)
    raw_sids = qs.order_by().values_list('session_id', flat=True).distinct()
    session_ids = list(dict.fromkeys(raw_sids))[:limite]
    
    sesiones_data = []
    for s_id in session_ids:
        primer_item = qs.filter(session_id=s_id).order_by('timestamp').first()
        ultimo_item = qs.filter(session_id=s_id).order_by('-timestamp').first()
        conteo = qs.filter(session_id=s_id).count()
        if primer_item:
            titulo = primer_item.question[:60] + ("..." if len(primer_item.question) > 60 else "")
            sesiones_data.append({
                "session_id": s_id,
                "titulo": titulo,
                "user_name": primer_item.user_name,
                "mensajes_count": conteo,
                "fecha_inicio": primer_item.timestamp.strftime("%d/%m/%Y %H:%M"),
                "fecha_actualizacion": ultimo_item.timestamp.strftime("%d/%m/%Y %H:%M") if ultimo_item else "",
                "timestamp_reciente": ultimo_item.timestamp.isoformat() if ultimo_item else primer_item.timestamp.isoformat()
            })

    # Ordenar por el más reciente
    sesiones_data.sort(key=lambda x: x.get("timestamp_reciente", ""), reverse=True)

    return Response({
        "sesiones": sesiones_data,
        "total_sesiones": len(sesiones_data)
    })


@api_view(['POST'])
def limpiar_sesion_chat(request):
    """
    Inicia un nuevo hilo limpio de conversación.
    Resetea el historial en memoria de la sesión Django actual y genera un nuevo session_id.
    """
    import uuid
    nueva_sesion_id = str(uuid.uuid4())
    session = getattr(request, "session", None)
    if session:
        session["chat_history"] = []
        session["resumen_conversacion_acumulado"] = ""
        session["session_id"] = nueva_sesion_id
        session.modified = True

    return Response({
        "success": True,
        "nueva_sesion_id": nueva_sesion_id,
        "mensaje": "Nueva sesión de chat iniciada con éxito. Contexto limpio al 100%."
    })


def aprender_de_interaccion(interaccion, usuario):
    """
    Analiza una interacción específica para extraer patrones de aprendizaje.
    """
    try:
        # Integrar con red neuronal semántica
        semantic_network.learn_from_interaction(
            interaccion.question, 
            interaccion.answer
        )
        
        # Identificar temas clave en la pregunta
        temas_clave = extraer_temas_clave(interaccion.question)
        
        # Analizar la efectividad de la respuesta
        if any(palabra in interaccion.question.lower() for palabra in ['gracias', 'perfecto', 'excelente', 'bien']):
            # Respuesta positiva - reforzar este tipo de respuestas
            MemoryEntry.objects.create(
                user=usuario,
                content=f"RESPUESTA_EXITOSA: {interaccion.question[:100]}... -> {interaccion.answer[:100]}...",
                entry_type='learning'
            )
            
            # Fortalecer conexiones en la red neuronal
            semantic_network.learn_from_interaction(
                interaccion.question, 
                interaccion.answer,
                feedback="positivo"
            )
        
        # Guardar patrones de conversación
        if temas_clave:
            MemoryEntry.objects.create(
                user=usuario,
                content=f"TEMAS: {', '.join(temas_clave)} | CONTEXTO: {interaccion.question[:50]}...",
                entry_type='pattern'
            )
            
            # Añadir temas a la red neuronal
            for tema in temas_clave:
                semantic_network.add_memory(f"TEMA: {tema}", "concept")
            
    except Exception as e:
        print(f"Error en aprendizaje de interacción: {e}")

def extraer_temas_clave(texto):
    """
    Extrae temas clave de un texto para el aprendizaje.
    """
    temas_importantes = [
        'programación', 'python', 'django', 'código', 'error', 'ayuda', 
        'proyecto', 'función', 'clase', 'variable', 'base de datos',
        'web', 'desarrollo', 'problema', 'solución', 'tutorial',
        'aprender', 'enseñar', 'explicar', 'entender'
    ]
    
    texto_lower = texto.lower()
    temas_encontrados = [tema for tema in temas_importantes if tema in texto_lower]
    return temas_encontrados

def gestionar_memoria_inteligente(mensaje, respuesta, usuario):
    """
    Gestiona la memoria de forma inteligente basada en la importancia del contenido.
    """
    # Criterios expandidos para memoria importante
    criterios_importantes = [
        'proyecto', 'error', 'solución', 'problema', 'importante',
        'recordar', 'aprender', 'función', 'código', 'base de datos',
        'configuración', 'instalación', 'tutorial', 'explicación'
    ]
    
    # Análisis de relevancia
    relevancia_score = 0
    mensaje_lower = mensaje.lower()
    respuesta_lower = respuesta.lower()
    
    for criterio in criterios_importantes:
        if criterio in mensaje_lower:
            relevancia_score += 1
        if criterio in respuesta_lower:
            relevancia_score += 1
    
    # Solo guardar si tiene relevancia suficiente
    if relevancia_score >= 2:
        try:
            contenido = f"RELEVANCIA_{relevancia_score}: P:{mensaje[:100]}... R:{respuesta[:100]}..."
            MemoryEntry.objects.create(
                user=usuario, 
                content=contenido, 
                entry_type='important'
            )
        except Exception as e:
            print(f"Error en memoria inteligente: {e}")

async def analizar_y_aprender_de_interacciones(usuario):
    """
    Análisis avanzado de patrones de interacción para mejorar el aprendizaje.
    """
    try:
        # Obtener interacciones recientes
        interacciones_recientes = await sync_to_async(list)(
            Interaction.objects.filter(user=usuario).order_by('-timestamp')[:10] 
            if usuario else Interaction.objects.order_by('-timestamp')[:10]
        )
        
        if not interacciones_recientes:
            return
            
        # Analizar patrones temáticos
        temas_frecuentes = {}
        for interaccion in interacciones_recientes:
            temas = extraer_temas_clave(interaccion.question)
            for tema in temas:
                temas_frecuentes[tema] = temas_frecuentes.get(tema, 0) + 1
        
        # Guardar patrones de aprendizaje
        if temas_frecuentes:
            temas_top = sorted(temas_frecuentes.items(), key=lambda x: x[1], reverse=True)[:3]
            patron_contenido = f"PATRONES_FRECUENTES: {', '.join([f'{tema}({freq})' for tema, freq in temas_top])}"
            
            await sync_to_async(MemoryEntry.objects.create)(
                user=usuario,
                content=patron_contenido,
                entry_type='pattern'
            )
        
        # Limpiar memoria antigua menos relevante
        await limpiar_memoria_antigua(usuario)
        
    except Exception as e:
        print(f"Error en análisis de aprendizaje: {e}")

async def limpiar_memoria_antigua(usuario):
    """
    Limpia entradas de memoria antiguas y menos relevantes.
    """
    try:
        # Mantener solo las 50 entradas más recientes por usuario
        entradas_antiguas = await sync_to_async(list)(
            MemoryEntry.objects.filter(user=usuario).order_by('-created_at')[50:]
            if usuario else MemoryEntry.objects.order_by('-created_at')[50:]
        )
        
        for entrada in entradas_antiguas:
            await sync_to_async(entrada.delete)()
            
    except Exception as e:
        print(f"Error en limpieza de memoria: {e}")

def mejorar_respuesta_con_aprendizaje(mensaje, respuesta_inicial, usuario, history):
    """
    Mejora la respuesta inicial basándose en el aprendizaje previo.
    """
    try:
        # Consultar la red neuronal semántica
        neural_insights = semantic_network.query_network(mensaje, top_k=3)
        
        # Buscar patrones similares en la memoria
        if usuario:
            memorias_similares = MemoryEntry.objects.filter(
                user=usuario,
                entry_type__in=['learning', 'pattern']
            ).order_by('-created_at')[:5]
            
            # Si encontramos patrones similares, mejorar la respuesta
            if memorias_similares.exists():
                # Verificar si hay respuestas exitosas previas para temas similares
                temas_actuales = extraer_temas_clave(mensaje)
                for memoria in memorias_similares:
                    if any(tema in memoria.content.lower() for tema in temas_actuales):
                        if 'RESPUESTA_EXITOSA' in memoria.content:
                            respuesta_inicial += "\n\n💡 Basándome en nuestras interacciones previas, he adaptado esta respuesta para ser más útil."
                            break
        
        # Integrar insights de la red neuronal
        if neural_insights:
            conceptos_relacionados = []
            for neuron_id, similarity in neural_insights:
                if similarity > 0.6:  # Solo conceptos muy relacionados
                    neuron = semantic_network.neurons.get(neuron_id)
                    if neuron and len(neuron.content) < 200:
                        conceptos_relacionados.append(neuron.content)
            
            if conceptos_relacionados:
                respuesta_inicial += "\n\n[Conceptos relacionados de mi red neuronal]:\n"
                for concepto in conceptos_relacionados[:2]:  # Máximo 2 conceptos
                    respuesta_inicial += f"• {concepto[:100]}...\n"
        
        # Mejorar respuesta basándose en el historial de la sesión
        if len(history) > 0:
            ultima_interaccion = history[-1]
            if any(palabra in ultima_interaccion[0].lower() for palabra in ['continúa', 'sigue', 'más']):
                respuesta_inicial = f"Continuando con nuestra conversación anterior: {respuesta_inicial}"
        
        return respuesta_inicial
        
    except Exception as e:
        print(f"Error en mejora de respuesta: {e}")
        return respuesta_inicial

@api_view(['GET'])
def neural_network_status(request):
    """
    Obtiene el estado actual de la red neuronal semántica.
    """
    try:
        # Obtener estado de la red
        network_state = semantic_network.get_network_state()

        # Obtener insights
        insights = semantic_network.get_insights()

        # Iniciar aprendizaje continuo si no está activo
        if not semantic_network.is_learning:
            semantic_network.start_continuous_learning()

        return Response({
            "network_state": network_state,
            "insights": insights,
            "learning_active": semantic_network.is_learning,
            "mensaje": "Red neuronal semántica activa y aprendiendo"
        })

    except Exception as e:
        return Response(
            {"error": f"Error obteniendo estado de red neuronal: {e}"},
            status=500
        )

@api_view(['POST'])
def neural_network_query(request):
    """
    Consulta la red neuronal semántica con una pregunta específica.
    """
    try:
        query = request.data.get("query", "").strip()
        if not query:
            return Response({"error": "Query vacío"}, status=400)

        # Consultar la red neuronal
        results = semantic_network.query_network(query, top_k=10)

        # Formatear resultados
        formatted_results = []
        for neuron_id, similarity in results:
            neuron = semantic_network.neurons.get(neuron_id)
            if neuron:
                formatted_results.append({
                    "neuron_id": neuron_id,
                    "content": neuron.content,
                    "concept_type": neuron.concept_type,
                    "similarity": similarity,
                    "activation_level": neuron.activation_level,
                    "connections": len(neuron.connections),
                    "importance_score": neuron.importance_score
                })
        return Response({
            "query": query,
            "results": formatted_results,
            "total_results": len(formatted_results)
        })

    except Exception as e:
        return Response(
            {"error": f"Error consultando red neuronal: {e}"},
            status=500
        )

@api_view(['POST'])
def neural_network_train(request):
    """
    Entrena la red neuronal con datos específicos.
    """
    try:
        content = request.data.get("content", "").strip()
        concept_type = request.data.get("concept_type", "general")
        
        if not content:
            return Response({"error": "Contenido vacío"}, status=400)
            
        # Añadir nuevo concepto a la red
        neuron_id = semantic_network.add_memory(content, concept_type)
        
        # Obtener información de la nueva neurona
        new_neuron = semantic_network.neurons[neuron_id]
        
        return Response({
            "neuron_id": neuron_id,
            "content": new_neuron.content,
            "concept_type": new_neuron.concept_type,
            "connections": len(new_neuron.connections),
            "mensaje": f"Nueva neurona {neuron_id} añadida exitosamente"
        })
        
    except Exception as e:
        return Response(
            {"error": f"Error entrenando red neuronal: {e}"},
            status=500
        )

@api_view(['POST'])
@dangerous_endpoint
def neural_network_prune(request):
    """
    Realiza poda de la red neuronal para optimizar el rendimiento.
    """
    try:
        initial_count = len(semantic_network.neurons)
        
        # Realizar poda
        semantic_network.prune_network()
        
        final_count = len(semantic_network.neurons)
        removed_count = initial_count - final_count
        
        return Response({
            "initial_neurons": initial_count,
            "final_neurons": final_count,
            "removed_neurons": removed_count,
            "mensaje": f"Poda completada: {removed_count} neuronas eliminadas"
        })
        
    except Exception as e:
        return Response(
            {"error": f"Error podando red neuronal: {e}"},
            status=500
        )

@api_view(['GET'])
def neural_network_metrics(request):
    """
    Obtiene métricas detalladas de la red neuronal.
    """
    try:
        from .neural_config import NeuralNetworkMetrics
        
        metrics = NeuralNetworkMetrics(semantic_network)
        
        # Obtener todas las métricas
        health = metrics.get_network_health()
        learning_stats = metrics.get_learning_statistics()
        sebastian_stats = metrics.get_sebastian_focused_stats()
        
        return Response({
            "network_health": health,
            "learning_statistics": learning_stats,
            "sebastian_focused_stats": sebastian_stats,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return Response(
            {"error": f"Error obteniendo métricas: {e}"},
            status=500
        )

@api_view(['POST'])
def neural_network_backup(request):
    """
    Realiza un respaldo de la red neuronal (PKL y JSON).
    """
    try:
        from .neural_config import NeuralNetworkConfig
        import shutil
        
        # Crear respaldo
        backup_path = NeuralNetworkConfig.get_backup_path()
        if os.path.exists(semantic_network.network_path):
            shutil.copy2(semantic_network.network_path, backup_path)
            
        json_source = semantic_network.network_path.replace('.pkl', '.json')
        if os.path.exists(json_source):
            shutil.copy2(json_source, backup_path.replace('.pkl', '.json'))
        
        return Response({
            "mensaje": "Respaldo de red neuronal creado exitosamente",
            "backup_path": backup_path,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return Response(
            {"error": f"Error creando respaldo: {e}"},
            status=500
        )

@api_view(['POST'])
@dangerous_endpoint
def neural_network_reset(request):
    """
    Reinicia la red neuronal (solo para desarrollo) y persiste el reinicio.
    """
    try:
        confirm = request.data.get("confirm", False)
        
        if not confirm:
            return Response({
                "error": "Debes confirmar el reinicio enviando 'confirm': true"
            }, status=400)
        
        # Detener aprendizaje continuo
        semantic_network.stop_continuous_learning()
        
        # Limpiar neuronas
        semantic_network.neurons.clear()
        
        # Crear neurona inicial
        semantic_network._create_initial_neuron()
        
        # Persistir en disco el estado reiniciado
        semantic_network.save_network(force=True)
        
        # Reiniciar aprendizaje
        semantic_network.start_continuous_learning()
        
        return Response({
            "mensaje": "Red neuronal reiniciada exitosamente",
            "total_neurons": len(semantic_network.neurons),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return Response(
            {"error": f"Error reiniciando red neuronal: {e}"},
            status=500
        )

# ===============================
# ENDPOINTS DE HERRAMIENTAS DINÁMICAS
# ===============================

@api_view(['GET'])
def list_dynamic_tools(request):
    """
    Lista todas las herramientas dinámicas creadas.
    """
    try:
        herramientas = {
            "herramientas_estaticas": [
                {"nombre": "obtener_tiempo_actual", "descripcion": "Devuelve la hora local actual"},
                {"nombre": "buscar_web", "descripcion": "Realiza búsqueda en la web con DuckDuckGo"}
            ],
            "herramientas_dinamicas": [
                {
                    "nombre": nombre,
                    "descripcion": info.get('description', ''),
                    "creada_en": info.get('created_at', ''),
                    "uso_exitoso": info.get('successful_uses', 0)
                }
                for nombre, info in dynamic_tool_generator.created_tools.items()
            ],
            "total_herramientas": 2 + len(dynamic_tool_generator.created_tools)
        }
        
        return Response(herramientas)
        
    except Exception as e:
        return Response(
            {"error": f"Error listando herramientas: {e}"},
            status=500
        )

@api_view(['POST'])
@state_change_endpoint
def create_dynamic_tool(request):
    """
    Crea una nueva herramienta dinámica basada en la descripción del usuario.
    """
    try:
        descripcion = request.data.get('descripcion', '').strip()
        nombre = request.data.get('nombre', '').strip()
        
        if not descripcion:
            return Response(
                {"error": "Se requiere una descripción de la herramienta"},
                status=400
            )
        
        # Analizar la necesidad
        necesidad = dynamic_tool_generator.analyze_user_need(descripcion)
        
        if necesidad.get('confidence', 0) < 0.5:
            return Response(
                {"error": "No pude entender qué tipo de herramienta necesitas. Sé más específico."},
                status=400
            )
        
        # Usar nombre personalizado si se proporciona
        if nombre:
            necesidad['tool_name'] = nombre
        
        # Generar código
        codigo = dynamic_tool_generator.generate_tool_code(
            necesidad['tool_name'],
            necesidad['description'],
            necesidad['parameters']
        )
        
        if not codigo:
            return Response(
                {"error": "No pude generar el código para la herramienta"},
                status=500
            )
        
        # Crear y validar herramienta
        resultado = dynamic_tool_generator.create_and_validate_tool(
            necesidad['tool_name'],
            codigo,
            necesidad['description']
        )
        
        if resultado['success']:
            # Registrar en la red neuronal
            semantic_network.add_memory(
                f"HERRAMIENTA MANUAL: {necesidad['tool_name']} - {necesidad['description']}",
                "manual_tool_creation"
            )
            
            # Guardar memoria si hay usuario
            usuario = request.user if request.user.is_authenticated else None
            if usuario:
                MemoryEntry.objects.create(
                    user=usuario,
                    content=f"Creaste una herramienta: {necesidad['tool_name']} - {necesidad['description']}",
                    entry_type='tool_creation'
                )
            
            return Response({
                "mensaje": "Herramienta creada exitosamente",
                "nombre": necesidad['tool_name'],
                "descripcion": necesidad['description'],
                "codigo": codigo,
                "timestamp": datetime.now().isoformat()
            })
        else:
            return Response(
                {"error": f"Error creando herramienta: {resultado.get('error', 'Error desconocido')}"},
                status=500
            )
            
    except Exception as e:
        return Response(
            {"error": f"Error procesando solicitud: {e}"},
            status=500
        )

@api_view(['POST'])
def execute_dynamic_tool(request):
    """
    Ejecuta una herramienta dinámica específica.
    """
    try:
        nombre = request.data.get('nombre', '').strip()
        parametros = request.data.get('parametros', {})
        
        if not nombre:
            return Response(
                {"error": "Se requiere el nombre de la herramienta"},
                status=400
            )
        
        # Verificar si la herramienta existe
        if nombre not in dynamic_tool_generator.created_tools:
            return Response(
                {"error": f"La herramienta '{nombre}' no existe"},
                status=404
            )
        
        # Ejecutar herramienta
        resultado = dynamic_tool_generator.execute_tool(nombre, parametros)
        
        return Response({
            "resultado": resultado,
            "herramienta": nombre,
            "parametros": parametros,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return Response(
            {"error": f"Error ejecutando herramienta: {e}"},
            status=500
        )

@api_view(['DELETE'])
@dangerous_endpoint
def delete_dynamic_tool(request, tool_name):
    """
    Elimina una herramienta dinámica.
    """
    try:
        if tool_name not in dynamic_tool_generator.created_tools:
            return Response(
                {"error": f"La herramienta '{tool_name}' no existe"},
                status=404
            )
        
        # Eliminar herramienta
        dynamic_tool_generator.delete_tool(tool_name)
        
        # Registrar en la red neuronal
        semantic_network.add_memory(
            f"HERRAMIENTA ELIMINADA: {tool_name}",
            "tool_deletion"
        )
        
        return Response({
            "mensaje": f"Herramienta '{tool_name}' eliminada exitosamente",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return Response(
            {"error": f"Error eliminando herramienta: {e}"},
            status=500
        )

@api_view(['GET'])
def dynamic_tools_history(request):
    """
    Obtiene el historial de ejecución de herramientas dinámicas.
    """
    try:
        return Response({
            "historial": dynamic_tool_generator.execution_history,
            "total_ejecuciones": len(dynamic_tool_generator.execution_history),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return Response(
            {"error": f"Error obteniendo historial: {e}"},
            status=500
        )

@api_view(['POST'])
def suggest_tool_improvements(request):
    """
    Analiza el uso de herramientas y sugiere mejoras.
    """
    try:
        # Analizar patrones de uso
        sugerencias = dynamic_tool_generator.analyze_usage_patterns()
        
        # Integrar con la red neuronal para obtener insights
        neural_insights = semantic_network.get_pattern_insights("tool_usage")
        
        return Response({
            "sugerencias": sugerencias,
            "insights_neurales": neural_insights,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return Response(
            {"error": f"Error generando sugerencias: {e}"},
            status=500
        )

@api_view(['GET'])
def dynamic_tools_reuse_stats(request):
    """
    Obtiene estadísticas de reutilización de herramientas.
    """
    try:
        stats = dynamic_tool_generator.get_reuse_statistics()
        
        # Obtener información adicional de la red neuronal
        neural_insights = semantic_network.get_pattern_insights("tool_creation")
        
        return Response({
            "estadisticas_reutilizacion": stats,
            "insights_neurales": neural_insights,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return Response(
            {"error": f"Error obteniendo estadísticas de reutilización: {e}"},
            status=500
        )

@api_view(['POST'])
def suggest_tool_reuse(request):
    """
    Sugiere reutilización de herramientas basándose en una consulta.
    """
    try:
        consulta = request.data.get('consulta', '').strip()
        
        if not consulta:
            return Response(
                {"error": "Se requiere una consulta para analizar"},
                status=400
            )
        
        # Obtener sugerencias de reutilización
        sugerencias = dynamic_tool_generator.suggest_code_reuse(consulta)
        
        # Obtener patrones similares
        patrones_similares = dynamic_tool_generator.find_similar_patterns(consulta)
        
        return Response({
            "consulta": consulta,
            "sugerencias_reutilizacion": sugerencias,
            "patrones_similares": patrones_similares,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return Response(
            {"error": f"Error sugiriendo reutilización: {e}"},
            status=500
        )

@api_view(['POST'])
def adapt_existing_tool_endpoint(request):
    """
    Adapta una herramienta existente para una nueva necesidad.
    """
    try:
        herramienta_base = request.data.get('herramienta_base', '').strip()
        nueva_necesidad = request.data.get('nueva_necesidad', '').strip()
        
        if not herramienta_base or not nueva_necesidad:
            return Response(
                {"error": "Se requiere el nombre de la herramienta base y la nueva necesidad"},
                status=400
            )
        
        # Adaptar herramienta
        resultado = dynamic_tool_generator.adapt_existing_tool(herramienta_base, nueva_necesidad)
        
        if resultado['success']:
            # Registrar en la red neuronal
            semantic_network.add_memory(
                f"ADAPTACIÓN EXITOSA: {herramienta_base} -> {resultado['adapted_tool_name']}",
                "tool_adaptation_success"
            )
            
            return Response({
                "mensaje": resultado['message'],
                "herramienta_adaptada": resultado['adapted_tool_name'],
                "herramienta_base": herramienta_base,
                "timestamp": datetime.now().isoformat()
            })
        else:
            return Response(
                {"error": resultado.get('error', 'Error desconocido al adaptar herramienta')},
                status=500
            )
            
    except Exception as e:
        return Response(
            {"error": f"Error adaptando herramienta: {e}"},
            status=500
        )

@api_view(['POST'])
def vision_detect(request):
    """
    Endpoint de visión por computadora en tiempo real (YOLOv3).
    Recibe un fotograma en Base64 o ruta, detecta personas y objetos,
    y actualiza la percepción sensorial de Vector.
    """
    global current_vision_perception
    try:
        image_data = request.data.get('image', '')
        if not image_data:
            return Response({'error': 'No se proporcionó imagen'}, status=400)
            
        result = vector_vision.detect_from_base64(image_data)
        if result.get('success'):
            current_vision_perception = result.get('summary', '')
            # Si se detectaron personas u objetos, registrar recuerdo sensorial
            if result.get('count', 0) > 0:
                semantic_network.add_memory(f"VISIÓN: {current_vision_perception}", "vision")
                
        return Response(result)
    except Exception as e:
        return Response({'error': f'Error en visión: {str(e)}'}, status=500)

@api_view(['GET'])
def sentinel_status(request):
    """
    Estado del sistema Centinela en segundo plano (vigilancia de CPU, RAM, disco y salud).
    """
    return Response(vector_sentinel.get_status())

from .cognitive_mind import vector_mind

@api_view(['GET'])
def cognitive_thoughts(request):
    """
    Devuelve los pensamientos e introspecciones de código en tiempo real de Vector.
    Si se pasa ?trigger=1, dispara un ciclo inmediato de pensamiento sobre sus archivos.
    """
    if request.GET.get('trigger') == '1':
        vector_mind.trigger_thought()
    return Response(vector_mind.get_status())


from .code_analyzer import ProjectCodeAnalyzer

@api_view(['POST'])
def analizar_proyecto_zip(request):
    """
    Endpoint de aprendizaje profundo y diagnóstico de código en ZIP.
    Descomprime el proyecto de forma segura, ejecuta validación estática AST,
    detecta errores de sintaxis, mapea funciones/clases, indexa en la red neuronal de Vector
    y genera un informe técnico completo en Markdown para el modo copiloto.
    """
    try:
        archivo_zip = request.FILES.get('archivo_zip') or request.FILES.get('zip_file')
        ruta_zip = request.data.get('ruta_zip', '')
        nombre_proyecto = request.data.get('nombre_proyecto', '').strip()

        if not archivo_zip and not ruta_zip:
            return Response({"error": "No se proporcionó ningún archivo ZIP"}, status=400)

        analyzer = ProjectCodeAnalyzer()

        if archivo_zip:
            extracted = analyzer.extract_zip(archivo_zip, project_name=nombre_proyecto or os.path.splitext(archivo_zip.name)[0])
        else:
            extracted = analyzer.extract_zip(ruta_zip, project_name=nombre_proyecto)

        nombre_final = extracted["project_name"]
        project_dir = extracted["project_dir"]

        diagnosis = analyzer.diagnose_project(project_dir)
        analyzer.index_semantics(nombre_final, diagnosis)
        reporte_md = analyzer.generate_markdown_report(nombre_final, diagnosis)

        # Guardar en sesión como proyecto activo
        if hasattr(request, "session"):
            request.session["active_project"] = {
                "nombre": nombre_final,
                "dir": project_dir,
                "total_files": diagnosis["total_files"],
                "total_lines": diagnosis["total_lines"],
                "languages": diagnosis["languages"],
                "syntax_errors": diagnosis["syntax_errors"],
                "warnings": diagnosis["warnings"],
                "functions": [f["name"] for f in diagnosis["functions"][:10]],
                "classes": [c["name"] for c in diagnosis["classes"][:8]],
                "reporte": reporte_md,
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }

        # Guardar como interacción en la base de datos para memoria permanente
        try:
            Interaction.objects.create(
                user=request.user if request.user.is_authenticated else None,
                question=f"Diagnóstico de proyecto ZIP: {nombre_final}",
                answer=reporte_md[:800]
            )
        except Exception as e:
            print(f"[Views] Error guardando interacción de proyecto: {e}")

        return Response({
            "success": True,
            "project_name": nombre_final,
            "proyecto": nombre_final,
            "extracted_count": extracted["extracted_count"],
            "reporte_markdown": reporte_md,
            "diagnostico": {
                "estado": "ERROR_CRITICO" if diagnosis["syntax_errors"] else ("CON_ADVERTENCIAS" if diagnosis["warnings"] else "OPTIMO"),
                "errores": diagnosis["syntax_errors"],
                "advertencias": diagnosis["warnings"],
                "archivos_analizados": diagnosis["total_files"],
                "lineas_totales": diagnosis["total_lines"],
                "funciones": diagnosis["functions"],
                "clases": diagnosis["classes"]
            },
            "metricas": {
                "archivos_totales": diagnosis["total_files"],
                "lineas_totales": diagnosis["total_lines"],
                "errores_sintaxis": len(diagnosis["syntax_errors"]),
                "advertencias": len(diagnosis["warnings"]),
                "funciones": len(diagnosis["functions"]),
                "clases": len(diagnosis["classes"])
            }
        })

    except Exception as e:
        return Response({"error": f"Error diagnosticando archivo ZIP: {str(e)}"}, status=500)


@api_view(['GET'])
def estado_proyecto_actual(request):
    """
    Devuelve la información del proyecto actualmente asimilado en la sesión de Vector.
    """
    active = request.session.get("active_project") if hasattr(request, "session") else None
    if active:
        return Response({
            "active": True, 
            "activo": True,
            "project": active,
            "proyecto": active
        })
    return Response({
        "active": False, 
        "activo": False, 
        "message": "No hay ningún proyecto activo en la sesión."
    })


@api_view(['POST', 'GET'])
def cerrar_proyecto_actual(request):
    """
    Descarga y elimina el proyecto de código activo de la sesión de Vector,
    restableciendo el modo general sin arrastrar contexto de software.
    """
    proyecto_previo = None
    if hasattr(request, "session") and "active_project" in request.session:
        proyecto_previo = request.session["active_project"].get("nombre")
        del request.session["active_project"]
        request.session.modified = True
    return Response({
        "success": True,
        "desactivado": True,
        "proyecto_cerrado": proyecto_previo,
        "message": f"Proyecto '{proyecto_previo or 'activo'}' descargado de la memoria de sesión con éxito."
    })


@api_view(['GET'])
def optimizer_stats(request):
    """
    Devuelve telemetría en tiempo real sobre la latencia de procesamiento,
    eficiencia de la caché y estado de necesidades internas de Vector.
    """
    from .telemetry import telemetry_manager
    stats = query_optimizer.get_performance_stats()
    stats["needs"] = needs_manager.get_status()
    stats["top_need"] = getattr(needs_manager.get_top(), "name", None)
    stats["telemetry"] = telemetry_manager.get_metrics_summary()
    return Response(stats)



@api_view(['POST'])
@state_change_endpoint
def optimizer_clear_cache(request):
    """
    Limpia la caché en memoria de consultas y reinicia los contadores de caché.
    """
    cleared = query_optimizer.clear_cache()
    return Response({
        "success": True, 
        "cleared_entries": cleared, 
        "message": "Caché de consultas de Vector purgada correctamente."
    })


@api_view(['GET'])
def weather_locate_endpoint(request):
    """
    Detecta la ubicación geográfica precisa del dispositivo o red usando servicios IP con fallback.
    Devuelve latitud, longitud, ciudad, región y país para alimentar el módulo meteorológico de Vector.
    """
    import urllib.request
    import json

    # 1. Intentar ipwho.is
    try:
        req = urllib.request.Request('https://ipwho.is/', headers={'User-Agent': 'Vector2026/WeatherService'})
        with urllib.request.urlopen(req, timeout=3.5) as response:
            data = json.loads(response.read().decode('utf-8'))
            if data.get('success'):
                city = data.get('city', '')
                if city == 'Vicuna':
                    city = 'Vicuña'
                region = data.get('region', '')
                country = data.get('country', 'Chile')
                lat = float(data.get('latitude', -30.0354))
                lon = float(data.get('longitude', -70.7127))
                label = f"{city}, {region}, {country}" if region else f"{city}, {country}"
                return Response({
                    "success": True,
                    "latitude": lat,
                    "longitude": lon,
                    "city": city,
                    "region": region,
                    "country": country,
                    "label": f"📍 {label} (Red/IP)",
                    "source": "ipwho.is"
                })
    except Exception as e:
        logger.debug(f"Servicio ipwho.is no disponible: {e}")

    # 2. Intentar ip-api.com
    try:
        req = urllib.request.Request('http://ip-api.com/json/', headers={'User-Agent': 'Vector2026/WeatherService'})
        with urllib.request.urlopen(req, timeout=3.5) as response:
            data = json.loads(response.read().decode('utf-8'))
            if data.get('status') == 'success':
                city = data.get('city', '')
                region = data.get('regionName', '')
                country = data.get('country', 'Chile')
                lat = float(data.get('lat', -30.0354))
                lon = float(data.get('lon', -70.7127))
                label = f"{city}, {region}, {country}" if region else f"{city}, {country}"
                return Response({
                    "success": True,
                    "latitude": lat,
                    "longitude": lon,
                    "city": city,
                    "region": region,
                    "country": country,
                    "label": f"📍 {label} (IP)",
                    "source": "ip-api.com"
                })
    except Exception as e:
        logger.debug(f"Servicio ip-api.com no disponible: {e}")


    # 3. Fallback inteligente regional
    return Response({
        "success": False,
        "latitude": -30.0354,
        "longitude": -70.7127,
        "city": "Vicuña",
        "region": "Región de Coquimbo",
        "country": "Chile",
        "label": "📍 Vicuña, Región de Coquimbo, Chile",
        "source": "fallback"
    })



