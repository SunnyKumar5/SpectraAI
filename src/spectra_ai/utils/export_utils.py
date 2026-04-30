"""
Export Utilities for SpectraAI.

Helper functions for exporting analysis results in various formats:
JSON, CSV, clipboard-ready text, and structured data for other tools.
"""

from __future__ import annotations

import csv
import json
import os
from datetime import datetime
from typing import Optional

from ..core.molecule import Molecule
from ..core.nmr_data import NMRData
from ..core.ir_data import IRData
from ..core.ms_data import MSData
from ..core.validation_report import ValidationReport


def export_compound_json(molecule: Molecule, filepath: str) -> bool:
    """Export a compound to a JSON file."""
    try:
        molecule.save_json(filepath)
        return True
    except Exception:
        return False


def export_validation_csv(
    report: ValidationReport,
    filepath: str,
    molecule: Optional[Molecule] = None,
) -> bool:
    """Export validation check results to CSV."""
    try:
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Compound", "Check Name", "Category",
                "Expected", "Observed", "Status", "Score", "Explanation",
            ])
            name = molecule.name if molecule else "Unknown"
            for check in report.checks:
                writer.writerow([
                    name, check.name, check.category,
                    check.expected, check.observed,
                    check.status, f"{check.score:.1f}", check.explanation,
                ])
        return True
    except Exception:
        return False


def export_batch_csv(
    results: list[dict],
    filepath: str,
) -> bool:
    """
    Export batch analysis results to CSV.

    Args:
        results: List of dicts with keys:
                 compound_id, name, formula, status, score, summary
        filepath: Output CSV path
    """
    try:
        if not results:
            return False
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
        return True
    except Exception:
        return False


def export_peak_list_csv(
    peaks: list[dict],
    filepath: str,
    nucleus: str = "1H",
) -> bool:
    """
    Export NMR peak list to CSV.

    Args:
        peaks: List of peak dicts (shift, multiplicity, J, integration, assignment)
        filepath: Output CSV path
        nucleus: "1H" or "13C"
    """
    try:
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if nucleus == "1H":
                writer.writerow([
                    "Chemical Shift (ppm)", "Multiplicity", "J (Hz)",
                    "Integration", "Assignment", "AI Confidence",
                ])
            else:
                writer.writerow([
                    "Chemical Shift (ppm)", "Assignment", "AI Confidence",
                ])

            for p in peaks:
                if nucleus == "1H":
                    j_str = ", ".join(str(j) for j in p.get("J", []))
                    writer.writerow([
                        f"{p.get('shift', 0):.2f}",
                        p.get("multiplicity", ""),
                        j_str,
                        f"{p.get('integration', 0):.1f}",
                        p.get("assignment", ""),
                        f"{p.get('confidence', 0)*100:.0f}%",
                    ])
                else:
                    writer.writerow([
                        f"{p.get('shift', 0):.1f}",
                        p.get("assignment", ""),
                        f"{p.get('confidence', 0)*100:.0f}%",
                    ])
        return True
    except Exception:
        return False


def format_characterization_text(
    molecule: Molecule,
    h1_data: Optional[NMRData] = None,
    c13_data: Optional[NMRData] = None,
    ir_data: Optional[IRData] = None,
    ms_data: Optional[MSData] = None,
    style: str = "ACS",
) -> str:
    """
    Format compound characterization text in journal style.

    This is a rule-based formatter (no AI) that assembles the
    characterization from parsed data. For AI-generated text,
    use CharacterizationWriter.

    Args:
        molecule: Molecule with name/formula
        h1_data:  ¹H NMR data
        c13_data: ¹³C NMR data
        ir_data:  IR data
        ms_data:  HRMS data
        style:    "ACS", "RSC", or "Wiley"

    Returns:
        Formatted characterization paragraph
    """
    parts = []

    # Name and physical properties
    name = molecule.name or "Unknown compound"
    parts.append(f"{name}.")

    if molecule.melting_point:
        mp_low, mp_high = molecule.melting_point
        parts.append(f"Mp {mp_low}–{mp_high} °C.")

    # ¹H NMR
    if h1_data and h1_data.raw_text:
        parts.append(h1_data.raw_text.strip().rstrip(".") + ".")

    # ¹³C NMR
    if c13_data and c13_data.raw_text:
        parts.append(c13_data.raw_text.strip().rstrip(".") + ".")

    # IR
    if ir_data and ir_data.raw_text:
        parts.append(ir_data.raw_text.strip().rstrip(".") + ".")

    # HRMS
    if ms_data and ms_data.raw_text:
        parts.append(ms_data.raw_text.strip().rstrip(".") + ".")

    return " ".join(parts)


def generate_report_dict(
    molecule: Molecule,
    validation_report: Optional[ValidationReport] = None,
    interpretation_text: str = "",
    characterization_text: str = "",
) -> dict:
    """
    Generate a complete report dictionary for export.

    Returns a dict suitable for JSON serialization containing
    all compound data, analysis results, and metadata.
    """
    report = {
        "generated_at": datetime.now().isoformat(),
        "version": "1.0.0",
        "compound": molecule.to_dict(),
    }

    if validation_report:
        report["validation"] = {
            "overall_score": validation_report.overall_score,
            "status": validation_report.overall_status,
            "checks": [
                {
                    "name": c.name,
                    "category": c.category,
                    "status": c.status,
                    "score": c.score,
                    "expected": c.expected,
                    "observed": c.observed,
                }
                for c in validation_report.checks
            ],
            "summary": validation_report.summary,
        }

    if interpretation_text:
        report["interpretation"] = interpretation_text

    if characterization_text:
        report["characterization"] = characterization_text

    return report
