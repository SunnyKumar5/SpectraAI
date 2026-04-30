"""
NMR Interpreter — AI-powered NMR spectral interpretation.

Uses Claude/Gemini to provide peak-by-peak assignments with
scaffold-aware chemical reasoning.
"""

from __future__ import annotations

import json
from typing import Optional

from .llm_client import LLMClient, AIResponse
from .prompts import interpret_h1, interpret_c13
from ..core.nmr_data import NMRData, NMRPeak
from ..core.molecule import Molecule
from ..utils.nmr_reference import get_scaffold_references


class NMRInterpreter:
    """
    AI-powered NMR spectral interpreter.

    Sends structured NMR data + molecular context to an LLM and returns
    peak-by-peak interpretations with chemical reasoning.
    """

    def __init__(self, client: LLMClient):
        self.client = client

    def interpret_h1(self, nmr_data: NMRData, molecule: Molecule) -> dict:
        """
        Interpret ¹H NMR data.

        Args:
            nmr_data:  Parsed ¹H NMR data
            molecule:  Molecule context (SMILES, formula, scaffold)

        Returns:
            Interpretation result dict with peaks, summary, warnings
        """
        # Build scaffold reference context
        scaffold_ref = ""
        if molecule.metadata.scaffold_family:
            ref = get_scaffold_references(molecule.metadata.scaffold_family)
            if ref:
                scaffold_ref = self._format_scaffold_reference(ref, "h1")

        # Format peaks for the prompt
        peaks_text = self._format_h1_peaks(nmr_data)

        # Build prompt
        user_prompt = interpret_h1.build_user_prompt(
            peaks_text=peaks_text,
            frequency=nmr_data.frequency,
            solvent=nmr_data.solvent,
            smiles=molecule.smiles,
            formula=molecule.formula,
            scaffold_family=molecule.metadata.scaffold_family,
            scaffold_reference=scaffold_ref,
            name=molecule.name,
        )

        # Call LLM
        result = self.client.generate_json(
            system=interpret_h1.SYSTEM_PROMPT,
            user=user_prompt,
            temperature=0.2,
        )

        if result is None:
            # Fallback: try non-JSON parse
            response = self.client.generate(
                system=interpret_h1.SYSTEM_PROMPT,
                user=user_prompt,
            )
            return {
                "peaks": [],
                "summary": response.text,
                "warnings": ["AI returned non-structured response"],
                "raw_response": response.text,
            }

        # Merge AI assignments back into peak objects
        self._apply_ai_assignments(nmr_data, result.get("peaks", []))

        return result

    def interpret_c13(self, nmr_data: NMRData, molecule: Molecule) -> dict:
        """
        Interpret ¹³C NMR data.

        Args:
            nmr_data:  Parsed ¹³C NMR data
            molecule:  Molecule context

        Returns:
            Interpretation result dict
        """
        scaffold_ref = ""
        if molecule.metadata.scaffold_family:
            ref = get_scaffold_references(molecule.metadata.scaffold_family)
            if ref:
                scaffold_ref = self._format_scaffold_reference(ref, "c13")

        peaks_text = self._format_c13_peaks(nmr_data)

        user_prompt = interpret_c13.build_user_prompt(
            peaks_text=peaks_text,
            frequency=nmr_data.frequency,
            solvent=nmr_data.solvent,
            smiles=molecule.smiles,
            formula=molecule.formula,
            scaffold_family=molecule.metadata.scaffold_family,
            scaffold_reference=scaffold_ref,
            name=molecule.name,
            expected_carbons=molecule.expected_carbon_count,
        )

        result = self.client.generate_json(
            system=interpret_c13.SYSTEM_PROMPT,
            user=user_prompt,
            temperature=0.2,
        )

        if result is None:
            response = self.client.generate(
                system=interpret_c13.SYSTEM_PROMPT,
                user=user_prompt,
            )
            return {
                "peaks": [],
                "summary": response.text,
                "warnings": ["AI returned non-structured response"],
            }

        return result

    def interpret_h1_stream(self, nmr_data: NMRData, molecule: Molecule):
        """
        Stream ¹H NMR interpretation for real-time UI display.

        Yields text chunks as they arrive from the API.
        """
        scaffold_ref = ""
        if molecule.metadata.scaffold_family:
            ref = get_scaffold_references(molecule.metadata.scaffold_family)
            if ref:
                scaffold_ref = self._format_scaffold_reference(ref, "h1")

        peaks_text = self._format_h1_peaks(nmr_data)

        # For streaming, use a text-oriented system prompt
        stream_system = interpret_h1.SYSTEM_PROMPT.replace(
            "Respond ONLY with a valid JSON object (no markdown fences, no explanatory text outside JSON).",
            "Provide a detailed, well-formatted text analysis. Use clear headers and bullet points."
        )

        user_prompt = interpret_h1.build_user_prompt(
            peaks_text=peaks_text,
            frequency=nmr_data.frequency,
            solvent=nmr_data.solvent,
            smiles=molecule.smiles,
            formula=molecule.formula,
            scaffold_family=molecule.metadata.scaffold_family,
            scaffold_reference=scaffold_ref,
            name=molecule.name,
        ).replace(
            "Provide your analysis as a JSON object with this exact structure:",
            "Provide a detailed text analysis covering each peak:"
        )
        # Remove JSON schema from streaming prompt
        user_prompt = user_prompt.split("Provide a detailed text analysis")[0] + \
            "Provide a detailed text analysis covering each peak, then a summary."

        yield from self.client.generate_stream(
            system=stream_system,
            user=user_prompt,
            temperature=0.3,
        )

    # ── Formatting helpers ────────────────────────────────────────────────────

    def _format_h1_peaks(self, nmr_data: NMRData) -> str:
        """Format ¹H NMR peaks for prompt injection."""
        if nmr_data.raw_text:
            return nmr_data.raw_text

        lines = []
        for p in nmr_data.sorted_peaks():
            lines.append(p.display_text)
        return "; ".join(lines) if lines else "No peaks provided"

    def _format_c13_peaks(self, nmr_data: NMRData) -> str:
        """Format ¹³C NMR peaks for prompt injection."""
        if nmr_data.raw_text:
            return nmr_data.raw_text

        shifts = [f"{p.chemical_shift:.1f}" for p in nmr_data.sorted_peaks()]
        return "δ " + ", ".join(shifts) if shifts else "No peaks provided"

    def _format_scaffold_reference(self, ref: dict, spectrum_type: str) -> str:
        """Format scaffold reference data for prompt context."""
        lines = [f"Scaffold: {ref.get('name', 'Unknown')}"]

        data = ref.get(spectrum_type, {})
        if data:
            lines.append(f"Typical {spectrum_type.upper()} chemical shifts:")
            for position, info in data.items():
                if spectrum_type == "h1":
                    low, high, mult, notes = info
                    lines.append(f"  {position}: δ {low}–{high} ({mult}) — {notes}")
                else:
                    low, high, notes = info
                    lines.append(f"  {position}: δ {low}–{high} — {notes}")

        diagnostics = ref.get("diagnostic_features", [])
        if diagnostics:
            lines.append("Key diagnostic features:")
            for d in diagnostics:
                lines.append(f"  • {d}")

        return "\n".join(lines)

    def _apply_ai_assignments(self, nmr_data: NMRData, ai_peaks: list[dict]):
        """Merge AI peak assignments back into NMRPeak objects."""
        for ai_peak in ai_peaks:
            ai_shift = ai_peak.get("shift", 0)
            # Find closest matching peak
            best_match = None
            best_dist = float("inf")
            for peak in nmr_data.peaks:
                dist = abs(peak.chemical_shift - ai_shift)
                if dist < best_dist:
                    best_dist = dist
                    best_match = peak

            if best_match and best_dist < 0.5:  # within 0.5 ppm tolerance
                best_match.ai_assignment = ai_peak.get("assignment", "")
                best_match.ai_reasoning = ai_peak.get("reasoning", "")
                best_match.ai_confidence = ai_peak.get("confidence", "")
                best_match.ai_status = ai_peak.get("status", "")
