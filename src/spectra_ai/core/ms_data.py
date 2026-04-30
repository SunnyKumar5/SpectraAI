"""
Mass Spectrometry data models for SpectraAI.

Represents HRMS (High Resolution Mass Spectrometry) data including
observed/calculated m/z, ion type, formula, and ppm error calculation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


# ── Common ion adducts and their mass offsets ─────────────────────────────────
ION_ADDUCTS = {
    "[M+H]+": 1.007276,
    "[M+Na]+": 22.989218,
    "[M+K]+": 38.963158,
    "[M+NH4]+": 18.034164,
    "[M-H]-": -1.007276,
    "[M+Cl]-": 34.969402,
    "[M]+": 0.000549,       # radical cation (EI)
    "[M-H2O+H]+": -17.002740,
    "[2M+H]+": 1.007276,    # dimer (offset applied to 2×mass)
    "[M+2H]2+": 1.007276,   # doubly charged
}


@dataclass
class MSData:
    """
    High Resolution Mass Spectrometry (HRMS) data.

    Attributes:
        technique:      Ionization technique (ESI, APCI, EI, MALDI, etc.)
        ion_type:       Ion adduct type (e.g. "[M+H]+", "[M+Na]+")
        calculated_mz:  Calculated exact mass for the ion
        observed_mz:    Experimentally observed m/z
        formula:        Molecular formula of the neutral molecule
        ion_formula:    Molecular formula of the detected ion
        raw_text:       Original text input
    """

    technique: str = "ESI"
    ion_type: str = "[M+H]+"
    calculated_mz: float = 0.0
    observed_mz: float = 0.0
    formula: str = ""
    ion_formula: str = ""
    raw_text: str = ""

    # AI-generated fields
    ai_assessment: str = ""
    ai_status: str = ""

    @property
    def ppm_error(self) -> float:
        """Calculate mass accuracy error in ppm."""
        if self.calculated_mz == 0:
            return 0.0
        return abs(
            (self.observed_mz - self.calculated_mz) / self.calculated_mz * 1e6
        )

    @property
    def absolute_error(self) -> float:
        """Calculate absolute mass error in Da."""
        return abs(self.observed_mz - self.calculated_mz)

    @property
    def is_within_tolerance(self) -> bool:
        """Check if mass error is within acceptable tolerance (< 5 ppm)."""
        return self.ppm_error < 5.0

    @property
    def tolerance_status(self) -> str:
        """Return status string based on ppm error."""
        ppm = self.ppm_error
        if ppm < 3.0:
            return "excellent"
        elif ppm < 5.0:
            return "acceptable"
        elif ppm < 10.0:
            return "warning"
        else:
            return "fail"

    @property
    def display_text(self) -> str:
        """Formatted display string for the HRMS data."""
        return (
            f"HRMS ({self.technique}) m/z calcd for {self.ion_formula} "
            f"{self.ion_type} {self.calculated_mz:.4f}, "
            f"found {self.observed_mz:.4f} "
            f"(Δ = {self.ppm_error:.1f} ppm)"
        )

    @property
    def adduct_mass_offset(self) -> float:
        """Get the mass offset for the ion adduct type."""
        return ION_ADDUCTS.get(self.ion_type, 0.0)

    def calculate_expected_mz(self, exact_mass: float) -> float:
        """Calculate expected m/z from neutral exact mass and ion type."""
        offset = self.adduct_mass_offset
        if "2M" in self.ion_type:
            return 2 * exact_mass + offset
        elif "2+" in self.ion_type:
            return (exact_mass + 2 * offset) / 2
        else:
            return exact_mass + offset

    def to_dict(self) -> dict:
        return {
            "technique": self.technique,
            "ion_type": self.ion_type,
            "calculated_mz": self.calculated_mz,
            "observed_mz": self.observed_mz,
            "formula": self.formula,
            "ion_formula": self.ion_formula,
            "raw_text": self.raw_text,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MSData":
        return cls(
            technique=data.get("technique", "ESI"),
            ion_type=data.get("ion_type", data.get("ion", "[M+H]+")),
            calculated_mz=data.get("calculated_mz", data.get("calculated", 0.0)),
            observed_mz=data.get("observed_mz", data.get("found", 0.0)),
            formula=data.get("formula", ""),
            ion_formula=data.get("ion_formula", ""),
            raw_text=data.get("raw_text", ""),
        )
