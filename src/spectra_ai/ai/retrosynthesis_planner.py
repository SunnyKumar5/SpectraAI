"""
Retrosynthesis Planner — AI-powered retrosynthetic route design.

Uses LLM to plan multi-step synthetic routes with strategic disconnections,
named reactions, condition optimization, and starting material assessment.
"""

from __future__ import annotations

from typing import Optional

from .llm_client import LLMClient
from .prompts import retrosynthesis


class RetrosynthesisPlanner:
    """AI-powered retrosynthetic analysis engine."""

    def __init__(self, client: LLMClient):
        self.client = client

    def plan(
        self,
        smiles: str,
        name: str = "",
        formula: str = "",
        scaffold_family: str = "",
        constraints: str = "",
        max_steps: int = 8,
        num_routes: int = 3,
    ) -> Optional[dict]:
        """
        Design retrosynthetic routes for a target molecule.

        Returns parsed JSON dict with target, routes (each with steps),
        comparison, and key_disconnections.
        Returns None if the AI call fails.
        """
        user_prompt = retrosynthesis.build_user_prompt(
            smiles=smiles,
            name=name,
            formula=formula,
            scaffold_family=scaffold_family,
            constraints=constraints,
            max_steps=max_steps,
            num_routes=num_routes,
        )

        result = self.client.generate_json(
            system=retrosynthesis.SYSTEM_PROMPT,
            user=user_prompt,
            temperature=0.3,
            max_tokens=8000,
        )
        return result
