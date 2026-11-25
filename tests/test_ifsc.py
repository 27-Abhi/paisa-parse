"""Unit tests for written and spoken Indian IFSC code parsing."""

import pytest

from paisa_parse import ConfirmAction, parse_ifsc_codes


@pytest.mark.parametrize(
    ("text", "expected_code", "expected_action"),
    [
        ("SBIN0001234", "SBIN0001234", ConfirmAction.ACCEPT),
        ("HDFC 0000240", "HDFC0000240", ConfirmAction.ACCEPT),
        ("ICIC-000-0104", "ICIC0000104", ConfirmAction.ACCEPT),
        ("IFSC SBIN triple zero ek do teen chaar", "SBIN0001234", ConfirmAction.ACCEPT),
        ("ifsc is h d f c zero zero zero zero two four zero", "HDFC0000240", ConfirmAction.ACCEPT),
        ("ifsc U T I B zero double zero nine eight seven six", "UTIB0009876", ConfirmAction.ACCEPT),
        ("PUNB zero one two three four five six", "PUNB0123456", ConfirmAction.ACCEPT),
        ("SBINO001234", "SBIN0001234", ConfirmAction.CONFIRM),
        ("XYZW0001234", "XYZW0001234", ConfirmAction.CONFIRM),
        ("ifsc IDFB oh double zero four three two one", "IDFB0004321", ConfirmAction.CONFIRM),
        ("ifsc code SBIN00012", "SBIN00012", ConfirmAction.REPROMPT),
        ("ifsc code SBIN1001234", "SBIN1001234", ConfirmAction.REPROMPT),
    ],
)
def test_ifsc_variants(text: str, expected_code: str, expected_action: ConfirmAction) -> None:
    ents = parse_ifsc_codes(text)
    assert len(ents) == 1
    assert ents[0].value == expected_code
    assert ents[0].action == expected_action


def test_ifsc_metadata_includes_bank_name() -> None:
    ents = parse_ifsc_codes("SBIN0001234")
    assert ents[0].metadata["bank_name"] == "State Bank of India"
    assert ents[0].metadata["known_bank"] is True
