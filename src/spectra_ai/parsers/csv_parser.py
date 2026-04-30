"""
CSV / Excel Parser for SpectraAI.

Parses peak lists and compound data from CSV/TSV files
for batch processing and data import.
"""

from __future__ import annotations

import csv
import json
import os
from typing import Optional

from ..core.molecule import Molecule, MoleculeMetadata
from ..core.nmr_data import NMRData, NMRPeak
from .nmr_text_parser import parse_h1_nmr_text, parse_c13_nmr_text
from .ir_parser import parse_ir_text
from .ms_parser import parse_ms_text


def parse_compound_csv(filepath: str) -> list[Molecule]:
    """
    Parse a CSV file containing compound data into Molecule objects.

    Expected columns (flexible naming):
        name, smiles, formula, scaffold,
        h1_nmr, c13_nmr, ir, hrms,
        mp_low, mp_high, solvent, source

    Args:
        filepath: Path to CSV file

    Returns:
        List of Molecule objects
    """
    molecules = []
    ext = os.path.splitext(filepath)[1].lower()

    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        for i, row in enumerate(reader):
            # Normalize column names
            row = {k.strip().lower().replace(" ", "_"): v.strip() for k, v in row.items()}

            mol = Molecule(
                compound_id=row.get("id", row.get("compound_id", f"CSV-{i+1:03d}")),
                name=row.get("name", row.get("compound_name", "")),
                smiles=row.get("smiles", ""),
                formula=row.get("formula", row.get("molecular_formula", "")),
                metadata=MoleculeMetadata(
                    scaffold_family=row.get("scaffold", row.get("scaffold_family", "other")),
                    source_paper=row.get("source", row.get("source_paper", "")),
                    solvent_media=row.get("media", row.get("solvent_media", "")),
                ),
            )

            # Parse spectral data if present
            h1_text = row.get("h1_nmr", row.get("h1", ""))
            if h1_text:
                nmr = parse_h1_nmr_text(h1_text)
                mol._h1_nmr = nmr.to_dict()

            c13_text = row.get("c13_nmr", row.get("c13", ""))
            if c13_text:
                nmr = parse_c13_nmr_text(c13_text)
                mol._c13_nmr = nmr.to_dict()

            ir_text = row.get("ir", "")
            if ir_text:
                ir = parse_ir_text(ir_text)
                mol._ir = ir.to_dict()

            hrms_text = row.get("hrms", row.get("ms", ""))
            if hrms_text:
                ms = parse_ms_text(hrms_text)
                mol._hrms = ms.to_dict()

            # Melting point
            mp_low = row.get("mp_low", row.get("mp", ""))
            mp_high = row.get("mp_high", "")
            if mp_low:
                try:
                    low = float(mp_low)
                    high = float(mp_high) if mp_high else low
                    mol.melting_point = (low, high)
                except ValueError:
                    pass

            # Calculate MW if formula is present
            if mol.formula:
                mol.calculate_molecular_weight()

            molecules.append(mol)

    return molecules


def parse_peak_list_csv(filepath: str, nucleus: str = "1H") -> NMRData:
    """
    Parse a CSV file containing a peak list.

    Expected columns: shift (or chemical_shift, ppm), multiplicity, J, integration, assignment

    Args:
        filepath: Path to CSV file
        nucleus: "1H" or "13C"

    Returns:
        NMRData object
    """
    peaks = []

    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        for row in reader:
            row = {k.strip().lower().replace(" ", "_"): v.strip() for k, v in row.items()}

            shift = float(row.get("shift", row.get("chemical_shift", row.get("ppm", "0"))))
            mult = row.get("multiplicity", row.get("mult", "s"))
            j_str = row.get("j", row.get("coupling", ""))
            integ = row.get("integration", row.get("int", row.get("h", "0")))
            assign = row.get("assignment", row.get("assign", ""))

            j_values = []
            if j_str:
                j_values = [float(j.strip()) for j in j_str.split(",") if j.strip()]

            peaks.append(NMRPeak(
                chemical_shift=shift,
                multiplicity=mult,
                coupling_constants=j_values,
                integration=float(integ) if integ else 0.0,
                assignment=assign,
            ))

    return NMRData(nucleus=nucleus, peaks=peaks)
