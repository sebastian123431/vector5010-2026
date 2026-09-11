import numpy as np
import json
import pickle
import os
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional
from collections import defaultdict
from sklearn.metrics.pairwise import cosine_similarity
import threading
import time

class SemanticNeuron:
    """
    Representa una neurona semántica que almacena un concepto/recuerdo específico.
    """
    def __init__(self, neuron_id: str, content: str, concept_type: str = "general"):
        self.id = neuron_id
        self.content = content
        self.concept_type = concept_type  # 'memory', 'pattern', 'fact', 'learning'
        self.activation_level = 0.0
        self.creation_time = datetime.now()
        self.last_activation = datetime.now()
        self.activation_count = 0
        self.importance_score = 1.0
        self.connections = {}  # {neuron_id: connection_strength}
        self.semantic_vector = None
        self.learning_rate = 0.1
        self.decay_rate = 0.01
        
    def activate(self, stimulus_strength: float = 1.0):
        """Activa la neurona con un estímulo dado."""
        self.activation_level = min(1.0, self.activation_level + stimulus_strength)
        self.last_activation = datetime.now()
        self.activation_count += 1
        self.importance_score += 0.1 * stimulus_strength
        
    def decay(self):
        """Reduce gradualmente la activación de la neurona."""
        self.activation_level *= (1 - self.decay_rate)
        if self.activation_level < 0.01:
            self.activation_level = 0.0
            
    def connect_to(self, other_neuron_id: str, strength: float):
        """Establece una conexión con otra neurona."""
        self.connections[other_neuron_id] = strength
        
    def strengthen_connection(self, other_neuron_id: str, amount: float = 0.1):
        """Fortalece la conexión con otra neurona."""
        if other_neuron_id in self.connections:
            self.connections[other_neuron_id] = min(1.0, 
                self.connections[other_neuron_id] + amount)
        else:
            self.connections[other_neuron_id] = amount
            
    def weaken_connection(self, other_neuron_id: str, amount: float = 0.05):
        """Debilita la conexión con otra neurona."""
        if other_neuron_id in self.connections:
            self.connections[other_neuron_id] = max(0.0, 
                self.connections[other_neuron_id] - amount)
            if self.connections[other_neuron_id] < 0.1:
                del self.connections[other_neuron_id]
                
    def get_related_neurons(self, threshold: float = 0.3) -> List[str]:
        """Obtiene neuronas relacionadas por encima de un umbral."""
        return [nid for nid, strength in self.connections.items() 
                if strength >= threshold]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte la neurona a diccionario para serialización."""
        d: Dict[str, Any] = {
            'id': self.id,
            'content': self.content,
            'concept_type': self.concept_type,
            'activation_level': self.activation_level,
            'creation_time': self.creation_time.isoformat(),
            'last_activation': self.last_activation.isoformat(),
            'activation_count': self.activation_count,
            'importance_score': self.importance_score,
            'connections': self.connections,
            'learning_rate': self.learning_rate,
            'decay_rate': self.decay_rate
        }
        if self.semantic_vector is not None:
            d['semantic_vector'] = self.semantic_vector.tolist() if isinstance(self.semantic_vector, np.ndarray) else list(self.semantic_vector)
        return d
    
    @classmethod
    def from_dict(cls, data: dict):
        """Crea una neurona desde un diccionario."""
        neuron = cls(data['id'], data['content'], data.get('concept_type', 'general'))
        neuron.activation_level = data.get('activation_level', 0.0)
        try:
            neuron.creation_time = datetime.fromisoformat(data['creation_time'])
            neuron.last_activation = datetime.fromisoformat(data['last_activation'])
        except Exception:
            pass
        neuron.activation_count = data.get('activation_count', 0)
        neuron.importance_score = data.get('importance_score', 1.0)
        neuron.connections = data.get('connections', {})
        neuron.learning_rate = data.get('learning_rate', 0.1)
        neuron.decay_rate = data.get('decay_rate', 0.01)
        if 'semantic_vector' in data and data['semantic_vector']:
            neuron.semantic_vector = np.array(data['semantic_vector'], dtype=np.float32)
        return neuron


class AdaptiveSemanticNetwork:
    """
    Red neuronal semántica autónoma de Vector impulsada por Nomic-Embed en GPU.
    Crece, conecta conceptos afines por similitud semántica densa (768-dim) y se adapta dinámicamente.
    """
    def __init__(self, network_path: str = "semantic_network.pkl"):
        self.neurons = {}  # {neuron_id: SemanticNeuron}
        self.network_path = network_path
        self.lock = threading.RLock()
        self.learning_threshold = 0.65
        self.connection_threshold = 0.50
        self.max_neurons = 1200
        self.pruning_threshold = 0.1
        self.is_learning = False
        self.learning_thread = None
        self._dirty = False
        self._matrix = None
        self._matrix_ids = []
        self._matrix_dirty = True
        
        # Cargar red existente si existe
        self.load_network()
        
        # Inicializar con neurona base si está vacía
        if not self.neurons:
            self._create_initial_neuron()
            
    def _rebuild_matrix_if_needed(self):
        """Construye una matriz densa NumPy (N x 768) normalizada para búsquedas vectorizadas ultra-rápidas."""
        if not self._matrix_dirty and self._matrix is not None:
            return
            
        valid_ids = []
        vectors = []
        for nid, neuron in self.neurons.items():
            if neuron.semantic_vector is not None and len(neuron.semantic_vector) == 768:
                valid_ids.append(nid)
                vectors.append(neuron.semantic_vector)
                
        if vectors:
            mat = np.array(vectors, dtype=np.float32)
            norms = np.linalg.norm(mat, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            self._matrix = mat / norms
            self._matrix_ids = valid_ids
        else:
            self._matrix = None
            self._matrix_ids = []
        self._matrix_dirty = False
            
    def _create_initial_neuron(self):
        """Crea la primera neurona de la red."""
        with self.lock:
            initial_neuron = SemanticNeuron(
                neuron_id="neuron_0",
                content="Soy Vector, asistente inteligente y copiloto técnico de Sebastian Espíndola.",
                concept_type="core"
            )
            self._calculate_semantic_vector(initial_neuron)
            self.neurons[initial_neuron.id] = initial_neuron
            self._dirty = True
            self._matrix_dirty = True
            print(f"[Vector] Neurona inicial creada: {initial_neuron.id}")
        
    def add_memory(self, content: str, memory_type: str = "general", 
                   related_content: Optional[str] = None) -> str:
        """
        Añade o refuerza un concepto en la red neuronal semántica.
        Aplica deduplicación y consolidación hebbiana: estímulos idénticos o afines (>= 0.90)
        refuerzan la sinapsis y activación de la neurona existente en lugar de duplicarla.
        """
        cleaned_content = content.strip()
        lower_content = cleaned_content.lower()
        
        with self.lock:
            # 1. Chequeo rápido de contenido exacto existente
            for nid, neuron in self.neurons.items():
                if neuron.content.strip().lower() == lower_content:
                    neuron.activate(1.0)
                    neuron.importance_score += 0.2
                    neuron.last_activation = datetime.now()
                    self._propagate_activation(nid)
                    self._dirty = True
                    return nid
            
            # 2. Crear neurona temporal y calcular vector semántico real (Nomic 768 dims en GPU)
            temp_neuron = SemanticNeuron("temp", cleaned_content, memory_type)
            self._calculate_semantic_vector(temp_neuron)
            
            # 3. Buscar afinidades semánticas existentes
            related_neurons = self._find_related_neurons(temp_neuron)
            
            # 4. Consolidación Hebbiana si existe una neurona sumamente afín (similitud >= 0.88)
            if related_neurons and related_neurons[0][1] >= 0.88:
                best_id, sim = related_neurons[0]
                existing = self.neurons[best_id]
                existing.activate(1.0)
                existing.importance_score += 0.2
                existing.last_activation = datetime.now()
                # Fortalecer sinapsis con las demás neuronas afines
                for related_id, rel_sim in related_neurons[1:]:
                    if rel_sim > self.connection_threshold:
                        existing.strengthen_connection(related_id, 0.15)
                        if related_id in self.neurons:
                            self.neurons[related_id].strengthen_connection(best_id, 0.15)
                self._propagate_activation(best_id)
                self._dirty = True
                return best_id
            
            # 5. Generar ID único seguro (sin colisiones aun con podas o fusiones)
            max_idx = -1
            for k in self.neurons.keys():
                if k.startswith("neuron_"):
                    suffix = k[7:]
                    if suffix.isdigit():
                        max_idx = max(max_idx, int(suffix))
            neuron_id = f"neuron_{max_idx + 1}"
            
            # Crear nueva neurona definitiva
            new_neuron = SemanticNeuron(neuron_id, cleaned_content, memory_type)
            new_neuron.semantic_vector = temp_neuron.semantic_vector
            
            # Establecer conexiones sinápticas bidireccionales
            for related_id, similarity in related_neurons:
                if similarity > self.connection_threshold:
                    new_neuron.connect_to(related_id, similarity)
                    if related_id in self.neurons:
                        self.neurons[related_id].connect_to(neuron_id, similarity)
                    
            # Añadir a la red
            self.neurons[neuron_id] = new_neuron
            new_neuron.activate(1.0)
            self._propagate_activation(neuron_id)
            
            self._dirty = True
            self._matrix_dirty = True
            return neuron_id
        
    def _calculate_semantic_vector(self, neuron: SemanticNeuron):
        """Calcula el vector semántico neuronal usando Nomic-Embed en GPU CUDA."""
        try:
            from .embeddings import _EMBEDDINGS
            vec = _EMBEDDINGS.embed_query(neuron.content)
            arr = np.array(vec, dtype=np.float32)
            norm = np.linalg.norm(arr)
            neuron.semantic_vector = (arr / norm) if norm > 1e-6 else arr
        except Exception:
            if neuron.semantic_vector is None:
                neuron.semantic_vector = np.zeros(768, dtype=np.float32)
            
    def _find_related_neurons(self, new_neuron: SemanticNeuron) -> List[Tuple[str, float]]:
        """Encuentra neuronas relacionadas semánticamente mediante proyección matricial NumPy."""
        if new_neuron.semantic_vector is None or len(new_neuron.semantic_vector) != 768:
            return []
            
        self._rebuild_matrix_if_needed()
        if self._matrix is None or len(self._matrix_ids) == 0:
            return []
            
        v1 = new_neuron.semantic_vector
        norm = np.linalg.norm(v1)
        if norm > 1e-6:
            v1 = v1 / norm
            
        sims = np.dot(self._matrix, v1)
        
        related = []
        for idx, sim in enumerate(sims):
            nid = self._matrix_ids[idx]
            if nid != new_neuron.id and sim > self.connection_threshold:
                related.append((nid, float(sim)))
                    
        related.sort(key=lambda x: x[1], reverse=True)
        return related[:10]
        
    def _propagate_activation(self, source_neuron_id: str, max_depth: int = 3):
        """
        Propaga la activación a través de la red sináptica mediante BFS iterativo con anti-ciclos.
        Garantiza que cada neurona se procese a lo sumo una vez por onda de propagación,
        eliminando rebotes infinitos en sinapsis bidireccionales y reduciendo drásticamente el consumo de CPU.
        """
        source_neuron = self.neurons.get(source_neuron_id)
        if not source_neuron or source_neuron.activation_level < 0.1:
            return

        from collections import deque
        queue = deque([(source_neuron_id, 0)])
        visited = {source_neuron_id}

        while queue:
            current_id, depth = queue.popleft()
            if depth >= max_depth:
                continue

            current_neuron = self.neurons.get(current_id)
            if not current_neuron:
                continue

            curr_act = current_neuron.activation_level
            for connected_id, strength in current_neuron.connections.items():
                if connected_id not in visited and connected_id in self.neurons:
                    activation_amount = curr_act * strength * 0.5
                    if activation_amount > 0.1:
                        connected_neuron = self.neurons[connected_id]
                        connected_neuron.activate(activation_amount)
                        visited.add(connected_id)
                        queue.append((connected_id, depth + 1))
                    
    def query_network(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """
        Consulta la red neuronal mediante búsqueda semántica densa de Nomic.
        """
        with self.lock:
            # Primero buscar coincidencias exactas (subcadena)
            lower_q = query.lower()
            exact = [(nid, 1.0) for nid, neuron in self.neurons.items() if lower_q in neuron.content.lower()]
            if exact:
                for nid, _ in exact[:top_k]:
                    if nid in self.neurons:
                        self.neurons[nid].activate(0.8)
                return exact[:top_k]
                
            # Proyección matricial densa
            related = self.recall(query, top_k=top_k)
            for neuron_id, similarity in related:
                if neuron_id in self.neurons:
                    self.neurons[neuron_id].activate(similarity)
                
            return related
        
    def learn_from_interaction(self, question: str, answer: str, 
                             feedback: Optional[str] = None):
        """
        Aprende de una interacción específica.
        """
        # Añadir pregunta como neurona
        q_neuron_id = self.add_memory(question, "question")
        
        # Añadir respuesta como neurona
        a_neuron_id = self.add_memory(answer, "answer")
        
        # Conectar pregunta y respuesta
        self.neurons[q_neuron_id].connect_to(a_neuron_id, 0.9)
        self.neurons[a_neuron_id].connect_to(q_neuron_id, 0.9)
        self._dirty = True
        
        # Procesar feedback si existe
        if feedback:
            if any(word in feedback.lower() for word in ['bien', 'correcto', 'perfecto', 'gracias']):
                # Feedback positivo: fortalecer conexiones
                self._strengthen_pathway(q_neuron_id, a_neuron_id)
            elif any(word in feedback.lower() for word in ['mal', 'error', 'incorrecto']):
                # Feedback negativo: debilitar conexiones
                self._weaken_pathway(q_neuron_id, a_neuron_id)
                
    def _strengthen_pathway(self, start_id: str, end_id: str):
        """Fortalece el camino entre dos neuronas."""
        if start_id in self.neurons and end_id in self.neurons:
            self.neurons[start_id].strengthen_connection(end_id, 0.2)
            self.neurons[end_id].strengthen_connection(start_id, 0.2)
            
            # Fortalecer conexiones indirectas
            for intermediate_id in self.neurons[start_id].get_related_neurons(0.5):
                if intermediate_id in self.neurons[end_id].connections:
                    self.neurons[intermediate_id].strengthen_connection(end_id, 0.1)
            self._dirty = True
                    
    def _weaken_pathway(self, start_id: str, end_id: str):
        """Debilita el camino entre dos neuronas."""
        if start_id in self.neurons and end_id in self.neurons:
            self.neurons[start_id].weaken_connection(end_id, 0.1)
            self.neurons[end_id].weaken_connection(start_id, 0.1)
            self._dirty = True
            
    def get_network_state(self) -> dict:
        """Obtiene el estado actual de la red."""
        total_neurons = len(self.neurons)
        total_connections = sum(len(n.connections) for n in self.neurons.values())
        avg_activation = np.mean([n.activation_level for n in self.neurons.values()])
        
        neuron_types = defaultdict(int)
        for neuron in self.neurons.values():
            neuron_types[neuron.concept_type] += 1
            
        return {
            'total_neurons': total_neurons,
            'total_connections': total_connections,
            'average_activation': avg_activation,
            'neuron_types': dict(neuron_types),
            'network_density': total_connections / (total_neurons * (total_neurons - 1)) if total_neurons > 1 else 0
        }
        
    def prune_network(self):
        """
        Poda la red eliminando neuronas poco importantes.
        """
        if len(self.neurons) <= 10:  # Mantener mínimo de neuronas
            return
            
        # Identificar neuronas a eliminar
        to_remove = []
        for neuron_id, neuron in self.neurons.items():
            if (neuron.importance_score < self.pruning_threshold and 
                neuron.activation_count < 5 and
                len(neuron.connections) < 2):
                to_remove.append(neuron_id)
                
        # Eliminar neuronas
        for neuron_id in to_remove:
            self._remove_neuron(neuron_id)
            
        if to_remove:
            self._dirty = True
            self._matrix_dirty = True
            print(f"[Vector] Red podada: {len(to_remove)} neuronas eliminadas")
        
    def _remove_neuron(self, neuron_id: str):
        """Elimina una neurona de la red."""
        if neuron_id not in self.neurons:
            return
            
        # Eliminar conexiones hacia esta neurona
        for other_neuron in self.neurons.values():
            if neuron_id in other_neuron.connections:
                del other_neuron.connections[neuron_id]
                
        # Eliminar la neurona
        del self.neurons[neuron_id]
        self._dirty = True
        self._matrix_dirty = True
        
    def start_continuous_learning(self):
        """Inicia el aprendizaje continuo en segundo plano."""
        if not self.is_learning:
            self.is_learning = True
            print("[Vector] Aprendizaje continuo iniciado")
            self.learning_thread = threading.Thread(target=self._learning_loop)
            self.learning_thread.daemon = True
            self.learning_thread.start()
            
    def stop_continuous_learning(self):
        """Detiene el aprendizaje continuo."""
        self.is_learning = False
        if self.learning_thread:
            self.learning_thread.join()
        print("[Vector] Aprendizaje continuo detenido")
        
    def _learning_loop(self):
        """Loop principal de aprendizaje continuo."""
        while self.is_learning:
            try:
                any_decay = False
                # Decay de activación
                for neuron in self.neurons.values():
                    old_act = neuron.activation_level
                    neuron.decay()
                    if abs(old_act - neuron.activation_level) > 0.05:
                        any_decay = True
                        
                if any_decay:
                    self._dirty = True
                    
                # Poda periódica
                if len(self.neurons) > self.max_neurons:
                    self.prune_network()
                    
                # Guardar estado sólo si hay modificaciones
                self.save_network(force=False)
                
                # Esperar antes del siguiente ciclo
                time.sleep(60)  # Ciclo cada minuto
                
            except Exception as e:
                print(f"Error en loop de aprendizaje: {e}")
                
    def save_network(self, force: bool = False):
        """Guarda la red neuronal en disco de forma atómica (JSON estructurado y PKL). Omite si no hay cambios."""
        with self.lock:
            if not force and not self._dirty:
                return
                
            try:
                network_data = {
                    'neurons': {nid: neuron.to_dict() for nid, neuron in self.neurons.items()},
                    'metadata': {
                        'creation_time': datetime.now().isoformat(),
                        'total_neurons': len(self.neurons),
                        'embedding_engine': 'nomic-embed-v1.5-cuda'
                    }
                }
                # 1. Guardar en JSON compacto de forma atómica
                json_path = self.network_path.replace('.pkl', '.json')
                json_tmp = f"{json_path}.tmp"
                try:
                    with open(json_tmp, 'w', encoding='utf-8') as f:
                        json.dump(network_data, f, ensure_ascii=False)
                    os.replace(json_tmp, json_path)
                except Exception as je:
                    print(f"Aviso guardando JSON de red neuronal: {je}")
                    if os.path.exists(json_tmp):
                        try:
                            os.remove(json_tmp)
                        except OSError:
                            pass

                # 2. Guardar en Pickle binario de forma atómica
                pkl_tmp = f"{self.network_path}.tmp"
                try:
                    with open(pkl_tmp, 'wb') as f:
                        pickle.dump(network_data, f)
                    os.replace(pkl_tmp, self.network_path)
                except Exception as pe:
                    print(f"Aviso guardando PKL de red neuronal: {pe}")
                    if os.path.exists(pkl_tmp):
                        try:
                            os.remove(pkl_tmp)
                        except OSError:
                            pass
                    
                self._dirty = False
            except Exception as e:
                print(f"Error guardando red neuronal: {e}")
                
    def load_network(self):
        """Carga la red neuronal desde disco prefiriendo JSON estructurado."""
        with self.lock:
            loaded = False
            json_path = self.network_path.replace('.pkl', '.json')
            
            if os.path.exists(json_path):
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        network_data = json.load(f)
                    for nid, neuron_data in network_data.get('neurons', {}).items():
                        self.neurons[nid] = SemanticNeuron.from_dict(neuron_data)
                    print(f"[Vector] Red neuronal cargada desde JSON: {len(self.neurons)} neuronas")
                    loaded = True
                except Exception as je:
                    print(f"Aviso cargando red desde JSON: {je}")

            if not loaded and os.path.exists(self.network_path):
                try:
                    with open(self.network_path, 'rb') as f:
                        network_data = pickle.load(f)
                    for nid, neuron_data in network_data.get('neurons', {}).items():
                        self.neurons[nid] = SemanticNeuron.from_dict(neuron_data)
                    print(f"[Vector] Red neuronal cargada desde PKL: {len(self.neurons)} neuronas")
                    loaded = True
                except Exception as pe:
                    print(f"Error cargando red neuronal PKL: {pe}")
                    
            self._matrix_dirty = True
            self._dirty = False
            
    def get_insights(self) -> dict:
        """Obtiene insights sobre la red neuronal."""
        if not self.neurons:
            return {}
            
        # Neurona más activa
        most_active = max(self.neurons.values(), key=lambda n: n.activation_level)
        
        # Neurona más conectada
        most_connected = max(self.neurons.values(), key=lambda n: len(n.connections))
        
        # Conceptos más importantes
        most_important = sorted(self.neurons.values(), 
                              key=lambda n: n.importance_score, reverse=True)[:5]
        
        return {
            'most_active_neuron': {
                'id': most_active.id,
                'content': most_active.content[:100] + '...',
                'activation': most_active.activation_level
            },
            'most_connected_neuron': {
                'id': most_connected.id,
                'content': most_connected.content[:100] + '...',
                'connections': len(most_connected.connections)
            },
            'most_important_concepts': [
                {
                    'id': n.id,
                    'content': n.content[:100] + '...',
                    'importance': n.importance_score
                }
                for n in most_important
            ]
        }
        
    def get_pattern_insights(self, pattern_type: str = "general") -> List[Dict[str, Any]]:
        """
        Obtiene insights sobre patrones específicos en la red neuronal.
        """
        insights: List[Dict[str, Any]] = []
        
        try:
            # Filtrar neuronas por tipo de patrón
            pattern_neurons = [
                neuron for neuron in self.neurons.values()
                if pattern_type in neuron.concept_type or pattern_type == "general"
            ]
            
            if not pattern_neurons:
                return [{"insight": f"No se encontraron patrones para '{pattern_type}'"}]
            
            # Analizar frecuencia de activación
            total_activations = sum(n.activation_count for n in pattern_neurons)
            avg_activation = total_activations / len(pattern_neurons) if pattern_neurons else 0
            
            insights.append({
                "type": "activation_pattern",
                "insight": f"Patrón de activación: {total_activations} activaciones totales, promedio {avg_activation:.2f} por neurona",
                "data": {
                    "total_activations": total_activations,
                    "average_activation": avg_activation,
                    "neuron_count": len(pattern_neurons)
                }
            })
            
            # Analizar conexiones más fuertes
            strongest_connections = []
            for neuron in pattern_neurons:
                for connected_id, strength in neuron.connections.items():
                    if strength > 0.5:  # Conexiones fuertes
                        strongest_connections.append({
                            "from": neuron.id,
                            "to": connected_id,
                            "strength": strength
                        })
            
            if strongest_connections:
                insights.append({
                    "type": "connection_strength",
                    "insight": f"Se encontraron {len(strongest_connections)} conexiones fuertes en el patrón '{pattern_type}'",
                    "data": strongest_connections[:5]  # Top 5
                })
            
            # Analizar tendencias temporales
            recent_neurons = [n for n in pattern_neurons if (datetime.now() - n.creation_time).days <= 7]
            if recent_neurons:
                insights.append({
                    "type": "temporal_trend",
                    "insight": f"{len(recent_neurons)} neuronas del patrón '{pattern_type}' fueron creadas en los últimos 7 días",
                    "data": {
                        "recent_count": len(recent_neurons),
                        "total_count": len(pattern_neurons),
                        "growth_rate": len(recent_neurons) / len(pattern_neurons) * 100
                    }
                })
            
            # Identificar clusters semánticos
            if len(pattern_neurons) > 3:
                semantic_clusters = self._identify_semantic_clusters(pattern_neurons)
                if semantic_clusters:
                    insights.append({
                        "type": "semantic_clustering",
                        "insight": f"Se identificaron {len(semantic_clusters)} clusters semánticos en el patrón '{pattern_type}'",
                        "data": semantic_clusters
                    })
            
            return insights if insights else [{"insight": "No se encontraron patrones significativos"}]
            
        except Exception as e:
            return [{"insight": f"Error analizando patrones: {str(e)}"}]

    def _identify_semantic_clusters(self, neurons: List[SemanticNeuron]) -> List[Dict[str, Any]]:
        """
        Identifica clusters semánticos en un conjunto de neuronas.
        """
        try:
            # Crear vectores semánticos si no existen
            for neuron in neurons:
                if neuron.semantic_vector is None:
                    self._calculate_semantic_vector(neuron)
            
            # Calcular similitudes
            vectors = np.array([n.semantic_vector for n in neurons])
            similarities = cosine_similarity(vectors)
            
            # Identificar grupos con alta similitud
            clusters = []
            threshold = 0.7
            
            for i, neuron in enumerate(neurons):
                similar_indices = np.where(similarities[i] > threshold)[0]
                if len(similar_indices) > 1:  # Más de una neurona similar
                    cluster = {
                        "center_neuron": neuron.id,
                        "similar_neurons": [neurons[j].id for j in similar_indices if j != i],
                        "similarity_scores": [similarities[i][j] for j in similar_indices if j != i],
                        "cluster_size": len(similar_indices)
                    }
                    clusters.append(cluster)
            
            return clusters[:3]  # Top 3 clusters
            
        except Exception as e:
            print(f"Error identificando clusters: {e}")
            return []

    def recall(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """
        Retorna las neuronas cuya semántica está más relacionada con la consulta
        usando proyección vectorial densa en matriz NumPy (tiempo sub-milisegundo).
        """
        with self.lock:
            if not self.neurons:
                return []
                
            temp_neuron = SemanticNeuron("temp_recall", query)
            self._calculate_semantic_vector(temp_neuron)
            if temp_neuron.semantic_vector is None or len(temp_neuron.semantic_vector) != 768:
                return []
                
            self._rebuild_matrix_if_needed()
            if self._matrix is None or len(self._matrix_ids) == 0:
                return []
                
            q_vec = temp_neuron.semantic_vector
            norm = np.linalg.norm(q_vec)
            if norm > 1e-6:
                q_vec = q_vec / norm
                
            sims = np.dot(self._matrix, q_vec)
            
            # Obtener top_k índices
            if len(sims) <= top_k:
                top_indices = np.argsort(sims)[::-1]
            else:
                top_indices = np.argpartition(sims, -top_k)[-top_k:]
                top_indices = top_indices[np.argsort(sims[top_indices])[::-1]]
                
            results = [(self._matrix_ids[idx], float(sims[idx])) for idx in top_indices]
            return results

# Instancia global de la red neuronal
semantic_network = AdaptiveSemanticNetwork()
