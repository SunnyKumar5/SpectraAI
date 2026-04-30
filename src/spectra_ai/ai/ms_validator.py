"""
MS Validator — AI-powered HRMS data validation.

Validates observed m/z against calculated values, checks ion type,
and assesses isotope pattern consistency.
"""

from __future__ import annotations

from .llm_client import LLMClient
from .prompts import validate_ms
from ..core.ms_data import MSData
from ..core.molecule import Molecule


class MSValidator:
    """AI-powered mass spectrometry validator."""

    def __init__(self, client: LLMClient):
        self.client = client

    def validate(self, ms_data: MSData, molecule: Molecule) -> dict:
        """
        Validate HRMS data against the molecular structure.

        Returns dict with assessment, ppm_error, formula check, and status.
        """
        ms_text = (
            f"Technique: {ms_data.technique}\n"
            f"Ion type: {ms_data.ion_type}\n"
            f"Ion formula: {ms_data.ion_formula}\n"
            f"Calculated m/z: {ms_data.calculated_mz}\n"
            f"Observed m/z: {ms_data.observed_mz}\n"
            f"PPM error: {ms_data.ppm_error:.2f}"
        )
        if ms_data.raw_text:
            ms_text = ms_data.raw_text + "\n\n" + ms_text

        user_prompt = validate_ms.build_user_prompt(
            ms_text=ms_text,
            formula=molecule.formula,
            smiles=molecule.smiles,
            name=molecule.name,
        )

        result = self.client.generate_json(
            system=validate_ms.SYSTEM_PROMPT,
            user=user_prompt,
            temperature=0.1,
        )

        if result is None:
            # Rule-based fallback
            ppm = ms_data.ppm_error
            return {
                "ppm_error": round(ppm, 2),
                "status": ms_data.tolerance_status,
                "formula_confirmed": ppm < 5.0,
                "assessment": f"Mass error: {ppm:.2f} ppm — {'acceptable' if ppm < 5 else 'exceeds tolerance'}",
                "warnings": [] if ppm < 5 else [f"Mass error of {ppm:.1f} ppm exceeds 5 ppm threshold"],
            }

        return result
