"""
Carbon Count Checker — Validates ¹³C peak count against molecular formula.

Checks if the number of observed ¹³C NMR peaks is consistent with
the number of carbon atoms in the molecular formula, accounting for
molecular symmetry and accidental overlap.
"""

from __future__ import annotations

from ..core.molecule import Molecule
from ..core.nmr_data import NMRData
from ..core.validation_report import ValidationCheck, CheckCategory, CheckStatus


class CarbonCountChecker:
    """Validates ¹³C NMR peak count against expected carbon count."""

    def check(self, molecule: Molecule, c13: NMRData = None) -> ValidationCheck:
        """
        Compare observed ¹³C peak count with expected carbon count from formula.

        Rules:
          - Exact match: Pass (100)
          - Within ±2 (symmetry/overlap): Pass with note (90)
          - Within ±4: Warning (60)
          - More than ±4 off: Fail (20)
        """
        if c13 is None or not c13.peaks:
            return ValidationCheck(
                name="Carbon Count",
                category=CheckCategory.CARBON_COUNT.value,
                status=CheckStatus.SKIPPED.value,
                explanation="No ¹³C NMR data provided",
            )

        expected = molecule.expected_carbon_count
        observed = c13.peak_count

        if expected == 0:
            return ValidationCheck(
                name="Carbon Count",
                category=CheckCategory.CARBON_COUNT.value,
                status=CheckStatus.SKIPPED.value,
                explanation="No molecular formula provided to determine expected carbon count",
            )

        diff = abs(expected - observed)

        if diff == 0:
            return ValidationCheck(
                name="Carbon Count",
                category=CheckCategory.CARBON_COUNT.value,
                expected=str(expected),
                observed=str(observed),
                status=CheckStatus.PASS.value,
                score=100.0,
                explanation=f"All {expected} carbons accounted for in ¹³C spectrum.",
            )
        elif diff <= 2:
            reason = "Possible overlap or symmetry equivalence" if observed < expected else "Possible impurity or rotamers"
            return ValidationCheck(
                name="Carbon Count",
                category=CheckCategory.CARBON_COUNT.value,
                expected=str(expected),
                observed=str(observed),
                status=CheckStatus.PASS.value,
                score=90.0,
                explanation=f"Close match ({observed} observed vs {expected} expected). {reason}.",
            )
        elif diff <= 4:
            return ValidationCheck(
                name="Carbon Count",
                category=CheckCategory.CARBON_COUNT.value,
                expected=str(expected),
                observed=str(observed),
                status=CheckStatus.WARNING.value,
                score=60.0,
                explanation=f"Discrepancy of {diff} carbons. Check for overlapping peaks or symmetry.",
                suggestion="Run DEPT experiment to resolve overlapping signals, or re-examine structure for symmetry.",
            )
        else:
            return ValidationCheck(
                name="Carbon Count",
                category=CheckCategory.CARBON_COUNT.value,
                expected=str(expected),
                observed=str(observed),
                status=CheckStatus.FAIL.value,
                score=20.0,
                explanation=f"Significant discrepancy: {observed} observed vs {expected} expected ({diff} difference).",
                suggestion="Verify molecular formula and structure. Consider re-acquiring ¹³C spectrum with more scans.",
            )
