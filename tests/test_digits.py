"""Unit tests for spoken and mixed digit-string parsing."""

from paisa_parse import ConfirmAction, parse_digit_strings


def test_spoken_hindi_and_english_phone_numbers() -> None:
    res1 = parse_digit_strings("nau aath saat chhe paanch chaar teen do ek shunya")
    assert len(res1) == 1
    assert res1[0].value == "9876543210"
    assert res1[0].metadata["subtype"] == "phone"
    assert res1[0].action == ConfirmAction.ACCEPT

    res2 = parse_digit_strings("nine eight seven six five four three two one zero")
    assert len(res2) == 1
    assert res2[0].value == "9876543210"
    assert res2[0].formatted == "98765 43210"


def test_repeat_modifiers_and_baar_syntax() -> None:
    res = parse_digit_strings("phone number eight eight double two triple five one zero nine")
    assert len(res) == 1
    assert res[0].value == "8822555109"

    res_baar = parse_digit_strings("number hai nau aath teen baar shunya ek do teen chaar")
    assert len(res_baar) == 1
    assert res_baar[0].value == "980001234"


def test_otp_pin_account_subtypes() -> None:
    otp = parse_digit_strings("otp hai chaar aath do nau")
    assert len(otp) == 1
    assert otp[0].value == "4829"
    assert otp[0].metadata["subtype"] == "otp"

    pin = parse_digit_strings("mpin tripal two five")
    assert len(pin) == 1
    assert pin[0].value == "2225"
    assert pin[0].metadata["subtype"] == "pin"

    acct = parse_digit_strings("account number 302918475612")
    assert len(acct) == 1
    assert acct[0].value == "302918475612"
    assert acct[0].metadata["subtype"] == "account"


def test_oh_as_zero_and_length_validation() -> None:
    double_oh = parse_digit_strings("mobile number nine eight oh oh seven six five four three two")
    assert len(double_oh) == 1
    assert double_oh[0].value == "9800765432"
    assert double_oh[0].action == ConfirmAction.CONFIRM

    short_phone = parse_digit_strings("mobile number nau aath saat chhe paanch chaar teen do ek")
    assert len(short_phone) == 1
    assert short_phone[0].action == ConfirmAction.REPROMPT

    short_otp = parse_digit_strings("otp is one two three")
    assert len(short_otp) == 1
    assert short_otp[0].value == "123"
    assert short_otp[0].action == ConfirmAction.CONFIRM


def test_digit_negative_controls() -> None:
    for text in (
        "no thanks I do not want a loan",
        "oh okay got it",
        "year 2026 statement",
        "one two three go",
    ):
        assert parse_digit_strings(text) == []
