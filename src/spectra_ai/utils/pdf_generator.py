"""
PDF Report Generator for SpectraAI.

Generates professional PDF reports containing compound characterization,
spectral data, validation results, and AI interpretation summaries.
Uses reportlab for PDF generation with fallback to basic text export.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

from ..core.molecule import Molecule
from ..core.nmr_data import NMRData
from ..core.ir_data import IRData
from ..core.ms_data import MSData
from ..core.validation_report import ValidationReport


def _has_reportlab() -> bool:
    try:
        import reportlab  # noqa
        return True
    except ImportError:
        return False


class PDFGenerator:
    """
    Generate PDF analysis reports for SpectraAI compounds.

    Uses reportlab when available, falls back to plain text export.
    """

    def generate(
        self,
        filepath: str,
        molecule: Molecule,
        h1_data: Optional[NMRData] = None,
        c13_data: Optional[NMRData] = None,
        ir_data: Optional[IRData] = None,
        ms_data: Optional[MSData] = None,
        validation_report: Optional[ValidationReport] = None,
        interpretation_text: str = "",
        characterization_text: str = "",
    ) -> bool:
        """
        Generate a PDF report.

        Args:
            filepath:             Output PDF file path
            molecule:             Molecule data
            h1_data:              ¹H NMR data
            c13_data:             ¹³C NMR data
            ir_data:              IR data
            ms_data:              HRMS data
            validation_report:    Validation results
            interpretation_text:  AI interpretation text
            characterization_text: Publication characterization text

        Returns:
            True if successful, False otherwise
        """
        if _has_reportlab():
            return self._generate_reportlab(
                filepath, molecule, h1_data, c13_data, ir_data, ms_data,
                validation_report, interpretation_text, characterization_text,
            )
        else:
            return self._generate_text_fallback(
                filepath, molecule, h1_data, c13_data, ir_data, ms_data,
                validation_report, interpretation_text, characterization_text,
            )

    def _generate_reportlab(self, filepath, molecule, h1_data, c13_data,
                             ir_data, ms_data, validation_report,
                             interpretation_text, characterization_text) -> bool:
        """Generate PDF using reportlab."""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import mm, cm
            from reportlab.platypus import (
                SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                PageBreak, HRFlowable,
            )
            from reportlab.lib.enums import TA_CENTER, TA_LEFT

            doc = SimpleDocTemplate(filepath, pagesize=A4,
                                     topMargin=2*cm, bottomMargin=2*cm,
                                     leftMargin=2*cm, rightMargin=2*cm)

            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                "CustomTitle", parent=styles["Title"],
                fontSize=18, textColor=colors.HexColor("#1f6feb"),
                spaceAfter=6*mm,
            )
            heading_style = ParagraphStyle(
                "CustomHeading", parent=styles["Heading2"],
                fontSize=13, textColor=colors.HexColor("#58a6ff"),
                spaceBefore=8*mm, spaceAfter=4*mm,
            )
            body_style = ParagraphStyle(
                "CustomBody", parent=styles["BodyText"],
                fontSize=10, leading=14,
            )

            elements = []

            # Title
            elements.append(Paragraph("SpectraAI Analysis Report", title_style))
            elements.append(Paragraph(
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                styles["Normal"],
            ))
            elements.append(HRFlowable(
                width="100%", thickness=1, color=colors.HexColor("#30363d"),
            ))
            elements.append(Spacer(1, 6*mm))

            # Compound info
            elements.append(Paragraph("Compound Information", heading_style))
            info_data = [
                ["Name:", molecule.name or "—"],
                ["ID:", molecule.compound_id or "—"],
                ["Formula:", molecule.formula or "—"],
                ["SMILES:", molecule.smiles or "—"],
                ["MW:", f"{molecule.molecular_weight:.4f}" if molecule.molecular_weight else "—"],
            ]
            if molecule.metadata and molecule.metadata.scaffold_family:
                info_data.append(["Scaffold:", molecule.metadata.scaffold_family])

            t = Table(info_data, colWidths=[3*cm, 13*cm])
            t.setStyle(TableStyle([
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            elements.append(t)

            # Spectral data
            if h1_data and h1_data.peaks:
                elements.append(Paragraph("¹H NMR Data", heading_style))
                elements.append(Paragraph(h1_data.raw_text or "—", body_style))

            if c13_data and c13_data.peaks:
                elements.append(Paragraph("¹³C NMR Data", heading_style))
                elements.append(Paragraph(c13_data.raw_text or "—", body_style))

            if ir_data and ir_data.absorptions:
                elements.append(Paragraph("IR Data", heading_style))
                elements.append(Paragraph(ir_data.raw_text or "—", body_style))

            if ms_data and ms_data.calculated_mz > 0:
                elements.append(Paragraph("HRMS Data", heading_style))
                elements.append(Paragraph(ms_data.display_text, body_style))

            # AI Interpretation
            if interpretation_text:
                elements.append(PageBreak())
                elements.append(Paragraph("AI Interpretation", heading_style))
                for para in interpretation_text.split("\n\n"):
                    if para.strip():
                        elements.append(Paragraph(para.strip(), body_style))
                        elements.append(Spacer(1, 3*mm))

            # Validation
            if validation_report:
                elements.append(Paragraph("Validation Results", heading_style))
                elements.append(Paragraph(
                    f"Overall Score: {validation_report.overall_score:.1f}/100 — "
                    f"{validation_report.overall_status_label}",
                    body_style,
                ))
                if validation_report.summary:
                    elements.append(Paragraph(validation_report.summary, body_style))

            # Characterization
            if characterization_text:
                elements.append(Paragraph("Characterization", heading_style))
                elements.append(Paragraph(characterization_text, body_style))

            doc.build(elements)
            return True

        except Exception as e:
            print(f"PDF generation error: {e}")
            return False

    def _generate_text_fallback(self, filepath, molecule, h1_data, c13_data,
                                 ir_data, ms_data, validation_report,
                                 interpretation_text, characterization_text) -> bool:
        """Fallback: generate a plain text report."""
        try:
            txt_path = filepath.replace(".pdf", ".txt")
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write("=" * 60 + "\n")
                f.write("  SpectraAI Analysis Report\n")
                f.write(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
                f.write("=" * 60 + "\n\n")

                f.write(f"Name:    {molecule.name or '—'}\n")
                f.write(f"ID:      {molecule.compound_id or '—'}\n")
                f.write(f"Formula: {molecule.formula or '—'}\n")
                f.write(f"SMILES:  {molecule.smiles or '—'}\n\n")

                if characterization_text:
                    f.write("CHARACTERIZATION:\n")
                    f.write(characterization_text + "\n\n")

                if validation_report:
                    f.write(f"VALIDATION SCORE: {validation_report.overall_score:.1f}/100\n")
                    if validation_report.summary:
                        f.write(validation_report.summary + "\n")

            return True
        except Exception:
            return False
