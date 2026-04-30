"""
MS Formula Checker — Validates HRMS m/z accuracy and formula confirmation.
"""

from __future__ import annotations

from ..core.molecule import Molecule
from ..core.ms_data import MSData
from ..core.validation_report import ValidationCheck, CheckCategory, CheckStatus


class MSFormulaChecker:
    """Validates HRMS data for formula confirmation."""

    def check(self, molecule: Molecule, ms: MSData = None) -> ValidationCheck:
        if ms is None or (ms.calculated_mz == 0 and ms.observed_mz == 0):
            return ValidationCheck(
                name="HRMS Formula",
                category=CheckCategory.MASS_SPEC.value,
                status=CheckStatus.SKIPPED.value,
                explanation="No HRMS data provided",
            )

        ppm = ms.ppm_error

        if ppm < 3.0:
            return ValidationCheck(
                name="HRMS Formula",
                category=CheckCategory.MASS_SPEC.value,
                expected=f"{ms.calculated_mz:.4f} ({ms.ion_type})",
                observed=f"{ms.observed_mz:.4f} (Δ {ppm:.1f} ppm)",
                status=CheckStatus.PASS.value,
                score=100.0,
                explanation=f"Excellent mass accuracy ({ppm:.1f} ppm). Molecular formula confirmed.",
            )
        elif ppm < 5.0:
            return ValidationCheck(
                name="HRMS Formula",
                category=CheckCategory.MASS_SPEC.value,
                expected=f"{ms.calculated_mz:.4f} ({ms.ion_type})",
                observed=f"{ms.observed_mz:.4f} (Δ {ppm:.1f} ppm)",
                status=CheckStatus.PASS.value,
                score=90.0,
                explanation=f"Acceptable mass accuracy ({ppm:.1f} ppm). Formula confirmed within tolerance.",
            )
        elif ppm < 10.0:
            return ValidationCheck(
                name="HRMS Formula",
                category=CheckCategory.MASS_SPEC.value,
                expected=f"{ms.calculated_mz:.4f} ({ms.ion_type})",
                observed=f"{ms.observed_mz:.4f} (Δ {ppm:.1f} ppm)",
                status=CheckStatus.WARNING.value,
                score=50.0,
                explanation=f"Marginal mass accuracy ({ppm:.1f} ppm). Outside typical 5 ppm threshold.",
                suggestion="Recalibrate mass spectrometer and re-measure. Check ion type assignment.",
            )
        else:
            return ValidationCheck(
                name="HRMS Formula",
                category=CheckCategory.MASS_SPEC.value,
                expected=f"{ms.calculated_mz:.4f} ({ms.ion_type})",
                observed=f"{ms.observed_mz:.4f} (Δ {ppm:.1f} ppm)",
                status=CheckStatus.FAIL.value,
                score=10.0,
                explanation=f"Poor mass accuracy ({ppm:.1f} ppm). Formula NOT confirmed.",
                suggestion="Verify correct ion type, recalculate exact mass, and re-measure.",
            )
