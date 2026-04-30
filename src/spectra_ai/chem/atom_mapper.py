"""
AtomMapper — Maps AI NMR peak assignments to 3D atom indices.

Uses RDKit SMARTS matching to correlate AI-generated peak assignments
(e.g. "ArH", "OCH3", "C-5") with specific atom indices in the molecule,
enabling bidirectional atom-peak highlighting.

For 1H NMR, returns the H atom indices (not the parent heavy atom) so the
3D viewer highlights the correct protons.  For 13C, returns carbon indices.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

# RDKit is optional — graceful fallback
try:
    from rdkit import Chem
    _HAS_RDKIT = True
except ImportError:
    _HAS_RDKIT = False


@dataclass
class AtomPeakMapping:
    """A single mapping between an NMR peak and atom indices."""
    shift: float
    assignment: str
    atom_indices: list[int] = field(default_factory=list)
    nucleus: str = "1H"           # "1H" or "13C"
    confidence: str = "medium"    # "high", "medium", "low"
    reasoning: str = ""


class AtomMapper:
    """
    Maps AI NMR peak assignments to atom indices in a molecule.

    Given a SMILES string and a list of AI peak assignment dicts,
    produces AtomPeakMapping objects that link each peak to one or
    more atom indices in the 3D structure.
    """

    # Common assignment patterns -> SMARTS for 1H
    # These match the HEAVY ATOM bearing the proton; _get_attached_hydrogens
    # converts them to the actual H-atom indices for the 3D viewer.
    _H1_SMARTS: dict[str, str] = {
        # Aromatic
        "ArH":         "[c;H1]",
        "Ar-H":        "[c;H1]",
        "aromatic H":  "[c;H1]",
        "aromatic":    "[c;H1]",
        "Ar":          "[c;H1]",
        # Methyl
        "CH3":         "[CH3]",
        "OCH3":        "[CH3][OX2]",
        "O-CH3":       "[CH3][OX2]",
        "OMe":         "[CH3][OX2]",
        "NCH3":        "[CH3][NX3]",
        "N-CH3":       "[CH3][NX3]",
        "NMe":         "[CH3][NX3]",
        "SCH3":        "[CH3][SX2]",
        "SMe":         "[CH3][SX2]",
        "C-CH3":       "[CH3][CX4]",
        "COCH3":       "[CH3][CX3]=O",
        "acetyl":      "[CH3][CX3]=O",
        # Methylene
        "CH2":         "[CH2]",
        "OCH2":        "[CH2][OX2]",
        "NCH2":        "[CH2][NX3]",
        # Methine
        "CH":          "[CH1]",
        "methine":     "[CH1]",
        # N-H
        "NH":          "[NH]",
        "NH2":         "[NH2]",
        "N-H":         "[NH]",
        "amide NH":    "[NX3H1][CX3]=O",
        "amine":       "[NX3;H1,H2]",
        # O-H
        "OH":          "[OH]",
        "O-H":         "[OH]",
        "alcohol":     "[CX4][OH]",
        "phenol":      "[c][OH]",
        "COOH":        "[CX3](=O)[OH]",
        # Aldehyde
        "CHO":         "[CH1]=O",
        "aldehyde":    "[CH1]=O",
        # Amide
        "CONH":        "[CX3](=O)[NH]",
        # Vinyl / olefinic
        "vinyl":       "[CX3H1]=[CX3]",
        "olefinic":    "[CX3;H1,H2]=[CX3]",
        "=CH":         "[CX3H1]=[CX3]",
        "=CH2":        "[CX3H2]=[CX3]",
        # Heterocyclic patterns
        "pyrrole":     "[nH]",
        "indole NH":   "[nH]",
        "imidazole":   "[c;H1]1[n][c][n][c]1",
    }

    # Common assignment patterns -> SMARTS for 13C
    _C13_SMARTS: dict[str, str] = {
        "C=O":         "[CX3]=O",
        "carbonyl":    "[CX3]=O",
        "ketone":      "[CX3](=O)([CX4])[CX4]",
        "C=N":         "[CX3]=[NX2]",
        "imine":       "[CX3]=[NX2]",
        "ArC":         "[c]",
        "aromatic C":  "[c]",
        "aromatic":    "[c]",
        "Ar":          "[c]",
        "CH3":         "[CH3]",
        "methyl":      "[CH3]",
        "CH2":         "[CH2]",
        "methylene":   "[CH2]",
        "CH":          "[CH1]",
        "methine":     "[CH1]",
        "quaternary":  "[CX4;H0]",
        "C-N":         "[CX4][NX3]",
        "C-O":         "[CX4][OX2]",
        "C=C":         "[CX3]=[CX3]",
        "alkene":      "[CX3]=[CX3]",
        "OCH3":        "[CH3][OX2]",
        "NCH3":        "[CH3][NX3]",
        "COOH":        "[CX3](=O)[OX2H1]",
        "carboxyl":    "[CX3](=O)[OX2H1]",
        "COO":         "[CX3](=O)[OX1-,OX2]",
        "ester":       "[CX3](=O)[OX2][CX4]",
        "amide":       "[CX3](=O)[NX3]",
        "nitrile":     "[CX2]#[NX1]",
        "C#N":         "[CX2]#[NX1]",
        "alkyne":      "[CX2]#[CX2]",
        "CF3":         "[CX4](F)(F)F",
    }

    # Chemical shift ranges for fallback mapping (1H NMR)
    _H1_SHIFT_RANGES: list[tuple[float, float, str]] = [
        (9.0, 12.0, "[CH1]=O"),              # aldehyde / formic
        (6.0, 9.0,  "[c;H1]"),               # aromatic / heteroaromatic
        (4.5, 6.5,  "[CX3;H1,H2]=[CX3]"),   # vinyl / olefinic
        (3.2, 4.5,  "[CX4;H1,H2,H3][OX2]"), # C-O (ether, ester, alcohol)
        (2.0, 3.5,  "[CX4;H1,H2,H3][NX3]"), # C-N
        (1.5, 2.5,  "[CX4;H1,H2,H3][CX3]=O"), # alpha to carbonyl
        (0.0, 2.0,  "[CX4;H1,H2,H3]"),      # aliphatic
    ]

    # Chemical shift ranges for fallback mapping (13C NMR)
    _C13_SHIFT_RANGES: list[tuple[float, float, str]] = [
        (190.0, 220.0, "[CX3]=O"),            # carbonyl (ketone, aldehyde)
        (160.0, 185.0, "[CX3](=O)[OX2,NX3]"), # ester, amide, carboxylic
        (110.0, 160.0, "[c]"),                 # aromatic / heteroaromatic
        (100.0, 150.0, "[CX3]=[CX3]"),        # alkene
        (50.0, 90.0,  "[CX4][OX2]"),          # C-O aliphatic
        (30.0, 70.0,  "[CX4][NX3]"),          # C-N aliphatic
        (0.0, 50.0,   "[CX4;H1,H2,H3]"),     # aliphatic CH
    ]

    def __init__(self, smiles: str):
        self._smiles = smiles
        self._mol = None
        self._used_indices: set[int] = set()  # track assigned atoms
        if _HAS_RDKIT and smiles:
            self._mol = Chem.MolFromSmiles(smiles)
            if self._mol is not None:
                self._mol = Chem.AddHs(self._mol)

    @property
    def is_valid(self) -> bool:
        return self._mol is not None

    def map_h1_peaks(self, ai_peaks: list[dict]) -> list[AtomPeakMapping]:
        """Map 1H NMR AI peak assignments to atom indices."""
        return self._map_peaks(ai_peaks, nucleus="1H")

    def map_c13_peaks(self, ai_peaks: list[dict]) -> list[AtomPeakMapping]:
        """Map 13C NMR AI peak assignments to atom indices."""
        return self._map_peaks(ai_peaks, nucleus="13C")

    def _map_peaks(self, ai_peaks: list[dict], nucleus: str) -> list[AtomPeakMapping]:
        self._used_indices = set()  # reset for each mapping run
        mappings = []
        for peak in ai_peaks:
            shift = peak.get("shift", 0.0)
            assignment = peak.get("assignment", "")
            confidence = peak.get("confidence", "medium")
            reasoning = peak.get("reasoning", "")

            indices = self._resolve_assignment(assignment, nucleus, shift)

            # Mark primary atoms as used so next peak with same
            # pattern maps to a different atom group
            for idx in indices:
                self._used_indices.add(idx)

            mappings.append(AtomPeakMapping(
                shift=shift,
                assignment=assignment,
                atom_indices=indices,
                nucleus=nucleus,
                confidence=confidence,
                reasoning=reasoning,
            ))
        return mappings

    def _resolve_assignment(self, assignment: str, nucleus: str,
                            shift: float = 0.0) -> list[int]:
        """Resolve an assignment string to atom indices via SMARTS matching."""
        if not self._mol:
            return []

        # 1) Try numbered atom label (e.g. "C-5", "H-3", "C5")
        if assignment:
            indices = self._try_numbered_label(assignment, nucleus)
            if indices:
                return indices

        # 2) Try SMARTS dictionary lookup
        if assignment:
            smarts_dict = self._H1_SMARTS if nucleus == "1H" else self._C13_SMARTS
            indices = self._try_smarts_lookup(assignment, smarts_dict)
            if indices:
                if nucleus == "1H":
                    return self._heavy_to_hydrogen_indices(indices)
                return indices

        # 3) Try direct SMARTS if assignment looks like one
        if assignment and any(c in assignment for c in "[]()=#"):
            indices = self._match_smarts(assignment)
            if indices:
                if nucleus == "1H":
                    return self._heavy_to_hydrogen_indices(indices)
                return indices

        # 4) Chemical shift range fallback
        indices = self._shift_range_fallback(shift, nucleus)
        if indices:
            return indices

        return []

    def _try_numbered_label(self, assignment: str, nucleus: str) -> list[int]:
        """Parse assignments like 'C-5', 'H-3', 'C5' to atom indices."""
        if not self._mol:
            return []
        m = re.match(r"[A-Z][a-z]?\s*[-_]?\s*(\d+)", assignment.strip())
        if m:
            idx = int(m.group(1))
            # Atom index in NMR labels is often 1-based
            zero_idx = idx - 1
            if 0 <= zero_idx < self._mol.GetNumAtoms():
                atom = self._mol.GetAtomWithIdx(zero_idx)
                if nucleus == "1H" and atom.GetAtomicNum() != 1:
                    # For 1H, if numbered label points to heavy atom,
                    # return its attached H atoms
                    return self._get_attached_hydrogens([zero_idx])
                return [zero_idx]
        return []

    def _try_smarts_lookup(self, assignment: str, smarts_dict: dict) -> list[int]:
        """Try matching assignment against known SMARTS patterns.

        Returns indices from a SINGLE match group (not all matches)
        to avoid mapping every peak with the same label to every atom.
        """
        assignment_lower = assignment.lower().strip()
        for key, smarts in smarts_dict.items():
            if key.lower() in assignment_lower or assignment_lower in key.lower():
                indices = self._match_smarts_single(smarts)
                if indices:
                    return indices
        return []

    def _match_smarts_single(self, smarts: str) -> list[int]:
        """Run SMARTS match and return the first UNASSIGNED match group.

        Skips match groups whose primary atom is already used by a
        previous peak, so multiple peaks with the same label (e.g.
        several "ArH" peaks) map to distinct atoms.
        """
        if not self._mol:
            return []
        try:
            pattern = Chem.MolFromSmarts(smarts)
            if pattern is None:
                return []
            matches = self._mol.GetSubstructMatches(pattern)
            if not matches:
                return []
            # Pick the first match whose primary atom is unassigned
            for match in matches:
                if match[0] not in self._used_indices:
                    return list(match)
            # All primary atoms used — fall back to first match
            return list(matches[0])
        except Exception:
            return []

    def _match_smarts(self, smarts: str) -> list[int]:
        """Run SMARTS match and return all matching atom indices."""
        if not self._mol:
            return []
        try:
            pattern = Chem.MolFromSmarts(smarts)
            if pattern is None:
                return []
            matches = self._mol.GetSubstructMatches(pattern)
            # Flatten to unique indices
            indices = []
            seen = set()
            for match in matches:
                for idx in match:
                    if idx not in seen:
                        seen.add(idx)
                        indices.append(idx)
            return indices
        except Exception:
            return []

    def _heavy_to_hydrogen_indices(self, heavy_indices: list[int]) -> list[int]:
        """
        Convert heavy atom indices to their attached hydrogen indices.

        For 1H NMR, we want to highlight the H atoms in the 3D viewer,
        not the C/N/O atoms that the SMARTS matched.
        Returns both the H atoms AND the parent heavy atoms for visual clarity.
        """
        if not self._mol:
            return heavy_indices
        result_h = []
        result_heavy = []
        seen = set()
        for idx in heavy_indices:
            atom = self._mol.GetAtomWithIdx(idx)
            if atom.GetAtomicNum() == 1:
                # Already an H atom
                if idx not in seen:
                    seen.add(idx)
                    result_h.append(idx)
                continue
            # Heavy atom — find its H neighbors
            result_heavy.append(idx)
            for neighbor in atom.GetNeighbors():
                if neighbor.GetAtomicNum() == 1:
                    nidx = neighbor.GetIdx()
                    if nidx not in seen:
                        seen.add(nidx)
                        result_h.append(nidx)
        # Return H atoms first (primary), then heavy atoms (context)
        return result_h + result_heavy if result_h else heavy_indices

    def _get_attached_hydrogens(self, heavy_indices: list[int]) -> list[int]:
        """Get H atom indices attached to the given heavy atoms."""
        if not self._mol:
            return heavy_indices
        h_indices = []
        seen = set()
        for idx in heavy_indices:
            atom = self._mol.GetAtomWithIdx(idx)
            for neighbor in atom.GetNeighbors():
                if neighbor.GetAtomicNum() == 1:
                    nidx = neighbor.GetIdx()
                    if nidx not in seen:
                        seen.add(nidx)
                        h_indices.append(nidx)
        # If no H atoms found, return the heavy atoms themselves
        return h_indices + heavy_indices if h_indices else heavy_indices

    def _shift_range_fallback(self, shift: float, nucleus: str) -> list[int]:
        """
        Fallback: use chemical shift range to guess the atom type.

        When SMARTS dictionary lookup fails, use the shift value to determine
        what kind of atom environment this peak likely represents.
        """
        if not self._mol or shift == 0.0:
            return []

        ranges = self._H1_SHIFT_RANGES if nucleus == "1H" else self._C13_SHIFT_RANGES

        for low, high, smarts in ranges:
            if low <= shift <= high:
                indices = self._match_smarts(smarts)
                if indices:
                    if nucleus == "1H":
                        return self._heavy_to_hydrogen_indices(indices)
                    return indices

        return []

    def get_atoms_for_shift(self, shift: float, mappings: list[AtomPeakMapping],
                            tolerance: float = 0.3) -> list[int]:
        """Find atom indices for a given chemical shift from existing mappings."""
        for m in mappings:
            if abs(m.shift - shift) <= tolerance:
                return m.atom_indices
        return []

    def get_peaks_for_atom(self, atom_idx: int,
                           mappings: list[AtomPeakMapping]) -> list[AtomPeakMapping]:
        """Find all peaks mapped to a given atom index."""
        return [m for m in mappings if atom_idx in m.atom_indices]

    def get_element(self, atom_idx: int) -> str:
        """Get element symbol for an atom index."""
        if not self._mol:
            return "?"
        try:
            return self._mol.GetAtomWithIdx(atom_idx).GetSymbol()
        except Exception:
            return "?"

    # -- IR -> Bond mapping --------------------------------------------------------

    # SMARTS for functional groups that correspond to IR absorption ranges
    _IR_BOND_SMARTS: dict[str, list[tuple[float, float, str]]] = {
        "[OX2H]":               [(3200, 3550, "O-H stretch")],
        "[NX3H2]":              [(3300, 3500, "N-H stretch")],
        "[NX3H1]":              [(3300, 3500, "N-H stretch")],
        "[nH]":                 [(3300, 3500, "N-H stretch (heterocyclic)")],
        "[CX4H3]":              [(2850, 3000, "C-H sp3 stretch")],
        "[CX4H2]":              [(2850, 3000, "C-H sp3 stretch")],
        "[CX4H1]":              [(2850, 3000, "C-H sp3 stretch")],
        "[cH1]":                [(3000, 3100, "C-H aromatic stretch")],
        "[CX3H1]=[CX3]":       [(3000, 3100, "C-H sp2 stretch")],
        "[CX2H1]#[CX2]":       [(3200, 3340, "C-H sp stretch")],
        "[CX2]#[NX1]":         [(2200, 2260, "C≡N stretch")],
        "[CX2]#[CX2]":         [(2100, 2260, "C≡C stretch")],
        "[CX3](=O)[OX2H1]":   [(1700, 1725, "C=O carboxylic")],
        "[CX3H1]=O":           [(1720, 1740, "C=O aldehyde")],
        "[CX3](=O)[OX2][CX4]": [(1735, 1750, "C=O ester")],
        "[CX3](=O)[NX3]":     [(1630, 1690, "C=O amide")],
        "[CX3](=O)[CX4]":     [(1700, 1725, "C=O ketone")],
        "[cX3]:[cX3]":        [(1450, 1600, "C=C aromatic")],
        "[CX3]=[CX3]":        [(1600, 1680, "C=C alkene")],
        "[CX3]=[NX2]":        [(1600, 1680, "C=N stretch")],
        "[NX3+](=O)[O-]":     [(1515, 1560, "N=O nitro (asym)"),
                                (1320, 1380, "N=O nitro (sym)")],
        "[SX4](=O)(=O)":      [(1120, 1160, "S=O sulfone (asym)"),
                                (1290, 1350, "S=O sulfone (sym)")],
        "[SX3](=O)":          [(1030, 1070, "S=O sulfoxide")],
        "[CX4][OX2][CX4]":    [(1000, 1300, "C-O-C ether")],
        "[CX4][F]":           [(1000, 1400, "C-F stretch")],
        "[CX4][Cl]":          [(550, 850, "C-Cl stretch")],
        "[CX4][Br]":          [(500, 680, "C-Br stretch")],
    }

    def map_ir_to_bonds(self, wavenumber: float,
                        tolerance: float = 50.0) -> list[tuple[int, int]]:
        """
        Map an IR wavenumber to bond atom-pairs in the molecule.

        Returns list of (atom_idx1, atom_idx2) pairs for bonds that
        match the functional group corresponding to that wavenumber.
        """
        if not self._mol:
            return []

        bond_pairs = []
        for smarts, ranges in self._IR_BOND_SMARTS.items():
            for low, high, _desc in ranges:
                if low - tolerance <= wavenumber <= high + tolerance:
                    matches = self._match_smarts_pairs(smarts)
                    bond_pairs.extend(matches)

        # Deduplicate
        seen = set()
        unique = []
        for pair in bond_pairs:
            key = (min(pair), max(pair))
            if key not in seen:
                seen.add(key)
                unique.append(pair)
        return unique

    def _match_smarts_pairs(self, smarts: str) -> list[tuple[int, int]]:
        """Match SMARTS and return bonded atom pairs from the match."""
        if not self._mol:
            return []
        try:
            pattern = Chem.MolFromSmarts(smarts)
            if pattern is None:
                return []
            matches = self._mol.GetSubstructMatches(pattern)
            pairs = []
            for match in matches:
                # Return consecutive atom pairs in the match as bonds
                for i in range(len(match) - 1):
                    a1, a2 = match[i], match[i + 1]
                    bond = self._mol.GetBondBetweenAtoms(a1, a2)
                    if bond is not None:
                        pairs.append((a1, a2))
            return pairs
        except Exception:
            return []

    def get_ir_group_name(self, wavenumber: float,
                          tolerance: float = 50.0) -> str:
        """Return a human-readable functional group name for a wavenumber."""
        for _smarts, ranges in self._IR_BOND_SMARTS.items():
            for low, high, desc in ranges:
                if low - tolerance <= wavenumber <= high + tolerance:
                    return desc
        return ""
