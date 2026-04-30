"""
CompoundSession -- In-memory session store for all analysed compounds.

Provides CompoundRecord (per-compound data) and CompoundSession (singleton
store with observer callbacks).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Callable, Any

from ..ui.styles.colors import Colors


@dataclass
class CompoundRecord:
    """Everything known about one compound in the session."""

    compound_id: str
    molecule: Any                       # Molecule
    h1_data: Any = None                 # NMRData | None
    c13_data: Any = None                # NMRData | None
    ir_data: Any = None                 # IRData | None
    ms_data: Any = None                 # MSData | None
    validation_report: Any = None       # ValidationReport | None
    h1_result: Optional[dict] = None
    c13_result: Optional[dict] = None
    ir_result: Optional[dict] = None
    ms_result: Optional[dict] = None
    cross_result: Optional[str] = None
    char_text: Optional[str] = None
    atom_mapper: Any = None
    h1_mappings: list = field(default_factory=list)
    c13_mappings: list = field(default_factory=list)
    correlation_maps: Optional[dict] = None
    conformer_sdfs: Optional[list] = None
    thumbnail_svg: Optional[str] = None
    added_at: datetime = field(default_factory=datetime.now)
    analysis_complete: bool = False

    def overall_score(self) -> Optional[int]:
        if self.validation_report and hasattr(self.validation_report, "overall_score"):
            s = self.validation_report.overall_score
            return int(s) if s is not None else None
        return None

    def score_colour(self) -> str:
        s = self.overall_score()
        if s is None:
            return Colors.TEXT_MUTED
        if s >= 80:
            return Colors.ACCENT_GREEN
        if s >= 50:
            return Colors.ACCENT_AMBER
        return Colors.ACCENT_RED

    def display_name(self) -> str:
        mol = self.molecule
        if mol:
            if hasattr(mol, "name") and mol.name:
                return mol.name
            if hasattr(mol, "compound_id") and mol.compound_id:
                return mol.compound_id
        return self.compound_id or "Unnamed"

    def status_label(self) -> str:
        if self.analysis_complete:
            return "Complete"
        return "Pending"


class CompoundSession:
    """
    Session-level store for all analysed compounds.

    Singleton -- use ``CompoundSession.instance()``.

    Observer callbacks (plain Python, not Qt signals):
        on_record_added:   list of  callback(record)
        on_record_removed: list of  callback(index)
        on_active_changed: list of  callback(record | None)
    """

    _instance: Optional["CompoundSession"] = None

    @classmethod
    def instance(cls) -> "CompoundSession":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.records: list[CompoundRecord] = []
        self.active_index: Optional[int] = None
        self.on_record_added: list[Callable] = []
        self.on_record_removed: list[Callable] = []
        self.on_active_changed: list[Callable] = []

    # -- Public API -----------------------------------------------------------

    def add_record(self, record: CompoundRecord) -> int:
        """Append *record* and return its index."""
        # Generate thumbnail if possible
        if record.molecule and hasattr(record.molecule, "smiles") and record.molecule.smiles:
            try:
                from ..chem.conformer_generator import ConformerGenerator
                gen = ConformerGenerator()
                record.thumbnail_svg = gen.smiles_to_2d_svg(record.molecule.smiles, 120, 120)
            except Exception:
                pass

        self.records.append(record)
        idx = len(self.records) - 1
        for cb in self.on_record_added:
            try:
                cb(record)
            except Exception:
                pass
        return idx

    def remove_record(self, index: int):
        if 0 <= index < len(self.records):
            self.records.pop(index)
            # Adjust active_index
            if self.active_index is not None:
                if index == self.active_index:
                    self.active_index = None
                elif index < self.active_index:
                    self.active_index -= 1
            for cb in self.on_record_removed:
                try:
                    cb(index)
                except Exception:
                    pass

    def set_active(self, index: int):
        if 0 <= index < len(self.records):
            self.active_index = index
            record = self.records[index]
            for cb in self.on_active_changed:
                try:
                    cb(record)
                except Exception:
                    pass

    def get_active(self) -> Optional[CompoundRecord]:
        if self.active_index is not None and 0 <= self.active_index < len(self.records):
            return self.records[self.active_index]
        return None

    def get_by_id(self, compound_id: str) -> Optional[CompoundRecord]:
        for r in self.records:
            if r.compound_id == compound_id:
                return r
        return None

    def count(self) -> int:
        return len(self.records)

    def clear(self):
        self.records.clear()
        self.active_index = None

    def get_all_scores(self) -> list[tuple[str, Optional[int]]]:
        return [(r.display_name(), r.overall_score()) for r in self.records]
