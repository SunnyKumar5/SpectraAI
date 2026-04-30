"""
IR (Infrared Spectroscopy) data models for SpectraAI.

Represents IR absorption data with wavenumber, intensity,
and functional group assignments.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ── Reference IR absorption ranges for common functional groups ───────────────
IR_FUNCTIONAL_GROUPS = {
    "O-H (alcohol)": (3200, 3550, "broad, strong"),
    "O-H (carboxylic)": (2500, 3300, "very broad, strong"),
    "N-H (amine)": (3300, 3500, "medium, sometimes two bands"),
    "N-H (amide)": (3100, 3500, "medium-strong"),
    "C-H (sp3)": (2850, 3000, "medium-strong"),
    "C-H (sp2)": (3000, 3100, "medium"),
    "C-H (sp/alkyne)": (3200, 3340, "strong, sharp"),
    "C-H (aldehyde)": (2700, 2850, "medium, two bands"),
    "C≡N (nitrile)": (2200, 2260, "medium-strong, sharp"),
    "C≡C (alkyne)": (2100, 2260, "weak-medium"),
    "C=O (ketone)": (1700, 1725, "strong"),
    "C=O (aldehyde)": (1720, 1740, "strong"),
    "C=O (ester)": (1735, 1750, "strong"),
    "C=O (carboxylic)": (1700, 1725, "strong"),
    "C=O (amide)": (1630, 1690, "strong"),
    "C=C (alkene)": (1600, 1680, "medium"),
    "C=C (aromatic)": (1450, 1600, "medium, multiple bands"),
    "C=N": (1600, 1680, "medium-strong"),
    "N=O (nitro)": (1515, 1560, "strong, two bands"),
    "C-O (ether)": (1000, 1300, "strong"),
    "C-O (ester)": (1150, 1300, "strong"),
    "C-F": (1000, 1400, "strong"),
    "C-Cl": (550, 850, "strong"),
    "C-Br": (500, 680, "strong"),
    "S=O (sulfone)": (1120, 1160, "strong"),
    "S=O (sulfoxide)": (1030, 1070, "strong"),
}


@dataclass
class IRAbsorption:
    """
    A single IR absorption band.

    Attributes:
        wavenumber:   Absorption frequency in cm⁻¹
        intensity:    Qualitative intensity (strong, medium, weak, broad)
        assignment:   Functional group assignment
    """

    wavenumber: float
    intensity: str = ""           # "strong", "medium", "weak", "broad"
    assignment: str = ""

    # AI-generated fields
    ai_assignment: str = ""
    ai_reasoning: str = ""
    ai_status: str = ""           # "consistent", "warning", "conflict"

    @property
    def region(self) -> str:
        """Classify absorption into spectral region."""
        if self.wavenumber >= 4000:
            return "out of range"
        elif self.wavenumber >= 2500:
            return "X-H stretching"
        elif self.wavenumber >= 2000:
            return "triple bond"
        elif self.wavenumber >= 1500:
            return "double bond"
        else:
            return "fingerprint"

    @property
    def display_text(self) -> str:
        parts = [f"{self.wavenumber:.0f} cm⁻¹"]
        if self.intensity:
            parts.append(f"({self.intensity})")
        if self.assignment:
            parts.append(f"— {self.assignment}")
        return " ".join(parts)

    def to_dict(self) -> dict:
        return {
            "wavenumber": self.wavenumber,
            "intensity": self.intensity,
            "assignment": self.assignment,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "IRAbsorption":
        return cls(
            wavenumber=data.get("wavenumber", 0.0),
            intensity=data.get("intensity", ""),
            assignment=data.get("assignment", ""),
        )


@dataclass
class IRData:
    """
    Complete IR spectral dataset.

    Attributes:
        method:       Sample preparation (KBr, ATR, neat, etc.)
        absorptions:  List of absorption bands
        raw_text:     Original text input before parsing
    """

    method: str = "KBr"
    absorptions: list[IRAbsorption] = field(default_factory=list)
    raw_text: str = ""

    @property
    def band_count(self) -> int:
        return len(self.absorptions)

    @property
    def wavenumber_range(self) -> tuple[float, float]:
        if not self.absorptions:
            return (0.0, 0.0)
        wn = [a.wavenumber for a in self.absorptions]
        return (min(wn), max(wn))

    def sorted_absorptions(self, descending: bool = True) -> list[IRAbsorption]:
        """Return absorptions sorted by wavenumber."""
        return sorted(
            self.absorptions, key=lambda a: a.wavenumber, reverse=descending
        )

    def find_in_range(self, low: float, high: float) -> list[IRAbsorption]:
        """Find absorptions within a wavenumber range."""
        return [a for a in self.absorptions if low <= a.wavenumber <= high]

    def has_functional_group(self, group_name: str, tolerance: float = 50.0) -> bool:
        """Check if an absorption consistent with a functional group is present."""
        if group_name not in IR_FUNCTIONAL_GROUPS:
            return False
        low, high, _ = IR_FUNCTIONAL_GROUPS[group_name]
        low -= tolerance
        high += tolerance
        return len(self.find_in_range(low, high)) > 0

    def to_dict(self) -> dict:
        return {
            "method": self.method,
            "absorptions": [a.to_dict() for a in self.absorptions],
            "raw_text": self.raw_text,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "IRData":
        absorptions = [IRAbsorption.from_dict(a) for a in data.get("absorptions", [])]
        return cls(
            method=data.get("method", "KBr"),
            absorptions=absorptions,
            raw_text=data.get("raw_text", ""),
        )
