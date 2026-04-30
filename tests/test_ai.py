"""
SpectraAI AI Module Test Suite.

Tests prompt generation, response parsing, and client configuration
WITHOUT making actual API calls (no API key required).
"""

import json
import os
import pytest
from spectra_ai.core.nmr_data import NMRPeak
from spectra_ai.core.ir_data import IRAbsorption
from spectra_ai.core.ms_data import MSData


# ══════════════════════════════════════════════════════════════════════════════
#  Prompt Template Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestH1Prompt:
    """Test ¹H NMR interpretation prompt generation."""

    def test_system_prompt_exists(self):
        from spectra_ai.ai.prompts.interpret_h1 import SYSTEM_PROMPT
        assert len(SYSTEM_PROMPT) > 100
        assert "NMR" in SYSTEM_PROMPT or "organic" in SYSTEM_PROMPT.lower()

    def test_build_user_prompt_basic(self):
        from spectra_ai.ai.prompts.interpret_h1 import build_user_prompt
        prompt = build_user_prompt(
            peaks_text="δ 7.26 (s, 1H), 3.85 (s, 3H, OCH3)",
            frequency=400,
            solvent="CDCl3",
            smiles="COc1ccccc1",
            formula="C7H8O",
        )
        assert "400" in prompt
        assert "CDCl3" in prompt
        assert "7.26" in prompt

    def test_build_user_prompt_with_scaffold(self):
        from spectra_ai.ai.prompts.interpret_h1 import build_user_prompt
        prompt = build_user_prompt(
            peaks_text="δ 8.15 (d, J = 6.8 Hz, 1H)",
            frequency=400,
            solvent="CDCl3",
            scaffold_family="imidazopyridine",
        )
        assert len(prompt) > 20

    def test_build_user_prompt_minimal(self):
        from spectra_ai.ai.prompts.interpret_h1 import build_user_prompt
        prompt = build_user_prompt(peaks_text="δ 7.50 (s, 1H)")
        assert "7.50" in prompt or "7.5" in prompt


class TestC13Prompt:
    def test_system_prompt(self):
        from spectra_ai.ai.prompts.interpret_c13 import SYSTEM_PROMPT
        assert len(SYSTEM_PROMPT) > 50

    def test_build_user_prompt(self):
        from spectra_ai.ai.prompts.interpret_c13 import build_user_prompt
        prompt = build_user_prompt(
            peaks_text="δ 159.7, 128.4, 55.4",
            formula="C14H12N2O",
        )
        assert "159.7" in prompt
        assert "55.4" in prompt


class TestIRPrompt:
    def test_system_prompt(self):
        from spectra_ai.ai.prompts.interpret_ir import SYSTEM_PROMPT
        assert len(SYSTEM_PROMPT) > 50

    def test_build_user_prompt(self):
        from spectra_ai.ai.prompts.interpret_ir import build_user_prompt
        prompt = build_user_prompt(
            bands_text="3312 (m), 1658 (s), 1598 (m) cm⁻¹",
            formula="C14H12N2O",
        )
        assert "3312" in prompt
        assert "1658" in prompt


class TestMSPrompt:
    def test_system_prompt(self):
        from spectra_ai.ai.prompts.validate_ms import SYSTEM_PROMPT
        assert len(SYSTEM_PROMPT) > 50

    def test_build_user_prompt(self):
        from spectra_ai.ai.prompts.validate_ms import build_user_prompt
        prompt = build_user_prompt(
            ms_text="HRMS (ESI) m/z calcd for C14H13N2O [M+H]+ 225.1022, found 225.1019",
            formula="C14H12N2O",
        )
        assert "225.1022" in prompt


class TestCrossSpectralPrompt:
    def test_system_prompt(self):
        from spectra_ai.ai.prompts.cross_spectral import SYSTEM_PROMPT
        assert len(SYSTEM_PROMPT) > 50

    def test_build_user_prompt(self):
        from spectra_ai.ai.prompts.cross_spectral import build_user_prompt
        prompt = build_user_prompt(
            name="Test Compound",
            formula="C14H12N2O",
            smiles="COc1ccc(-c2cnc3ccccn23)cc1",
            h1_summary="8 peaks observed, 12H total",
            c13_summary="12 peaks observed",
            ir_summary="Key bands: 1510, 1249 cm⁻¹",
            ms_summary="[M+H]+ 225.1019 (Δ 1.3 ppm)",
        )
        assert "C14H12N2O" in prompt


class TestPredictStructurePrompt:
    def test_system_prompt(self):
        from spectra_ai.ai.prompts.predict_structure import SYSTEM_PROMPT
        assert len(SYSTEM_PROMPT) > 50


class TestCharacterizationPrompt:
    def test_system_prompt(self):
        from spectra_ai.ai.prompts.write_characterization import SYSTEM_PROMPT
        assert len(SYSTEM_PROMPT) > 50

    def test_build_user_prompt(self):
        from spectra_ai.ai.prompts.write_characterization import build_user_prompt
        prompt = build_user_prompt(
            name="3-(4-Methoxyphenyl)imidazo[1,2-a]pyridine",
            formula="C14H12N2O",
            h1_data="δ 8.15 (d, 1H), 7.85 (d, 2H)",
        )
        assert "C14H12N2O" in prompt


class TestPredictReactionPrompt:
    def test_system_prompt(self):
        from spectra_ai.ai.prompts.predict_reaction import SYSTEM_PROMPT
        assert len(SYSTEM_PROMPT) > 50


# ══════════════════════════════════════════════════════════════════════════════
#  LLM Client Tests (skip if packages missing)
# ══════════════════════════════════════════════════════════════════════════════


class TestLLMClient:
    def test_import(self):
        from spectra_ai.ai.llm_client import LLMClient, AIProvider
        assert AIProvider.CLAUDE is not None
        assert AIProvider.GEMINI is not None

    def test_create_claude_client(self):
        from spectra_ai.ai.llm_client import LLMClient
        try:
            client = LLMClient(provider="claude")
            assert client.provider_display_name in ("Claude", "claude")
        except ImportError:
            pytest.skip("anthropic package not installed")

    def test_create_gemini_client(self):
        from spectra_ai.ai.llm_client import LLMClient
        try:
            client = LLMClient(provider="gemini")
            assert client.provider_display_name in ("Gemini", "gemini")
        except ImportError:
            pytest.skip("google-generativeai package not installed")

    def test_not_configured_without_key(self):
        from spectra_ai.ai.llm_client import LLMClient
        saved = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            client = LLMClient(provider="claude")
            assert not client.is_configured
        except ImportError:
            pytest.skip("anthropic package not installed")
        finally:
            if saved:
                os.environ["ANTHROPIC_API_KEY"] = saved


# ══════════════════════════════════════════════════════════════════════════════
#  Interpreter Module Import Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestNMRInterpreter:
    def test_import(self):
        from spectra_ai.ai.nmr_interpreter import NMRInterpreter
        assert NMRInterpreter is not None

    def test_h1_prompt_builds(self):
        from spectra_ai.ai.prompts.interpret_h1 import SYSTEM_PROMPT, build_user_prompt
        user = build_user_prompt(
            peaks_text="δ 8.15 (d, J = 6.8 Hz, 1H, H-5)",
            frequency=400,
            solvent="CDCl3",
        )
        assert len(SYSTEM_PROMPT) > 0
        assert len(user) > 0
        assert "8.15" in user


class TestIRInterpreter:
    def test_import(self):
        from spectra_ai.ai.ir_interpreter import IRInterpreter
        assert IRInterpreter is not None


class TestMSValidator:
    def test_import(self):
        from spectra_ai.ai.ms_validator import MSValidator
        assert MSValidator is not None


class TestCrossSpectralAnalyzer:
    def test_import(self):
        from spectra_ai.ai.cross_spectral_analyzer import CrossSpectralAnalyzer
        assert CrossSpectralAnalyzer is not None


class TestCharacterizationWriter:
    def test_import(self):
        from spectra_ai.ai.characterization_writer import CharacterizationWriter
        assert CharacterizationWriter is not None


class TestStructurePredictor:
    def test_import(self):
        from spectra_ai.ai.structure_predictor import StructurePredictor
        assert StructurePredictor is not None


class TestReactionPredictor:
    def test_import(self):
        from spectra_ai.ai.reaction_predictor import ReactionPredictor
        assert ReactionPredictor is not None


class TestImpurityDetector:
    def test_import(self):
        from spectra_ai.ai.impurity_detector import ImpurityDetector
        assert ImpurityDetector is not None
