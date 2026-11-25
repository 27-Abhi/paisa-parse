"""Lexicon, ASR phonetic variants, and Indian currency formatting helpers."""

from __future__ import annotations

from decimal import Decimal

# Devanagari digits to ASCII digits
DEVANAGARI_DIGITS: dict[str, str] = {
    "०": "0",
    "१": "1",
    "२": "2",
    "३": "3",
    "४": "4",
    "५": "5",
    "६": "6",
    "७": "7",
    "८": "8",
    "९": "9",
}
DEVANAGARI_TRANS = str.maketrans(DEVANAGARI_DIGITS)

# Common Devanagari number/fraction/scale/currency tokens mapped to Romanized equivalents
DEVANAGARI_WORDS: dict[str, str] = {
    "शून्य": "shunya",
    "एक": "ek",
    "दो": "do",
    "तीन": "teen",
    "चार": "chaar",
    "पांच": "paanch",
    "पाँच": "paanch",
    "छह": "chhe",
    "छः": "chhe",
    "सात": "saat",
    "आठ": "aath",
    "नौ": "nau",
    "दस": "das",
    "ग्यारह": "gyarah",
    "बारह": "barah",
    "पंद्रह": "pandrah",
    "बीस": "bees",
    "पच्चीस": "pachees",
    "तीस": "tees",
    "चालीस": "chalis",
    "पचास": "pachas",
    "साठ": "saath",
    "सत्तर": "sattar",
    "अस्सी": "assi",
    "नब्बे": "nabbe",
    "सौ": "sau",
    "हज़ार": "hazaar",
    "हजार": "hazaar",
    "लाख": "lakh",
    "करोड़": "crore",
    "करोड": "crore",
    "डेढ़": "dedh",
    "डेढ": "dedh",
    "ढाई": "dhai",
    "सवा": "sava",
    "पौने": "paune",
    "साढ़े": "saade",
    "साढे": "saade",
    "आधा": "aadha",
    "पाव": "paav",
    "रुपये": "rupaye",
    "रुपए": "rupaye",
    "रुपया": "rupiya",
    "पैसे": "paise",
    "पैसा": "paisa",
    "और": "aur",
}

# Romanized Hindi cardinal numbers 0-99 plus common ASR phonetic variants.
HINDI_NUMBERS: dict[str, int] = {
    "shunya": 0,
    "shoonya": 0,
    "sunya": 0,
    "sifr": 0,
    "ek": 1,
    "aik": 1,
    "ikk": 1,
    "do": 2,
    "doo": 2,
    "teen": 3,
    "tin": 3,
    "chaar": 4,
    "char": 4,
    "paanch": 5,
    "panch": 5,
    "paach": 5,
    "chhe": 6,
    "chhah": 6,
    "che": 6,
    "cheh": 6,
    "chay": 6,
    "saat": 7,
    "sat": 7,
    "aath": 8,
    "ath": 8,
    "aat": 8,
    "nau": 9,
    "nao": 9,
    "now": 9,  # disambiguated contextually in parsers when safe? Wait: keep "now" out of HINDI_NUMBERS to avoid English false positives!
    "das": 10,
    "dus": 10,
    "gyarah": 11,
    "gyara": 11,
    "gyaarah": 11,
    "barah": 12,
    "bara": 12,
    "baarah": 12,
    "terah": 13,
    "tera": 13,
    "chaudah": 14,
    "chauda": 14,
    "choudah": 14,
    "pandrah": 15,
    "pandra": 15,
    "solah": 16,
    "sola": 16,
    "satrah": 17,
    "satra": 17,
    "atharah": 18,
    "athara": 18,
    "attharah": 18,
    "unnis": 19,
    "unees": 19,
    "unnees": 19,
    "bees": 20,
    "bis": 20,
    "ikkees": 21,
    "ikkis": 21,
    "ikis": 21,
    "baees": 22,
    "bais": 22,
    "baais": 22,
    "teees": 23,
    "teis": 23,
    "chaubees": 24,
    "chaubis": 24,
    "chobis": 24,
    "pachees": 25,
    "pachis": 25,
    "pachchis": 25,
    "chhabbees": 26,
    "chhabbis": 26,
    "chhabis": 26,
    "sattaees": 27,
    "sattais": 27,
    "satais": 27,
    "atthaees": 28,
    "atthais": 28,
    "athais": 28,
    "untees": 29,
    "untis": 29,
    "tees": 30,
    "tis": 30,
    "ikattees": 31,
    "ikattis": 31,
    "iktis": 31,
    "battees": 32,
    "battis": 32,
    "taintees": 33,
    "taintis": 33,
    "tetis": 33,
    "chauntees": 34,
    "chauntis": 34,
    "chautis": 34,
    "paintees": 35,
    "paintis": 35,
    "pentis": 35,
    "chattees": 36,
    "chhattees": 36,
    "chattis": 36,
    "chhattis": 36,
    "saintees": 37,
    "saintis": 37,
    "sentis": 37,
    "adtees": 38,
    "adtis": 38,
    "artees": 38,
    "untalees": 39,
    "untalis": 39,
    "chalees": 40,
    "chalis": 40,
    "chaalis": 40,
    "iktalees": 41,
    "iktalis": 41,
    "bayalees": 42,
    "bayalis": 42,
    "byalis": 42,
    "taintalees": 43,
    "taintalis": 43,
    "tetalis": 43,
    "chawalees": 44,
    "chawalis": 44,
    "chaualis": 44,
    "paintalees": 45,
    "paintalis": 45,
    "pentalis": 45,
    "chiyalees": 46,
    "chiyalis": 46,
    "chhayalis": 46,
    "saintalees": 47,
    "saintalis": 47,
    "adtalees": 48,
    "adtalis": 48,
    "artalis": 48,
    "unchaas": 49,
    "unchas": 49,
    "pachas": 50,
    "pachaas": 50,
    "ikyavan": 51,
    "ikavan": 51,
    "bavan": 52,
    "baavan": 52,
    "tirpan": 53,
    "trepan": 53,
    "chauvan": 54,
    "chawan": 54,
    "pachpan": 55,
    "chhappan": 56,
    "chappan": 56,
    "sattavan": 57,
    "satavan": 57,
    "atthavan": 58,
    "athavan": 58,
    "unsath": 59,
    "saath": 60,
    "sath": 60,
    "iksath": 61,
    "basath": 62,
    "baasath": 62,
    "tirsath": 63,
    "tresath": 63,
    "chausath": 64,
    "chosath": 64,
    "painsath": 65,
    "pensath": 65,
    "chiyasath": 66,
    "chhiyasath": 66,
    "sarsath": 67,
    "sadsath": 67,
    "adsath": 68,
    "arsath": 68,
    "unhattar": 69,
    "sattar": 70,
    "ikhattar": 71,
    "bahattar": 72,
    "tihattar": 73,
    "chauhattar": 74,
    "pachhattar": 75,
    "pachattar": 75,
    "chhihattar": 76,
    "chihattar": 76,
    "sathattar": 77,
    "satattar": 77,
    "athhattar": 78,
    "athattar": 78,
    "unyasi": 79,
    "unasi": 79,
    "assi": 80,
    "assee": 80,
    "ikyasi": 81,
    "ikasi": 81,
    "bayasi": 82,
    "byasi": 82,
    "tirasi": 83,
    "chaurasi": 84,
    "pachasi": 85,
    "pachaasi": 85,
    "chhiyasi": 86,
    "chiyasi": 86,
    "sattasi": 87,
    "satasi": 87,
    "atthasi": 88,
    "athasi": 88,
    "navasi": 89,
    "nawasi": 89,
    "nabbe": 90,
    "nabbey": 90,
    "ikyanve": 91,
    "ikyanbe": 91,
    "banve": 92,
    "baanve": 92,
    "banbe": 92,
    "tiranve": 93,
    "tiranbe": 93,
    "chauranve": 94,
    "chauranbe": 94,
    "pachanve": 95,
    "pachanbe": 95,
    "chhiyanve": 96,
    "chiyanve": 96,
    "sattanve": 97,
    "satanve": 97,
    "atthanve": 98,
    "athanve": 98,
    "ninyanve": 99,
    "ninyanbe": 99,
    "ninanve": 99,
}
# Remove "now" from HINDI_NUMBERS so ordinary English sentences ("pay now") don't misparse.
HINDI_NUMBERS.pop("now", None)

ENGLISH_ONES: dict[str, int] = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
}

ENGLISH_TENS: dict[str, int] = {
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}

SINGLE_DIGITS: dict[str, str] = {
    "0": "0",
    "1": "1",
    "2": "2",
    "3": "3",
    "4": "4",
    "5": "5",
    "6": "6",
    "7": "7",
    "8": "8",
    "9": "9",
    "zero": "0",
    "shunya": "0",
    "shoonya": "0",
    "sunya": "0",
    "sifr": "0",
    "one": "1",
    "ek": "1",
    "aik": "1",
    "two": "2",
    "do": "2",
    "doo": "2",
    "three": "3",
    "teen": "3",
    "tin": "3",
    "four": "4",
    "chaar": "4",
    "char": "4",
    "five": "5",
    "paanch": "5",
    "panch": "5",
    "paach": "5",
    "six": "6",
    "chhe": "6",
    "chhah": "6",
    "che": "6",
    "cheh": "6",
    "chay": "6",
    "seven": "7",
    "saat": "7",
    "sat": "7",
    "eight": "8",
    "aath": "8",
    "ath": "8",
    "aat": "8",
    "nine": "9",
    "nau": "9",
    "nao": "9",
}

REPEAT_MULTIPLIERS: dict[str, int] = {
    "double": 2,
    "dabal": 2,
    "doble": 2,
    "triple": 3,
    "tripal": 3,
    "quadruple": 4,
}

# Indian and English scale words -> multiplier
SCALES: dict[str, int] = {
    "sau": 100,
    "hundred": 100,
    "hazaar": 1_000,
    "hazar": 1_000,
    "hajar": 1_000,
    "hajaar": 1_000,
    "thousand": 1_000,
    "k": 1_000,
    "grand": 1_000,
    "lakh": 100_000,
    "lakhs": 100_000,
    "lac": 100_000,
    "lacs": 100_000,
    "laakh": 100_000,
    "laks": 100_000,
    "crore": 10_000_000,
    "crores": 10_000_000,
    "karod": 10_000_000,
    "karor": 10_000_000,
    "karore": 10_000_000,
    "cr": 10_000_000,
    "arab": 1_000_000_000,
}

# Colloquial Hindi direct fractional values
DIRECT_FRACTIONS: dict[str, Decimal] = {
    "dedh": Decimal("1.5"),
    "derh": Decimal("1.5"),
    "deydh": Decimal("1.5"),
    "ded": Decimal("1.5"),
    "dhai": Decimal("2.5"),
    "dhaai": Decimal("2.5"),
    "adhayi": Decimal("2.5"),
    "adai": Decimal("2.5"),
    "aadha": Decimal("0.5"),
    "adha": Decimal("0.5"),
    "half": Decimal("0.5"),
    "paav": Decimal("0.25"),
    "pau": Decimal("0.25"),
    "quarter": Decimal("0.25"),
}

# Prefix modifier fractions:
# - sava (+0.25, standalone before scale = 1.25)
# - paune (-0.25, standalone before scale = 0.75)
# - saade (+0.5, requires integer N after it)
PREFIX_FRACTION_DELTAS: dict[str, tuple[Decimal, Decimal | None]] = {
    "sava": (Decimal("0.25"), Decimal("1.25")),
    "sawa": (Decimal("0.25"), Decimal("1.25")),
    "paune": (Decimal("-0.25"), Decimal("0.75")),
    "pauna": (Decimal("-0.25"), Decimal("0.75")),
    "pone": (Decimal("-0.25"), Decimal("0.75")),
    "saade": (Decimal("0.5"), None),
    "sade": (Decimal("0.5"), None),
    "sadhe": (Decimal("0.5"), None),
    "saadhe": (Decimal("0.5"), None),
}

NOISY_ASR_VARIANTS: frozenset[str] = frozenset(
    {"ded", "derh", "deydh", "pone", "so", "sade", "sadhe", "adai", "pau"}
)

RUPEE_MARKERS: frozenset[str] = frozenset(
    {"rupaye", "rupaiye", "rupiya", "rupiye", "rupees", "rupee", "rs", "inr", "₹"}
)
PAISE_MARKERS: frozenset[str] = frozenset({"paisa", "paise"})

FINANCIAL_CONTEXT_WORDS: frozenset[str] = frozenset(
    {
        "send",
        "transfer",
        "pay",
        "paid",
        "bhejo",
        "bhejna",
        "bhej",
        "bhejiye",
        "dena",
        "de",
        "do",
        "nikalna",
        "withdraw",
        "deposit",
        "jama",
        "amount",
        "bill",
        "emi",
        "loan",
        "balance",
        "credit",
        "debit",
        "refund",
        "kitna",
        "kitne",
        "total",
        "charge",
        "fee",
        "rent",
        "salary",
        "payment",
        "upi",
    }
)


def format_inr(amount: Decimal) -> str:
    """Format a numeric amount using the Indian 3-2-2 digit grouping system with `₹`."""
    negative = amount < 0
    abs_val = abs(amount)
    if abs_val == abs_val.to_integral_value():
        int_part = str(int(abs_val))
        frac_part = ""
    else:
        quantized = f"{abs_val:.2f}".rstrip("0").rstrip(".")
        if "." in quantized:
            int_part, frac_part = quantized.split(".", 1)
            if len(frac_part) == 1:
                frac_part += "0"
            frac_part = "." + frac_part
        else:
            int_part = quantized
            frac_part = ""

    if len(int_part) <= 3:
        grouped = int_part
    else:
        last3 = int_part[-3:]
        rest = int_part[:-3]
        pairs: list[str] = []
        while len(rest) > 2:
            pairs.append(rest[-2:])
            rest = rest[:-2]
        if rest:
            pairs.append(rest)
        grouped = ",".join(reversed(pairs)) + "," + last3

    prefix = "-₹" if negative else "₹"
    return f"{prefix}{grouped}{frac_part}"


_ONES_WORDS = [
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
    "thirteen",
    "fourteen",
    "fifteen",
    "sixteen",
    "seventeen",
    "eighteen",
    "nineteen",
]
_TENS_WORDS = [
    "",
    "",
    "twenty",
    "thirty",
    "forty",
    "fifty",
    "sixty",
    "seventy",
    "eighty",
    "ninety",
]


def _under_100_words(n: int) -> str:
    if n < 20:
        return _ONES_WORDS[n]
    tens, ones = divmod(n, 10)
    return _TENS_WORDS[tens] if ones == 0 else f"{_TENS_WORDS[tens]} {_ONES_WORDS[ones]}"


def _int_to_indian_words(n: int) -> str:
    if n == 0:
        return "zero"
    parts: list[str] = []
    crores, rem = divmod(n, 10_000_000)
    if crores:
        parts.append(f"{_int_to_indian_words(crores)} crore")
    lakhs, rem = divmod(rem, 100_000)
    if lakhs:
        parts.append(f"{_under_100_words(lakhs)} lakh")
    thousands, rem = divmod(rem, 1_000)
    if thousands:
        parts.append(f"{_under_100_words(thousands)} thousand")
    hundreds, rem = divmod(rem, 100)
    if hundreds:
        parts.append(f"{_ONES_WORDS[hundreds]} hundred")
    if rem:
        parts.append(_under_100_words(rem))
    return " ".join(parts)


def amount_to_words_en_in(amount: Decimal) -> str:
    """Convert an INR Decimal amount into natural Indian-English TTS words."""
    abs_val = abs(amount)
    rupees = int(abs_val)
    paise = int(((abs_val - Decimal(rupees)) * 100).to_integral_value())

    parts: list[str] = []
    if rupees > 0 or paise == 0:
        unit = "rupee" if rupees == 1 else "rupees"
        parts.append(f"{_int_to_indian_words(rupees)} {unit}")
    if paise > 0:
        p_unit = "paisa" if paise == 1 else "paise"
        if parts:
            parts.append(f"and {_under_100_words(paise)} {p_unit}")
        else:
            parts.append(f"{_under_100_words(paise)} {p_unit}")
    return " ".join(parts)
