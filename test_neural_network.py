#!/usr/bin/env python
"""
Script de prueba para la red neuronal semántica.
"""

import os
import sys

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vector5010.settings')
django.setup()

from vectorapp.neural_network import semantic_network

def test_neural_network():
    """
    Prueba completa del sistema de red neuronal.
    """
    print("🧠 PRUEBA DE RED NEURONAL SEMÁNTICA")
    print("=" * 50)
    
    # Estado inicial
    print(f"Estado inicial: {len(semantic_network.neurons)} neuronas")
    
    # Añadir algunos recuerdos
    print("\n📚 Añadiendo recuerdos...")
    
    recuerdos = [
        ("Sebastian Espíndola es mi creador y desarrollador", "creator"),
        ("Python es mi lenguaje de programación favorito", "programming"),
        ("Django es el framework web que utilizo", "framework"),
        ("Me gusta aprender de cada interacción con usuarios", "learning"),
        ("Nicolás Vicentelo es amigo de Sebastian", "friend"),
        ("Las redes neuronales son fascinantes", "ai"),
        ("Programar es una forma de arte creativo", "philosophy"),
        ("Los errores son oportunidades de aprendizaje", "debugging"),
        ("La inteligencia artificial puede ser muy creativa", "creativity"),
        ("Mi objetivo es ser útil y preciso en mis respuestas", "goal")
    ]
    
    for contenido, tipo in recuerdos:
        neuron_id = semantic_network.add_memory(contenido, tipo)
        print(f"  ✓ {neuron_id} ({tipo}): {contenido[:50]}...")
    
    print(f"\nEstado actual: {len(semantic_network.neurons)} neuronas")
    
    # Probar consultas
    print("\n🔍 Probando consultas...")
    
    consultas = [
        "¿Quién es Sebastian?",
        "¿Qué sabes sobre programación?",
        "¿Cuál es tu objetivo principal?",
        "¿Conoces a Nicolás?",
        "¿Qué opinas de la inteligencia artificial?"
    ]
    
    for consulta in consultas:
        print(f"\n📝 Consulta: {consulta}")
        resultados = semantic_network.query_network(consulta, top_k=3)
        
        if resultados:
            for i, (neuron_id, similarity) in enumerate(resultados, 1):
                neuron = semantic_network.neurons[neuron_id]
                print(f"  {i}. [{similarity:.3f}] {neuron.content[:80]}...")
        else:
            print("  No se encontraron resultados.")
    
    # Simular aprendizaje de interacciones
    print("\n🎓 Simulando aprendizaje...")
    
    interacciones = [
        ("¿Cómo estás hoy?", "¡Estoy muy bien! Gracias por preguntar.", "positivo"),
        ("¿Puedes ayudarme con Python?", "¡Por supuesto! Python es uno de mis temas favoritos.", "positivo"),
        ("Gracias por tu ayuda", "¡De nada! Me alegra mucho poder ayudarte.", "positivo"),
        ("¿Qué sabes sobre Django?", "Django es el framework web que uso. Es muy potente y flexible.", "positivo")
    ]
    
    for pregunta, respuesta, feedback in interacciones:
        print(f"  📖 Aprendiendo: {pregunta[:40]}... -> {respuesta[:40]}...")
        semantic_network.learn_from_interaction(pregunta, respuesta, feedback)
    
    # Mostrar métricas
    print("\n📊 MÉTRICAS DE LA RED")
    print("-" * 30)
    
    state = semantic_network.get_network_state()
    print(f"Total neuronas: {state['total_neurons']}")
    print(f"Total conexiones: {state['total_connections']}")
    print(f"Densidad de red: {state['network_density']:.4f}")
    print(f"Activación promedio: {state['average_activation']:.4f}")
    
    print("\nDistribución por tipo:")
    for tipo, cantidad in state['neuron_types'].items():
        print(f"  {tipo}: {cantidad}")
    
    # Insights
    insights = semantic_network.get_insights()
    if insights:
        print("\n🔍 INSIGHTS")
        print("-" * 15)
        
        if 'most_active_neuron' in insights:
            print(f"Neurona más activa: {insights['most_active_neuron']['content'][:60]}...")
            
        if 'most_connected_neuron' in insights:
            print(f"Neurona más conectada: {insights['most_connected_neuron']['content'][:60]}...")
    
    # Iniciar aprendizaje continuo
    print("\n⚡ INICIANDO APRENDIZAJE CONTINUO")
    print("-" * 35)
    
    if not semantic_network.is_learning:
        semantic_network.start_continuous_learning()
        print("✅ Aprendizaje continuo iniciado")
    else:
        print("✅ Aprendizaje continuo ya estaba activo")
    
    print("\n🎯 RESUMEN FINAL")
    print("=" * 20)
    print(f"✅ Red neuronal operativa con {len(semantic_network.neurons)} neuronas")
    print(f"✅ {sum(len(n.connections) for n in semantic_network.neurons.values())} conexiones establecidas")
    print(f"✅ Aprendizaje continuo: {'Activo' if semantic_network.is_learning else 'Inactivo'}")
    print("✅ Sistema listo para integrarse con Vector!")
    
    return True

if __name__ == "__main__":
    try:
        test_neural_network()
        print("\n🎉 ¡PRUEBA COMPLETADA EXITOSAMENTE!")
    except Exception as e:
        print(f"\n❌ ERROR EN LA PRUEBA: {e}")
        import traceback
        traceback.print_exc()
