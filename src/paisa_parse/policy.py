"""Confidence thresholds and voice-agent confirm-back readback policy."""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Literal

from paisa_parse.lexicon import amount_to_words_en_in
from paisa_parse.types import ConfirmAction, EntityType, ParsedEntity

_SPOKEN_DIGIT_EN = {
    "0": "zero",
    "1": "one",
    "2": "two",
    "3": "three",
    "4": "four",
    "5": "five",
    "6": "six",
    "7": "seven",
    "8": "eight",
    "9": "nine",
}


def _spell_digits(digits: str) -> str:
    return " ".join(_SPOKEN_DIGIT_EN.get(ch, ch) for ch in digits)


def _spell_ifsc(code: str) -> str:
    bank = " ".join(code[:4])
    rest = " ".join(_SPOKEN_DIGIT_EN.get(ch, ch) for ch in code[4:])
    return f"{bank} {rest}"


def _spell_upi(upi_id: str) -> str:
    if "@" not in upi_id:
        return upi_id
    user, handle = upi_id.split("@", 1)
    spoken_user = user.replace(".", " dot ").replace("_", " underscore ").replace("-", " dash ")
    return f"{spoken_user} at {handle}"


def build_confirm_prompt(
    entity: ParsedEntity,
    action: ConfirmAction,
    language: Literal["en-IN", "hinglish"],
) -> str | None:
    """Build a natural TTS-ready confirm-back or reprompt string."""
    if action == ConfirmAction.ACCEPT:
        return None

    if action == ConfirmAction.REPROMPT:
        if language == "hinglish":
            prompts = {
                EntityType.AMOUNT: "Maaf kijiye, amount clear nahi hua. Kitne rupaye bhejne hain, dobara bataiye?",
                EntityType.DIGITS: "Maaf kijiye, number poora nahi mila. Kripya poore digits ek-ek karke bataiye?",
                EntityType.UPI_ID: "Maaf kijiye, UPI ID samajh nahi aayi. Kripya apni UPI ID dobara bataiye?",
                EntityType.IFSC: "Maaf kijiye, IFSC code 11 characters ka nahi lag raha. Kripya 11-character IFSC dobara bataiye?",
            }
        else:
            prompts = {
                EntityType.AMOUNT: "Sorry, I didn't catch the amount clearly. Could you please repeat the amount?",
                EntityType.DIGITS: "Sorry, that number seems incomplete. Could you please repeat the digits one by one?",
                EntityType.UPI_ID: "Sorry, I couldn't catch the UPI ID clearly. Could you please repeat it?",
                EntityType.IFSC: "Sorry, a valid IFSC code has 11 characters with zero as the 5th character. Could you repeat it?",
            }
        return prompts[entity.kind]

    # ConfirmAction.CONFIRM
    if entity.kind == EntityType.AMOUNT and isinstance(entity.value, Decimal):
        words = amount_to_words_en_in(entity.value)
        if language == "hinglish":
            return f"Confirm kar dijiye: {entity.formatted} ({words}), sahi hai?"
        return f"Just to confirm, did you mean {entity.formatted} ({words})?"

    if entity.kind == EntityType.DIGITS:
        spoken = _spell_digits(str(entity.value))
        subtype = entity.metadata.get("subtype", "number")
        label = {
            "phone": "phone number",
            "otp": "OTP",
            "pin": "PIN",
            "account": "account number",
        }.get(subtype, "number")
        if language == "hinglish":
            return f"Confirm kar dijiye, {label} hai: {spoken}. Kya yeh sahi hai?"
        return f"Just to confirm, the {label} is {spoken}. Is that right?"

    if entity.kind == EntityType.UPI_ID:
        spoken_upi = _spell_upi(str(entity.value))
        if language == "hinglish":
            return f"Confirm kar dijiye, UPI ID hai {entity.value} ({spoken_upi}). Sahi hai?"
        return f"Just to confirm, the UPI ID is {entity.value} ({spoken_upi}). Is that right?"

    if entity.kind == EntityType.IFSC:
        spoken_ifsc = _spell_ifsc(str(entity.value))
        if language == "hinglish":
            return f"Confirm kar dijiye, IFSC code hai {entity.value} ({spoken_ifsc}). Sahi hai?"
        return f"Just to confirm, the IFSC code is {entity.value} ({spoken_ifsc}). Is that right?"

    return None


@dataclass(frozen=True)
class ConfirmPolicy:
    """Policy governing accept / confirm / reprompt decisions for parsed entities."""

    accept_threshold: float = 0.85
    confirm_threshold: float = 0.55
    high_value_amount_threshold: Decimal = Decimal("50000")
    always_confirm_kinds: frozenset[EntityType] = frozenset()
    language: Literal["en-IN", "hinglish"] = "en-IN"

    @classmethod
    def balanced(cls, language: Literal["en-IN", "hinglish"] = "en-IN") -> ConfirmPolicy:
        """Default production policy: auto-accept high confidence, confirm >= ₹50,000."""
        return cls(
            accept_threshold=0.85,
            confirm_threshold=0.55,
            high_value_amount_threshold=Decimal("50000"),
            always_confirm_kinds=frozenset(),
            language=language,
        )

    @classmethod
    def strict(cls, language: Literal["en-IN", "hinglish"] = "en-IN") -> ConfirmPolicy:
        """High-stakes transfer policy: always confirm UPI/IFSC and amounts >= ₹10,000."""
        return cls(
            accept_threshold=0.92,
            confirm_threshold=0.65,
            high_value_amount_threshold=Decimal("10000"),
            always_confirm_kinds=frozenset({EntityType.UPI_ID, EntityType.IFSC}),
            language=language,
        )

    @classmethod
    def permissive(cls, language: Literal["en-IN", "hinglish"] = "en-IN") -> ConfirmPolicy:
        """Low-friction policy for read-only / analytics voice flows."""
        return cls(
            accept_threshold=0.75,
            confirm_threshold=0.45,
            high_value_amount_threshold=Decimal("500000"),
            always_confirm_kinds=frozenset(),
            language=language,
        )

    def evaluate(self, entity: ParsedEntity) -> ParsedEntity:
        """Compute action, extra policy reasons, and confirm_prompt for a parsed entity."""
        reasons = list(entity.reasons)

        if entity.confidence < self.confirm_threshold:
            action = ConfirmAction.REPROMPT
        elif entity.confidence < self.accept_threshold:
            action = ConfirmAction.CONFIRM
        else:
            action = ConfirmAction.ACCEPT

        if action == ConfirmAction.ACCEPT and entity.kind in self.always_confirm_kinds:
            action = ConfirmAction.CONFIRM
            if "policy_always_confirm" not in reasons:
                reasons.append("policy_always_confirm")

        if (
            action == ConfirmAction.ACCEPT
            and entity.kind == EntityType.AMOUNT
            and isinstance(entity.value, Decimal)
            and entity.value >= self.high_value_amount_threshold
        ):
            action = ConfirmAction.CONFIRM
            if "high_value_threshold" not in reasons:
                reasons.append("high_value_threshold")

        prompt = build_confirm_prompt(entity, action, self.language)
        return replace(
            entity,
            action=action,
            confirm_prompt=prompt,
            reasons=tuple(reasons),
        )
