from unittest.mock import patch

from verifier import verify_email


def test_invalid_syntax():
    result = verify_email("not-an-email")
    assert result.final_status == "INVALID"
    assert result.syntax_status == "INVALID_FORMAT"


def test_likely_valid_with_mx():
    with patch("verifier._dns_status", return_value=("FOUND", "MX records found", ["mx.example.com"])):
        result = verify_email("person@example.com")
    assert result.final_status == "LIKELY_VALID"
    assert result.mx_status == "FOUND"


def test_disposable_is_risky():
    with patch("verifier._dns_status", return_value=("FOUND", "MX records found", ["mx.example.com"])):
        result = verify_email("person@mailinator.com", {"mailinator.com"})
    assert result.final_status == "RISKY"


def test_missing_domain_is_invalid():
    with patch("verifier._dns_status", return_value=("MISSING", "Domain does not exist", [])):
        result = verify_email("person@example.invalid")
    assert result.final_status == "INVALID"


def test_smtp_acceptance_is_not_claimed_active():
    with patch("verifier._dns_status", return_value=("FOUND", "MX records found", ["mx.example.com"])), patch("verifier._smtp_check", return_value=("ACCEPTED", "accepted")):
        result = verify_email("person@example.com", smtp_enabled=True)
    assert result.final_status == "ACCEPTED_BY_SERVER"
    assert "does not prove" in result.verification_reason


def test_smtp_554_recipient_rejection_is_invalid():
    with patch("verifier._dns_status", return_value=("FOUND", "MX records found", ["mx.example.com"])), patch("verifier._smtp_check", return_value=("REJECTED", "Server explicitly rejected the recipient (554)")):
        result = verify_email("asfweqr@ealamgroup.com", smtp_enabled=True)
    assert result.final_status == "INVALID"
    assert result.smtp_result == "REJECTED"


def test_role_flag_is_separate():
    with patch("verifier._dns_status", return_value=("FOUND", "MX records found", ["mx.example.com"])):
        result = verify_email("support@example.com")
    assert result.role_based is True
    assert result.final_status == "LIKELY_VALID"
