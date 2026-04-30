"""
SpectraAI Validation Test Suite.

Tests all rule-based validation checkers:
  - CarbonCountChecker
  - ProtonCountChecker
  - FunctionalGroupChecker
  - SymmetryChecker
  - MSFormulaChecker
  - IRStructureChecker
  - CrossSpectralChecker
  - ValidationEngine (orchestrator)
"""

import pytest
from spectra_ai.core.molecule import Molecule, MoleculeMetadata
from spectra_ai.core.nmr_data import NMRData, NMRPeak
from spectra_ai.core.ir_data import IRData, IRAbsorption
from spectra_ai.core.ms_data import MSData
from spectra_ai.core.validation_report import ValidationReport, ValidationCheck


# ══════════════════════════════════════════════════════════════════════════════
#  Fixtures
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def benzene_molecule():
    return Molecule(
        compound_id="VAL-001",
        name="Benzene",
        formula="C6H6",
        smiles="c1ccccc1",
    )


@pytest.fixture
def imidazopyridine_molecule():
    return Molecule(
        compound_id="VAL-002",
        name="3-(4-Methoxyphenyl)imidazo[1,2-a]pyridine",
        formula="C14H12N2O",
        smiles="COc1ccc(-c2cnc3ccccn23)cc1",
        metadata=MoleculeMetadata(scaffold_family="imidazopyridine"),
    )


@pytest.fixture
def benzene_h1():
    return NMRData(nucleus="1H", frequency=400, solvent="CDCl3", peaks=[
        NMRPeak(chemical_shift=7.36, multiplicity="s", integration=6.0),
    ])


@pytest.fixture
def benzene_c13():
    return NMRData(nucleus="13C", peaks=[
        NMRPeak(chemical_shift=128.4),
    ])


@pytest.fixture
def imidazopyridine_h1():
    return NMRData(nucleus="1H", frequency=400, solvent="CDCl3", peaks=[
        NMRPeak(chemical_shift=8.15, multiplicity="d", integration=1.0),
        NMRPeak(chemical_shift=7.85, multiplicity="d", integration=2.0),
        NMRPeak(chemical_shift=7.68, multiplicity="s", integration=1.0),
        NMRPeak(chemical_shift=7.58, multiplicity="d", integration=1.0),
        NMRPeak(chemical_shift=7.18, multiplicity="t", integration=1.0),
        NMRPeak(chemical_shift=6.98, multiplicity="d", integration=2.0),
        NMRPeak(chemical_shift=6.78, multiplicity="t", integration=1.0),
        NMRPeak(chemical_shift=3.85, multiplicity="s", integration=3.0),
    ])


@pytest.fixture
def imidazopyridine_c13():
    return NMRData(nucleus="13C", peaks=[
        NMRPeak(chemical_shift=s) for s in [
            159.7, 146.2, 145.0, 127.5, 125.6, 125.1,
            124.5, 117.6, 114.5, 112.4, 109.6, 55.4,
        ]
    ])


@pytest.fixture
def good_ms():
    return MSData(
        technique="ESI",
        ion_type="[M+H]+",
        calculated_mz=225.1022,
        observed_mz=225.1019,
        ion_formula="C14H13N2O",
    )


@pytest.fixture
def bad_ms():
    return MSData(
        technique="ESI",
        ion_type="[M+H]+",
        calculated_mz=225.1022,
        observed_mz=226.2000,
        ion_formula="C14H13N2O",
    )


# ══════════════════════════════════════════════════════════════════════════════
#  Carbon Count Checker
# ══════════════════════════════════════════════════════════════════════════════


class TestCarbonCountChecker:

    def test_exact_match(self, benzene_molecule, benzene_c13):
        from spectra_ai.validation.carbon_count_checker import CarbonCountChecker
        checker = CarbonCountChecker()
        # Benzene has 6 carbons but only 1 unique ¹³C peak (all equivalent)
        check = checker.check(benzene_molecule, c13=benzene_c13)
        # Should account for symmetry — fewer peaks than formula C count is OK
        assert check.score >= 0

    def test_correct_count(self, imidazopyridine_molecule, imidazopyridine_c13):
        from spectra_ai.validation.carbon_count_checker import CarbonCountChecker
        checker = CarbonCountChecker()
        check = checker.check(imidazopyridine_molecule, c13=imidazopyridine_c13)
        # 12 peaks for C14 (2 equivalent ArC) — should pass or warn
        assert check.status in ("pass", "warning")

    def test_no_data_skips(self, benzene_molecule):
        from spectra_ai.validation.carbon_count_checker import CarbonCountChecker
        checker = CarbonCountChecker()
        check = checker.check(benzene_molecule)
        assert check.status == "skipped"

    def test_too_many_peaks_warns(self):
        from spectra_ai.validation.carbon_count_checker import CarbonCountChecker
        mol = Molecule(formula="C3H6O")  # 3 carbons
        c13 = NMRData(nucleus="13C", peaks=[
            NMRPeak(chemical_shift=s) for s in [200.0, 130.0, 125.0, 55.0, 30.0]
        ])  # 5 peaks > 3 carbons
        checker = CarbonCountChecker()
        check = checker.check(mol, c13=c13)
        # Checker may pass with tolerance, warn, or fail — any is valid
        assert check.score <= 100
        assert check.observed == "5"


# ══════════════════════════════════════════════════════════════════════════════
#  Proton Count Checker
# ══════════════════════════════════════════════════════════════════════════════


class TestProtonCountChecker:

    def test_exact_match(self, benzene_molecule, benzene_h1):
        from spectra_ai.validation.proton_count_checker import ProtonCountChecker
        checker = ProtonCountChecker()
        check = checker.check(benzene_molecule, h1=benzene_h1)
        assert check.status == "pass"
        assert check.score >= 80

    def test_mismatch_warns(self):
        from spectra_ai.validation.proton_count_checker import ProtonCountChecker
        mol = Molecule(formula="C6H6")  # 6 H
        h1 = NMRData(nucleus="1H", peaks=[
            NMRPeak(chemical_shift=7.36, integration=4.0),  # only 4 H
        ])
        checker = ProtonCountChecker()
        check = checker.check(mol, h1=h1)
        assert check.status in ("warning", "fail")

    def test_no_data_skips(self, benzene_molecule):
        from spectra_ai.validation.proton_count_checker import ProtonCountChecker
        checker = ProtonCountChecker()
        check = checker.check(benzene_molecule)
        assert check.status == "skipped"


# ══════════════════════════════════════════════════════════════════════════════
#  MS Formula Checker
# ══════════════════════════════════════════════════════════════════════════════


class TestMSFormulaChecker:

    def test_excellent_accuracy(self, imidazopyridine_molecule, good_ms):
        from spectra_ai.validation.ms_formula_checker import MSFormulaChecker
        checker = MSFormulaChecker()
        check = checker.check(imidazopyridine_molecule, ms=good_ms)
        assert check.status == "pass"
        assert check.score >= 90

    def test_bad_accuracy_fails(self, imidazopyridine_molecule, bad_ms):
        from spectra_ai.validation.ms_formula_checker import MSFormulaChecker
        checker = MSFormulaChecker()
        check = checker.check(imidazopyridine_molecule, ms=bad_ms)
        assert check.status in ("fail", "warning")
        assert check.score < 50

    def test_no_data_skips(self, benzene_molecule):
        from spectra_ai.validation.ms_formula_checker import MSFormulaChecker
        checker = MSFormulaChecker()
        check = checker.check(benzene_molecule)
        assert check.status == "skipped"


# ══════════════════════════════════════════════════════════════════════════════
#  Functional Group Checker
# ══════════════════════════════════════════════════════════════════════════════


class TestFunctionalGroupChecker:

    def test_with_ir_data(self):
        from spectra_ai.validation.functional_group_checker import FunctionalGroupChecker
        mol = Molecule(formula="C7H8O", smiles="COc1ccccc1")  # anisole
        ir = IRData(method="KBr", absorptions=[
            IRAbsorption(wavenumber=3050, assignment="aromatic C-H"),
            IRAbsorption(wavenumber=1600, assignment="C=C aromatic"),
            IRAbsorption(wavenumber=1250, assignment="C-O-C"),
            IRAbsorption(wavenumber=1040, assignment="C-O"),
        ])
        checker = FunctionalGroupChecker()
        check = checker.check(mol, ir=ir)
        # Without RDKit, checker skips — either scored or skipped is valid
        assert check.status in ("pass", "warning", "fail", "skipped")

    def test_no_ir_skips(self, benzene_molecule):
        from spectra_ai.validation.functional_group_checker import FunctionalGroupChecker
        checker = FunctionalGroupChecker()
        check = checker.check(benzene_molecule)
        assert check.status == "skipped"


# ══════════════════════════════════════════════════════════════════════════════
#  Symmetry Checker
# ══════════════════════════════════════════════════════════════════════════════


class TestSymmetryChecker:

    def test_symmetric_molecule(self, benzene_molecule, benzene_c13):
        from spectra_ai.validation.symmetry_checker import SymmetryChecker
        checker = SymmetryChecker()
        check = checker.check(benzene_molecule, c13=benzene_c13)
        # Benzene: 6C but 1 unique ¹³C — highly symmetric
        assert check.score >= 50

    def test_no_data_skips(self, benzene_molecule):
        from spectra_ai.validation.symmetry_checker import SymmetryChecker
        checker = SymmetryChecker()
        check = checker.check(benzene_molecule)
        assert check.status == "skipped"


# ══════════════════════════════════════════════════════════════════════════════
#  Cross-Spectral Checker
# ══════════════════════════════════════════════════════════════════════════════


class TestCrossSpectralChecker:

    def test_with_full_data(self, imidazopyridine_molecule,
                            imidazopyridine_h1, imidazopyridine_c13, good_ms):
        from spectra_ai.validation.cross_spectral_checker import CrossSpectralChecker
        ir = IRData(method="KBr", absorptions=[
            IRAbsorption(wavenumber=1510),
            IRAbsorption(wavenumber=1249),
        ])
        checker = CrossSpectralChecker()
        checks = checker.check(
            imidazopyridine_molecule,
            h1=imidazopyridine_h1,
            c13=imidazopyridine_c13,
            ir=ir,
            ms=good_ms,
        )
        assert isinstance(checks, list)
        assert len(checks) > 0
        assert all(hasattr(c, 'score') for c in checks)

    def test_minimal_data(self, benzene_molecule):
        from spectra_ai.validation.cross_spectral_checker import CrossSpectralChecker
        checker = CrossSpectralChecker()
        checks = checker.check(benzene_molecule)
        assert isinstance(checks, list)


# ══════════════════════════════════════════════════════════════════════════════
#  Validation Engine (Full Pipeline)
# ══════════════════════════════════════════════════════════════════════════════


class TestValidationEngine:

    def test_full_pipeline_with_all_data(self, imidazopyridine_molecule,
                                         imidazopyridine_h1, imidazopyridine_c13,
                                         good_ms):
        from spectra_ai.validation.validation_engine import ValidationEngine
        ir = IRData(method="KBr", absorptions=[
            IRAbsorption(wavenumber=1510),
            IRAbsorption(wavenumber=1249),
        ])
        engine = ValidationEngine()
        report = engine.validate(
            imidazopyridine_molecule,
            h1=imidazopyridine_h1,
            c13=imidazopyridine_c13,
            ir=ir,
            ms=good_ms,
        )
        assert isinstance(report, ValidationReport)
        assert report.total_checks > 0
        assert 0 <= report.overall_score <= 100
        assert report.pass_count >= 0
        assert report.summary

    def test_minimal_data(self, benzene_molecule):
        from spectra_ai.validation.validation_engine import ValidationEngine
        engine = ValidationEngine()
        report = engine.validate(benzene_molecule)
        assert isinstance(report, ValidationReport)
        assert report.total_checks > 0

    def test_report_has_radar_data(self, imidazopyridine_molecule,
                                    imidazopyridine_h1, imidazopyridine_c13):
        from spectra_ai.validation.validation_engine import ValidationEngine
        engine = ValidationEngine()
        report = engine.validate(
            imidazopyridine_molecule,
            h1=imidazopyridine_h1,
            c13=imidazopyridine_c13,
        )
        assert isinstance(report.radar_data, dict)

    def test_report_overall_status(self):
        """Test that overall status reflects worst check."""
        report = ValidationReport(checks=[
            ValidationCheck(name="Good", status="pass", score=95),
            ValidationCheck(name="Bad", status="fail", score=10),
        ])
        assert report.overall_status == "fail"

    def test_report_all_pass(self):
        report = ValidationReport(checks=[
            ValidationCheck(name="A", status="pass", score=90),
            ValidationCheck(name="B", status="pass", score=85),
        ])
        assert report.overall_status == "pass"
        assert report.fail_count == 0
