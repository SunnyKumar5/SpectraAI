"""
SMILES utility functions for SpectraAI.

Provides molecular property calculations and 2D structure rendering
using RDKit when available, with graceful fallbacks when not installed.
"""

from __future__ import annotations

import io
import re
from typing import Optional

# Try to import RDKit (optional dependency)
_HAS_RDKIT = False
try:
    from rdkit import Chem
    from rdkit.Chem import Draw, Descriptors, rdMolDescriptors, AllChem
    from rdkit.Chem.Draw import rdMolDraw2D
    _HAS_RDKIT = True
except ImportError:
    pass


def has_rdkit() -> bool:
    """Check if RDKit is available."""
    return _HAS_RDKIT


def validate_smiles(smiles: str) -> tuple[bool, str]:
    """
    Validate a SMILES string.

    Returns:
        (is_valid, message)
    """
    if not smiles or not smiles.strip():
        return False, "Empty SMILES"

    if _HAS_RDKIT:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return False, "RDKit could not parse SMILES"
        return True, "Valid SMILES"

    # Basic regex validation without RDKit
    if re.match(r'^[A-Za-z0-9@+\-\[\]\(\)\\/=#%\.:]+$', smiles):
        return True, "SMILES format appears valid (RDKit not available for full validation)"
    return False, "Invalid characters in SMILES"


def smiles_to_formula(smiles: str) -> Optional[str]:
    """Calculate molecular formula from SMILES."""
    if not _HAS_RDKIT:
        return None
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    mol = Chem.AddHs(mol)
    return rdMolDescriptors.CalcMolFormula(mol)


def smiles_to_mw(smiles: str) -> Optional[float]:
    """Calculate molecular weight from SMILES."""
    if not _HAS_RDKIT:
        return None
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return round(Descriptors.MolWt(mol), 4)


def smiles_to_exact_mass(smiles: str) -> Optional[float]:
    """Calculate exact monoisotopic mass from SMILES."""
    if not _HAS_RDKIT:
        return None
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return round(Descriptors.ExactMolWt(mol), 6)


def count_atoms(smiles: str) -> Optional[dict]:
    """
    Count atoms by element in a molecule.

    Returns:
        Dict of element_symbol → count, or None if SMILES invalid
    """
    if not _HAS_RDKIT:
        return None
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    mol = Chem.AddHs(mol)
    counts = {}
    for atom in mol.GetAtoms():
        symbol = atom.GetSymbol()
        counts[symbol] = counts.get(symbol, 0) + 1
    return counts


def count_aromatic_rings(smiles: str) -> Optional[int]:
    """Count the number of aromatic rings."""
    if not _HAS_RDKIT:
        return None
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return rdMolDescriptors.CalcNumAromaticRings(mol)


def get_functional_groups(smiles: str) -> list[str]:
    """
    Identify key functional groups present in the molecule.

    Returns a list of functional group names relevant for IR analysis.
    """
    if not _HAS_RDKIT:
        return []

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return []

    groups = []
    # SMARTS patterns for common functional groups
    patterns = {
        "N-H (primary amine)": "[NH2]",
        "N-H (secondary amine)": "[NH1;!$([NH1]C=O)]",
        "N-H (amide)": "[NH1]C=O",
        "O-H (alcohol)": "[OH1;!$([OH1]C=O)]",
        "O-H (carboxylic acid)": "[OH1]C=O",
        "C=O (ketone)": "[#6]C(=O)[#6;!$([OH])]",
        "C=O (aldehyde)": "[CH1]=O",
        "C=O (ester)": "C(=O)O[#6]",
        "C=O (amide I)": "C(=O)[NH]",
        "C≡N (nitrile)": "C#N",
        "C≡C (terminal alkyne)": "C#[CH]",
        "N=O (nitro asymm)": "[N+](=O)[O-]",
        "C=C (aromatic)": "c1ccccc1",
        "C-F": "[#6]F",
        "C-Cl": "[#6]Cl",
        "C-Br": "[#6]Br",
        "S=O (sulfone)": "S(=O)(=O)",
        "S=O (sulfoxide)": "[S;!$([S](=O)(=O))](=O)",
        "C-O (ether)": "[#6]O[#6;!$([#6]=O)]",
    }

    for name, smarts in patterns.items():
        pattern = Chem.MolFromSmarts(smarts)
        if pattern and mol.HasSubstructMatch(pattern):
            groups.append(name)

    return groups


def render_molecule_svg(smiles: str, width: int = 400, height: int = 300,
                        highlight_atoms: list[int] = None,
                        highlight_color: tuple = None) -> Optional[str]:
    """
    Render a 2D structure as SVG string.

    Args:
        smiles:          SMILES string
        width:           Image width in pixels
        height:          Image height in pixels
        highlight_atoms: List of atom indices to highlight
        highlight_color: RGBA color tuple for highlights

    Returns:
        SVG string, or None if rendering failed
    """
    if not _HAS_RDKIT:
        return None

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None

    # Generate 2D coordinates
    AllChem.Compute2DCoords(mol)

    drawer = rdMolDraw2D.MolDraw2DSVG(width, height)
    drawer.drawOptions().addAtomIndices = False
    drawer.drawOptions().addStereoAnnotation = True

    if highlight_atoms:
        colors = {}
        if highlight_color:
            for idx in highlight_atoms:
                colors[idx] = highlight_color
        drawer.DrawMolecule(mol, highlightAtoms=highlight_atoms,
                            highlightAtomColors=colors if colors else None)
    else:
        drawer.DrawMolecule(mol)

    drawer.FinishDrawing()
    return drawer.GetDrawingText()


def render_molecule_png(smiles: str, width: int = 400, height: int = 300) -> Optional[bytes]:
    """Render a 2D structure as PNG bytes."""
    if not _HAS_RDKIT:
        return None

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None

    AllChem.Compute2DCoords(mol)
    img = Draw.MolToImage(mol, size=(width, height))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def canonical_smiles(smiles: str) -> Optional[str]:
    """Return canonical SMILES representation."""
    if not _HAS_RDKIT:
        return smiles  # return as-is without RDKit
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return Chem.MolToSmiles(mol, canonical=True)
