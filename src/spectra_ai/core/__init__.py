"""
Core data models for SpectraAI.

Contains dataclasses and models representing molecules, spectral data,
prediction results, and validation reports.
"""

from .molecule import Molecule, MoleculeMetadata
from .nmr_data import NMRData, NMRPeak, NMRSpectrum
from .ir_data import IRData, IRAbsorption
from .ms_data import MSData
from .uv_data import UVData, UVAbsorption
from .prediction_result import PredictionResult, StructureCandidate
from .validation_report import ValidationReport, ValidationCheck

__all__ = [
    "Molecule", "MoleculeMetadata",
    "NMRData", "NMRPeak", "NMRSpectrum",
    "IRData", "IRAbsorption",
    "MSData",
    "UVData", "UVAbsorption",
    "PredictionResult", "StructureCandidate",
    "ValidationReport", "ValidationCheck",
]
