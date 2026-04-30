"""
TautomerEnumerator -- Enumerate tautomers using RDKit.

Returns a ranked list of tautomer dicts with SMILES, SVG, score,
and human-readable description.
"""

from __future__ import annotations

from typing import Optional


class TautomerEnumerator:
    """Enumerate tautomers of a molecule using RDKit."""

    def enumerate(self, smiles: str, max_tautomers: int = 8) -> list[dict]:
        """
        Return a list of tautomer dicts sorted by RDKit stability score.

        Each dict: {smiles, svg, rank, score, description}
        Always returns at least one entry (the input molecule).
        """
        try:
            from rdkit import Chem
            from rdkit.Chem.MolStandardize import rdMolStandardize

            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                return [self._fallback(smiles)]

            enumerator = rdMolStandardize.TautomerEnumerator()
            tauts = enumerator.Enumerate(mol)

            results = []
            seen = set()
            for t_mol in tauts:
                t_smi = Chem.MolToSmiles(t_mol)
                if t_smi in seen:
                    continue
                seen.add(t_smi)
                score = enumerator.ScoreTautomer(t_mol)
                svg = self._mol_to_svg(t_mol)
                results.append({
                    "smiles": t_smi,
                    "svg": svg,
                    "rank": 0,  # set below
                    "score": score,
                    "description": "",
                })
                if len(results) >= max_tautomers:
                    break

            # Sort by score (higher = more stable in RDKit convention)
            results.sort(key=lambda x: x["score"], reverse=True)

            # Assign ranks and descriptions
            if results:
                canonical = results[0]["smiles"]
                for i, r in enumerate(results):
                    r["rank"] = i + 1
                    if i == 0:
                        r["description"] = "Most stable (canonical)"
                    else:
                        r["description"] = self._describe_difference(canonical, r["smiles"])

            return results if results else [self._fallback(smiles)]

        except Exception:
            return [self._fallback(smiles)]

    def _fallback(self, smiles: str) -> dict:
        return {
            "smiles": smiles,
            "svg": None,
            "rank": 1,
            "score": 0.0,
            "description": "Original structure",
        }

    def _mol_to_svg(self, mol) -> Optional[str]:
        try:
            from rdkit.Chem import Draw
            svg = Draw.MolToImage(mol, size=(120, 120))
            # MolToImage returns PIL Image, not SVG. Use MolsToGridImage for SVG
            from rdkit.Chem.Draw import rdMolDraw2D
            drawer = rdMolDraw2D.MolDraw2DSVG(120, 120)
            drawer.DrawMolecule(mol)
            drawer.FinishDrawing()
            return drawer.GetDrawingText()
        except Exception:
            return None

    def _describe_difference(self, canonical_smi: str, taut_smi: str) -> str:
        """Generate a brief description of how this tautomer differs."""
        try:
            from rdkit import Chem
            mol1 = Chem.MolFromSmiles(canonical_smi)
            mol2 = Chem.MolFromSmiles(taut_smi)
            if mol1 is None or mol2 is None:
                return "Alternative tautomer"

            # Count NH and OH groups
            nh1 = len(mol1.GetSubstructMatches(Chem.MolFromSmarts("[#7H]")))
            nh2 = len(mol2.GetSubstructMatches(Chem.MolFromSmarts("[#7H]")))
            oh1 = len(mol1.GetSubstructMatches(Chem.MolFromSmarts("[OH]")))
            oh2 = len(mol2.GetSubstructMatches(Chem.MolFromSmarts("[OH]")))

            parts = []
            if nh2 != nh1:
                parts.append(f"NH: {nh1}->{nh2}")
            if oh2 != oh1:
                parts.append(f"OH: {oh1}->{oh2}")
            if parts:
                return "Proton shift: " + ", ".join(parts)
            return "Alternative tautomer"
        except Exception:
            return "Alternative tautomer"
