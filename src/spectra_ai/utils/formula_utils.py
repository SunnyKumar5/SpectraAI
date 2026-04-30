"""
Molecular formula utilities for SpectraAI.

Provides parsing, validation, and calculation functions for
molecular formulas used across the application.
"""

from __future__ import annotations

import re
from typing import Optional

# Standard atomic weights (IUPAC 2021)
ATOMIC_WEIGHTS = {
    "H": 1.00794, "He": 4.00260, "Li": 6.941, "Be": 9.01218,
    "B": 10.811, "C": 12.0107, "N": 14.0067, "O": 15.9994,
    "F": 18.9984, "Ne": 20.1797, "Na": 22.9898, "Mg": 24.3050,
    "Al": 26.9815, "Si": 28.0855, "P": 30.9738, "S": 32.065,
    "Cl": 35.453, "Ar": 39.948, "K": 39.0983, "Ca": 40.078,
    "Fe": 55.845, "Cu": 63.546, "Zn": 65.38, "Se": 78.971,
    "Br": 79.904, "Pd": 106.42, "I": 126.904, "Ru": 101.07,
    "Rh": 102.906,
}

# Monoisotopic exact masses
EXACT_MASSES = {
    "H": 1.0078250, "C": 12.0000000, "N": 14.0030740, "O": 15.9949146,
    "F": 18.9984032, "Si": 27.9769265, "P": 30.9737620, "S": 31.9720707,
    "Cl": 34.9688527, "Br": 78.9183371, "I": 126.9044719, "Se": 79.9165218,
    "B": 11.0093054, "Na": 22.9897693,
}


def parse_formula(formula: str) -> dict[str, int]:
    """
    Parse a molecular formula string into element counts.

    Args:
        formula: Molecular formula (e.g. "C15H12N2O", "C₁₅H₁₂N₂O")

    Returns:
        Dictionary of element → count (e.g. {"C": 15, "H": 12, "N": 2, "O": 1})
    """
    if not formula:
        return {}

    # Normalize subscript digits to regular digits
    subscript_map = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
    formula = formula.translate(subscript_map)

    # Remove spaces, charges, brackets
    formula = formula.replace(" ", "").replace("+", "").replace("-", "")

    elements = {}
    tokens = re.findall(r"([A-Z][a-z]?)(\d*)", formula)
    for symbol, count_str in tokens:
        if not symbol:
            continue
        count = int(count_str) if count_str else 1
        elements[symbol] = elements.get(symbol, 0) + count

    return elements


def formula_to_dict(formula: str) -> dict[str, int]:
    """Alias for parse_formula."""
    return parse_formula(formula)


def dict_to_formula(elements: dict[str, int]) -> str:
    """
    Convert element count dict to a Hill system formula string.

    Hill system: C first, H second, then alphabetical.
    """
    if not elements:
        return ""

    parts = []
    # C first
    if "C" in elements:
        parts.append(f"C{elements['C']}" if elements["C"] > 1 else "C")
    # H second
    if "H" in elements:
        parts.append(f"H{elements['H']}" if elements["H"] > 1 else "H")
    # Rest alphabetical
    for elem in sorted(elements.keys()):
        if elem in ("C", "H"):
            continue
        count = elements[elem]
        parts.append(f"{elem}{count}" if count > 1 else elem)

    return "".join(parts)


def calculate_mw(formula: str) -> float:
    """
    Calculate molecular weight from formula string.

    Args:
        formula: Molecular formula (e.g. "C15H12N2O")

    Returns:
        Molecular weight in g/mol
    """
    elements = parse_formula(formula)
    mw = 0.0
    for symbol, count in elements.items():
        if symbol in ATOMIC_WEIGHTS:
            mw += ATOMIC_WEIGHTS[symbol] * count
    return round(mw, 4)


def calculate_exact_mass(formula: str) -> float:
    """
    Calculate monoisotopic exact mass from formula string.

    Args:
        formula: Molecular formula

    Returns:
        Monoisotopic exact mass in Da
    """
    elements = parse_formula(formula)
    mass = 0.0
    for symbol, count in elements.items():
        if symbol in EXACT_MASSES:
            mass += EXACT_MASSES[symbol] * count
    return round(mass, 6)


def degree_of_unsaturation(formula: str) -> float:
    """
    Calculate degree of unsaturation (double bond equivalents).

    DoU = (2C + 2 + N - H - X) / 2
    where X = halogens (F, Cl, Br, I)
    """
    elements = parse_formula(formula)
    c = elements.get("C", 0)
    h = elements.get("H", 0)
    n = elements.get("N", 0)
    halogens = (
        elements.get("F", 0) + elements.get("Cl", 0) +
        elements.get("Br", 0) + elements.get("I", 0)
    )
    dou = (2 * c + 2 + n - h - halogens) / 2
    return dou


def validate_formula(formula: str) -> tuple[bool, str]:
    """
    Validate a molecular formula for basic chemical sense.

    Returns:
        (is_valid, message)
    """
    if not formula or not formula.strip():
        return False, "Empty formula"

    elements = parse_formula(formula)
    if not elements:
        return False, "Could not parse formula"

    # Check for unknown elements
    for symbol in elements:
        if symbol not in ATOMIC_WEIGHTS:
            return False, f"Unknown element: {symbol}"

    # Check for negative counts (shouldn't happen but sanity check)
    for symbol, count in elements.items():
        if count <= 0:
            return False, f"Invalid count for {symbol}: {count}"

    # DoU should be non-negative for organic molecules
    dou = degree_of_unsaturation(formula)
    if dou < 0:
        return False, f"Negative degree of unsaturation ({dou}) — check H count"

    return True, "Valid formula"


def compare_formulas(formula1: str, formula2: str) -> bool:
    """Check if two formula strings represent the same composition."""
    return parse_formula(formula1) == parse_formula(formula2)
