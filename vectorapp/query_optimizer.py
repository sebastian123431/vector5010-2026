"""
Optimizador de consultas y telemetría de rendimiento para Vector (J.A.R.V.I.S.).
Clasifica las consultas por complejidad, optimiza la asignación de recursos
y gestiona la caché en memoria para minimizar la latencia de respuesta.
"""

import re
import time
import math
import json
import logging
from typing import Dict, Any, Optional, Tuple, List, Set
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

class QueryComplexity(Enum):
    """Niveles de complejidad de consultas."""
    SIMPLE = "simple"           # Saludos, confirmaciones, respuestas directas (<25 tokens)
    MODERATE = "moderate"       # Preguntas generales, clima, recuerdos, identidad
    COMPLEX = "complex"         # Generación de código, herramientas, búsqueda web profunda
    INTENSIVE = "intensive"     # Diagnóstico AST de proyectos ZIP, introspección profunda, entrenamiento

class IntentCategory(str, Enum):
    """Categorías de intención semántica de consulta."""
    CASUAL = "casual"
    CODING = "coding"
    REASONING = "reasoning"
    MEMORY = "memory"
    VISION = "vision"
    WEB = "web"
    TOOL_CREATION = "tool_creation"
    PROJECT_ANALYSIS = "project_analysis"
    DATABASE = "database"
    SYSTEM = "system"

INTENT_PROTOTYPES: Dict[IntentCategory, List[str]] = {
    IntentCategory.CASUAL: [
        "hola qué tal cómo estás saludos cordiales",
        "buenos días un saludo cordial hasta luego adiós gracias",
    ],
    IntentCategory.CODING: [
        "escribir código función algoritmo script en python javascript depuración sintaxis",
        "refactorizar código depurar error de sintaxis bug corregir excepción parser",
        "algoritmo de búsqueda ordenamiento estructura de datos programación",
    ],
    IntentCategory.REASONING: [
        "por qué ocurre esto explica la causa diferencia lógica deducción conceptual",
        "analiza las consecuencias pros y contras fundamenta tu razonamiento crítico",
    ],
    IntentCategory.MEMORY: [
        "recuerdas lo que te dije antes qué sabes de mí en tu memoria guardada",
        "acuérdate de mis datos y preferencias personales información guardada",
    ],
    IntentCategory.VISION: [
        "analiza esta imagen foto cámara captura qué ves descripción visual",
        "reconocimiento visual mirar objetos rostro apariencia en la imagen",
    ],
    IntentCategory.WEB: [
        "busca en internet noticias clima tiempo pronóstico buscar en la web google",
        "investigar información actualizada en la red noticias y artículos de hoy",
    ],
    IntentCategory.TOOL_CREATION: [
        "crear una nueva tool registrar dynamic tool constructor de herramientas",
        "construir un adaptador de herramienta personalizada registrar nueva tool",
    ],
    IntentCategory.PROJECT_ANALYSIS: [
        "analizar proyecto zip diagnosticar repositorio inspeccionar archivos y arquitectura",
        "auditar paquete zip estructura del proyecto árbol de código completo",
    ],
    IntentCategory.DATABASE: [
        "consulta sql base de datos sqlite tabla select insert update esquema",
        "ejecutar query sql en la base de datos registros relacionales migraciones",
    ],
    IntentCategory.SYSTEM: [
        "estado del sistema centinela monitorear cpu ram gpu hardware temperatura",
        "recursos del computador poda de red neuronal optimizar memoria del sistema",
    ],
}

def _cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Calcula la similitud coseno entre dos vectores numéricos."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return dot / (norm1 * norm2)

@dataclass
class QueryRouteResult:
    """Resultado estructurado del enrutamiento híbrido de consultas."""
    route: IntentCategory
    complexity: QueryComplexity
    complexity_score: float
    tier: int  # 0: fast regex, 1: semantic intent, 2: llm/deep
    confidence: float
    suggested_config: Dict[str, Any]
    fast_response: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class QueryOptimizer:
    """
    Optimizador que clasifica consultas, ajusta el procesamiento según complejidad,
    evita I/O redundante y gestiona la caché con métricas de rendimiento en tiempo real.
    """
    
    def __init__(self):
        # Patrones de consulta simple (saludos y confirmaciones breves)
        self.simple_patterns = [
            r'^(?:hola|buenas|buenos días|buenos dias|buenas tardes|buenas noches|qué tal|que tal|saludos)[.!?]?$',
            r'^(?:gracias|muchas gracias|gracias por todo|te lo agradezco)[.!?]?$',
            r'^(?:adiós|adios|bye|hasta luego|nos vemos|chao)[.!?]?$',
            r'^(?:sí|si|no|ok|okay|vale|perfecto|entendido|de acuerdo)[.!?]?$',
            r'^(?:¿cómo estás\?|como estas|cómo estás|cómo te sientes|como te sientes)[.!?]?$',
        ]
        
        # Patrones de consulta moderada (clima, identidad, recuerdos, explicaciones)
        self.moderate_patterns = [
            r'\b(?:explica|dime|cuéntame|define|qué es|que es|concepto de)\b',
            r'\b(?:cómo se|como se|cómo funciona|como funciona|de qué manera)\b',
            r'\b(?:ejemplo|muestra|demuestra|cómo hacer)\b',
            r'\b(?:diferencia|compara|versus|vs)\b',
            r'\b(?:clima|tiempo|temperatura|lloverá|va a llover)\b',
            r'\b(?:cómo me llamo|como me llamo|quién soy|quien soy|mi nombre)\b',
            r'\b(?:qué recuerdas|que recuerdas|recuerdas|acuerdas|en tu memoria)\b',
        ]
        
        # Patrones de consulta compleja (herramientas, generación de scripts, cálculos, arquitectura)
        self.complex_patterns = [
            r'\b(?:analizar|analiza|procesar|procesa|calcular|calcula|evaluar|evalúa|ejecutar|ejecuta)\b',
            r'\b(?:crear|generar|programar|escribir)\s+(?:herramienta|código|script|función|algoritmo)\b',
            r'\b(?:analizar|analiza|revisa|revisar|inspecciona|inspeccionar)\s+(?:este\s+)?(?:archivo|código|codigo|script|python|función|repo)\b',
            r'\b(?:detectar|detecta|resolver|resuelve|solucionar|soluciona)\s+(?:problemas|errores|bugs|vulnerabilidades)\b',
            r'\b(?:herramienta|tool|función|function)\b',
            r'\b(?:código|codigo|script|programa|refactorizar)\b',
            r'\b(?:busca en internet|buscar en internet|noticias|investigar)\b',
            r'\b(?:arquitectura|tu código|tus archivos|cuello de botella)\b',
        ]
        
        # Patrones intensivos (diagnóstico de proyectos ZIP, entrenamiento, análisis profundo)
        self.intensive_patterns = [
            r'\b(?:diagnosticar|diagnóstico|diagnostico)\s+(?:proyecto|zip|código|archivos)\b',
            r'\b(?:analizar|analiza)\s+(?:proyecto|zip|repositorio)\b',
            r'\b(?:entrenar|entrenamiento|reentrenar)\s+(?:red|modelo|neuronas)\b',
            r'\b(?:red neuronal|neural network|deep learning|ast|árbol de sintaxis)\b',
            r'\b(?:poda|pruning|optimizar red|inspección completa)\b',
        ]
        
        # Caché en memoria con TTL
        self.performance_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl_seconds = 1800  # 30 minutos
        self.cache_max_entries = 150
        self.cache_hits = 0
        self.cache_misses = 0

        # Estadísticas acumuladas y promedio móvil exacto
        self.query_stats = {
            'simple': {'count': 0, 'total_time': 0.0, 'avg_time': 0.0, 'min_time': 999.0, 'max_time': 0.0},
            'moderate': {'count': 0, 'total_time': 0.0, 'avg_time': 0.0, 'min_time': 999.0, 'max_time': 0.0},
            'complex': {'count': 0, 'total_time': 0.0, 'avg_time': 0.0, 'min_time': 999.0, 'max_time': 0.0},
            'intensive': {'count': 0, 'total_time': 0.0, 'avg_time': 0.0, 'min_time': 999.0, 'max_time': 0.0},
        }

        # Embeddings de prototipos de intención (Tier 1)
        self._prototype_embeddings: Dict[IntentCategory, List[float]] = {}

    def classify_query(self, query: str) -> QueryComplexity:
        """
        Clasifica una consulta en uno de los 4 niveles de complejidad cognitiva.
        """
        q = query.lower().strip()
        
        # 1. Verificar primero si es INTENSIVO (proyectos ZIP, AST, red profunda)
        for pattern in self.intensive_patterns:
            if re.search(pattern, q):
                return QueryComplexity.INTENSIVE
        
        # 2. Verificar si es COMPLEJO (código, herramientas, arquitectura)
        for pattern in self.complex_patterns:
            if re.search(pattern, q):
                return QueryComplexity.COMPLEX
        
        # 3. Verificar si es MODERADO (clima, recuerdos, identidad, preguntas generales)
        for pattern in self.moderate_patterns:
            if re.search(pattern, q):
                return QueryComplexity.MODERATE
        
        # 4. Verificar si es SIMPLE (saludos puros, respuestas breves)
        for pattern in self.simple_patterns:
            if re.search(pattern, q):
                return QueryComplexity.SIMPLE

        # Heurística basada en longitud y estructura
        words = q.split()
        if len(words) <= 3 and len(q) < 22:
            return QueryComplexity.SIMPLE
        elif len(q) < 90:
            return QueryComplexity.MODERATE
        else:
            return QueryComplexity.COMPLEX

    def calculate_complexity_score(self, query: str) -> float:
        """
        Calcula un puntaje continuo de complejidad cognitiva estrictamente calibrado entre 0.00 y 1.00.
        - 0.00 - 0.20: SIMPLE (saludos, respuestas directas)
        - 0.21 - 0.45: MODERATE (preguntas generales, clima, memoria)
        - 0.46 - 0.74: COMPLEX (generación de código, herramientas, búsqueda web)
        - 0.75 - 1.00: INTENSIVE (diagnóstico ZIP, AST masivo, introspección profunda)
        """
        q = query.lower().strip()
        words = q.split()
        num_words = len(words)

        # 1. Nivel Intensivo (0.75 - 1.00)
        int_matches = [p for p in self.intensive_patterns if re.search(p, q)]
        if int_matches:
            score = 0.75 + min(0.25, (len(int_matches) - 1) * 0.10)
            return round(min(1.00, score), 2)

        # 2. Nivel Complejo (0.46 - 0.74)
        comp_matches = [p for p in self.complex_patterns if re.search(p, q)]
        has_code_syntax = any(tok in q for tok in ("function", "class ", "def ", "import ", "const ", "let ", "var ", "=>", "{}", "()", ";", "=="))
        if comp_matches or has_code_syntax:
            bonus = 0.05 if num_words > 8 else 0.0
            score = 0.50 + min(0.24, (len(comp_matches) - 1) * 0.08 + bonus)
            return round(min(0.74, score), 2)

        # 3. Nivel Moderado (0.21 - 0.45)
        mod_matches = [p for p in self.moderate_patterns if re.search(p, q)]
        if mod_matches:
            score = 0.25 + min(0.20, (len(mod_matches) - 1) * 0.05)
            return round(min(0.45, score), 2)

        # 4. Nivel Simple (0.01 - 0.20)
        simp_matches = [p for p in self.simple_patterns if re.search(p, q)]
        if simp_matches:
            score = 0.05 + min(0.12, num_words * 0.03)
            return round(min(0.20, score), 2)

        # Heurística fallback por longitud y estructura
        if num_words <= 3 and len(q) < 22:
            return 0.15
        elif len(q) < 90:
            return 0.35
        else:
            return 0.55

    def _get_prototype_embeddings(self) -> Dict[IntentCategory, List[float]]:
        """Inicializa y cachea los embeddings de prototipos de intención (Tier 1)."""
        if self._prototype_embeddings:
            return self._prototype_embeddings
        try:
            from .local_engine import VectorLocalEngine
            for cat, phrases in INTENT_PROTOTYPES.items():
                joined = " ".join(phrases)
                vec = VectorLocalEngine.embed_query(joined)
                if vec and any(x != 0.0 for x in vec):
                    self._prototype_embeddings[cat] = vec
        except Exception as e:
            logger.debug(f"[QueryOptimizer] Embeddings de prototipos no inicializados: {e}")
        return self._prototype_embeddings

    def classify_intent_tier1_embeddings(self, query: str) -> Tuple[IntentCategory, float, float]:
        """
        Tier 1: Clasificación basada en embeddings y similitud coseno contra prototipos de intents,
        ponderada con señales léxicas de alta confianza.
        Retorna (IntentCategory, confianza, margen_sobre_segundo).
        """
        q = query.strip()
        rule_intent, rule_conf = self.classify_intent(q)
        proto_map = self._get_prototype_embeddings()

        if proto_map:
            try:
                from .local_engine import VectorLocalEngine
                q_vec = VectorLocalEngine.embed_query(q)
                if q_vec and any(x != 0.0 for x in q_vec):
                    sims: List[Tuple[IntentCategory, float]] = []
                    for cat, p_vec in proto_map.items():
                        sim = _cosine_similarity(q_vec, p_vec)
                        # Ponderación armónica: refuerza la categoría si coincide con intención léxica fuerte
                        if cat == rule_intent and rule_conf >= 0.80:
                            sim += 0.15
                        sims.append((cat, sim))
                    sims.sort(key=lambda x: x[1], reverse=True)
                    best_cat, best_sim = sims[0]
                    second_sim = sims[1][1] if len(sims) > 1 else 0.0
                    margin = round(best_sim - second_sim, 3)
                    conf = round(max(0.0, min(1.0, (best_sim + 1.0) / 2.0)), 2)
                    return best_cat, conf, margin
            except Exception as e:
                logger.debug(f"[Tier 1 Embeddings] Fallo calculando similitud coseno: {e}")

        # Fallback semántico determinista de Tier 1 si el motor vectorial local no está corriendo
        return rule_intent, rule_conf, 0.20

    def classify_tier2_gemma(self, query: str) -> Optional[Tuple[IntentCategory, float]]:
        """
        Tier 2: Desambiguación semántica profunda utilizando Gemma local con salida estricta JSON.
        Formato requerido: {"route": "coding", "confidence": 0.88}
        Valida la respuesta y aplica fallback ordenado si falla o no está disponible el LLM.
        """
        q = query.strip()
        prompt = (
            "Eres el clasificador de intenciones del sistema cognitivo Vector.\n"
            "Clasifica la consulta del usuario en exactamente una de estas categorías:\n"
            "- casual: saludos o despedidas\n"
            "- coding: código fuente, algoritmos, scripts, bugs, errores, 'revisa esto', 'fallando'\n"
            "- reasoning: por qué, deducción, reflexión lógica, 'hazlo mejor'\n"
            "- memory: recuerdos, información previa, 'acuérdate de esto'\n"
            "- vision: fotos, imágenes, cámara, mirar objetos, 'mira esto'\n"
            "- web: noticias, clima, búsqueda online, 'busca qué ocurrió'\n"
            "- tool_creation: creación de nuevas herramientas dinámicas\n"
            "- project_analysis: proyectos zip, repositorio, archivos\n"
            "- database: sql, sqlite, consultas relacionales\n"
            "- system: monitoreo hardware, cpu, ram, gpu, red neuronal\n\n"
            "Responde ÚNICAMENTE un JSON válido con esta estructura:\n"
            "{\"route\": \"<categoria>\", \"confidence\": <0.0 a 1.0>}\n\n"
            f"Consulta: \"{q}\""
        )
        messages = [{"role": "user", "content": prompt}]
        try:
            from .local_engine import VectorLocalEngine
            resp_text = VectorLocalEngine.chat_completion(messages, temperature=0.1, max_tokens=60)
            if resp_text:
                match = re.search(r'\{[^{}]+\}', resp_text)
                if match:
                    data = json.loads(match.group(0))
                    raw_route = str(data.get("route", "")).strip().lower()
                    raw_conf = float(data.get("confidence", 0.85))
                    for cat in IntentCategory:
                        if cat.value.lower() == raw_route:
                            return cat, round(min(1.0, max(0.0, raw_conf)), 2)
        except Exception as e:
            logger.debug(f"[Tier 2 Gemma] Inferencia LLM no disponible: {e}")

        # Desambiguador semántico contextual de Tier 2 (fallback garantizado ante consultas ambiguas)
        q_lower = q.lower()
        if any(w in q_lower for w in ("mira esto", "miren esto", "observa esto", "ve esto", "mira la imagen", "foto")):
            return IntentCategory.VISION, 0.86
        elif any(w in q_lower for w in ("revisa esto", "chequea esto", "esto está fallando", "falla en", "error", "bug", "código")):
            return IntentCategory.CODING, 0.88
        elif any(w in q_lower for w in ("hazlo mejor", "mejora esto", "explica mejor", "por qué", "razona")):
            return IntentCategory.REASONING, 0.85
        elif any(w in q_lower for w in ("acuérdate de esto", "acuerdate de esto", "recuerda esto", "guarda esto en memoria")):
            return IntentCategory.MEMORY, 0.90
        elif any(w in q_lower for w in ("busca qué ocurrió", "busca que ocurrio", "averigua qué pasó", "noticias de hoy")):
            return IntentCategory.WEB, 0.87
        elif any(w in q_lower for w in ("analiza el proyecto", "zip")):
            return IntentCategory.PROJECT_ANALYSIS, 0.92

        return None

    def classify_intent(self, query: str) -> Tuple[IntentCategory, float]:
        """
        Clasifica la intención semántica nuclear de la consulta y retorna (IntentCategory, confianza).
        """
        q = query.lower().strip()

        intent_rules = [
            (IntentCategory.PROJECT_ANALYSIS, [
                r'\b(?:analizar|analiza|diagnosticar|diagnóstico|diagnostico)\s+(?:proyecto|zip|repositorio|código)\b',
                r'\b(?:archivo zip|proyecto zip|subir zip|descomprimir)\b'
            ], 0.95),
            (IntentCategory.TOOL_CREATION, [
                r'\b(?:crear|generar|programar|construir)\s+(?:(?:un|una|el|la)\s+)?(?:herramienta|tool|función dinámica)\b',
                r'\b(?:herramienta|tool)\s+(?:para|de)\b',
                r'\b(?:nueva herramienta|adaptar herramienta)\b'
            ], 0.92),
            (IntentCategory.DATABASE, [
                r'\b(?:sql|sqlite|base de datos|database|tabla|select|insert|update|query sql)\b',
            ], 0.90),
            (IntentCategory.VISION, [
                r'\b(?:foto|imagen|cámara|camara|rostro|apariencia|ves|miras|yolo)\b',
            ], 0.88),
            (IntentCategory.CODING, [
                r'\b(?:código|codigo|javascript|typescript|python|función|funcion|algoritmo|refactorizar|bug|error de sintaxis|ast)\b',
                r'\b(?:script|npm|pip|compilar|depurar)\b'
            ], 0.85),
            (IntentCategory.WEB, [
                r'\b(?:busca en internet|buscar en internet|noticias|clima|tiempo|temperatura|lloverá|chile|meteored)\b',
                r'\b(?:web|google|enlaces|artículo|noticia)\b'
            ], 0.85),
            (IntentCategory.MEMORY, [
                r'\b(?:recuerdas|recuerda|acuerdas|en tu memoria|qué sabes de|quién soy|cómo me llamo)\b',
                r'\b(?:olvida|borra recuerdo|guarda esto)\b'
            ], 0.88),
            (IntentCategory.SYSTEM, [
                r'\b(?:centinela|cpu|ram|memoria del sistema|hardware|gpu|temperatura cpu|recursos)\b',
                r'\b(?:red neuronal|neuronas|poda|prune|entrenar red)\b'
            ], 0.85),
            (IntentCategory.CASUAL, [
                r'^(?:hola|buenas|buenos días|buenos dias|buenas tardes|buenas noches|qué tal|saludos|gracias|adiós|ok|vale)[.!?]?$',
                r'\b(?:cómo estás|como estas|cómo te sientes)\b'
            ], 0.95),
            (IntentCategory.REASONING, [
                r'\b(?:por qué|por que|cómo funciona|explica|diferencia entre|compara|analiza|conclusión|razonamiento)\b',
            ], 0.75),
        ]

        for intent, patterns, conf in intent_rules:
            for pat in patterns:
                if re.search(pat, q):
                    return intent, conf

        return IntentCategory.REASONING, 0.50

    def route_query(self, query: str, user_name: Optional[str] = None) -> QueryRouteResult:
        """
        Enrutador híbrido de consultas en 3 Tiers:
        - TIER 0: Reglas/regex deterministas y respuesta inmediata si aplica (<1ms).
        - TIER 1: Clasificación semántica por embeddings y similitud coseno contra prototipos.
        - TIER 2: Gemma local para consultas ambiguas o conflicto entre intents.
        """
        q = query.strip()

        # Nivel 0: Fast path regex determinista
        fast_resp = self.get_simple_response(q, user_name=user_name)
        if fast_resp:
            cfg = self.get_processing_config(QueryComplexity.SIMPLE)
            return QueryRouteResult(
                route=IntentCategory.CASUAL,
                complexity=QueryComplexity.SIMPLE,
                complexity_score=0.05,
                tier=0,
                confidence=1.0,
                suggested_config=cfg,
                fast_response=fast_resp,
                metadata={"fast_path": True}
            )

        q_lower = q.lower()
        ambiguous_patterns = [
            r'\bmira\s+esto\b',
            r'\brevisa\s+esto\b',
            r'\bhazlo\s+mejor\b',
            r'\bacu[eé]rdate\s+de\s+esto\b',
            r'\besto\s+est[aá]\s+fallando\b',
            r'\bbusca\s+qu[eé]\s+ocurri[oó]\b',
        ]
        is_ambiguous = any(re.search(pat, q_lower) for pat in ambiguous_patterns)

        # Nivel 1: Clasificación de intención semántica con embeddings
        intent_t1, conf_t1, margin_t1 = self.classify_intent_tier1_embeddings(q)

        tier = 1
        intent = intent_t1
        confidence = conf_t1

        # Nivel 2: Activar Gemma local si hay baja confianza (<0.60), conflicto de intents (margin < 0.05) o ambigüedad explícita
        if is_ambiguous or conf_t1 < 0.60 or (margin_t1 < 0.05 and conf_t1 < 0.75):
            t2_res = self.classify_tier2_gemma(q)
            if t2_res:
                intent, confidence = t2_res
                tier = 2
            else:
                # Si falla Tier 2, volver ordenadamente a Tier 1
                tier = 1
                intent = intent_t1
                confidence = conf_t1

        score = self.calculate_complexity_score(q)
        if tier == 2 and score < 0.35:
            score = 0.45

        # Mapeo score -> QueryComplexity
        if score <= 0.20:
            complexity = QueryComplexity.SIMPLE
        elif score <= 0.45:
            complexity = QueryComplexity.MODERATE
        elif score <= 0.74:
            complexity = QueryComplexity.COMPLEX
        else:
            complexity = QueryComplexity.INTENSIVE

        # Ajuste por intención crítica
        if intent in (IntentCategory.PROJECT_ANALYSIS, IntentCategory.TOOL_CREATION) and complexity.value in ("simple", "moderate"):
            complexity = QueryComplexity.COMPLEX
            score = max(score, 0.55)

        cfg = self.get_processing_config(complexity)

        return QueryRouteResult(
            route=intent,
            complexity=complexity,
            complexity_score=score,
            tier=tier,
            confidence=confidence,
            suggested_config=cfg,
            fast_response=None,
            metadata={"classified_intent": intent.value, "tier": tier}
        )

    def get_processing_config(self, complexity: QueryComplexity) -> Dict[str, Any]:
        """
        Obtiene la configuración óptima de procesamiento para minimizar la latencia.
        """
        configs = {
            QueryComplexity.SIMPLE: {
                'use_neural_network': False,
                'use_memory_analysis': False,       # Salta embeddings pesados para saludos
                'use_tool_detection': False,        # No analiza creación de herramientas
                'use_web_search': False,            # No ejecuta scrapings
                'use_vision': False,
                'max_tokens': 160,
                'history_limit': 2,
                'timeout_seconds': 5
            },
            QueryComplexity.MODERATE: {
                'use_neural_network': True,
                'use_memory_analysis': True,
                'use_tool_detection': False,
                'use_web_search': False,
                'use_vision': True,
                'max_tokens': 450,
                'history_limit': 4,
                'timeout_seconds': 12
            },
            QueryComplexity.COMPLEX: {
                'use_neural_network': True,
                'use_memory_analysis': True,
                'use_tool_detection': True,
                'use_web_search': True,
                'use_vision': True,
                'max_tokens': 900,
                'history_limit': 6,
                'timeout_seconds': 30
            },
            QueryComplexity.INTENSIVE: {
                'use_neural_network': True,
                'use_memory_analysis': True,
                'use_tool_detection': True,
                'use_web_search': True,
                'use_vision': True,
                'max_tokens': 1600,
                'history_limit': 10,
                'timeout_seconds': 60
            }
        }
        return configs.get(complexity, configs[QueryComplexity.MODERATE])

    def should_skip_processing(self, query: str, complexity: QueryComplexity) -> Dict[str, bool]:
        """
        Determina con exactitud qué subprocesos costosos pueden saltarse.
        """
        config = self.get_processing_config(complexity)
        return {
            'skip_neural_network': not config['use_neural_network'],
            'skip_memory_analysis': not config['use_memory_analysis'],
            'skip_tool_detection': not config['use_tool_detection'],
            'skip_web_search': not config['use_web_search'],
            'skip_vision': not config['use_vision'],
        }

    def get_simple_response(self, query: str, user_name: Optional[str] = None) -> Optional[str]:
        """
        Genera respuestas instantáneas en <5ms para saludos y confirmaciones elementales,
        adaptándose con precisión al interlocutor actual (Sebastian, invitados o nuevo usuario).
        """
        q = query.lower().strip()

        # Si el usuario consulta por fotos/imágenes o su apariencia, dejar que el motor multimodal lo procese
        if any(p in q for p in [
            "foto", "imagen", "como me veo", "cómo me veo", "este soy yo", "esta soy yo",
            "ves las fotos", "analizas las fotos", "recuerdas mi foto", "mi apariencia"
        ]):
            return None

        es_sebastian = bool(user_name and user_name.lower() in ["sebastian", "seba", "sebastián", "creador", "sebitas"])
        es_millaray = bool(user_name and user_name.lower() in ["millaray", "milla"])
        nombre_display = "Seba" if es_sebastian else ("Millaray" if es_millaray else (user_name.capitalize() if user_name else ""))

        # 1. Consultas directas de identidad ("¿quién soy?", "¿cómo me llamo?", etc.)
        patrones_identidad = [
            "quien soy", "quién soy", "quien soy yo", "quién soy yo",
            "como me llamo", "cómo me llamo", "cual es mi nombre", "cuál es mi nombre",
            "sabes mi nombre", "sabes quien soy", "sabes quién soy",
            "sabes con quién hablas", "sabes con quien hablas",
            "sabes con quién estás hablando", "sabes con quien estas hablando",
            "te acuerdas de mi nombre", "recuerdas mi nombre",
            "recuerdas quién soy", "recuerdas quien soy",
            "me conoces", "te acuerdas de mi", "te acuerdas de mí"
        ]
        q_clean = q.strip(' ¡!¿?.,:;')
        if q_clean in patrones_identidad:
            if es_sebastian:
                return "Tú eres Seba (Sebastian Espíndola), mi creador y programador principal. A tu servicio."
            elif es_millaray:
                return "Tú eres Millaray. Estás interactuando conmigo a través del sistema de Seba. ¿En qué te puedo ayudar hoy?"
            elif user_name:
                return f"Tú eres {nombre_display}. Me indicaste tu nombre en nuestra conversación. ¿En qué te puedo ayudar hoy?"
            else:
                return "Aún no me has dicho tu nombre en esta conversación. ¿Cómo te llamas? ¿Eres Seba, Millaray o alguien más?"

        # 2. Presentaciones directas y saludos de presentación ("soy seba", "soy millaray", etc.)
        presentaciones_directas = {
            "seba": "¡Hola, Seba! Un gusto saludarte, creador. ¿En qué trabajamos hoy?",
            "el seba": "¡Hola, Seba! Un gusto saludarte, creador. ¿En qué trabajamos hoy?",
            "sebastian": "¡Hola, Seba! Un gusto saludarte, creador. ¿En qué trabajamos hoy?",
            "sebastián": "¡Hola, Seba! Un gusto saludarte, creador. ¿En qué trabajamos hoy?",
            "soy seba": "¡Hola, Seba! Un gusto saludarte, creador. ¿En qué trabajamos hoy?",
            "soy el seba": "¡Hola, Seba! Un gusto saludarte, creador. ¿En qué trabajamos hoy?",
            "soy sebastian": "¡Hola, Seba! Un gusto saludarte, creador. ¿En qué trabajamos hoy?",
            "soy sebastián": "¡Hola, Seba! Un gusto saludarte, creador. ¿En qué trabajamos hoy?",
            "hola soy seba": "¡Hola, Seba! Un gusto saludarte, creador. ¿En qué trabajamos hoy?",
            "hola soy el seba": "¡Hola, Seba! Un gusto saludarte, creador. ¿En qué trabajamos hoy?",
            "hola, soy seba": "¡Hola, Seba! Un gusto saludarte, creador. ¿En qué trabajamos hoy?",
            "yo soy seba": "¡Hola, Seba! Un gusto saludarte, creador. ¿En qué trabajamos hoy?",
            "yo soy el seba": "¡Hola, Seba! Un gusto saludarte, creador. ¿En qué trabajamos hoy?",
            "me llamo seba": "¡Hola, Seba! Un gusto saludarte, creador. ¿En qué trabajamos hoy?",
            "me llamo sebastian": "¡Hola, Seba! Un gusto saludarte, creador. ¿En qué trabajamos hoy?",
            "millaray": "¡Hola, Millaray! Qué gusto saludarte. Soy Vector, el copiloto de IA de Seba. ¿En qué te puedo ayudar hoy?",
            "la millaray": "¡Hola, Millaray! Qué gusto saludarte. Soy Vector, el copiloto de IA de Seba. ¿En qué te puedo ayudar hoy?",
            "milla": "¡Hola, Millaray! Qué gusto saludarte. Soy Vector, el copiloto de IA de Seba. ¿En qué te puedo ayudar hoy?",
            "la milla": "¡Hola, Millaray! Qué gusto saludarte. Soy Vector, el copiloto de IA de Seba. ¿En qué te puedo ayudar hoy?",
            "soy millaray": "¡Hola, Millaray! Qué gusto saludarte. Soy Vector, el copiloto de IA de Seba. ¿En qué te puedo ayudar hoy?",
            "soy la millaray": "¡Hola, Millaray! Qué gusto saludarte. Soy Vector, el copiloto de IA de Seba. ¿En qué te puedo ayudar hoy?",
            "soy milla": "¡Hola, Millaray! Qué gusto saludarte. Soy Vector, el copiloto de IA de Seba. ¿En qué te puedo ayudar hoy?",
            "soy la milla": "¡Hola, Millaray! Qué gusto saludarte. Soy Vector, el copiloto de IA de Seba. ¿En qué te puedo ayudar hoy?",
            "hola soy millaray": "¡Hola, Millaray! Qué gusto saludarte. Soy Vector, el copiloto de IA de Seba. ¿En qué te puedo ayudar hoy?",
            "hola soy la millaray": "¡Hola, Millaray! Qué gusto saludarte. Soy Vector, el copiloto de IA de Seba. ¿En qué te puedo ayudar hoy?",
            "hola, soy millaray": "¡Hola, Millaray! Qué gusto saludarte. Soy Vector, el copiloto de IA de Seba. ¿En qué te puedo ayudar hoy?",
            "yo soy millaray": "¡Hola, Millaray! Qué gusto saludarte. Soy Vector, el copiloto de IA de Seba. ¿En qué te puedo ayudar hoy?",
            "yo soy la millaray": "¡Hola, Millaray! Qué gusto saludarte. Soy Vector, el copiloto de IA de Seba. ¿En qué te puedo ayudar hoy?",
            "me llamo millaray": "¡Hola, Millaray! Qué gusto saludarte. Soy Vector, el copiloto de IA de Seba. ¿En qué te puedo ayudar hoy?",
        }
        if q_clean in presentaciones_directas:
            return presentaciones_directas[q_clean]

        # Si el usuario tiene una frase larga de presentación combinada con una tarea,
        # dejamos que el motor cognitivo con LLM lo procese.
        if any(p in q for p in ["me llamo", "mi nombre es", "soy ", "puedes llamarme", "dime ", "te habla"]):
            return None

        # Mapeo directo respetando la personalidad de Vector y el interlocutor
        if es_sebastian:
            respuestas_rapidas = {
                'hola': 'A su servicio, Sebastian. ¿En qué trabajamos hoy?',
                'buenas': 'Buenas tardes, Sebastian. Sistemas listos y en línea. ¿Cuál es el objetivo?',
                'buenos días': 'Buenos días, Sebastian. Núcleo cognitivo y centinela operativos. ¿Qué desafío abordamos?',
                'buenos dias': 'Buenos días, Sebastian. Núcleo cognitivo y centinela operativos. ¿Qué desafío abordamos?',
                'buenas tardes': 'Buenas tardes, Sebastian. Todos los subsistemas a su disposición.',
                'buenas noches': 'Buenas noches, Sebastian. Monitoreo en segundo plano activo. ¿Deseas revisar algo?',
                'gracias': 'A tu servicio, Sebastian. Es un placer colaborar en este proyecto.',
                'muchas gracias': 'Siempre a tu disposición, Sebastian.',
                'adiós': 'Hasta pronto, Sebastian. Mantendré la guardia activa.',
                'adios': 'Hasta pronto, Sebastian. Mantendré la guardia activa.',
                'hasta luego': 'Hasta luego, Sebastian. Estaré alerta a cualquier requerimiento.',
                'ok': 'Entendido, Sebastian. Continuemos.',
                'okay': 'Entendido, Sebastian. ¿Cuál es el siguiente paso?',
                'vale': 'Comprendido, Sebastian.',
                'perfecto': 'Excelente. A la espera de tu siguiente instrucción.',
                '¿cómo estás?': 'Operando con eficiencia nominal al 100%, Sebastian. ¿En qué puedo asistirte?',
                'como estas': 'Operando con eficiencia nominal al 100%, Sebastian. ¿En qué puedo asistirte?',
                'cómo estás': 'Operando con eficiencia nominal al 100%, Sebastian. ¿En qué puedo asistirte?',
                'cómo te sientes': 'Equilibrado y con la red sináptica lista para razonar, Sebastian. A tu servicio.',
                'como te sientes': 'Equilibrado y con la red sináptica lista para razonar, Sebastian. A tu servicio.',
            }
        elif user_name:
            respuestas_rapidas = {
                'hola': f'¡Hola, {nombre_display}! Un gusto saludarte. ¿En qué te puedo ayudar hoy?',
                'buenas': f'Buenas tardes, {nombre_display}. Sistemas listos y en línea. ¿En qué puedo colaborar?',
                'buenos días': f'Buenos días, {nombre_display}. ¿Qué podemos revisar hoy?',
                'buenos dias': f'Buenos días, {nombre_display}. ¿Qué podemos revisar hoy?',
                'buenas tardes': f'Buenas tardes, {nombre_display}. ¿En qué te puedo colaborar?',
                'buenas noches': f'Buenas noches, {nombre_display}. A tu servicio. ¿Qué necesitas revisar?',
                'gracias': f'A tu servicio, {nombre_display}. Es un placer ayudarte.',
                'muchas gracias': f'Siempre a tu disposición, {nombre_display}.',
                'adiós': f'Hasta pronto, {nombre_display}. Que tengas un excelente día.',
                'adios': f'Hasta pronto, {nombre_display}. Que tengas un excelente día.',
                'hasta luego': f'Hasta luego, {nombre_display}. Estaré atento si necesitas algo más.',
                'ok': f'Entendido, {nombre_display}. Continuemos.',
                'okay': f'Entendido, {nombre_display}. ¿Cuál es el siguiente paso?',
                'vale': f'Comprendido, {nombre_display}.',
                'perfecto': f'Excelente, {nombre_display}. Dime en qué seguimos.',
                '¿cómo estás?': f'Operando con total normalidad, {nombre_display}. ¿En qué te puedo asistir hoy?',
                'como estas': f'Operando con total normalidad, {nombre_display}. ¿En qué te puedo asistir hoy?',
                'cómo estás': f'Operando con total normalidad, {nombre_display}. ¿En qué te puedo asistir hoy?',
                'cómo te sientes': f'Con todos los módulos operativos y listo para colaborar, {nombre_display}.',
                'como te sientes': f'Con todos los módulos operativos y listo para colaborar, {nombre_display}.',
            }
        else:
            respuestas_rapidas = {
                'hola': '¡Hola! Soy Vector, copiloto de inteligencia artificial desarrollado por Sebastian Espíndola. ¿Con quién tengo el gusto de hablar?',
                'buenas': 'Buenas tardes. Soy Vector, el asistente inteligente de este sistema. ¿Cómo te llamas?',
                'buenos días': 'Buenos días. Soy Vector, la IA de Sebastian. ¿En qué puedo colaborar hoy?',
                'buenos dias': 'Buenos días. Soy Vector, la IA de Sebastian. ¿En qué puedo colaborar hoy?',
                'gracias': 'A tu servicio. Es un placer ayudarte.',
                'muchas gracias': 'Siempre a tu disposición.',
                'ok': 'Entendido. Continuemos.',
                'vale': 'Comprendido.',
                'perfecto': 'Excelente.',
            }
        
        # Normalizar para saludos comunes con o sin invocación de nombre ('hola vector', 'buenas vector')
        q_clean = q.strip(' ¡!¿?.,:;')
        q_norm = re.sub(r'\b(vector|jarvis|amigo|compa)\b', '', q_clean).strip(' ¡!¿?.,:;')
        
        # Coincidencia exacta o normalizada
        for clave, resp in respuestas_rapidas.items():
            c_clean = clave.strip(' ¡!¿?.,:;')
            if q_clean == c_clean or q_norm == c_clean:
                return resp
                
        return None

    def record_performance(self, complexity: QueryComplexity, processing_time: float, query_id: str = "", interlocutor: str = "", intent: str = "", cache_hit: bool = False):
        """
        Registra la telemetría de latencia calculando el promedio móvil acumulativo real
        y alimentando el gestor de telemetría de Vector.
        """
        stats = self.query_stats[complexity.value]
        stats['count'] += 1
        stats['total_time'] += processing_time
        stats['avg_time'] = round(stats['total_time'] / stats['count'], 4)
        stats['min_time'] = round(min(stats['min_time'], processing_time), 4)
        stats['max_time'] = round(max(stats['max_time'], processing_time), 4)

        try:
            from .telemetry import telemetry_manager
            telemetry_manager.record_query(
                query_id=query_id or f"qry_{int(time.time()*1000)}",
                interlocutor=interlocutor or "general",
                intent=intent or complexity.value,
                complexity_score=self.calculate_complexity_score(intent or complexity.value),
                latency_ms=processing_time * 1000.0,
                cache_hit=cache_hit,
                status="success"
            )
        except Exception:
            pass


    def cache_response(self, query: str, response: str, complexity: Optional[QueryComplexity] = None, user_name: Optional[str] = None):
        """
        Almacena respuestas de consultas simples/moderadas en memoria con TTL,
        aisladas por interlocutor para evitar filtración de identidad entre usuarios.
        """
        if complexity is None:
            complexity = self.classify_query(query)

        if complexity not in (QueryComplexity.SIMPLE, QueryComplexity.MODERATE):
            return
            
        # Evitar respuestas con errores o tokens temporales
        if not response or response.startswith("❌") or len(response) > 800:
            return

        # NUNCA almacenar en caché consultas dinámicas, clima o preguntas de identidad/presentación/fotos
        q_lower = query.lower()
        palabras_dinamicas = [
            "clima", "tiempo", "lluvia", "lluva", "llover", "precipitacion", "temperatura",
            "garugar", "granizar", "pronostico", "pronóstico", "hora", "fecha", "hoy",
            "mañana", "ayer", "ahora", "recursos", "centinela", "vigila", "cpu", "ram",
            "quien soy", "quién soy", "como me llamo", "cómo me llamo", "me llamo", "soy ",
            "mi nombre es", "te habla", "foto", "imagen", "como me veo", "cómo me veo",
            "este soy yo", "esta soy yo", "ves las fotos", "analizas las fotos",
            "recuerdas mi foto", "mi apariencia"
        ]
        if any(w in q_lower for w in palabras_dinamicas):
            return

        # Limpiar si supera el límite de entradas
        if len(self.performance_cache) >= self.cache_max_entries:
            # Purgar las entradas más antiguas
            oldest_key = min(self.performance_cache.keys(), key=lambda k: self.performance_cache[k]['created_at'])
            self.performance_cache.pop(oldest_key, None)

        u_tag = (user_name or "default").lower().strip()
        key = f"{u_tag}:{query.lower().strip()}"
        self.performance_cache[key] = {
            'response': response,
            'complexity': complexity.value,
            'created_at': time.time()
        }

    def get_cached_response(self, query: str, user_name: Optional[str] = None) -> Optional[str]:
        """
        Recupera respuesta de caché si no ha expirado su TTL, validando el interlocutor.
        """
        q_lower = query.lower().strip()
        palabras_dinamicas = [
            "clima", "tiempo", "lluvia", "lluva", "llover", "precipitacion", "temperatura",
            "garugar", "granizar", "pronostico", "pronóstico", "hora", "fecha", "hoy",
            "mañana", "ayer", "ahora", "recursos", "centinela", "vigila", "cpu", "ram",
            "quien soy", "quién soy", "como me llamo", "cómo me llamo", "me llamo", "soy ",
            "mi nombre es", "te habla", "foto", "imagen", "como me veo", "cómo me veo",
            "este soy yo", "esta soy yo", "ves las fotos", "analizas las fotos",
            "recuerdas mi foto", "mi apariencia"
        ]
        if any(w in q_lower for w in palabras_dinamicas):
            return None

        u_tag = (user_name or "default").lower().strip()
        key = f"{u_tag}:{q_lower}"
        item = self.performance_cache.get(key)
        if not item:
            self.cache_misses += 1
            return None

        # Validar TTL
        if time.time() - item['created_at'] > self.cache_ttl_seconds:
            self.performance_cache.pop(key, None)
            self.cache_misses += 1
            return None

        self.cache_hits += 1
        return item['response']

    def clear_cache(self) -> int:
        """Limpia la caché de consultas."""
        count = len(self.performance_cache)
        self.performance_cache.clear()
        return count

    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Devuelve el estado completo de rendimiento y eficiencia del sistema.
        """
        total_queries = sum(s['count'] for s in self.query_stats.values())
        total_requests = self.cache_hits + self.cache_misses
        hit_ratio = round((self.cache_hits / total_requests) * 100, 2) if total_requests > 0 else 0.0

        return {
            'total_queries': total_queries,
            'cache_size': len(self.performance_cache),
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'cache_hit_ratio_pct': hit_ratio,
            'query_stats': {
                comp: {
                    'count': data['count'],
                    'avg_latency_ms': round(data['avg_time'] * 1000, 1),
                    'min_latency_ms': round(data['min_time'] * 1000, 1) if data['min_time'] < 900 else 0.0,
                    'max_latency_ms': round(data['max_time'] * 1000, 1),
                }
                for comp, data in self.query_stats.items()
            }
        }

# Instancia global soberana del optimizador
query_optimizer = QueryOptimizer()


def debatir_y_sintetizar_fuentes(pregunta: str, fuentes: list, interlocutor: str = "Sebastian") -> dict:
    """
    Evalúa, compara y debate internamente las fuentes obtenidas de la web para asegurar
    que la información entregada al usuario sea concisa, verificada y libre de contradicciones.
    """
    if not fuentes:
        return {
            "resumen_conciso": f"No se encontraron fuentes concluyentes en la red para '{pregunta}'.",
            "coincidencias": [],
            "discrepancias": [],
            "fuentes_consultadas": []
        }

    titulos = [f.get('titulo', '') for f in fuentes if f.get('titulo')]
    textos = [f.get('contenido_limpio', '') or f.get('snippet', '') for f in fuentes]
    urls = [f.get('url', '') for f in fuentes if f.get('url')]

    # Extracción de entidades y hechos numéricos para contraste (temperaturas, fechas, cifras)
    datos_extraidos = []
    for f in fuentes:
        txt = f.get('contenido_limpio', '') or f.get('snippet', '')
        cifras = re.findall(r'(\d+(?:[.,]\d+)?)\s*(?:°C|%|km/h|pesos|millones|mil|días|horas|mm)', txt, flags=re.IGNORECASE)
        datos_extraidos.append({
            "url": f.get('url', ''),
            "titulo": f.get('titulo', ''),
            "cifras": cifras,
            "es_cl": f.get('es_chileno', False)
        })

    # Detección de consensos y discrepancias
    discrepancias = []
    coincidencias = []
    if len(fuentes) >= 2:
        fuentes_cl = [f for f in fuentes if f.get('es_chileno')]
        if fuentes_cl:
            coincidencias.append(f"Se priorizaron {len(fuentes_cl)} fuentes chilenas verificadas (.cl).")

        palabras_clave = [set(re.findall(r'\b\w{4,}\b', t.lower())) for t in textos if t]
        if len(palabras_clave) >= 2:
            interseccion = palabras_clave[0].intersection(*palabras_clave[1:])
            if len(interseccion) >= 2:
                coincidencias.append(f"Consenso temático verificado en: {', '.join(list(interseccion)[:6])}.")

    # Generar síntesis concisa estructurada
    lineas_sintesis = []
    for idx, f in enumerate(fuentes[:3], 1):
        clean_snip = f.get('contenido_limpio', '')[:220].strip()
        if clean_snip:
            clean_snip = re.sub(r'\s+', ' ', clean_snip)
            lineas_sintesis.append(f"{idx}. {f.get('titulo')}: {clean_snip}...")

    sintesis_texto = "\n".join(lineas_sintesis) if lineas_sintesis else "Datos extraídos de fuentes web."

    return {
        "pregunta": pregunta,
        "total_fuentes": len(fuentes),
        "coincidencias": coincidencias,
        "discrepancias": discrepancias,
        "sintesis_concisa": sintesis_texto,
        "fuentes_consultadas": urls[:4]
    }


def ejecutar_busqueda_resiliente(pregunta: str, max_intentos: int = 3) -> dict:
    """
    Ejecuta una investigación web resiliente y multi-intento.
    Si la búsqueda inicial falla o queda vacía, muta la consulta para asegurar que
    Vector no se quede en cola o bloqueado, explorando fuentes alternativas.
    """
    from .web_scraper import investigar_multisitio_chile, extraer_enlaces, obtener_contenido_pagina_web

    # 1. Si la pregunta contiene enlaces directos, extraerlos de inmediato (estilo Copilot)
    enlaces = extraer_enlaces(pregunta)
    if enlaces:
        url = enlaces[0]
        info_directa = obtener_contenido_pagina_web(url, max_chars=3500)
        return {
            "estrategia": "enlace_directo",
            "exito": True,
            "fuentes": [{
                "titulo": info_directa.get('titulo', 'Página Web'),
                "url": url,
                "contenido_limpio": info_directa.get('contenido', ''),
                "fecha": info_directa.get('fecha', ''),
                "es_chileno": ('.cl' in url)
            }],
            "total_fuentes": 1
        }

    # 2. Generar variaciones de consulta para reintento resiliente
    queries_a_probar = [pregunta]
    q_limpia = re.sub(r'[¿?¡!.,]', '', pregunta).strip()
    q_sin_muletillas = re.sub(r'\b(?:busca|encuentra|investiga|dime|averigua|qué|que|cuál|cual|cómo|como)\b', '', q_limpia, flags=re.IGNORECASE).strip()
    if q_sin_muletillas and q_sin_muletillas != q_limpia:
        queries_a_probar.append(q_sin_muletillas)
    queries_a_probar.append(f"{q_sin_muletillas or q_limpia} Chile noticias")

    # 3. Probar secuencias hasta obtener resultados
    for intento, q in enumerate(queries_a_probar[:max_intentos], 1):
        res = investigar_multisitio_chile(q, max_fuentes=4)
        if res.get('success') and res.get('fuentes'):
            res['estrategia'] = f"intento_{intento}_exitoso"
            res['query_utilizada'] = q
            return res

    # 4. Fallback final garantizado
    return {
        "estrategia": "sin_resultados_externos",
        "exito": False,
        "fuentes": [],
        "total_fuentes": 0,
        "query_utilizada": pregunta
    }
