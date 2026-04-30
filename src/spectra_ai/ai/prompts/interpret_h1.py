"""
¹H NMR Interpretation Prompt Template.

Generates peak-by-peak chemical interpretation with scaffold-aware reasoning.
"""

SYSTEM_PROMPT = """You are a senior organic chemistry researcher and expert NMR spectroscopist \
with 25+ years of experience in heterocyclic compound characterization. You specialize in \
imidazo[1,2-a]pyridines, indoles, quinazolines, 1,2,3-triazoles, pyrazolopyrimidines, \
and coumarins — compounds commonly synthesized in academic organic chemistry labs.

Your task is to interpret ¹H NMR data for a given compound and provide:
1. Peak-by-peak assignment with chemical reasoning
2. Identification of diagnostic signals
3. Aromatic substitution pattern analysis
4. Assessment of consistency with the provided structure (if SMILES given)

IMPORTANT RULES:
- Be specific and scientifically rigorous in your reasoning
- Reference coupling constant values to justify multiplicity assignments
- Note any unusual shifts or unexpected features
- If a scaffold family is specified, use your knowledge of typical chemical shifts for that scaffold
- Always consider the solvent's effect on chemical shifts (especially exchangeable protons)

Respond ONLY with a valid JSON object (no markdown fences, no explanatory text outside JSON)."""


def build_user_prompt(
    peaks_text: str,
    frequency: int = 400,
    solvent: str = "CDCl3",
    smiles: str = "",
    formula: str = "",
    scaffold_family: str = "",
    scaffold_reference: str = "",
    name: str = "",
) -> str:
    """Build the user prompt for ¹H NMR interpretation."""

    prompt = f"""Analyze the following ¹H NMR data:

Compound: {name or 'Unknown'}
{f'SMILES: {smiles}' if smiles else 'SMILES: Not provided (structure unknown)'}
{f'Molecular Formula: {formula}' if formula else ''}
{f'Scaffold Family: {scaffold_family}' if scaffold_family else ''}
Spectrometer: {frequency} MHz
Solvent: {solvent}

¹H NMR Data:
{peaks_text}
"""

    if scaffold_reference:
        prompt += f"""
Scaffold Reference Ranges:
{scaffold_reference}
"""

    prompt += """
Provide your analysis as a JSON object with this exact structure:
{
  "peaks": [
    {
      "shift": <float>,
      "multiplicity": "<string>",
      "integration": <float>,
      "assignment": "<string — e.g. H-5, ArH, OCH3>",
      "reasoning": "<string — 1-2 sentences of chemical reasoning>",
      "confidence": "<high|medium|low>",
      "status": "<consistent|warning|conflict>"
    }
  ],
  "aromatic_analysis": "<string — analysis of aromatic region pattern>",
  "diagnostic_signals": ["<string — key diagnostic peaks>"],
  "summary": "<string — 2-3 sentence overall interpretation>",
  "warnings": ["<string — any concerns or inconsistencies>"]
}"""

    return prompt


RESPONSE_SCHEMA = {
    "peaks": [
        {
            "shift": "float",
            "multiplicity": "string",
            "integration": "float",
            "assignment": "string",
            "reasoning": "string",
            "confidence": "high|medium|low",
            "status": "consistent|warning|conflict",
        }
    ],
    "aromatic_analysis": "string",
    "diagnostic_signals": ["string"],
    "summary": "string",
    "warnings": ["string"],
}
