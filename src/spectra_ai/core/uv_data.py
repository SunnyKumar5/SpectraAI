"""
UV-Vis Spectroscopy data models for SpectraAI.

Represents UV-Visible absorption data including wavelength maxima,
extinction coefficients, and chromophore assignments.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class UVAbsorption:
    """A single UV-Vis absorption band."""

    wavelength: float               # λmax in nm
    extinction_coefficient: float = 0.0   # ε (L·mol⁻¹·cm⁻¹)
    log_epsilon: float = 0.0        # log(ε)
    shoulder: bool = False          # Is this a shoulder rather than a max?
    assignment: str = ""            # Chromophore assignment

    @property
    def display_text(self) -> str:
        parts = [f"λmax = {self.wavelength:.0f} nm"]
        if self.extinction_coefficient > 0:
            parts.append(f"(ε = {self.extinction_coefficient:.0f})")
        elif self.log_epsilon > 0:
            parts.append(f"(log ε = {self.log_epsilon:.2f})")
        if self.shoulder:
            parts.append("(sh)")
        if self.assignment:
            parts.append(f"— {self.assignment}")
        return " ".join(parts)

    def to_dict(self) -> dict:
        return {
            "wavelength": self.wavelength,
            "extinction_coefficient": self.extinction_coefficient,
            "log_epsilon": self.log_epsilon,
            "shoulder": self.shoulder,
            "assignment": self.assignment,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UVAbsorption":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class UVData:
    """Complete UV-Vis spectral dataset."""

    solvent: str = ""
    absorptions: list[UVAbsorption] = field(default_factory=list)
    raw_text: str = ""

    @property
    def lambda_max(self) -> Optional[float]:
        """Return the longest wavelength absorption (lowest energy transition)."""
        if not self.absorptions:
            return None
        return max(a.wavelength for a in self.absorptions)

    @property
    def band_count(self) -> int:
        return len(self.absorptions)

    def to_dict(self) -> dict:
        return {
            "solvent": self.solvent,
            "absorptions": [a.to_dict() for a in self.absorptions],
            "raw_text": self.raw_text,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UVData":
        absorptions = [UVAbsorption.from_dict(a) for a in data.get("absorptions", [])]
        return cls(
            solvent=data.get("solvent", ""),
            absorptions=absorptions,
            raw_text=data.get("raw_text", ""),
        )
