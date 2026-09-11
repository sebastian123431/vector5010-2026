"""
Motor de Razonamiento Cognitivo (Reasoning Engine) para Vector (Fase P1 / P2).
Orquesta el ciclo cognitivo integral:
Planificación (Planner) -> Ejecución Supervisada (Executor) -> Verificación (Verifier) -> Crítica (Critic).
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from .planner import CognitivePlanner, CognitivePlan
from .executor import PlanExecutor
from .critic import CognitiveCritic, CriticEvaluation
from .verifier import CognitiveVerifier
from .tool_adapter import vector_tool_adapter


class ReasoningMode(str, Enum):
    """Modo de operación del motor cognitivo."""
    PLAN_ONLY = "plan_only"          # Genera plan y simulación sin efectos colaterales (dry-run)
    EXECUTE = "execute"              # Ejecuta efectivamente los pasos y herramientas del plan
    PLAN_AND_EXECUTE = "execute"     # Alias semántico para planificar y ejecutar con herramientas


class ReasoningEngine:
    """
    Orquestador cognitivo central que articula la cognición profunda de Vector.
    """

    def __init__(self, tool_runner: Any = "default"):
        self.planner = CognitivePlanner()
        actual_runner = vector_tool_adapter if tool_runner == "default" else tool_runner
        self.executor = PlanExecutor(tool_runner=actual_runner)
        self.critic = CognitiveCritic()
        self.verifier = CognitiveVerifier()

    def reason(
        self,
        query: str,
        interlocutor: str = "Interlocutor",
        mode: ReasoningMode = ReasoningMode.EXECUTE,
        draft_response: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta el ciclo de razonamiento completo sobre una consulta o tarea.
        """
        dry_run = (mode == ReasoningMode.PLAN_ONLY)

        # 1. Planificación adaptativa
        plan = self.planner.create_plan(query, context=context)

        # 2. Verificación de Seguridad preventiva (Pre-Execution Safety)
        pre_safety = self.verifier.verify_safety(query)

        # 3. Ejecución del plan (supervisada o dry-run según el modo)
        if pre_safety["safe"]:
            exec_res = self.executor.execute_plan(plan, dry_run=dry_run)
        else:
            exec_res = {
                "success": False,
                "completed_count": 0,
                "total_steps": len(plan.steps),
                "trace": [{"status": "blocked", "reason": "Bloqueado por verificación de seguridad preventiva."}]
            }

        # 4. Verificación Post-Ejecución (Post-Execution Verification)
        verification_res = self.verifier.verify_execution(plan, exec_res, context=context)

        # 5. Evaluación crítica del borrador de respuesta (si se proporciona)
        critic_res: Optional[CriticEvaluation] = None
        if draft_response:
            critic_res = self.critic.evaluate_response(
                draft_response,
                query=query,
                interlocutor=interlocutor,
                execution=exec_res,
                verification=verification_res
            )

        overall_success = pre_safety["safe"] and exec_res.get("success", False) and verification_res.get("passed", False)

        return {
            "success": overall_success,
            "mode": mode.value if isinstance(mode, ReasoningMode) else str(mode),
            "query": query,
            "interlocutor": interlocutor,
            "pre_safety": pre_safety,
            "safety": pre_safety,             # Compatibilidad retroactiva
            "verification": verification_res, # Verificación post-ejecución real
            "verifier": verification_res,     # Clave separada de pre-safety
            "plan": plan.to_dict(),
            "execution": exec_res,
            "critic": critic_res.to_dict() if critic_res else None,
            "approved": overall_success and (critic_res.passed if critic_res else True)
        }


reasoning_engine = ReasoningEngine()
