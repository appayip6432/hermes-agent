"""Structured OTP identifiers must not broaden recognition of unrelated fields."""

import pytest

from agent.vault_login_classifier import LoginControl, classify_otp_controls


@pytest.mark.parametrize("name", [
    "totpPin", "otpCode", "totpToken", "TOTPPIN", "OTPCODE", "TOTPTOKEN",
    "code totpPin", "totpPin code", "code\totpCode", "code totpToken",
])
@pytest.mark.parametrize("input_type", ["text", "tel", "number", "password", ""])
def test_structured_otp_name_or_id_is_a_code_target(name, input_type):
    control = LoginControl("", 0, 2, "Enter code", name, input_type)
    targets = classify_otp_controls([control])
    assert len(targets) == 1
    assert targets[0].control == control
    assert (targets[0].token, targets[0].score) == ("one-time-code", 70)


@pytest.mark.parametrize("name,input_type", [
    (name, "text") for name in (
        "cardSecurityCode", "code", "promoCode", "postalCode", "discountCode",
        "totpPinExtra", "prefixotpCode", "totpTokenSuffix", "code unrelatedId",
    )
] + [
    (name, input_type)
    for name in ("totpPin", "otpCode", "totpToken")
    for input_type in ("email", "checkbox", "hidden", "submit")
])
def test_unrelated_identifiers_and_non_code_input_types_are_not_otp(name, input_type):
    control = LoginControl("", 0, 2, "Enter code", name, input_type)
    assert classify_otp_controls([control]) == []
