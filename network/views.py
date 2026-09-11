import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

def network_view(request):
    """Renderiza la vista principal de la red neuronal y consola cognitiva de Vector"""
    return render(request, 'network.html')

def home(request):
    """Página de inicio o redirección a la estación neural"""
    return render(request, 'network/home.html')

COLOR_MAP = {
    'core': '#e74c3c',         # Red
    'creator': '#e67e22',      # Orange
    'programming': '#3498db',  # Blue
    'framework': '#2980b9',    # Darker blue
    'learning': '#2ecc71',     # Emerald green
    'memory': '#1abc9c',       # Teal
    'ai': '#9b59b6',           # Purple
    'philosophy': '#8e44ad',   # Violet
    'capability': '#f1c40f',   # Yellow
    'goal': '#e84393',         # Pink
    'fact': '#00cec9',         # Cyan
    'interaction': '#6c5ce7',  # Indigo
    'tool_creation': '#fdcb6e',# Amber
    'concept': '#0984e3',      # Sky blue
    'question': '#00b894',     # Mint
    'answer': '#fab1a0',       # Peach
    'general': '#a29bfe'       # Lavender
}

def semantic_network_data(request):
    """Devuelve los nodos y aristas de la red neuronal semántica real de Vector"""
    try:
        from vectorapp.neural_network import semantic_network
        network_ai = semantic_network
        if not network_ai.neurons:
            network_ai.load_network()
    except Exception as e:
        return JsonResponse({'error': f'Error cargando red neuronal: {str(e)}'}, status=500)

    nodes = []
    edges = []
    seen_edges = set()
    
    # Verificar que la red tenga neuronas
    if hasattr(network_ai, 'neurons') and network_ai.neurons:
        for neuron in network_ai.neurons.values():
            color = COLOR_MAP.get(neuron.concept_type, '#a29bfe')
            conn_count = len(neuron.connections)
            nodes.append({
                'id': neuron.id,
                'label': neuron.content[:24] + ('...' if len(neuron.content) > 24 else ''),
                'title': f"ID: {neuron.id}\nTipo: {neuron.concept_type}\nActivación: {neuron.activation_level:.2f}\nConexiones: {conn_count}\n\n{neuron.content}",
                'content': neuron.content,
                'group': neuron.concept_type,
                'activation': round(neuron.activation_level, 2),
                'connections_count': conn_count,
                'value': max(10, min(36, 12 + conn_count * 1.5)),
                'color': color
            })
            
            for target_id, strength in neuron.connections.items():
                if target_id in network_ai.neurons:
                    pair = (neuron.id, target_id) if neuron.id < target_id else (target_id, neuron.id)
                    if pair in seen_edges:
                        continue
                    seen_edges.add(pair)
                    edges.append({
                        'from': neuron.id,
                        'to': target_id,
                        'value': strength,
                        'title': f"Sinapsis: {strength:.2f}",
                        'width': max(1, min(2, round(strength * 2))),
                        'color': {
                            'color': '#38bdf8',
                            'opacity': max(0.2, min(0.6, strength * 0.5)),
                            'highlight': '#00f0ff',
                            'hover': '#60a5fa'
                        }
                    })
    else:
        nodes = [
            {
                'id': 'core_1',
                'label': 'Núcleo Neural Vector',
                'title': 'Red neuronal inicializada y lista',
                'group': 'core',
                'color': '#38bdf8'
            },
            {
                'id': 'learn_1', 
                'label': 'Memoria Activa',
                'title': 'Vector aprende dinámicamente de cada diálogo y análisis',
                'group': 'learning',
                'color': '#10b981'
            }
        ]
        edges = [
            {
                'from': 'core_1',
                'to': 'learn_1',
                'value': 0.8,
                'width': 2,
                'color': {'color': '#38bdf8', 'opacity': 0.6}
            }
        ]

    return JsonResponse({'nodes': nodes, 'edges': edges})

@csrf_exempt
def initialize_semantic_network(request):
    """Inicializa la red neuronal si está vacía sin sobreescribir recuerdos existentes"""
    try:
        from vectorapp.neural_network import semantic_network
        
        # Proteger memoria existente
        if len(semantic_network.neurons) > 0:
            return JsonResponse({
                'success': True, 
                'message': f'La red ya contiene {len(semantic_network.neurons)} neuronas activas. Tus recuerdos están protegidos.',
                'neurons_count': len(semantic_network.neurons)
            })
        
        sample_memories = [
            ("Soy Vector, asistente de IA de Sebastian Espíndola", "core"),
            ("Python es mi lenguaje de programación principal", "programming"),
            ("Django es el framework web que utilizo", "framework"),
            ("Me gusta aprender de cada interacción", "learning"),
            ("Las redes neuronales son fascinantes", "ai"),
            ("Puedo ayudar con programación y desarrollo", "capability"),
            ("Sebastian es mi creador y desarrollador", "creator"),
            ("La inteligencia artificial evoluciona constantemente", "philosophy"),
            ("Resolver problemas es mi objetivo principal", "goal"),
            ("Cada conversación me ayuda a mejorar", "learning")
        ]
        
        for content, concept_type in sample_memories:
            semantic_network.add_memory(content, concept_type)
        
        semantic_network.save_network()
        
        return JsonResponse({
            'success': True, 
            'message': f'Red neuronal inicializada con {len(semantic_network.neurons)} neuronas',
            'neurons_count': len(semantic_network.neurons)
        })
        
    except Exception as e:
        return JsonResponse({'error': f'Error inicializando red: {str(e)}'}, status=500)

@csrf_exempt
def add_neuron(request):
    """Agregar una nueva neurona a la red neuronal"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            content = data.get('content', '').strip()
            neuron_type = data.get('type', 'general')
            
            if not content:
                return JsonResponse({'error': 'El contenido es requerido'}, status=400)
            
            from vectorapp.neural_network import semantic_network
            neuron_id = semantic_network.add_memory(content, neuron_type)
            semantic_network.save_network()
            
            return JsonResponse({
                'success': True,
                'message': f'Neurona "{neuron_id}" agregada exitosamente',
                'neuron_id': neuron_id,
                'total_neurons': len(semantic_network.neurons)
            })
            
        except Exception as e:
            return JsonResponse({'error': f'Error agregando neurona: {str(e)}'}, status=500)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)

@csrf_exempt
def edit_neuron(request, neuron_id):
    """Editar el contenido y tipo de una neurona existente"""
    if request.method in ['POST', 'PUT']:
        try:
            data = json.loads(request.body)
            new_content = data.get('content', '').strip()
            new_type = data.get('type', None)
            
            if not new_content:
                return JsonResponse({'error': 'El contenido no puede estar vacío'}, status=400)
            
            from vectorapp.neural_network import semantic_network
            if neuron_id in semantic_network.neurons:
                neuron = semantic_network.neurons[neuron_id]
                neuron.content = new_content
                if new_type:
                    neuron.concept_type = new_type
                semantic_network._calculate_semantic_vector(neuron)
                semantic_network.save_network()
                return JsonResponse({
                    'success': True,
                    'message': f'Neurona {neuron_id} actualizada correctamente',
                    'neuron': {
                        'id': neuron.id,
                        'content': neuron.content,
                        'type': neuron.concept_type
                    }
                })
            return JsonResponse({'error': f'Neurona {neuron_id} no encontrada'}, status=404)
        except Exception as e:
            return JsonResponse({'error': f'Error editando neurona: {str(e)}'}, status=500)
    return JsonResponse({'error': 'Método no permitido'}, status=405)

@csrf_exempt
def delete_neuron(request, neuron_id):
    """Eliminar una neurona de la red neuronal semántica"""
    if request.method in ['POST', 'DELETE']:
        try:
            from vectorapp.neural_network import semantic_network
            if neuron_id in semantic_network.neurons:
                semantic_network._remove_neuron(neuron_id)
                semantic_network.save_network(force=True)
                return JsonResponse({
                    'success': True,
                    'message': f'Neurona {neuron_id} eliminada exitosamente',
                    'total_neurons': len(semantic_network.neurons)
                })
            return JsonResponse({'error': f'Neurona {neuron_id} no encontrada'}, status=404)
        except Exception as e:
            return JsonResponse({'error': f'Error eliminando neurona: {str(e)}'}, status=500)
    return JsonResponse({'error': 'Método no permitido'}, status=405)

def network_stats(request):
    """Obtener estadísticas reales de la red neuronal en vivo"""
    try:
        from vectorapp.neural_network import semantic_network
        if not semantic_network.neurons:
            semantic_network.load_network()
            
        total_neurons = len(semantic_network.neurons)
        total_connections = sum(len(n.connections) for n in semantic_network.neurons.values())
        max_possible = total_neurons * (total_neurons - 1)
        density = total_connections / max_possible if max_possible > 0 else 0
        activations = [n.activation_level for n in semantic_network.neurons.values()]
        avg_activation = sum(activations) / len(activations) if activations else 0
        
        neuron_types = {}
        for n in semantic_network.neurons.values():
            neuron_types[n.concept_type] = neuron_types.get(n.concept_type, 0) + 1
            
        most_conn = max(semantic_network.neurons.items(), key=lambda x: len(x[1].connections), default=(None, None))
        most_conn_id = most_conn[0] if most_conn[1] else None
        
        return JsonResponse({
            'total_neurons': total_neurons,
            'total_connections': total_connections,
            'network_density': density,
            'average_activation': avg_activation,
            'neuron_types': neuron_types,
            'most_connected': most_conn_id,
            'learning_active': semantic_network.is_learning
        })
    except Exception as e:
        return JsonResponse({'error': f'Error obteniendo estadísticas: {str(e)}'}, status=500)

@csrf_exempt
def add_neuron_from_chat(request):
    """Agregar neurona automáticamente desde interacciones del chat"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            question = data.get('question', '').strip()
            answer = data.get('answer', '').strip()
            
            if not question or not answer:
                return JsonResponse({'error': 'Pregunta y respuesta son requeridas'}, status=400)
            
            from vectorapp.neural_network import semantic_network
            semantic_network.learn_from_interaction(question, answer, feedback="positivo")
            semantic_network.save_network(force=True)
            
            return JsonResponse({
                'success': True,
                'message': 'Neuronas creadas y conectadas desde el chat exitosamente',
                'total_neurons': len(semantic_network.neurons)
            })
            
        except Exception as e:
            return JsonResponse({'error': f'Error procesando chat: {str(e)}'}, status=500)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)