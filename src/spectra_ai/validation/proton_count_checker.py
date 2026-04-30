"""
Proton Count Checker — Validates ¹H NMR integration total against molecular formula.
"""

from __future__ import annotations

from ..core.molecule import Molecule
from ..core.nmr_data import NMRData
from ..core.validation_report import ValidationCheck, CheckCategory, CheckStatus


class ProtonCountChecker:
    """Validates total ¹H NMR integration against expected hydrogen count."""

    def check(self, molecule: Molecule, h1: NMRData = None) -> ValidationCheck:
        if h1 is None or not h1.peaks:
            return ValidationCheck(
                name="Proton Count",
                category=CheckCategory.PROTON_COUNT.value,
                status=CheckStatus.SKIPPED.value,
                explanation="No ¹H NMR data provided",
            )

        expected = molecule.expected_hydrogen_count
        observed = h1.total_integration

        if expected == 0:
            return ValidationCheck(
                name="Proton Count",
                category=CheckCategory.PROTON_COUNT.value,
                status=CheckStatus.SKIPPED.value,
                explanation="No molecular formula provided",
            )

        if observed == 0:
            return ValidationCheck(
                name="Proton Count",
                category=CheckCategory.PROTON_COUNT.value,
                expected=str(expected),
                observed="0 (no integration data)",
                status=CheckStatus.WARNING.value,
                score=50.0,
                explanation="Peak integrations not provided — cannot verify proton count.",
                suggestion="Enter integration values for each peak.",
            )

        diff = abs(expected - observed)

        if diff <= 0.5:
            return ValidationCheck(
                name="Proton Count",
                category=CheckCategory.PROTON_COUNT.value,
                expected=f"{expected}H",
                observed=f"{observed:.0f}H",
                status=CheckStatus.PASS.value,
                score=100.0,
                explanation=f"Proton count matches: {observed:.0f}H observed, {expected}H expected.",
            )
        elif diff <= 2:
            reason = "exchangeable protons (NH, OH) may not be observed" if observed < expected else "possible impurity or solvent"
            return ValidationCheck(
                name="Proton Count",
                category=CheckCategory.PROTON_COUNT.value,
                expected=f"{expected}H",
                observed=f"{observed:.0f}H",
                status=CheckStatus.WARNING.value,
                score=70.0,
                explanation=f"Minor discrepancy ({diff:.0f}H). Likely cause: {reason}.",
                suggestion="Check for exchangeable protons with D₂O shake experiment.",
            )
        else:
            return ValidationCheck(
                name="Proton Count",
                category=CheckCategory.PROTON_COUNT.value,
                expected=f"{expected}H",
                observed=f"{observed:.0f}H",
                status=CheckStatus.FAIL.value,
                score=20.0,
                explanation=f"Significant discrepancy: {observed:.0f}H observed vs {expected}H expected.",
                suggestion="Re-check integration calibration and molecular formula.",
            )
