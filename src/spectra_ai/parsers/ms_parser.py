"""
Mass Spectrometry Text Parser for SpectraAI.

Parses HRMS data from journal experimental sections.

Handles formats like:
  HRMS (ESI) m/z calcd for C₁₅H₁₃N₂O [M+H]⁺ 237.1022, found 237.1019
  HRMS (ESI-TOF): m/z [M + H]+ Calcd for C15H13N2O 237.1022; Found 237.1019
"""

from __future__ import annotations

import re
from ..core.ms_data import MSData


class MSTextParser:
    """Parser for HRMS text from journal experimental sections."""

    def parse(self, text: str) -> MSData:
        """
        Parse HRMS text into MSData.

        Args:
            text: Raw HRMS text

        Returns:
            MSData object
        """
        text = self._normalize(text)

        technique = self._extract_technique(text)
        ion_type = self._extract_ion_type(text)
        formula, ion_formula = self._extract_formulas(text)
        calculated, observed = self._extract_masses(text)

        return MSData(
            technique=technique,
            ion_type=ion_type,
            calculated_mz=calculated,
            observed_mz=observed,
            formula=formula,
            ion_formula=ion_formula,
            raw_text=text.strip(),
        )

    def _normalize(self, text: str) -> str:
        """Normalize unicode characters."""
        subscripts = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
        text = text.translate(subscripts)
        text = text.replace("⁺", "+").replace("⁻", "-")
        text = re.sub(r"\s+", " ", text)
        return text

    def _extract_technique(self, text: str) -> str:
        """Extract ionization technique."""
        techniques = ["ESI-TOF", "ESI-QTOF", "ESI", "APCI", "EI", "MALDI", "FAB", "CI"]
        for tech in techniques:
            if tech.lower() in text.lower():
                return tech
        return "ESI"

    def _extract_ion_type(self, text: str) -> str:
        """Extract ion adduct type."""
        ion_patterns = [
            (r"\[M\s*\+\s*H\]\s*\+", "[M+H]+"),
            (r"\[M\s*\+\s*Na\]\s*\+", "[M+Na]+"),
            (r"\[M\s*\+\s*K\]\s*\+", "[M+K]+"),
            (r"\[M\s*\+\s*NH4\]\s*\+", "[M+NH4]+"),
            (r"\[M\s*-\s*H\]\s*-", "[M-H]-"),
            (r"\[M\s*\+\s*Cl\]\s*-", "[M+Cl]-"),
            (r"\[M\]\s*\+", "[M]+"),
            (r"\[M\s*\+\s*2H\]\s*2\+", "[M+2H]2+"),
        ]
        for pattern, ion_type in ion_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return ion_type
        return "[M+H]+"

    def _extract_formulas(self, text: str) -> tuple[str, str]:
        """Extract molecular and ion formulas."""
        # Look for formula pattern like C15H13N2O
        formula_pattern = re.compile(r"([A-Z][a-z]?\d*(?:[A-Z][a-z]?\d*)*)")
        formulas = formula_pattern.findall(text)

        # Filter to keep only things that look like molecular formulas
        valid_formulas = []
        for f in formulas:
            if re.match(r"^[CHNO][A-Za-z0-9]+$", f) and len(f) >= 4:
                valid_formulas.append(f)

        ion_formula = valid_formulas[0] if valid_formulas else ""
        # The neutral formula is often the same but without the extra H for [M+H]+
        formula = ion_formula

        return formula, ion_formula

    def _extract_masses(self, text: str) -> tuple[float, float]:
        """Extract calculated and observed m/z values."""
        # Look for pairs of decimal numbers
        numbers = re.findall(r"(\d+\.\d{3,6})", text)

        calculated = 0.0
        observed = 0.0

        if len(numbers) >= 2:
            # Usually calculated comes before found
            calculated = float(numbers[0])
            observed = float(numbers[1])
        elif len(numbers) == 1:
            # Only one number found
            if "found" in text.lower() or "obs" in text.lower():
                observed = float(numbers[0])
            else:
                calculated = float(numbers[0])

        return calculated, observed


# Convenience function
_parser = MSTextParser()


def parse_ms_text(text: str) -> MSData:
    """Parse HRMS text into MSData (convenience function)."""
    return _parser.parse(text)
