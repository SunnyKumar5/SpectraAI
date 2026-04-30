"""
SpectraAI Test Suite.

Tests cover:
  - Core data models (Molecule, NMRData, IRData, MSData, ValidationReport)
  - Parsers (NMR text, IR text, MS text)
  - Utility functions (formula parsing, MW calculation, DoU)
  - Validation engine (carbon count, proton count, MS formula)
  - NMR reference data
"""

import json
import os
import pytest

# ══════════════════════════════════════════════════════════════════════════════
#  Core Model Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestMolecule:
    """Tests for the Molecule data model."""

    def test_create_molecule(self):
        from spectra_ai.core.molecule import Molecule
        mol = Molecule(
            compound_id="TEST-001",
            name="Test Compound",
            smiles="c1ccccc1",
            formula="C6H6",
        )
        assert mol.compound_id == "TEST-001"
        assert mol.name == "Test Compound"
        assert mol.formula == "C6H6"

    def test_calculate_molecular_weight(self):
        from spectra_ai.core.molecule import Molecule
        mol = Molecule(formula="C14H12N2O")
        mw = mol.calculate_molecular_weight()
        assert abs(mw - 224.261) < 0.01

    def test_calculate_exact_mass(self):
        from spectra_ai.core.molecule import Molecule
        mol = Molecule(formula="C14H12N2O")
        exact = mol.calculate_exact_mass()
        assert abs(exact - 224.0949) < 0.001

    def test_element_counting(self):
        from spectra_ai.core.molecule import Molecule
        mol = Molecule(formula="C15H13N2O")
        assert mol.expected_carbon_count == 15
        assert mol.expected_hydrogen_count == 13
        assert mol.expected_nitrogen_count == 2

    def test_data_completeness_empty(self):
        from spectra_ai.core.molecule import Molecule
        mol = Molecule()
        assert mol.data_completeness == 0.0

    def test_data_completeness_partial(self):
        from spectra_ai.core.molecule import Molecule
        mol = Molecule(smiles="c1ccccc1")
        mol._h1_nmr = {"peaks": []}
        assert mol.data_completeness > 0.0
        assert mol.has_smiles
        assert mol.has_h1_nmr
        assert not mol.has_c13_nmr

    def test_serialization_roundtrip(self):
        from spectra_ai.core.molecule import Molecule
        mol = Molecule(
            compound_id="TEST-002",
            name="Roundtrip Test",
            smiles="CCO",
            formula="C2H6O",
        )
        mol.calculate_molecular_weight()
        mol.melting_point = (78, 80)

        json_str = mol.to_json()
        mol2 = Molecule.from_json(json_str)

        assert mol2.compound_id == mol.compound_id
        assert mol2.name == mol.name
        assert mol2.smiles == mol.smiles
        assert mol2.formula == mol.formula
        assert mol2.melting_point == (78, 80)

    def test_completeness_breakdown(self):
        from spectra_ai.core.molecule import Molecule
        mol = Molecule(smiles="CCO")
        breakdown = mol.completeness_breakdown
        assert breakdown["Structure"] is True
        assert breakdown["¹H NMR"] is False


class TestNMRData:
    """Tests for NMR data models."""

    def test_create_peak(self):
        from spectra_ai.core.nmr_data import NMRPeak
        peak = NMRPeak(
            chemical_shift=7.26,
            multiplicity="s",
            integration=1.0,
            assignment="CHCl3",
        )
        assert peak.chemical_shift == 7.26
        assert peak.display_text.startswith("δ 7.26")

    def test_peak_j_string(self):
        from spectra_ai.core.nmr_data import NMRPeak
        peak = NMRPeak(
            chemical_shift=7.85,
            multiplicity="dd",
            coupling_constants=[8.4, 2.1],
        )
        assert peak.j_string == "8.4, 2.1"

    def test_nmr_data_regions(self):
        from spectra_ai.core.nmr_data import NMRData, NMRPeak
        data = NMRData(
            nucleus="1H",
            peaks=[
                NMRPeak(chemical_shift=7.50),
                NMRPeak(chemical_shift=7.20),
                NMRPeak(chemical_shift=3.85),
                NMRPeak(chemical_shift=1.25),
            ],
        )
        assert len(data.aromatic_peaks) == 2
        assert len(data.aliphatic_peaks) == 2

    def test_nmr_data_sorting(self):
        from spectra_ai.core.nmr_data import NMRData, NMRPeak
        data = NMRData(
            peaks=[
                NMRPeak(chemical_shift=1.0),
                NMRPeak(chemical_shift=8.0),
                NMRPeak(chemical_shift=3.5),
            ],
        )
        sorted_peaks = data.sorted_peaks(descending=True)
        assert sorted_peaks[0].chemical_shift == 8.0
        assert sorted_peaks[-1].chemical_shift == 1.0

    def test_nmr_data_serialization(self):
        from spectra_ai.core.nmr_data import NMRData, NMRPeak
        data = NMRData(
            nucleus="1H",
            frequency=400,
            solvent="CDCl3",
            peaks=[NMRPeak(chemical_shift=7.26, multiplicity="s")],
        )
        d = data.to_dict()
        data2 = NMRData.from_dict(d)
        assert data2.nucleus == "1H"
        assert data2.frequency == 400
        assert len(data2.peaks) == 1

    def test_c13_carbonyl_peaks(self):
        from spectra_ai.core.nmr_data import NMRData, NMRPeak
        data = NMRData(
            nucleus="13C",
            peaks=[
                NMRPeak(chemical_shift=190.5),
                NMRPeak(chemical_shift=128.3),
                NMRPeak(chemical_shift=55.4),
            ],
        )
        assert len(data.carbonyl_peaks) == 1


class TestMSData:
    """Tests for mass spectrometry data."""

    def test_ppm_error(self):
        from spectra_ai.core.ms_data import MSData
        ms = MSData(calculated_mz=225.1022, observed_mz=225.1019)
        assert ms.ppm_error < 2.0

    def test_tolerance_status(self):
        from spectra_ai.core.ms_data import MSData
        ms = MSData(calculated_mz=225.1022, observed_mz=225.1019)
        assert ms.tolerance_status == "excellent"

        ms_bad = MSData(calculated_mz=225.1022, observed_mz=225.1100)
        assert ms_bad.tolerance_status == "fail"

    def test_display_text(self):
        from spectra_ai.core.ms_data import MSData
        ms = MSData(
            technique="ESI",
            ion_type="[M+H]+",
            calculated_mz=225.1022,
            observed_mz=225.1019,
            ion_formula="C14H13N2O",
        )
        assert "225.1022" in ms.display_text
        assert "ESI" in ms.display_text


class TestValidationReport:
    """Tests for validation report model."""

    def test_overall_status(self):
        from spectra_ai.core.validation_report import ValidationReport, ValidationCheck
        report = ValidationReport(checks=[
            ValidationCheck(name="Check 1", status="pass", score=90),
            ValidationCheck(name="Check 2", status="pass", score=85),
        ])
        assert report.overall_status == "pass"
        assert report.pass_count == 2

    def test_overall_status_with_failure(self):
        from spectra_ai.core.validation_report import ValidationReport, ValidationCheck
        report = ValidationReport(checks=[
            ValidationCheck(name="Check 1", status="pass", score=90),
            ValidationCheck(name="Check 2", status="fail", score=10),
        ])
        assert report.overall_status == "fail"
        assert report.fail_count == 1


# ══════════════════════════════════════════════════════════════════════════════
#  Parser Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestNMRParser:
    """Tests for the NMR text parser."""

    def test_parse_h1_basic(self):
        from spectra_ai.parsers.nmr_text_parser import parse_h1_nmr_text
        text = "1H NMR (400 MHz, CDCl3): δ 8.15 (d, J = 6.8 Hz, 1H), 7.68 (s, 1H), 3.85 (s, 3H)"
        result = parse_h1_nmr_text(text)
        assert result.nucleus == "1H"
        assert result.frequency == 400
        assert result.solvent == "CDCl3"
        assert len(result.peaks) >= 3

    def test_parse_h1_with_assignments(self):
        from spectra_ai.parsers.nmr_text_parser import parse_h1_nmr_text
        text = "1H NMR (400 MHz, DMSO-d6): δ 11.52 (br s, 1H, NH), 7.87 (d, J = 7.6 Hz, 2H, ArH)"
        result = parse_h1_nmr_text(text)
        assert result.solvent == "DMSO-d6"
        assert len(result.peaks) >= 2

    def test_parse_c13(self):
        from spectra_ai.parsers.nmr_text_parser import parse_c13_nmr_text
        text = "13C NMR (100 MHz, CDCl3): δ 159.7, 146.2, 145.0, 127.5, 55.4"
        result = parse_c13_nmr_text(text)
        assert result.nucleus == "13C"
        assert result.frequency == 100
        assert len(result.peaks) == 5
        assert result.peaks[0].chemical_shift > result.peaks[-1].chemical_shift

    def test_parse_empty_text(self):
        from spectra_ai.parsers.nmr_text_parser import parse_h1_nmr_text
        result = parse_h1_nmr_text("")
        assert len(result.peaks) == 0

    def test_parse_unicode_text(self):
        from spectra_ai.parsers.nmr_text_parser import parse_h1_nmr_text
        text = "¹H NMR (500 MHz, DMSO-d₆): δ 8.45 (s, 1H)"
        result = parse_h1_nmr_text(text)
        assert result.frequency == 500
        assert len(result.peaks) >= 1


class TestIRParser:
    """Tests for the IR text parser."""

    def test_parse_ir_basic(self):
        from spectra_ai.parsers.ir_parser import parse_ir_text
        text = "IR (KBr): 3312, 1658, 1598, 1492, 1240, 1028 cm-1"
        result = parse_ir_text(text)
        assert result.method == "KBr"
        assert len(result.absorptions) == 6

    def test_parse_ir_with_intensities(self):
        from spectra_ai.parsers.ir_parser import parse_ir_text
        text = "FT-IR (ATR): 3450 (br), 1720 (s), 1600 (m) cm-1"
        result = parse_ir_text(text)
        assert result.method == "ATR"
        assert any(a.intensity == "br" for a in result.absorptions)


class TestMSParser:
    """Tests for the MS text parser."""

    def test_parse_hrms(self):
        from spectra_ai.parsers.ms_parser import parse_ms_text
        text = "HRMS (ESI) m/z calcd for C14H13N2O [M+H]+ 225.1022, found 225.1019"
        result = parse_ms_text(text)
        assert result.technique == "ESI"
        assert result.ion_type == "[M+H]+"
        assert abs(result.calculated_mz - 225.1022) < 0.0001
        assert abs(result.observed_mz - 225.1019) < 0.0001

    def test_parse_ms_sodium_adduct(self):
        from spectra_ai.parsers.ms_parser import parse_ms_text
        text = "HRMS (ESI) m/z calcd for C10H10N2O2Na [M+Na]+ 213.0634, found 213.0631"
        result = parse_ms_text(text)
        assert result.ion_type == "[M+Na]+"


# ══════════════════════════════════════════════════════════════════════════════
#  Utility Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestFormulaUtils:
    """Tests for formula parsing and calculation utilities."""

    def test_parse_formula(self):
        from spectra_ai.utils.formula_utils import parse_formula
        result = parse_formula("C14H12N2O")
        assert result == {"C": 14, "H": 12, "N": 2, "O": 1}

    def test_parse_formula_with_halogens(self):
        from spectra_ai.utils.formula_utils import parse_formula
        result = parse_formula("C6H4BrCl")
        assert result["Br"] == 1
        assert result["Cl"] == 1

    def test_calculate_mw(self):
        from spectra_ai.utils.formula_utils import calculate_mw
        mw = calculate_mw("H2O")
        assert abs(mw - 18.015) < 0.01

    def test_degree_of_unsaturation(self):
        from spectra_ai.utils.formula_utils import degree_of_unsaturation
        # Benzene: C6H6 → DoU = 4
        assert degree_of_unsaturation("C6H6") == 4
        # Methane: CH4 → DoU = 0
        assert degree_of_unsaturation("CH4") == 0
        # Ethylene: C2H4 → DoU = 1
        assert degree_of_unsaturation("C2H4") == 1

    def test_validate_formula(self):
        from spectra_ai.utils.formula_utils import validate_formula
        is_valid, msg = validate_formula("C14H12N2O")
        assert is_valid
        is_valid2, msg2 = validate_formula("")
        assert not is_valid2

    def test_compare_formulas(self):
        from spectra_ai.utils.formula_utils import compare_formulas
        assert compare_formulas("C6H6", "C6H6")
        assert not compare_formulas("C6H6", "C6H12")

    def test_dict_to_formula(self):
        from spectra_ai.utils.formula_utils import dict_to_formula
        result = dict_to_formula({"C": 6, "H": 6})
        assert result == "C6H6"


class TestNMRReference:
    """Tests for NMR reference data."""

    def test_scaffold_lookup(self):
        from spectra_ai.utils.nmr_reference import get_scaffold_references
        ref = get_scaffold_references("imidazopyridine")
        assert ref is not None
        assert "h1" in ref
        assert "c13" in ref
        assert "H-3" in ref["h1"]

    def test_unknown_scaffold(self):
        from spectra_ai.utils.nmr_reference import get_scaffold_references
        ref = get_scaffold_references("nonexistent")
        assert ref is None

    def test_all_scaffolds(self):
        from spectra_ai.utils.nmr_reference import get_all_scaffold_names
        names = get_all_scaffold_names()
        assert "imidazopyridine" in names
        assert "indole" in names
        assert "triazole" in names


class TestIRReference:
    """Tests for IR reference data."""

    def test_find_matching_groups(self):
        from spectra_ai.utils.ir_reference import find_matching_groups
        matches = find_matching_groups(1720)
        group_names = [m[0] for m in matches]
        assert any("C=O" in name for name in group_names)

    def test_no_match(self):
        from spectra_ai.utils.ir_reference import find_matching_groups
        matches = find_matching_groups(100, tolerance=0)
        assert len(matches) == 0


# ══════════════════════════════════════════════════════════════════════════════
#  Validation Engine Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestValidationEngine:
    """Tests for the rule-based validation engine."""

    def test_carbon_count_check(self):
        from spectra_ai.validation.carbon_count_checker import CarbonCountChecker
        from spectra_ai.core.molecule import Molecule
        from spectra_ai.core.nmr_data import NMRData, NMRPeak

        mol = Molecule(formula="C6H6")
        c13 = NMRData(nucleus="13C", peaks=[
            NMRPeak(chemical_shift=128.0 + i) for i in range(6)
        ])

        checker = CarbonCountChecker()
        check = checker.check(mol, c13=c13)
        assert check.status == "pass"

    def test_proton_count_check(self):
        from spectra_ai.validation.proton_count_checker import ProtonCountChecker
        from spectra_ai.core.molecule import Molecule
        from spectra_ai.core.nmr_data import NMRData, NMRPeak

        mol = Molecule(formula="C6H6")
        h1 = NMRData(nucleus="1H", peaks=[
            NMRPeak(chemical_shift=7.26, integration=6.0),
        ])

        checker = ProtonCountChecker()
        check = checker.check(mol, h1=h1)
        assert check.status == "pass"

    def test_ms_formula_check_pass(self):
        from spectra_ai.validation.ms_formula_checker import MSFormulaChecker
        from spectra_ai.core.molecule import Molecule
        from spectra_ai.core.ms_data import MSData

        mol = Molecule(formula="C14H12N2O")
        ms = MSData(calculated_mz=225.1022, observed_mz=225.1019)

        checker = MSFormulaChecker()
        check = checker.check(mol, ms=ms)
        assert check.status == "pass"

    def test_ms_formula_check_fail(self):
        from spectra_ai.validation.ms_formula_checker import MSFormulaChecker
        from spectra_ai.core.molecule import Molecule
        from spectra_ai.core.ms_data import MSData

        mol = Molecule(formula="C14H12N2O")
        ms = MSData(calculated_mz=225.1022, observed_mz=226.2000)

        checker = MSFormulaChecker()
        check = checker.check(mol, ms=ms)
        assert check.status in ("fail", "warning")

    def test_full_validation_pipeline(self):
        from spectra_ai.validation.validation_engine import ValidationEngine
        from spectra_ai.core.molecule import Molecule
        from spectra_ai.core.nmr_data import NMRData, NMRPeak
        from spectra_ai.core.ms_data import MSData

        mol = Molecule(formula="C6H6", smiles="c1ccccc1")
        h1 = NMRData(nucleus="1H", peaks=[
            NMRPeak(chemical_shift=7.36, multiplicity="s", integration=6.0),
        ])
        c13 = NMRData(nucleus="13C", peaks=[
            NMRPeak(chemical_shift=128.4),
        ])

        engine = ValidationEngine()
        report = engine.validate(mol, h1, c13)
        assert report.total_checks > 0
        assert 0 <= report.overall_score <= 100


# ══════════════════════════════════════════════════════════════════════════════
#  Sample Data Loading Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestSampleData:
    """Tests for loading sample compound data."""

    def _get_sample_dir(self):
        """Locate the sample compounds directory."""
        test_dir = os.path.dirname(__file__)
        return os.path.join(
            test_dir, "..", "src", "spectra_ai", "data", "sample_compounds"
        )

    def test_load_sample_imidazopyridine(self):
        from spectra_ai.core.molecule import Molecule
        sample_dir = self._get_sample_dir()
        filepath = os.path.join(sample_dir, "SPEC-001_imidazopyridine.json")
        if os.path.exists(filepath):
            mol = Molecule.from_json_file(filepath)
            assert mol.compound_id == "SPEC-001"
            assert mol.metadata.scaffold_family == "imidazopyridine"
            assert mol.has_h1_nmr
            assert mol.has_c13_nmr
            assert mol.has_ir
            assert mol.has_hrms

    def test_load_all_samples(self):
        from spectra_ai.core.molecule import Molecule
        sample_dir = self._get_sample_dir()
        if not os.path.exists(sample_dir):
            pytest.skip("Sample data directory not found")
        count = 0
        for fname in os.listdir(sample_dir):
            if fname.endswith(".json"):
                mol = Molecule.from_json_file(os.path.join(sample_dir, fname))
                assert mol.compound_id
                assert mol.formula
                count += 1
        assert count >= 1


# ══════════════════════════════════════════════════════════════════════════════
#  Integration Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestIntegration:
    """End-to-end integration tests (without AI API calls)."""

    def test_parse_and_validate_workflow(self):
        """Test the full parse → validate pipeline without AI."""
        from spectra_ai.parsers.nmr_text_parser import parse_h1_nmr_text, parse_c13_nmr_text
        from spectra_ai.parsers.ir_parser import parse_ir_text
        from spectra_ai.parsers.ms_parser import parse_ms_text
        from spectra_ai.validation.validation_engine import ValidationEngine
        from spectra_ai.core.molecule import Molecule

        mol = Molecule(
            compound_id="INT-001",
            name="Test Integration",
            formula="C14H12N2O",
            smiles="COc1ccc(-c2cnc3ccccn23)cc1",
        )
        mol.calculate_molecular_weight()

        h1_text = "1H NMR (400 MHz, CDCl3): δ 8.15 (d, J = 6.8 Hz, 1H), 7.85 (d, J = 8.6 Hz, 2H), 7.68 (s, 1H), 7.58 (d, J = 9.0 Hz, 1H), 7.18 (t, J = 7.8 Hz, 1H), 6.98 (d, J = 8.6 Hz, 2H), 6.78 (t, J = 6.8 Hz, 1H), 3.85 (s, 3H)"
        c13_text = "13C NMR (100 MHz, CDCl3): δ 159.7, 146.2, 145.0, 127.5, 125.6, 125.1, 124.5, 117.6, 114.5, 112.4, 109.6, 55.4"
        ms_text = "HRMS (ESI) m/z calcd for C14H13N2O [M+H]+ 225.1022, found 225.1019"

        h1 = parse_h1_nmr_text(h1_text)
        c13 = parse_c13_nmr_text(c13_text)
        ms = parse_ms_text(ms_text)

        assert len(h1.peaks) >= 8
        assert len(c13.peaks) >= 12
        assert ms.ppm_error < 5.0

        engine = ValidationEngine()
        report = engine.validate(mol, h1, c13, ms=ms)
        assert report.total_checks > 0
        assert report.overall_score > 0
