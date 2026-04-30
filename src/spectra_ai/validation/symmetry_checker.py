"""
Symmetry Checker — Checks molecular symmetry implications on NMR peak counts.
"""

from __future__ import annotations

from ..core.molecule import Molecule
from ..core.nmr_data import NMRData
from ..core.validation_report import ValidationCheck, CheckCategory, CheckStatus


class SymmetryChecker:
    """Checks if symmetry explains discrepancies between expected and observed peaks."""

    def check(self, molecule: Molecule, c13: NMRData = None,
              h1: NMRData = None) -> ValidationCheck:
        if c13 is None or not c13.peaks:
            return ValidationCheck(
                name="Molecular Symmetry",
                category=CheckCategory.MOLECULAR_SYMMETRY.value,
                status=CheckStatus.SKIPPED.value,
                explanation="No ¹³C NMR data to assess symmetry",
            )

        expected_c = molecule.expected_carbon_count
        observed_c = c13.peak_count

        if expected_c == 0:
            return ValidationCheck(
                name="Molecular Symmetry",
                category=CheckCategory.MOLECULAR_SYMMETRY.value,
                status=CheckStatus.SKIPPED.value,
                explanation="No formula provided",
            )

        if observed_c == expected_c:
            return ValidationCheck(
                name="Molecular Symmetry",
                category=CheckCategory.MOLECULAR_SYMMETRY.value,
                expected=f"{expected_c} unique carbons",
                observed=f"{observed_c} ¹³C peaks",
                status=CheckStatus.PASS.value,
                score=100.0,
                explanation="All carbons resolved. Molecule has no symmetry equivalence or all unique.",
            )
        elif observed_c < expected_c:
            missing = expected_c - observed_c
            return ValidationCheck(
                name="Molecular Symmetry",
                category=CheckCategory.MOLECULAR_SYMMETRY.value,
                expected=f"{expected_c} carbons",
                observed=f"{observed_c} ¹³C peaks ({missing} fewer)",
                status=CheckStatus.PASS.value,
                score=85.0,
                explanation=(
                    f"{missing} fewer peaks than expected — consistent with molecular symmetry "
                    f"(e.g., para-substituted ring, equivalent substituents) or accidental overlap."
                ),
            )
        else:
            extra = observed_c - expected_c
            return ValidationCheck(
                name="Molecular Symmetry",
                category=CheckCategory.MOLECULAR_SYMMETRY.value,
                expected=f"{expected_c} carbons",
                observed=f"{observed_c} ¹³C peaks ({extra} extra)",
                status=CheckStatus.WARNING.value,
                score=50.0,
                explanation=(
                    f"{extra} more peaks than expected. Possible causes: impurity, "
                    f"rotamers/conformers (restricted rotation), or incorrect formula."
                ),
                suggestion="Check for impurities. Consider variable-temperature NMR for rotamers.",
            )
