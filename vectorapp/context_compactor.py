"""
Módulo de Compactación de Contexto y Memoria Sináptica Continua para Vector.
Implementa el protocolo de Rolling Context Compaction (Compensación de Contexto Rodante)
integrado directamente con la Red Neuronal Semántica de 402+ nodos.
"""

from typing import List, Dict, Tuple, Optional, Any
import logging
import re

logger = logging.getLogger(__name__)

class ContextCompactor:
    """
    Compacta historiales conversacionales largos en 3 niveles:
    1. Inmediato: Últimos N turnos (verbatim, sin alteración).
    2. Intermedio: Turnos antiguos compactados en una cápsula semántica densa.
    3. Profundo: Asimilación en la red neuronal sináptica como recuerdo permanente.
    """
    
    # Si hay más de este número de turnos, se activa la compactación de los antiguos
    UMBRAL_COMPACTACION_TURNOS = 6
    # Cantidad de turnos recientes que se preservan palabra por palabra
    TURNOS_RECIENTES_PRESERVADOS = 4

    @classmethod
    def should_compact(cls, raw_turns: List[Dict[str, str]]) -> bool:
        """Determina si la lista de turnos amerita compactación."""
        if not raw_turns:
            return False
        return len(raw_turns) > cls.UMBRAL_COMPACTACION_TURNOS

    @classmethod
    def extract_key_concepts(cls, text: str) -> List[str]:
        """Extrae entidades técnicas, archivos, funciones y conceptos clave de un texto."""
        conceptos = set()
        
        # Archivos con extensiones comunes (.py, .js, .csv, .json, etc.)
        archivos = re.findall(r'\b[a-zA-Z0-9_\-]+\.(?:py|js|ts|csv|json|html|css|sql|txt|md|zip)\b', text, re.IGNORECASE)
        conceptos.update(archivos)
        
        # Funciones o métodos con paréntesis func()
        funciones = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\s*\(\s*\)', text)
        conceptos.update([f.strip() for f in funciones if not f.startswith(('if', 'for', 'while', 'print', 'len'))])
        
        # Librerías o tecnologías frecuentes
        tech_words = [
            'python', 'django', 'cuda', 'nvidia', 'ast', 'csv', 'json', 'llm', 'gemma',
            'nomic', 'embeddings', 'yolo', 'opencv', 'threejs', 'visjs', 'numpy',
            'pandas', 'clima', 'vicuña', 'coquimbo', 'centinela', 'cpu', 'ram', 'gpu'
        ]
        text_lower = text.lower()
        for tech in tech_words:
            if re.search(rf'\b{re.escape(tech)}\b', text_lower):
                conceptos.add(tech)
                
        return sorted(list(conceptos))

    @classmethod
    def summarize_older_turns(cls, older_turns: List[Dict[str, str]], prev_summary: str = "", interlocutor_ref: str = "Sebastian") -> str:
        """
        Sintetiza los turnos antiguos en un resumen estructurado y denso en información técnica.
        """
        user_queries = []
        assistant_points = []
        all_concepts = set()

        for turn in older_turns:
            role = turn.get("role", "")
            content = turn.get("content", "").strip()
            if not content:
                continue

            # Extraer conceptos
            concepts = cls.extract_key_concepts(content)
            all_concepts.update(concepts)

            # Limpiar contenido para el resumen
            first_line = content.split('\n')[0].strip()
            # Remover prefijos
            first_line = re.sub(r'^(Tú|Vector|Usuario|Assistant)\s*:\s*', '', first_line, flags=re.IGNORECASE).strip()

            if role == "user":
                # Resumir la consulta del usuario
                resumen_q = first_line[:140] + ("..." if len(first_line) > 140 else "")
                if resumen_q and not any(resumen_q in q for q in user_queries):
                    user_queries.append(resumen_q)
            elif role == "assistant":
                # Resumir la respuesta técnica o solución del asistente
                bullets = [l.strip() for l in content.split('\n') if l.strip().startswith(('*', '-', '1.', '2.', '3.'))]
                if bullets:
                    sample_bullet = bullets[0][:120]
                    assistant_points.append(sample_bullet)
                else:
                    resumen_a = first_line[:140] + ("..." if len(first_line) > 140 else "")
                    if resumen_a and not any(resumen_a in a for a in assistant_points):
                        assistant_points.append(resumen_a)

        # Construir la cápsula consolidada
        partes = []
        if prev_summary:
            partes.append(f"- Antecedentes previos: {prev_summary}")

        if user_queries:
            q_str = " | ".join(user_queries[:4])
            partes.append(f"- Consultas y solicitudes previas de {interlocutor_ref}: {q_str}")

        if assistant_points:
            a_str = " | ".join(assistant_points[:3])
            partes.append(f"- Soluciones y diagnósticos técnicos acordados: {a_str}")

        if all_concepts:
            c_str = ", ".join(sorted(list(all_concepts))[:12])
            partes.append(f"- Elementos y componentes trabajados: {c_str}")

        return "\n".join(partes)

    @classmethod
    def compact_conversation_history(
        cls, 
        raw_turns: List[Dict[str, str]], 
        session=None,
        semantic_network=None,
        interlocutor_ref: str = "Sebastian",
        session_id: str = ""
    ) -> Tuple[str, List[Dict[str, str]]]:
        """
        Punto de entrada principal para compactación de conversación:
        Retorna:
          - capsule_context (str): Texto para inyectar en system_prompt con el historial compactado.
          - recent_turns (List[Dict]): Los turnos recientes preservados verbatim.
        """
        if not cls.should_compact(raw_turns):
            return "", raw_turns

        # Dividir turnos antiguos y recientes
        split_idx = max(0, len(raw_turns) - cls.TURNOS_RECIENTES_PRESERVADOS)
        older_turns = raw_turns[:split_idx]
        recent_turns = raw_turns[split_idx:]

        # Obtener resumen acumulado previo si existe en sesión aislado por session_id
        resumen_key = f"resumen_conversacion_{session_id}" if session_id else "resumen_conversacion_acumulado"
        prev_summary = ""
        if session and hasattr(session, "get"):
            prev_summary = session.get(resumen_key, "")

        # Generar nueva síntesis compactada
        nuevo_resumen = cls.summarize_older_turns(older_turns, prev_summary=prev_summary, interlocutor_ref=interlocutor_ref)

        # Guardar resumen en sesión si está disponible
        if session and hasattr(session, "__setitem__"):
            session[resumen_key] = nuevo_resumen[:600]
            if hasattr(session, "modified"):
                session.modified = True

        # Asimilación selectiva en la Red Neuronal Semántica solo para Sebastian
        if semantic_network and hasattr(semantic_network, "add_memory") and nuevo_resumen and interlocutor_ref == "Sebastian":
            try:
                conceptos_clave = cls.extract_key_concepts(nuevo_resumen)
                conceptos_tag = f" [Conceptos: {', '.join(conceptos_clave[:6])}]" if conceptos_clave else ""
                memory_text = f"CONVERSACION CONSOLIDADA SEBASTIAN: {nuevo_resumen[:280]}{conceptos_tag}"
                semantic_network.add_memory(memory_text, "conversation_synapse")
                logger.info("[ContextCompactor] Hilo de conversación asimilado exitosamente en red neuronal sináptica.")
            except Exception as e_synapse:
                logger.warning(f"[ContextCompactor] Aviso al asimilar en red sináptica: {e_synapse}")

        # Formatear la cápsula para el system_prompt
        capsule_context = (
            f"\n=== CAPSULA DE CONTEXTO CONVERSACIONAL CONSOLIDADO (HILO HISTORICO COMPACTADO) ===\n"
            f"La conversacion actual con {interlocutor_ref} tiene antecedentes consolidados para optimizar memoria:\n"
            f"{nuevo_resumen}\n"
            f"DIRECTIVA DE HILO COMPACTADO: Mantén total continuidad con los antecedentes arriba indicados. "
            f"No repitas soluciones ya dadas ni olvides los objetivos acordados.\n"
        )

        return capsule_context, recent_turns
