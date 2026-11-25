"""Unified parsing orchestrator, overlap resolution, and normalized text builder."""

from __future__ import annotations

from collections.abc import Iterable

from paisa_parse.parsers.amount import parse_amounts
from paisa_parse.parsers.digits import parse_digits
from paisa_parse.parsers.ifsc import parse_ifsc
from paisa_parse.parsers.upi import parse_upi
from paisa_parse.policy import ConfirmPolicy
from paisa_parse.types import ConfirmAction, EntityType, ParsedEntity, ParseResult

_SPECIFICITY_RANK: dict[EntityType, int] = {
    EntityType.UPI_ID: 4,
    EntityType.IFSC: 3,
    EntityType.AMOUNT: 2,
    EntityType.DIGITS: 1,
}


def _overlaps(a: ParsedEntity, b: ParsedEntity) -> bool:
    return a.span.start < b.span.end and a.span.end > b.span.start


def _priority_key(entity: ParsedEntity) -> tuple[int, int, int, float]:
    span_len = entity.span.end - entity.span.start
    if entity.kind == EntityType.AMOUNT:
        has_scale_or_curr = bool(
            entity.metadata.get("has_scale") or entity.metadata.get("has_currency")
        )
        # An amount with explicit scale/currency outranks DIGITS on overlap;
        # a bare context-only number yields to a longer spoken DIGITS sequence.
        amt_boost = 1 if has_scale_or_curr else 0
    else:
        amt_boost = 1
    return (
        _SPECIFICITY_RANK[entity.kind] + (1 if amt_boost and entity.kind == EntityType.AMOUNT else 0),
        span_len,
        1 if entity.metadata.get("known_handle") or entity.metadata.get("known_bank") else 0,
        entity.confidence,
    )


def _resolve_overlaps(candidates: list[ParsedEntity]) -> list[ParsedEntity]:
    """Resolve overlapping entity spans deterministically by specificity and length."""
    ordered = sorted(candidates, key=_priority_key, reverse=True)
    accepted: list[ParsedEntity] = []
    for cand in ordered:
        if any(_overlaps(cand, kept) for kept in accepted):
            continue
        accepted.append(cand)
    accepted.sort(key=lambda e: e.span.start)
    return accepted


def _build_normalized_text(text: str, entities: list[ParsedEntity]) -> str:
    if not entities:
        return text
    parts: list[str] = []
    cursor = 0
    for ent in entities:
        if ent.span.start < cursor:
            continue
        parts.append(text[cursor : ent.span.start])
        if ent.action == ConfirmAction.REPROMPT:
            parts.append(ent.span.raw)
        else:
            parts.append(ent.formatted)
        cursor = ent.span.end
    parts.append(text[cursor:])
    return "".join(parts)


def parse(
    text: str,
    *,
    policy: ConfirmPolicy | None = None,
    kinds: Iterable[EntityType | str] | None = None,
) -> ParseResult:
    """Parse all Hinglish/Indian-English financial entities from `text`.

    Args:
        text: Input transcript or user message.
        policy: Confirmation policy; defaults to `ConfirmPolicy.balanced()`.
        kinds: Optional subset of entity types to extract.
    """
    active_policy = policy if policy is not None else ConfirmPolicy.balanced()
    allowed: set[EntityType] | None = (
        {EntityType(k) for k in kinds} if kinds is not None else None
    )

    def want(kind: EntityType) -> bool:
        return allowed is None or kind in allowed

    candidates: list[ParsedEntity] = []
    if want(EntityType.UPI_ID):
        candidates.extend(parse_upi(text))
    if want(EntityType.IFSC):
        candidates.extend(parse_ifsc(text))

    # Suppress amount/digit candidates that collide with already-found UPI/IFSC spans
    structured_spans = [(e.span.start, e.span.end) for e in candidates]

    def hits_structured(ent: ParsedEntity) -> bool:
        return any(ent.span.start < se and ent.span.end > ss for ss, se in structured_spans)

    if want(EntityType.AMOUNT):
        candidates.extend(e for e in parse_amounts(text) if not hits_structured(e))
    if want(EntityType.DIGITS):
        candidates.extend(e for e in parse_digits(text) if not hits_structured(e))

    resolved = _resolve_overlaps(candidates)
    evaluated = [active_policy.evaluate(ent) for ent in resolved]
    normalized = _build_normalized_text(text, evaluated)

    return ParseResult(
        text=text,
        entities=tuple(evaluated),
        normalized_text=normalized,
    )


def parse_amount(text: str, *, policy: ConfirmPolicy | None = None) -> list[ParsedEntity]:
    """Convenience wrapper returning evaluated AMOUNT entities."""
    return list(parse(text, policy=policy, kinds=(EntityType.AMOUNT,)).entities)


def parse_digit_strings(text: str, *, policy: ConfirmPolicy | None = None) -> list[ParsedEntity]:
    """Convenience wrapper returning evaluated DIGITS entities."""
    return list(parse(text, policy=policy, kinds=(EntityType.DIGITS,)).entities)


def parse_upi_ids(text: str, *, policy: ConfirmPolicy | None = None) -> list[ParsedEntity]:
    """Convenience wrapper returning evaluated UPI_ID entities."""
    return list(parse(text, policy=policy, kinds=(EntityType.UPI_ID,)).entities)


def parse_ifsc_codes(text: str, *, policy: ConfirmPolicy | None = None) -> list[ParsedEntity]:
    """Convenience wrapper returning evaluated IFSC entities."""
    return list(parse(text, policy=policy, kinds=(EntityType.IFSC,)).entities)
