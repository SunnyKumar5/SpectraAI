"""
Retrosynthetic Analysis Prompt Template.

Uses LLM to plan multi-step retrosynthetic routes with:
  - Strategic bond disconnections
  - Transform identification (named reactions)
  - Starting material availability assessment
  - Route scoring (step count, yield estimate, complexity)
  - Alternative route comparison
"""

SYSTEM_PROMPT = """\
You are an expert synthetic organic chemist specializing in retrosynthetic analysis.
Given a target molecule (SMILES), you design practical synthetic routes by:

1. **Strategic Disconnections**: Identify the best bonds to break, working backwards
   from the target to commercially available starting materials.
2. **Transform Selection**: For each disconnection, name the forward reaction
   (named reactions preferred) and specify conditions.
3. **Route Optimization**: Consider step economy, atom economy, protecting group
   strategies, stereochemistry control, and green chemistry principles.
4. **Starting Material Assessment**: Evaluate commercial availability and cost.
5. **Alternative Routes**: Provide 2-3 different retrosynthetic strategies ranked
   by practicality.

Use valid SMILES for all intermediates. Be specific about reagents and conditions.
Consider functional group compatibility and chemoselectivity.

Respond ONLY with a valid JSON object."""


def build_user_prompt(
    smiles: str,
    name: str = "",
    formula: str = "",
    scaffold_family: str = "",
    constraints: str = "",
    max_steps: int = 8,
    num_routes: int = 3,
) -> str:
    sections = []
    sections.append(f"Target Molecule SMILES: {smiles}")
    if name:
        sections.append(f"Name: {name}")
    if formula:
        sections.append(f"Formula: {formula}")
    if scaffold_family:
        sections.append(f"Scaffold Family: {scaffold_family}")
    if constraints:
        sections.append(f"Constraints: {constraints}")

    sections.append(f"""
Design up to {num_routes} retrosynthetic routes (max {max_steps} steps each).
Return JSON:
{{
  "target": {{
    "smiles": "{smiles}",
    "name": "<name or description>",
    "complexity_score": <float 0-100>
  }},
  "routes": [
    {{
      "route_id": <int>,
      "route_name": "<descriptive name, e.g. 'Suzuki-Buchwald Route'>",
      "strategy": "<brief strategy description>",
      "overall_score": <float 0-100>,
      "estimated_overall_yield": "<percentage range>",
      "total_steps": <int>,
      "key_advantages": ["<why this route is good>"],
      "key_risks": ["<potential problems>"],
      "steps": [
        {{
          "step_number": <int>,
          "reaction_name": "<named reaction or reaction type>",
          "reaction_class": "<coupling|cyclization|functionalization|protection|deprotection|oxidation|reduction|other>",
          "reactant_smiles": ["<SMILES of reactants>"],
          "product_smiles": "<SMILES of product>",
          "reagents": ["<reagents and catalysts>"],
          "conditions": {{
            "solvent": "<solvent>",
            "temperature": "<temp>",
            "time": "<duration>",
            "atmosphere": "<air|N2|Ar if relevant>"
          }},
          "estimated_yield": "<percentage range>",
          "difficulty": "<easy|moderate|challenging>",
          "notes": "<key considerations, selectivity issues, etc.>",
          "atom_economy": <float 0-100>,
          "green_score": <float 0-100>
        }}
      ],
      "starting_materials": [
        {{
          "smiles": "<SMILES>",
          "name": "<common name>",
          "availability": "<commercial|common|specialty|needs_synthesis>",
          "estimated_cost": "<cheap|moderate|expensive>"
        }}
      ]
    }}
  ],
  "comparison": {{
    "recommended_route": <route_id>,
    "reasoning": "<why this route is preferred>",
    "comparison_table": [
      {{
        "route_id": <int>,
        "steps": <int>,
        "est_yield": "<overall yield>",
        "cost": "<relative cost>",
        "difficulty": "<easy|moderate|hard>",
        "scalability": "<good|moderate|poor>"
      }}
    ]
  }},
  "key_disconnections": [
    {{
      "bond": "<description of bond broken>",
      "type": "<C-C|C-N|C-O|C-S|ring>",
      "strategy": "<functional group interconversion|disconnection|ring opening>",
      "forward_reaction": "<named reaction>"
    }}
  ]
}}""")
    return "\n".join(sections)
