"""
Ejecutor de planes cognitivos (Plan Executor) para Vector (Fase P2).
Ejecuta pasos secuenciales o dependientes observando cuotas y tolerando fallos.
"""

from typing import Dict, Any, List, Optional, Callable
from .planner import CognitivePlan, PlanStep, StepStatus


import time


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
            t0 = time.perf_counter()
            # Verificar si las dependencias se han completado
            unmet = [dep for dep in step.dependencies if dep not in completed_steps]
            if unmet:
                step.status = StepStatus.SKIPPED
                step.error = f"Dependencias no satisfechas: {unmet}"
                step.latency_ms = (time.perf_counter() - t0) * 1000.0
                execution_trace.append({
                    "step": step.step_number,
                    "status": "skipped",
                    "reason": step.error,
                    "latency_ms": round(step.latency_ms, 2)
                })
                continue

            step.status = StepStatus.RUNNING
            if step.input_data is None:
                step.input_data = {"description": step.description, "tool": step.required_tool}
            elif isinstance(step.input_data, dict):
                step.input_data.setdefault("description", step.description)
                step.input_data.setdefault("tool", step.required_tool)

            if dry_run:
                step.status = StepStatus.COMPLETED
                step.result = f"[DRY-RUN] Simulación exitosa de: {step.title}"
                step.output_data = step.result
                step.latency_ms = (time.perf_counter() - t0) * 1000.0
                completed_steps.add(step.step_number)
                execution_trace.append({
                    "step": step.step_number,
                    "status": "completed",
                    "mode": "dry_run",
                    "latency_ms": round(step.latency_ms, 2)
                })
            else:
                # Ejecución real (o delegación al tool_runner si existe)
                try:
                    if step.required_tool:
                        if self.tool_runner is None:
                            step.status = StepStatus.FAILED
                            step.error = "required tool runner unavailable"
                            step.result = "required tool runner unavailable"
                            step.latency_ms = (time.perf_counter() - t0) * 1000.0
                            execution_trace.append({
                                "step": step.step_number,
                                "status": "failed",
                                "error": step.error,
                                "latency_ms": round(step.latency_ms, 2)
                            })
                            continue

                        tool_input = dict(step.input_data) if isinstance(step.input_data, dict) else {}
                        tool_input.setdefault("description", step.description)
                        res = self.tool_runner(step.required_tool, tool_input)
                        step.result = res
                        step.output_data = res

                        # Validación estricta del resultado de la herramienta
                        tool_failed = False
                        tool_err_msg = None
                        if isinstance(res, dict):
                            if res.get("success") is False:
                                tool_failed = True
                                tool_err_msg = res.get("error") or "tool returned failure status"
                        elif hasattr(res, "success"):
                            if not res.success:
                                tool_failed = True
                                tool_err_msg = getattr(res, "error", None) or "tool returned failure status"

                        if tool_failed:
                            step.status = StepStatus.FAILED
                            step.error = tool_err_msg
                            step.latency_ms = (time.perf_counter() - t0) * 1000.0
                            execution_trace.append({
                                "step": step.step_number,
                                "status": "failed",
                                "error": tool_err_msg,
                                "latency_ms": round(step.latency_ms, 2)
                            })
                            continue
                    else:
                        step.result = f"Paso cognitivo completado: {step.title}"
                        step.output_data = step.result

                    step.status = StepStatus.COMPLETED
                    step.latency_ms = (time.perf_counter() - t0) * 1000.0
                    completed_steps.add(step.step_number)
                    execution_trace.append({
                        "step": step.step_number,
                        "status": "completed",
                        "result": step.result,
                        "latency_ms": round(step.latency_ms, 2)
                    })
                except Exception as e:
                    step.status = StepStatus.FAILED
                    step.error = str(e)
                    step.result = str(e)
                    step.latency_ms = (time.perf_counter() - t0) * 1000.0
                    execution_trace.append({
                        "step": step.step_number,
                        "status": "failed",
                        "error": str(e),
                        "latency_ms": round(step.latency_ms, 2)
                    })

        return {
            "success": all(s.status == StepStatus.COMPLETED for s in plan.steps),
            "completed_count": len(completed_steps),
            "total_steps": len(plan.steps),
            "trace": execution_trace
        }
