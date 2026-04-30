"""
AI Engine for SpectraAI.

Provides generative AI-powered spectral interpretation, structure
prediction, validation, and text generation using Claude or Gemini APIs.
"""

from .llm_client import LLMClient, AIProvider
from .nmr_interpreter import NMRInterpreter
from .ir_interpreter import IRInterpreter
from .ms_validator import MSValidator
from .structure_predictor import StructurePredictor
from .cross_spectral_analyzer import CrossSpectralAnalyzer
from .characterization_writer import CharacterizationWriter

__all__ = [
    "LLMClient", "AIProvider",
    "NMRInterpreter", "IRInterpreter", "MSValidator",
    "StructurePredictor", "CrossSpectralAnalyzer",
    "CharacterizationWriter",
]
