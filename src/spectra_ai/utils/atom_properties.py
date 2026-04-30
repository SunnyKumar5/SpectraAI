"""
Atom / Element properties for structure rendering and chemical calculations.

Contains colors (CPK scheme), van der Waals radii, covalent radii,
atomic masses, and element symbols.
"""

from typing import Optional


# ── Element data: (symbol, name, atomic_weight, color_rgba, vdw_radius, covalent_radius)
ELEMENT_DATA = {
    1:  ("H",  "Hydrogen",   1.008,   (0.95, 0.95, 0.95, 1.0), 1.20, 0.31),
    5:  ("B",  "Boron",      10.811,  (1.00, 0.71, 0.71, 1.0), 1.92, 0.84),
    6:  ("C",  "Carbon",     12.011,  (0.30, 0.30, 0.30, 1.0), 1.70, 0.76),
    7:  ("N",  "Nitrogen",   14.007,  (0.20, 0.30, 0.90, 1.0), 1.55, 0.71),
    8:  ("O",  "Oxygen",     15.999,  (0.90, 0.15, 0.15, 1.0), 1.52, 0.66),
    9:  ("F",  "Fluorine",   18.998,  (0.56, 0.88, 0.31, 1.0), 1.47, 0.57),
    11: ("Na", "Sodium",     22.990,  (0.67, 0.36, 0.95, 1.0), 2.27, 1.66),
    14: ("Si", "Silicon",    28.086,  (0.94, 0.78, 0.63, 1.0), 2.10, 1.11),
    15: ("P",  "Phosphorus", 30.974,  (1.00, 0.50, 0.00, 1.0), 1.80, 1.07),
    16: ("S",  "Sulfur",     32.065,  (0.90, 0.78, 0.20, 1.0), 1.80, 1.05),
    17: ("Cl", "Chlorine",   35.453,  (0.12, 0.94, 0.12, 1.0), 1.75, 1.02),
    19: ("K",  "Potassium",  39.098,  (0.56, 0.25, 0.83, 1.0), 2.75, 2.03),
    26: ("Fe", "Iron",       55.845,  (0.88, 0.40, 0.20, 1.0), 2.00, 1.32),
    29: ("Cu", "Copper",     63.546,  (0.78, 0.50, 0.20, 1.0), 1.40, 1.32),
    30: ("Zn", "Zinc",       65.380,  (0.49, 0.50, 0.69, 1.0), 1.39, 1.22),
    34: ("Se", "Selenium",   78.971,  (1.00, 0.63, 0.00, 1.0), 1.90, 1.20),
    35: ("Br", "Bromine",    79.904,  (0.65, 0.16, 0.16, 1.0), 1.85, 1.20),
    46: ("Pd", "Palladium",  106.42,  (0.00, 0.41, 0.52, 1.0), 1.63, 1.39),
    53: ("I",  "Iodine",     126.90,  (0.58, 0.00, 0.58, 1.0), 1.98, 1.39),
    44: ("Ru", "Ruthenium",  101.07,  (0.14, 0.56, 0.56, 1.0), 2.00, 1.46),
    45: ("Rh", "Rhodium",    102.91,  (0.04, 0.49, 0.55, 1.0), 2.00, 1.42),
}

# ── Symbol → atomic number lookup ────────────────────────────────────────────
SYMBOL_TO_ATOMIC_NUMBER = {
    data[0]: z for z, data in ELEMENT_DATA.items()
}


def get_atom_symbol(atomic_number: int) -> str:
    """Get element symbol from atomic number."""
    if atomic_number in ELEMENT_DATA:
        return ELEMENT_DATA[atomic_number][0]
    return "?"


def get_atom_name(atomic_number: int) -> str:
    """Get element name from atomic number."""
    if atomic_number in ELEMENT_DATA:
        return ELEMENT_DATA[atomic_number][1]
    return "Unknown"


def get_atom_color(atomic_number: int) -> tuple:
    """Get CPK color (RGBA float tuple) from atomic number."""
    if atomic_number in ELEMENT_DATA:
        return ELEMENT_DATA[atomic_number][3]
    return (0.5, 0.5, 0.5, 1.0)  # default gray


def get_atom_color_hex(atomic_number: int) -> str:
    """Get CPK color as hex string from atomic number."""
    r, g, b, _ = get_atom_color(atomic_number)
    return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"


def get_vdw_radius(atomic_number: int) -> float:
    """Get van der Waals radius in Angstroms."""
    if atomic_number in ELEMENT_DATA:
        return ELEMENT_DATA[atomic_number][4]
    return 1.70  # default


def get_covalent_radius(atomic_number: int) -> float:
    """Get covalent radius in Angstroms."""
    if atomic_number in ELEMENT_DATA:
        return ELEMENT_DATA[atomic_number][5]
    return 0.77  # default


def get_atomic_weight(atomic_number: int) -> float:
    """Get standard atomic weight."""
    if atomic_number in ELEMENT_DATA:
        return ELEMENT_DATA[atomic_number][2]
    return 0.0


def symbol_to_atomic_number(symbol: str) -> Optional[int]:
    """Convert element symbol to atomic number."""
    return SYMBOL_TO_ATOMIC_NUMBER.get(symbol.strip().capitalize())
