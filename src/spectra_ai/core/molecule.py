"""
Molecule data model — central container for all compound data.

A Molecule holds structural information (SMILES, formula, MW) plus
all spectral data (NMR, IR, MS, UV-Vis) and metadata about synthesis
conditions and scaffold classification.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime


# ── Standard atomic weights for formula → MW calculation ──────────────────────
_ATOMIC_WEIGHTS = {
    "H": 1.00794, "C": 12.0107, "N": 14.0067, "O": 15.9994,
    "F": 18.9984, "S": 32.065, "P": 30.9738, "Cl": 35.453,
    "Br": 79.904, "I": 126.904, "Si": 28.0855, "B": 10.811,
    "Se": 78.971, "Na": 22.9898,
}

# ── Scaffold family constants ─────────────────────────────────────────────────
SCAFFOLD_FAMILIES = [
    "imidazopyridine",
    "indole",
    "quinazoline",
    "triazole",
    "pyrazolopyrimidine",
    "coumarin",
    "quinoline",
    "isoquinoline",
    "oxadiazole",
    "thiazole",
    "benzimidazole",
    "other",
]


@dataclass
class MoleculeMetadata:
    """Metadata about synthesis conditions and provenance."""

    scaffold_family: str = "other"
    reaction_type: str = ""          # e.g. "CuAAC", "Pd-catalyzed C-N coupling"
    catalyst: str = ""               # e.g. "CuCl₂", "Pd(OAc)₂"
    solvent_media: str = ""          # e.g. "[bmim][BF4]", "DMF"
    is_ionic_liquid: bool = False
    source_paper: str = ""           # Citation string
    date_analyzed: str = field(default_factory=lambda: datetime.now().isoformat())
    notes: str = ""
    extra_data: dict = field(default_factory=dict)


@dataclass
class Molecule:
    """
    Central container representing a chemical compound with all associated data.

    Attributes:
        compound_id:  Unique identifier (e.g. "SPEC-001")
        name:         Human-readable name
        smiles:       SMILES string (canonical preferred)
        formula:      Molecular formula (e.g. "C15H12N2O")
        molecular_weight: Calculated molecular weight
        metadata:     Synthesis / provenance metadata
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    compound_id: str = ""
    name: str = ""
    smiles: str = ""
    formula: str = ""
    molecular_weight: float = 0.0

    # ── Metadata ──────────────────────────────────────────────────────────────
    metadata: MoleculeMetadata = field(default_factory=MoleculeMetadata)

    # ── Spectral data (set after construction via setters / parsers) ──────────
    # These are stored as dicts and converted to typed objects when accessed
    _h1_nmr: Optional[dict] = field(default=None, repr=False)
    _c13_nmr: Optional[dict] = field(default=None, repr=False)
    _dept: Optional[dict] = field(default=None, repr=False)
    _ir: Optional[dict] = field(default=None, repr=False)
    _hrms: Optional[dict] = field(default=None, repr=False)
    _uv_vis: Optional[dict] = field(default=None, repr=False)
    melting_point: Optional[tuple] = None          # (low, high) in °C
    elemental_analysis: Optional[dict] = None      # {"C": 72.3, "H": 5.1, ...}

    # ── Computed properties ───────────────────────────────────────────────────

    @property
    def has_smiles(self) -> bool:
        return bool(self.smiles and self.smiles.strip())

    @property
    def has_h1_nmr(self) -> bool:
        return self._h1_nmr is not None

    @property
    def has_c13_nmr(self) -> bool:
        return self._c13_nmr is not None

    @property
    def has_ir(self) -> bool:
        return self._ir is not None

    @property
    def has_hrms(self) -> bool:
        return self._hrms is not None

    @property
    def has_uv_vis(self) -> bool:
        return self._uv_vis is not None

    @property
    def has_melting_point(self) -> bool:
        return self.melting_point is not None

    @property
    def has_elemental_analysis(self) -> bool:
        return self.elemental_analysis is not None

    @property
    def data_completeness(self) -> float:
        """Calculate data completeness as a percentage (0–100)."""
        checks = [
            self.has_smiles,
            self.has_h1_nmr,
            self.has_c13_nmr,
            self.has_ir,
            self.has_hrms,
            self.has_uv_vis,
            self.has_melting_point,
            self.has_elemental_analysis,
        ]
        return round((sum(checks) / len(checks)) * 100, 1)

    @property
    def completeness_breakdown(self) -> dict:
        """Return per-data-type completeness for the UI ring widget."""
        return {
            "Structure": self.has_smiles,
            "¹H NMR": self.has_h1_nmr,
            "¹³C NMR": self.has_c13_nmr,
            "IR": self.has_ir,
            "HRMS": self.has_hrms,
            "UV-Vis": self.has_uv_vis,
            "MP": self.has_melting_point,
            "EA": self.has_elemental_analysis,
        }

    @property
    def expected_carbon_count(self) -> int:
        """Extract expected number of unique carbons from molecular formula."""
        return self._count_element_in_formula("C")

    @property
    def expected_hydrogen_count(self) -> int:
        """Extract expected number of hydrogens from molecular formula."""
        return self._count_element_in_formula("H")

    @property
    def expected_nitrogen_count(self) -> int:
        """Extract expected number of nitrogens from molecular formula."""
        return self._count_element_in_formula("N")

    # ── Formula parsing ───────────────────────────────────────────────────────

    def _count_element_in_formula(self, element: str) -> int:
        """Count occurrences of an element in the molecular formula."""
        if not self.formula:
            return 0
        # Match element symbol followed by optional count
        pattern = rf"{re.escape(element)}(\d*)"
        matches = re.findall(pattern, self.formula)
        total = 0
        for count_str in matches:
            total += int(count_str) if count_str else 1
        return total

    def calculate_molecular_weight(self) -> float:
        """Calculate MW from molecular formula."""
        if not self.formula:
            return 0.0
        mw = 0.0
        # Parse formula: match element symbol + optional count
        tokens = re.findall(r"([A-Z][a-z]?)(\d*)", self.formula)
        for symbol, count_str in tokens:
            if symbol in _ATOMIC_WEIGHTS:
                count = int(count_str) if count_str else 1
                mw += _ATOMIC_WEIGHTS[symbol] * count
        self.molecular_weight = round(mw, 4)
        return self.molecular_weight

    def calculate_exact_mass(self) -> float:
        """Calculate monoisotopic exact mass from formula."""
        # Monoisotopic masses
        exact = {
            "H": 1.007825, "C": 12.000000, "N": 14.003074, "O": 15.994915,
            "F": 18.998403, "S": 31.972071, "P": 30.973762, "Cl": 34.968853,
            "Br": 78.918338, "I": 126.904473, "Si": 27.976927, "Se": 79.916522,
        }
        if not self.formula:
            return 0.0
        mass = 0.0
        tokens = re.findall(r"([A-Z][a-z]?)(\d*)", self.formula)
        for symbol, count_str in tokens:
            if symbol in exact:
                count = int(count_str) if count_str else 1
                mass += exact[symbol] * count
        return round(mass, 6)

    # ── Serialization ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Convert molecule to a serializable dictionary."""
        d = {
            "compound_id": self.compound_id,
            "name": self.name,
            "smiles": self.smiles,
            "formula": self.formula,
            "molecular_weight": self.molecular_weight,
            "metadata": asdict(self.metadata),
            "h1_nmr": self._h1_nmr,
            "c13_nmr": self._c13_nmr,
            "dept": self._dept,
            "ir": self._ir,
            "hrms": self._hrms,
            "uv_vis": self._uv_vis,
            "melting_point": list(self.melting_point) if self.melting_point else None,
            "elemental_analysis": self.elemental_analysis,
        }
        return d

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict) -> "Molecule":
        """Construct a Molecule from a dictionary."""
        meta_data = data.get("metadata", {})
        
        # Filter known metadata fields to avoid TypeError
        import dataclasses
        valid_keys = {f.name for f in dataclasses.fields(MoleculeMetadata)}
        clean_meta = {k: v for k, v in meta_data.items() if k in valid_keys}
        
        # Put any extra metadata fields into extra_data
        extra_meta = {k: v for k, v in meta_data.items() if k not in valid_keys}
        if "extra_data" in valid_keys:
            if "extra_data" not in clean_meta:
                clean_meta["extra_data"] = {}
            clean_meta["extra_data"].update(extra_meta)
            
        # Catch any top-level unrecognized fields and push them to extra_data
        valid_mol_keys = {"compound_id", "name", "smiles", "formula", "molecular_weight", "metadata", "h1_nmr", "c13_nmr", "dept", "ir", "hrms", "uv_vis", "melting_point", "elemental_analysis"}
        mol_extra = {k: v for k, v in data.items() if k not in valid_mol_keys}
        if mol_extra and "extra_data" in valid_keys:
            if "extra_data" not in clean_meta:
                clean_meta["extra_data"] = {}
            clean_meta["extra_data"].update(mol_extra)

        mol = cls(
            compound_id=data.get("compound_id", ""),
            name=data.get("name", ""),
            smiles=data.get("smiles", ""),
            formula=data.get("formula", ""),
            molecular_weight=data.get("molecular_weight", 0.0),
            metadata=MoleculeMetadata(**clean_meta) if clean_meta else MoleculeMetadata(),
        )
        mol._h1_nmr = data.get("h1_nmr")
        mol._c13_nmr = data.get("c13_nmr")
        mol._dept = data.get("dept")
        mol._ir = data.get("ir")
        mol._hrms = data.get("hrms")
        mol._uv_vis = data.get("uv_vis")
        mp = data.get("melting_point")
        mol.melting_point = tuple(mp) if mp else None
        mol.elemental_analysis = data.get("elemental_analysis")
        return mol

    @classmethod
    def from_json(cls, json_str: str) -> "Molecule":
        """Construct a Molecule from a JSON string."""
        return cls.from_dict(json.loads(json_str))

    @classmethod
    def from_json_file(cls, filepath: str) -> "Molecule":
        """Load a Molecule from a JSON file."""
        with open(filepath, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    def save_json(self, filepath: str) -> None:
        """Save molecule data to a JSON file."""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    def __str__(self) -> str:
        return (
            f"Molecule({self.compound_id}: {self.name}, "
            f"{self.formula}, MW={self.molecular_weight:.2f}, "
            f"completeness={self.data_completeness}%)"
        )
