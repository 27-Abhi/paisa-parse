"""Unit tests for written and spoken Indian UPI ID parsing."""

import pytest

from paisa_parse import ConfirmAction, parse_upi_ids


@pytest.mark.parametrize(
    ("text", "expected_upi", "expected_action"),
    [
        ("rahul.sharma@okicici", "rahul.sharma@okicici", ConfirmAction.ACCEPT),
        ("send to 9876543210@ybl", "9876543210@ybl", ConfirmAction.ACCEPT),
        ("rahul dot verma at ok icici", "rahul.verma@okicici", ConfirmAction.ACCEPT),
        ("priya underscore k at the rate ybl", "priya_k@ybl", ConfirmAction.ACCEPT),
        ("rohit.kumar @ ok axis pe bhejo", "rohit.kumar@okaxis", ConfirmAction.ACCEPT),
        ("vpa is amit at the rate of ok sbi", "amit@oksbi", ConfirmAction.ACCEPT),
        ("neha dot singh at ok hdfc bank", "neha.singh@okhdfcbank", ConfirmAction.ACCEPT),
        ("nau aath saat chhe paanch chaar teen do ek shunya at ybl", "9876543210@ybl", ConfirmAction.ACCEPT),
        ("arjun dash 99 at a p l", "arjun-99@apl", ConfirmAction.ACCEPT),
        ("bhej do vikram at i b l", "vikram@ibl", ConfirmAction.ACCEPT),
        ("kavita at the rate custombank", "kavita@custombank", ConfirmAction.CONFIRM),
        ("deepak@unknownpsp", "deepak@unknownpsp", ConfirmAction.CONFIRM),
    ],
)
def test_upi_variants(text: str, expected_upi: str, expected_action: ConfirmAction) -> None:
    ents = parse_upi_ids(text)
    assert len(ents) == 1
    assert ents[0].value == expected_upi
    assert ents[0].action == expected_action


def test_upi_rejects_emails_and_casual_at() -> None:
    for text in (
        "priya@gmail.com pe email bhej do",
        "support@yahoo.co.in",
        "rahul dot sharma at gmail dot com",
        "meet me at 5 pm near the office",
        "please check my transaction history at home",
    ):
        assert parse_upi_ids(text) == []
