"""
NMR Prediction Prompt Template.

Given a SMILES structure, predict expected ¹H and ¹³C NMR spectra.
"""

SYSTEM_PROMPT = """You are an expert NMR spectroscopist. Given a molecular structure (SMILES), \
predict the expected ¹H and ¹³C NMR chemical shifts, multiplicities, and coupling constants.

Use your knowledge of chemical shift prediction rules, ring current effects, \
electronegativity effects, and anisotropy.

Respond ONLY with a valid JSON object."""


def build_user_prompt(
    smiles: str,
    formula: str = "",
    scaffold_family: str = "",
    solvent: str = "CDCl3",
    frequency: int = 400,
) -> str:
    return f"""Predict the NMR spectrum for:

SMILES: {smiles}
{f'Formula: {formula}' if formula else ''}
{f'Scaffold: {scaffold_family}' if scaffold_family else ''}
Solvent: {solvent}
Frequency: {frequency} MHz

Return JSON:
{{
  "h1_predicted": [
    {{
      "shift": <float>,
      "multiplicity": "<s|d|t|q|m|dd|...>",
      "coupling_constants": [<float>],
      "integration": <int>,
      "assignment": "<atom label>"
    }}
  ],
  "c13_predicted": [
    {{
      "shift": <float>,
      "assignment": "<atom label>",
      "carbon_type": "<CH3|CH2|CH|quaternary>"
    }}
  ],
  "notes": "<any prediction caveats>"
}}"""
