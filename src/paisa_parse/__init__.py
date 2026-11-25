"""paisa-parse: Hinglish & Indian-English spoken financial entity parser."""

from paisa_parse.engine import (
    parse,
    parse_amount,
    parse_digit_strings,
    parse_ifsc_codes,
    parse_upi_ids,
)
from paisa_parse.lexicon import amount_to_words_en_in, format_inr
from paisa_parse.policy import ConfirmPolicy
from paisa_parse.types import (
    ConfirmAction,
    EntitySpan,
    EntityType,
    ParsedEntity,
    ParseResult,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "ConfirmAction",
    "ConfirmPolicy",
    "EntitySpan",
    "EntityType",
    "ParseResult",
    "ParsedEntity",
    "amount_to_words_en_in",
    "format_inr",
    "parse",
    "parse_amount",
    "parse_digit_strings",
    "parse_ifsc_codes",
    "parse_upi_ids",
]
