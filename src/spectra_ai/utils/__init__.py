"""
Utility functions and reference data for SpectraAI.
"""

from .atom_properties import ELEMENT_DATA, get_atom_color, get_atom_symbol
from .nmr_reference import NMR_REFERENCE_RANGES, get_scaffold_references
from .formula_utils import parse_formula, formula_to_dict, calculate_mw

__all__ = [
    "ELEMENT_DATA", "get_atom_color", "get_atom_symbol",
    "NMR_REFERENCE_RANGES", "get_scaffold_references",
    "parse_formula", "formula_to_dict", "calculate_mw",
]
