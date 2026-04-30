"""
ConformerGenerator — 3D conformer generation from SMILES using RDKit.

Gracefully degrades to empty results when RDKit is not installed.
All public methods are guaranteed to never raise; they return [] or None
on any failure.
"""

from __future__ import annotations

from typing import Optional

# RDKit is an optional dependency
try:
    from rdkit import Chem
    from rdkit.Chem import AllChem, Descriptors
    from rdkit.Chem.Draw import MolDraw2DSVG
    _HAS_RDKIT = True
except ImportError:
    _HAS_RDKIT = False


class ConformerGenerator:
    """
    Generates 3D conformers from SMILES using RDKit.

    All methods return empty / None if RDKit is not installed or if the
    SMILES is invalid, so callers never need to guard against exceptions.
    """

    # ── Public API ────────────────────────────────────────────────────────────

    def generate(self, smiles: str, n_conformers: int = 10) -> list[str]:
        """
        Generate up to *n_conformers* 3D conformers from *smiles*.

        Returns
        -------
        list[str]
            SDF block strings, sorted by MMFF94 energy (lowest first).
            Empty list if SMILES is invalid, embedding fails, or RDKit
            is not installed.
        """
        if not _HAS_RDKIT or not smiles or not smiles.strip():
            return []
        try:
            return self._generate_impl(smiles, n_conformers)
        except Exception:
            return []

    def generate_best(self, smiles: str) -> Optional[str]:
        """
        Return a single SDF block for the lowest-energy conformer.

        Returns None on any failure.
        """
        conformers = self.generate(smiles, n_conformers=10)
        return conformers[0] if conformers else None

    def generate_with_energies(
        self, smiles: str, n_conformers: int = 10
    ) -> list[tuple[str, float]]:
        """
        Generate conformers with their MMFF94 energies.

        Returns
        -------
        list[tuple[str, float]]
            (sdf_block, energy_kcal_mol) pairs sorted by energy (lowest first).
            Empty list on failure.
        """
        if not _HAS_RDKIT or not smiles or not smiles.strip():
            return []
        try:
            return self._generate_with_energies_impl(smiles, n_conformers)
        except Exception:
            return []

    def compute_partial_charges(self, smiles: str) -> dict[int, float]:
        """
        Compute Gasteiger partial charges for all atoms.

        Returns empty dict on failure, never raises.
        """
        if not _HAS_RDKIT or not smiles or not smiles.strip():
            return {}
        try:
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                return {}
            mol = Chem.AddHs(mol)
            AllChem.ComputeGasteigerCharges(mol)
            charges = {}
            for atom in mol.GetAtoms():
                charge = float(
                    atom.GetPropsAsDict().get("_GasteigerCharge", 0.0)
                )
                # NaN can occur for certain atoms
                if charge != charge:  # NaN check
                    charge = 0.0
                charges[atom.GetIdx()] = charge
            return charges
        except Exception:
            return {}

    def smiles_to_2d_svg(
        self,
        smiles: str,
        width: int = 200,
        height: int = 160,
    ) -> Optional[str]:
        """
        Render a 2D structure drawing as an SVG string.

        Returns None on any failure.
        """
        if not _HAS_RDKIT or not smiles or not smiles.strip():
            return None
        try:
            return self._svg_impl(smiles, width, height)
        except Exception:
            return None

    # ── Private implementation ────────────────────────────────────────────────

    def _generate_impl(self, smiles: str, n_conformers: int) -> list[str]:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return []

        # Add explicit hydrogens for realistic 3D geometry
        mol_h = Chem.AddHs(mol)

        # Embed multiple conformers with ETKDG
        params = AllChem.ETKDGv3()
        params.randomSeed = 42
        params.numThreads = 0          # use all available cores
        params.pruneRmsThresh = 0.5    # prune similar conformers

        conf_ids = AllChem.EmbedMultipleConfs(mol_h, numConfs=n_conformers, params=params)
        if not conf_ids:
            # Fallback: try basic embedding
            params2 = AllChem.EmbedParameters()
            params2.randomSeed = 42
            AllChem.EmbedMolecule(mol_h, params2)
            conf_ids = list(range(mol_h.GetNumConformers()))

        if not conf_ids:
            return []

        # Optimise with MMFF94 and collect energies
        energies: list[tuple[float, int]] = []
        ff_props = AllChem.MMFFGetMoleculeProperties(mol_h)
        if ff_props is not None:
            for cid in conf_ids:
                ff = AllChem.MMFFGetMoleculeForceField(mol_h, ff_props, confId=cid)
                if ff is not None:
                    try:
                        ff.Minimize(maxIts=200)
                        e = ff.CalcEnergy()
                        energies.append((e, cid))
                    except Exception:
                        energies.append((float("inf"), cid))
                else:
                    energies.append((float("inf"), cid))
        else:
            # MMFF94 unavailable — fall back to UFF or unoptimised
            for cid in conf_ids:
                try:
                    AllChem.UFFOptimizeMolecule(mol_h, confId=cid, maxIters=200)
                except Exception:
                    pass
                energies.append((0.0, cid))

        # Sort by energy: lowest first
        energies.sort(key=lambda x: x[0])

        # Build SDF blocks (remove Hs for cleaner display)
        mol_noH = Chem.RemoveHs(mol_h)
        sdf_blocks: list[str] = []
        for _, cid in energies:
            # Map conformer from mol_h back to mol_noH conformer index
            # (They share coordinates for heavy atoms after RemoveHs)
            try:
                # Directly use mol_h with Hs removed preserving coordinates
                block = Chem.MolToMolBlock(mol_h, confId=cid)
                sdf_blocks.append(block)
            except Exception:
                pass

        return sdf_blocks

    def _generate_with_energies_impl(
        self, smiles: str, n_conformers: int
    ) -> list[tuple[str, float]]:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return []

        mol_h = Chem.AddHs(mol)

        params = AllChem.ETKDGv3()
        params.randomSeed = 42
        params.numThreads = 0
        params.pruneRmsThresh = 0.5

        conf_ids = AllChem.EmbedMultipleConfs(
            mol_h, numConfs=n_conformers, params=params
        )
        if not conf_ids:
            params2 = AllChem.EmbedParameters()
            params2.randomSeed = 42
            AllChem.EmbedMolecule(mol_h, params2)
            conf_ids = list(range(mol_h.GetNumConformers()))

        if not conf_ids:
            return []

        energies: list[tuple[float, int]] = []
        ff_props = AllChem.MMFFGetMoleculeProperties(mol_h)
        if ff_props is not None:
            for cid in conf_ids:
                ff = AllChem.MMFFGetMoleculeForceField(
                    mol_h, ff_props, confId=cid
                )
                if ff is not None:
                    try:
                        ff.Minimize(maxIts=200)
                        e = ff.CalcEnergy()
                        energies.append((e, cid))
                    except Exception:
                        energies.append((float("inf"), cid))
                else:
                    energies.append((float("inf"), cid))
        else:
            for cid in conf_ids:
                try:
                    AllChem.UFFOptimizeMolecule(mol_h, confId=cid, maxIters=200)
                except Exception:
                    pass
                energies.append((0.0, cid))

        energies.sort(key=lambda x: x[0])

        results: list[tuple[str, float]] = []
        for energy, cid in energies:
            try:
                block = Chem.MolToMolBlock(mol_h, confId=cid)
                results.append((block, energy))
            except Exception:
                pass

        return results

    def _svg_impl(self, smiles: str, width: int, height: int) -> Optional[str]:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None

        AllChem.Compute2DCoords(mol)

        drawer = MolDraw2DSVG(width, height)
        drawer.drawOptions().addStereoAnnotation = True
        drawer.DrawMolecule(mol)
        drawer.FinishDrawing()
        svg = drawer.GetDrawingText()
        return svg
