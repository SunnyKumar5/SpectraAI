"""
NMR Text Parser for SpectraAI.

Parses ¹H NMR and ¹³C NMR text as typically written in journal
experimental sections into structured NMRData and NMRPeak objects.

Handles formats like:
  ¹H NMR (400 MHz, CDCl₃): δ 8.45 (s, 1H, H-5), 7.72 (d, J = 8.4 Hz, 2H, ArH), ...
  ¹³C NMR (100 MHz, CDCl₃): δ 158.2, 147.5, 133.8, ...
"""

from __future__ import annotations

import re
from typing import Optional

from ..core.nmr_data import NMRData, NMRPeak


class NMRTextParser:
    """
    Parser for NMR text from journal experimental sections.

    Supports both ¹H and ¹³C NMR formats with various journal styles
    (ACS, RSC, Wiley, etc.).
    """

    # ── Regex patterns ────────────────────────────────────────────────────────

    # Header pattern: "¹H NMR (400 MHz, CDCl₃): δ ..."
    HEADER_PATTERN = re.compile(
        r"(?:¹H|1H|H-1|proton)\s*NMR\s*"
        r"\(\s*(\d+)\s*MHz\s*,\s*([^)]+)\s*\)\s*:?\s*(?:δ|delta)?\s*",
        re.IGNORECASE,
    )

    C13_HEADER_PATTERN = re.compile(
        r"(?:¹³C|13C|C-13|carbon)\s*(?:[\{\(]?\s*DEPT\s*[\}\)]?)?\s*NMR\s*"
        r"\(\s*(\d+)\s*MHz\s*,\s*([^)]+)\s*\)\s*:?\s*(?:δ|delta)?\s*",
        re.IGNORECASE,
    )

    # Individual ¹H peak: "8.45 (s, 1H, H-5)" or "8.45 (s, 1H)" or "8.45 (s)"
    H1_PEAK_PATTERN = re.compile(
        r"(\d+\.?\d*)\s*"                              # chemical shift
        r"\(\s*"                                         # opening paren
        r"((?:br\s+)?[a-z]{1,4}(?:\s+[a-z]{1,3})?)\s*" # multiplicity
        r"(?:,\s*J\s*=?\s*([\d.,\s]+)\s*Hz)?\s*"       # optional J values
        r"(?:,\s*(\d+\.?\d*)\s*H)?\s*"                  # optional integration
        r"(?:,\s*([^)]*?))?\s*"                          # optional assignment
        r"\)",                                            # closing paren
        re.IGNORECASE,
    )

    # Simpler pattern for peaks without parenthetical details: "8.45"
    SIMPLE_SHIFT_PATTERN = re.compile(r"(\d+\.?\d+)")

    # ¹³C peaks are typically just comma-separated shifts
    C13_PEAKS_PATTERN = re.compile(r"(\d+\.?\d+)")

    def parse_h1(self, text: str) -> NMRData:
        """
        Parse ¹H NMR text into NMRData.

        Args:
            text: Raw NMR text (e.g. from a paper's experimental section)

        Returns:
            NMRData object with parsed peaks
        """
        # Normalize unicode characters
        text = self._normalize_text(text)

        # Extract header info
        frequency, solvent = self._extract_header(text, nucleus="1H")

        # Extract peaks
        peaks = self._extract_h1_peaks(text)

        return NMRData(
            nucleus="1H",
            frequency=frequency,
            solvent=solvent,
            peaks=peaks,
            raw_text=text.strip(),
        )

    def parse_c13(self, text: str) -> NMRData:
        """
        Parse ¹³C NMR text into NMRData.

        Args:
            text: Raw ¹³C NMR text

        Returns:
            NMRData object with parsed peaks
        """
        text = self._normalize_text(text)
        frequency, solvent = self._extract_header(text, nucleus="13C")
        peaks = self._extract_c13_peaks(text)

        return NMRData(
            nucleus="13C",
            frequency=frequency,
            solvent=solvent,
            peaks=peaks,
            raw_text=text.strip(),
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _normalize_text(self, text: str) -> str:
        """Normalize unicode and special characters."""
        replacements = {
            "δ": "δ", "¹": "1", "³": "3",
            "\u2013": "-", "\u2014": "-",     # en/em dashes
            "\u00a0": " ",                     # non-breaking space
            "−": "-",                          # minus sign
            "'": "'", "'": "'",
            "\n": " ", "\r": " ",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        # Collapse whitespace
        text = re.sub(r"\s+", " ", text)
        return text

    def _extract_header(self, text: str, nucleus: str = "1H") -> tuple[int, str]:
        """Extract frequency and solvent from header."""
        if nucleus == "1H":
            match = self.HEADER_PATTERN.search(text)
        else:
            match = self.C13_HEADER_PATTERN.search(text)

        if match:
            frequency = int(match.group(1))
            solvent = match.group(2).strip().rstrip(",").strip()
            # Normalize solvent names
            solvent = self._normalize_solvent(solvent)
            return frequency, solvent

        # Try generic extraction
        freq_match = re.search(r"(\d{2,3})\s*MHz", text, re.IGNORECASE)
        frequency = int(freq_match.group(1)) if freq_match else 400

        solvent = "CDCl3"
        for s in ["DMSO-d6", "DMSO", "CDCl3", "CDCl₃", "D2O", "CD3OD", "acetone-d6", "C6D6", "CD3CN"]:
            if s.lower() in text.lower():
                solvent = self._normalize_solvent(s)
                break

        return frequency, solvent

    def _normalize_solvent(self, solvent: str) -> str:
        """Normalize solvent name to standard form."""
        mapping = {
            "cdcl3": "CDCl3", "cdcl₃": "CDCl3", "chloroform-d": "CDCl3",
            "dmso-d6": "DMSO-d6", "dmso-d₆": "DMSO-d6", "dmso": "DMSO-d6",
            "d2o": "D2O", "d₂o": "D2O",
            "cd3od": "CD3OD", "cd₃od": "CD3OD", "methanol-d4": "CD3OD",
            "acetone-d6": "acetone-d6", "cd3cn": "CD3CN",
            "c6d6": "C6D6", "benzene-d6": "C6D6",
        }
        return mapping.get(solvent.lower().strip(), solvent.strip())

    def _extract_h1_peaks(self, text: str) -> list[NMRPeak]:
        """Extract individual ¹H NMR peaks from text."""
        peaks = []

        # Try the detailed pattern first
        for match in self.H1_PEAK_PATTERN.finditer(text):
            shift = float(match.group(1))
            mult = match.group(2).strip().lower()
            j_str = match.group(3)
            integ_str = match.group(4)
            assignment = (match.group(5) or "").strip()

            # Parse J-values
            j_values = []
            if j_str:
                j_values = [float(j.strip()) for j in re.findall(r"[\d.]+", j_str)]

            # Parse integration
            integration = float(integ_str) if integ_str else 0.0

            peak = NMRPeak(
                chemical_shift=shift,
                multiplicity=mult,
                coupling_constants=j_values,
                integration=integration,
                assignment=assignment,
                raw_text=match.group(0),
            )
            peaks.append(peak)

        # If no peaks found with detailed pattern, try simpler approach
        if not peaks:
            peaks = self._fallback_h1_parse(text)

        # Sort by chemical shift (descending, as is convention)
        peaks.sort(key=lambda p: p.chemical_shift, reverse=True)
        return peaks

    def _fallback_h1_parse(self, text: str) -> list[NMRPeak]:
        """
        Fallback parser for less standard ¹H NMR formats.

        Tries to extract at least chemical shifts from the text.
        """
        peaks = []
        # Remove header portion
        text_body = re.sub(
            r".*?(?:δ|delta)\s*", "", text, count=1, flags=re.IGNORECASE
        )

        # Split by common delimiters
        segments = re.split(r"[;,]\s*", text_body)

        for segment in segments:
            shift_match = re.search(r"(\d+\.?\d+)", segment)
            if shift_match:
                shift = float(shift_match.group(1))
                # Basic range check for ¹H
                if 0.0 <= shift <= 15.0:
                    peak = NMRPeak(
                        chemical_shift=shift,
                        raw_text=segment.strip(),
                    )
                    peaks.append(peak)

        return peaks

    def _extract_c13_peaks(self, text: str) -> list[NMRPeak]:
        """
        Extract ¹³C NMR peaks from text.

        ¹³C peaks are typically just comma-separated shift values.
        """
        peaks = []

        # Remove header
        text_body = re.sub(
            r".*?(?:δ|delta)\s*", "", text, count=1, flags=re.IGNORECASE
        )

        # Extract all numbers that look like ¹³C chemical shifts (0-230 ppm)
        for match in self.C13_PEAKS_PATTERN.finditer(text_body):
            shift = float(match.group(1))
            if 0.0 <= shift <= 230.0:
                peak = NMRPeak(chemical_shift=shift, multiplicity="s")
                peaks.append(peak)

        # Sort descending
        peaks.sort(key=lambda p: p.chemical_shift, reverse=True)
        return peaks


# ── Convenience functions ─────────────────────────────────────────────────────

_parser = NMRTextParser()


def parse_h1_nmr_text(text: str) -> NMRData:
    """Parse ¹H NMR text into NMRData (convenience function)."""
    return _parser.parse_h1(text)


def parse_c13_nmr_text(text: str) -> NMRData:
    """Parse ¹³C NMR text into NMRData (convenience function)."""
    return _parser.parse_c13(text)
