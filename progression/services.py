from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from progression.models import PhaseDefinition, TitleDefinition
from rulesets.models import Ruleset


@dataclass(frozen=True)
class ProgressionFact:
    kind: str
    key: str
    amount: int | float | None = None
    completed: bool = False


@dataclass(frozen=True)
class TitleSummary:
    key: str
    name: str
    category: str
    requirements: list[dict[str, Any]]
    effects: list[dict[str, Any]]


@dataclass(frozen=True)
class PhaseUnlockSummary:
    key: str
    name: str
    unlock_type: str
    description: str
    data: dict[str, Any]


@dataclass(frozen=True)
class PhaseSummary:
    key: str
    name: str
    description: str
    requirements: list[dict[str, Any]]
    unlocks: list[PhaseUnlockSummary]


@dataclass(frozen=True)
class RequirementStatus:
    requirement: dict[str, Any]
    status: str
    current: int | float | bool | None
    target: int | float | bool | None
    missing: int | float | None

    @property
    def is_met(self) -> bool:
        return self.status == "met"


def latest_ruleset() -> Ruleset | None:
    return Ruleset.objects.order_by("-imported_at", "-id").first()


def title_catalog(ruleset: Ruleset) -> list[TitleSummary]:
    return [
        TitleSummary(
            key=title.key,
            name=title.name,
            category=title.category,
            requirements=title.requirements,
            effects=title.effects,
        )
        for title in TitleDefinition.objects.filter(ruleset=ruleset)
    ]


def phase_catalog(ruleset: Ruleset) -> list[PhaseSummary]:
    phases = PhaseDefinition.objects.filter(ruleset=ruleset).prefetch_related("unlocks")
    return [_phase_summary(phase) for phase in phases]


def next_phase(ruleset: Ruleset, current_phase_key: str | None = None) -> PhaseSummary | None:
    phases = list(PhaseDefinition.objects.filter(ruleset=ruleset).prefetch_related("unlocks"))
    if not phases:
        return None
    if current_phase_key is None:
        return _phase_summary(phases[0])

    for index, phase in enumerate(phases):
        if phase.key == current_phase_key:
            if index + 1 >= len(phases):
                return None
            return _phase_summary(phases[index + 1])
    return _phase_summary(phases[0])


def phase_requirement_statuses(
    phase: PhaseSummary | PhaseDefinition,
    facts: list[ProgressionFact],
) -> list[RequirementStatus]:
    fact_map = {(fact.kind, fact.key): fact for fact in facts}
    requirements = phase.requirements
    return [_requirement_status(requirement, fact_map) for requirement in requirements]


def _phase_summary(phase: PhaseDefinition) -> PhaseSummary:
    return PhaseSummary(
        key=phase.key,
        name=phase.name,
        description=phase.description,
        requirements=phase.requirements,
        unlocks=[
            PhaseUnlockSummary(
                key=unlock.key,
                name=unlock.name,
                unlock_type=unlock.unlock_type,
                description=unlock.description,
                data=unlock.data,
            )
            for unlock in phase.unlocks.all()
        ],
    )


def _requirement_status(
    requirement: dict[str, Any],
    fact_map: dict[tuple[str, str], ProgressionFact],
) -> RequirementStatus:
    kind = requirement.get("kind")
    key = requirement.get("key", "")
    if not kind:
        return RequirementStatus(
            requirement=requirement,
            status="unknown",
            current=None,
            target=None,
            missing=None,
        )

    fact = fact_map.get((kind, key))
    target = requirement.get("amount")
    if target is None:
        current = bool(fact and fact.completed)
        return RequirementStatus(
            requirement=requirement,
            status="met" if current else "missing",
            current=current,
            target=True,
            missing=None,
        )

    current = fact.amount if fact and fact.amount is not None else 0
    missing = max(target - current, 0)
    return RequirementStatus(
        requirement=requirement,
        status="met" if missing == 0 else "missing",
        current=current,
        target=target,
        missing=missing,
    )
