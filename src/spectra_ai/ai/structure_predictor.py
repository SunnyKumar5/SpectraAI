"""
Structure Predictor — AI-powered scaffold-constrained structure elucidation.

Given spectral data (with or without SMILES), generates ranked candidate
structures constrained to specific heterocyclic scaffold families.
"""

from __future__ import annotations

from .llm_client import LLMClient
from .prompts import predict_structure
from ..core.molecule import Molecule
from ..core.nmr_data import NMRData
from ..core.prediction_result import PredictionResult, StructureCandidate


class StructurePredictor:
    """AI-powered structure prediction with scaffold constraints."""

    def __init__(self, client: LLMClient):
        self.client = client

    def predict(self, molecule: Molecule, h1_data: NMRData = None,
                c13_data: NMRData = None) -> PredictionResult:
        """
        Predict or verify molecular structure from spectral data.

        Mode A (SMILES given): Verify structure against spectra
        Mode B (no SMILES):    Generate candidate structures

        Returns:
            PredictionResult with ranked candidates
        """
        mode = "verify" if molecule.has_smiles else "predict"

        h1_text = ""
        if h1_data:
            h1_text = h1_data.raw_text or "; ".join(
                p.display_text for p in h1_data.sorted_peaks()
            )

        c13_text = ""
        if c13_data:
            c13_text = c13_data.raw_text or "δ " + ", ".join(
                f"{p.chemical_shift:.1f}" for p in c13_data.sorted_peaks()
            )

        user_prompt = predict_structure.build_user_prompt(
            mode=mode,
            smiles=molecule.smiles,
            formula=molecule.formula,
            scaffold_family=molecule.metadata.scaffold_family,
            h1_text=h1_text,
            c13_text=c13_text,
            name=molecule.name,
        )

        result = self.client.generate_json(
            system=predict_structure.SYSTEM_PROMPT,
            user=user_prompt,
            temperature=0.3,
            max_tokens=4096,
        )

        if result is None:
            return PredictionResult(
                warnings=["AI returned non-structured response"],
                method=mode,
            )

        candidates = []
        for i, c in enumerate(result.get("candidates", [])):
            candidates.append(StructureCandidate(
                rank=i + 1,
                smiles=c.get("smiles", ""),
                name=c.get("name", ""),
                formula=c.get("formula", ""),
                confidence=c.get("confidence", 0.0),
                explanation=c.get("explanation", ""),
                matching_peaks=c.get("matching_peaks", []),
                conflicting_peaks=c.get("conflicting_peaks", []),
                scaffold_family=c.get("scaffold_family", molecule.metadata.scaffold_family),
            ))

        return PredictionResult(
            candidates=candidates,
            method=mode,
            scaffold_constraint=molecule.metadata.scaffold_family,
            reasoning=result.get("reasoning", ""),
            warnings=result.get("warnings", []),
        )
