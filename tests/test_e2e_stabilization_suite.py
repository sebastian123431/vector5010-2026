"""
Suite de Validación End-to-End de Estabilización de VECTOR 2026.
Implementa las pruebas obligatorias E2E:
1. Memoria conversacional y aislamiento estricto (Juan vs Seba).
2. Persistencia y recuperación FAISS post-reinicio.
3. Fallo real de herramienta (success=False -> FAILED).
4. Extracción y análisis ZIP real vía ReasoningEngine.
5. Control de PendingAction (mismatch, replay prevention).
6. Clasificación de Tiers en QueryRouter.
"""

import os
import zipfile
import tempfile
from django.test import TestCase
from vectorapp.identity.manager import identity_manager
from vectorapp.memory.manager import MemoryManager, memory_manager
from vectorapp.neural_network import semantic_network
from vectorapp.cognition.reasoning_engine import ReasoningEngine, ReasoningMode
from vectorapp.security.action_policy import PendingActionManager
from vectorapp.query_optimizer import query_optimizer, QueryComplexity


class TestVector2026StabilizationE2E(TestCase):
    """Pruebas integrales de extremo a extremo para validar la estabilización definitiva."""

    def test_e2e_1_memory_conversational_isolation(self):
        """E2E-1: Juan recuerda VS Code; Seba NO puede acceder a las preferencias de Juan."""
        # Turno 1 & 2: Juan establece preferencia
        juan_ident = "juan_developer_id"
        memory_manager.store(
            content="Recuerda que mi editor favorito es VS Code.",
            user_name="Juan",
            identity_id=juan_ident,
            scope="PERSONAL"
        )

        # Turno 3: Juan consulta su preferencia
        juan_recall = memory_manager.recall(
            query="¿Cuál es mi editor favorito?",
            identity_id=juan_ident,
            user_name="Juan",
            top_k=3
        )
        juan_texts = [r.get("content", "") for r in juan_recall]
        self.assertTrue(any("VS Code" in t for t in juan_texts), "Juan debe recuperar su editor favorito")

        # Turno 4 & 5: Seba consulta su preferencia
        seba_ident = "seba_admin_id"
        seba_recall = memory_manager.recall(
            query="¿Cuál es mi editor favorito?",
            identity_id=seba_ident,
            user_name="Seba",
            top_k=5
        )
        seba_texts = [r.get("content", "") for r in seba_recall]

        # REGLA CRÍTICA: Seba NUNCA debe ver la preferencia de Juan
        for item_text in seba_texts:
            self.assertNotIn("VS Code", item_text, "Fuga detectada: Seba no debe recuperar memorias de Juan")

        # Comprobar además que la preferencia personal NO contaminó el grafo global
        if hasattr(semantic_network, "graph"):
            nodes_text = " ".join([str(n) for n in semantic_network.graph.nodes])
            self.assertNotIn("VS Code", nodes_text, "Preferencia personal no debe estar en grafo global")

    def test_e2e_2_faiss_restart_and_bootstrap(self):
        """E2E-2: Persistencia SQLite + FAISS y recuperación intacta tras reinicio y bootstrap."""
        ident = "juan_restart_test"
        # 1. Guardar memoria en SQLite y FAISS
        memory_manager.store(
            content="Mi framework predilecto para backend es Django 5.2.",
            user_name="Juan",
            identity_id=ident,
            scope="PERSONAL"
        )

        # 2. Simular reinicio creando un nuevo MemoryManager
        fresh_memory_manager = MemoryManager(use_faiss=True)
        # 3. Ejecutar bootstrap idempotente
        loaded = fresh_memory_manager.bootstrap(force=True)
        self.assertGreaterEqual(loaded, 1)

        # 4. Juan consulta tras el reinicio
        recalled = fresh_memory_manager.recall(
            query="¿Cuál es mi framework predilecto?",
            identity_id=ident,
            top_k=3
        )
        recalled_texts = [r.get("content", "") for r in recalled]
        self.assertTrue(any("Django 5.2" in t for t in recalled_texts), "Memoria debe persistir y ser recuperable post-reinicio")

    def test_e2e_3_tool_failure_marks_failed(self):
        """E2E-3: Si una tool retorna success=False, PlanStep es FAILED y ReasoningEngine.success es False."""
        def fake_error_tool(tool_name: str, tool_input: dict):
            return {
                "success": False,
                "error": "Conexión rechazada por el servidor destino",
                "result": None
            }

        engine = ReasoningEngine(tool_runner=fake_error_tool)
        res = engine.reason(
            query="investigar noticias y clima",
            mode=ReasoningMode.EXECUTE
        )

        # La herramienta web_search falla simuladamente
        self.assertFalse(res["success"], "ReasoningEngine no puede reportar éxito si una tool falló")
        self.assertFalse(res["execution"]["success"], "Execution debe ser False")
        self.assertFalse(res["verification"]["passed"], "Post-execution verification debe ser False")
        steps = res["plan"]["steps"]
        failed_steps = [s for s in steps if s["status"] in ("failed", "FAILED")]
        self.assertGreater(len(failed_steps), 0, "Debe existir al menos un step FAILED")

    def test_e2e_4_zip_real_execution(self):
        """E2E-4: Pipeline completo de extracción ZIP real vía Router -> ReasoningEngine -> ToolRunner."""
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "test_code.zip")
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("module_alpha.py", "def compute_alpha(x):\n    return x * 2\n")

            engine = ReasoningEngine()
            res = engine.reason(
                query="analiza este proyecto ZIP",
                context={"file_path": zip_path, "project_name": "test_pkg"},
                mode=ReasoningMode.EXECUTE
            )

            # Debe haber ejecutado el step 1 con extract_zip exitosamente
            self.assertTrue(res["execution"]["success"], f"Fallo en ejecución: {res['execution']}")
            self.assertTrue(res["verification"]["passed"])
            trace = res["execution"]["trace"]
            self.assertTrue(any(t.get("status") == "completed" for t in trace))

    def test_e2e_5_pending_action_security(self):
        """E2E-5: Validación estricta de PendingAction (parameter mismatch, autorización y replay)."""
        mgr = PendingActionManager()
        token_a = mgr.create_pending_action(
            action_type="delete_dynamic_tool",
            parameters={"tool_name": "tool_A"}
        )

        # 1. Intentar usar token de tool_A sobre tool_B -> DENIED
        denied_b, err_b = mgr.validate_and_consume(
            token_a,
            action_type="delete_dynamic_tool",
            parameters={"tool_name": "tool_B"}
        )
        self.assertFalse(denied_b)
        self.assertIn("mismatch", err_b.lower())

        # 2. Confirmar tool_A con token de tool_A -> ALLOWED
        allowed_a, err_a = mgr.validate_and_consume(
            token_a,
            action_type="delete_dynamic_tool",
            parameters={"tool_name": "tool_A"}
        )
        self.assertTrue(allowed_a)
        self.assertIsNone(err_a)

        # 3. Reutilizar token ya consumido -> DENIED
        replayed, err_replay = mgr.validate_and_consume(
            token_a,
            action_type="delete_dynamic_tool",
            parameters={"tool_name": "tool_A"}
        )
        self.assertFalse(replayed)

    def test_e2e_6_router_tiers(self):
        """E2E-6: Validación de clasificación de Tiers en QueryRouter."""
        # Saludo simple -> Tier 0 (Fast Path)
        r0 = query_optimizer.route_query("hola")
        self.assertEqual(r0.tier, 0)

        # Código -> Tier 1 o 2 (Coding)
        r1 = query_optimizer.route_query("corrige este código Python con error de sintaxis")
        self.assertIn(r1.tier, (1, 2))

        # Visión / Multimodal ambiguo -> Tier 2 (Gemma local)
        r2 = query_optimizer.route_query("mira esto")
        self.assertEqual(r2.tier, 2)
