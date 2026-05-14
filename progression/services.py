from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from progression.models import PhaseDefinition, TitleDefinition
from rulesets.models import Ruleset


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
