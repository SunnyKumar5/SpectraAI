"""
IR Text Parser for SpectraAI.

Parses IR absorption data from journal experimental sections.

Handles formats like:
  IR (KBr): ν̃ 3312, 1658, 1598, 1492, 1240, 1028 cm⁻¹
  FT-IR (ATR): 3450 (br), 1720 (s), 1600 (m) cm⁻¹
"""

from __future__ import annotations

import re
from ..core.ir_data import IRData, IRAbsorption


class IRTextParser:
    """Parser for IR spectral text from journal experimental sections."""

    def parse(self, text: str) -> IRData:
        """
        Parse IR text into IRData.

        Args:
            text: Raw IR text from experimental section

        Returns:
            IRData object with parsed absorptions
        """
        text = self._normalize(text)
        method = self._extract_method(text)
        absorptions = self._extract_absorptions(text)

        return IRData(
            method=method,
            absorptions=absorptions,
            raw_text=text.strip(),
        )

    def _normalize(self, text: str) -> str:
        """Normalize unicode and special characters."""
        text = text.replace("ν̃", "v").replace("ν", "v")
        text = text.replace("cm⁻¹", "cm-1").replace("cm−1", "cm-1")
        text = re.sub(r"\s+", " ", text)
        return text

    def _extract_method(self, text: str) -> str:
        """Extract sample preparation method."""
        methods = {
            "KBr": r"\bKBr\b",
            "ATR": r"\bATR\b",
            "neat": r"\bneat\b",
            "film": r"\bfilm\b",
            "Nujol": r"\bNujol\b",
            "CHCl3": r"\bCHCl3\b",
        }
        for method, pattern in methods.items():
            if re.search(pattern, text, re.IGNORECASE):
                return method
        return "KBr"  # default

    def _extract_absorptions(self, text: str) -> list[IRAbsorption]:
        """Extract IR absorption bands from text."""
        absorptions = []

        # Pattern: number possibly followed by (intensity)
        pattern = re.compile(
            r"(\d{3,4})\s*(?:\(\s*([^)]*?)\s*\))?"
        )

        for match in pattern.finditer(text):
            wavenumber = float(match.group(1))
            intensity = (match.group(2) or "").strip()

            # Sanity check: IR range is typically 400-4000 cm⁻¹
            if 400 <= wavenumber <= 4000:
                absorptions.append(IRAbsorption(
                    wavenumber=wavenumber,
                    intensity=intensity,
                ))

        # Sort by wavenumber descending
        absorptions.sort(key=lambda a: a.wavenumber, reverse=True)
        return absorptions


# Convenience function
_parser = IRTextParser()


def parse_ir_text(text: str) -> IRData:
    """Parse IR text into IRData (convenience function)."""
    return _parser.parse(text)
