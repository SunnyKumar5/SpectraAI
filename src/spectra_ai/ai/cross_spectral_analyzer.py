"""
Cross-Spectral Analyzer — Multi-spectrum consistency analysis.

The core novelty of SpectraAI: jointly reasons across ¹H NMR, ¹³C NMR,
IR, HRMS, UV-Vis to identify contradictions and produce a unified
confidence assessment.
"""

from __future__ import annotations

from .llm_client import LLMClient
from .prompts import cross_spectral
from ..core.molecule import Molecule
from ..core.nmr_data import NMRData
from ..core.ir_data import IRData
from ..core.ms_data import MSData
from ..core.uv_data import UVData


class CrossSpectralAnalyzer:
    """
    AI-powered cross-spectral consistency analyzer.

    Simultaneously considers all available spectral data to find
    contradictions and assess overall characterization confidence.
    """

    def __init__(self, client: LLMClient):
        self.client = client

    def analyze(self, molecule: Molecule, h1: NMRData = None,
                c13: NMRData = None, ir: IRData = None,
                ms: MSData = None, uv: UVData = None) -> dict:
        """
        Perform cross-spectral consistency analysis.

        Args:
            molecule: Molecule with structure data
            h1, c13, ir, ms, uv: Available spectral data objects

        Returns:
            Dict with consistency report, contradictions, confidence score
        """
        # Build data summary for each spectrum
        h1_summary = self._summarize_h1(h1, molecule) if h1 and h1.peaks else ""
        c13_summary = self._summarize_c13(c13, molecule) if c13 and c13.peaks else ""
        ir_summary = self._summarize_ir(ir) if ir and ir.absorptions else ""
        ms_summary = self._summarize_ms(ms) if ms and (ms.calculated_mz or ms.observed_mz) else ""
        uv_summary = self._summarize_uv(uv) if uv and uv.absorptions else ""

        if not any([h1_summary, c13_summary, ir_summary, ms_summary, uv_summary]):
            return {
                "consistency_score": 0,
                "contradictions": [],
                "summary": "No spectral data provided for cross-spectral analysis.",
                "spectra_analyzed": [],
            }

        user_prompt = cross_spectral.build_user_prompt(
            h1_summary=h1_summary,
            c13_summary=c13_summary,
            ir_summary=ir_summary,
            ms_summary=ms_summary,
            uv_summary=uv_summary,
            smiles=molecule.smiles,
            formula=molecule.formula,
            name=molecule.name,
            scaffold_family=molecule.metadata.scaffold_family,
        )

        result = self.client.generate_json(
            system=cross_spectral.SYSTEM_PROMPT,
            user=user_prompt,
            temperature=0.2,
        )

        if result is None:
            response = self.client.generate(
                system=cross_spectral.SYSTEM_PROMPT,
                user=user_prompt,
            )
            return {
                "consistency_score": 50,
                "summary": response.text,
                "contradictions": [],
                "warnings": ["Non-structured response from AI"],
            }

        return result

    # ── Data summarization helpers ────────────────────────────────────────────

    def _summarize_h1(self, h1: NMRData, molecule: Molecule) -> str:
        lines = [f"¹H NMR ({h1.frequency} MHz, {h1.solvent}):"]
        lines.append(f"  Total peaks: {h1.peak_count}")
        lines.append(f"  Total integration: {h1.total_integration:.1f}H")
        lines.append(f"  Expected H count from formula: {molecule.expected_hydrogen_count}")
        lines.append(f"  Aromatic peaks: {len(h1.aromatic_peaks)}")
        lines.append(f"  Aliphatic peaks: {len(h1.aliphatic_peaks)}")
        lines.append(f"  Shift range: δ {h1.shift_range[0]:.2f}–{h1.shift_range[1]:.2f}")
        if h1.raw_text:
            lines.append(f"  Raw data: {h1.raw_text[:500]}")
        return "\n".join(lines)

    def _summarize_c13(self, c13: NMRData, molecule: Molecule) -> str:
        lines = [f"¹³C NMR ({c13.frequency} MHz, {c13.solvent}):"]
        lines.append(f"  Total peaks: {c13.peak_count}")
        lines.append(f"  Expected C count from formula: {molecule.expected_carbon_count}")
        lines.append(f"  Aromatic carbons: {len(c13.aromatic_peaks)}")
        lines.append(f"  Aliphatic carbons: {len(c13.aliphatic_peaks)}")
        lines.append(f"  Carbonyl carbons: {len(c13.carbonyl_peaks)}")
        shifts = ", ".join(f"{p.chemical_shift:.1f}" for p in c13.sorted_peaks()[:20])
        lines.append(f"  Shifts: δ {shifts}")
        return "\n".join(lines)

    def _summarize_ir(self, ir: IRData) -> str:
        lines = [f"IR ({ir.method}):"]
        lines.append(f"  Number of bands: {ir.band_count}")
        for a in ir.sorted_absorptions()[:15]:
            intensity = f" ({a.intensity})" if a.intensity else ""
            lines.append(f"  {a.wavenumber:.0f} cm⁻¹{intensity}")
        return "\n".join(lines)

    def _summarize_ms(self, ms: MSData) -> str:
        lines = [f"HRMS ({ms.technique}):"]
        lines.append(f"  Ion type: {ms.ion_type}")
        lines.append(f"  Calculated m/z: {ms.calculated_mz:.4f}")
        lines.append(f"  Observed m/z: {ms.observed_mz:.4f}")
        lines.append(f"  ppm error: {ms.ppm_error:.2f}")
        lines.append(f"  Formula: {ms.formula}")
        return "\n".join(lines)

    def _summarize_uv(self, uv: UVData) -> str:
        lines = [f"UV-Vis ({uv.solvent}):"]
        for a in uv.absorptions:
            lines.append(f"  λmax = {a.wavelength:.0f} nm")
        return "\n".join(lines)
