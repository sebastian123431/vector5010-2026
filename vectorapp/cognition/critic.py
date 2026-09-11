"""
Crítico cognitivo (Cognitive Critic) para Vector (Fase P2).
Evalúa la calidad, coherencia, fidelidad y seguridad de las respuestas antes de entregarlas.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import re


@dataclass
class CriticEvaluation:
    """Resultado de la evaluación crítica de una respuesta."""
    score: float             # 0.0 a 1.0
    passed: bool
    feedback: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "passed": self.passed,
            "feedback": self.feedback,
            "suggestions": self.suggestions,
        }


class CognitiveCritic:
    """
    Evaluador crítico de respuestas generadas por el sistema cognitivo.
    """

    @staticmethod
    def evaluate_response(response: str, query: str = "", interlocutor: str = "Sebastian") -> CriticEvaluation:
        feedback = []
        suggestions = []
        score = 1.0

        if not response or not response.strip():
            return CriticEvaluation(score=0.0, passed=False, feedback=["Respuesta vacía."], suggestions=["Generar respuesta válida."])

        resp_clean = response.strip()

        # 1. Detección de auto-saludo absurdo ("Hola Vector")
        if re.search(r'\b(hola|buenos días|buenas tardes)\s+vector\b', resp_clean, re.IGNORECASE):
            score -= 0.35
            feedback.append("El modelo se saludó a sí mismo diciendo 'Hola Vector'.")
            suggestions.append("Dirigirse siempre al usuario/interlocutor, nunca a sí mismo.")

        # 2. Bloques de código incompletos (``` sin cerrar)
        fence_count = resp_clean.count("```")
        if fence_count % 2 != 0:
            score -= 0.30
            feedback.append("Bloque de código con delimitadores '```' desbalanceados (sin cerrar).")
            suggestions.append("Cerrar los bloques de código abiertos con '```'.")

        # 3. Discrepancia de interlocutor (llamar Seba a quien no es Seba o viceversa)
        is_seba = interlocutor.lower() in ("sebastian", "seba", "sebastián")
        if not is_seba:
            if re.search(r'\b(seba|sebastian|sebastián)\b', resp_clean, re.IGNORECASE) and "mi creador" not in resp_clean.lower():
                score -= 0.20
                feedback.append(f"Se mencionó 'Sebastian' al hablar con otro usuario ({interlocutor}).")
                suggestions.append(f"Adaptar el tono respetando que el interlocutor actual es {interlocutor}.")

        # 4. Marcadores de alucinación o vacilación no resuelta
        if any(marker in resp_clean.lower() for marker in ("como modelo de ia no puedo", "no tengo acceso a internet", "no soy capaz")):
            score -= 0.20
            feedback.append("La respuesta contiene frases genéricas de limitación no acordes con las capacidades de Vector.")
            suggestions.append("Responder de forma asertiva utilizando las herramientas del sistema.")

        score = max(0.0, min(1.0, round(score, 2)))
        passed = score >= 0.70

        return CriticEvaluation(
            score=score,
            passed=passed,
            feedback=feedback,
            suggestions=suggestions
        )

    evaluate = evaluate_response

