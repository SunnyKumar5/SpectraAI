"""
Tests for SpectraAI parsers module.

Covers NMR text parser, IR parser, MS parser, CSV parser,
and JCAMP-DX parser edge cases.
"""

import pytest


class TestNMRTextParserEdgeCases:
    """Edge case tests for the NMR text parser."""

    def test_missing_header(self):
        from spectra_ai.parsers.nmr_text_parser import parse_h1_nmr_text
        text = "δ 7.26 (s, 1H), 3.85 (s, 3H)"
        result = parse_h1_nmr_text(text)
        assert len(result.peaks) >= 2

    def test_multiple_j_values(self):
        from spectra_ai.parsers.nmr_text_parser import parse_h1_nmr_text
        text = "1H NMR (400 MHz, CDCl3): δ 7.10 (dd, J = 8.4, 2.1 Hz, 1H)"
        result = parse_h1_nmr_text(text)
        assert result.peaks[0].multiplicity in ("dd", "m")

    def test_broad_singlet(self):
        from spectra_ai.parsers.nmr_text_parser import parse_h1_nmr_text
        text = "1H NMR (400 MHz, DMSO-d6): δ 11.52 (br s, 1H, NH)"
        result = parse_h1_nmr_text(text)
        assert len(result.peaks) >= 1

    def test_c13_dept_header(self):
        from spectra_ai.parsers.nmr_text_parser import parse_c13_nmr_text
        text = "13C NMR (100 MHz, CDCl3): δ 170.5, 130.2, 128.9, 55.4"
        result = parse_c13_nmr_text(text)
        assert len(result.peaks) == 4
        assert result.peaks[0].chemical_shift > result.peaks[-1].chemical_shift

    def test_empty_input(self):
        from spectra_ai.parsers.nmr_text_parser import parse_h1_nmr_text
        assert parse_h1_nmr_text("").peaks == []
        assert parse_h1_nmr_text("   ").peaks == []

    def test_unicode_normalization(self):
        from spectra_ai.parsers.nmr_text_parser import parse_h1_nmr_text
        text = "¹H NMR (500 MHz, DMSO-d₆): δ 8.45 (s, 1H)"
        result = parse_h1_nmr_text(text)
        assert result.frequency == 500
        assert len(result.peaks) >= 1


class TestIRParserEdgeCases:
    """Edge case tests for the IR parser."""

    def test_atr_method(self):
        from spectra_ai.parsers.ir_parser import parse_ir_text
        text = "FT-IR (ATR): 3312, 1658, 1598 cm-1"
        result = parse_ir_text(text)
        assert result.method == "ATR"

    def test_intensity_annotations(self):
        from spectra_ai.parsers.ir_parser import parse_ir_text
        text = "IR (KBr): 3450 (br), 1720 (s), 1600 (m), 1250 (w) cm-1"
        result = parse_ir_text(text)
        assert len(result.absorptions) >= 4

    def test_no_method(self):
        from spectra_ai.parsers.ir_parser import parse_ir_text
        text = "IR: 3312, 1658 cm-1"
        result = parse_ir_text(text)
        assert len(result.absorptions) >= 2


class TestMSParserEdgeCases:
    """Edge case tests for the MS parser."""

    def test_negative_mode(self):
        from spectra_ai.parsers.ms_parser import parse_ms_text
        text = "HRMS (ESI) m/z calcd for C10H9N2O3 [M-H]- 205.0613, found 205.0610"
        result = parse_ms_text(text)
        assert result.ion_type == "[M-H]-"

    def test_apci_technique(self):
        from spectra_ai.parsers.ms_parser import parse_ms_text
        text = "HRMS (APCI) m/z calcd for C8H10N [M+H]+ 120.0808, found 120.0805"
        result = parse_ms_text(text)
        assert result.technique == "APCI"


class TestCSVParser:
    """Tests for the CSV compound parser."""

    def test_parse_csv_with_headers(self, tmp_path):
        from spectra_ai.parsers.csv_parser import parse_compound_csv
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(
            "name,smiles,formula,scaffold\n"
            "Test Compound,c1ccccc1,C6H6,indole\n"
        )
        molecules = parse_compound_csv(str(csv_file))
        assert len(molecules) == 1
        assert molecules[0].name == "Test Compound"
        assert molecules[0].formula == "C6H6"


class TestJCAMPParser:
    """Tests for the JCAMP-DX parser."""

    def test_parse_header(self):
        from spectra_ai.parsers.jcamp_parser import JCAMPParser
        parser = JCAMPParser()
        content = (
            "##TITLE= Test Spectrum\n"
            "##DATATYPE= NMR SPECTRUM\n"
            "##XUNITS= PPM\n"
            "##YUNITS= ARBITRARY\n"
            "##NPOINTS= 3\n"
            "##END=\n"
        )
        result = parser.parse_text(content)
        assert result["type"] == "NMR"
        assert result["header"]["TITLE"] == "Test Spectrum"

    def test_detect_ir_type(self):
        from spectra_ai.parsers.jcamp_parser import JCAMPParser
        parser = JCAMPParser()
        content = (
            "##TITLE= IR Test\n"
            "##DATATYPE= INFRARED SPECTRUM\n"
            "##XUNITS= 1/CM\n"
            "##END=\n"
        )
        result = parser.parse_text(content)
        assert result["type"] == "IR"
