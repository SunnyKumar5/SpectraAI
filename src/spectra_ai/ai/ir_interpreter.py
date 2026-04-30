"""
IR Interpreter — AI-powered infrared spectral interpretation.

Uses Claude/Gemini to assign IR absorption bands to functional groups
and cross-check against the molecular structure.
"""

from __future__ import annotations

from .llm_client import LLMClient
from .prompts import interpret_ir
from ..core.ir_data import IRData
from ..core.molecule import Molecule


class IRInterpreter:
    """AI-powered IR spectral interpreter."""

    def __init__(self, client: LLMClient):
        self.client = client

    def interpret(self, ir_data: IRData, molecule: Molecule) -> dict:
        """
        Interpret IR data with structure cross-referencing.

        Returns dict with band assignments, functional groups, and consistency check.
        """
        bands_text = self._format_bands(ir_data)

        user_prompt = interpret_ir.build_user_prompt(
            bands_text=bands_text,
            method=ir_data.method,
            smiles=molecule.smiles,
            formula=molecule.formula,
            name=molecule.name,
        )

        result = self.client.generate_json(
            system=interpret_ir.SYSTEM_PROMPT,
            user=user_prompt,
            temperature=0.2,
        )

        if result is None:
            response = self.client.generate(
                system=interpret_ir.SYSTEM_PROMPT,
                user=user_prompt,
            )
            return {
                "bands": [],
                "summary": response.text,
                "warnings": ["AI returned non-structured response"],
            }

        # Apply AI assignments back to absorption objects
        for ai_band in result.get("bands", []):
            wn = ai_band.get("wavenumber", 0)
            for absorption in ir_data.absorptions:
                if abs(absorption.wavenumber - wn) < 20:
                    absorption.ai_assignment = ai_band.get("assignment", "")
                    absorption.ai_reasoning = ai_band.get("reasoning", "")
                    absorption.ai_status = ai_band.get("status", "")
                    break

        return result

    def _format_bands(self, ir_data: IRData) -> str:
        if ir_data.raw_text:
            return ir_data.raw_text
        parts = []
        for a in ir_data.sorted_absorptions():
            s = f"{a.wavenumber:.0f}"
            if a.intensity:
                s += f" ({a.intensity})"
            parts.append(s)
        return ", ".join(parts) + " cm⁻¹" if parts else "No IR data provided"
