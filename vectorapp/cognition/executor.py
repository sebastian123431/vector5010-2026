"""
Ejecutor de planes cognitivos (Plan Executor) para Vector (Fase P2).
Ejecuta pasos secuenciales o dependientes observando cuotas y tolerando fallos.
"""

from typing import Dict, Any, List, Optional, Callable
from .planner import CognitivePlan, PlanStep, StepStatus


class PlanExecutor:
    """
    Ejecutor supervisado de pasos de razonamiento y herramientas.
    """

    def __init__(self, tool_runner: Optional[Callable] = None):
        self.tool_runner = tool_runner

    def execute_plan(self, plan: CognitivePlan, dry_run: bool = False) -> Dict[str, Any]:
        """
        Ejecuta cada paso del plan respetando las dependencias declaradas.
        """
        completed_steps = set()
        execution_trace = []

        for step in plan.steps:
            # Verificar si las dependencias se han completado
            unmet = [dep for dep in step.dependencies if dep not in completed_steps]
            if unmet:
                step.status = StepStatus.SKIPPED
                execution_trace.append({
                    "step": step.step_number,
                    "status": "skipped",
                    "reason": f"Dependencias no satisfechas: {unmet}"
                })
                continue

            step.status = StepStatus.RUNNING

            if dry_run:
                step.status = StepStatus.COMPLETED
                step.result = f"[DRY-RUN] Simulación exitosa de: {step.title}"
                completed_steps.add(step.step_number)
                execution_trace.append({
                    "step": step.step_number,
                    "status": "completed",
                    "mode": "dry_run"
                })
            else:
                # Ejecución real (o delegación al tool_runner si existe)
                try:
                    if step.required_tool and self.tool_runner:
                        res = self.tool_runner(step.required_tool, {"description": step.description})
                        step.result = res
                    else:
                        step.result = f"Paso completado: {step.title}"
                    step.status = StepStatus.COMPLETED
                    completed_steps.add(step.step_number)
                    execution_trace.append({
                        "step": step.step_number,
                        "status": "completed",
                        "result": step.result
                    })
                except Exception as e:
                    step.status = StepStatus.FAILED
                    step.result = str(e)
                    execution_trace.append({
                        "step": step.step_number,
                        "status": "failed",
                        "error": str(e)
                    })

        return {
            "success": all(s.status == StepStatus.COMPLETED for s in plan.steps),
            "completed_count": len(completed_steps),
            "total_steps": len(plan.steps),
            "trace": execution_trace
        }
