"""
NMR Reference Ranges for Heterocyclic Scaffold Families.

Contains typical ¹H and ¹³C chemical shift ranges for diagnostic
positions in common heterocyclic scaffolds, sourced from published
literature and reference databases.

This is the core domain knowledge that enables scaffold-constrained
interpretation and prediction — a key novelty of SpectraAI.
"""

from typing import Optional


# ──────────────────────────────────────────────────────────────────────────────
# ¹H NMR reference ranges: {position: (min_ppm, max_ppm, typical_mult, notes)}
# ¹³C NMR reference ranges: {position: (min_ppm, max_ppm, notes)}
# ──────────────────────────────────────────────────────────────────────────────

NMR_REFERENCE_RANGES = {
    "imidazopyridine": {
        "name": "Imidazo[1,2-a]pyridine",
        "core_formula": "C7H6N2",
        "numbering_note": "Bridgehead N at 4-position; C-2, C-3 on imidazole ring; C-5 to C-8 on pyridine ring",
        "h1": {
            "H-3": (7.40, 8.60, "s or d", "Diagnostic singlet when C-3 unsubstituted; shifts downfield with EWG at C-2"),
            "H-5": (7.50, 8.60, "d, J~6-7 Hz", "Most downfield pyridine proton; peri to bridgehead N"),
            "H-6": (6.70, 7.30, "t or td", "Middle of pyridine ring"),
            "H-7": (7.00, 7.50, "t or td", "Middle of pyridine ring"),
            "H-8": (7.40, 8.20, "d, J~6-7 Hz", "Adjacent to bridgehead N"),
            "H-2": (7.80, 8.50, "s", "When C-3 substituted, H-2 appears as singlet"),
        },
        "c13": {
            "C-2": (141.0, 150.0, "Often most downfield aromatic C if unsubstituted"),
            "C-3": (108.0, 135.0, "Varies widely with substitution"),
            "C-5": (112.0, 128.0, "Pyridine ring carbon"),
            "C-6": (116.0, 128.0, "Pyridine ring carbon"),
            "C-7": (124.0, 132.0, "Pyridine ring carbon"),
            "C-8": (112.0, 118.0, "Adjacent to bridgehead N"),
            "C-8a": (143.0, 150.0, "Bridgehead carbon, quaternary"),
        },
        "diagnostic_features": [
            "H-3 singlet at δ 7.4-8.6 is the most diagnostic signal",
            "C-8a (bridgehead) typically appears at δ 143-150",
            "Two nitrogen atoms create characteristic deshielding pattern",
        ],
    },

    "indole": {
        "name": "Indole",
        "core_formula": "C8H7N",
        "numbering_note": "N-1, C-2, C-3 on pyrrole ring; C-4 to C-7 on benzene ring",
        "h1": {
            "N-H": (7.80, 10.50, "br s", "Exchangeable; position depends heavily on solvent. Absent in N-substituted indoles"),
            "H-2": (6.40, 7.50, "d or s", "Characteristic; shifts with C-3 substitution"),
            "H-3": (6.40, 7.80, "d or s", "Shifts significantly with substitution pattern"),
            "H-4": (7.30, 7.80, "d, J~7-8 Hz", "Peri to nitrogen"),
            "H-5": (7.00, 7.30, "td", "Middle of benzo ring"),
            "H-6": (7.05, 7.35, "td", "Middle of benzo ring"),
            "H-7": (7.20, 7.60, "d, J~7-8 Hz", "Adjacent to nitrogen"),
        },
        "c13": {
            "C-2": (121.0, 142.0, "Wide range depending on substitution"),
            "C-3": (102.0, 120.0, "Diagnostic for 3-substituted indoles"),
            "C-3a": (127.0, 132.0, "Ring junction, quaternary"),
            "C-4": (119.0, 122.0, "Benzo ring"),
            "C-5": (119.0, 123.0, "Benzo ring"),
            "C-6": (120.0, 124.0, "Benzo ring"),
            "C-7": (110.0, 115.0, "Adjacent to N"),
            "C-7a": (135.0, 140.0, "Ring junction, quaternary"),
        },
        "diagnostic_features": [
            "N-H broad singlet at δ 7.8-10.5 (absent in N-substituted)",
            "H-2/H-3 coupling pattern diagnostic for substitution",
            "Four characteristic aromatic protons in benzo ring",
        ],
    },

    "quinazoline": {
        "name": "Quinazoline / Quinazolinone",
        "core_formula": "C8H6N2",
        "numbering_note": "N-1, C-2, N-3, C-4 in diazine ring; C-5 to C-8 in benzo ring",
        "h1": {
            "H-2": (8.80, 9.50, "s", "Most downfield; between two nitrogens"),
            "H-4": (8.20, 9.00, "s", "Downfield singlet in quinazolines"),
            "H-5": (7.40, 8.30, "d or dd", "Benzo ring, peri to C-4"),
            "H-6": (7.30, 7.80, "td", "Benzo ring"),
            "H-7": (7.50, 7.90, "td", "Benzo ring"),
            "H-8": (7.60, 8.20, "dd", "Benzo ring, peri to N-1"),
            "NH (amide)": (8.00, 12.00, "br s", "In quinazolinones; N-3-H or N-1-H"),
        },
        "c13": {
            "C-2": (148.0, 165.0, "Highly deshielded; between two N atoms"),
            "C-4": (155.0, 168.0, "C=O in quinazolinones, or C=N"),
            "C-4a": (120.0, 128.0, "Ring junction"),
            "C-8a": (145.0, 155.0, "Ring junction, next to N-1"),
        },
        "diagnostic_features": [
            "H-2 singlet at δ 8.8-9.5 is highly diagnostic",
            "C-2 and C-4 are the most deshielded carbons",
            "In quinazolinones, C-4 carbonyl appears at δ 160-168",
        ],
    },

    "triazole": {
        "name": "1,2,3-Triazole",
        "core_formula": "C2H3N3",
        "numbering_note": "1,4-disubstituted triazoles from CuAAC (click chemistry)",
        "h1": {
            "H-5 (triazole)": (7.40, 8.50, "s", "Diagnostic singlet for 1,4-disubstituted triazole"),
            "N-CH₂": (4.20, 5.60, "s or d", "Methylene adjacent to N-1; varies with substituent"),
        },
        "c13": {
            "C-4": (143.0, 150.0, "Quaternary in 1,4-disubstituted"),
            "C-5": (119.0, 128.0, "C-H carbon of triazole ring"),
        },
        "diagnostic_features": [
            "Triazole C-H singlet at δ 7.4-8.5 is the key diagnostic",
            "1,4-regioisomer (from CuAAC) vs 1,5-regioisomer have distinct shifts",
            "N-CH₂ typically at δ 4.2-5.6",
        ],
    },

    "pyrazolopyrimidine": {
        "name": "Pyrazolo[1,5-a]pyrimidine / Pyrazolo[3,4-d]pyrimidine",
        "core_formula": "C5H4N4",
        "h1": {
            "H-3 (pyrazole)": (6.50, 8.20, "s or d", "Pyrazole ring proton"),
            "H-5": (7.80, 8.80, "s or d", "Pyrimidine ring"),
            "H-7": (8.20, 9.00, "s or d", "Pyrimidine ring, most downfield"),
        },
        "c13": {
            "C-3": (95.0, 110.0, "Pyrazole carbon"),
            "C-5": (145.0, 158.0, "Pyrimidine carbon"),
            "C-7": (148.0, 158.0, "Pyrimidine carbon, near N"),
        },
        "diagnostic_features": [
            "Pyrazole H-3 at δ 6.5-8.2",
            "Two pyrimidine protons typically appear as singlets",
        ],
    },

    "coumarin": {
        "name": "Coumarin / Coumestan",
        "core_formula": "C9H6O2",
        "h1": {
            "H-3": (6.20, 6.50, "d, J~9-10 Hz", "Vinyl proton cis to C=O; large J with H-4"),
            "H-4": (7.50, 8.00, "d, J~9-10 Hz", "Vinyl proton; large J with H-3"),
            "H-5": (7.20, 7.60, "dd", "Aromatic ring"),
            "H-6": (7.15, 7.40, "td", "Aromatic ring"),
            "H-7": (7.30, 7.60, "td", "Aromatic ring"),
            "H-8": (7.00, 7.40, "dd", "Aromatic ring"),
        },
        "c13": {
            "C-2 (C=O)": (158.0, 164.0, "Lactone carbonyl"),
            "C-3": (113.0, 120.0, "Vinyl carbon adjacent to C=O"),
            "C-4": (140.0, 148.0, "Vinyl carbon"),
            "C-8a": (152.0, 158.0, "Aromatic carbon bearing O"),
        },
        "diagnostic_features": [
            "H-3/H-4 doublet pair with J ~9-10 Hz is highly diagnostic",
            "Lactone C=O at δ 158-164 in ¹³C",
            "Distinct from chromanone pattern",
        ],
    },
}


# ── Common substituent chemical shift contributions ──────────────────────────
SUBSTITUENT_SHIFTS = {
    "h1": {
        "OCH₃": (3.70, 4.00, "s, 3H", "Methoxy singlet"),
        "N-CH₃": (3.20, 3.80, "s, 3H", "N-methyl singlet"),
        "CH₃ (aromatic)": (2.20, 2.50, "s, 3H", "Aromatic methyl"),
        "CH₃ (aliphatic)": (0.80, 1.20, "s or t, 3H", "Aliphatic methyl"),
        "OCH₂CH₃": (1.30, 1.45, "t, 3H; 4.00-4.20, q, 2H", "Ethoxy group"),
        "CHO": (9.70, 10.10, "s, 1H", "Aldehyde proton"),
        "OH (phenol)": (5.00, 12.00, "br s, 1H", "Phenolic OH, very variable"),
        "NH₂": (3.50, 5.50, "br s, 2H", "Primary amine, broad"),
        "NHCO": (7.50, 10.00, "br s, 1H", "Amide NH"),
        "CF₃": (None, None, None, "No ¹H signal; ¹⁹F NMR diagnostic"),
    },
    "c13": {
        "OCH₃": (55.0, 56.5, "Methoxy carbon"),
        "N-CH₃": (28.0, 38.0, "N-methyl carbon; varies with ring type"),
        "CH₃ (aromatic)": (18.0, 22.0, "Aromatic methyl carbon"),
        "C=O (ketone)": (190.0, 210.0, "Ketone carbonyl"),
        "C=O (amide)": (165.0, 175.0, "Amide carbonyl"),
        "C=O (ester)": (170.0, 175.0, "Ester carbonyl"),
        "CHO": (190.0, 205.0, "Aldehyde carbon"),
        "CN": (115.0, 120.0, "Nitrile carbon"),
    },
}


# ── Aromatic substitution pattern recognition ────────────────────────────────
AROMATIC_PATTERNS = {
    "monosubstituted": {
        "h_count": 5,
        "pattern": "2H + 1H + 2H or 2H + 3H multiplet",
        "j_values": "J_ortho ~7-8 Hz, J_meta ~1-3 Hz",
    },
    "para-disubstituted": {
        "h_count": 4,
        "pattern": "Two doublets, 2H each, J ~8-9 Hz",
        "j_values": "J_ortho ~8-9 Hz",
    },
    "ortho-disubstituted": {
        "h_count": 4,
        "pattern": "Complex multiplet region",
        "j_values": "J_ortho ~7-8 Hz",
    },
    "meta-disubstituted": {
        "h_count": 4,
        "pattern": "Singlet + doublet + triplet + doublet",
        "j_values": "J_ortho ~7-8 Hz, J_meta ~1-3 Hz",
    },
    "1,2,4-trisubstituted": {
        "h_count": 3,
        "pattern": "dd + d + d",
        "j_values": "J_ortho ~8 Hz, J_meta ~2 Hz",
    },
    "1,3,5-trisubstituted": {
        "h_count": 3,
        "pattern": "Three equivalent singlets or one singlet (3H)",
        "j_values": "No ortho coupling",
    },
}


def get_scaffold_references(scaffold_family: str) -> Optional[dict]:
    """
    Get NMR reference data for a specific scaffold family.

    Args:
        scaffold_family: Scaffold family key (e.g. "imidazopyridine")

    Returns:
        Dictionary with h1, c13 reference ranges and diagnostic features,
        or None if scaffold not found.
    """
    return NMR_REFERENCE_RANGES.get(scaffold_family)


def get_all_scaffold_names() -> list[str]:
    """Return list of all available scaffold family keys."""
    return list(NMR_REFERENCE_RANGES.keys())


def get_scaffold_display_names() -> dict[str, str]:
    """Return mapping of scaffold key → display name."""
    return {
        key: data["name"]
        for key, data in NMR_REFERENCE_RANGES.items()
    }
