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
    html_body: str | None = None,
    reply_to_value: str | None = None,
    forwarded_to_value: str | None = None,
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
    reply_to_address = from_address
    if reply_to_value is not None:
        reply_to_address = normalize_lookup_address(reply_to_value, settings.mail_domain)
    if reply_to_value is not None or from_address != envelope_from_address:
        message["Reply-To"] = reply_to_address
    if forwarded_to_value:
        message["X-Forwarded-To"] = normalize_lookup_address(
            forwarded_to_value, settings.mail_domain
        )
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
    if html_body and html_body.strip():
        message.add_alternative(html_body, subtype="html")
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


def send_automatic_forward(
    *,
    source_message: dict[str, Any],
    target_address: str,
    attachments: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    source_address = str(source_message.get("recipient_address") or "").strip()
    sender_name = str(
        source_message.get("from_name")
        or source_message.get("from_email")
        or "Unknown Sender"
    ).strip()
    sender_email = str(source_message.get("from_email") or "").strip()
    original_subject = str(
        source_message.get("subject") or "(No subject)"
    ).strip()
    original_body = str(
        source_message.get("text_body") or source_message.get("snippet") or ""
    ).strip()
    original_html = str(source_message.get("html_body") or "").strip()
    sender_line = (
        f"{sender_name} <{sender_email}>"
        if sender_email and sender_email not in sender_name
        else sender_name
    )
    body = "\n".join(
        [
            f"Email được tự động chuyển tiếp từ {source_address}.",
            "",
            "---------- Thư gốc ----------",
            f"Từ: {sender_line}",
            f"Đến: {source_address}",
            f"Ngày: {source_message.get('received_at') or '-'}",
            f"Tiêu đề: {original_subject}",
            "",
            original_body,
        ]
    )
    return send_composed_message(
        source_message=source_message,
        mode="auto-forward",
        from_value=None,
        to_value=target_address,
        cc_value="",
        subject=original_subject,
        body=body,
        html_body=original_html,
        reply_to_value=source_address,
        forwarded_to_value=source_address,
        attachments=attachments,
    )
