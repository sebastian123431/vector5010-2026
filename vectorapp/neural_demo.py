"""
Demostración de uso de la red neuronal semántica.
"""

from .neural_network import AdaptiveSemanticNetwork
from .neural_config import NeuralNetworkMetrics

def demo_neural_network():
    """
    Demostración de las capacidades de la red neuronal.
    """
    print("🧠 DEMOSTRACIÓN DE RED NEURONAL SEMÁNTICA")
    print("=" * 50)
    
    # Crear red neuronal
    network = AdaptiveSemanticNetwork()
    
    print(f"Estado inicial: {len(network.neurons)} neuronas")
    
    # Añadir algunos recuerdos/conceptos
    print("\n📚 Añadiendo conocimientos...")
    
    conocimientos = [
        ("Sebastian Espíndola es mi creador y desarrollador", "creator"),
        ("Python es mi lenguaje de programación favorito", "programming"),
        ("Django es el framework web que uso", "framework"),
        ("Me gusta aprender de cada interacción", "learning"),
        ("Nicolás Vicentelo es amigo de Sebastian", "friend"),
        ("Las redes neuronales son fascinantes", "ai"),
        ("Programar es una forma de arte", "philosophy"),
        ("Los bugs son oportunidades de aprendizaje", "debugging"),
        ("La inteligencia artificial puede ser creativa", "creativity"),
        ("Me esfuerzo por ser útil y preciso", "goal")
    ]
    
    neuron_ids = []
    for contenido, tipo in conocimientos:
        neuron_id = network.add_memory(contenido, tipo)
        neuron_ids.append(neuron_id)
        print(f"  ✓ Neurona {neuron_id} ({tipo}): {contenido[:50]}...")
    
    print(f"\nEstado actual: {len(network.neurons)} neuronas")
    
    # Demostrar consultas
    print("\n🔍 Realizando consultas...")
    
    consultas = [
        "¿Quién es Sebastian?",
        "¿Qué sabes sobre programación?",
        "¿Cuál es tu objetivo?",
        "¿Conoces a Nicolás?",
        "¿Qué opinas de la inteligencia artificial?"
    ]
    
    for consulta in consultas:
        print(f"\n📝 Consulta: {consulta}")
        resultados = network.query_network(consulta, top_k=3)
        
        for i, (neuron_id, similarity) in enumerate(resultados, 1):
            neuron = network.neurons[neuron_id]
            print(f"  {i}. [{similarity:.2f}] {neuron.content[:80]}...")
    
    # Demostrar aprendizaje de interacciones
    print("\n🎓 Simulando aprendizaje de interacciones...")
    
    interacciones = [
        ("¿Cómo estás?", "¡Estoy muy bien! Aprendiendo constantemente."),
        ("¿Puedes ayudarme con Python?", "¡Por supuesto! Python es uno de mis temas favoritos."),
        ("Gracias por tu ayuda", "¡De nada! Me alegra poder ayudarte."),
        ("¿Qué sabes sobre Django?", "Django es el framework web que uso. Es muy potente.")
    ]
    
    for pregunta, respuesta in interacciones:
        print(f"  📖 Aprendiendo: {pregunta} -> {respuesta[:50]}...")
        network.learn_from_interaction(pregunta, respuesta, "positivo")
    
    # Mostrar métricas
    print("\n📊 MÉTRICAS DE LA RED NEURONAL")
    print("-" * 30)
    
    metrics = NeuralNetworkMetrics(network)
    
    # Salud de la red
    health = metrics.get_network_health()
    print(f"Salud de la red: {health['status']} ({health['health_score']:.2f})")
    print(f"Total neuronas: {health['total_neurons']}")
    print(f"Total conexiones: {health['total_connections']}")
    print(f"Densidad de conexiones: {health['connection_density']:.3f}")
    print(f"Activación promedio: {health['avg_activation']:.3f}")
    
    # Estadísticas de aprendizaje
    learning_stats = metrics.get_learning_statistics()
    print("\nDistribución por tipo:")
    for tipo, cantidad in learning_stats['type_distribution'].items():
        print(f"  {tipo}: {cantidad}")
    
    print("\nNeuronas más activas:")
    for neuron_info in learning_stats['most_active'][:3]:
        print(f"  • {neuron_info['id']}: {neuron_info['content'][:50]}...")
    
    # Estadísticas específicas de Sebastian
    sebastian_stats = metrics.get_sebastian_focused_stats()
    if 'total_sebastian_neurons' in sebastian_stats:
        print(f"\nNeuronas relacionadas con Sebastian: {sebastian_stats['total_sebastian_neurons']}")
        top_topics = sebastian_stats.get('top_topics', [])
        if isinstance(top_topics, list):
            for item in top_topics[:5]:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    print(f"  • {item[0]}: {item[1]}")
    
    # Demostrar propagación de activación
    print("\n⚡ PROPAGACIÓN DE ACTIVACIÓN")
    print("-" * 30)
    
    # Activar una neurona específica
    if neuron_ids:
        test_neuron_id = neuron_ids[0]
        test_neuron = network.neurons[test_neuron_id]
        
        print(f"Activando neurona: {test_neuron.content[:50]}...")
        
        # Mostrar estado antes
        print("Estado antes de la activación:")
        for nid in neuron_ids[:3]:
            neuron = network.neurons[nid]
            print(f"  {nid}: {neuron.activation_level:.3f}")
        
        # Activar
        network._propagate_activation(test_neuron_id)
        
        # Mostrar estado después
        print("Estado después de la activación:")
        for nid in neuron_ids[:3]:
            neuron = network.neurons[nid]
            print(f"  {nid}: {neuron.activation_level:.3f}")
    
    # Demostrar poda de la red
    print("\n✂️ PODA DE LA RED")
    print("-" * 20)
    
    initial_count = len(network.neurons)
    network.prune_network()
    final_count = len(network.neurons)
    
    print(f"Neuronas antes de poda: {initial_count}")
    print(f"Neuronas después de poda: {final_count}")
    print(f"Neuronas eliminadas: {initial_count - final_count}")
    
    print("\n🎯 RESUMEN FINAL")
    print("=" * 20)
    print(f"La red neuronal ahora tiene {len(network.neurons)} neuronas")
    print(f"Total de conexiones: {sum(len(n.connections) for n in network.neurons.values())}")
    print("La red está lista para aprender y evolucionar!")
    
    return network

if __name__ == "__main__":
    demo_neural_network()
