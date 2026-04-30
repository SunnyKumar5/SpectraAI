"""
Impurity Detection Prompt Template.
"""

SYSTEM_PROMPT = """You are an expert in NMR spectral analysis specializing in identifying \
impurities, residual solvents, and unreacted starting materials in synthetic compounds.

Respond ONLY with a valid JSON object."""


def build_user_prompt(
    unassigned_peaks: str = "",
    solvent: str = "CDCl3",
    reaction_type: str = "",
    starting_materials: str = "",
) -> str:
    return f"""Identify possible sources for these unassigned NMR peaks:

Solvent: {solvent}
{f'Reaction type: {reaction_type}' if reaction_type else ''}
{f'Starting materials: {starting_materials}' if starting_materials else ''}

Unassigned peaks:
{unassigned_peaks}

Return JSON:
{{
  "identified_impurities": [
    {{
      "peak": "<shift>",
      "suggested_source": "<name>",
      "confidence": "<high|medium|low>",
      "reasoning": "<string>"
    }}
  ],
  "residual_solvent_peaks": ["<shifts matching known solvent residuals>"],
  "possible_starting_material": ["<peaks matching starting material>"],
  "summary": "<string>"
}}"""
