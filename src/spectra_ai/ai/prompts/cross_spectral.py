"""
Cross-Spectral Analysis Prompt Template.

Performs joint reasoning across all available spectral data to identify
contradictions and confirm consistency — a key novelty of SpectraAI.
"""

SYSTEM_PROMPT = """You are a senior analytical chemistry expert performing multi-spectral \
cross-validation of a compound's characterization data. You have access to multiple types \
of spectral data and must check them against each other for internal consistency.

Your reasoning approach:
Step 1: Summarize what each spectrum individually tells us
Step 2: Check proton count consistency (¹H integration vs formula vs HRMS)
Step 3: Check carbon count consistency (¹³C peaks vs formula)
Step 4: Check functional group consistency (IR vs structure vs NMR)
Step 5: Check mass consistency (HRMS vs formula)
Step 6: Identify ANY contradictions between different data types
Step 7: Calculate an overall confidence score (0-100)

Be meticulous. A single contradiction should lower the confidence significantly.

Respond ONLY with a valid JSON object."""


def build_user_prompt(
    h1_summary: str = "",
    c13_summary: str = "",
    ir_summary: str = "",
    ms_summary: str = "",
    uv_summary: str = "",
    formula: str = "",
    smiles: str = "",
    name: str = "",
    scaffold_family: str = "",
) -> str:
    sections = [f"Compound: {name or 'Unknown'}"]
    if smiles:
        sections.append(f"SMILES: {smiles}")
    if formula:
        sections.append(f"Molecular Formula: {formula}")
    if scaffold_family:
        sections.append(f"Scaffold: {scaffold_family}")

    sections.append("\n--- Available Spectral Data ---")
    if h1_summary:
        sections.append(f"\n¹H NMR:\n{h1_summary}")
    if c13_summary:
        sections.append(f"\n¹³C NMR:\n{c13_summary}")
    if ir_summary:
        sections.append(f"\nIR:\n{ir_summary}")
    if ms_summary:
        sections.append(f"\nHRMS:\n{ms_summary}")
    if uv_summary:
        sections.append(f"\nUV-Vis:\n{uv_summary}")

    prompt = "\n".join(sections) + """

Perform a thorough cross-spectral consistency analysis. Return JSON:
{
  "individual_assessments": {
    "h1_nmr": "<string — brief assessment>",
    "c13_nmr": "<string>",
    "ir": "<string>",
    "hrms": "<string>",
    "uv_vis": "<string>"
  },
  "cross_checks": [
    {
      "check": "<string — what was compared>",
      "data_types": ["<string — which spectra involved>"],
      "result": "<consistent|warning|conflict>",
      "detail": "<string — explanation>"
    }
  ],
  "contradictions": ["<string — any contradictions found>"],
  "confidence_score": <int 0-100>,
  "confidence_breakdown": {
    "proton_count": <int 0-100>,
    "carbon_count": <int 0-100>,
    "functional_groups": <int 0-100>,
    "mass_spec": <int 0-100>,
    "chemical_shifts": <int 0-100>,
    "cross_spectral": <int 0-100>
  },
  "overall_assessment": "<string — HIGH CONFIDENCE / MEDIUM CONFIDENCE / LOW CONFIDENCE / ISSUES DETECTED>",
  "summary": "<string — 3-4 sentence summary>",
  "recommendations": ["<string — suggested additional experiments or checks>"]
}"""
    return prompt
