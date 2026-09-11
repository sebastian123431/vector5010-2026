"""
Configuración y utilidades para la red neuronal semántica.
"""

import os
from django.conf import settings

class NeuralNetworkConfig:
    """
    Configuración de la red neuronal semántica.
    """
    
    # Rutas de archivos
    NETWORK_PATH = os.path.join(settings.BASE_DIR, 'vectorapp', 'data', 'semantic_network.pkl')
    NETWORK_BACKUP_PATH = os.path.join(settings.BASE_DIR, 'vectorapp', 'data', 'semantic_network_backup.pkl')
    
    # Parámetros de la red
    MAX_NEURONS = 2000
    LEARNING_THRESHOLD = 0.6
    CONNECTION_THRESHOLD = 0.4
    PRUNING_THRESHOLD = 0.1
    
    # Parámetros de aprendizaje
    LEARNING_RATE = 0.1
    DECAY_RATE = 0.01
    ACTIVATION_BOOST = 1.0
    CONNECTION_STRENGTH_BOOST = 0.2
    
    # Parámetros de consulta
    DEFAULT_TOP_K = 5
    MIN_SIMILARITY = 0.3
    MAX_PROPAGATION_DEPTH = 3
    
    # Ciclos de mantenimiento
    LEARNING_CYCLE_SECONDS = 60
    PRUNING_CYCLE_MINUTES = 30
    BACKUP_CYCLE_HOURS = 6
    
    # Temas importantes para Sebastian
    SEBASTIAN_TOPICS = [
        'programación', 'python', 'django', 'desarrollo web',
        'inteligencia artificial', 'machine learning', 'deep learning',
        'bases de datos', 'apis', 'frontend', 'backend',
        'proyectos', 'código', 'debugging', 'optimización',
        'sebastián espíndola', 'sebastian', 'creador',
        'nicolás vicentelo', 'nicolas', 'amigo'
    ]
    
    # Tipos de conceptos
    CONCEPT_TYPES = {
        'core': 'Conceptos fundamentales del sistema',
        'memory': 'Recuerdos específicos',
        'pattern': 'Patrones de comportamiento',
        'learning': 'Aprendizajes específicos',
        'question': 'Preguntas del usuario',
        'answer': 'Respuestas del sistema',
        'concept': 'Conceptos generales',
        'fact': 'Hechos importantes',
        'emotion': 'Estados emocionales',
        'goal': 'Objetivos y metas',
        'skill': 'Habilidades aprendidas'
    }
    
    @classmethod
    def get_network_path(cls):
        """Obtiene la ruta del archivo de la red neuronal."""
        # Crear directorio si no existe
        os.makedirs(os.path.dirname(cls.NETWORK_PATH), exist_ok=True)
        return cls.NETWORK_PATH
    
    @classmethod
    def get_backup_path(cls):
        """Obtiene la ruta del archivo de respaldo."""
        os.makedirs(os.path.dirname(cls.NETWORK_BACKUP_PATH), exist_ok=True)
        return cls.NETWORK_BACKUP_PATH
    
    @classmethod
    def is_important_topic(cls, text):
        """Verifica si un texto contiene temas importantes para Sebastian."""
        text_lower = text.lower()
        return any(topic in text_lower for topic in cls.SEBASTIAN_TOPICS)
    
    @classmethod
    def get_topic_importance(cls, text):
        """Calcula la importancia de un texto basado en temas relevantes."""
        text_lower = text.lower()
        importance = 0.0
        
        for topic in cls.SEBASTIAN_TOPICS:
            if topic in text_lower:
                importance += 0.1
                
        return min(1.0, importance)

class NeuralNetworkMetrics:
    """
    Métricas y estadísticas de la red neuronal.
    """
    
    def __init__(self, network):
        self.network = network
        
    def get_network_health(self):
        """Evalúa la salud general de la red neuronal."""
        if not self.network.neurons:
            return {"status": "empty", "health_score": 0.0}
            
        total_neurons = len(self.network.neurons)
        total_connections = sum(len(n.connections) for n in self.network.neurons.values())
        avg_activation = sum(n.activation_level for n in self.network.neurons.values()) / total_neurons
        
        # Calcular puntuación de salud
        health_score = 0.0
        
        # Diversidad de tipos de neuronas
        concept_types = set(n.concept_type for n in self.network.neurons.values())
        health_score += len(concept_types) * 0.1
        
        # Densidad de conexiones
        max_connections = total_neurons * (total_neurons - 1)
        connection_density = total_connections / max_connections if max_connections > 0 else 0
        health_score += connection_density * 0.3
        
        # Nivel de activación promedio
        health_score += avg_activation * 0.2
        
        # Penalizar redes demasiado grandes o pequeñas
        if total_neurons < 10:
            health_score *= 0.5
        elif total_neurons > 1500:
            health_score *= 0.8
            
        health_score = min(1.0, health_score)
        
        status = "excellent" if health_score > 0.8 else \
                "good" if health_score > 0.6 else \
                "fair" if health_score > 0.4 else \
                "poor"
        
        return {
            "status": status,
            "health_score": health_score,
            "total_neurons": total_neurons,
            "total_connections": total_connections,
            "connection_density": connection_density,
            "avg_activation": avg_activation,
            "concept_types": list(concept_types)
        }
    
    def get_learning_statistics(self):
        """Obtiene estadísticas de aprendizaje."""
        if not self.network.neurons:
            return {}
            
        # Neuronas por tipo
        type_counts = {}
        for neuron in self.network.neurons.values():
            type_counts[neuron.concept_type] = type_counts.get(neuron.concept_type, 0) + 1
        
        # Neuronas más activas
        most_active = sorted(
            self.network.neurons.values(),
            key=lambda n: n.activation_level,
            reverse=True
        )[:5]
        
        # Neuronas más conectadas
        most_connected = sorted(
            self.network.neurons.values(),
            key=lambda n: len(n.connections),
            reverse=True
        )[:5]
        
        # Neuronas más importantes
        most_important = sorted(
            self.network.neurons.values(),
            key=lambda n: n.importance_score,
            reverse=True
        )[:5]
        
        return {
            "type_distribution": type_counts,
            "most_active": [
                {
                    "id": n.id,
                    "content": n.content[:100] + "..." if len(n.content) > 100 else n.content,
                    "activation": n.activation_level,
                    "type": n.concept_type
                }
                for n in most_active
            ],
            "most_connected": [
                {
                    "id": n.id,
                    "content": n.content[:100] + "..." if len(n.content) > 100 else n.content,
                    "connections": len(n.connections),
                    "type": n.concept_type
                }
                for n in most_connected
            ],
            "most_important": [
                {
                    "id": n.id,
                    "content": n.content[:100] + "..." if len(n.content) > 100 else n.content,
                    "importance": n.importance_score,
                    "type": n.concept_type
                }
                for n in most_important
            ]
        }
    
    def get_sebastian_focused_stats(self):
        """Estadísticas enfocadas en Sebastian y sus intereses."""
        sebastian_neurons = []
        
        for neuron in self.network.neurons.values():
            if NeuralNetworkConfig.is_important_topic(neuron.content):
                sebastian_neurons.append(neuron)
        
        if not sebastian_neurons:
            return {"message": "No hay neuronas específicas para Sebastian aún"}
        
        # Temas más frecuentes
        topic_counts = {}
        for topic in NeuralNetworkConfig.SEBASTIAN_TOPICS:
            count = sum(1 for n in sebastian_neurons if topic in n.content.lower())
            if count > 0:
                topic_counts[topic] = count
        
        # Ordenar por frecuencia
        sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "total_sebastian_neurons": len(sebastian_neurons),
            "top_topics": sorted_topics[:10],
            "most_active_sebastian_neurons": [
                {
                    "id": n.id,
                    "content": n.content[:100] + "...",
                    "activation": n.activation_level,
                    "importance": n.importance_score
                }
                for n in sorted(sebastian_neurons, key=lambda n: n.activation_level, reverse=True)[:5]
            ]
        }
