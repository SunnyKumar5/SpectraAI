"""
IR (Infrared) reference data for functional group identification.

Contains reference absorption ranges, diagnostic patterns, and
tools for matching observed IR bands to expected functional groups.
"""

from __future__ import annotations

from typing import Optional


# ── Comprehensive IR reference database ───────────────────────────────────────
# Format: (min_cm, max_cm, intensity, description)
IR_REFERENCE = {
    # X-H Stretching Region (4000-2500 cm⁻¹)
    "O-H (free alcohol)": (3580, 3650, "sharp, medium", "Free O-H stretch; no H-bonding"),
    "O-H (H-bonded alcohol)": (3200, 3550, "broad, strong", "Hydrogen-bonded O-H; broad band"),
    "O-H (carboxylic acid)": (2500, 3300, "very broad, strong", "Carboxylic acid O-H; extremely broad"),
    "N-H (primary amine)": (3350, 3500, "medium, two bands", "Two bands for NH₂ (symmetric + asymmetric)"),
    "N-H (secondary amine)": (3310, 3350, "medium, one band", "Single band for N-H"),
    "N-H (amide)": (3100, 3500, "strong", "Amide N-H; position depends on type"),
    "=C-H (aromatic)": (3000, 3100, "medium", "Aromatic C-H stretch"),
    "=C-H (vinyl)": (3010, 3095, "medium", "Vinyl C-H stretch"),
    "C-H (sp3)": (2850, 3000, "strong", "Alkane C-H stretches"),
    "≡C-H (alkyne)": (3260, 3330, "strong, sharp", "Terminal alkyne C-H"),
    "C-H (aldehyde)": (2700, 2850, "medium, two bands", "Aldehyde C-H; Fermi resonance doublet"),

    # Triple Bond / Cumulated Double Bond Region (2500-2000 cm⁻¹)
    "C≡N (nitrile)": (2200, 2260, "medium-strong, sharp", "Nitrile stretch; very diagnostic"),
    "C≡C (terminal alkyne)": (2100, 2140, "weak-medium", "Terminal alkyne stretch"),
    "C≡C (internal alkyne)": (2190, 2260, "weak", "Internal alkyne; may be absent if symmetric"),
    "N=C=O (isocyanate)": (2250, 2275, "strong", "Isocyanate asymmetric stretch"),
    "N=C=S (isothiocyanate)": (2050, 2100, "strong", "Isothiocyanate stretch"),
    "N₃ (azide)": (2080, 2160, "strong, two bands", "Azide asymmetric stretch"),

    # Double Bond Region (2000-1500 cm⁻¹)
    "C=O (ketone)": (1700, 1725, "strong", "Ketone carbonyl stretch"),
    "C=O (aldehyde)": (1720, 1740, "strong", "Aldehyde carbonyl stretch"),
    "C=O (carboxylic acid)": (1700, 1725, "strong", "Carboxylic acid C=O"),
    "C=O (ester)": (1735, 1750, "strong", "Ester carbonyl stretch"),
    "C=O (anhydride)": (1800, 1850, "strong, two bands", "Anhydride C=O; two bands"),
    "C=O (amide I)": (1630, 1690, "strong", "Amide I band (C=O stretch)"),
    "C=O (lactone)": (1735, 1780, "strong", "Lactone carbonyl"),
    "C=C (alkene)": (1620, 1680, "medium", "Alkene C=C stretch"),
    "C=C (aromatic)": (1450, 1600, "medium, multiple", "Aromatic ring stretches; typically 2-4 bands"),
    "C=N": (1600, 1680, "medium-strong", "Imine / C=N stretch"),
    "N-H (amide II)": (1510, 1570, "strong", "Amide II band (N-H bend + C-N stretch)"),
    "N=O (nitro asymm)": (1515, 1560, "strong", "Nitro asymmetric stretch"),
    "N=O (nitro symm)": (1340, 1380, "strong", "Nitro symmetric stretch"),

    # Fingerprint Region (1500-400 cm⁻¹)
    "C-O (ether)": (1000, 1300, "strong", "C-O-C stretch; position varies with ether type"),
    "C-O (ester, two bands)": (1150, 1300, "strong", "Ester C-O stretch"),
    "C-O (alcohol)": (1000, 1150, "strong", "Alcohol C-O stretch"),
    "C-N (amine)": (1020, 1250, "medium", "C-N stretch"),
    "C-F": (1000, 1400, "strong", "C-F stretch"),
    "C-Cl": (550, 850, "strong", "C-Cl stretch"),
    "C-Br": (500, 680, "strong", "C-Br stretch"),
    "C-I": (485, 600, "strong", "C-I stretch"),
    "S=O (sulfone)": (1120, 1160, "strong", "Sulfone S=O stretch"),
    "S=O (sulfoxide)": (1030, 1070, "strong", "Sulfoxide S=O stretch"),
    "P=O": (1100, 1250, "strong", "Phosphoryl stretch"),
}


def find_matching_groups(wavenumber: float, tolerance: float = 30.0) -> list[tuple[str, str]]:
    """
    Find functional groups that match a given wavenumber.

    Args:
        wavenumber: Observed absorption in cm⁻¹
        tolerance: Matching tolerance in cm⁻¹

    Returns:
        List of (group_name, description) tuples
    """
    matches = []
    for group, (low, high, intensity, desc) in IR_REFERENCE.items():
        if (low - tolerance) <= wavenumber <= (high + tolerance):
            matches.append((group, f"{desc} ({intensity})"))
    return matches


def get_expected_ir_for_smiles_features(functional_groups: list[str]) -> list[dict]:
    """
    Given a list of functional group names present in a molecule,
    return expected IR absorption bands.

    Args:
        functional_groups: List of group names (e.g. ["C=O (amide I)", "N-H (amide)"])

    Returns:
        List of dicts with expected band info
    """
    expected = []
    for group in functional_groups:
        if group in IR_REFERENCE:
            low, high, intensity, desc = IR_REFERENCE[group]
            expected.append({
                "group": group,
                "range": (low, high),
                "midpoint": (low + high) / 2,
                "intensity": intensity,
                "description": desc,
            })
    return expected
