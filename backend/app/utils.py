from __future__ import annotations

import re
import secrets
from datetime import UTC, datetime, timedelta


LOCAL_PART_RE = re.compile(r"^(?:[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*)$")


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_now_iso() -> str:
    return utc_now().isoformat()


def iso_in_hours(hours: int) -> str:
    return (utc_now() + timedelta(hours=hours)).isoformat()


def iso_in_seconds(seconds: int) -> str:
    return (utc_now() + timedelta(seconds=seconds)).isoformat()


def iso_days_ago(days: int) -> str:
    return (utc_now() - timedelta(days=days)).isoformat()


def normalize_address(address: str) -> str:
    return address.strip().lower()


def normalize_lookup_address(address_or_local_part: str, default_domain: str) -> str:
    candidate = normalize_address(address_or_local_part)
    domain = normalize_address(default_domain)
    if not candidate:
        raise ValueError("Vui lòng nhập alias email")

    if "@" in candidate:
        local_part, explicit_domain = split_address(candidate)
        if explicit_domain != domain:
            raise ValueError(f"Chỉ hỗ trợ alias @{domain}")
    else:
        local_part = candidate

    if not is_valid_local_part(local_part):
        raise ValueError("Alias email không hợp lệ")

    return f"{local_part}@{domain}"


def split_address(address: str) -> tuple[str, str]:
    normalized = normalize_address(address)
    local_part, domain = normalized.split("@", 1)
    return local_part, domain


def is_valid_local_part(local_part: str) -> bool:
    return bool(LOCAL_PART_RE.fullmatch(local_part.strip().lower()))


def random_local_part(length: int = 10) -> str:
    alphabet = "abcdefghijklmnopqrstuvwxyz0123456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))
