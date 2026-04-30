"""
Cross-Spectral Checker — Rule-based multi-spectrum consistency validation.

Checks consistency across ¹H NMR, ¹³C NMR, IR, HRMS, and elemental analysis
using deterministic rules (no AI required).
"""

from __future__ import annotations

from ..core.molecule import Molecule
from ..core.nmr_data import NMRData
from ..core.ir_data import IRData
from ..core.ms_data import MSData
from ..core.validation_report import ValidationCheck, CheckCategory, CheckStatus


class CrossSpectralChecker:
    """Rule-based cross-spectral consistency checker."""

    def check(self, molecule: Molecule, h1: NMRData = None,
              c13: NMRData = None, ir: IRData = None,
              ms: MSData = None) -> list[ValidationCheck]:
        """
        Run all cross-spectral consistency checks.

        Returns list of ValidationCheck objects.
        """
        checks = []

        # Check 1: H count from ¹H NMR vs HRMS formula
        if h1 and h1.peaks and ms and ms.formula:
            checks.append(self._check_h_count_consistency(h1, molecule))

        # Check 2: C count from ¹³C NMR vs HRMS formula
        if c13 and c13.peaks and ms and ms.formula:
            checks.append(self._check_c_count_consistency(c13, molecule))

        # Check 3: IR N-H vs ¹H exchangeable protons
        if ir and ir.absorptions and h1 and h1.peaks:
            checks.append(self._check_nh_consistency(ir, h1, molecule))

        if not checks:
            checks.append(ValidationCheck(
                name="Cross-Spectral Consistency",
                category=CheckCategory.CROSS_SPECTRAL.value,
                status=CheckStatus.SKIPPED.value,
                explanation="Insufficient data for cross-spectral checks (need 2+ spectrum types)",
            ))

        return checks

    def _check_h_count_consistency(self, h1: NMRData, molecule: Molecule) -> ValidationCheck:
        """Check if ¹H integration matches expected H count from formula."""
        expected = molecule.expected_hydrogen_count
        observed = h1.total_integration

        if observed == 0:
            return ValidationCheck(
                name="Cross: ¹H vs Formula H-count",
                category=CheckCategory.CROSS_SPECTRAL.value,
                status=CheckStatus.SKIPPED.value,
                explanation="No ¹H integration data to cross-check",
            )

        diff = abs(expected - observed)
        if diff <= 1:
            return ValidationCheck(
                name="Cross: ¹H vs Formula H-count",
                category=CheckCategory.CROSS_SPECTRAL.value,
                expected=f"{expected}H (from formula)",
                observed=f"{observed:.0f}H (from ¹H NMR integration)",
                status=CheckStatus.PASS.value,
                score=100.0,
                explanation="¹H NMR integration total is consistent with molecular formula.",
            )
        elif diff <= 3:
            return ValidationCheck(
                name="Cross: ¹H vs Formula H-count",
                category=CheckCategory.CROSS_SPECTRAL.value,
                expected=f"{expected}H",
                observed=f"{observed:.0f}H",
                status=CheckStatus.WARNING.value,
                score=65.0,
                explanation=f"Minor discrepancy ({diff:.0f}H) between ¹H NMR and formula.",
                suggestion="Check for exchangeable protons (NH, OH) or integration calibration.",
            )
        else:
            return ValidationCheck(
                name="Cross: ¹H vs Formula H-count",
                category=CheckCategory.CROSS_SPECTRAL.value,
                expected=f"{expected}H",
                observed=f"{observed:.0f}H",
                status=CheckStatus.FAIL.value,
                score=20.0,
                explanation=f"Major discrepancy ({diff:.0f}H) — ¹H data inconsistent with formula.",
            )

    def _check_c_count_consistency(self, c13: NMRData, molecule: Molecule) -> ValidationCheck:
        expected = molecule.expected_carbon_count
        observed = c13.peak_count

        if expected == 0:
            return ValidationCheck(
                name="Cross: ¹³C vs Formula C-count",
                category=CheckCategory.CROSS_SPECTRAL.value,
                status=CheckStatus.SKIPPED.value,
                explanation="No formula available",
            )

        diff = abs(expected - observed)
        if diff <= 2:
            return ValidationCheck(
                name="Cross: ¹³C vs Formula C-count",
                category=CheckCategory.CROSS_SPECTRAL.value,
                expected=f"{expected}C",
                observed=f"{observed} peaks",
                status=CheckStatus.PASS.value,
                score=95.0,
                explanation="¹³C peak count is consistent with molecular formula.",
            )
        else:
            return ValidationCheck(
                name="Cross: ¹³C vs Formula C-count",
                category=CheckCategory.CROSS_SPECTRAL.value,
                expected=f"{expected}C",
                observed=f"{observed} peaks",
                status=CheckStatus.WARNING.value,
                score=55.0,
                explanation=f"¹³C peak count differs from formula by {diff}.",
            )

    def _check_nh_consistency(self, ir: IRData, h1: NMRData,
                               molecule: Molecule) -> ValidationCheck:
        """Check if IR N-H bands are consistent with exchangeable ¹H signals."""
        has_ir_nh = ir.has_functional_group("N-H (amide)") or ir.has_functional_group("N-H (primary amine)")

        # Look for broad singlets or downfield exchangeable protons in ¹H
        exchangeable_h1 = [p for p in h1.peaks if "br" in p.multiplicity.lower() and p.chemical_shift > 6.0]

        if has_ir_nh and exchangeable_h1:
            return ValidationCheck(
                name="Cross: IR N-H vs ¹H exchangeable",
                category=CheckCategory.CROSS_SPECTRAL.value,
                expected="N-H present (from IR)",
                observed=f"Exchangeable proton(s) at δ {', '.join(f'{p.chemical_shift:.1f}' for p in exchangeable_h1)}",
                status=CheckStatus.PASS.value,
                score=100.0,
                explanation="IR N-H band confirmed by exchangeable proton in ¹H NMR.",
            )
        elif has_ir_nh and not exchangeable_h1:
            return ValidationCheck(
                name="Cross: IR N-H vs ¹H exchangeable",
                category=CheckCategory.CROSS_SPECTRAL.value,
                expected="N-H present (from IR)",
                observed="No clear exchangeable proton in ¹H NMR",
                status=CheckStatus.WARNING.value,
                score=60.0,
                explanation="IR shows N-H but no clear exchangeable proton in ¹H. May be exchange-broadened or overlapped.",
                suggestion="Try D₂O shake experiment or measure in different solvent.",
            )
        else:
            return ValidationCheck(
                name="Cross: IR N-H vs ¹H exchangeable",
                category=CheckCategory.CROSS_SPECTRAL.value,
                status=CheckStatus.PASS.value,
                score=85.0,
                explanation="No N-H expected or detected — consistent.",
            )
