"""
Publication Characterization Writer Prompt Template.

Generates publication-ready compound characterization text in
ACS, RSC, or Wiley journal format.
"""

SYSTEM_PROMPT = """You are an expert scientific writer specializing in organic chemistry \
compound characterization for peer-reviewed journals. You produce precise, properly formatted \
characterization paragraphs following strict journal conventions.

FORMAT RULES:
- ACS style: ¹H NMR (frequency MHz, solvent): δ shift (mult, J = x Hz, nH, assignment); ...
- RSC style: Similar to ACS but uses ; between entries
- Wiley style: Similar but may use different notation

PRECISION RULES:
- ¹H shifts to 2 decimal places
- ¹³C shifts to 1 decimal place  
- J-coupling to 1 decimal place
- HRMS to 4 decimal places
- Include ALL data types provided

Respond with ONLY the characterization text, no JSON wrapper."""


def build_user_prompt(
    name: str = "",
    smiles: str = "",
    formula: str = "",
    h1_data: str = "",
    c13_data: str = "",
    ir_data: str = "",
    ms_data: str = "",
    uv_data: str = "",
    melting_point: str = "",
    elemental_analysis: str = "",
    journal_format: str = "ACS",
    verbosity: str = "standard",
) -> str:
    sections = [
        f"Generate a {journal_format}-format characterization paragraph.",
        f"Verbosity: {verbosity}",
        f"\nCompound: {name or 'Unknown'}",
    ]
    if formula:
        sections.append(f"Formula: {formula}")
    if h1_data:
        sections.append(f"\n¹H NMR data:\n{h1_data}")
    if c13_data:
        sections.append(f"\n¹³C NMR data:\n{c13_data}")
    if ir_data:
        sections.append(f"\nIR data:\n{ir_data}")
    if ms_data:
        sections.append(f"\nHRMS data:\n{ms_data}")
    if uv_data:
        sections.append(f"\nUV-Vis data:\n{uv_data}")
    if melting_point:
        sections.append(f"\nMelting point: {melting_point}")
    if elemental_analysis:
        sections.append(f"\nElemental analysis: {elemental_analysis}")

    return "\n".join(sections)
