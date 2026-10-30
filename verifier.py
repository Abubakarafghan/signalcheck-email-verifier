from __future__ import annotations

import smtplib
import socket
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import dns.exception
import dns.resolver
from email_validator import EmailNotValidError, validate_email

ROLE_PREFIXES = {"info", "support", "sales", "admin", "contact", "help", "billing", "noreply"}


@dataclass
class VerificationResult:
    email: str
    syntax_status: str
    domain_status: str
    mx_status: str
    disposable_status: str
    role_based: bool
    smtp_result: str
    final_status: str
    verification_reason: str

    def as_dict(self):
        return asdict(self)


def load_disposable_domains(path: Path) -> set[str]:
    try:
        if not path.exists():
            return set()
        return {
            line.strip().lower()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
    except (OSError, PermissionError):
        return set()


def _dns_status(domain: str, timeout: float) -> tuple[str, str, list[str]]:
    resolver = dns.resolver.Resolver()
    resolver.timeout = timeout
    resolver.lifetime = timeout
    try:
        answers = resolver.resolve(domain, "MX")
        hosts = [str(answer.exchange).rstrip(".") for answer in answers]
        return "FOUND", "MX records found", hosts
    except dns.resolver.NXDOMAIN:
        return "MISSING", "Domain does not exist", []
    except (dns.resolver.NoAnswer, dns.resolver.NoNameservers):
        try:
            resolver.resolve(domain, "A")
            return "IMPLICIT_MX", "No MX record; domain has an A record", [domain]
        except Exception:
            try:
                resolver.resolve(domain, "AAAA")
                return "IMPLICIT_MX", "No MX record; domain has an AAAA record", [domain]
            except Exception:
                return "MISSING", "No usable MX, A, or AAAA record", []
    except (dns.exception.Timeout, dns.exception.DNSException):
        return "TEMPORARY_ERROR", "DNS lookup was inconclusive", []


def _smtp_check(email: str, hosts: list[str], timeout: float) -> tuple[str, str]:
    if not hosts:
        return "NOT_RUN", "SMTP check skipped because no mail host was found"
    for host in hosts[:2]:
        try:
            with smtplib.SMTP(host, 25, timeout=timeout) as client:
                client.ehlo_or_helo_if_needed()
                code, message = client.mail("")
                if code >= 400:
                    return "UNKNOWN", "Mail server did not permit verification"
                code, response = client.rcpt(email)
                text = response.decode(errors="replace") if isinstance(response, bytes) else str(response)
                if 200 <= code < 300:
                    return "ACCEPTED", "Server accepted the recipient during this test"
                if code in {550, 551, 553, 554, 556}:
                    return "REJECTED", f"Server explicitly rejected the recipient ({code})"
                return "UNKNOWN", f"Inconclusive SMTP response ({code}: {text[:120]})"
        except (socket.timeout, OSError, smtplib.SMTPException):
            continue
    return "UNKNOWN", "SMTP connection was inconclusive"


def verify_email(
    email: str,
    disposable_domains: Optional[set[str]] = None,
    dns_timeout: float = 5,
    smtp_enabled: bool = False,
    smtp_timeout: float = 8,
) -> VerificationResult:
    normalized = email.strip().lower()
    disposable_domains = disposable_domains or set()
    try:
        validated = validate_email(normalized, check_deliverability=False)
        normalized = validated.normalized
    except EmailNotValidError as exc:
        return VerificationResult(normalized, "INVALID_FORMAT", "NOT_CHECKED", "NOT_CHECKED", "NOT_CHECKED", False, "NOT_RUN", "INVALID", str(exc))

    local, domain = normalized.rsplit("@", 1)
    role_based = local in ROLE_PREFIXES
    disposable = domain in disposable_domains
    mx_status, domain_reason, hosts = _dns_status(domain, dns_timeout)
    smtp_result, smtp_reason = _smtp_check(normalized, hosts, smtp_timeout) if smtp_enabled else ("NOT_RUN", "SMTP verification disabled")

    if mx_status == "MISSING":
        final_status = "INVALID"
        reason = domain_reason
    elif mx_status == "TEMPORARY_ERROR":
        final_status = "UNKNOWN"
        reason = domain_reason
    elif disposable:
        final_status = "RISKY"
        reason = "Disposable email domain"
    elif smtp_result == "REJECTED":
        final_status = "INVALID"
        reason = smtp_reason
    elif smtp_result == "ACCEPTED":
        final_status = "ACCEPTED_BY_SERVER"
        reason = "Server accepted the recipient; this does not prove the mailbox is active"
    elif role_based:
        final_status = "LIKELY_VALID"
        reason = f"{domain_reason}; role-based address"
    else:
        final_status = "LIKELY_VALID"
        reason = domain_reason

    return VerificationResult(normalized, "VALID_FORMAT", "EXISTS", mx_status, "DISPOSABLE" if disposable else "NOT_DISPOSABLE", role_based, smtp_result, final_status, reason)
