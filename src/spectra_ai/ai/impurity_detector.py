"""
Impurity Detector for SpectraAI.

Identifies unexpected peaks in NMR spectra that don't correspond
to the proposed structure, flagging potential impurities, solvents,
or degradation products.
"""

from __future__ import annotations

from typing import Optional

from .llm_client import LLMClient
from .prompts import detect_impurity
from ..core.nmr_data import NMRData, SOLVENT_RESIDUAL_PEAKS


class ImpurityDetector:
    """
    AI-powered impurity detection from NMR spectral data.

    Compares observed peaks against expected peaks from the structure
    and known solvent/impurity signatures to identify unassigned signals.
    """

    def __init__(self, llm: LLMClient):
        self._llm = llm

    def detect(
        self,
        h1_data: NMRData,
        smiles: str = "",
        formula: str = "",
        name: str = "",
        expected_peak_count: int = 0,
    ) -> Optional[dict]:
        """
        Analyze NMR data for potential impurities.

        Args:
            h1_data:              ¹H NMR data with peaks
            smiles:               Expected structure SMILES
            formula:              Expected molecular formula
            name:                 Compound name
            expected_peak_count:  Expected number of distinct proton environments

        Returns:
            dict with keys:
                unassigned_peaks: list of shifts not matching expected structure
                solvent_peaks: list of shifts identified as solvent residuals
                possible_impurities: list of suggested impurity identities
                purity_assessment: str (high/medium/low)
                reasoning: str
        """
        # Pre-filter known solvent peaks
        solvent_shifts = self._get_solvent_shifts(h1_data.solvent)

        user_prompt = detect_impurity.build_user_prompt(
            peaks_text=self._format_peaks(h1_data),
            solvent=h1_data.solvent,
            frequency=h1_data.frequency,
            smiles=smiles,
            formula=formula,
            name=name,
            known_solvent_shifts=solvent_shifts,
        )

        result = self._llm.generate_json(
            system=detect_impurity.SYSTEM_PROMPT,
            user=user_prompt,
            temperature=0.2,
            max_tokens=2000,
        )

        return result

    def quick_solvent_check(self, h1_data: NMRData) -> list[dict]:
        """
        Rule-based quick check for common solvent residual peaks.

        Returns list of detected solvent signals with assignments.
        """
        detected = []
        solvent_db = SOLVENT_RESIDUAL_PEAKS
        tolerance = 0.05  # ppm

        for peak in h1_data.peaks:
            for solvent_name, shifts in solvent_db.items():
                h1_shifts = shifts.get("1H", [])
                for ref_shift in h1_shifts:
                    if abs(peak.chemical_shift - ref_shift) < tolerance:
                        detected.append({
                            "shift": peak.chemical_shift,
                            "solvent": solvent_name,
                            "reference_shift": ref_shift,
                            "type": "solvent_residual",
                        })

        # Common impurity peaks
        common_impurities = {
            "water": {"CDCl3": 1.56, "DMSO-d6": 3.33, "CD3OD": 4.87},
            "grease": {"any": [0.86, 1.26]},
            "acetone": {"any": [2.17]},
            "DCM": {"any": [5.30]},
            "ethyl acetate": {"any": [1.26, 2.05, 4.12]},
        }

        for impurity, solvents in common_impurities.items():
            ref_shifts = solvents.get(h1_data.solvent, solvents.get("any", []))
            if isinstance(ref_shifts, (int, float)):
                ref_shifts = [ref_shifts]
            for ref in ref_shifts:
                for peak in h1_data.peaks:
                    if abs(peak.chemical_shift - ref) < tolerance:
                        detected.append({
                            "shift": peak.chemical_shift,
                            "impurity": impurity,
                            "reference_shift": ref,
                            "type": "common_impurity",
                        })

        return detected

    def _get_solvent_shifts(self, solvent: str) -> list[float]:
        """Get known ¹H shifts for a solvent."""
        return SOLVENT_RESIDUAL_PEAKS.get(solvent, {}).get("1H", [])

    def _format_peaks(self, h1_data: NMRData) -> str:
        """Format peaks for prompt injection."""
        lines = []
        for p in h1_data.sorted_peaks():
            parts = [f"δ {p.chemical_shift:.2f}"]
            if p.multiplicity:
                parts.append(f"({p.multiplicity}")
                if p.coupling_constants:
                    j_str = ", ".join(f"{j:.1f}" for j in p.coupling_constants)
                    parts[-1] += f", J = {j_str} Hz"
                if p.integration > 0:
                    parts[-1] += f", {p.integration:.0f}H"
                parts[-1] += ")"
            lines.append(" ".join(parts))
        return "\n".join(lines)
