from telegram_knowledge_base.domain.tagging import (
    EffectiveTag,
    TagAssignment,
    TagOrigin,
    merge_effective_tags,
    preview_context_assignments,
)


def test_empty_context_preview_has_no_assignments() -> None:
    assert (
        preview_context_assignments([], minimum_confidence=0.8, blocked=frozenset())
        == ()
    )


def test_same_tag_is_visible_once_with_all_origins_preserved() -> None:
    assignments = [
        TagAssignment("1001", 1, 7, TagOrigin.MANUAL),
        TagAssignment("1001", 1, 7, TagOrigin.RULE),
        TagAssignment("1001", 1, 7, TagOrigin.CONTEXT, 0.92),
    ]

    assert merge_effective_tags(assignments) == (
        EffectiveTag(
            7,
            frozenset({TagOrigin.MANUAL, TagOrigin.RULE, TagOrigin.CONTEXT}),
            0.92,
        ),
    )


def test_manual_block_excludes_only_selected_post_tag_from_context_preview() -> None:
    blocked_assignment = TagAssignment("1001", 1, 7, TagOrigin.CONTEXT, 0.95)
    other_assignment = TagAssignment("1001", 2, 7, TagOrigin.CONTEXT, 0.90)

    assert preview_context_assignments(
        [blocked_assignment, other_assignment],
        minimum_confidence=0.8,
        blocked=frozenset({("1001", 1, 7)}),
    ) == (other_assignment,)


def test_context_preview_accepts_threshold_and_deduplicates_maximum_batch() -> None:
    threshold_match = TagAssignment("1001", 1, 7, TagOrigin.CONTEXT, 0.8)
    below_threshold = TagAssignment("1001", 2, 7, TagOrigin.CONTEXT, 0.79)
    repeated = [threshold_match] * 500 + [below_threshold]

    assert preview_context_assignments(
        repeated, minimum_confidence=0.8, blocked=frozenset()
    ) == (threshold_match,)
