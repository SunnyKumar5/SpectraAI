"""
Validation report models for SpectraAI.

Holds individual validation check results and the overall confidence
score with radar chart data for the validation dashboard.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class CheckStatus(str, Enum):
    """Status of a single validation check."""
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"
    SKIPPED = "skipped"     # Not enough data to run this check
    PENDING = "pending"     # Not yet evaluated

    @property
    def icon(self) -> str:
        return {
            "pass": "✅",
            "warning": "⚠️",
            "fail": "❌",
            "skipped": "⏭️",
            "pending": "⏳",
        }[self.value]

    @property
    def color(self) -> str:
        return {
            "pass": "#22c55e",
            "warning": "#f59e0b",
            "fail": "#ef4444",
            "skipped": "#6b7280",
            "pending": "#8b949e",
        }[self.value]


class CheckCategory(str, Enum):
    """Categories for grouping validation checks."""
    CARBON_COUNT = "Carbon Count"
    PROTON_COUNT = "Proton Count"
    FUNCTIONAL_GROUPS = "Functional Groups"
    MOLECULAR_SYMMETRY = "Symmetry"
    MASS_SPEC = "Mass Spectrometry"
    IR_CONSISTENCY = "IR Consistency"
    CROSS_SPECTRAL = "Cross-Spectral"
    CHEMICAL_SHIFT = "Chemical Shifts"


@dataclass
class ValidationCheck:
    """
    Result of a single validation check.

    Attributes:
        name:         Human-readable check name
        category:     Check category for grouping
        expected:     What was expected (string representation)
        observed:     What was observed (string representation)
        status:       Pass / Warning / Fail
        score:        Numeric score (0–100) for this check
        explanation:  Detailed explanation of the result
        suggestion:   Suggested action if warning/fail
    """

    name: str
    category: str = ""
    expected: str = ""
    observed: str = ""
    status: str = CheckStatus.PENDING.value
    score: float = 0.0
    explanation: str = ""
    suggestion: str = ""

    @property
    def status_enum(self) -> CheckStatus:
        try:
            return CheckStatus(self.status)
        except ValueError:
            return CheckStatus.PENDING

    @property
    def is_passing(self) -> bool:
        return self.status == CheckStatus.PASS.value

    @property
    def is_warning(self) -> bool:
        return self.status == CheckStatus.WARNING.value

    @property
    def is_failing(self) -> bool:
        return self.status == CheckStatus.FAIL.value

    @property
    def icon(self) -> str:
        return self.status_enum.icon

    @property
    def color(self) -> str:
        return self.status_enum.color

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "category": self.category,
            "expected": self.expected,
            "observed": self.observed,
            "status": self.status,
            "score": self.score,
            "explanation": self.explanation,
            "suggestion": self.suggestion,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ValidationCheck":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ValidationReport:
    """
    Complete validation report containing all check results.

    Attributes:
        checks:          List of individual validation check results
        overall_score:   Aggregate confidence score (0–100)
        summary:         AI-generated natural language summary
        radar_data:      Per-category scores for radar chart display
        pass_count:      Number of passing checks
        warning_count:   Number of warning checks
        fail_count:      Number of failing checks
    """

    checks: list[ValidationCheck] = field(default_factory=list)
    overall_score: float = 0.0
    summary: str = ""
    radar_data: dict = field(default_factory=dict)

    @property
    def pass_count(self) -> int:
        return sum(1 for c in self.checks if c.is_passing)

    @property
    def warning_count(self) -> int:
        return sum(1 for c in self.checks if c.is_warning)

    @property
    def fail_count(self) -> int:
        return sum(1 for c in self.checks if c.is_failing)

    @property
    def skipped_count(self) -> int:
        return sum(1 for c in self.checks if c.status == CheckStatus.SKIPPED.value)

    @property
    def total_checks(self) -> int:
        return len(self.checks)

    @property
    def active_checks(self) -> int:
        """Number of checks that were actually evaluated (not skipped)."""
        return self.total_checks - self.skipped_count

    @property
    def overall_status(self) -> str:
        """Determine overall status from individual checks."""
        if self.fail_count > 0:
            return "fail"
        elif self.warning_count > 0:
            return "warning"
        elif self.pass_count > 0:
            return "pass"
        return "pending"

    @property
    def overall_status_label(self) -> str:
        labels = {
            "fail": "Issues Detected",
            "warning": "Minor Concerns",
            "pass": "All Checks Passed",
            "pending": "Not Yet Evaluated",
        }
        return labels.get(self.overall_status, "Unknown")

    @property
    def overall_color(self) -> str:
        colors = {
            "fail": "#ef4444",
            "warning": "#f59e0b",
            "pass": "#22c55e",
            "pending": "#8b949e",
        }
        return colors.get(self.overall_status, "#8b949e")

    def calculate_overall_score(self) -> float:
        """
        Calculate the weighted overall confidence score.

        Weights:
          - Carbon count:        15%
          - Proton count:        15%
          - Functional groups:   15%
          - Mass spec:           20%
          - IR consistency:      10%
          - Chemical shifts:     15%
          - Cross-spectral:      10%
        """
        weights = {
            CheckCategory.CARBON_COUNT.value: 0.15,
            CheckCategory.PROTON_COUNT.value: 0.15,
            CheckCategory.FUNCTIONAL_GROUPS.value: 0.15,
            CheckCategory.MASS_SPEC.value: 0.20,
            CheckCategory.IR_CONSISTENCY.value: 0.10,
            CheckCategory.CHEMICAL_SHIFT.value: 0.15,
            CheckCategory.CROSS_SPECTRAL.value: 0.10,
        }

        weighted_sum = 0.0
        weight_total = 0.0

        for check in self.checks:
            if check.status == CheckStatus.SKIPPED.value:
                continue
            w = weights.get(check.category, 0.1)
            weighted_sum += check.score * w
            weight_total += w

        if weight_total > 0:
            self.overall_score = round(weighted_sum / weight_total, 1)
        else:
            self.overall_score = 0.0

        return self.overall_score

    def build_radar_data(self) -> dict:
        """Build per-category scores for radar chart display."""
        category_scores = {}
        category_counts = {}

        for check in self.checks:
            if check.status == CheckStatus.SKIPPED.value:
                continue
            cat = check.category or "Other"
            if cat not in category_scores:
                category_scores[cat] = 0.0
                category_counts[cat] = 0
            category_scores[cat] += check.score
            category_counts[cat] += 1

        self.radar_data = {
            cat: round(category_scores[cat] / category_counts[cat], 1)
            for cat in category_scores
            if category_counts[cat] > 0
        }
        return self.radar_data

    def get_checks_by_status(self, status: str) -> list[ValidationCheck]:
        """Filter checks by status."""
        return [c for c in self.checks if c.status == status]

    def get_checks_by_category(self, category: str) -> list[ValidationCheck]:
        """Filter checks by category."""
        return [c for c in self.checks if c.category == category]

    def to_dict(self) -> dict:
        return {
            "checks": [c.to_dict() for c in self.checks],
            "overall_score": self.overall_score,
            "summary": self.summary,
            "radar_data": self.radar_data,
            "pass_count": self.pass_count,
            "warning_count": self.warning_count,
            "fail_count": self.fail_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ValidationReport":
        checks = [ValidationCheck.from_dict(c) for c in data.get("checks", [])]
        report = cls(
            checks=checks,
            overall_score=data.get("overall_score", 0.0),
            summary=data.get("summary", ""),
            radar_data=data.get("radar_data", {}),
        )
        return report
