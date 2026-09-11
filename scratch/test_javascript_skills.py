"""
TEST SUITE: HABILIDADES DE JAVASCRIPT - VECTOR 2026
Validacion de capacidades de nivel experto:
1. Analisis lexico y balance de delimitadores (JavaScriptEngine.verificar_balance_delimitadores)
2. Extraccion estructural de funciones, clases e imports (JavaScriptEngine.analizar_codigo_js)
3. Auditoria de seguridad y anti-patrones (XSS, eval, var, ==, DOM nulls)
4. Motor de Auto-Reparacion Sintactica y Refactorizacion (JavaScriptEngine.reparar_codigo_js)
5. Integracion con deep_inspect_file para archivos .js adjuntos
6. Prueba End-to-End en /api/chat/ (reparacion de codigo roto y codificacion ES6+)
"""

import os
import sys

# Configurar sys.path y Django
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vector5010.settings')
import django
django.setup()

from vectorapp.javascript_engine import javascript_engine
from vectorapp.file_deep_analyzer import deep_inspect_file
from django.test import RequestFactory
from vectorapp.views import interactuar


def test_1_balance_delimitadores():
    print("[TEST JS 1] Verificando Balance Sintactico y Delimitadores...")
    codigo_valido = """
    function saludar(nombre) {
        if (!nombre) {
            return 'Hola desconocido';
        }
        return `Hola, ${nombre}!`;
    }
    """
    valido, err = javascript_engine.verificar_balance_delimitadores(codigo_valido)
    assert valido is True, f"Fallo en codigo valido: {err}"
    assert err is None

    # Codigo con llave faltante
    codigo_roto = """
    function calcular(a, b) {
        if (a > 0) {
            return a + b;
    }
    """
    valido_roto, err_roto = javascript_engine.verificar_balance_delimitadores(codigo_roto)
    assert valido_roto is False, "Fallo: Debio detectar llave sin cerrar"
    assert err_roto["tipo"] == "apertura_sin_cerrar"
    print(f"  [OK] Balance sintactico validado. Error detectado correctamente: {err_roto['mensaje']}")


def test_2_extraccion_estructural():
    print("[TEST JS 2] Verificando Extraccion Estructural (Funciones, Clases, Modulos)...")
    codigo_complejo = """
    import { EventEmitter } from 'events';
    const express = require('express');

    class GestorDatos extends EventEmitter {
        constructor(config = {}) {
            super();
            this.config = config;
        }

        async procesar(payload) {
            return payload;
        }
    }

    const sumar = (x, y) => x + y;
    async function descargar(url) {
        return await fetch(url);
    }

    export default GestorDatos;
    """
    res = javascript_engine.analizar_codigo_js(codigo_complejo, filename="gestor.js")
    assert res["es_valido"] is True, f"Fallo de validez: {res.get('error_sintaxis')}"
    
    nombres_fn = [f["nombre"] for f in res["funciones"]]
    assert "sumar" in nombres_fn, "Fallo: Arrow function 'sumar' no detectada"
    assert "descargar" in nombres_fn, "Fallo: Async function 'descargar' no detectada"
    
    nombres_cls = [c["nombre"] for c in res["clases"]]
    assert "GestorDatos" in nombres_cls, "Fallo: Clase 'GestorDatos' no detectada"
    assert res["clases"][0]["hereda_de"] == "EventEmitter", "Fallo: Herencia no detectada"
    
    assert len(res["imports"]) >= 2, "Fallo: Imports ES6/CommonJS no extraidos"
    print(f"  [OK] Estructura JS extraida: {len(res['funciones'])} funciones, {len(res['clases'])} clases, {len(res['imports'])} dependencias.")


def test_3_auditoria_seguridad_y_antipatrones():
    print("[TEST JS 3] Verificando Auditoria de Seguridad y Linter...")
    codigo_inseguro = """
    var usuario = 'admin';
    if (usuario == 'admin') {
        eval("console.log('acceso')");
        document.getElementById('panel').innerHTML = '<h1>Bienvenido</h1>';
    }
    """
    res = javascript_engine.analizar_codigo_js(codigo_inseguro, filename="inseguro.js")
    issues_texto = " ".join(res["issues"]).lower()
    
    assert "var" in issues_texto, "Fallo: No detecto uso obsoleto de 'var'"
    assert "igualdad" in issues_texto, "Fallo: No detecto igualdad debil '=='"
    assert "eval" in issues_texto, "Fallo: No detecto vulnerabilidad de 'eval()'"
    assert "innerhtml" in issues_texto, "Fallo: No detecto riesgo de XSS en '.innerHTML'"
    assert "dom" in issues_texto, "Fallo: No detecto acceso directo inseguro al DOM"
    print(f"  [OK] Auditoria estatica exitosa. Se detectaron {len(res['issues'])} vulnerabilidades/anti-patrones.")


def test_4_auto_reparacion_codigo_js():
    print("[TEST JS 4] Verificando Motor de Auto-Reparacion de JavaScript...")
    codigo_con_fallas = """
    var contador = 10;
    if (contador == 10) {
        document.getElementById('contador').innerText = contador;
    """
    reparacion = javascript_engine.reparar_codigo_js(codigo_con_fallas)
    assert reparacion["success"] is True, "Fallo en auto-reparacion"
    assert reparacion["es_valido"] is True, "Fallo: El codigo reparado debe ser sintacticamente valido"
    
    reparado = reparacion["codigo_reparado"]
    assert "let " in reparado or "const " in reparado, "Fallo: 'var' no fue reemplazado"
    assert "===" in reparado, "Fallo: '==' no fue promovido a '==='"
    assert "?." in reparado, "Fallo: No se anadio optional chaining en el DOM"
    assert reparado.strip().endswith("}"), "Fallo: No cerro la llave pendiente"
    print(f"  [OK] Auto-reparacion aplicada con {len(reparacion['cambios_aplicados'])} mejoras exitosas.")


def test_5_integracion_deep_inspect_file():
    print("[TEST JS 5] Verificando Integracion con deep_inspect_file para archivos .js...")
    archivo_js = """
    class MotorWeb {
        conectar(puerto) {
            console.log('Conectado a puerto ' + puerto);
        }
    }
    const app = new MotorWeb();
    app.conectar(8080);
    """
    reporte = deep_inspect_file("motor.js", archivo_js, "text/javascript")
    assert "ANÁLISIS TÉCNICO PROFUNDO DE JAVASCRIPT" in reporte or "ANALISIS TECNICO PROFUNDO DE JAVASCRIPT" in reporte, "Fallo: Encabezado JS no encontrado"
    assert "MotorWeb" in reporte, "Fallo: Clase no mencionada en el reporte"
    assert "conectar" in reporte, "Fallo: Metodo no mencionado en el reporte"
    print("  [OK] deep_inspect_file genera el informe tecnico de JavaScript correctamente.")


def test_6_blackbox_chat_javascript_repair_and_coding():
    print("[TEST JS 6] Verificando End-to-End /api/chat/ de Reparacion y Codificacion JS...")
    factory = RequestFactory()
    
    # Caso A: Reparacion de codigo roto
    payload_reparar = {
        "mensaje": "repara este código javascript por favor: function calcularTotal(precio, tasa) { var total = precio == 0 ? 0 : precio * tasa; document.getElementById('resultado').innerText = total; return total;",
        "nombre_cliente": "Sebastian",
        "session_id": "session_test_js_repair"
    }
    req = factory.post('/api/chat/', data=payload_reparar, content_type='application/json')
    res = interactuar(req)
    assert res.status_code == 200, f"HTTP Error: {res.status_code}"
    texto_res = res.data.get("respuesta", "")
    assert len(texto_res) > 30, "Respuesta demasiado breve"
    assert "function" in texto_res or "calcularTotal" in texto_res or "total" in texto_res, "Fallo: No incluyo explicacion o codigo JS"
    print(f"  [OK] Reparacion por chat respondida ({len(texto_res)} chars): {texto_res[:100]}...")

    # Caso B: Generacion de codigo ES6+
    payload_generar = {
        "mensaje": "hazme una función en javascript moderno ES6+ para formatear fechas en horario de Chile",
        "nombre_cliente": "Sebastian",
        "session_id": "session_test_js_coding"
    }
    req2 = factory.post('/api/chat/', data=payload_generar, content_type='application/json')
    res2 = interactuar(req2)
    assert res2.status_code == 200, f"HTTP Error: {res2.status_code}"
    texto_res2 = res2.data.get("respuesta", "")
    assert len(texto_res2) > 30, "Respuesta demasiado breve"
    print(f"  [OK] Codificacion ES6+ respondida ({len(texto_res2)} chars): {texto_res2[:100]}...")


def run_all_js_tests():
    print("================================================================")
    print("INICIANDO SUITE DE PRUEBAS DE JAVASCRIPT - VECTOR 2026")
    print("================================================================")
    test_1_balance_delimitadores()
    test_2_extraccion_estructural()
    test_3_auditoria_seguridad_y_antipatrones()
    test_4_auto_reparacion_codigo_js()
    test_5_integracion_deep_inspect_file()
    test_6_blackbox_chat_javascript_repair_and_coding()
    print("================================================================")
    print("TODAS LAS PRUEBAS DE JAVASCRIPT PASARON EXITOSAMENTE [6/6]")
    print("================================================================")


if __name__ == "__main__":
    run_all_js_tests()
