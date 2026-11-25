"""Spoken & mixed digit-string parser (phone, OTP, PIN, account numbers)."""

from __future__ import annotations

import re

from paisa_parse.lexicon import (
    DEVANAGARI_TRANS,
    DEVANAGARI_WORDS,
    REPEAT_MULTIPLIERS,
    SCALES,
    SINGLE_DIGITS,
)
from paisa_parse.types import EntitySpan, EntityType, ParsedEntity

_TOKEN_RE = re.compile(r"[\u0900-\u097F]+|[A-Za-z0-9]+")

_BAAR_COUNTS: dict[str, int] = {
    "ek": 1,
    "one": 1,
    "do": 2,
    "two": 2,
    "teen": 3,
    "three": 3,
    "chaar": 4,
    "char": 4,
    "four": 4,
    "paanch": 5,
    "panch": 5,
    "five": 5,
}

_PHONE_CTX: frozenset[str] = frozenset({"phone", "mobile", "mob", "contact", "whatsapp", "call"})
_OTP_CTX: frozenset[str] = frozenset({"otp", "verification", "verify", "code"})
_PIN_CTX: frozenset[str] = frozenset({"pin", "mpin", "cvv", "passcode"})
_ACCOUNT_CTX: frozenset[str] = frozenset({"account", "acc", "acct", "khata"})
_GENERIC_NUM_CTX: frozenset[str] = frozenset({"number", "no", "num"})

_VERB_BEFORE_DO: frozenset[str] = frozenset(
    {"bhej", "bhejo", "bhejna", "kar", "karo", "de", "bol", "bata", "batao", "send", "give"}
)

_SCALE_BOUNDARY: frozenset[str] = frozenset(SCALES.keys()) | {
    "so",
    "rupaye",
    "rupaiye",
    "rupiya",
    "rupiye",
    "rupees",
    "rupee",
    "paisa",
    "paise",
}


def _norm(tok: str) -> str:
    if tok in DEVANAGARI_WORDS:
        return DEVANAGARI_WORDS[tok]
    return tok.translate(DEVANAGARI_TRANS).lower()


def _infer_subtype(digits: str, left_ctx: set[str], right_ctx: set[str]) -> str:
    ctx = left_ctx | right_ctx
    if ctx & _OTP_CTX:
        return "otp"
    if ctx & _PIN_CTX:
        return "pin"
    if ctx & _ACCOUNT_CTX:
        return "account"
    if ctx & _PHONE_CTX:
        return "phone"
    if (len(digits) == 10 and digits[0] in "6789") or (
        len(digits) == 12 and digits.startswith("91") and digits[2] in "6789"
    ):
        return "phone"
    return "generic"


def _format_digits(digits: str, subtype: str) -> str:
    if subtype == "phone" and len(digits) == 10:
        return f"{digits[:5]} {digits[5:]}"
    if subtype == "phone" and len(digits) == 12 and digits.startswith("91"):
        return f"+91 {digits[2:7]} {digits[7:]}"
    return digits


def parse_digits(text: str) -> list[ParsedEntity]:
    """Extract spoken or mixed digit strings (phone, OTP, PIN, account numbers)."""
    if not text or not text.strip():
        return []

    raw_tokens = [(m.group(0), _norm(m.group(0)), m.start(), m.end()) for m in _TOKEN_RE.finditer(text)]
    n = len(raw_tokens)
    entities: list[ParsedEntity] = []
    i = 0

    while i < n:
        _, low, start_pos, _ = raw_tokens[i]

        # Do not start a digit sequence on bare "oh"/"o" or on a scale-bound number
        if low in ("oh", "o"):
            i += 1
            continue

        # Check if this token starts an amount expression ("ek lakh", "do sau", "500 rupees")
        if i + 1 < n and raw_tokens[i + 1][1] in _SCALE_BOUNDARY:
            i += 1
            continue

        # Guard against "bhej do ..." where "do" is a Hindi verb particle
        if low == "do" and i >= 1 and raw_tokens[i - 1][1] in _VERB_BEFORE_DO:
            i += 1
            continue

        digits_parts: list[str] = []
        oh_count = 0
        used_repeat = False
        token_count = 0
        j = i
        end_pos = start_pos

        while j < n:
            raw_j, low_j, _, end_j = raw_tokens[j]

            # Stop before a scale expression (e.g. "... 9876543210 do hazaar")
            if j > i and j + 1 < n and raw_tokens[j + 1][1] in _SCALE_BOUNDARY:
                break

            # Stop on Hindi verb "do" after verb
            if low_j == "do" and j >= 1 and raw_tokens[j - 1][1] in _VERB_BEFORE_DO:
                break

            # Repeat prefix: "double 9", "triple zero", "dabal aath"
            if low_j in REPEAT_MULTIPLIERS and j + 1 < n:
                mult = REPEAT_MULTIPLIERS[low_j]
                nxt_low = raw_tokens[j + 1][1]
                if nxt_low in ("oh", "o"):
                    digits_parts.append("0" * mult)
                    oh_count += 1
                    used_repeat = True
                    token_count += 1
                    end_pos = raw_tokens[j + 1][3]
                    j += 2
                    continue
                if nxt_low in SINGLE_DIGITS:
                    digits_parts.append(SINGLE_DIGITS[nxt_low] * mult)
                    used_repeat = True
                    token_count += 1
                    end_pos = raw_tokens[j + 1][3]
                    j += 2
                    continue
                break

            # Hindi count repeat: "teen baar shunya", "do baar aath"
            if (
                low_j in _BAAR_COUNTS
                and j + 2 < n
                and raw_tokens[j + 1][1] == "baar"
            ):
                mult = _BAAR_COUNTS[low_j]
                nxt_low = raw_tokens[j + 2][1]
                if nxt_low in ("oh", "o"):
                    digits_parts.append("0" * mult)
                    oh_count += 1
                    used_repeat = True
                    token_count += 1
                    end_pos = raw_tokens[j + 2][3]
                    j += 3
                    continue
                if nxt_low in SINGLE_DIGITS:
                    digits_parts.append(SINGLE_DIGITS[nxt_low] * mult)
                    used_repeat = True
                    token_count += 1
                    end_pos = raw_tokens[j + 2][3]
                    j += 3
                    continue

            # Contextual "oh"/"o" -> "0" ONLY mid-sequence
            if low_j in ("oh", "o") and digits_parts:
                digits_parts.append("0")
                oh_count += 1
                token_count += 1
                end_pos = end_j
                j += 1
                continue

            if low_j in SINGLE_DIGITS:
                digits_parts.append(SINGLE_DIGITS[low_j])
                token_count += 1
                end_pos = end_j
                j += 1
                continue

            # Multi-digit numeric chunk (e.g. "98 76 54 32 10" or "9876543210")
            if raw_j.isdigit() or low_j.isdigit():
                chunk = low_j
                digits_parts.append(chunk)
                token_count += 1
                end_pos = end_j
                j += 1
                continue

            break

        if not digits_parts:
            i += 1
            continue

        digits = "".join(digits_parts)
        left_ctx = {raw_tokens[k][1] for k in range(max(0, i - 4), i)}
        right_ctx = {raw_tokens[k][1] for k in range(j, min(n, j + 3))}
        subtype = _infer_subtype(digits, left_ctx, right_ctx)

        # Require >= 4 digits normally, or >= 3 digits if explicitly tagged OTP/PIN/CVV
        min_len = 3 if subtype in ("otp", "pin") else 4
        if len(digits) < min_len:
            i = max(j, i + 1)
            continue

        # Reject bare single raw 4-digit numbers (e.g. "2026" or "5000") unless in digit/phone/otp/pin/account context
        has_any_ctx = bool(left_ctx & (_PHONE_CTX | _OTP_CTX | _PIN_CTX | _ACCOUNT_CTX | _GENERIC_NUM_CTX))
        if token_count == 1 and len(digits) < 10 and not has_any_ctx:
            i = max(j, i + 1)
            continue

        # Also skip if immediately preceded by currency marker (handled as amount)
        if i >= 1 and raw_tokens[i - 1][1] in {"rs", "inr", "rupees", "rupaye"}:
            i = max(j, i + 1)
            continue

        # Confidence calibration
        reasons: list[str] = ["spoken_digit_sequence" if token_count >= 2 else "raw_digit_string"]
        conf = 0.93 if token_count >= 2 else 0.91

        if oh_count > 0:
            conf -= min(0.14, 0.06 * oh_count)
            reasons.append("oh_as_zero")
        if used_repeat:
            conf -= 0.04
            reasons.append("repeat_modifier")

        if subtype == "phone":
            valid_phone = (len(digits) == 10 and digits[0] in "6789") or (
                len(digits) == 12 and digits.startswith("91") and digits[2] in "6789"
            )
            if not valid_phone:
                conf = min(conf, 0.48)
                reasons.append("unexpected_phone_length")
        elif subtype == "otp" and len(digits) not in (4, 6):
            conf = min(conf, 0.62)
            reasons.append("unexpected_otp_length")
        elif subtype == "pin" and len(digits) not in (4, 6):
            conf = min(conf, 0.60)
            reasons.append("unexpected_pin_length")

        conf = max(0.10, min(0.98, round(conf, 4)))

        entities.append(
            ParsedEntity(
                kind=EntityType.DIGITS,
                value=digits,
                formatted=_format_digits(digits, subtype),
                confidence=conf,
                span=EntitySpan(start_pos, end_pos, text[start_pos:end_pos]),
                reasons=tuple(reasons),
                metadata={
                    "subtype": subtype,
                    "length": len(digits),
                    "token_count": token_count,
                },
            )
        )
        i = max(j, i + 1)

    return entities
