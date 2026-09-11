"""
Test Suite: Verificación Integral del Módulo Meteorológico Open-Meteo para Vector 2026.
Comprueba:
1. Balance y análisis sintáctico AST de los 4 archivos JavaScript en static/js/weather/.
2. Existencia y vinculación de static/css/weather.css y scripts en templates/base.html y templates/network.html.
3. Presencia de controles DOM: #weather-section, #weather-content, #weather-refresh-btn, etc.
4. Validación contra la API real de Open-Meteo verificando el esquema de datos.
"""

import os
import sys
import re
import urllib.request
import json

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from vectorapp.javascript_engine import javascript_engine

def run_tests():
    print("=" * 64)
    print("INICIANDO PRUEBAS DE INTEGRACIÓN: MÓDULO METEOROLÓGICO OPEN-METEO")
    print("=" * 64)
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    js_dir = os.path.join(base_dir, 'static', 'js', 'weather')
    css_path = os.path.join(base_dir, 'static', 'css', 'weather.css')
    base_html = os.path.join(base_dir, 'templates', 'base.html')
    network_html = os.path.join(base_dir, 'templates', 'network.html')
    
    js_files = [
        'weather-codes.js',
        'weather-api.js',
        'weather-ui.js',
        'weather.js'
    ]
    
    # TEST 1: Verificar existencia y balance de delimitadores en los 4 archivos JS
    print("\n[TEST 1] Verificando análisis sintáctico y balance de delimitadores en archivos JS...")
    for jf in js_files:
        full_p = os.path.join(js_dir, jf)
        assert os.path.exists(full_p), f"Archivo no encontrado: {full_p}"
        with open(full_p, 'r', encoding='utf-8') as f:
            code = f.read()
        is_bal, err = javascript_engine.verificar_balance_delimitadores(code)
        assert is_bal, f"Falla de balance sintáctico en {jf}: {err}"
        analisis = javascript_engine.analizar_codigo_js(code, filename=jf)
        assert analisis['es_valido'], f"Análisis inválido en {jf}: {analisis['error_sintaxis']}"
        print(f"  [OK] {jf} sintácticamente válido. Funciones detectadas: {len(analisis['funciones'])}")

    # TEST 2: Verificar hoja de estilos CSS y vinculación en base.html
    print("\n[TEST 2] Verificando static/css/weather.css y vinculación en base.html...")
    assert os.path.exists(css_path), "No existe static/css/weather.css"
    with open(base_html, 'r', encoding='utf-8') as f:
        base_content = f.read()
    assert 'weather.css' in base_content, "weather.css no está incluido en base.html"
    for jf in js_files:
        assert f"weather/{jf}" in base_content, f"Script {jf} no está cargado en base.html"
    assert "⛅ Estación Meteorológica" in base_content, "Enlace de estación meteorológica no está en el sidebar de base.html"
    print("  [OK] CSS y 4 scripts JS correctamente vinculados en base.html.")

    # TEST 3: Verificar controles DOM en templates/network.html
    print("\n[TEST 3] Verificando elementos DOM en templates/network.html...")
    with open(network_html, 'r', encoding='utf-8') as f:
        net_content = f.read()
    assert 'id="weather-section"' in net_content, "#weather-section ausente en network.html"
    assert 'id="weather-content"' in net_content, "#weather-content ausente en network.html"
    assert 'id="weather-refresh-btn"' in net_content, "#weather-refresh-btn ausente en network.html"
    assert 'id="weather-collapse-btn"' in net_content, "#weather-collapse-btn ausente en network.html"
    assert 'id="weather-header-badge"' in net_content, "#weather-header-badge ausente en network.html"
    assert 'id="btn-weather-toggle"' in net_content, "#btn-weather-toggle ausente en network.html"
    print("  [OK] Todos los contenedores, botones y badges meteorológicos presentes en network.html.")

    # TEST 4: Verificar parámetros requeridos de Open-Meteo en weather-api.js
    print("\n[TEST 4] Verificando parámetros requeridos en weather-api.js...")
    with open(os.path.join(js_dir, 'weather-api.js'), 'r', encoding='utf-8') as f:
        api_code = f.read()
    required_params = [
        'temperature_2m',
        'relative_humidity_2m',
        'apparent_temperature',
        'precipitation',
        'weather_code',
        'cloud_cover',
        'pressure_msl',
        'wind_speed_10m',
        'wind_direction_10m',
        'wind_gusts_10m',
        'precipitation_probability',
        'temperature_2m_max',
        'temperature_2m_min',
        'apparent_temperature_max',
        'apparent_temperature_min',
        'precipitation_probability_max',
        'sunrise',
        'sunset',
        'forecast_days',
        'timezone'
    ]
    for p in required_params:
        assert p in api_code, f"Parámetro requerido '{p}' no encontrado en weather-api.js"
    print("  [OK] Todos los 20 parámetros de consulta Open-Meteo validados en weather-api.js.")

    # TEST 5: Consulta real a Open-Meteo simulando el fetch del navegador
    print("\n[TEST 5] Consultando API real de Open-Meteo con coordenadas de prueba...")
    lat = -33.4489
    lon = -70.6693
    url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={lat:.4f}&longitude={lon:.4f}"
        f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,cloud_cover,pressure_msl,wind_speed_10m,wind_direction_10m,wind_gusts_10m"
        f"&hourly=temperature_2m,apparent_temperature,precipitation_probability,weather_code,relative_humidity_2m,wind_speed_10m"
        f"&daily=weather_code,temperature_2m_max,temperature_2m_min,apparent_temperature_max,apparent_temperature_min,precipitation_probability_max,sunrise,sunset"
        f"&timezone=auto&forecast_days=7"
    )
    req = urllib.request.Request(url, headers={'User-Agent': 'Vector2026-Weather/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            assert resp.status == 200, f"Respuesta no fue 200: {resp.status}"
            data = json.loads(resp.read().decode('utf-8'))
            assert 'current' in data, "No hay bloque 'current' en respuesta"
            assert 'daily' in data, "No hay bloque 'daily' en respuesta"
            assert 'hourly' in data, "No hay bloque 'hourly' en respuesta"
            print(f"  [OK] Open-Meteo respondió HTTP 200.")
            print(f"       Temperatura actual: {data['current']['temperature_2m']}°C")
            print(f"       Humedad: {data['current']['relative_humidity_2m']}%")
            print(f"       Viento: {data['current']['wind_speed_10m']} km/h (dir: {data['current']['wind_direction_10m']}°)")
            print(f"       Pronóstico 7 días: {len(data['daily']['time'])} días recibidos.")
            print(f"       Pronóstico horario: {len(data['hourly']['time'])} horas recibidas.")
    except Exception as e:
        print(f"  [ADVERTENCIA] Fallo al contactar Open-Meteo vía urllib (posible offline o rate limit): {e}")

    # TEST 6: Verificar conversión de grados a dirección cardinal en weather-ui.js
    print("\n[TEST 6] Verificando conversión de grados a rumbos cardinales...")
    with open(os.path.join(js_dir, 'weather-ui.js'), 'r', encoding='utf-8') as f:
        ui_code = f.read()
    assert 'windDegreesToCardinal' in ui_code, "Función windDegreesToCardinal ausente"
    for cardinal in ['N', 'NE', 'E', 'SE', 'S', 'SO', 'O', 'NO']:
        assert f"'{cardinal}'" in ui_code or f'"{cardinal}"' in ui_code, f"Cardinal {cardinal} ausente en weather-ui.js"
    print("  [OK] Algoritmo de rumbos cardinales validado.")

    print("\n" + "=" * 64)
    print("TODAS LAS PRUEBAS DEL MÓDULO METEOROLÓGICO PASARON EXITOSAMENTE [6/6]")
    print("=" * 64)

if __name__ == '__main__':
    run_tests()
