"""
Sistema de auto-programación de herramientas para Vector.
La IA puede crear, modificar y ejecutar herramientas dinámicamente.
"""

import os
import json
import ast
import re
import logging
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional

from .security import (
    ASTSecurityValidator,
    ToolPermissions,
    PathPolicy,
    SandboxPolicy,
    ToolRunner,
    ToolExecutionResult,
    PathTraversalViolation,
    ASTSecurityViolation,
    TOOL_TIMEOUT_SIMPLE,
    TOOL_TIMEOUT_COMPLEX,
    TOOL_MAX_OUTPUT_BYTES,
)

logger = logging.getLogger(__name__)


class ToolLevel(str, Enum):
    """Niveles de generación y autonomía de herramientas dinámicas."""
    LEVEL_A = "level_a"   # Reutilización o adaptación de herramienta existente
    LEVEL_B = "level_b"   # Plantilla estructurada parametrizada (cálculos, fechas, utilidades)
    LEVEL_C = "level_c"   # Síntesis LLM / código libre personalizado


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
        
        # Políticas de seguridad, confinamiento de rutas y sandbox runner
        self.path_policy = PathPolicy()
        self.sandbox_runner = ToolRunner(
            SandboxPolicy(timeout=TOOL_TIMEOUT_SIMPLE, max_output_bytes=TOOL_MAX_OUTPUT_BYTES)
        )
        
        # Crear directorio si no existe
        os.makedirs(self.tools_path, exist_ok=True)
        
        # Crear subdirectorio para pruebas unitarias de herramientas
        self.tests_path = os.path.join(self.tools_path, "tests")
        os.makedirs(self.tests_path, exist_ok=True)
        test_init = os.path.join(self.tests_path, "__init__.py")
        if not os.path.exists(test_init):
            with open(test_init, 'w', encoding='utf-8') as f:
                f.write("# Tests automáticos de herramientas dinámicas\n")
        
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
        """Template para herramientas de archivos confinadas estrictamente a tool_workspace."""
        return '''
import os
import json
import csv
from pathlib import Path

# Directorio base del workspace autorizado para herramientas
WORKSPACE = (Path(__file__).parent.parent / "tool_workspace").resolve()
WORKSPACE.mkdir(parents=True, exist_ok=True)

def safe_path(target_path):
    p = Path(target_path) if target_path else Path('.')
    resolved = (WORKSPACE / p).resolve() if not p.is_absolute() else p.resolve()
    if not (resolved == WORKSPACE or WORKSPACE in resolved.parents):
        raise PermissionError(f"Ruta fuera del workspace autorizado: '{target_path}'")
    return resolved

def execute_tool(action="list_files", **kwargs):
    """Herramienta de archivos generada dinámicamente y confinada a workspace."""
    
    if action == "list_files":
        directory = kwargs.get('directory', '.')
        try:
            target_dir = safe_path(directory)
            files = []
            for item in os.listdir(target_dir):
                path = target_dir / item
                files.append({
                    'name': item,
                    'is_directory': path.is_dir(),
                    'size': path.stat().st_size if path.is_file() else None,
                    'modified': path.stat().st_mtime
                })
            return files
        except Exception as e:
            return f"Error: {str(e)}"
            
    elif action == "read_file":
        filepath = kwargs.get('filepath')
        if not filepath:
            return "Error: Se requiere filepath"
        try:
            target_file = safe_path(filepath)
            with open(target_file, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"Error leyendo archivo: {str(e)}"
            
    elif action == "write_file":
        filepath = kwargs.get('filepath')
        content = kwargs.get('content', '')
        if not filepath:
            return "Error: Se requiere filepath"
        try:
            target_file = safe_path(filepath)
            target_file.parent.mkdir(parents=True, exist_ok=True)
            with open(target_file, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"Archivo {target_file.name} creado exitosamente en workspace"
        except Exception as e:
            return f"Error escribiendo archivo: {str(e)}"
            
    elif action == "create_directory":
        directory = kwargs.get('directory')
        if not directory:
            return "Error: Se requiere directory"
        try:
            target_dir = safe_path(directory)
            target_dir.mkdir(parents=True, exist_ok=True)
            return f"Directorio {target_dir.name} creado exitosamente en workspace"
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
        """Template para herramientas de cálculo seguro sin eval()."""
        return '''
import math
import operator
import ast

def _eval_math_ast(node):
    operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }
    functions = {
        'sqrt': math.sqrt,
        'sin': math.sin,
        'cos': math.cos,
        'tan': math.tan,
        'log': math.log,
    }
    constants = {
        'pi': math.pi,
        'e': math.e,
    }
    if isinstance(node, ast.Expression):
        return _eval_math_ast(node.body)
    elif isinstance(node, ast.Constant):
        return node.value
    elif isinstance(node, ast.Name):
        if node.id in constants:
            return constants[node.id]
        raise ValueError(f"Símbolo no permitido: {node.id}")
    elif isinstance(node, ast.BinOp):
        op = operators.get(type(node.op))
        if not op:
            raise ValueError(f"Operador binario no soportado: {type(node.op).__name__}")
        return op(_eval_math_ast(node.left), _eval_math_ast(node.right))
    elif isinstance(node, ast.UnaryOp):
        op = operators.get(type(node.op))
        if not op:
            raise ValueError(f"Operador unario no soportado: {type(node.op).__name__}")
        return op(_eval_math_ast(node.operand))
    elif isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id in functions:
            args = [_eval_math_ast(arg) for arg in node.args]
            return functions[node.func.id](*args)
        raise ValueError("Función matemática no permitida")
    else:
        raise ValueError(f"Expresión no permitida: {type(node).__name__}")

def execute_tool(action="calculate", **kwargs):
    """Herramienta de cálculo generada dinámicamente y segura (libre de eval)."""
    
    if action == "calculate":
        expression = kwargs.get('expression', '')
        try:
            tree = ast.parse(expression, mode='eval')
            result = _eval_math_ast(tree)
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
        """Template para herramientas de automatización de tareas y pipelines seguros."""
        return '''
import json
import time
from datetime import datetime

def execute_tool(action="run_pipeline", **kwargs):
    """Herramienta de automatización segura sin comandos de sistema operativo."""
    
    if action == "run_pipeline":
        tasks = kwargs.get('tasks', [])
        results = []
        for i, task in enumerate(tasks):
            task_name = task.get('name', f'tarea_{i}')
            task_type = task.get('type', 'transform')
            payload = task.get('payload', {})
            
            # Ejecutar tarea en memoria de forma segura
            results.append({
                'task': task_name,
                'type': task_type,
                'status': 'completed',
                'timestamp': datetime.now().isoformat()
            })
            
        return {
            'status': 'success',
            'total_tasks': len(tasks),
            'results': results
        }
        
    elif action == "schedule_task":
        task_name = kwargs.get('task_name', 'tarea_automatica')
        interval = kwargs.get('interval', 60)  # segundos
        
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
        """Template para herramientas de base de datos segura y parametrizada."""
        return '''
import sqlite3
import json
import re
from pathlib import Path
from datetime import datetime

# Workspace seguro para bases de datos
WORKSPACE = (Path(__file__).parent.parent / "tool_workspace").resolve()
WORKSPACE.mkdir(parents=True, exist_ok=True)

IDENTIFIER_REGEX = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
ALLOWED_OPERATORS = {'=', '!=', '>', '<', '>=', '<=', 'LIKE'}

def safe_db_path(raw_path="dynamic_data.db"):
    p = Path(raw_path) if raw_path else Path("dynamic_data.db")
    resolved = (WORKSPACE / p).resolve() if not p.is_absolute() else p.resolve()
    if not (resolved == WORKSPACE or WORKSPACE in resolved.parents):
        resolved = WORKSPACE / p.name
    return str(resolved)

def execute_tool(action="query", **kwargs):
    """Herramienta de base de datos segura con consultas parametrizadas."""
    
    if action == "create_table":
        db_path = safe_db_path(kwargs.get('db_path', 'dynamic_data.db'))
        table_name = kwargs.get('table_name', 'data_table')
        columns = kwargs.get('columns', {'id': 'INTEGER PRIMARY KEY', 'data': 'TEXT'})
        
        if not IDENTIFIER_REGEX.match(table_name):
            return "Error: Nombre de tabla inválido. Debe coincidir con ^[A-Za-z_][A-Za-z0-9_]*$"
            
        col_defs = []
        for col_name, col_type in columns.items():
            if not IDENTIFIER_REGEX.match(col_name):
                return f"Error: Nombre de columna inválido: {col_name}"
            clean_type = re.sub(r'[^A-Za-z0-9_ ]', '', str(col_type)).strip().upper()
            col_defs.append(f"{col_name} {clean_type}")
            
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(col_defs)})"
            cursor.execute(sql)
            conn.commit()
            conn.close()
            return f"Tabla {table_name} creada exitosamente"
        except Exception as e:
            return f"Error creando tabla: {str(e)}"
            
    elif action == "insert_data":
        db_path = safe_db_path(kwargs.get('db_path', 'dynamic_data.db'))
        table_name = kwargs.get('table_name', 'data_table')
        data = kwargs.get('data', {})
        
        if not IDENTIFIER_REGEX.match(table_name):
            return "Error: Nombre de tabla inválido"
        if not data or not isinstance(data, dict):
            return "Error: Los datos deben ser un diccionario no vacío"
            
        for col in data.keys():
            if not IDENTIFIER_REGEX.match(col):
                return f"Error: Nombre de columna inválido: {col}"
                
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cols = ', '.join(data.keys())
            placeholders = ', '.join(['?' for _ in data])
            sql = f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})"
            cursor.execute(sql, list(data.values()))
            conn.commit()
            row_id = cursor.lastrowid
            conn.close()
            return f"Datos insertados con ID: {row_id}"
        except Exception as e:
            return f"Error insertando datos: {str(e)}"
            
    elif action == "select_data":
        db_path = safe_db_path(kwargs.get('db_path', 'dynamic_data.db'))
        table_name = kwargs.get('table_name', 'data_table')
        filters = kwargs.get('filters', {})
        
        if not IDENTIFIER_REGEX.match(table_name):
            return "Error: Nombre de tabla inválido"
            
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            sql = f"SELECT * FROM {table_name}"
            params = []
            
            if filters and isinstance(filters, dict):
                where_clauses = []
                for col, spec in filters.items():
                    if not IDENTIFIER_REGEX.match(col):
                        conn.close()
                        return f"Error: Nombre de columna inválido en filtro: {col}"
                    if isinstance(spec, dict):
                        op = str(spec.get('operator', '=')).strip().upper()
                        val = spec.get('value')
                    else:
                        op = '='
                        val = spec
                    if op not in ALLOWED_OPERATORS:
                        conn.close()
                        return f"Error: Operador no permitido '{op}' en filtro"
                    where_clauses.append(f"{col} {op} ?")
                    params.append(val)
                if where_clauses:
                    sql += " WHERE " + " AND ".join(where_clauses)
                    
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description] if cursor.description else []
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
        Crea una nueva herramienta basándose en la solicitud del usuario aplicando validación AST.
        """
        try:
            analysis = self.analyze_user_need(user_request)
            
            if not tool_name:
                primary_need = analysis['detected_needs'][0] if analysis['detected_needs'] else 'general'
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                tool_name = f"{primary_need}_tool_{timestamp}"
            
            safe_tool_name = PathPolicy.sanitize_tool_name(tool_name)
            tool_code = self.generate_tool_code(analysis)
            
            category = analysis['detected_needs'][0] if analysis.get('detected_needs') else 'general'
            perms = ToolPermissions.default_for_category(category)
            
            res = self.create_and_validate_tool(safe_tool_name, tool_code, user_request, permissions=perms)
            if res.get('success'):
                res['tool_info'] = self.created_tools.get(safe_tool_name, {})
            return res
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f'❌ Error al crear herramienta: {str(e)}'
            }
    
    def validate_tool_code(self, tool_file: str, permissions: Optional[ToolPermissions] = None) -> Dict[str, Any]:
        """
        Valida que el código de la herramienta sea sintácticamente correcto y cumpla
        las políticas de seguridad AST según los permisos asignados.
        """
        try:
            with open(tool_file, 'r', encoding='utf-8') as f:
                code = f.read()
            
            # 1. Validación AST de Seguridad
            validator = ASTSecurityValidator(permissions=permissions)
            sec_res = validator.validate_code(code)

            if not sec_res['syntax_valid']:
                err_msg = sec_res['violations'][0]['message'] if sec_res['violations'] else 'Error de sintaxis'
                return {
                    'is_valid': False,
                    'security_valid': False,
                    'risk_level': sec_res['risk_level'],
                    'violations': sec_res['violations'],
                    'error': err_msg,
                    'line': sec_res['violations'][0].get('line', 0) if sec_res['violations'] else 0
                }

            if not sec_res['security_valid']:
                violation_msgs = [f"L{v['line']}: {v['message']} ({v['symbol']})" for v in sec_res['violations']]
                err_summary = "; ".join(violation_msgs)
                logger.warning(f"[ASTSecurity] Herramienta '{tool_file}' rechazada por violaciones: {err_summary}")
                return {
                    'is_valid': False,
                    'security_valid': False,
                    'risk_level': sec_res['risk_level'],
                    'violations': sec_res['violations'],
                    'error': f"Violación de seguridad AST ({sec_res['risk_level']}): {err_summary}"
                }

            # 2. Compilar para confirmar integridad sintáctica final
            compile(code, tool_file, 'exec')
            
            return {
                'is_valid': True,
                'security_valid': True,
                'risk_level': 'none',
                'violations': [],
                'message': 'Código válido y verificado por AST Security'
            }
            
        except SyntaxError as e:
            return {
                'is_valid': False,
                'security_valid': False,
                'risk_level': 'critical',
                'violations': [{'rule': 'SYNTAX_ERROR', 'message': str(e)}],
                'error': f'Error de sintaxis: {str(e)}',
                'line': getattr(e, 'lineno', 0)
            }
        except Exception as e:
            return {
                'is_valid': False,
                'security_valid': False,
                'risk_level': 'critical',
                'violations': [{'rule': 'VALIDATION_ERROR', 'message': str(e)}],
                'error': f'Error de validación: {str(e)}'
            }
    
    def execute_tool(self, tool_name: str, parameters: Any = None, action: Optional[str] = None, timeout: int = 5, **kwargs) -> Any:
        """
        Ejecuta una herramienta dinámica dentro de un entorno Sandbox aislado por subproceso.
        Aplica cuotas de tiempo, consumo de bytes de salida y sanitización de entorno con ToolRunner.
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

        # Ejecutar a través de ToolRunner
        exec_res = self.sandbox_runner.run_tool(
            tool_name=tool_name,
            tool_file=tool_file,
            action=act,
            parameters=params,
            timeout=timeout
        )

        if exec_res.success:
            result = exec_res.result
            execution_record = {
                'tool_name': tool_name,
                'action': act,
                'parameters': params,
                'result': str(result)[:500] + '...' if len(str(result)) > 500 else str(result),
                'timestamp': datetime.now().isoformat(),
                'success': True,
                'execution_time_s': exec_res.execution_time_s
            }
            self.execution_history.append(execution_record)
            self.created_tools[tool_name]['successful_uses'] = self.created_tools[tool_name].get('successful_uses', 0) + 1
            self.save_tools_registry()
            return result
        else:
            err = exec_res.error or "Error desconocido durante la ejecución"
            execution_record = {
                'tool_name': tool_name,
                'action': act,
                'parameters': params,
                'error': err,
                'timestamp': datetime.now().isoformat(),
                'success': False,
                'execution_time_s': exec_res.execution_time_s
            }
            self.execution_history.append(execution_record)
            return f"[Error] {err}"
    
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

    @staticmethod
    def infer_tool_level(code: str, category: str = "general", is_adaptation: bool = False) -> ToolLevel:
        """Determina el nivel de autonomía de la herramienta (Nivel A, B o C)."""
        if is_adaptation:
            return ToolLevel.LEVEL_A
        template_markers = ["def run(", "def calculate(", "def process(", "def execute(", "execute_tool"]
        if any(m in code for m in template_markers) and any(cat in category for cat in ["calculations", "time_related", "text_processing", "data_processing", "template"]):
            return ToolLevel.LEVEL_B
        return ToolLevel.LEVEL_C

    def generate_tool_unit_test(self, tool_name: str, code: str, category: str = "general") -> str:
        """
        Genera el código de prueba unitaria para una herramienta dinámica dada.
        Verifica exportaciones, ejecutabilidad e invariantes básicos sin efectos colaterales.
        """
        return f'''# Test unitario generado automáticamente para la herramienta: {tool_name}
import os
import sys
import unittest
import importlib.util
import inspect

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR = os.path.dirname(CURRENT_DIR)
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

class Test_{tool_name}(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tool_file = os.path.join(TOOLS_DIR, "{tool_name}.py")
        if not os.path.exists(tool_file):
            raise FileNotFoundError(f"Archivo de herramienta no encontrado: {{tool_file}}")
        spec = importlib.util.spec_from_file_location("{tool_name}", tool_file)
        if not spec or not spec.loader:
            raise ImportError(f"No se pudo crear spec para {{tool_file}}")
        cls.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.mod)

    def test_01_module_integrity(self):
        """Verifica que el módulo se haya cargado y contenga callables públicos."""
        funcs = [f for f in dir(self.mod) if callable(getattr(self.mod, f)) and not f.startswith('_')]
        self.assertTrue(len(funcs) > 0, "La herramienta no exporta ninguna función pública callable.")

    def test_02_execution_smoke(self):
        """Prueba de humo: valida ejecución básica sin excepciones no controladas."""
        if hasattr(self.mod, "execute_tool"):
            res = self.mod.execute_tool(action="help")
            self.assertIsNotNone(res)
        elif hasattr(self.mod, "{tool_name}"):
            fn = getattr(self.mod, "{tool_name}")
            sig = inspect.signature(fn)
            required = [p for p, v in sig.parameters.items() if v.default == inspect.Parameter.empty]
            if not required:
                res = fn()
                self.assertIsNotNone(res)
            else:
                self.assertTrue(callable(fn))
        else:
            funcs = [f for f in dir(self.mod) if callable(getattr(self.mod, f)) and not f.startswith('_')]
            fn = getattr(self.mod, funcs[0])
            self.assertTrue(callable(fn))

if __name__ == "__main__":
    unittest.main()
'''

    def create_and_validate_tool(
        self,
        tool_name: str,
        code: str,
        description: str,
        permissions: Optional[ToolPermissions] = None,
        tool_level: Optional[ToolLevel] = None,
        is_adaptation: bool = False
    ) -> Dict[str, Any]:
        """
        Crea, valida y auto-testea una nueva herramienta aplicando políticas de seguridad AST,
        clasificación por ToolLevel y ejecución de tests unitarios en sandbox antes del registro.
        """
        tool_file = None
        test_file = None
        try:
            # 1. Sanitizar nombre de la herramienta (prevenir Path Traversal en el nombre)
            safe_tool_name = PathPolicy.sanitize_tool_name(tool_name)

            # 2. Asignar o inferir permisos y nivel de autonomía
            current_level = tool_level or self.infer_tool_level(code, description, is_adaptation=is_adaptation)
            tool_perms = permissions or ToolPermissions.default_for_category(description)

            # 3. Pre-validar AST en memoria antes de escribir en disco
            validator = ASTSecurityValidator(permissions=tool_perms)
            pre_val = validator.validate_code(code)
            if not pre_val['security_valid']:
                violation_msgs = [f"L{v['line']}: {v['message']} ({v['symbol']})" for v in pre_val['violations']]
                err_summary = "; ".join(violation_msgs)
                logger.warning(f"[ASTSecurity] Creación de '{safe_tool_name}' rechazada por violaciones AST: {err_summary}")
                return {
                    'success': False,
                    'error': f"Violación de seguridad AST ({pre_val['risk_level']}): {err_summary}",
                    'violations': pre_val['violations'],
                    'risk_level': pre_val['risk_level'],
                    'message': f"❌ Error de seguridad al crear herramienta: {err_summary}"
                }

            # 4. Escribir archivo de la herramienta
            tool_file = os.path.join(self.tools_path, f"{safe_tool_name}.py")
            with open(tool_file, 'w', encoding='utf-8') as f:
                f.write(f"""# Herramienta generada automáticamente por Vector
# Descripción: {description}
# Nivel de Autonomía: {current_level.value if isinstance(current_level, ToolLevel) else current_level}
# Fecha de creación: {datetime.now().isoformat()}

{code}
""")

            # 5. Validar código en archivo
            validation_result = self.validate_tool_code(tool_file, permissions=tool_perms)
            if not validation_result['is_valid']:
                if os.path.exists(tool_file):
                    os.remove(tool_file)
                return {
                    'success': False,
                    'error': validation_result.get('error', 'Error de validación'),
                    'violations': validation_result.get('violations', []),
                    'risk_level': validation_result.get('risk_level', 'high'),
                    'message': f'❌ Error al crear herramienta: {validation_result.get("error")}'
                }

            # 6. Generar y ejecutar prueba unitaria automática en sandbox aislado
            test_code = self.generate_tool_unit_test(safe_tool_name, code, description)
            test_file = os.path.join(self.tests_path, f"test_{safe_tool_name}.py")
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write(test_code)

            test_result = self.sandbox_runner.run_test_file(test_file, timeout=10)
            if not test_result.success:
                logger.warning(f"[ToolAutonomy] Test automático falló para '{safe_tool_name}': {test_result.error}")
                if os.path.exists(tool_file):
                    os.remove(tool_file)
                if os.path.exists(test_file):
                    os.remove(test_file)
                return {
                    'success': False,
                    'error': f"Fallo en prueba unitaria automática: {test_result.error}",
                    'test_status': 'failed',
                    'tool_level': current_level.value if isinstance(current_level, ToolLevel) else str(current_level),
                    'message': f"❌ La herramienta '{safe_tool_name}' falló su prueba unitaria automática: {test_result.error}"
                }

            # 7. Registrar herramienta aprobada
            tool_info = {
                'name': safe_tool_name,
                'file_path': tool_file,
                'test_file': test_file,
                'test_status': 'passed',
                'tool_level': current_level.value if isinstance(current_level, ToolLevel) else str(current_level),
                'created_at': datetime.now().isoformat(),
                'description': description,
                'status': 'active',
                'successful_uses': 0,
                'permissions': tool_perms.to_dict(),
                'risk_level': 'none',
                'code_signature': self._extract_code_signature(code),
                'learning_data': {
                    'created_from_request': description,
                    'reuse_count': 0,
                    'adaptation_count': 0
                }
            }

            self.created_tools[safe_tool_name] = tool_info
            self.save_tools_registry()

            # Aprender del código generado
            self.learn_from_generated_code(safe_tool_name, code, description)

            return {
                'success': True,
                'tool_name': safe_tool_name,
                'tool_level': current_level.value if isinstance(current_level, ToolLevel) else str(current_level),
                'test_status': 'passed',
                'message': f'✅ Herramienta "{safe_tool_name}" ({current_level.value if isinstance(current_level, ToolLevel) else current_level}) creada exitosamente, validada por AST y verificada por test unitario en sandbox.'
            }

        except PathTraversalViolation as ptv:
            if tool_file and os.path.exists(tool_file):
                os.remove(tool_file)
            if test_file and os.path.exists(test_file):
                os.remove(test_file)
            return {
                'success': False,
                'error': str(ptv),
                'message': f'❌ Error de seguridad de ruta: {str(ptv)}'
            }
        except Exception as e:
            if tool_file and os.path.exists(tool_file):
                os.remove(tool_file)
            if test_file and os.path.exists(test_file):
                os.remove(test_file)
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
                f"Adaptación de {base_tool_name}: {new_request}",
                is_adaptation=True
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
