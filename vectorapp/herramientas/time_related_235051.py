# Herramienta generada automáticamente por Vector
# Descripción: Herramienta para: hazme una función en javascript moderno ES6+ para formatear fechas en horario de Chile
# Fecha de creación: 2026-09-10T23:50:51.290486


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

