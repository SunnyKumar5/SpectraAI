"""
Functional Group Checker — Cross-checks IR absorption bands against expected groups from structure.
"""

from __future__ import annotations

from ..core.molecule import Molecule
from ..core.ir_data import IRData, IR_FUNCTIONAL_GROUPS
from ..core.validation_report import ValidationCheck, CheckCategory, CheckStatus
from ..utils.smiles_utils import get_functional_groups, has_rdkit


class FunctionalGroupChecker:
    """Validates IR bands against functional groups expected from the molecular structure."""

    def check(self, molecule: Molecule, ir: IRData = None) -> ValidationCheck:
        if ir is None or not ir.absorptions:
            return ValidationCheck(
                name="Functional Groups (IR)",
                category=CheckCategory.FUNCTIONAL_GROUPS.value,
                status=CheckStatus.SKIPPED.value,
                explanation="No IR data provided",
            )

        if not molecule.has_smiles or not has_rdkit():
            return ValidationCheck(
                name="Functional Groups (IR)",
                category=CheckCategory.FUNCTIONAL_GROUPS.value,
                status=CheckStatus.SKIPPED.value,
                explanation="SMILES or RDKit not available for functional group detection",
            )

        expected_groups = get_functional_groups(molecule.smiles)
        if not expected_groups:
            return ValidationCheck(
                name="Functional Groups (IR)",
                category=CheckCategory.FUNCTIONAL_GROUPS.value,
                status=CheckStatus.PASS.value,
                score=85.0,
                expected="No specific groups detected from structure",
                observed=f"{ir.band_count} IR bands recorded",
                explanation="No specific functional groups to cross-check.",
            )

        found = []
        missing = []

        for group in expected_groups:
            if ir.has_functional_group(group, tolerance=40.0):
                found.append(group)
            else:
                missing.append(group)

        total = len(expected_groups)
        found_count = len(found)
        score = (found_count / total) * 100 if total > 0 else 100

        if not missing:
            return ValidationCheck(
                name="Functional Groups (IR)",
                category=CheckCategory.FUNCTIONAL_GROUPS.value,
                expected=", ".join(expected_groups),
                observed=f"All {found_count} groups detected",
                status=CheckStatus.PASS.value,
                score=score,
                explanation=f"All expected functional groups ({found_count}) have corresponding IR absorptions.",
            )
        elif len(missing) <= 1:
            return ValidationCheck(
                name="Functional Groups (IR)",
                category=CheckCategory.FUNCTIONAL_GROUPS.value,
                expected=", ".join(expected_groups),
                observed=f"{found_count}/{total} detected; missing: {', '.join(missing)}",
                status=CheckStatus.WARNING.value,
                score=max(score, 60.0),
                explanation=f"Missing IR band for: {', '.join(missing)}. May be overlapped or weak.",
                suggestion="Re-examine IR spectrum in the expected region for weak or broad bands.",
            )
        else:
            return ValidationCheck(
                name="Functional Groups (IR)",
                category=CheckCategory.FUNCTIONAL_GROUPS.value,
                expected=", ".join(expected_groups),
                observed=f"{found_count}/{total} detected; missing: {', '.join(missing)}",
                status=CheckStatus.FAIL.value,
                score=max(score, 15.0),
                explanation=f"Multiple expected functional groups not found in IR: {', '.join(missing)}.",
                suggestion="Verify the structure or re-acquire IR spectrum with better sample preparation.",
            )
