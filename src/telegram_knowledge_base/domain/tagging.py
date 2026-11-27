from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum


class TagOrigin(StrEnum):
    MANUAL = "manual"
    RULE = "rule"
    CONTEXT = "context"


@dataclass(frozen=True, slots=True)
class TagAssignment:
    source_id: str
    message_id: int
    tag_id: int
    origin: TagOrigin
    confidence: float | None = None


@dataclass(frozen=True, slots=True)
class EffectiveTag:
    tag_id: int
    origins: frozenset[TagOrigin]
    confidence: float | None = None


def merge_effective_tags(
    assignments: Iterable[TagAssignment],
) -> tuple[EffectiveTag, ...]:
    del assignments
    raise NotImplementedError("Effective tag merging is not implemented yet.")


def preview_context_assignments(
    assignments: Iterable[TagAssignment],
    *,
    minimum_confidence: float,
    blocked: frozenset[tuple[str, int, int]],
) -> tuple[TagAssignment, ...]:
    del assignments, minimum_confidence, blocked
    raise NotImplementedError("Context tag preview is not implemented yet.")
