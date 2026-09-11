from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime

@dataclass
class Need:
    name: str
    description: str = ""
    priority: float = 1.0
    satisfied: bool = False
    last_satisfied: Optional[str] = None

class NeedsManager:
    """
    Gestor de necesidades cognitivas y operativas internas de Vector (J.A.R.V.I.S.).
    Evalúa continuamente qué subsistema o apoyo cognitivo requiere mayor atención:
    - Búsqueda y actualización de información externa
    - Eficiencia de latencia y caché
    - Consolidación y poda de recuerdos
    - Diagnóstico de código
    - Vigilancia de hardware y procesos
    """
    def __init__(self):
        self.needs: Dict[str, Need] = {
            'search_support': Need(
                name='search_support', 
                description='Búsqueda de información externa actualizada en la web', 
                priority=0.8
            ),
            'system_efficiency': Need(
                name='system_efficiency', 
                description='Optimización de latencia y caché de consultas frecuentes', 
                priority=0.9
            ),
            'memory_consolidation': Need(
                name='memory_consolidation', 
                description='Consolidación sináptica y poda periódica de recuerdos', 
                priority=0.7
            ),
            'code_diagnosis': Need(
                name='code_diagnosis', 
                description='Diagnóstico AST y supervisión técnica de código de proyectos', 
                priority=0.75
            ),
            'surveillance': Need(
                name='surveillance', 
                description='Vigilancia centinela de hardware, red neuronal y procesos', 
                priority=0.85
            )
        }

    def evaluate(self, history: Optional[List[Any]] = None, memory: Optional[List[Any]] = None, query: str = "", complexity: Optional[str] = None) -> List[Need]:
        """
        Evalúa y reordena dinámicamente las necesidades según la consulta, el historial y la complejidad.
        """
        q = (query or "").lower().strip()
        
        # Ajustar por complejidad de consulta
        if complexity == "simple":
            self.needs['system_efficiency'].priority = min(2.5, self.needs['system_efficiency'].priority + 0.3)
        elif complexity in ("complex", "intensive"):
            self.needs['code_diagnosis'].priority = min(2.5, self.needs['code_diagnosis'].priority + 0.3)

        # Ajustar prioridades basadas en intención detectada
        if any(w in q for w in ["busca", "noticias", "google", "web", "internet"]):
            self.needs['search_support'].priority = min(2.5, self.needs['search_support'].priority + 0.5)
            
        if any(w in q for w in ["código", "codigo", "script", "error", "zip", "ast", "proyecto", "bug"]):
            self.needs['code_diagnosis'].priority = min(2.5, self.needs['code_diagnosis'].priority + 0.6)
            
        if any(w in q for w in ["vigila", "supervisa", "estado", "recursos", "cpu", "memoria", "centinela"]):
            self.needs['surveillance'].priority = min(2.5, self.needs['surveillance'].priority + 0.5)
            
        if any(w in q for w in ["recuerdas", "memoria", "aprende", "entrena", "olvida"]):
            self.needs['memory_consolidation'].priority = min(2.5, self.needs['memory_consolidation'].priority + 0.4)

        return sorted(self.needs.values(), key=lambda n: -n.priority)

    def get_top(self) -> Optional[Need]:
        """Obtiene la necesidad cognitiva con mayor prioridad actual."""
        needs = self.evaluate()
        return needs[0] if needs else None

    def satisfy(self, name: str):
        """Marca una necesidad como satisfecha y atenúa temporalmente su prioridad."""
        if name in self.needs:
            self.needs[name].satisfied = True
            self.needs[name].last_satisfied = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.needs[name].priority = max(0.5, self.needs[name].priority * 0.7)

    def get_status(self) -> Dict[str, Any]:
        """Devuelve un informe estructurado de las necesidades del agente."""
        return {
            name: {
                "description": n.description,
                "priority": round(n.priority, 2),
                "satisfied": n.satisfied,
                "last_satisfied": n.last_satisfied
            }
            for name, n in self.needs.items()
        }

# Instancia global del gestor de necesidades
needs_manager = NeedsManager()

