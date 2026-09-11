#!/usr/bin/env python
"""
Demostración del sistema de reutilización de herramientas de Vector.
Este script muestra cómo Vector aprende y reutiliza código.
"""

import os
import sys
import django
from pathlib import Path

# Configurar Django
sys.path.append(str(Path(__file__).parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vector5010.settings')
django.setup()

from vectorapp.dynamic_tools_generator import DynamicToolGenerator
from vectorapp.neural_network import semantic_network

def demo_tool_reuse():
    """
    Demostración del sistema de reutilización de herramientas.
    """
    print("🔧 DEMOSTRACIÓN DEL SISTEMA DE REUTILIZACIÓN DE HERRAMIENTAS")
    print("=" * 60)
    
    # Inicializar generador
    generator = DynamicToolGenerator()
    
    # Ejemplo 1: Crear herramienta de suma
    print("\n1. Creando herramienta de suma de números...")
    request1 = "Genera un código para sumar dos números"
    
    # Analizar necesidad
    analysis1 = generator.analyze_user_need(request1)
    print(f"   Análisis: {analysis1['detected_needs']}")
    print(f"   Confianza: {analysis1['confidence']:.2f}")
    
    # Crear herramienta
    if analysis1['confidence'] > 0.5:
        tool_code = generator.generate_tool_code(
            "suma_numeros",
            "Herramienta para sumar números",
            {"category": "calculations"}
        )
        
        result1 = generator.create_and_validate_tool(
            "suma_numeros",
            tool_code,
            "Herramienta para sumar números"
        )
        
        if result1['success']:
            print(f"   ✅ {result1['message']}")
            
            # Ejecutar herramienta
            resultado = generator.execute_tool("suma_numeros", {"action": "calculate", "expression": "5 + 3"})
            print(f"   Resultado de suma: {resultado}")
        else:
            print(f"   ❌ {result1['message']}")
    
    # Ejemplo 2: Solicitar herramienta similar
    print("\n2. Solicitando herramienta similar (multiplicación)...")
    request2 = "Necesito multiplicar dos números"
    
    # Analizar necesidad (debería sugerir reutilización)
    analysis2 = generator.analyze_user_need(request2)
    print(f"   Análisis: {analysis2['detected_needs']}")
    print(f"   Confianza: {analysis2['confidence']:.2f}")
    
    # Verificar sugerencias de reutilización
    reuse_suggestion = analysis2.get('reuse_suggestion', {})
    if reuse_suggestion.get('can_reuse', False):
        print(f"   🔄 Sugerencia de reutilización: {reuse_suggestion['message']}")
        
        # Adaptar herramienta existente
        adaptation_result = generator.adapt_existing_tool(
            reuse_suggestion['suggested_tool'],
            request2
        )
        
        if adaptation_result['success']:
            print(f"   ✅ {adaptation_result['message']}")
            
            # Ejecutar herramienta adaptada
            resultado = generator.execute_tool(
                adaptation_result['adapted_tool_name'],
                {"action": "calculate", "expression": "5 * 3"}
            )
            print(f"   Resultado de multiplicación: {resultado}")
        else:
            print(f"   ❌ Error adaptando: {adaptation_result['error']}")
    else:
        print("   ℹ️  No se sugirió reutilización")
    
    # Ejemplo 3: Mostrar estadísticas de reutilización
    print("\n3. Estadísticas de reutilización...")
    stats = generator.get_reuse_statistics()
    print(f"   Total de patrones aprendidos: {stats['total_patterns']}")
    print(f"   Total de reutilizaciones: {stats.get('total_reuses', 0)}")
    print(f"   Tasa de reutilización: {stats['reuse_rate']:.2%}")
    
    if stats.get('most_reused_pattern'):
        most_reused = stats['most_reused_pattern']
        print(f"   Patrón más reutilizado: {most_reused['tool_name']} ({most_reused['usage_count']} usos)")
    
    # Ejemplo 4: Listar herramientas creadas
    print("\n4. Herramientas creadas:")
    tool_list = generator.list_tools()
    for tool in tool_list['tools']:
        print(f"   - {tool['name']}: {tool.get('user_request', 'N/A')}")
    
    # Ejemplo 5: Integración con red neuronal
    print("\n5. Integración con red neuronal...")
    neural_insights = semantic_network.get_pattern_insights("tool_creation")
    print(f"   Insights neurales sobre creación de herramientas: {len(neural_insights)} patrones encontrados")
    
    for insight in neural_insights[:3]:  # Mostrar primeros 3
        print(f"   - {insight.get('insight', 'N/A')}")
    
    print("\n" + "=" * 60)
    print("🎉 DEMOSTRACIÓN COMPLETADA")
    print("Vector ahora puede:")
    print("- Aprender de cada herramienta que crea")
    print("- Detectar patrones similares en nuevas solicitudes")
    print("- Reutilizar código existente cuando es apropiado")
    print("- Adaptar herramientas existentes para nuevas necesidades")
    print("- Mantener estadísticas de uso y reutilización")

if __name__ == "__main__":
    demo_tool_reuse()
