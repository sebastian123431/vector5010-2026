"""
Módulo de Telemetría y Observabilidad para Vector 2026.
Monitorea la latencia, selección de intenciones, complejidad, uso de herramientas
y tasa de aciertos de caché para todo el pipeline cognitivo.
"""

import os
import json
import time
import logging
import threading
from datetime import datetime
from collections import deque, Counter
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class QueryTelemetryRecord:
    """Registro individual de telemetría para una consulta o interacción."""
    query_id: str
    timestamp: str
    interlocutor: str
    intent: str
    complexity_score: float
    latency_ms: float
    tools_invoked: List[str] = field(default_factory=list)
    planner_steps: int = 0
    cache_hit: bool = False
    status: str = "success"  # "success", "error", "blocked"
    error_message: Optional[str] = None
    identity_source: str = "unknown"
    identity_confidence: float = 1.0
    route: str = "tier_0"
    complexity: str = "simple"
    sandbox_blocks: int = 0
    # Métricas P2 de observabilidad e integración
    identity_id: Optional[str] = None
    identity_changed: bool = False
    query_tier: str = "tier_0"
    memory_backend: str = "faiss"
    memory_hits: int = 0
    reasoning_mode: str = "direct"
    tool_steps: int = 0
    failed_steps: int = 0
    verification_status: str = "n/a"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if not d.get("identity_id"):
            d["identity_id"] = self.interlocutor
        return d


class TelemetryManager:
    """
    Gestor de telemetría y métricas operacionales de Vector.
    Mantiene un buffer circular en memoria y provee agregación estadística.
    """

    def __init__(self, max_buffer_size: int = 1000, storage_path: Optional[str] = None):
        self.max_buffer_size = max_buffer_size
        self._buffer: deque = deque(maxlen=max_buffer_size)
        self._lock = threading.Lock()
        
        if storage_path:
            self.storage_path = storage_path
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self.storage_path = os.path.join(base_dir, "workspace", "telemetry.json")

    def record_query(
        self,
        query_id: str,
        interlocutor: str,
        intent: str,
        complexity_score: float,
        latency_ms: float,
        tools_invoked: Optional[List[str]] = None,
        planner_steps: int = 0,
        cache_hit: bool = False,
        status: str = "success",
        error_message: Optional[str] = None,
        identity_source: str = "unknown",
        identity_confidence: float = 1.0,
        route: str = "tier_0",
        complexity: Optional[str] = None,
        sandbox_blocks: int = 0,
        identity_id: Optional[str] = None,
        identity_changed: bool = False,
        query_tier: Optional[str] = None,
        memory_backend: str = "faiss",
        memory_hits: int = 0,
        reasoning_mode: str = "direct",
        tool_steps: int = 0,
        failed_steps: int = 0,
        verification_status: str = "n/a"
    ) -> QueryTelemetryRecord:
        """
        Registra una consulta en el buffer de telemetría.
        Garantiza privacidad estricta: jamás registra biometría en bruto ni credenciales privadas.
        """
        if complexity is None:
            if complexity_score <= 0.20:
                complexity = "simple"
            elif complexity_score <= 0.45:
                complexity = "moderate"
            elif complexity_score <= 0.74:
                complexity = "complex"
            else:
                complexity = "intensive"

        if query_tier is None:
            query_tier = route

        resolved_identity_id = identity_id if identity_id is not None else interlocutor

        record = QueryTelemetryRecord(
            query_id=query_id,
            timestamp=datetime.now().isoformat(),
            interlocutor=interlocutor,
            intent=intent,
            complexity_score=round(float(complexity_score), 4),
            latency_ms=round(float(latency_ms), 2),
            tools_invoked=tools_invoked or [],
            planner_steps=planner_steps,
            cache_hit=cache_hit,
            status=status,
            error_message=error_message,
            identity_source=identity_source,
            identity_confidence=round(float(identity_confidence), 4),
            route=route,
            complexity=complexity,
            sandbox_blocks=sandbox_blocks,
            identity_id=resolved_identity_id,
            identity_changed=identity_changed,
            query_tier=query_tier,
            memory_backend=memory_backend,
            memory_hits=memory_hits,
            reasoning_mode=reasoning_mode,
            tool_steps=tool_steps,
            failed_steps=failed_steps,
            verification_status=verification_status
        )

        with self._lock:
            self._buffer.append(record)

        return record

    def get_recent_records(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retorna las consultas más recientes registradas."""
        with self._lock:
            records = list(self._buffer)
        return [r.to_dict() for r in records[-limit:]][::-1]

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Calcula métricas agregadas operacionales."""
        with self._lock:
            records = list(self._buffer)

        total = len(records)
        if total == 0:
            return {
                "total_queries": 0,
                "avg_latency_ms": 0.0,
                "cache_hit_rate": 0.0,
                "error_rate": 0.0,
                "intent_distribution": {},
                "complexity_distribution": {
                    "simple": 0,
                    "moderate": 0,
                    "complex": 0,
                    "intensive": 0
                },
                "total_tools_invoked": 0,
                "total_sandbox_blocks": 0,
                "identity_source_distribution": {},
                "route_distribution": {}
            }

        total_latency = sum(r.latency_ms for r in records)
        cache_hits = sum(1 for r in records if r.cache_hit)
        errors = sum(1 for r in records if r.status == "error")
        all_tools = sum(len(r.tools_invoked) for r in records)
        total_sandbox_blocks = sum(r.sandbox_blocks for r in records)

        # Distribuciones agregadas
        intents = Counter(r.intent for r in records)
        identity_sources = Counter(r.identity_source for r in records)
        routes = Counter(r.route for r in records)

        # Distribución de complejidad
        complexity_counts = {"simple": 0, "moderate": 0, "complex": 0, "intensive": 0}
        for r in records:
            c = r.complexity_score
            if c <= 0.20:
                complexity_counts["simple"] += 1
            elif c <= 0.45:
                complexity_counts["moderate"] += 1
            elif c <= 0.74:
                complexity_counts["complex"] += 1
            else:
                complexity_counts["intensive"] += 1

        return {
            "total_queries": total,
            "avg_latency_ms": round(total_latency / total, 2),
            "cache_hit_rate": round(cache_hits / total, 4),
            "error_rate": round(errors / total, 4),
            "intent_distribution": dict(intents),
            "identity_source_distribution": dict(identity_sources),
            "route_distribution": dict(routes),
            "complexity_distribution": complexity_counts,
            "total_tools_invoked": all_tools,
            "total_sandbox_blocks": total_sandbox_blocks
        }

    def clear(self):
        """Limpia el buffer de telemetría."""
        with self._lock:
            self._buffer.clear()


# Instancia singleton para uso en toda la aplicación
telemetry_manager = TelemetryManager()
