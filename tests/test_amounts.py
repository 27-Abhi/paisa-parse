"""Unit tests for Hinglish & Indian-English monetary amount parsing."""

from decimal import Decimal

import pytest

from paisa_parse import ConfirmAction, format_inr, parse_amount


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("dedh lakh", Decimal("150000")),
        ("dedh hazaar", Decimal("1500")),
        ("dedh sau", Decimal("150")),
        ("dhai lakh", Decimal("250000")),
        ("dhai crore", Decimal("25000000")),
        ("dhai hazaar", Decimal("2500")),
        ("sava hazaar", Decimal("1250")),
        ("sava do lakh", Decimal("225000")),
        ("sawa paanch hazaar", Decimal("5250")),
        ("sava lakh", Decimal("125000")),
        ("paune sau", Decimal("75")),
        ("paune do lakh", Decimal("175000")),
        ("paune lakh", Decimal("75000")),
        ("saade teen lakh", Decimal("350000")),
        ("saade barah hazaar", Decimal("12500")),
        ("saade 4 lakh", Decimal("450000")),
        ("aadha lakh", Decimal("50000")),
        ("paav lakh", Decimal("25000")),
    ],
)
def test_colloquial_fractions(text: str, expected: Decimal) -> None:
    ents = parse_amount(text)
    assert len(ents) == 1
    assert ents[0].value == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("ek lakh pachaas hazaar rupaye", Decimal("150000")),
        ("do crore paanch lakh das hazaar paanch sau", Decimal("20510500")),
        ("ek hazaar do sau pachees rupaye", Decimal("1225")),
        ("teen lakh twenty five thousand", Decimal("325000")),
        ("unnis hazaar nau sau ninyanve", Decimal("19999")),
        ("chhattees hazaar do sau", Decimal("36200")),
        ("dedh lakh aur paanch hazaar", Decimal("155000")),
        ("pachas rupaye pachees paise", Decimal("50.25")),
        ("ek sau rupaye aur pachaas paise", Decimal("100.50")),
        ("500 rupees 75 paise", Decimal("500.75")),
        ("pachaas paise", Decimal("0.50")),
        ("₹1,50,000", Decimal("150000")),
        ("Rs. 45,000.50", Decimal("45000.50")),
        ("INR 2500", Decimal("2500")),
        ("50k", Decimal("50000")),
        ("1.25 cr", Decimal("12500000")),
        ("डेढ़ लाख रुपये", Decimal("150000")),
        ("५०० रुपये", Decimal("500")),
    ],
)
def test_compound_written_and_devanagari_amounts(text: str, expected: Decimal) -> None:
    ents = parse_amount(text)
    assert len(ents) == 1
    assert ents[0].value == expected


def test_format_inr_indian_grouping() -> None:
    assert format_inr(Decimal("75")) == "₹75"
    assert format_inr(Decimal("1500")) == "₹1,500"
    assert format_inr(Decimal("150000")) == "₹1,50,000"
    assert format_inr(Decimal("12500000")) == "₹1,25,00,000"
    assert format_inr(Decimal("50.25")) == "₹50.25"
    assert format_inr(Decimal("100.50")) == "₹100.50"


def test_noisy_asr_variants_trigger_confirm() -> None:
    for text in ("ded sau rupaye", "paanch so rupaye", "pone teen hazar"):
        ents = parse_amount(text)
        assert len(ents) == 1
        assert ents[0].action == ConfirmAction.CONFIRM


def test_amount_negative_controls() -> None:
    negatives = [
        "so what is my account balance",
        "I have two bank accounts",
        "meet me at 5 pm",
        "aadha ghanta ruk jao",
        "send it now please",
    ]
    for text in negatives:
        assert parse_amount(text) == []
