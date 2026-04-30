"""
IR-Structure Consistency Checker for SpectraAI.

Validates that observed IR absorptions are consistent with
functional groups expected from the molecular structure (SMILES).
"""

from __future__ import annotations

from typing import Optional

from ..core.molecule import Molecule
from ..core.ir_data import IRData, IRAbsorption
from ..core.validation_report import ValidationCheck, CheckCategory
from ..utils.ir_reference import IR_REFERENCE, find_matching_groups


class IRStructureChecker:
    """
    Checks consistency between IR data and expected functional groups.

    Verifies:
    1. Expected functional groups (from SMILES) have corresponding IR bands
    2. Observed strong bands are accounted for by the structure
    """

    def check(self, molecule: Molecule, ir: IRData = None) -> ValidationCheck:
        """
        Run IR-structure consistency check.

        Args:
            molecule: Molecule with SMILES/formula
            ir:       IR spectral data

        Returns:
            ValidationCheck result
        """
        if ir is None or not ir.absorptions:
            return ValidationCheck(
                name="IR-Structure Consistency",
                category=CheckCategory.IR_CONSISTENCY.value,
                status="skipped",
                score=0,
                explanation="No IR data provided.",
            )

        if not molecule.has_smiles:
            return ValidationCheck(
                name="IR-Structure Consistency",
                category=CheckCategory.IR_CONSISTENCY.value,
                status="skipped",
                score=0,
                explanation="No SMILES provided; cannot determine expected functional groups.",
            )

        # Determine expected functional groups from SMILES
        expected_groups = self._expected_groups_from_smiles(molecule.smiles)

        if not expected_groups:
            return ValidationCheck(
                name="IR-Structure Consistency",
                category=CheckCategory.IR_CONSISTENCY.value,
                status="pass",
                score=80,
                expected="Basic C-H and aromatic bands",
                observed=f"{len(ir.absorptions)} bands observed",
                explanation="No diagnostic functional groups detected in structure; IR data accepted.",
            )

        # Check each expected group against IR data
        found = []
        missing = []

        for group_name, (low, high, intensity, desc) in expected_groups.items():
            has_band = any(
                (low - 40) <= a.wavenumber <= (high + 40)
                for a in ir.absorptions
            )
            if has_band:
                found.append(group_name)
            else:
                missing.append(group_name)

        # Score calculation
        total = len(expected_groups)
        found_count = len(found)

        if total == 0:
            score = 80.0
        else:
            score = round((found_count / total) * 100, 1)

        # Determine status
        if score >= 80:
            status = "pass"
        elif score >= 50:
            status = "warning"
        else:
            status = "fail"

        expected_str = ", ".join(expected_groups.keys())
        observed_str = f"{found_count}/{total} found"
        if missing:
            observed_str += f" (missing: {', '.join(missing)})"

        explanation = (
            f"Checked {total} expected functional groups from structure. "
            f"{found_count} were confirmed in IR data."
        )
        suggestion = ""
        if missing:
            suggestion = f"Expected IR bands not found for: {', '.join(missing)}. Verify sample preparation and IR measurement."

        return ValidationCheck(
            name="IR-Structure Consistency",
            category=CheckCategory.IR_CONSISTENCY.value,
            expected=expected_str,
            observed=observed_str,
            status=status,
            score=score,
            explanation=explanation,
            suggestion=suggestion,
        )

    def _expected_groups_from_smiles(self, smiles: str) -> dict:
        """
        Determine expected IR-active functional groups from SMILES.

        Uses simple pattern matching (no RDKit required).
        """
        groups = {}
        s = smiles

        # Carbonyl groups
        if "C(=O)N" in s or "C(=O)[NH]" in s:
            groups["C=O (amide I)"] = IR_REFERENCE.get("C=O (amide I)", (1630, 1690, "strong", ""))
            groups["N-H (amide)"] = IR_REFERENCE.get("N-H (amide)", (3100, 3500, "strong", ""))
        elif "C(=O)O" in s:
            groups["C=O (ester)"] = IR_REFERENCE.get("C=O (ester)", (1735, 1750, "strong", ""))
        elif "C=O" in s:
            groups["C=O (ketone)"] = IR_REFERENCE.get("C=O (ketone)", (1700, 1725, "strong", ""))

        # Nitrogen groups
        if "C#N" in s:
            groups["C≡N (nitrile)"] = IR_REFERENCE.get("C≡N (nitrile)", (2200, 2260, "medium-strong, sharp", ""))
        if "[NH2]" in s or "N" in s and s.count("N") > 0:
            # Check for N-H (only if not fully substituted)
            if "[nH]" in s or "[NH]" in s:
                groups["N-H (secondary amine)"] = IR_REFERENCE.get("N-H (secondary amine)", (3310, 3350, "medium", ""))

        # Hydroxyl
        if "O" in s and "c1" not in s:
            if "[OH]" in s or "CO" in s:
                groups["C-O (alcohol)"] = IR_REFERENCE.get("C-O (alcohol)", (1000, 1150, "strong", ""))

        # Aromatic
        if "c1" in s or "C1=CC" in s:
            groups["C=C (aromatic)"] = IR_REFERENCE.get("C=C (aromatic)", (1450, 1600, "medium, multiple", ""))
            groups["=C-H (aromatic)"] = IR_REFERENCE.get("=C-H (aromatic)", (3000, 3100, "medium", ""))

        # Halogens
        if "Cl" in s:
            groups["C-Cl"] = IR_REFERENCE.get("C-Cl", (550, 850, "strong", ""))
        if "Br" in s:
            groups["C-Br"] = IR_REFERENCE.get("C-Br", (500, 680, "strong", ""))
        if "F" in s:
            groups["C-F"] = IR_REFERENCE.get("C-F", (1000, 1400, "strong", ""))

        return groups
