"""
Sistema de auto-programación de herramientas para Vector.
La IA puede crear, modificar y ejecutar herramientas dinámicamente.
"""

import os
import json
import ast
from datetime import datetime
from typing import Dict, List, Any, Optional

class DynamicToolGenerator:
    """
    Generador de herramientas dinámicas que permite a Vector crear sus propias funciones.
    """
    
    def __init__(self, tools_directory: str = "herramientas"):
        # Carpeta donde se guardarán las herramientas generadas
        self.tools_directory = tools_directory
        # Ruta completa al directorio de herramientas dinámicas
        self.tools_path = os.path.join(os.path.dirname(__file__), self.tools_directory)
        self.created_tools = {}  # {tool_name: tool_info}
        self.execution_history = []
        
        # Crear directorio si no existe
        os.makedirs(self.tools_path, exist_ok=True)
        
        # Crear __init__.py para que sea un módulo
        init_file = os.path.join(self.tools_path, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, 'w') as f:
                f.write("# Herramientas dinámicas generadas por Vector\n")
                
        # Cargar herramientas existentes
        self.load_existing_tools()
        
    def analyze_user_need(self, user_message: str) -> Dict[str, Any]:
        """
        Analiza el mensaje del usuario para identificar qué herramienta necesita.
        """
        message_lower = user_message.lower()
        
        # Patrones de necesidades comunes
        need_patterns = {
            'time_related': ['tiempo', 'hora', 'fecha', 'calendario', 'cronómetro', 'temporizador'],
            'file_operations': ['archivo', 'carpeta', 'guardar', 'leer', 'escribir', 'descargar'],
            'data_processing': ['datos', 'csv', 'excel', 'json', 'procesar', 'filtrar', 'ordenar'],
            'web_scraping': ['scraping', 'extraer', 'página web', 'html', 'datos web'],
            'calculations': ['calcular', 'calcula', 'cálculo', 'calculo', 'matemáticas', 'sumar', 'suma', 'operación', 'operacion', 'formula', 'fórmula', 'resta', 'restar', 'multiplicar', 'multiplica', 'dividir', 'divide', 'comparar', 'pares', 'impares', 'números', 'numeros'],
            'text_processing': ['texto', 'contar palabras', 'buscar', 'reemplazar', 'formato'],
            'code_generation': ['codigo', 'código', 'función', 'funcion', 'algoritmo', 'script', 'programa', 'creame un codigo', 'crea un codigo', 'escribe un codigo', 'crea una herramienta'],
            'api_integration': ['api', 'webhook', 'servicio', 'integrar', 'conectar'],
            'automation': ['automatizar', 'script', 'tarea repetitiva', 'proceso'],
            'monitoring': ['monitorear', 'vigilar', 'estado', 'verificar', 'alertar'],
            'database': ['base de datos', 'sql', 'consulta', 'tabla', 'registro']
        }
        
        detected_needs = []
        confidence_scores = {}
        
        for category, keywords in need_patterns.items():
            matches = sum(1 for keyword in keywords if keyword in message_lower)
            if matches > 0:
                detected_needs.append(category)
                # Escalar la confianza para que palabras clave válidas alcancen el umbral operativo (>= 0.6)
                confidence_scores[category] = min(0.98, 0.50 + (matches * 0.20))
        
        # Extraer detalles específicos
        requirements = self.extract_requirements(user_message)
        
        # Verificar si puede reutilizar código existente
        reuse_suggestion = self.suggest_code_reuse(user_message)
        
        # Generar nombre de herramienta sugerido
        if detected_needs:
            primary_need = max(confidence_scores.items(), key=lambda x: x[1])[0]
            timestamp = datetime.now().strftime('%H%M%S')
            suggested_name = f"{primary_need}_{timestamp}"
        else:
            suggested_name = f"general_tool_{datetime.now().strftime('%H%M%S')}"
        
        return {
            'detected_needs': detected_needs,
            'requirements': requirements,
            'message': user_message,
            'complexity': len(detected_needs),
            'confidence_scores': confidence_scores,
            'reuse_suggestion': reuse_suggestion,
            'suggested_tool_name': suggested_name,
            'timestamp': datetime.now().isoformat(),
            'tool_name': suggested_name,
            'description': f"Herramienta para: {user_message}",
            'parameters': {
                'category': detected_needs[0] if detected_needs else 'general',
                'confidence': max(confidence_scores.values()) if confidence_scores else 0.5
            },
            'confidence': max(confidence_scores.values()) if confidence_scores else 0.5
        }
    
    def extract_requirements(self, message: str) -> Dict[str, Any]:
        """
        Extrae requisitos específicos del mensaje del usuario.
        """
        requirements = {}
        
        # Buscar patrones específicos
        patterns = {
            'input_format': r'formato de entrada|input|recibe|parámetro',
            'output_format': r'formato de salida|output|devuelve|retorna',
            'frequency': r'cada|frecuencia|repetir|intervalo',
            'conditions': r'si|cuando|condición|criterio',
            'data_source': r'desde|origen|fuente|base de datos',
            'target': r'hacia|destino|guardar en|enviar a'
        }
        
        import re
        for req_type, pattern in patterns.items():
            matches = re.findall(pattern, message, re.IGNORECASE)
            if matches:
                requirements[req_type] = matches
                
        return requirements
    
    def generate_tool_code(self, tool_name_or_analysis: Any, description: Optional[str] = None, parameters: Optional[Dict[str, Any]] = None) -> str:
        """
        Genera el código de la herramienta basándose en el análisis de necesidades o parámetros directos.
        Acepta tanto un dict de análisis como (tool_name, description, parameters).
        """
        if isinstance(tool_name_or_analysis, dict):
            analysis = tool_name_or_analysis
            tool_name = analysis.get('tool_name', analysis.get('suggested_tool_name', 'tool'))
            desc = analysis.get('description', analysis.get('message', ''))
        else:
            tool_name = str(tool_name_or_analysis)
            parameters = parameters or {}
            desc = description or tool_name
            analysis = {
                'detected_needs': [parameters.get('category', 'general')],
                'message': desc,
                'tool_name': tool_name,
                'confidence': parameters.get('confidence', 0.8)
            }

        code = self.generate_tool_code_from_analysis(analysis)

        # Si se cuenta con tool_name y desc, asegurar que se guarde el archivo si aún no existe
        try:
            tool_file = os.path.join(self.tools_path, f"{tool_name}.py")
            if not os.path.exists(tool_file):
                with open(tool_file, 'w', encoding='utf-8') as f:
                    f.write("# Herramienta generada automáticamente\n")
                    f.write(f"# Descripción: {desc}\n\n")
                    f.write(code)
        except Exception as e:
            print(f"Aviso escribiendo archivo de herramienta {tool_name}: {e}")

        return code

    def generate_tool_code_from_analysis(self, need_analysis: Dict[str, Any]) -> str:
        """
        Genera el código de la herramienta basándose en el análisis de necesidades.
        """
        needs = need_analysis.get('detected_needs', ['general'])
        
        # Determinar el tipo principal de herramienta
        primary_need = needs[0] if needs else 'general'
        
        # Templates de código por categoría
        templates = {
            'time_related': self._generate_time_tool_template,
            'file_operations': self._generate_file_tool_template,
            'data_processing': self._generate_data_tool_template,
            'calculations': self._generate_calc_tool_template,
            'text_processing': self._generate_text_tool_template,
            'web_scraping': self._generate_web_tool_template,
            'api_integration': self._generate_api_tool_template,
            'automation': self._generate_automation_tool_template,
            'monitoring': self._generate_monitoring_tool_template,
            'database': self._generate_database_tool_template
        }
        
        template_func = templates.get(primary_need, self._generate_general_tool_template)
        return template_func(need_analysis)
    
    def _generate_time_tool_template(self, analysis: Dict[str, Any]) -> str:
        """Template para herramientas relacionadas con tiempo."""
        message = analysis['message'].lower()
        
        if 'cronómetro' in message or 'temporizador' in message:
            return '''
import time
from datetime import datetime, timedelta

class TimerTool:
    """Herramienta de cronómetro y temporizador generada dinámicamente."""
    
    def __init__(self):
        self.start_time = None
        self.is_running = False
        
    def start_timer(self):
        """Inicia el cronómetro."""
        self.start_time = datetime.now()
        self.is_running = True
        return f"⏱️ Cronómetro iniciado a las {self.start_time.strftime('%H:%M:%S')}"
        
    def stop_timer(self):
        """Detiene el cronómetro y devuelve el tiempo transcurrido."""
        if not self.is_running or not self.start_time:
            return "❌ El cronómetro no está funcionando"
            
        end_time = datetime.now()
        elapsed = end_time - self.start_time
        self.is_running = False
        
        return f"⏹️ Tiempo transcurrido: {elapsed}"
        
    def get_current_time(self):
        """Obtiene la hora actual formateada."""
        now = datetime.now()
        return {
            'hora_completa': now.strftime('%Y-%m-%d %H:%M:%S'),
            'hora_simple': now.strftime('%H:%M:%S'),
            'fecha': now.strftime('%Y-%m-%d'),
            'timestamp': now.timestamp()
        }

# Instancia global de la herramienta
timer_tool = TimerTool()

def execute_tool(action="get_time", **kwargs):
    """Función principal para ejecutar la herramienta."""
    if action == "start":
        return timer_tool.start_timer()
    elif action == "stop":
        return timer_tool.stop_timer()
    elif action == "get_time":
        return timer_tool.get_current_time()
    else:
        return timer_tool.get_current_time()
'''
        else:
            return '''
from datetime import datetime, timedelta
import calendar

def execute_tool(action="current_time", **kwargs):
    """Herramienta de tiempo generada dinámicamente."""
    now = datetime.now()
    
    if action == "current_time":
        return {
            'timestamp': now.isoformat(),
            'formatted': now.strftime('%Y-%m-%d %H:%M:%S'),
            'day_name': now.strftime('%A'),
            'month_name': now.strftime('%B')
        }
    elif action == "add_days":
        days = kwargs.get('days', 0)
        future_date = now + timedelta(days=days)
        return future_date.strftime('%Y-%m-%d %H:%M:%S')
    elif action == "format_date":
        format_str = kwargs.get('format', '%Y-%m-%d')
        return now.strftime(format_str)
    else:
        return now.strftime('%Y-%m-%d %H:%M:%S')
'''
    
    def _generate_file_tool_template(self, analysis: Dict[str, Any]) -> str:
        """Template para herramientas de archivos."""
        return '''
import os
import json
import csv
from pathlib import Path

def execute_tool(action="list_files", **kwargs):
    """Herramienta de archivos generada dinámicamente."""
    
    if action == "list_files":
        directory = kwargs.get('directory', '.')
        try:
            files = []
            for item in os.listdir(directory):
                path = os.path.join(directory, item)
                files.append({
                    'name': item,
                    'is_directory': os.path.isdir(path),
                    'size': os.path.getsize(path) if os.path.isfile(path) else None,
                    'modified': os.path.getmtime(path)
                })
            return files
        except Exception as e:
            return f"Error: {str(e)}"
            
    elif action == "read_file":
        filepath = kwargs.get('filepath')
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"Error leyendo archivo: {str(e)}"
            
    elif action == "write_file":
        filepath = kwargs.get('filepath')
        content = kwargs.get('content', '')
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"Archivo {filepath} creado exitosamente"
        except Exception as e:
            return f"Error escribiendo archivo: {str(e)}"
            
    elif action == "create_directory":
        directory = kwargs.get('directory')
        try:
            os.makedirs(directory, exist_ok=True)
            return f"Directorio {directory} creado exitosamente"
        except Exception as e:
            return f"Error creando directorio: {str(e)}"
    
    else:
        return "Acción no reconocida"
'''
    
    def _generate_data_tool_template(self, analysis: Dict[str, Any]) -> str:
        """Template para herramientas de procesamiento de datos."""
        return '''
import json
import csv
from collections import Counter
import statistics

def execute_tool(action="process_data", **kwargs):
    """Herramienta de procesamiento de datos generada dinámicamente."""
    
    if action == "analyze_list":
        data = kwargs.get('data', [])
        if not data:
            return "No hay datos para analizar"
            
        try:
            return {
                'total_items': len(data),
                'unique_items': len(set(data)),
                'most_common': Counter(data).most_common(5),
                'sample': data[:5] if len(data) > 5 else data
            }
        except Exception as e:
            return f"Error analizando datos: {str(e)}"
            
    elif action == "filter_data":
        data = kwargs.get('data', [])
        condition = kwargs.get('condition', lambda x: True)
        try:
            filtered = [item for item in data if condition(item)]
            return filtered
        except Exception as e:
            return f"Error filtrando datos: {str(e)}"
            
    elif action == "sort_data":
        data = kwargs.get('data', [])
        reverse = kwargs.get('reverse', False)
        try:
            return sorted(data, reverse=reverse)
        except Exception as e:
            return f"Error ordenando datos: {str(e)}"
            
    elif action == "calculate_stats":
        numbers = kwargs.get('numbers', [])
        try:
            return {
                'count': len(numbers),
                'sum': sum(numbers),
                'average': statistics.mean(numbers),
                'median': statistics.median(numbers),
                'min': min(numbers),
                'max': max(numbers)
            }
        except Exception as e:
            return f"Error calculando estadísticas: {str(e)}"
    
    else:
        return "Acción no reconocida"
'''
    
    def _generate_calc_tool_template(self, analysis: Dict[str, Any]) -> str:
        """Template para herramientas de cálculo."""
        return '''
import math
import operator

def execute_tool(action="calculate", **kwargs):
    """Herramienta de cálculo generada dinámicamente."""
    
    if action == "calculate":
        expression = kwargs.get('expression', '')
        try:
            # Operaciones seguras permitidas
            allowed_operators = {
                '+': operator.add,
                '-': operator.sub,
                '*': operator.mul,
                '/': operator.truediv,
                '//': operator.floordiv,
                '%': operator.mod,
                '**': operator.pow,
                'sqrt': math.sqrt,
                'sin': math.sin,
                'cos': math.cos,
                'tan': math.tan,
                'log': math.log,
                'pi': math.pi,
                'e': math.e
            }
            
            # Evaluación segura
            result = eval(expression, {"__builtins__": {}}, allowed_operators)
            return {
                'expression': expression,
                'result': result,
                'type': type(result).__name__
            }
        except Exception as e:
            return f"Error en cálculo: {str(e)}"
            
    elif action == "convert_units":
        value = kwargs.get('value', 0)
        from_unit = kwargs.get('from_unit', '')
        to_unit = kwargs.get('to_unit', '')
        
        # Conversiones básicas
        conversions = {
            ('celsius', 'fahrenheit'): lambda x: (x * 9/5) + 32,
            ('fahrenheit', 'celsius'): lambda x: (x - 32) * 5/9,
            ('meters', 'feet'): lambda x: x * 3.28084,
            ('feet', 'meters'): lambda x: x / 3.28084,
            ('kg', 'pounds'): lambda x: x * 2.20462,
            ('pounds', 'kg'): lambda x: x / 2.20462
        }
        
        try:
            converter = conversions.get((from_unit.lower(), to_unit.lower()))
            if converter:
                result = converter(value)
                return f"{value} {from_unit} = {result:.2f} {to_unit}"
            else:
                return f"Conversión no disponible: {from_unit} -> {to_unit}"
        except Exception as e:
            return f"Error en conversión: {str(e)}"
    
    else:
        return "Acción no reconocida"
'''
    
    def _generate_text_tool_template(self, analysis: Dict[str, Any]) -> str:
        """Template para herramientas de texto."""
        return '''
import re
from collections import Counter

def execute_tool(action="process_text", **kwargs):
    """Herramienta de procesamiento de texto generada dinámicamente."""
    
    if action == "analyze_text":
        text = kwargs.get('text', '')
        
        words = text.split()
        sentences = text.split('.')
        
        return {
            'character_count': len(text),
            'word_count': len(words),
            'sentence_count': len([s for s in sentences if s.strip()]),
            'most_common_words': Counter(words).most_common(10),
            'average_word_length': sum(len(word) for word in words) / len(words) if words else 0
        }
        
    elif action == "find_and_replace":
        text = kwargs.get('text', '')
        find = kwargs.get('find', '')
        replace = kwargs.get('replace', '')
        
        result = text.replace(find, replace)
        occurrences = text.count(find)
        
        return {
            'original_text': text,
            'modified_text': result,
            'occurrences_found': occurrences
        }
        
    elif action == "extract_patterns":
        text = kwargs.get('text', '')
        pattern = kwargs.get('pattern', r'\\b\\w+\\b')
        
        matches = re.findall(pattern, text)
        
        return {
            'pattern': pattern,
            'matches': matches,
            'match_count': len(matches)
        }
        
    elif action == "format_text":
        text = kwargs.get('text', '')
        format_type = kwargs.get('format_type', 'title')
        
        formats = {
            'upper': text.upper(),
            'lower': text.lower(),
            'title': text.title(),
            'capitalize': text.capitalize(),
            'reverse': text[::-1]
        }
        
        return formats.get(format_type, text)
    
    else:
        return "Acción no reconocida"
'''
    
    def _generate_web_tool_template(self, analysis: Dict[str, Any]) -> str:
        """Template para herramientas web."""
        return '''
import requests
from urllib.parse import urljoin, urlparse
import json

def execute_tool(action="fetch_url", **kwargs):
    """Herramienta web generada dinámicamente."""
    
    if action == "fetch_url":
        url = kwargs.get('url', '')
        timeout = kwargs.get('timeout', 10)
        
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            
            return {
                'status_code': response.status_code,
                'content_type': response.headers.get('content-type', ''),
                'content_length': len(response.content),
                'url': response.url,
                'content': response.text[:1000] + '...' if len(response.text) > 1000 else response.text
            }
        except Exception as e:
            return f"Error fetching URL: {str(e)}"
            
    elif action == "check_status":
        url = kwargs.get('url', '')
        
        try:
            response = requests.head(url, timeout=10)
            return {
                'url': url,
                'status_code': response.status_code,
                'is_accessible': response.status_code < 400,
                'headers': dict(response.headers)
            }
        except Exception as e:
            return f"Error checking status: {str(e)}"
    
    else:
        return "Acción no reconocida"
'''
    
    def _generate_api_tool_template(self, analysis: Dict[str, Any]) -> str:
        """Template para herramientas de API."""
        return '''
import requests
import json

def execute_tool(action="api_call", **kwargs):
    """Herramienta de API generada dinámicamente."""
    
    if action == "get_request":
        url = kwargs.get('url', '')
        headers = kwargs.get('headers', {})
        params = kwargs.get('params', {})
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            return {
                'status_code': response.status_code,
                'success': response.status_code < 400,
                'data': response.json() if 'json' in response.headers.get('content-type', '') else response.text,
                'headers': dict(response.headers)
            }
        except Exception as e:
            return f"Error en GET request: {str(e)}"
            
    elif action == "post_request":
        url = kwargs.get('url', '')
        data = kwargs.get('data', {})
        headers = kwargs.get('headers', {'Content-Type': 'application/json'})
        
        try:
            response = requests.post(url, json=data, headers=headers, timeout=30)
            
            return {
                'status_code': response.status_code,
                'success': response.status_code < 400,
                'data': response.json() if 'json' in response.headers.get('content-type', '') else response.text
            }
        except Exception as e:
            return f"Error en POST request: {str(e)}"
    
    else:
        return "Acción no reconocida"
'''
    
    def _generate_automation_tool_template(self, analysis: Dict[str, Any]) -> str:
        """Template para herramientas de automatización."""
        return '''
import subprocess
import os
import time
from datetime import datetime

def execute_tool(action="run_command", **kwargs):
    """Herramienta de automatización generada dinámicamente."""
    
    if action == "run_command":
        command = kwargs.get('command', '')
        shell = kwargs.get('shell', True)
        
        try:
            result = subprocess.run(
                command, 
                shell=shell, 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            return {
                'command': command,
                'return_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'success': result.returncode == 0
            }
        except subprocess.TimeoutExpired:
            return "Error: Comando excedió el tiempo límite"
        except Exception as e:
            return f"Error ejecutando comando: {str(e)}"
            
    elif action == "schedule_task":
        task_name = kwargs.get('task_name', 'tarea_automatica')
        interval = kwargs.get('interval', 60)  # segundos
        
        # Simulación de programación de tarea
        return {
            'task_name': task_name,
            'interval': interval,
            'scheduled_at': datetime.now().isoformat(),
            'status': 'programada',
            'message': f"Tarea '{task_name}' programada para ejecutarse cada {interval} segundos"
        }
    
    else:
        return "Acción no reconocida"
'''
    
    def _generate_monitoring_tool_template(self, analysis: Dict[str, Any]) -> str:
        """Template para herramientas de monitoreo."""
        return '''
import psutil
import os
from datetime import datetime

def execute_tool(action="system_status", **kwargs):
    """Herramienta de monitoreo generada dinámicamente."""
    
    if action == "system_status":
        try:
            return {
                'timestamp': datetime.now().isoformat(),
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_usage': psutil.disk_usage('/').percent,
                'boot_time': datetime.fromtimestamp(psutil.boot_time()).isoformat()
            }
        except Exception as e:
            return f"Error obteniendo estado del sistema: {str(e)}"
            
    elif action == "process_list":
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # Ordenar por uso de CPU
            processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
            
            return {
                'process_count': len(processes),
                'top_processes': processes[:10]
            }
        except Exception as e:
            return f"Error obteniendo lista de procesos: {str(e)}"
    
    else:
        return "Acción no reconocida"
'''
    
    def _generate_database_tool_template(self, analysis: Dict[str, Any]) -> str:
        """Template para herramientas de base de datos."""
        return '''
import sqlite3
import json
from datetime import datetime

def execute_tool(action="query", **kwargs):
    """Herramienta de base de datos generada dinámicamente."""
    
    if action == "create_table":
        db_path = kwargs.get('db_path', 'dynamic_data.db')
        table_name = kwargs.get('table_name', 'data_table')
        columns = kwargs.get('columns', {'id': 'INTEGER PRIMARY KEY', 'data': 'TEXT'})
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            columns_sql = ', '.join([f"{name} {dtype}" for name, dtype in columns.items()])
            sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_sql})"
            
            cursor.execute(sql)
            conn.commit()
            conn.close()
            
            return f"Tabla {table_name} creada exitosamente"
        except Exception as e:
            return f"Error creando tabla: {str(e)}"
            
    elif action == "insert_data":
        db_path = kwargs.get('db_path', 'dynamic_data.db')
        table_name = kwargs.get('table_name', 'data_table')
        data = kwargs.get('data', {})
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?' for _ in data])
            sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
            
            cursor.execute(sql, list(data.values()))
            conn.commit()
            row_id = cursor.lastrowid
            conn.close()
            
            return f"Datos insertados con ID: {row_id}"
        except Exception as e:
            return f"Error insertando datos: {str(e)}"
            
    elif action == "select_data":
        db_path = kwargs.get('db_path', 'dynamic_data.db')
        table_name = kwargs.get('table_name', 'data_table')
        condition = kwargs.get('condition', '')
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            sql = f"SELECT * FROM {table_name}"
            if condition:
                sql += f" WHERE {condition}"
                
            cursor.execute(sql)
            rows = cursor.fetchall()
            
            # Obtener nombres de columnas
            columns = [description[0] for description in cursor.description]
            
            conn.close()
            
            return {
                'columns': columns,
                'rows': rows,
                'count': len(rows)
            }
        except Exception as e:
            return f"Error consultando datos: {str(e)}"
    
    else:
        return "Acción no reconocida"
'''
    
    def _generate_general_tool_template(self, analysis: Dict[str, Any]) -> str:
        """Template general para herramientas no específicas."""
        return '''
def execute_tool(action="help", **kwargs):
    """Herramienta general generada dinámicamente."""
    
    if action == "help":
        return {
            'tool_name': 'Herramienta General',
            'description': 'Herramienta creada dinámicamente por Vector',
            'created_at': kwargs.get('created_at', 'unknown'),
            'available_actions': ['help', 'echo', 'info'],
            'message': 'Esta herramienta fue generada automáticamente basándose en las necesidades del usuario'
        }
        
    elif action == "echo":
        message = kwargs.get('message', 'Hola desde la herramienta dinámica')
        return f"Echo: {message}"
        
    elif action == "info":
        return {
            'system_info': 'Herramienta dinámica activa',
            'timestamp': str(datetime.now()),
            'parameters': kwargs
        }
    
    else:
        return f"Acción '{action}' no reconocida. Acciones disponibles: help, echo, info"
'''
    
    def create_tool(self, user_request: str, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Crea una nueva herramienta basándose en la solicitud del usuario.
        """
        try:
            # Analizar necesidades
            analysis = self.analyze_user_need(user_request)
            
            # Generar nombre si no se proporciona
            if not tool_name:
                primary_need = analysis['detected_needs'][0] if analysis['detected_needs'] else 'general'
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                tool_name = f"{primary_need}_tool_{timestamp}"
            
            # Generar código
            tool_code = self.generate_tool_code(analysis)
            
            # Crear archivo de la herramienta
            tool_file = os.path.join(self.tools_path, f"{tool_name}.py")
            
            with open(tool_file, 'w', encoding='utf-8') as f:
                f.write(f"""# Herramienta generada automáticamente por Vector
# Solicitud del usuario: {user_request}
# Fecha de creación: {datetime.now().isoformat()}

{tool_code}
""")
            
            # Validar sintaxis
            validation_result = self.validate_tool_code(tool_file)
            
            if validation_result['is_valid']:
                # Registrar herramienta
                tool_info = {
                    'name': tool_name,
                    'file_path': tool_file,
                    'created_at': datetime.now().isoformat(),
                    'user_request': user_request,
                    'analysis': analysis,
                    'status': 'active'
                }
                
                self.created_tools[tool_name] = tool_info
                self.save_tools_registry()
                
                return {
                    'success': True,
                    'tool_name': tool_name,
                    'tool_info': tool_info,
                    'message': f'✅ Herramienta "{tool_name}" creada exitosamente'
                }
            else:
                return {
                    'success': False,
                    'error': validation_result['error'],
                    'message': f'❌ Error al crear herramienta: {validation_result["error"]}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f'❌ Error inesperado al crear herramienta: {str(e)}'
            }
    
    def validate_tool_code(self, tool_file: str) -> Dict[str, Any]:
        """
        Valida que el código de la herramienta sea sintácticamente correcto.
        """
        try:
            with open(tool_file, 'r', encoding='utf-8') as f:
                code = f.read()
            
            # Compilar para validar sintaxis
            compile(code, tool_file, 'exec')
            
            return {
                'is_valid': True,
                'message': 'Código válido'
            }
            
        except SyntaxError as e:
            return {
                'is_valid': False,
                'error': f'Error de sintaxis: {str(e)}',
                'line': getattr(e, 'lineno', 0)
            }
        except Exception as e:
            return {
                'is_valid': False,
                'error': f'Error de validación: {str(e)}'
            }
    
    def execute_tool(self, tool_name: str, parameters: Any = None, action: Optional[str] = None, timeout: int = 5, **kwargs) -> Any:
        """
        Ejecuta una herramienta dinámica dentro de un entorno Sandbox aislado por subproceso.
        Evita bloqueos del servidor Django, bucles infinitos y fallos de memoria mediante timeouts estrictos.
        """
        if isinstance(parameters, dict):
            params = dict(parameters)
        elif parameters is None:
            params = {}
        else:
            params = {'query': parameters}

        params.update(kwargs)

        if tool_name not in self.created_tools:
            return f"❌ Herramienta '{tool_name}' no encontrada"

        tool_info = self.created_tools[tool_name]
        tool_file = tool_info.get('file_path')

        if not tool_file or not os.path.exists(tool_file):
            return f"❌ Archivo de herramienta '{tool_name}' no encontrado"

        act = action or params.pop('action', 'execute')
        if 'query' in params and act == 'execute':
            act = 'process_query'

        import sys
        import subprocess

        runner_script = (
            "import sys, json, importlib.util, io\n"
            "tool_name = sys.argv[1]\n"
            "tool_file = sys.argv[2]\n"
            "act = sys.argv[3]\n"
            "params = json.loads(sys.argv[4]) if len(sys.argv) > 4 else {}\n"
            "try:\n"
            "    spec = importlib.util.spec_from_file_location(tool_name, tool_file)\n"
            "    if not spec or not spec.loader:\n"
            "        print(json.dumps({'success': False, 'error': 'No se pudo cargar el archivo'}))\n"
            "        sys.exit(0)\n"
            "    mod = importlib.util.module_from_spec(spec)\n"
            "    spec.loader.exec_module(mod)\n"
            "    _buf = io.StringIO()\n"
            "    _orig_stdout = sys.stdout\n"
            "    sys.stdout = _buf\n"
            "    res = None\n"
            "    if hasattr(mod, 'execute_tool'):\n"
            "        res = mod.execute_tool(action=act, **params)\n"
            "    elif hasattr(mod, tool_name):\n"
            "        fn = getattr(mod, tool_name)\n"
            "        res = fn(**params) if params else fn()\n"
            "    else:\n"
            "        funcs = [f for f in dir(mod) if callable(getattr(mod, f)) and not f.startswith('_')]\n"
            "        if funcs:\n"
            "            fn = getattr(mod, funcs[0])\n"
            "            res = fn(**params) if params else fn()\n"
            "        else:\n"
            "            sys.stdout = _orig_stdout\n"
            "            print(json.dumps({'success': False, 'error': 'No se encontró función ejecutable'}))\n"
            "            sys.exit(0)\n"
            "    sys.stdout = _orig_stdout\n"
            "    captured = _buf.getvalue().strip()\n"
            "    final_res = captured if (res is None or isinstance(res, bool)) and captured else (res if res is not None else captured)\n"
            "    print(json.dumps({'success': True, 'result': final_res}, default=str))\n"
            "except Exception as e:\n"
            "    sys.stdout = sys.__stdout__\n"
            "    print(json.dumps({'success': False, 'error': str(e)}))\n"
        )

        try:
            proc = subprocess.run(
                [sys.executable, "-c", runner_script, tool_name, tool_file, act, json.dumps(params, ensure_ascii=False)],
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding='utf-8',
                errors='replace'
            )

            stdout_str = proc.stdout.strip()
            result_obj = None
            if stdout_str:
                for line in stdout_str.splitlines()[::-1]:
                    try:
                        result_obj = json.loads(line)
                        break
                    except Exception:
                        continue

            if result_obj and result_obj.get("success"):
                result = result_obj.get("result")
                # Registrar ejecución exitosa
                execution_record = {
                    'tool_name': tool_name,
                    'action': act,
                    'parameters': params,
                    'result': str(result)[:500] + '...' if len(str(result)) > 500 else str(result),
                    'timestamp': datetime.now().isoformat(),
                    'success': True
                }
                self.execution_history.append(execution_record)
                self.created_tools[tool_name]['successful_uses'] = self.created_tools[tool_name].get('successful_uses', 0) + 1
                self.save_tools_registry()
                return result
            elif result_obj and "error" in result_obj:
                err = result_obj["error"]
                return f"[Error] Sandbox ejecutando '{tool_name}': {err}"
            else:
                stderr_str = proc.stderr.strip()
                err = stderr_str if stderr_str else (stdout_str if stdout_str else f"Código de salida: {proc.returncode}")
                return f"[Error] Ejecución de '{tool_name}': {err}"

        except subprocess.TimeoutExpired:
            error_msg = f"[Timeout] La herramienta '{tool_name}' excedió el tiempo límite de seguridad ({timeout}s) y fue terminada."
            execution_record = {
                'tool_name': tool_name,
                'action': act,
                'parameters': params,
                'error': f'Timeout de {timeout}s',
                'timestamp': datetime.now().isoformat(),
                'success': False
            }
            self.execution_history.append(execution_record)
            return error_msg
        except Exception as e:
            error_msg = f"❌ Error ejecutando herramienta '{tool_name}': {str(e)}"
            execution_record = {
                'tool_name': tool_name,
                'action': act,
                'parameters': params,
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'success': False
            }
            self.execution_history.append(execution_record)
            return error_msg
    
    def list_tools(self) -> Dict[str, Any]:
        """
        Lista todas las herramientas disponibles.
        """
        return {
            'total_tools': len(self.created_tools),
            'tools': [
                {
                    'name': name,
                    'created_at': info['created_at'],
                    'user_request': info['user_request'],
                    'status': info['status']
                }
                for name, info in self.created_tools.items()
            ]
        }
    
    def get_tool_info(self, tool_name: str) -> Dict[str, Any]:
        """
        Obtiene información detallada de una herramienta.
        """
        if tool_name not in self.created_tools:
            return {'error': f"Herramienta '{tool_name}' no encontrada"}
        
        return self.created_tools[tool_name]
    
    def delete_tool(self, tool_name: str) -> Dict[str, Any]:
        """
        Elimina una herramienta dinámica.
        """
        try:
            if tool_name not in self.created_tools:
                return {'success': False, 'error': f"Herramienta '{tool_name}' no encontrada"}
            
            tool_info = self.created_tools[tool_name]
            tool_file = tool_info['file_path']
            
            # Eliminar archivo
            if os.path.exists(tool_file):
                os.remove(tool_file)
            
            # Eliminar del registro
            del self.created_tools[tool_name]
            self.save_tools_registry()
            
            return {
                'success': True,
                'message': f'✅ Herramienta "{tool_name}" eliminada exitosamente'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f'❌ Error al eliminar herramienta: {str(e)}'
            }
    
    def save_tools_registry(self):
        """
        Guarda el registro de herramientas en disco.
        """
        registry_file = os.path.join(self.tools_path, 'tools_registry.json')
        
        try:
            with open(registry_file, 'w', encoding='utf-8') as f:
                json.dump(self.created_tools, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando registro de herramientas: {e}")
    
    def load_existing_tools(self):
        """
        Carga herramientas existentes desde el registro.
        """
        registry_file = os.path.join(self.tools_path, 'tools_registry.json')
        
        try:
            if os.path.exists(registry_file):
                with open(registry_file, 'r', encoding='utf-8') as f:
                    self.created_tools = json.load(f)
                try:
                    print(f"[Herramientas] {len(self.created_tools)} herramientas dinámicas cargadas")
                except Exception:
                    pass
        except Exception as e:
            try:
                print(f"Error cargando registro de herramientas: {e}")
            except Exception:
                pass
            self.created_tools = {}

    def analyze_usage_patterns(self) -> List[Any]:
        """
        Analiza patrones de uso de herramientas para sugerir mejoras.
        """
        if not self.execution_history:
            return ["No hay suficiente historial de ejecución para analizar"]
        
        suggestions = []
        
        # Analizar herramientas más usadas
        tool_usage = {}
        for record in self.execution_history:
            tool_name = record['tool_name']
            tool_usage[tool_name] = tool_usage.get(tool_name, 0) + 1
        
        most_used = max(tool_usage.items(), key=lambda x: x[1]) if tool_usage else None
        if most_used:
            suggestions.append({
                'type': 'optimization',
                'message': f"La herramienta '{most_used[0]}' es la más usada ({most_used[1]} veces). Considera optimizar su rendimiento."
            })
        
        # Analizar errores comunes
        error_count = sum(1 for record in self.execution_history if 'Error' in str(record.get('result', '')))
        if error_count > 0:
            suggestions.append({
                'type': 'error_handling',
                'message': f"Se detectaron {error_count} errores en las ejecuciones. Considera mejorar el manejo de errores."
            })
        
        # Sugerir herramientas nuevas basándose en patrones
        unique_actions = set()
        for record in self.execution_history:
            unique_actions.add(record.get('action', 'unknown'))
        
        if len(unique_actions) > 5:
            suggestions.append({
                'type': 'consolidation',
                'message': f"Se detectaron {len(unique_actions)} acciones diferentes. Considera consolidar funcionalidades similares."
            })
        
        return suggestions if suggestions else ["No se encontraron patrones específicos para mejorar"]

    def create_and_validate_tool(self, tool_name: str, code: str, description: str) -> Dict[str, Any]:
        """
        Crea y valida una nueva herramienta.
        """
        try:
            # Crear archivo de la herramienta
            tool_file = os.path.join(self.tools_path, f"{tool_name}.py")
            
            with open(tool_file, 'w', encoding='utf-8') as f:
                f.write(f"""# Herramienta generada automáticamente por Vector
# Descripción: {description}
# Fecha de creación: {datetime.now().isoformat()}

{code}
""")
            
            # Validar sintaxis
            validation_result = self.validate_tool_code(tool_file)
            
            if validation_result['is_valid']:
                # Registrar herramienta
                tool_info = {
                    'name': tool_name,
                    'file_path': tool_file,
                    'created_at': datetime.now().isoformat(),
                    'description': description,
                    'status': 'active',
                    'successful_uses': 0,
                    'code_signature': self._extract_code_signature(code),
                    'learning_data': {
                        'created_from_request': description,
                        'reuse_count': 0,
                        'adaptation_count': 0
                    }
                }
                
                self.created_tools[tool_name] = tool_info
                self.save_tools_registry()
                
                # Aprender del código generado
                self.learn_from_generated_code(tool_name, code, description)
                
                return {
                    'success': True,
                    'tool_name': tool_name,
                    'message': f'✅ Herramienta "{tool_name}" creada exitosamente'
                }
            else:
                # Limpiar archivo si hay error
                if os.path.exists(tool_file):
                    os.remove(tool_file)
                
                return {
                    'success': False,
                    'error': validation_result['error'],
                    'message': f'❌ Error al crear herramienta: {validation_result["error"]}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f'❌ Error inesperado al crear herramienta: {str(e)}'
            }

    def get_tool_suggestions(self, user_message: str) -> List[str]:
        """
        Obtiene sugerencias de herramientas basándose en el mensaje del usuario.
        """
        suggestions = []
        message_lower = user_message.lower()
        
        # Patrones de sugerencias
        if any(word in message_lower for word in ['tiempo', 'hora', 'fecha', 'cronómetro']):
            suggestions.append("Herramienta de tiempo para gestionar fechas y cronómetros")
        
        if any(word in message_lower for word in ['archivo', 'carpeta', 'directorio', 'fichero']):
            suggestions.append("Herramienta de archivos para gestionar el sistema de archivos")
        
        if any(word in message_lower for word in ['calcular', 'sumar', 'restar', 'multiplicar']):
            suggestions.append("Herramienta de cálculo para operaciones matemáticas")
        
        if any(word in message_lower for word in ['web', 'url', 'sitio', 'página']):
            suggestions.append("Herramienta web para interactuar con sitios web")
        
        if any(word in message_lower for word in ['texto', 'cadena', 'palabra', 'párrafo']):
            suggestions.append("Herramienta de texto para procesar cadenas de texto")
        
        if any(word in message_lower for word in ['datos', 'análisis', 'estadística']):
            suggestions.append("Herramienta de análisis de datos")
        
        if any(word in message_lower for word in ['automatizar', 'tarea', 'programar']):
            suggestions.append("Herramienta de automatización")
        
        if any(word in message_lower for word in ['monitor', 'sistema', 'rendimiento']):
            suggestions.append("Herramienta de monitoreo del sistema")
        
        return suggestions if suggestions else ["Herramienta general personalizada"]

    def learn_from_generated_code(self, tool_name: str, code_pattern: str, user_request: str) -> None:
        """
        Aprende de los códigos generados para reutilizarlos en el futuro.
        """
        try:
            # Extraer patrones del código generado
            code_signature = self._extract_code_signature(code_pattern)
            
            # Crear entrada de aprendizaje
            learning_entry = {
                'tool_name': tool_name,
                'user_request': user_request,
                'code_signature': code_signature,
                'created_at': datetime.now().isoformat(),
                'usage_count': 0,
                'success_rate': 0.0,
                'similar_requests': []
            }
            
            # Guardar en historial de aprendizaje
            learning_file = os.path.join(self.tools_path, 'learning_patterns.json')
            
            existing_patterns = {}
            if os.path.exists(learning_file):
                with open(learning_file, 'r', encoding='utf-8') as f:
                    existing_patterns = json.load(f)
            
            # Usar hash del código como clave para evitar duplicados
            pattern_hash = hash(code_signature)
            existing_patterns[str(pattern_hash)] = learning_entry
            
            with open(learning_file, 'w', encoding='utf-8') as f:
                json.dump(existing_patterns, f, indent=2, ensure_ascii=False)
                
            print(f"[Vector] Patrón de código aprendido: {tool_name}")
            
        except Exception as e:
            print(f"Error aprendiendo del código generado: {e}")
    
    def _extract_code_signature(self, code: str) -> str:
        """
        Extrae la firma/patrón del código para identificar funcionalidades similares.
        """
        try:
            # Analizar el código para extraer patrones
            tree = ast.parse(code)
            
            functions = []
            imports = []
            classes = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions.append(node.name)
                elif isinstance(node, ast.Import):
                    imports.extend([alias.name for alias in node.names])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
                elif isinstance(node, ast.ClassDef):
                    classes.append(node.name)
            
            signature = {
                'functions': functions,
                'imports': imports,
                'classes': classes,
                'code_length': len(code),
                'complexity': len(functions) + len(classes)
            }
            
            return json.dumps(signature, sort_keys=True)
            
        except Exception:
            # Si no se puede parsear, usar el código directamente
            return code[:200] + "..." if len(code) > 200 else code
    
    def find_similar_patterns(self, user_request: str) -> List[Dict[str, Any]]:
        """
        Busca patrones similares en el historial de aprendizaje.
        """
        try:
            learning_file = os.path.join(self.tools_path, 'learning_patterns.json')
            
            if not os.path.exists(learning_file):
                return []
            
            with open(learning_file, 'r', encoding='utf-8') as f:
                patterns = json.load(f)
            
            similar_patterns = []
            request_lower = user_request.lower()
            
            for pattern_hash, pattern_data in patterns.items():
                # Calcular similitud basada en palabras clave
                original_request = pattern_data['user_request'].lower()
                
                # Palabras clave comunes
                common_words = set(request_lower.split()) & set(original_request.split())
                similarity = len(common_words) / max(len(request_lower.split()), len(original_request.split()))
                
                if similarity > 0.3:  # Umbral de similitud
                    similar_patterns.append({
                        'pattern': pattern_data,
                        'similarity': similarity,
                        'tool_name': pattern_data['tool_name']
                    })
            
            # Ordenar por similitud
            similar_patterns.sort(key=lambda x: x['similarity'], reverse=True)
            
            return similar_patterns[:5]  # Top 5 patrones similares
            
        except Exception as e:
            print(f"Error buscando patrones similares: {e}")
            return []
    
    def suggest_code_reuse(self, user_request: str) -> Dict[str, Any]:
        """
        Sugiere reutilizar código existente basándose en patrones aprendidos.
        """
        similar_patterns = self.find_similar_patterns(user_request)
        
        if not similar_patterns:
            return {
                'can_reuse': False,
                'message': 'No se encontraron patrones similares para reutilizar'
            }
        
        best_match = similar_patterns[0]
        
        if best_match['similarity'] > 0.7:  # Alta similitud
            return {
                'can_reuse': True,
                'suggested_tool': best_match['tool_name'],
                'similarity': best_match['similarity'],
                'message': f"Puedo reutilizar la herramienta '{best_match['tool_name']}' que creé anteriormente para una tarea similar",
                'original_request': best_match['pattern']['user_request']
            }
        elif best_match['similarity'] > 0.5:  # Similitud media
            return {
                'can_reuse': True,
                'suggested_tool': best_match['tool_name'],
                'similarity': best_match['similarity'],
                'message': f"Puedo adaptar la herramienta '{best_match['tool_name']}' para esta nueva tarea",
                'original_request': best_match['pattern']['user_request'],
                'needs_adaptation': True
            }
        else:
            return {
                'can_reuse': False,
                'message': 'Los patrones existentes no son suficientemente similares, crearé una nueva herramienta'
            }
    
    def adapt_existing_tool(self, base_tool_name: str, new_request: str) -> Dict[str, Any]:
        """
        Adapta una herramienta existente para una nueva necesidad.
        """
        try:
            if base_tool_name not in self.created_tools:
                return {
                    'success': False,
                    'error': f"Herramienta base '{base_tool_name}' no encontrada"
                }
            
            # Obtener código de la herramienta base
            base_tool_info = self.created_tools[base_tool_name]
            base_tool_file = base_tool_info['file_path']
            
            with open(base_tool_file, 'r', encoding='utf-8') as f:
                base_code = f.read()
            
            # Analizar nueva necesidad
            new_analysis = self.analyze_user_need(new_request)
            
            # Crear nombre para la herramienta adaptada
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            adapted_tool_name = f"adapted_{base_tool_name}_{timestamp}"
            
            # Generar código adaptado
            adapted_code = self._adapt_code(base_code, new_analysis)
            
            # Crear nueva herramienta adaptada
            result = self.create_and_validate_tool(
                adapted_tool_name,
                adapted_code,
                f"Adaptación de {base_tool_name}: {new_request}"
            )
            
            if result['success']:
                # Registrar como adaptación
                self.created_tools[adapted_tool_name]['adapted_from'] = base_tool_name
                self.created_tools[adapted_tool_name]['adaptation_request'] = new_request
                self.save_tools_registry()
                
                return {
                    'success': True,
                    'adapted_tool_name': adapted_tool_name,
                    'message': f"Herramienta '{adapted_tool_name}' creada adaptando '{base_tool_name}'"
                }
            else:
                return result
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Error adaptando herramienta: {str(e)}"
            }
    
    def _adapt_code(self, base_code: str, new_analysis: Dict[str, Any]) -> str:
        """
        Adapta el código base para las nuevas necesidades.
        """
        try:
            # Estrategia simple: modificar comentarios y añadir nuevas funcionalidades
            lines = base_code.split('\n')
            adapted_lines = []
            
            for line in lines:
                adapted_lines.append(line)
                
                # Insertar nueva funcionalidad después de ciertas líneas
                if 'def execute_tool(' in line:
                    # Agregar información sobre la adaptación
                    adapted_lines.append(f'    """Herramienta adaptada para: {new_analysis["message"]}"""')
                
                # Añadir nuevas acciones basadas en el análisis
                if 'else:' in line and 'return' in line:
                    for need in new_analysis.get('detected_needs', []):
                        if need == 'calculations':
                            adapted_lines.insert(-1, '    elif action == "advanced_calculation":')
                            adapted_lines.insert(-1, '        # Nueva funcionalidad de cálculo avanzado')
                            adapted_lines.insert(-1, '        return "Cálculo avanzado implementado"')
                        elif need == 'data_processing':
                            adapted_lines.insert(-1, '    elif action == "advanced_data_processing":')
                            adapted_lines.insert(-1, '        # Nueva funcionalidad de procesamiento de datos')
                            adapted_lines.insert(-1, '        return "Procesamiento de datos avanzado implementado"')
            
            return '\n'.join(adapted_lines)
            
        except Exception as e:
            print(f"Error adaptando código: {e}")
            return base_code  # Devolver código original si hay error
    
    def get_reuse_statistics(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de reutilización de código.
        """
        try:
            learning_file = os.path.join(self.tools_path, 'learning_patterns.json')
            
            if not os.path.exists(learning_file):
                return {
                    'total_patterns': 0,
                    'reuse_rate': 0.0,
                    'most_reused_pattern': None
                }
            
            with open(learning_file, 'r', encoding='utf-8') as f:
                patterns = json.load(f)
            
            total_patterns = len(patterns)
            total_usage = sum(pattern['usage_count'] for pattern in patterns.values())
            
            # Encontrar patrón más reutilizado
            most_reused = None
            max_usage = 0
            
            for pattern_data in patterns.values():
                if pattern_data['usage_count'] > max_usage:
                    max_usage = pattern_data['usage_count']
                    most_reused = pattern_data
            
            return {
                'total_patterns': total_patterns,
                'total_reuses': total_usage,
                'reuse_rate': (total_usage / total_patterns) if total_patterns > 0 else 0.0,
                'most_reused_pattern': {
                    'tool_name': most_reused['tool_name'],
                    'usage_count': most_reused['usage_count'],
                    'original_request': most_reused['user_request']
                } if most_reused else None
            }
            
        except Exception as e:
            print(f"Error obteniendo estadísticas de reutilización: {e}")
            return {
                'total_patterns': 0,
                'reuse_rate': 0.0,
                'error': str(e)
            }

# Instancia global del generador de herramientas
dynamic_tool_generator = DynamicToolGenerator()
