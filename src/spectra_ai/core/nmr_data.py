"""
NMR data models for SpectraAI.

Represents ¹H NMR, ¹³C NMR, and DEPT spectral data with peak-level
granularity including chemical shifts, multiplicities, coupling constants,
integrations, and assignments.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class NMRNucleus(str, Enum):
    """Supported NMR nuclei."""
    H1 = "1H"
    C13 = "13C"
    DEPT135 = "DEPT-135"
    DEPT90 = "DEPT-90"


class Multiplicity(str, Enum):
    """Standard NMR peak multiplicities."""
    SINGLET = "s"
    DOUBLET = "d"
    TRIPLET = "t"
    QUARTET = "q"
    QUINTET = "quint"
    SEXTET = "sext"
    SEPTET = "sept"
    MULTIPLET = "m"
    DOUBLET_OF_DOUBLETS = "dd"
    DOUBLET_OF_TRIPLETS = "dt"
    TRIPLET_OF_DOUBLETS = "td"
    DOUBLET_OF_DOUBLET_OF_DOUBLETS = "ddd"
    BROAD_SINGLET = "br s"
    BROAD = "br"
    APPARENT_TRIPLET = "app t"

    @classmethod
    def from_string(cls, s: str) -> "Multiplicity":
        """Parse a multiplicity string to enum value."""
        s = s.strip().lower()
        for member in cls:
            if member.value == s:
                return member
        # Fuzzy matching
        mapping = {
            "singlet": cls.SINGLET, "doublet": cls.DOUBLET,
            "triplet": cls.TRIPLET, "quartet": cls.QUARTET,
            "multiplet": cls.MULTIPLET, "broad singlet": cls.BROAD_SINGLET,
            "broad": cls.BROAD, "br s": cls.BROAD_SINGLET,
            "app t": cls.APPARENT_TRIPLET,
        }
        return mapping.get(s, cls.MULTIPLET)


# ── Standard solvent residual peaks (for reference / impurity detection) ──────
SOLVENT_RESIDUAL_PEAKS = {
    "CDCl3": {"1H": [7.26], "13C": [77.16]},
    "DMSO-d6": {"1H": [2.50], "13C": [39.52]},
    "D2O": {"1H": [4.79], "13C": []},
    "CD3OD": {"1H": [3.31, 4.87], "13C": [49.00]},
    "acetone-d6": {"1H": [2.05], "13C": [29.84, 206.26]},
    "CD3CN": {"1H": [1.94], "13C": [1.32, 118.26]},
    "C6D6": {"1H": [7.16], "13C": [128.06]},
}


@dataclass
class NMRPeak:
    """
    A single NMR peak with full characterization.

    Attributes:
        chemical_shift: Chemical shift in ppm (δ)
        multiplicity:   Peak multiplicity (s, d, t, q, m, dd, etc.)
        coupling_constants: J-values in Hz (list for multi-coupling)
        integration:    Number of protons (¹H only)
        assignment:     Chemical assignment (e.g. "H-5", "ArH", "OCH₃")
        raw_text:       Original text as parsed from input
    """

    chemical_shift: float
    multiplicity: str = "s"
    coupling_constants: list[float] = field(default_factory=list)
    integration: float = 0.0
    assignment: str = ""
    raw_text: str = ""

    # ── AI-generated fields (populated after analysis) ────────────────────────
    ai_assignment: str = ""
    ai_reasoning: str = ""
    ai_confidence: str = ""      # "high", "medium", "low"
    ai_status: str = ""          # "consistent", "warning", "conflict"

    @property
    def multiplicity_enum(self) -> Multiplicity:
        """Get multiplicity as enum."""
        return Multiplicity.from_string(self.multiplicity)

    @property
    def j_string(self) -> str:
        """Format coupling constants as a display string."""
        if not self.coupling_constants:
            return ""
        return ", ".join(f"{j:.1f}" for j in self.coupling_constants)

    @property
    def display_text(self) -> str:
        """Generate a formatted display string for this peak."""
        parts = [f"δ {self.chemical_shift:.2f}"]
        mult_str = f"({self.multiplicity}"
        if self.coupling_constants:
            mult_str += f", J = {self.j_string} Hz"
        if self.integration > 0:
            h_count = int(self.integration) if self.integration == int(self.integration) else self.integration
            mult_str += f", {h_count}H"
        mult_str += ")"
        parts.append(mult_str)
        if self.assignment:
            parts.append(self.assignment)
        return " ".join(parts)

    def to_dict(self) -> dict:
        return {
            "shift": self.chemical_shift,
            "multiplicity": self.multiplicity,
            "J": self.coupling_constants,
            "integration": self.integration,
            "assignment": self.assignment,
            "raw_text": self.raw_text,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NMRPeak":
        return cls(
            chemical_shift=data.get("shift", 0.0),
            multiplicity=data.get("multiplicity", "s"),
            coupling_constants=data.get("J", []),
            integration=data.get("integration", 0.0),
            assignment=data.get("assignment", ""),
            raw_text=data.get("raw_text", ""),
        )


@dataclass
class NMRData:
    """
    Complete NMR dataset for one nucleus type.

    Attributes:
        nucleus:    NMR nucleus type ("1H", "13C", "DEPT-135")
        frequency:  Spectrometer frequency in MHz (e.g. 400, 500)
        solvent:    Deuterated solvent (e.g. "CDCl3", "DMSO-d6")
        peaks:      List of NMR peaks
        raw_text:   Original text input before parsing
    """

    nucleus: str = "1H"
    frequency: int = 400
    solvent: str = "CDCl3"
    peaks: list[NMRPeak] = field(default_factory=list)
    raw_text: str = ""

    @property
    def peak_count(self) -> int:
        return len(self.peaks)

    @property
    def total_integration(self) -> float:
        """Sum of all peak integrations (meaningful for ¹H)."""
        return sum(p.integration for p in self.peaks)

    @property
    def shift_range(self) -> tuple[float, float]:
        """Return (min_shift, max_shift) across all peaks."""
        if not self.peaks:
            return (0.0, 0.0)
        shifts = [p.chemical_shift for p in self.peaks]
        return (min(shifts), max(shifts))

    @property
    def aromatic_peaks(self) -> list[NMRPeak]:
        """Peaks in the aromatic region (6.0–9.5 ppm for ¹H, 100–160 for ¹³C)."""
        if self.nucleus == "1H":
            return [p for p in self.peaks if 6.0 <= p.chemical_shift <= 9.5]
        elif self.nucleus == "13C":
            return [p for p in self.peaks if 100.0 <= p.chemical_shift <= 160.0]
        return []

    @property
    def aliphatic_peaks(self) -> list[NMRPeak]:
        """Peaks in the aliphatic region (0–4.5 ppm for ¹H, 0–80 for ¹³C)."""
        if self.nucleus == "1H":
            return [p for p in self.peaks if 0.0 <= p.chemical_shift <= 4.5]
        elif self.nucleus == "13C":
            return [p for p in self.peaks if 0.0 <= p.chemical_shift <= 80.0]
        return []

    @property
    def carbonyl_peaks(self) -> list[NMRPeak]:
        """¹³C peaks in the carbonyl region (160–220 ppm)."""
        if self.nucleus != "13C":
            return []
        return [p for p in self.peaks if 160.0 <= p.chemical_shift <= 220.0]

    def sorted_peaks(self, descending: bool = True) -> list[NMRPeak]:
        """Return peaks sorted by chemical shift."""
        return sorted(self.peaks, key=lambda p: p.chemical_shift, reverse=descending)

    def to_dict(self) -> dict:
        return {
            "nucleus": self.nucleus,
            "frequency": self.frequency,
            "solvent": self.solvent,
            "peaks": [p.to_dict() for p in self.peaks],
            "raw_text": self.raw_text,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NMRData":
        peaks = [NMRPeak.from_dict(p) for p in data.get("peaks", [])]
        return cls(
            nucleus=data.get("nucleus", "1H"),
            frequency=data.get("frequency", 400),
            solvent=data.get("solvent", "CDCl3"),
            peaks=peaks,
            raw_text=data.get("raw_text", ""),
        )


@dataclass
class NMRSpectrum:
    """
    Synthetic spectrum data for rendering (generated from peak list).

    Contains arrays of x (ppm) and y (intensity) values for plotting
    a continuous spectrum from discrete peak data.
    """

    x_ppm: list[float] = field(default_factory=list)
    y_intensity: list[float] = field(default_factory=list)
    nucleus: str = "1H"
    x_label: str = "Chemical Shift (ppm)"
    y_label: str = "Intensity"

    @classmethod
    def from_nmr_data(cls, nmr_data: NMRData, num_points: int = 4000,
                       line_width: float = 1.5) -> "NMRSpectrum":
        """
        Generate a synthetic Lorentzian spectrum from discrete NMR peaks.

        Args:
            nmr_data:    Source NMR data with peaks
            num_points:  Number of x-axis points for the spectrum
            line_width:  Peak width at half-height (Hz equivalent, controls broadness)

        Returns:
            NMRSpectrum with x_ppm and y_intensity arrays
        """
        import numpy as np

        if not nmr_data.peaks:
            return cls(nucleus=nmr_data.nucleus)

        shifts = [p.chemical_shift for p in nmr_data.peaks]
        x_min = min(shifts) - 1.0
        x_max = max(shifts) + 1.0

        # For ¹H NMR, typical range is -1 to 14 ppm
        if nmr_data.nucleus == "1H":
            x_min = max(x_min, -0.5)
            x_max = min(x_max, 14.0)
        elif nmr_data.nucleus == "13C":
            x_min = max(x_min, -5.0)
            x_max = min(x_max, 230.0)

        x = np.linspace(x_min, x_max, num_points)
        y = np.zeros_like(x)

        # Convert line_width to ppm (approximate)
        lw_ppm = line_width / nmr_data.frequency if nmr_data.frequency > 0 else 0.004

        for peak in nmr_data.peaks:
            intensity = peak.integration if peak.integration > 0 else 1.0
            # Lorentzian line shape
            y += intensity * (lw_ppm ** 2) / (
                (x - peak.chemical_shift) ** 2 + lw_ppm ** 2
            )

        # Normalize to [0, 1]
        if y.max() > 0:
            y = y / y.max()

        return cls(
            x_ppm=x.tolist(),
            y_intensity=y.tolist(),
            nucleus=nmr_data.nucleus,
        )
