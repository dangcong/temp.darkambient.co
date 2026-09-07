from __future__ import annotations

import smtplib
from email.message import EmailMessage
from email.utils import formataddr, formatdate, getaddresses, make_msgid
from typing import Any

from .config import settings
from .utils import normalize_lookup_address


MAX_ATTACHMENT_COUNT = 10
MAX_ATTACHMENT_TOTAL_BYTES = 18 * 1024 * 1024


def parse_address_list(value: str) -> list[str]:
    addresses = []
    for _display_name, addr in getaddresses([value or ""]):
        normalized = addr.strip()
        if normalized:
            addresses.append(normalized)
    return addresses


def validate_outgoing_attachments(attachments: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    outgoing = attachments or []
    if len(outgoing) > MAX_ATTACHMENT_COUNT:
        raise ValueError(f"Chỉ được đính kèm tối đa {MAX_ATTACHMENT_COUNT} tệp")

    total_size = 0
    for attachment in outgoing:
        content = attachment.get("content")
        if content is None:
            raise ValueError("Không đọc được nội dung tệp đính kèm")
        total_size += len(bytes(content))
    if total_size > MAX_ATTACHMENT_TOTAL_BYTES:
        raise ValueError("Tổng dung lượng tệp đính kèm không được vượt quá 18 MB")
    return outgoing


def send_composed_message(
    *,
    source_message: dict[str, Any],
    mode: str,
    from_value: str | None = None,
    to_value: str,
    cc_value: str,
    subject: str,
    body: str,
    attachments: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    from_address = (
        normalize_lookup_address(from_value, settings.mail_domain)
        if from_value is not None
        else settings.smtp_from_address
    )
    envelope_from_address = settings.smtp_from_address
    to_addresses = parse_address_list(to_value)
    cc_addresses = parse_address_list(cc_value)
    recipients = to_addresses + cc_addresses

    if not recipients:
        raise ValueError("Cần ít nhất một địa chỉ nhận mail")
    if not subject.strip():
        raise ValueError("Subject không được để trống")
    if not body.strip():
        raise ValueError("Message không được để trống")
    if settings.smtp_security not in {"starttls", "ssl", "none"}:
        raise ValueError("SMTP_SECURITY không hợp lệ")

    message = EmailMessage()
    message["From"] = formataddr((settings.smtp_from_name, from_address))
    if from_address != envelope_from_address:
        message["Reply-To"] = from_address
    message["To"] = ", ".join(to_addresses)
    if cc_addresses:
        message["Cc"] = ", ".join(cc_addresses)
    message["Subject"] = subject.strip()
    message["Date"] = formatdate(localtime=True)
    message["Message-Id"] = make_msgid(domain=settings.mail_domain)

    raw_headers = source_message.get("raw_headers") or {}
    original_message_id = (source_message.get("message_id") or raw_headers.get("message_id") or "").strip()
    if mode == "reply" and original_message_id:
        message["In-Reply-To"] = original_message_id
        message["References"] = original_message_id

    message.set_content(body)
    outgoing_attachments = validate_outgoing_attachments(attachments)
    for attachment in outgoing_attachments:
        content = attachment.get("content")
        if content is None:
            continue
        content_type = str(attachment.get("content_type") or "application/octet-stream")
        if "/" in content_type:
            maintype, subtype = content_type.split("/", 1)
        else:
            maintype, subtype = "application", "octet-stream"
        message.add_attachment(
            bytes(content),
            maintype=maintype,
            subtype=subtype,
            filename=str(attachment.get("filename") or "attachment"),
        )

    if settings.smtp_security == "ssl":
        client = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=20)
    else:
        client = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20)

    try:
        client.ehlo()
        if settings.smtp_security == "starttls":
            client.starttls()
            client.ehlo()
        if settings.smtp_username and settings.smtp_password:
            client.login(settings.smtp_username, settings.smtp_password)
        client.send_message(message, from_addr=envelope_from_address, to_addrs=recipients)
    finally:
        try:
            client.quit()
        except Exception:
            pass

    return {
        "mode": mode,
        "to": to_addresses,
        "cc": cc_addresses,
        "subject": subject.strip(),
        "from": from_address,
        "message_id": message["Message-Id"],
        "attachment_count": len(outgoing_attachments),
    }
