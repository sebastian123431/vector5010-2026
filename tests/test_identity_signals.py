import os
import django

if not os.environ.get("DJANGO_SETTINGS_MODULE"):
    os.environ["DJANGO_SETTINGS_MODULE"] = "vector5010.settings"
    django.setup()

import unittest
from vectorapp.identity import (
    IdentitySource,
    IdentityStatus,
    IdentityState,
    IdentitySignal,
    IdentityResolver,
    VisionIdentityProcessor,
    VoiceIdentityProcessor,
    MultimodalIdentityProcessor,
)


class TestIdentitySignals(unittest.TestCase):
    """
    Pruebas unitarias para el subsistema de señales multimodales (Visión y Voz)
    y resolución epistemológica de conflictos y consensos.
    """

    def setUp(self):
        self.vision_proc = VisionIdentityProcessor(confidence_threshold=0.85)
        self.voice_proc = VoiceIdentityProcessor(confidence_threshold=0.80)
        self.multi_proc = MultimodalIdentityProcessor(self.vision_proc, self.voice_proc)

    def test_vision_processor_threshold(self):
        """Verifica que el procesador visual genere señales por encima del umbral (0.85)."""
        sig_high = self.vision_proc.extract_signal(
            image_input=None, candidate_hint="Seba", confidence_hint=0.88, session_id="s1"
        )
        self.assertIsNotNone(sig_high)
        self.assertEqual(sig_high.candidate, "Seba")
        self.assertEqual(sig_high.source, IdentitySource.FACE)
        self.assertGreaterEqual(sig_high.confidence, 0.85)

    def test_voice_processor_threshold(self):
        """Verifica que el procesador vocal genere señales por encima del umbral (0.80)."""
        sig_voice = self.voice_proc.extract_signal(
            audio_input=None, candidate_hint="Juan", confidence_hint=0.82, session_id="s1"
        )
        self.assertIsNotNone(sig_voice)
        self.assertEqual(sig_voice.candidate, "Juan")
        self.assertEqual(sig_voice.source, IdentitySource.VOICE)
        self.assertGreaterEqual(sig_voice.confidence, 0.80)

    def test_multimodal_consensus(self):
        """Cuando Visión y Voz coinciden en el mismo interlocutor, se refuerza la certeza."""
        sig_face = IdentitySignal(candidate="Juan", confidence=0.88, source=IdentitySource.FACE)
        sig_voice = IdentitySignal(candidate="Juan", confidence=0.84, source=IdentitySource.VOICE)

        state, is_new = IdentityResolver.resolve_identity(
            current_state=None,
            signals=[sig_face, sig_voice],
            session_id="s_consensus"
        )

        self.assertEqual(state.identity_id, "juan")
        self.assertEqual(state.display_name, "Juan")
        self.assertEqual(state.status, IdentityStatus.RECOGNIZED)
        self.assertGreaterEqual(state.confidence, 0.90)  # Reforzado por ambos canales
        self.assertIn("reinforced_by", state.metadata)

    def test_multimodal_conflict_leads_to_ambiguous(self):
        """Si la cámara ve a 'Juan' (conf 0.88) pero la voz es de 'Pedro' (conf 0.85), el estado pasa a AMBIGUOUS."""
        sig_face = IdentitySignal(candidate="Juan", confidence=0.88, source=IdentitySource.FACE)
        sig_voice = IdentitySignal(candidate="Pedro", confidence=0.85, source=IdentitySource.VOICE)

        state, changed = IdentityResolver.resolve_identity(
            current_state=None,
            signals=[sig_face, sig_voice],
            session_id="s_conflict"
        )

        self.assertEqual(state.status, IdentityStatus.AMBIGUOUS)
        self.assertIn("conflict", state.metadata)
        self.assertEqual(state.metadata.get("conflict"), "multimodal_divergence")

    def test_explicit_text_trumps_weak_biometric(self):
        """Texto explícito 'Soy Juan' prevalece sobre una señal biométrica débil o contraria."""
        sig_text = IdentitySignal(candidate="Juan", confidence=1.0, source=IdentitySource.EXPLICIT_TEXT)
        sig_weak_face = IdentitySignal(candidate="Pedro", confidence=0.60, source=IdentitySource.FACE)

        state, is_new = IdentityResolver.resolve_identity(
            current_state=None,
            signals=[sig_text, sig_weak_face],
            session_id="s_text_win"
        )

        self.assertEqual(state.identity_id, "juan")
        self.assertEqual(state.display_name, "Juan")
        self.assertEqual(state.status, IdentityStatus.DECLARED)
        self.assertIn("contrary_biometrics_suppressed", state.metadata)

    def test_declared_identity_not_silently_overwritten_by_face(self):
        """Un interlocutor que declaró ser 'Juan' no es sobreescrito silenciosamente por una cámara que detecta 'Seba'."""
        current_state = IdentityState(
            identity_id="juan",
            display_name="Juan",
            confidence=1.0,
            source=IdentitySource.EXPLICIT_TEXT,
            status=IdentityStatus.DECLARED,
            session_id="s_decl"
        )

        sig_face = IdentitySignal(candidate="Seba", confidence=0.89, source=IdentitySource.FACE)

        new_state, changed = IdentityResolver.resolve_identity(
            current_state=current_state,
            signals=[sig_face],
            session_id="s_decl"
        )

        # No se sobreescribe como Seba; se marca como AMBIGUOUS para solicitar aclaración
        self.assertEqual(new_state.status, IdentityStatus.AMBIGUOUS)
        self.assertEqual(new_state.identity_id, "juan")
        self.assertFalse(changed)
