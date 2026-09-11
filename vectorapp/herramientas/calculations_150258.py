# Herramienta generada automáticamente
# Descripción: Herramienta para: calcula 5 + 3 por favor


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
