"""
SpectraAI Database Generator
=============================

Offline script that calls the Claude API to generate structured JSON databases
for the reaction-aware spectral intelligence features.

Generates 5 database types:
  1. Reaction Templates       -> data/reaction_templates/
  2. Scaffold Shift References -> data/shift_references/
  3. Byproduct Library         -> data/byproduct_library/
  4. Regioisomer Discrimination -> data/regioisomer_discrimination/
  5. Cascade Intermediates     -> data/cascade_intermediates/

Usage:
  python scripts/generate_databases.py --all
  python scripts/generate_databases.py --reactions
  python scripts/generate_databases.py --shifts
  python scripts/generate_databases.py --byproducts
  python scripts/generate_databases.py --regioisomers
  python scripts/generate_databases.py --cascades
  python scripts/generate_databases.py --validate-only
  python scripts/generate_databases.py --dry-run   (print prompts, don't call API)

Requirements:
  pip install anthropic rdkit   (rdkit-pypi on PyPI)

Environment:
  ANTHROPIC_API_KEY must be set.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
#  Paths
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

# Load .env file if it exists (so we don't need dotenv dependency)
_env_file = PROJECT_ROOT / ".env"
if _env_file.exists():
    for line in _env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip()
            if key and value and key not in os.environ:
                os.environ[key] = value
DATA_DIR = PROJECT_ROOT / "src" / "spectra_ai" / "data"

OUT_DIRS = {
    "reactions":     DATA_DIR / "reaction_templates",
    "shifts":        DATA_DIR / "shift_references",
    "byproducts":    DATA_DIR / "byproduct_library",
    "regioisomers":  DATA_DIR / "regioisomer_discrimination",
    "cascades":      DATA_DIR / "cascade_intermediates",
}

# Create output dirs
for d in OUT_DIRS.values():
    d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
#  Target Reactions  (~30 reactions relevant to heterocyclic chemistry)
# ---------------------------------------------------------------------------

TARGET_REACTIONS = [
    # --- Multicomponent Reactions ---
    {
        "id": "RXN-001", "name": "Groebke-Blackburn-Bienayme (GBB) MCR",
        "class": "multicomponent",
        "reactants": "2-aminopyridine + aldehyde + isocyanide",
        "product": "imidazo[1,2-a]pyridine",
        "catalyst": "ZnCl2 or Sc(OTf)3",
    },
    {
        "id": "RXN-002", "name": "Ugi Four-Component Reaction",
        "class": "multicomponent",
        "reactants": "amine + aldehyde + carboxylic acid + isocyanide",
        "product": "alpha-acylaminoamide",
        "catalyst": "none (MeOH, rt)",
    },
    {
        "id": "RXN-003", "name": "Biginelli Reaction",
        "class": "multicomponent",
        "reactants": "aldehyde + urea + beta-ketoester",
        "product": "dihydropyrimidinone (DHPM)",
        "catalyst": "HCl or FeCl3",
    },
    {
        "id": "RXN-004", "name": "Hantzsch Pyridine Synthesis",
        "class": "multicomponent",
        "reactants": "aldehyde + 2 equiv beta-ketoester + ammonium acetate",
        "product": "1,4-dihydropyridine then pyridine",
        "catalyst": "AcOH / thermal",
    },
    {
        "id": "RXN-005", "name": "Passerini Three-Component Reaction",
        "class": "multicomponent",
        "reactants": "aldehyde + carboxylic acid + isocyanide",
        "product": "alpha-acyloxyamide",
        "catalyst": "none (neat or DCM)",
    },
    {
        "id": "RXN-006", "name": "van Leusen Oxazole Synthesis",
        "class": "multicomponent",
        "reactants": "aldehyde + TosMIC + amine (or direct)",
        "product": "oxazole",
        "catalyst": "K2CO3",
    },

    # --- Click Chemistry ---
    {
        "id": "RXN-007", "name": "CuAAC (Copper-Catalyzed Azide-Alkyne Cycloaddition)",
        "class": "cycloaddition",
        "reactants": "organic azide + terminal alkyne",
        "product": "1,4-disubstituted 1,2,3-triazole",
        "catalyst": "CuSO4 / sodium ascorbate",
    },
    {
        "id": "RXN-008", "name": "RuAAC (Ruthenium-Catalyzed AAC)",
        "class": "cycloaddition",
        "reactants": "organic azide + terminal alkyne",
        "product": "1,5-disubstituted 1,2,3-triazole",
        "catalyst": "Cp*RuCl(PPh3)2",
    },
    {
        "id": "RXN-009", "name": "Thermal [3+2] Huisgen Cycloaddition",
        "class": "cycloaddition",
        "reactants": "organic azide + alkyne (terminal or internal)",
        "product": "mixture of 1,4- and 1,5-triazole regioisomers",
        "catalyst": "thermal (no catalyst)",
    },

    # --- Cross-Coupling ---
    {
        "id": "RXN-010", "name": "Suzuki-Miyaura Cross-Coupling",
        "class": "cross_coupling",
        "reactants": "aryl halide + arylboronic acid",
        "product": "biaryl",
        "catalyst": "Pd(PPh3)4 / Pd(dppf)Cl2",
    },
    {
        "id": "RXN-011", "name": "Sonogashira Coupling",
        "class": "cross_coupling",
        "reactants": "aryl halide + terminal alkyne",
        "product": "aryl alkyne",
        "catalyst": "PdCl2(PPh3)2 / CuI",
    },
    {
        "id": "RXN-012", "name": "Buchwald-Hartwig Amination",
        "class": "cross_coupling",
        "reactants": "aryl halide + amine",
        "product": "arylamine (diarylamine, aryl-heterocycle amine)",
        "catalyst": "Pd2(dba)3 / XPhos or BINAP",
    },
    {
        "id": "RXN-013", "name": "Ullmann C-N Coupling",
        "class": "cross_coupling",
        "reactants": "aryl halide + nitrogen nucleophile (amine, amide, azole)",
        "product": "N-aryl heterocycle",
        "catalyst": "CuI / 1,10-phenanthroline / Cs2CO3",
    },
    {
        "id": "RXN-014", "name": "Heck Reaction",
        "class": "cross_coupling",
        "reactants": "aryl halide + alkene",
        "product": "aryl-substituted alkene (stilbene-type)",
        "catalyst": "Pd(OAc)2 / PPh3 / Et3N",
    },
    {
        "id": "RXN-015", "name": "Stille Coupling",
        "class": "cross_coupling",
        "reactants": "aryl halide + organostannane",
        "product": "biaryl or aryl-vinyl",
        "catalyst": "Pd(PPh3)4",
    },
    {
        "id": "RXN-016", "name": "Negishi Coupling",
        "class": "cross_coupling",
        "reactants": "aryl halide + organozinc reagent",
        "product": "biaryl",
        "catalyst": "Pd(PPh3)4 or NiCl2(dppf)",
    },

    # --- C-H Functionalization ---
    {
        "id": "RXN-017", "name": "C-H Arylation of Imidazo[1,2-a]pyridine at C-3",
        "class": "ch_functionalization",
        "reactants": "imidazo[1,2-a]pyridine + aryl halide",
        "product": "3-arylimidazo[1,2-a]pyridine",
        "catalyst": "Pd(OAc)2 / Cu(OAc)2",
    },
    {
        "id": "RXN-018", "name": "C-H Sulfonylation of Imidazo[1,2-a]pyridine",
        "class": "ch_functionalization",
        "reactants": "imidazo[1,2-a]pyridine + sulfonyl chloride or sodium sulfinate",
        "product": "3-sulfonylimidazo[1,2-a]pyridine",
        "catalyst": "metal-free or Cu-catalyzed oxidative",
    },
    {
        "id": "RXN-019", "name": "C-H Halogenation of Heterocycles (NBS/NCS)",
        "class": "ch_functionalization",
        "reactants": "electron-rich heterocycle + NBS or NCS",
        "product": "C-3 halogenated heterocycle",
        "catalyst": "none (electrophilic)",
    },
    {
        "id": "RXN-020", "name": "Oxidative C-H/C-H Cross-Coupling of Heterocycles",
        "class": "ch_functionalization",
        "reactants": "two C-H bonds (e.g., indole + azole)",
        "product": "bi-heteroaryl (C2-C3 linked)",
        "catalyst": "Pd(OAc)2 / Ag2CO3 or Cu(OAc)2 / O2",
    },

    # --- Condensation / Cyclization ---
    {
        "id": "RXN-021", "name": "Fischer Indole Synthesis",
        "class": "cyclization",
        "reactants": "arylhydrazine + ketone/aldehyde",
        "product": "indole",
        "catalyst": "ZnCl2, AcOH, or p-TsOH",
    },
    {
        "id": "RXN-022", "name": "Niementowski Quinazoline Synthesis",
        "class": "condensation",
        "reactants": "anthranilic acid + formamide or amide",
        "product": "4(3H)-quinazolinone",
        "catalyst": "thermal (neat or AcOH)",
    },
    {
        "id": "RXN-023", "name": "Dimroth Rearrangement",
        "class": "rearrangement",
        "reactants": "aminotriazine or aminopyrimidine (thermal isomerization)",
        "product": "isomeric aminoheterocycle",
        "catalyst": "heat / base",
    },
    {
        "id": "RXN-024", "name": "Chichibabin Amination",
        "class": "nucleophilic_substitution",
        "reactants": "pyridine + NaNH2",
        "product": "2-aminopyridine",
        "catalyst": "NaNH2 (excess)",
    },
    {
        "id": "RXN-025", "name": "Knorr Pyrazole Synthesis",
        "class": "condensation",
        "reactants": "hydrazine + 1,3-diketone",
        "product": "pyrazole",
        "catalyst": "AcOH (acidic) or EtOH (neutral)",
    },

    # --- Cascade / Tandem ---
    {
        "id": "RXN-026", "name": "Ullmann Coupling + Intramolecular Cyclization Cascade",
        "class": "cascade",
        "reactants": "2-haloaryl substrate with tethered nucleophile",
        "product": "fused N-heterocycle (e.g., benzimidazole, carbazole)",
        "catalyst": "CuI / 1,10-phenanthroline / Cs2CO3",
    },
    {
        "id": "RXN-027", "name": "One-Pot Azidation + CuAAC Click",
        "class": "cascade",
        "reactants": "alkyl halide + NaN3 (in situ) + terminal alkyne",
        "product": "1,4-disubstituted triazole (one-pot)",
        "catalyst": "CuSO4 / NaAsc / DMSO-H2O",
    },
    {
        "id": "RXN-028", "name": "Tandem Buchwald-Hartwig / Cyclization",
        "class": "cascade",
        "reactants": "dihaloarene + diamine",
        "product": "benzimidazole or dihydroquinoxaline",
        "catalyst": "Pd(OAc)2 / XPhos / NaOtBu",
    },
    {
        "id": "RXN-029", "name": "Gewald Reaction",
        "class": "multicomponent",
        "reactants": "ketone + elemental sulfur + alpha-cyanoacetate",
        "product": "2-aminothiophene",
        "catalyst": "morpholine or Et3N",
    },
    {
        "id": "RXN-030", "name": "Doebner-Miller Quinoline Synthesis",
        "class": "condensation",
        "reactants": "aniline + alpha,beta-unsaturated aldehyde",
        "product": "2-substituted quinoline",
        "catalyst": "conc. HCl or p-TsOH",
    },
]

# ---------------------------------------------------------------------------
#  Target Scaffolds for Shift References (~20 scaffolds)
# ---------------------------------------------------------------------------

TARGET_SCAFFOLDS = [
    {"id": "SCAF-001", "name": "imidazo[1,2-a]pyridine", "smiles": "c1ccn2ccnc2c1"},
    {"id": "SCAF-002", "name": "1H-indole", "smiles": "c1ccc2[nH]ccc2c1"},
    {"id": "SCAF-003", "name": "1,2,3-triazole (1,4-disubstituted)", "smiles": "c1cnnn1"},
    {"id": "SCAF-004", "name": "quinazoline", "smiles": "c1ccc2ncncc2c1"},
    {"id": "SCAF-005", "name": "pyrazolo[1,5-a]pyrimidine", "smiles": "c1cc2cnnc2nc1"},
    {"id": "SCAF-006", "name": "quinoline", "smiles": "c1ccc2ncccc2c1"},
    {"id": "SCAF-007", "name": "isoquinoline", "smiles": "c1ccc2cnccc2c1"},
    {"id": "SCAF-008", "name": "benzimidazole", "smiles": "c1ccc2[nH]cnc2c1"},
    {"id": "SCAF-009", "name": "benzoxazole", "smiles": "c1ccc2ocnc2c1"},
    {"id": "SCAF-010", "name": "benzothiazole", "smiles": "c1ccc2scnc2c1"},
    {"id": "SCAF-011", "name": "pyrazole", "smiles": "c1cc[nH]n1"},
    {"id": "SCAF-012", "name": "imidazole", "smiles": "c1c[nH]cn1"},
    {"id": "SCAF-013", "name": "1,2,4-triazole", "smiles": "c1nc[nH]n1"},
    {"id": "SCAF-014", "name": "tetrazole", "smiles": "c1nnn[nH]1"},
    {"id": "SCAF-015", "name": "thiophene", "smiles": "c1ccsc1"},
    {"id": "SCAF-016", "name": "2-aminothiophene (Gewald product)", "smiles": "Nc1ccsc1"},
    {"id": "SCAF-017", "name": "4(3H)-quinazolinone", "smiles": "O=c1[nH]cnc2ccccc12"},
    {"id": "SCAF-018", "name": "dihydropyrimidinone (Biginelli)", "smiles": "O=C1NC(=O)CC(C)N1"},
    {"id": "SCAF-019", "name": "oxazole", "smiles": "c1cocn1"},
    {"id": "SCAF-020", "name": "1,3,4-oxadiazole", "smiles": "c1nnoc1"},
    {"id": "SCAF-021", "name": "carbazole", "smiles": "c1ccc2c(c1)[nH]c1ccccc12"},
    {"id": "SCAF-022", "name": "acridine", "smiles": "c1ccc2nc3ccccc3cc2c1"},
    {"id": "SCAF-023", "name": "pyrimidine", "smiles": "c1ccncn1"},
    {"id": "SCAF-024", "name": "pyridazine", "smiles": "c1ccnnc1"},
    {"id": "SCAF-025", "name": "pyrazine", "smiles": "c1cnccn1"},
]

# ---------------------------------------------------------------------------
#  Target Regioisomer Discrimination Entries (~12 entries)
# ---------------------------------------------------------------------------

TARGET_REGIOISOMERS = [
    {
        "id": "REG-001",
        "question": "C-3 vs C-5 arylation of imidazo[1,2-a]pyridine",
        "scaffold": "imidazo[1,2-a]pyridine",
    },
    {
        "id": "REG-002",
        "question": "C-2 vs C-3 substitution of indole",
        "scaffold": "indole",
    },
    {
        "id": "REG-003",
        "question": "1,4- vs 1,5-disubstituted 1,2,3-triazole (CuAAC vs RuAAC)",
        "scaffold": "1,2,3-triazole",
    },
    {
        "id": "REG-004",
        "question": "C-2 vs C-4 halogenation of quinoline",
        "scaffold": "quinoline",
    },
    {
        "id": "REG-005",
        "question": "N-1 vs C-3 alkylation of indole",
        "scaffold": "indole",
    },
    {
        "id": "REG-006",
        "question": "C-5 vs C-6 substitution of benzimidazole",
        "scaffold": "benzimidazole",
    },
    {
        "id": "REG-007",
        "question": "1,3- vs 1,5-disubstituted pyrazole (Knorr regiochemistry)",
        "scaffold": "pyrazole",
    },
    {
        "id": "REG-008",
        "question": "C-2 vs C-5 arylation of thiophene",
        "scaffold": "thiophene",
    },
    {
        "id": "REG-009",
        "question": "N-1 vs N-2 substitution of 1,2,4-triazole",
        "scaffold": "1,2,4-triazole",
    },
    {
        "id": "REG-010",
        "question": "C-3 vs C-5 sulfonylation of imidazo[1,2-a]pyridine",
        "scaffold": "imidazo[1,2-a]pyridine",
    },
    {
        "id": "REG-011",
        "question": "2- vs 4-aminoquinazoline from different amination routes",
        "scaffold": "quinazoline",
    },
    {
        "id": "REG-012",
        "question": "C-3 vs C-6 bromination of imidazo[1,2-a]pyridine (NBS)",
        "scaffold": "imidazo[1,2-a]pyridine",
    },
]

# ---------------------------------------------------------------------------
#  Target Cascade Entries (~8 entries)
# ---------------------------------------------------------------------------

TARGET_CASCADES = [
    {
        "id": "CAS-001",
        "cascade": "Ullmann C-N coupling -> intramolecular cyclization to benzimidazole",
        "reaction_ids": ["RXN-013", "RXN-026"],
    },
    {
        "id": "CAS-002",
        "cascade": "One-pot azidation -> CuAAC click to triazole",
        "reaction_ids": ["RXN-007", "RXN-027"],
    },
    {
        "id": "CAS-003",
        "cascade": "Tandem Buchwald-Hartwig amination -> cyclization to benzimidazole",
        "reaction_ids": ["RXN-012", "RXN-028"],
    },
    {
        "id": "CAS-004",
        "cascade": "Sonogashira coupling -> intramolecular cyclization to benzofuran",
        "reaction_ids": ["RXN-011"],
    },
    {
        "id": "CAS-005",
        "cascade": "GBB MCR: imine formation -> [4+1] cycloaddition with isocyanide -> aromatization",
        "reaction_ids": ["RXN-001"],
    },
    {
        "id": "CAS-006",
        "cascade": "Fischer indolization: enehydrazine -> [3,3]-sigmatropic -> aromatization",
        "reaction_ids": ["RXN-021"],
    },
    {
        "id": "CAS-007",
        "cascade": "Gewald: Knoevenagel -> sulfur incorporation -> cyclization to aminothiophene",
        "reaction_ids": ["RXN-029"],
    },
    {
        "id": "CAS-008",
        "cascade": "Hantzsch: Knoevenagel + enamine formation -> cyclocondensation -> oxidation to pyridine",
        "reaction_ids": ["RXN-004"],
    },
]


# ═══════════════════════════════════════════════════════════════════════════
#  Generation Prompts
# ═══════════════════════════════════════════════════════════════════════════

def _read_schema(db_type: str) -> str:
    """Read the JSON schema for a given database type."""
    schema_path = OUT_DIRS[db_type] / "_schema.json"
    if schema_path.exists():
        return schema_path.read_text(encoding="utf-8")
    return "(schema not found)"


def make_reaction_prompt(rxn: dict) -> str:
    schema = _read_schema("reactions")
    return f"""You are an expert synthetic organic chemist and spectroscopist. Generate a detailed Reaction Template database entry in JSON format.

REACTION TO DOCUMENT:
- ID: {rxn['id']}
- Name: {rxn['name']}
- Class: {rxn['class']}
- Reactants: {rxn['reactants']}
- Product scaffold: {rxn['product']}
- Typical catalyst: {rxn['catalyst']}

REQUIRED JSON SCHEMA:
{schema}

INSTRUCTIONS:
1. Provide a valid SMIRKS pattern for the core reaction transformation. Use atom-mapped SMIRKS where possible. If the reaction is too complex for a single SMIRKS, provide the most representative simplification and note limitations.

2. For reactant_roles, provide SMARTS patterns for each reactant class and 3-5 example SMILES.

3. For spectral_fingerprint, be VERY specific with chemical shift ranges based on real literature data:
   - diagnostic_h1: list 4-8 key proton signals with shift ranges, multiplicity, and diagnostic value
   - diagnostic_c13: list 4-8 key carbon signals with shift ranges and carbon types
   - diagnostic_ir: list 3-5 IR bands (present AND absent) that confirm the product
   - diagnostic_ms: list characteristic fragmentation patterns

4. For scope, list real functional group tolerances and substrate limitations.

5. For literature, provide 2-3 real references (use DOIs where possible).

6. Include 5-8 searchable tags.

OUTPUT: Return ONLY valid JSON matching the schema. No markdown fences, no commentary."""


def make_shift_reference_prompt(scaf: dict) -> str:
    schema = _read_schema("shifts")
    return f"""You are an expert NMR spectroscopist specializing in heterocyclic compounds. Generate a detailed Scaffold NMR Shift Reference entry in JSON format.

SCAFFOLD TO DOCUMENT:
- ID: {scaf['id']}
- Name: {scaf['name']}
- Core SMILES: {scaf['smiles']}

REQUIRED JSON SCHEMA:
{schema}

INSTRUCTIONS:
1. Map ALL ring positions with their atom types and properties.

2. For h1_shifts, provide for EACH proton-bearing position:
   - base_shift: the chemical shift in the unsubstituted parent scaffold
   - range: the range observed across literature examples
   - typical_multiplicity and J-coupling
   - substituent_effects: provide shift changes (delta_shift in ppm) for 5 important substituents:
     -OMe, -NO2, -Cl, -Ph, -COCH3. Include the position where the substituent is placed.
   - solvent_effects: provide shifts in CDCl3 and DMSO-d6

3. For c13_shifts, provide for EACH carbon position:
   - base_shift, range, carbon_type, DEPT phase
   - substituent_effects for 4 common substituents (-OMe, -NO2, -Cl, -Ph)

4. For ir_bands, list both present and absent diagnostic bands.

5. diagnostic_features: 4-6 human-readable notes for quick identification.

Use REAL chemical shift data from literature. Be quantitative with shift values.

OUTPUT: Return ONLY valid JSON matching the schema. No markdown fences, no commentary."""


def make_byproduct_prompt(rxn: dict) -> str:
    schema = _read_schema("byproducts")
    return f"""You are an expert synthetic organic chemist. Generate a detailed Byproduct Library entry in JSON format.

REACTION:
- ID: {rxn['id']}
- Name: {rxn['name']}
- Class: {rxn['class']}
- Reactants: {rxn['reactants']}
- Desired product: {rxn['product']}
- Catalyst: {rxn['catalyst']}

REQUIRED JSON SCHEMA:
{schema}

INSTRUCTIONS:
1. List 3-6 realistic byproducts/side products that can form in this reaction.

2. For each byproduct, provide:
   - Name and type (regioisomer, homocoupling, starting material, etc.)
   - SMILES template (use generic R groups where needed, e.g., [R] or *)
   - Mechanistic explanation of formation
   - Conditions that favor its formation
   - Frequency (common/occasional/rare) and typical amount
   - Detailed spectral signatures that distinguish it from the desired product:
     * h1_diagnostic: specific signals with shift ranges and how they differ from product
     * c13_diagnostic: key carbons that are different
     * ir_diagnostic: bands present or absent
     * ms_diagnostic: mass difference and characteristic fragments
   - How to confirm its identity
   - How to minimize its formation

3. Include general purity checks for this reaction class.

Be specific with chemical shift values based on real chemistry.

OUTPUT: Return ONLY valid JSON matching the schema. No markdown fences, no commentary."""


def make_regioisomer_prompt(entry: dict) -> str:
    schema = _read_schema("regioisomers")
    return f"""You are an expert NMR spectroscopist and heterocyclic chemist. Generate a detailed Regioisomer Discrimination entry in JSON format.

REGIOCHEMISTRY QUESTION:
- ID: {entry['id']}
- Question: {entry['question']}
- Scaffold: {entry['scaffold']}

REQUIRED JSON SCHEMA:
{schema}

INSTRUCTIONS:
1. Define 2 (or more) regioisomeric products with:
   - SMILES templates
   - Which is the major product and why (kinetic/thermodynamic/catalyst control)
   - Detailed 1H fingerprint: list 4-6 diagnostic signals per isomer with specific shift ranges
   - Detailed 13C fingerprint: list 4-6 diagnostic carbons per isomer
   - NOE evidence: which through-space correlations confirm each isomer
   - HMBC evidence: which 2-3 bond H->C correlations are diagnostic

2. For discrimination_strategy:
   - primary_method: the single most reliable way to tell them apart
   - key_differences: quantitative comparisons (shift A vs shift B, delta difference)
   - decision_tree: step-by-step procedure a chemist would follow
   - common_pitfalls: things that can mislead assignment

3. Literature precedent: cite 1-2 real examples where this regiochemistry was established.

Be very specific with shift values. The whole point is to enable automated assignment.

OUTPUT: Return ONLY valid JSON matching the schema. No markdown fences, no commentary."""


def make_cascade_prompt(entry: dict) -> str:
    schema = _read_schema("cascades")
    return f"""You are an expert synthetic organic chemist specializing in tandem/cascade reactions. Generate a detailed Cascade Intermediate entry in JSON format.

CASCADE REACTION:
- ID: {entry['id']}
- Cascade: {entry['cascade']}

REQUIRED JSON SCHEMA:
{schema}

INSTRUCTIONS:
1. Break the cascade into 2-4 discrete stages.

2. For each stage, provide:
   - Stage name and type
   - Input and output SMILES templates
   - Conditions specific to that stage
   - Detailed spectral fingerprint of the INTERMEDIATE (what you see if the cascade stops here):
     * h1_diagnostic: signals present in intermediate but absent in product (and vice versa)
     * c13_diagnostic: carbons that change between intermediate and product
     * ir_diagnostic: bands that appear/disappear
   - how_to_detect_stall: the key spectral evidence
   - how_to_push_forward: practical conditions to restart

3. For final_product:
   - SMILES template, scaffold family
   - key_spectral_confirmation: 3-4 signals that confirm full cascade completion

Be specific with chemical shift values. The goal is to let the AI detect whether a tandem reaction ran to completion or stalled at an intermediate.

OUTPUT: Return ONLY valid JSON matching the schema. No markdown fences, no commentary."""


# ═══════════════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════════════

import re as _re

def _safe_filename(raw: str, max_len: int = 40) -> str:
    """Sanitize a string for use as a filename component."""
    s = raw.lower()
    s = s.replace("->", "_to_")
    s = _re.sub(r"[^a-z0-9_]", "_", s)
    s = _re.sub(r"_+", "_", s).strip("_")
    return s[:max_len]


# ═══════════════════════════════════════════════════════════════════════════
#  RDKit Validation
# ═══════════════════════════════════════════════════════════════════════════

def validate_entry(entry: dict, db_type: str) -> list[str]:
    """Validate a generated entry. Returns list of warning strings (empty = OK)."""
    warnings = []

    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem
        HAS_RDKIT = True
    except ImportError:
        HAS_RDKIT = False
        warnings.append("RDKit not available — skipping chemical validation")

    # --- Common checks ---
    if not isinstance(entry, dict):
        warnings.append("Entry is not a JSON object")
        return warnings

    # --- Reaction-specific ---
    if db_type == "reactions" and HAS_RDKIT:
        smirks = entry.get("smirks", "")
        if smirks:
            try:
                rxn = AllChem.ReactionFromSmarts(smirks)
                if rxn is None:
                    warnings.append(f"SMIRKS parse failed: {smirks[:80]}")
                else:
                    n_reactants = rxn.GetNumReactantTemplates()
                    n_products = rxn.GetNumProductTemplates()
                    if n_products < 1:
                        warnings.append(f"SMIRKS has {n_products} product templates")
            except Exception as e:
                warnings.append(f"SMIRKS validation error: {e}")
        else:
            warnings.append("No SMIRKS provided")

        # Validate example SMILES in reactant_roles
        for role in entry.get("reactant_roles", []):
            for smi in role.get("examples", []):
                mol = Chem.MolFromSmiles(smi)
                if mol is None:
                    warnings.append(f"Invalid example SMILES in role '{role.get('role','')}': {smi}")

        # Validate core_smiles in product_scaffold
        core = entry.get("product_scaffold", {}).get("core_smiles", "")
        if core and Chem.MolFromSmiles(core) is None:
            warnings.append(f"Invalid core_smiles: {core}")

    # --- Shift references ---
    if db_type == "shifts" and HAS_RDKIT:
        core = entry.get("core_smiles", "")
        if core:
            mol = Chem.MolFromSmiles(core)
            if mol is None:
                warnings.append(f"Invalid core_smiles: {core}")

        # Check shift ranges are reasonable
        for pos, data in entry.get("h1_shifts", {}).items():
            r = data.get("range", [])
            if len(r) == 2:
                if r[0] < -2 or r[1] > 16:
                    warnings.append(f"H1 shift range out of bounds for {pos}: {r}")
                if r[0] > r[1]:
                    warnings.append(f"H1 shift range inverted for {pos}: {r}")

        for pos, data in entry.get("c13_shifts", {}).items():
            r = data.get("range", [])
            if len(r) == 2:
                if r[0] < -10 or r[1] > 230:
                    warnings.append(f"C13 shift range out of bounds for {pos}: {r}")
                if r[0] > r[1]:
                    warnings.append(f"C13 shift range inverted for {pos}: {r}")

    # --- Byproducts ---
    if db_type == "byproducts" and HAS_RDKIT:
        for bp in entry.get("byproducts", []):
            smi = bp.get("smiles_template", "")
            # Skip generic templates with wildcards
            if smi and "*" not in smi and "[R]" not in smi:
                mol = Chem.MolFromSmiles(smi)
                if mol is None:
                    warnings.append(f"Invalid byproduct SMILES: {smi}")

    # --- Check spectral data ranges ---
    def _check_h1_list(signals, context):
        for sig in signals:
            r = sig.get("shift_range", [])
            if len(r) == 2 and (r[0] < -2 or r[1] > 16 or r[0] > r[1]):
                warnings.append(f"Bad H1 range in {context}: {r}")

    def _check_c13_list(signals, context):
        for sig in signals:
            r = sig.get("shift_range", [])
            if len(r) == 2 and (r[0] < -10 or r[1] > 230 or r[0] > r[1]):
                warnings.append(f"Bad C13 range in {context}: {r}")

    if db_type == "reactions":
        fp = entry.get("spectral_fingerprint", {})
        _check_h1_list(fp.get("diagnostic_h1", []), "reaction fingerprint")
        _check_c13_list(fp.get("diagnostic_c13", []), "reaction fingerprint")

    if db_type == "regioisomers":
        for iso in entry.get("regioisomers", []):
            _check_h1_list(iso.get("h1_fingerprint", []), f"regioisomer {iso.get('label','')}")
            _check_c13_list(iso.get("c13_fingerprint", []), f"regioisomer {iso.get('label','')}")

    if db_type == "cascades":
        for stage in entry.get("stages", []):
            fp = stage.get("spectral_fingerprint", {})
            _check_h1_list(fp.get("h1_diagnostic", []), f"cascade stage {stage.get('stage_number','')}")
            _check_c13_list(fp.get("c13_diagnostic", []), f"cascade stage {stage.get('stage_number','')}")

    return warnings


# ═══════════════════════════════════════════════════════════════════════════
#  Claude API Client
# ═══════════════════════════════════════════════════════════════════════════

class DatabaseGenerator:
    """Calls Claude API to generate database entries."""

    MODEL = "claude-sonnet-4-20250514"
    MAX_TOKENS = 16384
    RETRY_LIMIT = 4
    RETRY_DELAY = 10  # seconds

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self._client = None
        if not dry_run:
            try:
                import anthropic
                self._client = anthropic.Anthropic()
            except ImportError:
                print("ERROR: `anthropic` package not installed. pip install anthropic")
                sys.exit(1)
            except Exception as e:
                print(f"ERROR: Could not init Anthropic client: {e}")
                sys.exit(1)

        self._stats = {"generated": 0, "failed": 0, "warnings": 0, "skipped": 0}

    def generate_json(self, prompt: str, entry_id: str) -> Optional[dict]:
        """Call Claude and parse the JSON response."""
        if self.dry_run:
            print(f"\n{'='*60}")
            print(f"[DRY RUN] Prompt for {entry_id}:")
            print(f"{'='*60}")
            print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
            return None

        for attempt in range(1, self.RETRY_LIMIT + 1):
            try:
                print(f"  Calling Claude API for {entry_id} (attempt {attempt})...", end=" ", flush=True)

                response = self._client.messages.create(
                    model=self.MODEL,
                    max_tokens=self.MAX_TOKENS,
                    temperature=0.3,
                    messages=[{"role": "user", "content": prompt}],
                )

                text = response.content[0].text.strip()

                # Strip markdown fences if present
                if text.startswith("```"):
                    lines = text.split("\n")
                    # Remove first and last lines (fences)
                    lines = [l for l in lines if not l.strip().startswith("```")]
                    text = "\n".join(lines)

                data = json.loads(text)
                print("OK")
                self._stats["generated"] += 1
                return data

            except json.JSONDecodeError as e:
                print(f"JSON parse error: {e}")
                if attempt < self.RETRY_LIMIT:
                    print(f"  Retrying in {self.RETRY_DELAY}s...")
                    time.sleep(self.RETRY_DELAY)
            except Exception as e:
                print(f"API error: {e}")
                if attempt < self.RETRY_LIMIT:
                    time.sleep(self.RETRY_DELAY * attempt)

        print(f"  FAILED after {self.RETRY_LIMIT} attempts for {entry_id}")
        self._stats["failed"] += 1
        return None

    def save_entry(self, data: dict, db_type: str, filename: str):
        """Validate and save a generated entry."""
        if data is None:
            return

        warnings = validate_entry(data, db_type)
        if warnings:
            self._stats["warnings"] += len(warnings)
            print(f"  Warnings for {filename}:")
            for w in warnings:
                print(f"    - {w}")

        out_path = OUT_DIRS[db_type] / filename
        out_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"  Saved: {out_path.relative_to(PROJECT_ROOT)}")

    def print_stats(self):
        print(f"\n{'='*60}")
        print(f"Generation Summary:")
        print(f"  Generated: {self._stats['generated']}")
        print(f"  Failed:    {self._stats['failed']}")
        print(f"  Warnings:  {self._stats['warnings']}")
        print(f"  Skipped:   {self._stats['skipped']}")
        print(f"{'='*60}")


# ═══════════════════════════════════════════════════════════════════════════
#  Generation Orchestrators
# ═══════════════════════════════════════════════════════════════════════════

def generate_reactions(gen: DatabaseGenerator, skip_existing: bool = True):
    """Generate all reaction template entries."""
    print(f"\n{'='*60}")
    print(f"Generating Reaction Templates ({len(TARGET_REACTIONS)} reactions)")
    print(f"{'='*60}")

    for rxn in TARGET_REACTIONS:
        filename = f"{rxn['id'].lower()}_{_safe_filename(rxn['name'])}.json"
        out_path = OUT_DIRS["reactions"] / filename

        if skip_existing and out_path.exists():
            print(f"  Skipping {rxn['id']} (already exists)")
            gen._stats["skipped"] += 1
            continue

        prompt = make_reaction_prompt(rxn)
        data = gen.generate_json(prompt, rxn["id"])
        gen.save_entry(data, "reactions", filename)

        # Rate limit
        if not gen.dry_run and data:
            time.sleep(8)


def generate_shifts(gen: DatabaseGenerator, skip_existing: bool = True):
    """Generate all scaffold shift reference entries."""
    print(f"\n{'='*60}")
    print(f"Generating Scaffold Shift References ({len(TARGET_SCAFFOLDS)} scaffolds)")
    print(f"{'='*60}")

    for scaf in TARGET_SCAFFOLDS:
        filename = f"{scaf['id'].lower()}_{_safe_filename(scaf['name'])}.json"
        out_path = OUT_DIRS["shifts"] / filename

        if skip_existing and out_path.exists():
            print(f"  Skipping {scaf['id']} (already exists)")
            gen._stats["skipped"] += 1
            continue

        prompt = make_shift_reference_prompt(scaf)
        data = gen.generate_json(prompt, scaf["id"])
        gen.save_entry(data, "shifts", filename)

        if not gen.dry_run and data:
            time.sleep(8)


def generate_byproducts(gen: DatabaseGenerator, skip_existing: bool = True):
    """Generate byproduct entries for all reactions."""
    print(f"\n{'='*60}")
    print(f"Generating Byproduct Library ({len(TARGET_REACTIONS)} reactions)")
    print(f"{'='*60}")

    for rxn in TARGET_REACTIONS:
        filename = f"byp_{rxn['id'].lower()}_{_safe_filename(rxn['name'], 35)}.json"
        out_path = OUT_DIRS["byproducts"] / filename

        if skip_existing and out_path.exists():
            print(f"  Skipping byproducts for {rxn['id']} (already exists)")
            gen._stats["skipped"] += 1
            continue

        prompt = make_byproduct_prompt(rxn)
        data = gen.generate_json(prompt, f"BYP-{rxn['id']}")
        gen.save_entry(data, "byproducts", filename)

        if not gen.dry_run and data:
            time.sleep(8)


def generate_regioisomers(gen: DatabaseGenerator, skip_existing: bool = True):
    """Generate regioisomer discrimination entries."""
    print(f"\n{'='*60}")
    print(f"Generating Regioisomer Discrimination ({len(TARGET_REGIOISOMERS)} entries)")
    print(f"{'='*60}")

    for entry in TARGET_REGIOISOMERS:
        filename = f"{entry['id'].lower()}_{_safe_filename(entry['scaffold'], 35)}.json"
        out_path = OUT_DIRS["regioisomers"] / filename

        if skip_existing and out_path.exists():
            print(f"  Skipping {entry['id']} (already exists)")
            gen._stats["skipped"] += 1
            continue

        prompt = make_regioisomer_prompt(entry)
        data = gen.generate_json(prompt, entry["id"])
        gen.save_entry(data, "regioisomers", filename)

        if not gen.dry_run and data:
            time.sleep(8)


def generate_cascades(gen: DatabaseGenerator, skip_existing: bool = True):
    """Generate cascade intermediate entries."""
    print(f"\n{'='*60}")
    print(f"Generating Cascade Intermediates ({len(TARGET_CASCADES)} entries)")
    print(f"{'='*60}")

    for entry in TARGET_CASCADES:
        filename = f"{entry['id'].lower()}_{_safe_filename(entry['cascade'])}.json"
        out_path = OUT_DIRS["cascades"] / filename

        if skip_existing and out_path.exists():
            print(f"  Skipping {entry['id']} (already exists)")
            gen._stats["skipped"] += 1
            continue

        prompt = make_cascade_prompt(entry)
        data = gen.generate_json(prompt, entry["id"])
        gen.save_entry(data, "cascades", filename)

        if not gen.dry_run and data:
            time.sleep(8)


# ═══════════════════════════════════════════════════════════════════════════
#  Validate Existing Entries
# ═══════════════════════════════════════════════════════════════════════════

def validate_all():
    """Validate all existing database entries."""
    print(f"\n{'='*60}")
    print("Validating All Database Entries")
    print(f"{'='*60}")

    total_files = 0
    total_warnings = 0

    for db_type, dir_path in OUT_DIRS.items():
        json_files = sorted(dir_path.glob("*.json"))
        json_files = [f for f in json_files if f.name != "_schema.json"]

        if not json_files:
            print(f"\n  {db_type}: (no entries)")
            continue

        print(f"\n  {db_type}: {len(json_files)} entries")
        for fp in json_files:
            total_files += 1
            try:
                data = json.loads(fp.read_text(encoding="utf-8"))
                warnings = validate_entry(data, db_type)
                if warnings:
                    total_warnings += len(warnings)
                    print(f"    {fp.name}: {len(warnings)} warning(s)")
                    for w in warnings:
                        print(f"      - {w}")
                else:
                    print(f"    {fp.name}: OK")
            except json.JSONDecodeError as e:
                total_warnings += 1
                print(f"    {fp.name}: INVALID JSON - {e}")

    print(f"\n  Total: {total_files} files, {total_warnings} warnings")


# ═══════════════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="SpectraAI Database Generator — Generate reaction/spectral reference databases using Claude API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/generate_databases.py --all                 # Generate everything
  python scripts/generate_databases.py --reactions --shifts   # Just reactions and shifts
  python scripts/generate_databases.py --dry-run --all        # Preview prompts
  python scripts/generate_databases.py --validate-only        # Validate existing files
  python scripts/generate_databases.py --all --force          # Regenerate even if exists
        """,
    )
    parser.add_argument("--all", action="store_true", help="Generate all 5 database types")
    parser.add_argument("--reactions", action="store_true", help="Generate reaction templates")
    parser.add_argument("--shifts", action="store_true", help="Generate scaffold shift references")
    parser.add_argument("--byproducts", action="store_true", help="Generate byproduct library")
    parser.add_argument("--regioisomers", action="store_true", help="Generate regioisomer discrimination")
    parser.add_argument("--cascades", action="store_true", help="Generate cascade intermediates")
    parser.add_argument("--validate-only", action="store_true", help="Only validate existing entries")
    parser.add_argument("--dry-run", action="store_true", help="Print prompts without calling API")
    parser.add_argument("--force", action="store_true", help="Regenerate even if file exists")
    parser.add_argument("--model", default=None, help="Override Claude model (default: claude-sonnet-4-20250514)")

    args = parser.parse_args()

    # If no specific type selected, show help
    if not any([args.all, args.reactions, args.shifts, args.byproducts,
                args.regioisomers, args.cascades, args.validate_only]):
        parser.print_help()
        return

    if args.validate_only:
        validate_all()
        return

    gen = DatabaseGenerator(dry_run=args.dry_run)
    if args.model:
        gen.MODEL = args.model

    skip = not args.force

    print(f"SpectraAI Database Generator")
    print(f"  Model: {gen.MODEL}")
    print(f"  Dry run: {gen.dry_run}")
    print(f"  Skip existing: {skip}")
    print(f"  Output: {DATA_DIR.relative_to(PROJECT_ROOT)}")

    try:
        if args.all or args.reactions:
            generate_reactions(gen, skip_existing=skip)

        if args.all or args.shifts:
            generate_shifts(gen, skip_existing=skip)

        if args.all or args.byproducts:
            generate_byproducts(gen, skip_existing=skip)

        if args.all or args.regioisomers:
            generate_regioisomers(gen, skip_existing=skip)

        if args.all or args.cascades:
            generate_cascades(gen, skip_existing=skip)

    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")

    gen.print_stats()

    # Run validation on everything we generated
    if not gen.dry_run and gen._stats["generated"] > 0:
        print("\nRunning validation on generated entries...")
        validate_all()


if __name__ == "__main__":
    main()
