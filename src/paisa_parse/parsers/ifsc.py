"""Written and spoken Indian IFSC code parser with RBI structure & bank-prefix checks."""

from __future__ import annotations

import re

from paisa_parse.lexicon import REPEAT_MULTIPLIERS, SINGLE_DIGITS
from paisa_parse.types import EntitySpan, EntityType, ParsedEntity

# Major RBI-assigned 4-letter IFSC bank prefixes.
KNOWN_BANK_CODES: dict[str, str] = {
    "SBIN": "State Bank of India",
    "HDFC": "HDFC Bank",
    "ICIC": "ICICI Bank",
    "UTIB": "Axis Bank",
    "KKBK": "Kotak Mahindra Bank",
    "BARB": "Bank of Baroda",
    "PUNB": "Punjab National Bank",
    "CNRB": "Canara Bank",
    "UBIN": "Union Bank of India",
    "BKID": "Bank of India",
    "IDIB": "Indian Bank",
    "CBIN": "Central Bank of India",
    "IOBA": "Indian Overseas Bank",
    "UCBA": "UCO Bank",
    "MAHB": "Bank of Maharashtra",
    "PSIB": "Punjab & Sind Bank",
    "INDB": "IndusInd Bank",
    "YESB": "Yes Bank",
    "IDFB": "IDFC First Bank",
    "FDRL": "Federal Bank",
    "RATN": "RBL Bank",
    "SIBL": "South Indian Bank",
    "KARB": "Karnataka Bank",
    "KVBL": "Karur Vysya Bank",
    "CIUB": "City Union Bank",
    "TMBL": "Tamilnad Mercantile Bank",
    "CSBK": "CSB Bank",
    "DLXB": "Dhanlaxmi Bank",
    "DCBL": "DCB Bank",
    "JAKA": "Jammu & Kashmir Bank",
    "BAND": "Bandhan Bank",
    "AUBL": "AU Small Finance Bank",
    "ESFB": "Equitas Small Finance Bank",
    "UJVN": "Ujjivan Small Finance Bank",
    "JSFB": "Jana Small Finance Bank",
    "SURY": "Suryoday Small Finance Bank",
    "UTKS": "Utkarsh Small Finance Bank",
    "ESMF": "ESAF Small Finance Bank",
    "FSFB": "Fincare Small Finance Bank",
    "NESF": "North East Small Finance Bank",
    "SHIX": "Shivalik Small Finance Bank",
    "AIRP": "Airtel Payments Bank",
    "PYTM": "Paytm Payments Bank",
    "IPOS": "India Post Payments Bank",
    "FINO": "Fino Payments Bank",
    "JIOP": "Jio Payments Bank",
    "NSPB": "NSDL Payments Bank",
    "HSBC": "HSBC Bank",
    "SCBL": "Standard Chartered Bank",
    "CITI": "Citibank",
    "DBSS": "DBS Bank India",
    "DEUT": "Deutsche Bank",
    "BARC": "Barclays Bank",
    "BNPA": "BNP Paribas",
    "CHAS": "JPMorgan Chase Bank",
    "BOFA": "Bank of America",
    "SVCB": "SVC Co-operative Bank",
    "SRCB": "Saraswat Co-operative Bank",
    "COSB": "Cosmos Co-operative Bank",
    "ABHY": "Abhyudaya Co-operative Bank",
    "KCCB": "Kalupur Commercial Co-op Bank",
    "TJSB": "TJSB Sahakari Bank",
    "APBL": "Andhra Pradesh Grameena Vikas Bank",
    "KGBX": "Kerala Gramin Bank",
    "BUPB": "Baroda UP Bank",
    "PUNX": "Punjab Gramin Bank",
    "SBBJ": "State Bank of Bikaner & Jaipur (merged SBI)",
    "SBHY": "State Bank of Hyderabad (merged SBI)",
}

_IFSC_STRICT_RE = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")
# Direct/spaced/hyphenated IFSC candidate in text:
# Contiguous 11-char (allowing 5th char O/o) OR spaced/hyphenated with explicit 0 as 5th char
_DIRECT_IFSC_RE = re.compile(
    r"(?<![A-Za-z0-9])([A-Za-z]{4})(?:"
    r"([0Oo])([A-Za-z0-9]{6})"
    r"|[\s-]+(0)[\s-]*([A-Za-z0-9]{6}|[A-Za-z0-9]{3}[\s-][A-Za-z0-9]{3})"
    r"|-(0)-([A-Za-z0-9]{3}-[A-Za-z0-9]{3})"
    r"|[\s-]*(0)[\s-]*([A-Za-z0-9]{3}[\s-]+[A-Za-z0-9]{3})"
    r")(?![A-Za-z0-9])"
)
_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
_IFSC_TRIGGER_WORDS: frozenset[str] = frozenset({"ifsc", "branch"})


def _has_ifsc_context(text: str, pos: int) -> bool:
    prefix = text[max(0, pos - 32) : pos].lower()
    return "ifsc" in prefix or "i f s c" in prefix


def _parse_spoken_alnum(tokens: list[tuple[str, int, int]], start_idx: int, explicit_ifsc: bool) -> tuple[str, int, int, bool, bool] | None:
    """Reconstruct spoken IFSC starting at `start_idx`.

    Returns (assembled_raw, end_pos, next_idx, used_spoken, used_oh_for_zero) or None.
    """
    n = len(tokens)
    i = start_idx

    # Phase 1: Collect 4-letter bank prefix (either one 4-letter token or 4 single letters)
    bank_chars = ""
    first_tok = tokens[i][0].upper()
    if len(first_tok) == 4 and first_tok.isalpha():
        bank_chars = first_tok
        i += 1
    elif (
        i + 3 < n
        and all(len(tokens[i + k][0]) == 1 and tokens[i + k][0].isalpha() for k in range(4))
    ):
        bank_chars = "".join(tokens[i + k][0].upper() for k in range(4))
        i += 4
    else:
        return None

    if not explicit_ifsc and bank_chars not in KNOWN_BANK_CODES:
        return None

    # Phase 2: Collect remaining characters (expecting 7 more -> total 11)
    rest_chars = ""
    used_spoken = len(first_tok) != 4
    used_oh = False
    end_pos = tokens[i - 1][2]

    while i < n and len(rest_chars) < 10:
        tok_raw, _, tok_end = tokens[i]
        low = tok_raw.lower()

        if low in REPEAT_MULTIPLIERS and i + 1 < n:
            mult = REPEAT_MULTIPLIERS[low]
            nxt_raw, _, nxt_end = tokens[i + 1]
            nxt_low = nxt_raw.lower()
            if nxt_low in ("oh", "o"):
                ch = "0"
                used_oh = True
            elif nxt_low in SINGLE_DIGITS:
                ch = SINGLE_DIGITS[nxt_low]
            elif len(nxt_raw) == 1 and nxt_raw.isalnum():
                ch = nxt_raw.upper()
            else:
                break
            rest_chars += ch * mult
            used_spoken = True
            end_pos = nxt_end
            i += 2
            continue

        if low in ("oh", "o"):
            rest_chars += "0"
            used_spoken = True
            used_oh = True
            end_pos = tok_end
            i += 1
            continue

        if low in SINGLE_DIGITS:
            rest_chars += SINGLE_DIGITS[low]
            if not low.isdigit():
                used_spoken = True
            end_pos = tok_end
            i += 1
            continue

        if tok_raw.isdigit():
            rest_chars += tok_raw
            end_pos = tok_end
            i += 1
            continue

        if len(tok_raw) == 1 and tok_raw.isalpha():
            rest_chars += tok_raw.upper()
            used_spoken = True
            end_pos = tok_end
            i += 1
            continue

        if tok_raw.isalnum() and len(tok_raw) <= 7 and any(c.isdigit() for c in tok_raw):
            rest_chars += tok_raw.upper()
            end_pos = tok_end
            i += 1
            continue

        break

    if not rest_chars:
        return None

    return bank_chars + rest_chars, end_pos, i, used_spoken, used_oh


def parse_ifsc(text: str) -> list[ParsedEntity]:
    """Extract written and spoken Indian IFSC codes with RBI structure & bank checks."""
    if not text or not text.strip():
        return []

    entities: list[ParsedEntity] = []
    occupied: list[tuple[int, int]] = []

    def overlaps(s: int, e: int) -> bool:
        return any(s < oe and e > os for os, oe in occupied)

    # Mode A: Direct / spaced / hyphenated IFSC patterns
    for m in _DIRECT_IFSC_RE.finditer(text):
        bank = m.group(1).upper()
        # Pick whichever alternation matched (groups 2/3, 4/5, 6/7, or 8/9)
        fifth_raw = ""
        branch_part = ""
        for g_fifth, g_branch in ((2, 3), (4, 5), (6, 7), (8, 9)):
            if m.group(g_fifth) is not None:
                fifth_raw = m.group(g_fifth)
                branch_part = m.group(g_branch)
                break
        branch_raw = re.sub(r"[\s-]+", "", branch_part).upper()
        end_pos = m.end()
        if len(branch_raw) != 6:
            continue

        has_context = _has_ifsc_context(text, m.start())
        is_known_bank = bank in KNOWN_BANK_CODES

        # Guard against random 11-letter words with 'O' as 5th char unless digits exist or IFSC context
        if not any(ch.isdigit() for ch in branch_raw) and fifth_raw != "0" and not has_context:
            continue
        if not any(ch.isdigit() for ch in branch_raw) and not is_known_bank and not has_context:
            continue

        repaired_fifth = fifth_raw in ("O", "o")
        canonical = f"{bank}0{branch_raw}"
        if not _IFSC_STRICT_RE.match(canonical):
            continue

        reasons: list[str] = ["direct_ifsc"]
        if repaired_fifth:
            reasons.append("fifth_char_o_repaired")
        if not is_known_bank:
            reasons.append("unknown_bank_prefix")

        if repaired_fifth:
            conf = 0.76 if is_known_bank else 0.62
        elif is_known_bank:
            conf = 0.96 if "-" not in m.group(0) and " " not in m.group(0) else 0.92
        else:
            conf = 0.64

        entities.append(
            ParsedEntity(
                kind=EntityType.IFSC,
                value=canonical,
                formatted=canonical,
                confidence=conf,
                span=EntitySpan(m.start(), end_pos, text[m.start() : end_pos]),
                reasons=tuple(reasons),
                metadata={
                    "bank_code": bank,
                    "bank_name": KNOWN_BANK_CODES.get(bank),
                    "branch_code": branch_raw,
                    "known_bank": is_known_bank,
                    "repaired_fifth_char": repaired_fifth,
                },
            )
        )
        occupied.append((m.start(), end_pos))

    # Mode B: Spoken IFSC reconstruction & explicit malformed-IFSC reprompt detection
    tokens = [(m.group(0), m.start(), m.end()) for m in _TOKEN_RE.finditer(text)]
    n = len(tokens)
    i = 0
    while i < n:
        tok_start = tokens[i][1]
        if overlaps(tok_start, tokens[i][2]):
            i += 1
            continue

        explicit_ctx = (
            (i >= 1 and tokens[i - 1][0].lower() in _IFSC_TRIGGER_WORDS)
            or (
                i >= 2
                and tokens[i - 2][0].lower() == "ifsc"
                and tokens[i - 1][0].lower() in {"code", "is", "hai"}
            )
            or (
                i >= 4
                and " ".join(tokens[k][0].lower() for k in range(i - 4, i)) == "i f s c"
            )
        )

        # Also check direct invalid 5th-char token under explicit IFSC context (e.g. "ifsc code SBIN1001234")
        tok_up = tokens[i][0].upper()
        if (
            explicit_ctx
            and len(tok_up) >= 6
            and tok_up[:4].isalpha()
            and tok_up[4:].isalnum()
            and not overlaps(tokens[i][1], tokens[i][2])
        ):
            if len(tok_up) != 11:
                entities.append(
                    ParsedEntity(
                        kind=EntityType.IFSC,
                        value=tok_up,
                        formatted=tok_up,
                        confidence=0.35,
                        span=EntitySpan(tokens[i][1], tokens[i][2], tokens[i][0]),
                        reasons=("invalid_ifsc_length",),
                        metadata={"bank_code": tok_up[:4], "known_bank": tok_up[:4] in KNOWN_BANK_CODES},
                    )
                )
                occupied.append((tokens[i][1], tokens[i][2]))
                i += 1
                continue
            if tok_up[4] not in ("0", "O"):
                entities.append(
                    ParsedEntity(
                        kind=EntityType.IFSC,
                        value=tok_up,
                        formatted=tok_up,
                        confidence=0.35,
                        span=EntitySpan(tokens[i][1], tokens[i][2], tokens[i][0]),
                        reasons=("invalid_fifth_char",),
                        metadata={"bank_code": tok_up[:4], "known_bank": tok_up[:4] in KNOWN_BANK_CODES},
                    )
                )
                occupied.append((tokens[i][1], tokens[i][2]))
                i += 1
                continue

        spoken = _parse_spoken_alnum(tokens, i, explicit_ctx)
        if spoken is None:
            i += 1
            continue

        assembled, end_pos, next_idx, used_spoken, used_oh = spoken
        if overlaps(tok_start, end_pos):
            i += 1
            continue

        bank = assembled[:4]
        is_known_bank = bank in KNOWN_BANK_CODES

        if len(assembled) != 11:
            if explicit_ctx and len(assembled) >= 6:
                entities.append(
                    ParsedEntity(
                        kind=EntityType.IFSC,
                        value=assembled,
                        formatted=assembled,
                        confidence=0.35,
                        span=EntitySpan(tok_start, end_pos, text[tok_start:end_pos]),
                        reasons=("invalid_ifsc_length",),
                        metadata={"bank_code": bank, "known_bank": is_known_bank},
                    )
                )
                occupied.append((tok_start, end_pos))
                i = next_idx
                continue
            i += 1
            continue

        fifth = assembled[4]
        repaired_fifth = fifth == "O" or (used_oh and fifth == "0")
        canonical = f"{bank}0{assembled[5:]}" if fifth == "O" else assembled

        if not _IFSC_STRICT_RE.match(canonical):
            if explicit_ctx:
                entities.append(
                    ParsedEntity(
                        kind=EntityType.IFSC,
                        value=assembled,
                        formatted=assembled,
                        confidence=0.35,
                        span=EntitySpan(tok_start, end_pos, text[tok_start:end_pos]),
                        reasons=("invalid_fifth_char",),
                        metadata={"bank_code": bank, "known_bank": is_known_bank},
                    )
                )
                occupied.append((tok_start, end_pos))
                i = next_idx
                continue
            i += 1
            continue

        reasons = ["spoken_ifsc"] if used_spoken else ["direct_ifsc"]
        if repaired_fifth:
            reasons.append("fifth_char_o_repaired")
        if not is_known_bank:
            reasons.append("unknown_bank_prefix")

        if not is_known_bank:
            conf = 0.62
        elif fifth == "O":
            conf = 0.76
        elif used_oh:
            conf = 0.80
        elif used_spoken:
            conf = 0.88
        else:
            conf = 0.93

        entities.append(
            ParsedEntity(
                kind=EntityType.IFSC,
                value=canonical,
                formatted=canonical,
                confidence=conf,
                span=EntitySpan(tok_start, end_pos, text[tok_start:end_pos]),
                reasons=tuple(reasons),
                metadata={
                    "bank_code": bank,
                    "bank_name": KNOWN_BANK_CODES.get(bank),
                    "branch_code": canonical[5:],
                    "known_bank": is_known_bank,
                    "repaired_fifth_char": repaired_fifth,
                },
            )
        )
        occupied.append((tok_start, end_pos))
        i = next_idx

    entities.sort(key=lambda e: e.span.start)
    return entities
