"""
Motor de Razonamiento Cognitivo (Reasoning Engine) para Vector (Fase P2).
Orquesta el ciclo cognitivo integral:
Planificación (Planner) -> Ejecución Supervisada (Executor) -> Verificación (Verifier) -> Crítica (Critic).
"""

from typing import Dict, Any, List, Optional
from .planner import CognitivePlanner, CognitivePlan
from .executor import PlanExecutor
from .critic import CognitiveCritic, CriticEvaluation
from .verifier import CognitiveVerifier


class ReasoningEngine:
    """
    Orquestador cognitivo central que articula la cognición profunda de Vector.
    """

    def __init__(self):
        self.planner = CognitivePlanner()
        self.executor = PlanExecutor()
        self.critic = CognitiveCritic()
        self.verifier = CognitiveVerifier()

    def reason(
        self,
        query: str,
        interlocutor: str = "Sebastian",
        draft_response: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta el ciclo de razonamiento completo sobre una consulta o tarea.
        """
        # 1. Planificación
        plan = self.planner.create_plan(query, context=context)

        # 2. Verificación de Seguridad
        safety_check = self.verifier.verify_safety(query)

        # 3. Ejecución del plan (dry-run o contextual)
        exec_res = self.executor.execute_plan(plan, dry_run=True)

        # 4. Evaluación crítica del borrador de respuesta (si se proporciona)
        critic_res: Optional[CriticEvaluation] = None
        if draft_response:
            critic_res = self.critic.evaluate_response(
                draft_response,
                query=query,
                interlocutor=interlocutor
            )

        return {
            "success": safety_check["safe"],
            "query": query,
            "interlocutor": interlocutor,
            "safety": safety_check,
            "plan": plan.to_dict(),
            "execution": exec_res,
            "critic": critic_res.to_dict() if critic_res else None,
            "approved": safety_check["safe"] and (critic_res.passed if critic_res else True)
        }


reasoning_engine = ReasoningEngine()
