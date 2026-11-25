"""Unit tests for unified parse() engine, overlap resolution, and ConfirmPolicy."""

import json
from decimal import Decimal

from paisa_parse import ConfirmAction, ConfirmPolicy, EntityType, parse


def test_multi_entity_and_normalized_text() -> None:
    res = parse(
        "bhai rahul dot verma at ok icici pe dedh lakh bhej do",
        policy=ConfirmPolicy.balanced(language="hinglish"),
    )
    assert len(res.entities) == 2
    upi = res.by_kind(EntityType.UPI_ID)[0]
    amt = res.by_kind(EntityType.AMOUNT)[0]

    assert upi.value == "rahul.verma@okicici"
    assert upi.action == ConfirmAction.ACCEPT
    assert amt.value == Decimal("150000")
    assert amt.action == ConfirmAction.CONFIRM
    assert "high_value_threshold" in amt.reasons
    assert "₹1,50,000" in (amt.confirm_prompt or "")
    assert "rahul.verma@okicici" in res.normalized_text
    assert "₹1,50,000" in res.normalized_text


def test_upi_suppresses_embedded_phone_digits() -> None:
    res = parse("pay Rs 2500 to 9876543210@okaxis")
    assert [e.kind for e in res.entities] == [EntityType.AMOUNT, EntityType.UPI_ID]
    assert res.by_kind("digits") == ()


def test_ifsc_suppresses_embedded_digits_or_amounts() -> None:
    res = parse("sava sau rupaye bhejo SBINO001234 pe")
    assert [e.kind for e in res.entities] == [EntityType.AMOUNT, EntityType.IFSC]
    assert res.entities[0].value == Decimal("125")
    assert res.entities[1].value == "SBIN0001234"
    assert res.entities[1].action == ConfirmAction.CONFIRM


def test_policy_presets_and_json_serialization() -> None:
    text = "pay 15000 rupees to rahul@okicici"
    strict_res = parse(text, policy=ConfirmPolicy.strict(language="en-IN"))
    permissive_res = parse(text, policy=ConfirmPolicy.permissive(language="en-IN"))

    assert strict_res.by_kind("amount")[0].action == ConfirmAction.CONFIRM
    assert strict_res.by_kind("upi_id")[0].action == ConfirmAction.CONFIRM
    assert permissive_res.by_kind("amount")[0].action == ConfirmAction.ACCEPT
    assert permissive_res.by_kind("upi_id")[0].action == ConfirmAction.ACCEPT

    encoded = json.dumps(strict_res.to_dict(), ensure_ascii=False)
    decoded = json.loads(encoded)
    assert decoded["needs_confirmation"] is True
    assert len(decoded["entities"]) == 2
