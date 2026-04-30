"""
Structure Prediction Prompt Template.

Generates ranked candidate structures from spectral data,
constrained by scaffold family when specified.
"""

SYSTEM_PROMPT = """You are an expert in computer-aided structure elucidation (CASE). \
Given NMR and other spectral data, you propose candidate molecular structures ranked by \
how well they match the observed data.

When a scaffold family constraint is provided, all candidates MUST contain that scaffold core.

For each candidate, you must explain:
- Which peaks support this structure
- Which peaks conflict (if any)
- Why this candidate ranks where it does

Provide SMILES strings that are valid and canonical.

Respond ONLY with a valid JSON object."""


def build_user_prompt(
    h1_text: str = "",
    c13_text: str = "",
    ir_text: str = "",
    ms_text: str = "",
    formula: str = "",
    scaffold_family: str = "",
    scaffold_reference: str = "",
    reaction_context: str = "",
    max_candidates: int = 5,
) -> str:
    sections = []
    if formula:
        sections.append(f"Molecular Formula: {formula}")
    if scaffold_family:
        sections.append(f"Scaffold Constraint: {scaffold_family}")
    if reaction_context:
        sections.append(f"Reaction Context: {reaction_context}")

    sections.append("\n--- Spectral Data ---")
    if h1_text:
        sections.append(f"¹H NMR: {h1_text}")
    if c13_text:
        sections.append(f"¹³C NMR: {c13_text}")
    if ir_text:
        sections.append(f"IR: {ir_text}")
    if ms_text:
        sections.append(f"HRMS: {ms_text}")
    if scaffold_reference:
        sections.append(f"\nScaffold Reference:\n{scaffold_reference}")

    prompt = "\n".join(sections) + f"""

Propose up to {max_candidates} candidate structures. Return JSON:
{{
  "candidates": [
    {{
      "rank": <int>,
      "smiles": "<valid SMILES string>",
      "name": "<proposed IUPAC or common name>",
      "formula": "<molecular formula>",
      "confidence": <float 0.0-1.0>,
      "explanation": "<why this candidate>",
      "matching_peaks": ["<peaks that support this>"],
      "conflicting_peaks": ["<peaks that conflict>"],
      "scaffold_family": "<detected scaffold>"
    }}
  ],
  "reasoning": "<overall reasoning chain>",
  "warnings": ["<any caveats>"]
}}"""
    return prompt
