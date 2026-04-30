"""
NMR Chemical Shift Predictor for SpectraAI.

Predicts expected ¹H and ¹³C chemical shifts for a given molecular
structure using AI-based reasoning combined with scaffold reference data.
Enables pre-reaction spectral prediction and post-reaction comparison.
"""

from __future__ import annotations

from typing import Optional

from ..ai.llm_client import LLMClient
from ..ai.prompts import predict_nmr
from ..core.nmr_data import NMRData, NMRPeak
from ..utils.nmr_reference import get_scaffold_references


class NMRPredictor:
    """
    Predict expected NMR chemical shifts for a molecular structure.

    Combines:
    1. Scaffold reference ranges (rule-based)
    2. AI reasoning for substituent effects
    3. Empirical increment calculations
    """

    def __init__(self, llm: Optional[LLMClient] = None):
        self._llm = llm

    def predict_h1(
        self,
        smiles: str,
        formula: str = "",
        scaffold_family: str = "",
        solvent: str = "CDCl3",
        frequency: int = 400,
    ) -> Optional[NMRData]:
        """
        Predict ¹H NMR spectrum for a given SMILES.

        Returns NMRData with predicted peaks, or None if prediction fails.
        """
        if not self._llm:
            return self._rule_based_predict_h1(smiles, scaffold_family, solvent, frequency)

        scaffold_ref = ""
        if scaffold_family:
            ref = get_scaffold_references(scaffold_family)
            if ref:
                scaffold_ref = self._format_scaffold_ref(ref, "h1")

        user_prompt = predict_nmr.build_user_prompt(
            smiles=smiles,
            formula=formula,
            scaffold_family=scaffold_family,
            scaffold_reference=scaffold_ref,
            solvent=solvent,
            nucleus="1H",
        )

        result = self._llm.generate_json(
            system=predict_nmr.SYSTEM_PROMPT,
            user=user_prompt,
            temperature=0.3,
        )

        if not result:
            return None

        peaks = []
        for p in result.get("predicted_peaks", []):
            peaks.append(NMRPeak(
                chemical_shift=p.get("shift", 0.0),
                multiplicity=p.get("multiplicity", "s"),
                coupling_constants=p.get("J", []),
                integration=p.get("integration", 1.0),
                assignment=p.get("assignment", ""),
            ))

        return NMRData(
            nucleus="1H",
            frequency=frequency,
            solvent=solvent,
            peaks=peaks,
        )

    def predict_c13(
        self,
        smiles: str,
        formula: str = "",
        scaffold_family: str = "",
        solvent: str = "CDCl3",
    ) -> Optional[NMRData]:
        """Predict ¹³C NMR spectrum for a given SMILES."""
        if not self._llm:
            return None

        scaffold_ref = ""
        if scaffold_family:
            ref = get_scaffold_references(scaffold_family)
            if ref:
                scaffold_ref = self._format_scaffold_ref(ref, "c13")

        user_prompt = predict_nmr.build_user_prompt(
            smiles=smiles,
            formula=formula,
            scaffold_family=scaffold_family,
            scaffold_reference=scaffold_ref,
            solvent=solvent,
            nucleus="13C",
        )

        result = self._llm.generate_json(
            system=predict_nmr.SYSTEM_PROMPT,
            user=user_prompt,
            temperature=0.3,
        )

        if not result:
            return None

        peaks = [
            NMRPeak(
                chemical_shift=p.get("shift", 0.0),
                assignment=p.get("assignment", ""),
            )
            for p in result.get("predicted_peaks", [])
        ]

        return NMRData(nucleus="13C", solvent=solvent, peaks=peaks)

    def _rule_based_predict_h1(self, smiles: str, scaffold_family: str,
                                solvent: str, frequency: int) -> Optional[NMRData]:
        """Fallback rule-based prediction using scaffold references."""
        if not scaffold_family:
            return None

        ref = get_scaffold_references(scaffold_family)
        if not ref or "h1" not in ref:
            return None

        peaks = []
        for pos, (low, high, mult, note) in ref["h1"].items():
            avg_shift = (low + high) / 2
            mult_str = mult.split(",")[0].strip() if mult else "s"
            peaks.append(NMRPeak(
                chemical_shift=round(avg_shift, 2),
                multiplicity=mult_str,
                integration=1.0,
                assignment=pos,
            ))

        return NMRData(
            nucleus="1H",
            frequency=frequency,
            solvent=solvent,
            peaks=peaks,
        )

    def _format_scaffold_ref(self, ref: dict, nucleus: str) -> str:
        """Format scaffold reference data for prompt injection."""
        lines = []
        data = ref.get(nucleus, {})
        for pos, vals in data.items():
            if nucleus == "h1":
                low, high, mult, note = vals
                lines.append(f"  {pos}: δ {low:.1f}–{high:.1f} ({mult}) — {note}")
            else:
                low, high, note = vals
                lines.append(f"  {pos}: δ {low:.1f}–{high:.1f} — {note}")
        return "\n".join(lines)
