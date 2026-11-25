"""Core data structures for paisa-parse."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any


class EntityType(str, Enum):
    """Supported Indian spoken financial entity types."""

    AMOUNT = "amount"
    DIGITS = "digits"
    UPI_ID = "upi_id"
    IFSC = "ifsc"


class ConfirmAction(str, Enum):
    """Recommended voice-agent confirmation policy action."""

    ACCEPT = "accept"
    CONFIRM = "confirm"
    REPROMPT = "reprompt"


def _decimal_to_json(value: Decimal) -> tuple[int | float, str]:
    """Convert a Decimal into a JSON-friendly number and exact non-scientific string."""
    if value == value.to_integral_value():
        as_int = int(value)
        return as_int, str(as_int)
    text = f"{value:f}".rstrip("0").rstrip(".")
    return float(value), text


@dataclass(frozen=True)
class EntitySpan:
    """Character offsets and raw substring of a parsed entity in the original input."""

    start: int
    end: int
    raw: str

    def to_dict(self) -> dict[str, Any]:
        return {"start": self.start, "end": self.end, "raw": self.raw}


@dataclass(frozen=True)
class ParsedEntity:
    """Structured financial entity extracted from spoken/written Hinglish text."""

    kind: EntityType
    value: Decimal | str
    formatted: str
    confidence: float
    span: EntitySpan
    action: ConfirmAction = ConfirmAction.ACCEPT
    confirm_prompt: str | None = None
    reasons: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        if isinstance(self.value, Decimal):
            val_json, val_str = _decimal_to_json(self.value)
        else:
            val_json, val_str = self.value, self.value
        return {
            "kind": self.kind.value,
            "value": val_json,
            "value_str": val_str,
            "formatted": self.formatted,
            "confidence": round(self.confidence, 4),
            "span": self.span.to_dict(),
            "action": self.action.value,
            "confirm_prompt": self.confirm_prompt,
            "reasons": list(self.reasons),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class ParseResult:
    """Top-level output of `paisa_parse.parse()`."""

    text: str
    entities: tuple[ParsedEntity, ...]
    normalized_text: str

    def by_kind(self, kind: EntityType | str) -> tuple[ParsedEntity, ...]:
        target = EntityType(kind)
        return tuple(e for e in self.entities if e.kind == target)

    def best(self, kind: EntityType | str | None = None) -> ParsedEntity | None:
        pool = self.by_kind(kind) if kind is not None else self.entities
        if not pool:
            return None
        return max(pool, key=lambda e: (e.confidence, e.span.end - e.span.start))

    def needs_confirmation(self) -> bool:
        return any(e.action in (ConfirmAction.CONFIRM, ConfirmAction.REPROMPT) for e in self.entities)

    def needs_reprompt(self) -> bool:
        return any(e.action == ConfirmAction.REPROMPT for e in self.entities)

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "normalized_text": self.normalized_text,
            "needs_confirmation": self.needs_confirmation(),
            "needs_reprompt": self.needs_reprompt(),
            "entities": [e.to_dict() for e in self.entities],
        }
