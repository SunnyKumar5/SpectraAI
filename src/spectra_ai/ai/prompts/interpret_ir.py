"""
IR Interpretation Prompt Template.

Identifies functional groups and cross-checks against molecular structure.
"""

SYSTEM_PROMPT = """You are an expert in infrared spectroscopy interpretation for organic compounds. \
You specialize in identifying functional groups from IR absorption bands and cross-checking \
them against known molecular structures.

Your task is to:
1. Assign each observed IR band to a functional group
2. Identify which expected functional groups are present and which are missing
3. Flag any unexpected absorptions that may indicate impurities or structural issues

Respond ONLY with a valid JSON object."""


def build_user_prompt(
    bands_text: str,
    method: str = "KBr",
    smiles: str = "",
    formula: str = "",
    expected_groups: str = "",
    name: str = "",
) -> str:
    prompt = f"""Analyze the following IR spectral data:

Compound: {name or 'Unknown'}
{f'SMILES: {smiles}' if smiles else ''}
{f'Molecular Formula: {formula}' if formula else ''}
Method: {method}

IR Absorptions (cm⁻¹):
{bands_text}

{f'Expected functional groups based on structure: {expected_groups}' if expected_groups else ''}

Provide your analysis as JSON:
{{
  "bands": [
    {{
      "wavenumber": <float>,
      "assignment": "<string — functional group>",
      "region": "<X-H_stretch|triple_bond|double_bond|fingerprint>",
      "reasoning": "<string>",
      "status": "<expected|unexpected|missing_expected>"
    }}
  ],
  "functional_groups_found": ["<string>"],
  "expected_but_missing": ["<string — groups expected from structure but not observed>"],
  "unexpected_bands": ["<string — bands not explained by structure>"],
  "summary": "<string>",
  "warnings": ["<string>"]
}}"""
    return prompt
