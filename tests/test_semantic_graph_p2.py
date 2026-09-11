"""
Pruebas automatizadas para el Grafo Semántico y Aristas Tipadas (Fase P2).
Valida tipos de relaciones (SemanticRelationType), SemanticEdge, persistencia y consultas tipadas.
"""

import unittest
from vectorapp.neural_network import (
    SemanticNeuron, SemanticRelationType, SemanticEdge
)


class TestSemanticGraphP2(unittest.TestCase):

    def test_typed_edges_creation_and_filtering(self):
        """Valida que una neurona pueda conectar y filtrar aristas por tipo de relación."""
        n_vector = SemanticNeuron("vector", "Asistente Inteligente Vector", "concept")
        n_python = SemanticNeuron("python", "Lenguaje Python", "technical")
        n_gemma = SemanticNeuron("gemma", "Modelo Gemma 3 GGUF", "model")

        n_vector.connect_typed("python", SemanticRelationType.USES, strength=0.9)
        n_vector.connect_typed("gemma", SemanticRelationType.DEPENDS_ON, strength=0.95)

        # Conexiones numéricas para retrocompatibilidad
        self.assertEqual(n_vector.connections["python"], 0.9)
        self.assertEqual(n_vector.connections["gemma"], 0.95)

        # Consulta tipada
        uses_edges = n_vector.get_typed_edges(SemanticRelationType.USES)
        self.assertEqual(len(uses_edges), 1)
        self.assertEqual(uses_edges[0].target_id, "python")

        depends_edges = n_vector.get_typed_edges(SemanticRelationType.DEPENDS_ON)
        self.assertEqual(len(depends_edges), 1)
        self.assertEqual(depends_edges[0].target_id, "gemma")

    def test_typed_edges_serialization_cycle(self):
        """Valida que las aristas tipadas se serialicen y deserialicen sin pérdida."""
        n1 = SemanticNeuron("bug_01", "Fallo de sintaxis", "error")
        n1.connect_typed("patch_01", SemanticRelationType.SOLVES, strength=1.0)

        data = n1.to_dict()
        self.assertIn("typed_edges", data)
        self.assertIn("patch_01", data["typed_edges"])
        self.assertEqual(data["typed_edges"]["patch_01"]["relation_type"], "solves")

        n1_restored = SemanticNeuron.from_dict(data)
        self.assertIn("patch_01", n1_restored.typed_edges)
        self.assertEqual(n1_restored.typed_edges["patch_01"].relation_type, SemanticRelationType.SOLVES)
        self.assertEqual(n1_restored.connections["patch_01"], 1.0)

    def test_strengthen_and_weaken_typed_edges(self):
        """Valida que el refuerzo o debilitamiento hebbiano sincronice conexiones y aristas tipadas."""
        n = SemanticNeuron("origin", "Origen")
        n.connect_typed("dest", SemanticRelationType.CAUSES, strength=0.5)

        n.strengthen_connection("dest", amount=0.2)
        self.assertAlmostEqual(n.connections["dest"], 0.7)
        self.assertAlmostEqual(n.typed_edges["dest"].strength, 0.7)

        n.weaken_connection("dest", amount=0.65)  # Cae por debajo de 0.1 -> poda
        self.assertNotIn("dest", n.connections)
        self.assertNotIn("dest", n.typed_edges)


if __name__ == "__main__":
    unittest.main()
