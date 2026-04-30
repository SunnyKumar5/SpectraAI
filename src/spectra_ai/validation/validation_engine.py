"""
Validation Engine — Orchestrates all validation checkers.

Runs all available checks against the molecule + spectral data
and produces a unified ValidationReport with confidence scoring.
"""

from __future__ import annotations

from ..core.molecule import Molecule
from ..core.nmr_data import NMRData
from ..core.ir_data import IRData
from ..core.ms_data import MSData
from ..core.validation_report import ValidationReport, ValidationCheck

from .carbon_count_checker import CarbonCountChecker
from .proton_count_checker import ProtonCountChecker
from .functional_group_checker import FunctionalGroupChecker
from .ms_formula_checker import MSFormulaChecker
from .symmetry_checker import SymmetryChecker
from .cross_spectral_checker import CrossSpectralChecker


class ValidationEngine:
    """
    Orchestrates all validation checks and produces a unified report.

    Usage:
        engine = ValidationEngine()
        report = engine.validate(molecule, h1=h1_data, c13=c13_data, ir=ir_data, ms=ms_data)
        print(f"Score: {report.overall_score}/100")
    """

    def __init__(self):
        self.carbon_checker = CarbonCountChecker()
        self.proton_checker = ProtonCountChecker()
        self.fg_checker = FunctionalGroupChecker()
        self.ms_checker = MSFormulaChecker()
        self.symmetry_checker = SymmetryChecker()
        self.cross_checker = CrossSpectralChecker()

    def validate(self, molecule: Molecule, h1: NMRData = None,
                 c13: NMRData = None, ir: IRData = None,
                 ms: MSData = None) -> ValidationReport:
        """
        Run all validation checks and produce a report.

        Args:
            molecule: Molecule with structure/formula
            h1:   ¹H NMR data (optional)
            c13:  ¹³C NMR data (optional)
            ir:   IR data (optional)
            ms:   HRMS data (optional)

        Returns:
            ValidationReport with all check results and overall score
        """
        checks = []

        # Individual spectrum checks
        checks.append(self.carbon_checker.check(molecule, c13))
        checks.append(self.proton_checker.check(molecule, h1))
        checks.append(self.fg_checker.check(molecule, ir))
        checks.append(self.ms_checker.check(molecule, ms))
        checks.append(self.symmetry_checker.check(molecule, c13, h1))

        # Cross-spectral checks
        cross_checks = self.cross_checker.check(molecule, h1, c13, ir, ms)
        checks.extend(cross_checks)

        # Build report
        report = ValidationReport(checks=checks)
        report.calculate_overall_score()
        report.build_radar_data()
        report.summary = self._generate_summary(report)

        return report

    def _generate_summary(self, report: ValidationReport) -> str:
        """Generate a natural language summary of the validation report."""
        total = report.active_checks
        passed = report.pass_count
        warnings = report.warning_count
        fails = report.fail_count

        if fails == 0 and warnings == 0:
            return (
                f"All {passed} validation checks passed. "
                f"Characterization data is consistent with the proposed structure. "
                f"Confidence score: {report.overall_score:.0f}/100."
            )
        elif fails == 0 and warnings > 0:
            warn_names = [c.name for c in report.get_checks_by_status("warning")]
            return (
                f"{passed}/{total} checks passed with {warnings} warning(s): "
                f"{', '.join(warn_names)}. "
                f"These are minor and may have simple explanations. "
                f"Confidence score: {report.overall_score:.0f}/100."
            )
        else:
            fail_names = [c.name for c in report.get_checks_by_status("fail")]
            return (
                f"Issues detected: {fails} check(s) failed ({', '.join(fail_names)}). "
                f"{passed} passed, {warnings} warnings. "
                f"Review the flagged items before proceeding. "
                f"Confidence score: {report.overall_score:.0f}/100."
            )
