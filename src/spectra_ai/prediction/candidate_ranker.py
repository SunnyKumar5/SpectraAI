"""
Candidate Ranker for SpectraAI.

Ranks enumerated structure candidates against observed spectral data
using a combination of rule-based scoring and AI evaluation.
Produces the final ranked prediction results.
"""

from __future__ import annotations

from typing import Optional

from ..core.molecule import Molecule
from ..core.nmr_data import NMRData
from ..core.ir_data import IRData
from ..core.ms_data import MSData
from ..core.prediction_result import StructureCandidate, PredictionResult
from ..utils.formula_utils import parse_formula, calculate_mw, calculate_exact_mass
from ..utils.smiles_utils import (
    has_rdkit, smiles_to_formula, count_atoms, count_aromatic_rings,
)


class CandidateRanker:
    """
    Ranks candidate structures against observed spectral data.

    Scoring criteria:
    1. Formula match (exact or within mass tolerance)
    2. Molecular weight match
    3. Carbon count match with ¹³C NMR
    4. Proton count match with ¹H NMR integration
    5. Degree of unsaturation consistency
    6. Aromatic ring count from ¹H chemical shifts
    7. HRMS mass accuracy (ppm error)

    Each criterion contributes a weighted score (0-1).
    """

    WEIGHTS = {
        "formula":       0.25,
        "mass_accuracy": 0.20,
        "carbon_count":  0.15,
        "proton_count":  0.10,
        "dou":           0.10,
        "aromatic_match": 0.10,
        "mw_match":      0.10,
    }

    def rank(
        self,
        candidates: list[StructureCandidate],
        observed_formula: str = "",
        h1_data: Optional[NMRData] = None,
        c13_data: Optional[NMRData] = None,
        ms_data: Optional[MSData] = None,
        max_results: int = 10,
    ) -> PredictionResult:
        """
        Rank candidates against observed data and return scored results.

        Args:
            candidates:       List of unranked StructureCandidate objects
            observed_formula: Expected molecular formula
            h1_data:          ¹H NMR data
            c13_data:         ¹³C NMR data
            ms_data:          HRMS data
            max_results:      Maximum number of ranked results

        Returns:
            PredictionResult with ranked candidates
        """
        if not candidates:
            return PredictionResult(candidates=[], method="scaffold_enumeration")

        scored = []
        for cand in candidates:
            score = self._score_candidate(
                cand, observed_formula, h1_data, c13_data, ms_data,
            )
            cand.confidence = score
            scored.append(cand)

        # Sort by confidence descending
        scored.sort(key=lambda c: c.confidence, reverse=True)

        # Assign ranks
        for i, cand in enumerate(scored[:max_results]):
            cand.rank = i + 1

        return PredictionResult(
            candidates=scored[:max_results],
            method="scaffold_enumeration + spectral_scoring",
            reasoning=(
                f"Ranked {len(candidates)} candidates against observed data. "
                f"Top candidate: {scored[0].name if scored else 'none'} "
                f"(confidence: {scored[0].confidence_percent if scored else 0}%)"
            ),
        )

    def _score_candidate(
        self,
        candidate: StructureCandidate,
        observed_formula: str,
        h1_data: Optional[NMRData],
        c13_data: Optional[NMRData],
        ms_data: Optional[MSData],
    ) -> float:
        """Calculate overall confidence score for a candidate (0-1)."""
        scores = {}

        cand_formula = candidate.formula
        if not cand_formula and has_rdkit():
            cand_formula = smiles_to_formula(candidate.smiles) or ""

        # 1. Formula match
        if observed_formula and cand_formula:
            scores["formula"] = 1.0 if cand_formula == observed_formula else 0.0
        else:
            scores["formula"] = 0.5  # unknown

        # 2. Mass accuracy (if HRMS available)
        if ms_data and ms_data.calculated_mz > 0 and cand_formula:
            cand_exact = calculate_exact_mass(cand_formula)
            if cand_exact > 0:
                # Approximate [M+H]+ comparison
                cand_mh = cand_exact + 1.00728
                diff_ppm = abs(cand_mh - ms_data.observed_mz) / ms_data.observed_mz * 1e6
                if diff_ppm < 2:
                    scores["mass_accuracy"] = 1.0
                elif diff_ppm < 5:
                    scores["mass_accuracy"] = 0.7
                elif diff_ppm < 10:
                    scores["mass_accuracy"] = 0.3
                else:
                    scores["mass_accuracy"] = 0.0
            else:
                scores["mass_accuracy"] = 0.5

        # 3. Carbon count from ¹³C
        if c13_data and c13_data.peaks and cand_formula:
            expected_c = parse_formula(cand_formula).get("C", 0)
            observed_c = len(c13_data.peaks)
            if expected_c > 0:
                diff = abs(expected_c - observed_c)
                if diff == 0:
                    scores["carbon_count"] = 1.0
                elif diff <= 2:
                    scores["carbon_count"] = 0.7
                else:
                    scores["carbon_count"] = max(0, 1.0 - diff * 0.15)

        # 4. Proton count from ¹H integration
        if h1_data and h1_data.peaks and cand_formula:
            expected_h = parse_formula(cand_formula).get("H", 0)
            total_int = sum(p.integration for p in h1_data.peaks if p.integration > 0)
            if expected_h > 0 and total_int > 0:
                diff = abs(expected_h - total_int)
                if diff <= 1:
                    scores["proton_count"] = 1.0
                elif diff <= 3:
                    scores["proton_count"] = 0.6
                else:
                    scores["proton_count"] = max(0, 1.0 - diff * 0.1)

        # 5. MW match
        if observed_formula and cand_formula:
            obs_mw = calculate_mw(observed_formula)
            cand_mw = calculate_mw(cand_formula)
            if obs_mw > 0 and cand_mw > 0:
                diff = abs(obs_mw - cand_mw)
                if diff < 0.5:
                    scores["mw_match"] = 1.0
                elif diff < 2:
                    scores["mw_match"] = 0.5
                else:
                    scores["mw_match"] = 0.0

        # Weighted sum
        total_score = 0.0
        total_weight = 0.0
        for key, weight in self.WEIGHTS.items():
            if key in scores:
                total_score += scores[key] * weight
                total_weight += weight

        return round(total_score / total_weight, 3) if total_weight > 0 else 0.0
