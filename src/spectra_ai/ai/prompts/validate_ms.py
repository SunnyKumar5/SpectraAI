"""
HRMS Validation Prompt Template.

Validates mass spectrometry data against molecular formula.
"""

SYSTEM_PROMPT = """You are an expert in high-resolution mass spectrometry interpretation. \
Evaluate the HRMS data for consistency with the proposed molecular formula and structure.

Respond ONLY with a valid JSON object."""


def build_user_prompt(
    ms_text: str,
    formula: str = "",
    smiles: str = "",
    name: str = "",
) -> str:
    return f"""Validate the following HRMS data:

Compound: {name or 'Unknown'}
{f'SMILES: {smiles}' if smiles else ''}
{f'Molecular Formula: {formula}' if formula else ''}

HRMS Data:
{ms_text}

Provide your analysis as JSON:
{{
  "formula_confirmed": <true|false>,
  "ppm_error": <float>,
  "tolerance_status": "<excellent|acceptable|warning|fail>",
  "ion_type_correct": <true|false>,
  "isotope_pattern_note": "<string>",
  "summary": "<string>",
  "status": "<consistent|warning|conflict>"
}}"""
