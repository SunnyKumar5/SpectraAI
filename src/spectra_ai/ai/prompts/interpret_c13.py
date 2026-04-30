"""
¹³C NMR Interpretation Prompt Template.

Generates carbon-by-carbon interpretation with DEPT awareness.
"""

SYSTEM_PROMPT = """You are a senior organic chemistry researcher and expert NMR spectroscopist \
specializing in ¹³C NMR interpretation of heterocyclic compounds. You have deep expertise in \
imidazo[1,2-a]pyridines, indoles, quinazolines, triazoles, pyrazolopyrimidines, and coumarins.

Your task is to interpret ¹³C NMR data and provide:
1. Classification of each peak by chemical environment (aromatic, aliphatic, carbonyl, etc.)
2. Assignment to specific carbons when structure is known
3. Carbon count verification against molecular formula
4. Identification of quaternary carbons and symmetry considerations

IMPORTANT RULES:
- Group carbons by region: carbonyl (160-220), aromatic/heteroaromatic (100-160), aliphatic C-O/C-N (40-100), aliphatic (0-40)
- Note if the observed peak count matches the expected unique carbon count
- Consider molecular symmetry that could reduce the observed number of peaks
- If DEPT data is provided, use it to distinguish CH3, CH2, CH, and quaternary carbons

Respond ONLY with a valid JSON object."""


def build_user_prompt(
    peaks_text: str,
    frequency: int = 100,
    solvent: str = "CDCl3",
    smiles: str = "",
    formula: str = "",
    scaffold_family: str = "",
    scaffold_reference: str = "",
    name: str = "",
    expected_carbons: int = 0,
) -> str:
    prompt = f"""Analyze the following ¹³C NMR data:

Compound: {name or 'Unknown'}
{f'SMILES: {smiles}' if smiles else 'SMILES: Not provided'}
{f'Molecular Formula: {formula}' if formula else ''}
{f'Expected unique carbons: {expected_carbons}' if expected_carbons else ''}
{f'Scaffold Family: {scaffold_family}' if scaffold_family else ''}
Spectrometer: {frequency} MHz
Solvent: {solvent}

¹³C NMR peaks (δ, ppm):
{peaks_text}
"""
    if scaffold_reference:
        prompt += f"\nScaffold Reference Ranges:\n{scaffold_reference}\n"

    prompt += """
Provide your analysis as JSON:
{
  "peaks": [
    {
      "shift": <float>,
      "region": "<carbonyl|aromatic|heteroaromatic|aliphatic_heteroatom|aliphatic>",
      "assignment": "<string — e.g. C-2, C=O, OCH3, ArC>",
      "carbon_type": "<quaternary|CH|CH2|CH3|unknown>",
      "reasoning": "<string>",
      "confidence": "<high|medium|low>",
      "status": "<consistent|warning|conflict>"
    }
  ],
  "carbon_count": {
    "observed": <int>,
    "expected": <int>,
    "status": "<match|possible_overlap|mismatch>",
    "explanation": "<string>"
  },
  "region_summary": {
    "carbonyl": <int>,
    "aromatic": <int>,
    "aliphatic_heteroatom": <int>,
    "aliphatic": <int>
  },
  "symmetry_note": "<string — any symmetry considerations>",
  "summary": "<string>",
  "warnings": ["<string>"]
}"""
    return prompt
