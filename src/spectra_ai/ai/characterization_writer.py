"""
Characterization Writer — Publication-ready text generator.

Generates formatted compound characterization text for journal
experimental sections in ACS, RSC, or Wiley style.
"""

from __future__ import annotations

from .llm_client import LLMClient
from .prompts import write_characterization
from ..core.molecule import Molecule
from ..core.nmr_data import NMRData
from ..core.ir_data import IRData
from ..core.ms_data import MSData


class CharacterizationWriter:
    """Generates publication-quality characterization text."""

    def __init__(self, client: LLMClient):
        self.client = client

    def generate(self, molecule: Molecule, h1: NMRData = None,
                 c13: NMRData = None, ir: IRData = None,
                 ms: MSData = None, format_style: str = "ACS",
                 verbosity: str = "standard") -> str:
        """
        Generate publication characterization text.

        Args:
            molecule:      Molecule data
            h1, c13, ir, ms: Spectral data
            format_style:  "ACS", "RSC", or "Wiley"
            verbosity:     "concise", "standard", or "detailed"

        Returns:
            Formatted characterization paragraph string
        """
        # Build data context
        data_sections = []

        if h1 and h1.peaks:
            data_sections.append(f"¹H NMR ({h1.frequency} MHz, {h1.solvent}): " +
                                 (h1.raw_text or self._format_h1(h1)))

        if c13 and c13.peaks:
            data_sections.append(f"¹³C NMR ({c13.frequency} MHz, {c13.solvent}): " +
                                 (c13.raw_text or self._format_c13(c13)))

        if ir and ir.absorptions:
            data_sections.append(f"IR ({ir.method}): " +
                                 (ir.raw_text or self._format_ir(ir)))

        if ms and ms.observed_mz:
            data_sections.append(ms.display_text)

        if molecule.melting_point:
            mp = molecule.melting_point
            data_sections.append(f"mp {mp[0]}–{mp[1]} °C")

        if molecule.elemental_analysis:
            ea_parts = []
            for elem, val in molecule.elemental_analysis.items():
                ea_parts.append(f"{elem} {val:.2f}")
            data_sections.append(f"Anal. ({', '.join(ea_parts)})")

        # Build individual data strings for the prompt
        h1_str = ""
        c13_str = ""
        ir_str = ""
        ms_str = ""
        uv_str = ""
        mp_str = ""
        ea_str = ""

        if h1 and h1.peaks:
            h1_str = f"({h1.frequency} MHz, {h1.solvent}): " + (h1.raw_text or self._format_h1(h1))
        if c13 and c13.peaks:
            c13_str = f"({c13.frequency} MHz, {c13.solvent}): " + (c13.raw_text or self._format_c13(c13))
        if ir and ir.absorptions:
            ir_str = f"({ir.method}): " + (ir.raw_text or self._format_ir(ir))
        if ms and ms.observed_mz:
            ms_str = ms.display_text
        if molecule.melting_point:
            mp = molecule.melting_point
            mp_str = f"{mp[0]}–{mp[1]} °C"
        if molecule.elemental_analysis:
            ea_parts = [f"{elem} {val:.2f}" for elem, val in molecule.elemental_analysis.items()]
            ea_str = ", ".join(ea_parts)

        user_prompt = write_characterization.build_user_prompt(
            name=molecule.name,
            smiles=molecule.smiles,
            formula=molecule.formula,
            h1_data=h1_str,
            c13_data=c13_str,
            ir_data=ir_str,
            ms_data=ms_str,
            melting_point=mp_str,
            elemental_analysis=ea_str,
            journal_format=format_style,
            verbosity=verbosity,
        )

        response = self.client.generate(
            system=write_characterization.SYSTEM_PROMPT,
            user=user_prompt,
            temperature=0.2,
        )

        # Clean up response (remove any markdown artifacts)
        text = response.text.strip()
        for prefix in ["```", "```text", "```\n"]:
            if text.startswith(prefix):
                text = text[len(prefix):]
        text = text.rstrip("`").strip()

        return text

    def generate_rule_based(self, molecule: Molecule, h1: NMRData = None,
                            c13: NMRData = None, ir: IRData = None,
                            ms: MSData = None, format_style: str = "ACS") -> str:
        """
        Generate characterization text using rule-based formatting.

        Fallback when AI is unavailable — produces standard format
        without intelligent assignment.
        """
        parts = []

        if h1 and h1.peaks:
            peaks_str = self._format_h1(h1)
            parts.append(f"¹H NMR ({h1.frequency} MHz, {h1.solvent}): δ {peaks_str}")

        if c13 and c13.peaks:
            peaks_str = self._format_c13(c13)
            parts.append(f"¹³C NMR ({c13.frequency} MHz, {c13.solvent}): δ {peaks_str}")

        if ir and ir.absorptions:
            ir_str = self._format_ir(ir)
            parts.append(f"IR ({ir.method}): ν̃ {ir_str} cm⁻¹")

        if ms and ms.observed_mz:
            parts.append(ms.display_text)

        if molecule.melting_point:
            parts.append(f"mp {molecule.melting_point[0]}–{molecule.melting_point[1]} °C")

        return "; ".join(parts) + "." if parts else ""

    # ── Formatting helpers ────────────────────────────────────────────────────

    def _format_h1(self, h1: NMRData) -> str:
        parts = []
        for p in h1.sorted_peaks():
            s = f"{p.chemical_shift:.2f}"
            details = [p.multiplicity]
            if p.coupling_constants:
                j_str = ", ".join(f"{j:.1f}" for j in p.coupling_constants)
                details.append(f"J = {j_str} Hz")
            if p.integration > 0:
                h = int(p.integration) if p.integration == int(p.integration) else p.integration
                details.append(f"{h}H")
            if p.assignment:
                details.append(p.assignment)
            s += f" ({', '.join(details)})"
            parts.append(s)
        return ", ".join(parts)

    def _format_c13(self, c13: NMRData) -> str:
        return ", ".join(f"{p.chemical_shift:.1f}" for p in c13.sorted_peaks())

    def _format_ir(self, ir: IRData) -> str:
        return ", ".join(f"{a.wavenumber:.0f}" for a in ir.sorted_absorptions())
