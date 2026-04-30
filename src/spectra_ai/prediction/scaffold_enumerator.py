"""
Scaffold Enumerator for SpectraAI.

Generates candidate molecular structures by systematically varying
substituents on a given heterocyclic scaffold. Used in the structure
prediction pipeline to create a ranked list of plausible products.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..core.prediction_result import StructureCandidate


# ── Common substituents for heterocycle decoration ────────────────────────────

SUBSTITUENT_LIBRARY: dict[str, list[tuple[str, str]]] = {
    # (SMILES fragment, display name)
    "aryl": [
        ("c1ccccc1", "phenyl"),
        ("c1ccc(OC)cc1", "4-methoxyphenyl"),
        ("c1ccc(C)cc1", "4-methylphenyl"),
        ("c1ccc(Cl)cc1", "4-chlorophenyl"),
        ("c1ccc(F)cc1", "4-fluorophenyl"),
        ("c1ccc([N+](=O)[O-])cc1", "4-nitrophenyl"),
        ("c1ccc(O)cc1", "4-hydroxyphenyl"),
        ("c1ccc2ccccc2c1", "2-naphthyl"),
    ],
    "alkyl": [
        ("C", "methyl"),
        ("CC", "ethyl"),
        ("C(C)C", "isopropyl"),
        ("C(C)(C)C", "tert-butyl"),
        ("CC(=O)", "acetyl"),
    ],
    "amino": [
        ("N", "amino"),
        ("NC", "methylamino"),
        ("N(C)C", "dimethylamino"),
        ("NC(=O)C", "acetylamino"),
        ("Nc1ccccc1", "phenylamino"),
    ],
    "heteroaryl": [
        ("c1ccncc1", "4-pyridyl"),
        ("c1ccoc1", "2-furyl"),
        ("c1ccsc1", "2-thienyl"),
        ("c1c[nH]cn1", "1H-imidazol-4-yl"),
    ],
}

# ── Scaffold SMILES templates with R-group placeholders ──────────────────────
# [R1], [R2], [R3] indicate substitution positions

SCAFFOLD_TEMPLATES: dict[str, dict] = {
    "imidazopyridine": {
        "core": "c1ccn2c([R1])c([R2])nc2c1",
        "positions": {"R1": "C-2", "R2": "C-3"},
        "default_sub_types": {"R1": "aryl", "R2": "aryl"},
        "display_name": "Imidazo[1,2-a]pyridine",
    },
    "indole": {
        "core": "c1ccc2[nH]c([R1])c([R2])c2c1",
        "positions": {"R1": "C-2", "R2": "C-3"},
        "default_sub_types": {"R1": "aryl", "R2": "alkyl"},
        "display_name": "1H-Indole",
    },
    "quinazoline": {
        "core": "c1ccc2nc([R1])nc([R2])c2c1",
        "positions": {"R1": "C-2", "R2": "C-4"},
        "default_sub_types": {"R1": "amino", "R2": "aryl"},
        "display_name": "Quinazoline",
    },
    "triazole": {
        "core": "c1nn([R1])c([R2])n1",
        "positions": {"R1": "N-1", "R2": "C-4"},
        "default_sub_types": {"R1": "alkyl", "R2": "aryl"},
        "display_name": "1,2,3-Triazole",
    },
    "pyrazolopyrimidine": {
        "core": "c1cc2c([R1])nn([R2])c2nc1",
        "positions": {"R1": "C-3", "R2": "N-1"},
        "default_sub_types": {"R1": "aryl", "R2": "alkyl"},
        "display_name": "Pyrazolo[1,5-a]pyrimidine",
    },
    "coumarin": {
        "core": "O=c1cc([R1])c2ccccc2o1",
        "positions": {"R1": "C-3"},
        "default_sub_types": {"R1": "aryl"},
        "display_name": "Coumarin",
    },
}


class ScaffoldEnumerator:
    """
    Enumerates candidate molecules by combining scaffold templates
    with substituent libraries.

    Usage:
        enumerator = ScaffoldEnumerator()
        candidates = enumerator.enumerate("imidazopyridine", max_candidates=20)
    """

    def enumerate(
        self,
        scaffold_family: str,
        substituent_types: Optional[dict[str, str]] = None,
        max_candidates: int = 25,
    ) -> list[StructureCandidate]:
        """
        Generate candidate structures for a scaffold.

        Args:
            scaffold_family:   Key into SCAFFOLD_TEMPLATES
            substituent_types: Override default substituent types per position
                               e.g. {"R1": "aryl", "R2": "amino"}
            max_candidates:    Maximum number to generate

        Returns:
            List of StructureCandidate objects (unranked, confidence=0)
        """
        template = SCAFFOLD_TEMPLATES.get(scaffold_family)
        if not template:
            return []

        core_smiles = template["core"]
        positions = template["positions"]
        sub_types = substituent_types or template.get("default_sub_types", {})

        # Build substituent pools per position
        pools: dict[str, list[tuple[str, str]]] = {}
        for r_group, sub_type in sub_types.items():
            pool = SUBSTITUENT_LIBRARY.get(sub_type, [])
            if pool:
                pools[r_group] = pool

        if not pools:
            return []

        candidates = []
        r_groups = sorted(pools.keys())

        if len(r_groups) == 1:
            rg = r_groups[0]
            for smi, name in pools[rg]:
                full_smiles = core_smiles.replace(f"[{rg}]", f"({smi})")
                cand_name = f"{template['display_name']}, {positions[rg]}={name}"
                candidates.append(StructureCandidate(
                    rank=0,
                    smiles=full_smiles,
                    name=cand_name,
                    scaffold_family=scaffold_family,
                    confidence=0.0,
                    explanation=f"Enumerated: {positions[rg]} = {name}",
                ))
                if len(candidates) >= max_candidates:
                    break

        elif len(r_groups) >= 2:
            r1, r2 = r_groups[0], r_groups[1]
            for smi1, name1 in pools[r1]:
                for smi2, name2 in pools[r2]:
                    full_smiles = core_smiles.replace(f"[{r1}]", f"({smi1})")
                    full_smiles = full_smiles.replace(f"[{r2}]", f"({smi2})")
                    cand_name = (
                        f"{template['display_name']}, "
                        f"{positions[r1]}={name1}, {positions[r2]}={name2}"
                    )
                    candidates.append(StructureCandidate(
                        rank=0,
                        smiles=full_smiles,
                        name=cand_name,
                        scaffold_family=scaffold_family,
                        confidence=0.0,
                        explanation=(
                            f"Enumerated: {positions[r1]}={name1}, "
                            f"{positions[r2]}={name2}"
                        ),
                    ))
                    if len(candidates) >= max_candidates:
                        break
                if len(candidates) >= max_candidates:
                    break

        return candidates[:max_candidates]

    def get_scaffold_names(self) -> list[str]:
        """Return all available scaffold family keys."""
        return list(SCAFFOLD_TEMPLATES.keys())

    def get_scaffold_info(self, scaffold_family: str) -> Optional[dict]:
        """Return template information for a scaffold."""
        return SCAFFOLD_TEMPLATES.get(scaffold_family)
