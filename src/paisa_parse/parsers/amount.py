"""Hinglish and Indian-English spoken financial amount parser."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from paisa_parse.lexicon import (
    DEVANAGARI_TRANS,
    DEVANAGARI_WORDS,
    DIRECT_FRACTIONS,
    ENGLISH_ONES,
    ENGLISH_TENS,
    FINANCIAL_CONTEXT_WORDS,
    HINDI_NUMBERS,
    NOISY_ASR_VARIANTS,
    PAISE_MARKERS,
    PREFIX_FRACTION_DELTAS,
    RUPEE_MARKERS,
    SCALES,
    format_inr,
)
from paisa_parse.types import EntitySpan, EntityType, ParsedEntity

_TOKEN_RE = re.compile(
    r"₹\s*\d[\d,]*(?:\.\d+)?(?:/-)?"
    r"|(?:Rs\.?|INR)\s*\d[\d,]*(?:\.\d+)?(?:/-)?"
    r"|\d[\d,]*(?:\.\d+)?(?:/-)?"
    r"|[\u0900-\u097F]+"
    r"|[A-Za-z]+",
    re.IGNORECASE,
)
_COMPACT_NUM_SCALE_RE = re.compile(r"^(\d+(?:\.\d+)?)(k|cr|lac|lacs|lakh|lakhs)$", re.IGNORECASE)
_INLINE_CURRENCY_RE = re.compile(r"^(₹|rs\.?|inr)\s*(\d[\d,]*(?:\.\d+)?)(?:/-)?$", re.IGNORECASE)
_PLAIN_NUMBER_RE = re.compile(r"^(\d[\d,]*(?:\.\d+)?)(?:/-)?$")


@dataclass(frozen=True)
class _Tok:
    raw: str
    norm: str
    start: int
    end: int
    has_currency_prefix: bool = False
    has_slash_dash: bool = False


def _tokenize(text: str) -> list[_Tok]:
    tokens: list[_Tok] = []
    for m in _TOKEN_RE.finditer(text):
        raw = m.group(0)
        start, end = m.start(), m.end()

        # Check compact attached currency+number like "₹1,50,000" or "Rs. 45,000"
        cm = _INLINE_CURRENCY_RE.match(raw.strip())
        if cm:
            num_str = cm.group(2).replace(",", "").translate(DEVANAGARI_TRANS)
            tokens.append(
                _Tok(
                    raw=raw,
                    norm=num_str,
                    start=start,
                    end=end,
                    has_currency_prefix=True,
                    has_slash_dash=raw.endswith("/-"),
                )
            )
            continue

        # Normalize Devanagari words / digits
        if raw in DEVANAGARI_WORDS:
            norm = DEVANAGARI_WORDS[raw]
        else:
            translated = raw.translate(DEVANAGARI_TRANS)
            norm = translated.lower().rstrip("/-")
            if norm.endswith("."):
                norm = norm[:-1]

        tokens.append(
            _Tok(
                raw=raw,
                norm=norm,
                start=start,
                end=end,
                has_currency_prefix=False,
                has_slash_dash=raw.endswith("/-"),
            )
        )
    return tokens


def _parse_numeric_token(tok: _Tok) -> Decimal | None:
    s = tok.norm.replace(",", "")
    if _PLAIN_NUMBER_RE.match(s):
        try:
            return Decimal(s)
        except InvalidOperation:
            return None
    if s in HINDI_NUMBERS:
        return Decimal(HINDI_NUMBERS[s])
    if s in ENGLISH_ONES:
        return Decimal(ENGLISH_ONES[s])
    if s in ENGLISH_TENS:
        return Decimal(ENGLISH_TENS[s])
    return None


def _consume_cardinal(
    tokens: list[_Tok], idx: int
) -> tuple[Decimal, int, bool, bool] | None:
    """Consume a cardinal integer/decimal < 100 (or raw numeric token).

    Returns (value, next_idx, used_noisy_variant, is_word_do_only).
    """
    if idx >= len(tokens):
        return None

    tok = tokens[idx]
    s = tok.norm.replace(",", "")

    # Reject long 9+ digit raw integers without currency prefix/commas (likely phone/account)
    if s.isdigit() and len(s) >= 9 and not tok.has_currency_prefix and "," not in tok.raw:
        return None

    if _PLAIN_NUMBER_RE.match(s):
        try:
            return Decimal(s), idx + 1, False, False
        except InvalidOperation:
            return None

    # English tens + ones (e.g. "twenty five")
    if s in ENGLISH_TENS:
        val = ENGLISH_TENS[s]
        if idx + 1 < len(tokens) and tokens[idx + 1].norm in ENGLISH_ONES and ENGLISH_ONES[tokens[idx + 1].norm] < 10:
            val += ENGLISH_ONES[tokens[idx + 1].norm]
            return Decimal(val), idx + 2, False, False
        return Decimal(val), idx + 1, False, False

    if s in ENGLISH_ONES:
        return Decimal(ENGLISH_ONES[s]), idx + 1, False, False

    if s in HINDI_NUMBERS:
        noisy = s in NOISY_ASR_VARIANTS
        return Decimal(HINDI_NUMBERS[s]), idx + 1, noisy, s == "do"

    return None


def _consume_multiplier(
    tokens: list[_Tok], idx: int
) -> tuple[Decimal, int, bool, bool, bool] | None:
    """Consume a number or colloquial fraction that precedes a scale (or stands as a rupee value).

    Returns (value, next_idx, used_fraction, used_noisy, is_bare_hindi_do).
    """
    if idx >= len(tokens):
        return None

    tok = tokens[idx]
    norm = tok.norm

    if norm in DIRECT_FRACTIONS:
        return DIRECT_FRACTIONS[norm], idx + 1, True, norm in NOISY_ASR_VARIANTS, False

    if norm in PREFIX_FRACTION_DELTAS:
        delta, standalone = PREFIX_FRACTION_DELTAS[norm]
        noisy = norm in NOISY_ASR_VARIANTS

        # Look ahead for an integer/cardinal before scale (e.g., "sava do lakh", "saade teen lakh")
        card = _consume_cardinal(tokens, idx + 1)
        if card is not None:
            n_val, next_i, card_noisy, _ = card
            # Guard: ensure the cardinal is actually followed by a scale or currency or standalone fraction
            if delta > 0 and norm.startswith(("saad", "sad")) and n_val == Decimal("1"):
                # "saade ek" is non-standard ("dedh" is standard) -> allow with noisy penalty
                noisy = True
            return n_val + delta, next_i, True, noisy or card_noisy, False

        # "sava lakh", "paune sau", "paune hazaar" (no explicit N, directly followed by scale)
        if standalone is not None and idx + 1 < len(tokens) and (
            tokens[idx + 1].norm in SCALES or tokens[idx + 1].norm == "so"
        ):
            return standalone, idx + 1, True, noisy, False
        return None

    card = _consume_cardinal(tokens, idx)
    if card is not None:
        val, next_i, card_noisy, is_do = card
        return val, next_i, False, card_noisy, is_do

    return None


def _is_scale_token(tokens: list[_Tok], idx: int, has_preceding_mult: bool) -> int | None:
    if idx >= len(tokens):
        return None
    norm = tokens[idx].norm
    if norm in SCALES:
        return SCALES[norm]
    if norm == "so" and has_preceding_mult:
        return 100
    return None


def _parse_clause_at(tokens: list[_Tok], start_idx: int) -> tuple[ParsedEntity, int] | None:
    """Try to parse a single Hinglish/Indian-English amount starting at `start_idx`."""
    n = len(tokens)
    if start_idx >= n:
        return None

    i = start_idx
    has_currency = False
    has_scale = False
    has_fraction = False
    has_noisy = False
    has_paise = False
    is_bare_hindi_do = False

    # Optional leading currency word ("Rs", "INR", "rupees") as separate token
    if tokens[i].norm in RUPEE_MARKERS and not tokens[i].has_currency_prefix:
        has_currency = True
        i += 1
        if i >= n:
            return None

    # Handle compact attached forms like "50k", "2.5cr", "1.5lakh"
    compact_m = _COMPACT_NUM_SCALE_RE.match(tokens[i].norm)
    if compact_m:
        num = Decimal(compact_m.group(1))
        scale_val = SCALES[compact_m.group(2).lower()]
        total = num * Decimal(scale_val)
        end_pos = tokens[i].end
        next_i = i + 1
        # Consume trailing rupee marker if present
        if next_i < n and tokens[next_i].norm in RUPEE_MARKERS:
            has_currency = True
            end_pos = tokens[next_i].end
            next_i += 1
        reasons = ["compact_scale"]
        if has_currency or tokens[i].has_currency_prefix:
            reasons.append("explicit_currency")
        return (
            ParsedEntity(
                kind=EntityType.AMOUNT,
                value=total,
                formatted=format_inr(total),
                confidence=0.93,
                span=EntitySpan(tokens[start_idx].start, end_pos, ""),
                reasons=tuple(reasons),
                metadata={"has_currency": has_currency, "has_scale": True, "has_fraction": False},
            ),
            next_i,
        )

    total = Decimal(0)
    last_scale: int | None = None
    consumed_any = False
    end_pos = tokens[start_idx].end

    # Main scale-clause loop (descending scales: arab > crore > lakh > hazaar > sau > remainder)
    while i < n:
        tok_i = tokens[i]
        if tok_i.has_currency_prefix:
            has_currency = True
        if tok_i.has_slash_dash:
            has_currency = True

        # Check standalone scale word without explicit multiplier?
        # Allow "hazaar rupaye" or "lakh rupaye" ONLY if preceded by nothing and followed by currency,
        # OR handle "ek lakh", "dedh lakh", etc. via multiplier first.
        mult_res = _consume_multiplier(tokens, i)
        if mult_res is None:
            # Handle bare "sau rupaye", "hazaar rupaye" (multiplier implied = 1)
            if not consumed_any and tok_i.norm in SCALES and i + 1 < n and tokens[i + 1].norm in RUPEE_MARKERS:
                scale_val = SCALES[tok_i.norm]
                total += Decimal(scale_val)
                has_scale = True
                consumed_any = True
                last_scale = scale_val
                end_pos = tok_i.end
                i += 1
                break
            break

        mult_val, after_mult_i, used_frac, used_noisy, bare_do = mult_res

        # Check compact scale right after? No, already handled if attached.
        scale_val = _is_scale_token(tokens, after_mult_i, has_preceding_mult=True)

        if scale_val is not None:
            # Ensure descending scale order (allow e.g. "125 crore" where mult < 1000, or "ek hazaar do sau")
            if last_scale is not None and scale_val >= last_scale:
                break
            if tokens[after_mult_i].norm == "so":
                has_noisy = True
            total += mult_val * Decimal(scale_val)
            has_scale = True
            has_fraction = has_fraction or used_frac
            has_noisy = has_noisy or used_noisy
            consumed_any = True
            last_scale = scale_val
            i = after_mult_i + 1
            end_pos = tokens[i - 1].end

            # Optional connector "aur" / "and" between scale clauses (e.g. "dedh lakh aur paanch hazaar")
            if (
                i + 1 < n
                and tokens[i].norm in {"aur", "and"}
                and (
                    _consume_multiplier(tokens, i + 1) is not None
                    or tokens[i + 1].norm in PAISE_MARKERS
                )
            ):
                # Peek: if next is paise ("aur pachaas paise"), break to paise handler below
                if (
                    i + 2 < n
                    and _consume_cardinal(tokens, i + 1) is not None
                    and tokens[i + 2].norm in PAISE_MARKERS
                ):
                    break
                i += 1
            continue

        # No scale after this multiplier:
        # Either it's a paise value ("50 paise"), or trailing remainder ("ek hazaar pachees"), or standalone number ("500 rupaye")
        if after_mult_i < n and tokens[after_mult_i].norm in PAISE_MARKERS:
            if not consumed_any:
                # Standalone "<N> paise"
                total = mult_val / Decimal(100)
                has_paise = True
                has_currency = True
                has_noisy = has_noisy or used_noisy
                consumed_any = True
                i = after_mult_i + 1
                end_pos = tokens[i - 1].end
            break

        # Trailing remainder (< 100 or plain number) after a previous scale (e.g. "ek hazaar pachees" or "ek sau pachaas")
        if consumed_any and last_scale is not None and last_scale >= 100 and mult_val < Decimal(100) and not used_frac:
            total += mult_val
            has_noisy = has_noisy or used_noisy
            i = after_mult_i
            end_pos = tokens[i - 1].end
            break

        # Standalone number / fraction without scale (e.g. "₹1,50,000", "500 rupees", "send 500")
        if not consumed_any:
            total = mult_val
            has_fraction = has_fraction or used_frac
            has_noisy = has_noisy or used_noisy
            is_bare_hindi_do = bare_do
            consumed_any = True
            i = after_mult_i
            end_pos = tokens[i - 1].end
        break

    if not consumed_any:
        return None

    # Trailing rupee marker
    if i < n and tokens[i].norm in RUPEE_MARKERS:
        has_currency = True
        end_pos = tokens[i].end
        i += 1

    # Optional paise clause after rupees / scale (e.g. "pachas rupaye pachees paise", "ek sau rupaye aur pachaas paise")
    paise_start = i
    if i < n and tokens[i].norm in {"aur", "and"}:
        i += 1
    if i < n:
        p_card = _consume_cardinal(tokens, i)
        if p_card is not None:
            p_val, p_next, p_noisy, _ = p_card
            if p_next < n and tokens[p_next].norm in PAISE_MARKERS and p_val < Decimal(100):
                total += p_val / Decimal(100)
                has_paise = True
                has_currency = True
                has_noisy = has_noisy or p_noisy
                i = p_next + 1
                end_pos = tokens[i - 1].end
            else:
                i = paise_start
        else:
            i = paise_start

    # False-positive gating: must have currency, scale, or nearby financial context
    has_context = False
    if not has_currency and not has_scale:
        # Reject bare colloquial fraction without scale ("aadha ghanta", "half day")
        if has_fraction:
            return None
        # Reject bare Hindi "do" ("bhej do", "kar do") without scale/currency
        if is_bare_hindi_do:
            return None
        # Look 3 tokens left and 3 tokens right for financial context
        left_ctx = any(
            tokens[k].norm in FINANCIAL_CONTEXT_WORDS for k in range(max(0, start_idx - 3), start_idx)
        )
        right_ctx = any(
            tokens[k].norm in FINANCIAL_CONTEXT_WORDS for k in range(i, min(n, i + 3))
        )
        # Do not interpret bare single-digit word "ek"/"one"/"two" from context alone unless numeric digits
        first_tok = tokens[start_idx]
        if (left_ctx or right_ctx) and (
            _PLAIN_NUMBER_RE.match(first_tok.norm) is not None or total >= Decimal(10)
        ):
            # Guard against "at 5", "at 5 pm", "5 pm", "5 am"
            if i < n and tokens[i].norm in {"pm", "am", "baje", "percent", "%", "times", "baar"}:
                return None
            if start_idx >= 1 and tokens[start_idx - 1].norm == "at":
                return None
            has_context = True
        else:
            return None

    # Calibrate confidence & collect reasons
    reasons: list[str] = []
    if has_currency and (has_scale or _PLAIN_NUMBER_RE.match(tokens[start_idx].norm) or has_paise):
        conf = 0.96
    elif has_fraction and has_scale:
        conf = 0.92
    elif has_scale:
        conf = 0.91
    elif has_currency:
        conf = 0.93
    else:
        conf = 0.78
        reasons.append("inferred_from_context")

    if has_currency:
        reasons.append("explicit_currency")
    if has_scale:
        reasons.append("indian_scale")
    if has_fraction:
        reasons.append("colloquial_fraction")
    if has_paise:
        reasons.append("includes_paise")
    if has_noisy:
        conf -= 0.13
        reasons.append("noisy_asr_variant")

    conf = max(0.10, min(0.99, round(conf, 4)))

    return (
        ParsedEntity(
            kind=EntityType.AMOUNT,
            value=total,
            formatted=format_inr(total),
            confidence=conf,
            span=EntitySpan(tokens[start_idx].start, end_pos, ""),
            reasons=tuple(reasons),
            metadata={
                "has_currency": has_currency,
                "has_scale": has_scale,
                "has_fraction": has_fraction,
                "has_paise": has_paise,
                "has_context": has_context,
            },
        ),
        i,
    )


def parse_amounts(text: str) -> list[ParsedEntity]:
    """Extract Hinglish and Indian-English monetary amounts from text."""
    if not text or not text.strip():
        return []

    tokens = _tokenize(text)
    entities: list[ParsedEntity] = []
    i = 0
    while i < len(tokens):
        res = _parse_clause_at(tokens, i)
        if res is None:
            i += 1
            continue
        ent, next_i = res
        span = EntitySpan(ent.span.start, ent.span.end, text[ent.span.start : ent.span.end])
        entities.append(
            ParsedEntity(
                kind=ent.kind,
                value=ent.value,
                formatted=ent.formatted,
                confidence=ent.confidence,
                span=span,
                action=ent.action,
                confirm_prompt=ent.confirm_prompt,
                reasons=ent.reasons,
                metadata=ent.metadata,
            )
        )
        i = max(next_i, i + 1)

    return entities
