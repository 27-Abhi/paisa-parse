"""Written and spoken Indian UPI ID (VPA) parser with NPCI PSP handle checks."""

from __future__ import annotations

import re

from paisa_parse.lexicon import SINGLE_DIGITS
from paisa_parse.types import EntitySpan, EntityType, ParsedEntity

# Common NPCI-approved PSP / bank handles -> provider description.
KNOWN_UPI_HANDLES: dict[str, str] = {
    # Google Pay
    "okicici": "Google Pay (ICICI)",
    "okaxis": "Google Pay (Axis)",
    "oksbi": "Google Pay (SBI)",
    "okhdfcbank": "Google Pay (HDFC)",
    # PhonePe
    "ybl": "PhonePe (Yes Bank)",
    "ibl": "PhonePe (ICICI)",
    "axl": "PhonePe (Axis)",
    # Paytm
    "paytm": "Paytm",
    "ptaxis": "Paytm (Axis)",
    "pthdfc": "Paytm (HDFC)",
    "ptsbi": "Paytm (SBI)",
    "ptyes": "Paytm (Yes Bank)",
    # BHIM / NPCI
    "upi": "BHIM / NPCI",
    # Amazon Pay
    "apl": "Amazon Pay (Axis)",
    "yapl": "Amazon Pay (Yes Bank)",
    "rapl": "Amazon Pay (RBL)",
    # CRED
    "axisb": "CRED (Axis)",
    "yescred": "CRED (Yes Bank)",
    "yescurie": "CRED Curie",
    # WhatsApp / Meta
    "waicici": "WhatsApp Pay (ICICI)",
    "waaxis": "WhatsApp Pay (Axis)",
    "wasbi": "WhatsApp Pay (SBI)",
    "wahdfcbank": "WhatsApp Pay (HDFC)",
    # Major Indian banks & fintech PSPs
    "sbi": "SBI Pay",
    "icici": "ICICI iMobile",
    "hdfcbank": "HDFC Bank",
    "axisbank": "Axis Bank",
    "kotak": "Kotak Mahindra Bank",
    "kotak811": "Kotak 811",
    "kaypay": "Kotak KayPay",
    "barodampay": "Bank of Baroda",
    "bob": "Bank of Baroda",
    "indus": "IndusInd Bank",
    "indie": "IndusInd INDIE",
    "federal": "Federal Bank",
    "fbl": "Federal Bank",
    "idfc": "IDFC First Bank",
    "idfcbank": "IDFC First Bank",
    "yesbank": "Yes Bank",
    "yesbankltd": "Yes Bank",
    "rbl": "RBL Bank",
    "pnb": "Punjab National Bank",
    "cnrb": "Canara Bank",
    "unionbank": "Union Bank of India",
    "uboi": "Union Bank of India",
    "indianbank": "Indian Bank",
    "iob": "Indian Overseas Bank",
    "boi": "Bank of India",
    "cbi": "Central Bank of India",
    "mahb": "Bank of Maharashtra",
    "uco": "UCO Bank",
    "psb": "Punjab & Sind Bank",
    "sib": "South Indian Bank",
    "kvb": "Karur Vysya Bank",
    "cub": "City Union Bank",
    "tmb": "Tamilnad Mercantile Bank",
    "csb": "CSB Bank",
    "dcb": "DCB Bank",
    "jkb": "J&K Bank",
    "bandhan": "Bandhan Bank",
    "aubank": "AU Small Finance Bank",
    "equitas": "Equitas Small Finance Bank",
    "ujjivan": "Ujjivan Small Finance Bank",
    "airtel": "Airtel Payments Bank",
    "airtelpaymentsbank": "Airtel Payments Bank",
    "jio": "Jio Payments Bank",
    "fino": "Fino Payments Bank",
    "postbank": "India Post Payments Bank",
    "ippb": "India Post Payments Bank",
    "slice": "Slice",
    "sliceaxis": "Slice (Axis)",
    "jupiteraxis": "Jupiter (Axis)",
    "fi": "Fi Money",
    "naviaxis": "Navi (Axis)",
    "ikwik": "MobiKwik",
    "freecharge": "Freecharge",
    "pingpay": "Axis PingPay",
    "citi": "Citibank",
    "citigold": "Citibank",
    "hsbc": "HSBC",
    "scb": "Standard Chartered",
    "dbs": "DBS digibank",
    "fam": "FamPay",
    "fampay": "FamPay",
    "superyes": "super.money",
    "bajaj": "Bajaj Pay",
    "timecosmos": "Cosmos Bank",
}

# Spaced / ASR-split handle phrases mapped to canonical handle.
SPOKEN_HANDLE_ALIASES: dict[str, str] = {
    "ok icici": "okicici",
    "ok axis": "okaxis",
    "ok sbi": "oksbi",
    "ok hdfc bank": "okhdfcbank",
    "ok hdfc": "okhdfcbank",
    "y b l": "ybl",
    "i b l": "ibl",
    "a x l": "axl",
    "pay tm": "paytm",
    "u p i": "upi",
    "a p l": "apl",
    "y a p l": "yapl",
    "r a p l": "rapl",
    "s b i": "sbi",
    "p n b": "pnb",
    "wa icici": "waicici",
    "wa axis": "waaxis",
    "wa sbi": "wasbi",
    "wa hdfc": "wahdfcbank",
    "pt axis": "ptaxis",
    "pt hdfc": "pthdfc",
    "pt sbi": "ptsbi",
    "pt yes": "ptyes",
    "hdfc bank": "hdfcbank",
    "axis bank": "axisbank",
    "idfc bank": "idfcbank",
    "idfc first": "idfcbank",
    "yes bank": "yesbank",
    "kotak 811": "kotak811",
    "baroda m pay": "barodampay",
    "airtel payments bank": "airtelpaymentsbank",
    "fam pay": "fampay",
    "free charge": "freecharge",
    "super yes": "superyes",
}

_EMAIL_DOMAINS: frozenset[str] = frozenset(
    {
        "gmail",
        "yahoo",
        "outlook",
        "hotmail",
        "icloud",
        "proton",
        "protonmail",
        "rediffmail",
        "live",
        "msn",
        "aol",
        "zoho",
        "yandex",
        "gmx",
        "me",
        "mail",
    }
)

_EMAIL_TLDS: frozenset[str] = frozenset(
    {"com", "in", "org", "net", "co", "io", "edu", "gov", "biz", "info", "ai", "dev", "me", "uk", "us"}
)

_STOPWORDS_BEFORE_USERNAME: frozenset[str] = frozenset(
    {
        "upi",
        "vpa",
        "id",
        "is",
        "hai",
        "mera",
        "meri",
        "mere",
        "my",
        "to",
        "on",
        "pe",
        "par",
        "ko",
        "ka",
        "ki",
        "ke",
        "se",
        "send",
        "transfer",
        "pay",
        "paid",
        "bhejo",
        "bhej",
        "bhejna",
        "bhejiye",
        "karo",
        "kar",
        "dena",
        "de",
        "bhai",
        "bro",
        "sir",
        "madam",
        "please",
        "pls",
        "from",
        "for",
        "via",
        "at",
        "and",
        "aur",
        "ya",
        "handle",
        "account",
        "number",
    }
)

_PUNCT_WORDS: dict[str, str] = {
    "dot": ".",
    "point": ".",
    "underscore": "_",
    "under": "_",  # handled carefully only before "score"
    "dash": "-",
    "hyphen": "-",
}

_UPI_CONTEXT_WORDS: frozenset[str] = frozenset({"upi", "vpa", "handle", "id", "gpay", "phonepe", "paytm", "bhim"})

_TOKEN_RE = re.compile(r"[A-Za-z0-9._-]+|@|[,:;!?]+")
_VALID_USERNAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,254}[a-z0-9]$|^[a-z0-9]{2}$")
_VALID_HANDLE_RE = re.compile(r"^[a-z0-9]{2,32}$")
_DIRECT_AT_RE = re.compile(
    r"(?<![A-Za-z0-9._-])([A-Za-z0-9][A-Za-z0-9._-]{1,63})\s*@\s*([A-Za-z0-9.-]+(?:\s+[A-Za-z0-9]+){0,2})"
)


def _is_email_handle(handle_raw: str) -> bool:
    low = handle_raw.lower().strip()
    if "." in low:
        parts = [p for p in low.split(".") if p]
        if any(p in _EMAIL_TLDS or p in _EMAIL_DOMAINS for p in parts):
            return True
        return True
    return low in _EMAIL_DOMAINS


def _match_handle_from_tokens(
    tokens: list[tuple[str, int, int]], start_idx: int
) -> tuple[str, int, int, bool] | None:
    """Match a canonical UPI handle starting at tokens[start_idx].

    Returns (canonical_handle, next_token_idx, end_char_offset, is_known).
    """
    if start_idx >= len(tokens):
        return None

    # Check if next tokens form an email domain with dot (e.g., "gmail . com" or "gmail.com")
    first = tokens[start_idx][0].lower()
    if "." in first or first in _EMAIL_DOMAINS:
        return None
    if start_idx + 1 < len(tokens) and tokens[start_idx + 1][0] == ".":
        return None
    if start_idx + 2 < len(tokens) and tokens[start_idx + 1][0].lower() == "dot":
        tld = tokens[start_idx + 2][0].lower()
        if tld in _EMAIL_TLDS:
            return None

    # Try longest alias match (up to 3 tokens)
    for size in (3, 2):
        if start_idx + size <= len(tokens):
            phrase = " ".join(tokens[start_idx + k][0].lower() for k in range(size))
            if phrase in SPOKEN_HANDLE_ALIASES:
                canonical = SPOKEN_HANDLE_ALIASES[phrase]
                end_pos = tokens[start_idx + size - 1][2]
                return canonical, start_idx + size, end_pos, True

    # Single token check
    cleaned = first.strip(".,:;!?")
    if cleaned in KNOWN_UPI_HANDLES:
        return cleaned, start_idx + 1, tokens[start_idx][2], True
    if cleaned in SPOKEN_HANDLE_ALIASES:
        return SPOKEN_HANDLE_ALIASES[cleaned], start_idx + 1, tokens[start_idx][2], True

    # Unknown single alphanumeric handle (reject common stopwords/prepositions/email words)
    if (
        _VALID_HANDLE_RE.match(cleaned)
        and cleaned not in _EMAIL_DOMAINS
        and cleaned not in _STOPWORDS_BEFORE_USERNAME
        and not cleaned.isdigit()
    ):
        return cleaned, start_idx + 1, tokens[start_idx][2], False

    return None


def _build_spoken_username(
    tokens: list[tuple[str, int, int]], sep_idx: int
) -> tuple[str, int, bool] | None:
    """Walk backwards from `sep_idx` to reconstruct a spoken/written UPI username.

    Returns (username, start_char_offset, used_spoken_transforms) or None.
    """
    raw_window: list[tuple[str, int, int]] = []
    idx = sep_idx - 1
    while idx >= 0 and len(raw_window) < 18:
        tok, s, e = tokens[idx]
        low = tok.lower()
        if tok in (",", ":", ";", "!", "?", "@"):
            break
        # Handle "bhej do", "kar do", "de do" so "do" isn't consumed as digit 2
        if low == "do" and idx >= 1 and tokens[idx - 1][0].lower() in {
            "bhej",
            "bhejo",
            "kar",
            "karo",
            "de",
            "bol",
            "likh",
        }:
            break
        if low in _STOPWORDS_BEFORE_USERNAME:
            break
        raw_window.append((tok, s, e))
        idx -= 1

    if not raw_window:
        return None
    raw_window.reverse()

    # Trim leading punctuation words (e.g. "dot rahul")
    while raw_window and raw_window[0][0].lower() in _PUNCT_WORDS:
        raw_window.pop(0)
    if not raw_window:
        return None

    # Count spoken single digits to decide whether Hindi/English digit words should be converted
    spoken_digit_run = sum(1 for tok, _, _ in raw_window if tok.lower() in SINGLE_DIGITS)
    convert_word_digits = spoken_digit_run >= 3

    pieces: list[str] = []
    used_spoken = False
    i = 0
    while i < len(raw_window):
        tok, _, _ = raw_window[i]
        low = tok.lower()

        if low in ("dot", "point"):
            pieces.append(".")
            used_spoken = True
            i += 1
            continue
        if low in ("underscore", "dash", "hyphen"):
            pieces.append("_" if low == "underscore" else "-")
            used_spoken = True
            i += 1
            continue
        if low == "under" and i + 1 < len(raw_window) and raw_window[i + 1][0].lower() == "score":
            pieces.append("_")
            used_spoken = True
            i += 2
            continue
        if convert_word_digits and low in SINGLE_DIGITS:
            pieces.append(SINGLE_DIGITS[low])
            if not low.isdigit():
                used_spoken = True
            i += 1
            continue
        if low == "double" and i + 1 < len(raw_window) and raw_window[i + 1][0].lower() in SINGLE_DIGITS:
            d = SINGLE_DIGITS[raw_window[i + 1][0].lower()]
            pieces.append(d * 2)
            used_spoken = True
            i += 2
            continue
        if low == "triple" and i + 1 < len(raw_window) and raw_window[i + 1][0].lower() in SINGLE_DIGITS:
            d = SINGLE_DIGITS[raw_window[i + 1][0].lower()]
            pieces.append(d * 3)
            used_spoken = True
            i += 2
            continue

        # Ordinary word/alphanumeric token inside username:
        # If there are multiple bare words without dots/digits (e.g. "please send rahul"),
        # keep only the trailing token(s) after the last non-username break.
        if re.fullmatch(r"[a-z0-9._-]+", low):
            pieces.append(low)
            i += 1
        else:
            pieces.clear()
            i += 1

    # If user wrote "mera naam rahul" -> keep only the last contiguous identifier unless joined by ._-/digits
    if not used_spoken and len(raw_window) > 1 and not all(
        t[0].isdigit() or "." in t[0] or "_" in t[0] or "-" in t[0] for t in raw_window
    ):
        # Keep only the final token if preceding tokens were natural prose words without punctuation links
        last_tok, last_s, _ = raw_window[-1]
        last_low = last_tok.lower()
        if re.fullmatch(r"[a-z0-9._-]{2,64}", last_low):
            return last_low, last_s, False
        return None

    username = "".join(pieces).strip("._-")
    if not username or ".." in username or not _VALID_USERNAME_RE.match(username):
        return None

    return username, raw_window[0][1], used_spoken


def parse_upi(text: str) -> list[ParsedEntity]:
    """Extract written and spoken UPI IDs from text."""
    if not text or not text.strip():
        return []

    entities: list[ParsedEntity] = []
    occupied: list[tuple[int, int]] = []

    def overlaps(s: int, e: int) -> bool:
        return any(s < oe and e > os for os, oe in occupied)

    # Stage A: Direct `@` matches (handles `a@okicici`, `a @ ok axis`, rejects emails)
    for m in _DIRECT_AT_RE.finditer(text):
        username = m.group(1).lower().strip("._-")
        after = m.group(2).strip()
        if not username or not _VALID_USERNAME_RE.match(username):
            continue

        # Check multi-word alias first, then first token
        after_words = after.lower().split()
        handle = None
        is_known = False
        used_words = 1

        if _is_email_handle(after_words[0]):
            continue

        for size in (3, 2):
            if len(after_words) >= size:
                phrase = " ".join(after_words[:size])
                if phrase in SPOKEN_HANDLE_ALIASES:
                    handle = SPOKEN_HANDLE_ALIASES[phrase]
                    is_known = True
                    used_words = size
                    break

        if handle is None:
            cand = after_words[0].rstrip(".,:;!?")
            if _is_email_handle(cand):
                continue
            if cand in KNOWN_UPI_HANDLES:
                handle = cand
                is_known = True
            elif cand in SPOKEN_HANDLE_ALIASES:
                handle = SPOKEN_HANDLE_ALIASES[cand]
                is_known = True
            elif _VALID_HANDLE_RE.match(cand):
                handle = cand
                is_known = False
            else:
                continue

        # Compute exact end position covering only `used_words` of group(2)
        g2_start = m.start(2)
        if used_words == len(after_words):
            end_pos = m.end(2)
        else:
            # Find end of the used_words-th word inside group(2)
            word_spans = list(re.finditer(r"\S+", m.group(2)))
            end_pos = g2_start + word_spans[used_words - 1].end()
        raw = text[m.start(1) : end_pos]
        # Strip trailing punctuation if captured
        trimmed = raw.rstrip(".,:;!?")
        end_pos = m.start(1) + len(trimmed)

        reasons: list[str] = ["direct_at_symbol"]
        if is_known:
            conf = 0.96 if used_words == 1 else 0.91
            if used_words > 1:
                reasons.append("spaced_psp_handle")
        else:
            conf = 0.62
            reasons.append("unknown_upi_handle")

        upi = f"{username}@{handle}"
        entities.append(
            ParsedEntity(
                kind=EntityType.UPI_ID,
                value=upi,
                formatted=upi,
                confidence=conf,
                span=EntitySpan(m.start(1), end_pos, text[m.start(1) : end_pos]),
                reasons=tuple(reasons),
                metadata={
                    "username": username,
                    "handle": handle,
                    "provider": KNOWN_UPI_HANDLES.get(handle),
                    "known_handle": is_known,
                },
            )
        )
        occupied.append((m.start(1), end_pos))

    # Stage B: Spoken `@` (`at the rate`, `at the rate of`, `at rate`, or contextual `at`)
    tokens = [(m.group(0), m.start(), m.end()) for m in _TOKEN_RE.finditer(text)]
    n = len(tokens)
    i = 0
    while i < n:
        low = tokens[i][0].lower()
        sep_end_idx = None
        explicit_at_phrase = False

        if (
            i + 3 < n
            and low == "at"
            and tokens[i + 1][0].lower() == "the"
            and tokens[i + 2][0].lower() == "rate"
            and tokens[i + 3][0].lower() == "of"
        ):
            sep_end_idx = i + 4
            explicit_at_phrase = True
        elif (
            i + 2 < n
            and low == "at"
            and tokens[i + 1][0].lower() == "the"
            and tokens[i + 2][0].lower() == "rate"
        ):
            sep_end_idx = i + 3
            explicit_at_phrase = True
        elif i + 1 < n and low == "at" and tokens[i + 1][0].lower() == "rate":
            sep_end_idx = i + 2
            explicit_at_phrase = True
        elif low == "at":
            sep_end_idx = i + 1
            explicit_at_phrase = False

        if sep_end_idx is None or sep_end_idx >= n:
            i += 1
            continue

        handle_match = _match_handle_from_tokens(tokens, sep_end_idx)
        if handle_match is None:
            i += 1
            continue

        handle, next_idx, end_pos, is_known = handle_match
        # Guard against casual English "at" (e.g. "meet me at office" or "at 5"):
        # If separator was bare "at", require either a known UPI handle OR explicit UPI context nearby.
        has_context = any(
            tokens[k][0].lower() in _UPI_CONTEXT_WORDS for k in range(max(0, i - 6), i)
        )
        if not explicit_at_phrase and not is_known and not has_context:
            i += 1
            continue

        user_match = _build_spoken_username(tokens, i)
        if user_match is None:
            i += 1
            continue

        username, start_pos, used_spoken = user_match
        if overlaps(start_pos, end_pos):
            i += 1
            continue

        reasons = ["spoken_at_separator" if explicit_at_phrase else "contextual_at_separator"]
        if is_known:
            conf = 0.89 if not used_spoken else 0.86
            if used_spoken:
                reasons.append("spoken_username_tokens")
        else:
            conf = 0.60
            reasons.append("unknown_upi_handle")

        upi = f"{username}@{handle}"
        entities.append(
            ParsedEntity(
                kind=EntityType.UPI_ID,
                value=upi,
                formatted=upi,
                confidence=conf,
                span=EntitySpan(start_pos, end_pos, text[start_pos:end_pos]),
                reasons=tuple(reasons),
                metadata={
                    "username": username,
                    "handle": handle,
                    "provider": KNOWN_UPI_HANDLES.get(handle),
                    "known_handle": is_known,
                },
            )
        )
        occupied.append((start_pos, end_pos))
        i = next_idx

    entities.sort(key=lambda e: e.span.start)
    return entities
