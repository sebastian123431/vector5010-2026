"""
Planificador cognitivo de tareas complejas (Cognitive Planner) para Vector (Fase P2).
Descompone metas u objetivos de software e investigación en planes secuenciales con dependencias.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PlanStep:
    """Paso unitario de un plan cognitivo."""
    step_number: int
    title: str
    description: str
    required_tool: Optional[str] = None
    dependencies: List[int] = field(default_factory=list)
    status: StepStatus = StepStatus.PENDING
    result: Optional[Any] = None
    input_data: Optional[Any] = None
    output_data: Optional[Any] = None
    latency_ms: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_number": self.step_number,
            "title": self.title,
            "description": self.description,
            "required_tool": self.required_tool,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "result": str(self.result) if self.result is not None else None,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "latency_ms": round(self.latency_ms, 2),
            "error": self.error,
        }


@dataclass
class CognitivePlan:
    """Plan de ejecución estructurado."""
    goal: str
    steps: List[PlanStep] = field(default_factory=list)
    estimated_complexity: str = "moderate"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal": self.goal,
            "steps": [s.to_dict() for s in self.steps],
            "total_steps": len(self.steps),
            "estimated_complexity": self.estimated_complexity,
        }


class CognitivePlanner:
    """
    Motor de planificación y descomposición recursiva de objetivos.
    """

    @staticmethod
    def create_plan(goal: str, context: Optional[Dict[str, Any]] = None) -> CognitivePlan:
        """
        Crea un plan estructurado para un objetivo dado.
        """
        g_lower = goal.lower()

        ctx = context or {}
        zip_params = {k: v for k, v in ctx.items() if k in ("file_path", "zip_source", "project_name", "target_dir")}
        if not zip_params and "file" in ctx:
            zip_params["file_path"] = ctx["file"]

        # 1. Si es análisis de proyecto ZIP / archivo comprimido
        if "zip" in g_lower or ("proyecto" in g_lower and zip_params) or ("archivo" in g_lower and zip_params):
            steps = [
                PlanStep(
                    step_number=1,
                    title="Extracción y Validación Segura de Archivos",
                    description="Descomprimir y verificar cuotas de seguridad y protección anti-ZipBomb.",
                    required_tool="extract_zip",
                    input_data=dict(zip_params) if zip_params else None
                ),
                PlanStep(
                    step_number=2,
                    title="Inspección Estructural y Parsing AST",
                    description="Analizar funciones, clases y errores de sintaxis en el AST.",
                    dependencies=[1],
                    input_data=dict(zip_params) if zip_params else None
                ),
                PlanStep(
                    step_number=3,
                    title="Auditoría de Seguridad y Anti-Patrones",
                    description="Escanear vulnerabilidades XSS, inyecciones y fallos estructurales.",
                    dependencies=[2]
                ),
                PlanStep(
                    step_number=4,
                    title="Síntesis de Informe Técnico y Auto-Reparación",
                    description="Consolidar reporte estructurado en Markdown y generar propuestas de mejora.",
                    dependencies=[3]
                )
            ]
            return CognitivePlan(goal=goal, steps=steps, estimated_complexity="intensive")

        # 1.1 Si es diagnóstico / refactorización de código sin archivo ZIP
        if any(w in g_lower for w in ("diagnosticar", "refactorizar", "codigo", "código", "modulo", "módulo", "ast")):
            steps = [
                PlanStep(
                    step_number=1,
                    title="Inspección Estructural y Parsing AST",
                    description="Analizar funciones, clases y árbol sintáctico del módulo.",
                ),
                PlanStep(
                    step_number=2,
                    title="Auditoría de Patrones y Seguridad",
                    description="Identificar anomalías, complejidad ciclomática y buenas prácticas.",
                    dependencies=[1]
                ),
                PlanStep(
                    step_number=3,
                    title="Generación de Diagnóstico y Plan de Refactorización",
                    description="Elaborar recomendaciones técnicas y código refactorizado.",
                    dependencies=[2]
                )
            ]
            return CognitivePlan(goal=goal, steps=steps, estimated_complexity="moderate")

        # 2. Si es investigación web con contraste
        web_params = {k: v for k, v in ctx.items() if k in ("query", "max_results", "lugar", "categoria")}
        if any(w in g_lower for w in ("investigar", "noticias", "buscar en internet", "clima")):
            steps = [
                PlanStep(
                    step_number=1,
                    title="Búsqueda Web Resiliente Multi-sitio",
                    description="Consultar fuentes oficiales verificadas con prioridad chilena (.cl).",
                    required_tool="web_search",
                    input_data=dict(web_params) if web_params else None
                ),
                PlanStep(
                    step_number=2,
                    title="Debate Epistemológico y Extracción de Hechos",
                    description="Comparar fuentes, detectar coincidencias y filtrar discrepancias.",
                    dependencies=[1]
                ),
                PlanStep(
                    step_number=3,
                    title="Consolidación y Verificación de Respuesta",
                    description="Sintetizar respuesta directa, concisa y respaldada por citas.",
                    dependencies=[2]
                )
            ]
            return CognitivePlan(goal=goal, steps=steps, estimated_complexity="moderate")

        # 3. Plan estándar de razonamiento
        steps = [
            PlanStep(
                step_number=1,
                title="Recuperación Semántica y Activación de Memoria",
                description="Consultar recuerdos vectoriales afines y red de conceptos."
            ),
            PlanStep(
                step_number=2,
                title="Formulación de Hipótesis y Razonamiento",
                description="Analizar lógica interna y evaluar alternativas de respuesta.",
                dependencies=[1]
            ),
            PlanStep(
                step_number=3,
                title="Verificación Crítica de Calidad",
                description="Confirmar ausencia de alucinaciones y adecuación al interlocutor.",
                dependencies=[2]
            )
        ]
        return CognitivePlan(goal=goal, steps=steps, estimated_complexity="simple")
