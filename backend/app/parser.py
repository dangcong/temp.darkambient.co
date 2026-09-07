from __future__ import annotations

import html
import copy
import re
from email.header import decode_header
from email.message import Message
from email.utils import getaddresses, parsedate_to_datetime
from typing import Any
from urllib.parse import urlparse

from .utils import normalize_address, utc_now


RECIPIENT_HEADERS = [
    "X-Original-To",
    "Delivered-To",
    "Envelope-To",
    "X-Envelope-To",
    "Original-Recipient",
    "To",
    "Cc",
]

URL_RE = re.compile(r"https?://[^\s<>\"]+")
HREF_RE = re.compile(r"""(?is)<a\b[^>]*\bhref\s*=\s*(?:"([^"]+)"|'([^']+)'|([^\s>]+))""")
OTP_CONTEXT_RE = re.compile(
    r"(?i)(?:otp|verification code|verify code|security code|m[aã]\s*x[aá]c\s*nh[aậ]n|m[aã]|code)"
    r"[^A-Z0-9]{0,20}([A-Z0-9]{4,10})"
)
GENERIC_CODE_RE = re.compile(r"\b\d{4,8}\b")
TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")
INTERNALDATE_RE = re.compile(r'INTERNALDATE "([^"]+)"')
STYLE_BLOCK_RE = re.compile(r"(?is)<style\b[^>]*>.*?</style>")
SCRIPT_BLOCK_RE = re.compile(r"(?is)<script\b[^>]*>.*?</script>")
HEAD_BLOCK_RE = re.compile(r"(?is)<head\b[^>]*>.*?</head>")
NOISE_MARKERS = (
    "font-family:",
    "@media only screen",
    "mso-",
    ".externalclass",
    "#bodytable",
    "#bodycell",
    "display:swap",
    "woff2",
)
ACTION_VERIFY_KEYWORDS = (
    "verify",
    "verification",
    "confirm",
    "confirmation",
    "activate",
    "signin",
    "sign-in",
    "login",
    "log-in",
    "auth",
    "magic",
    "email-verification",
)
ACTION_RESET_KEYWORDS = (
    "reset",
    "recover",
    "password-reset",
    "reset-password",
)
ACTION_CONTEXT_KEYWORDS = (
    "otp",
    "verification",
    "verify",
    "security code",
    "passcode",
    "sign in",
    "login",
    "log in",
)
ASSET_EXTENSIONS = (
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".webp",
    ".css",
    ".js",
    ".woff",
    ".woff2",
    ".ttf",
    ".ico",
    ".xml",
)


def decode_mime_text(value: str) -> str:
    raw_value = str(value or "")
    if not raw_value:
        return ""

    decoded_parts: list[str] = []
    for chunk, charset in decode_header(raw_value):
        if isinstance(chunk, bytes):
            encoding = charset or "utf-8"
            try:
                decoded_parts.append(chunk.decode(encoding, errors="replace"))
            except LookupError:
                decoded_parts.append(chunk.decode("utf-8", errors="replace"))
        else:
            decoded_parts.append(chunk)

    return "".join(decoded_parts).strip()


def html_to_text(value: str) -> str:
    sanitized = HEAD_BLOCK_RE.sub(" ", value or "")
    sanitized = STYLE_BLOCK_RE.sub(" ", sanitized)
    sanitized = SCRIPT_BLOCK_RE.sub(" ", sanitized)
    without_tags = TAG_RE.sub(" ", sanitized)
    unescaped = html.unescape(without_tags)
    return WHITESPACE_RE.sub(" ", unescaped).strip()


def extract_text_parts(message: Message) -> tuple[str, str]:
    text_body = ""
    html_body = ""

    if message.is_multipart():
        for part in message.walk():
            content_type = part.get_content_type()
            disposition = part.get_content_disposition()
            if disposition == "attachment":
                continue
            payload = part.get_payload(decode=True) or b""
            charset = part.get_content_charset() or "utf-8"
            decoded = payload.decode(charset, errors="replace")
            if content_type == "text/plain" and not text_body:
                text_body = decoded
            elif content_type == "text/html" and not html_body:
                html_body = decoded
    else:
        payload = message.get_payload(decode=True) or b""
        charset = message.get_content_charset() or "utf-8"
        decoded = payload.decode(charset, errors="replace")
        if message.get_content_type() == "text/html":
            html_body = decoded
        else:
            text_body = decoded

    if not text_body and html_body:
        text_body = html_to_text(html_body)

    return text_body.strip(), html_body.strip()


def _iter_attachment_payloads(message: Message) -> list[dict[str, Any]]:
    attachments: list[dict[str, Any]] = []
    for part in message.walk():
        if part.is_multipart():
            continue

        disposition = (part.get_content_disposition() or "").lower()
        filename = decode_mime_text(part.get_filename() or "")
        content_type = part.get_content_type()

        is_attachment = disposition == "attachment"
        is_inline_asset = disposition == "inline" and bool(filename)
        if not is_attachment and not is_inline_asset:
            continue

        payload = part.get_payload(decode=True) or b""
        index = len(attachments)
        attachments.append(
            {
                "index": index,
                "filename": filename or "Unnamed attachment",
                "content_type": content_type,
                "size_bytes": len(payload),
                "disposition": disposition or "attachment",
                "content": payload,
            }
        )

    return attachments


def strip_attachment_content(attachment: dict[str, Any]) -> dict[str, Any]:
    metadata = copy.copy(attachment)
    metadata.pop("content", None)
    return metadata


def extract_attachment_payloads(message: Message) -> list[dict[str, Any]]:
    return _iter_attachment_payloads(message)


def extract_attachments(message: Message) -> list[dict[str, Any]]:
    return [strip_attachment_content(attachment) for attachment in _iter_attachment_payloads(message)]


def extract_recipients(message: Message, domain: str, central_mailbox: str) -> list[str]:
    candidates: list[str] = []
    domain_suffix = f"@{domain.lower()}"
    central_normalized = normalize_address(central_mailbox)

    for header in RECIPIENT_HEADERS:
        values = message.get_all(header, [])
        for _display_name, addr in getaddresses(values):
            normalized = normalize_address(addr)
            if normalized.endswith(domain_suffix):
                if normalized not in candidates:
                    candidates.append(normalized)

    aliases = [candidate for candidate in candidates if candidate != central_normalized]
    return aliases or candidates


def extract_recipient(message: Message, domain: str, central_mailbox: str) -> str | None:
    recipients = extract_recipients(message, domain, central_mailbox)
    return recipients[0] if recipients else None


def extract_links(text_body: str, html_body: str) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    seen: set[str] = set()
    seen_types: set[str] = set()

    def register(url: str) -> None:
        normalized = normalize_link_candidate(url)
        if not normalized or normalized in seen:
            return
        link_type = classify_action_link(normalized)
        if not link_type or link_type in seen_types:
            return
        seen.add(normalized)
        seen_types.add(link_type)
        links.append({"url": normalized, "type": link_type})

    for url in URL_RE.findall(text_body or ""):
        register(url)

    for match in HREF_RE.finditer(html_body or ""):
        register(match.group(1) or match.group(2) or match.group(3) or "")

    return links


def extract_otps(text_body: str, html_body: str) -> list[dict[str, str]]:
    readable_html = html_to_text(html_body) if html_body else ""
    combined = "\n".join(part for part in (text_body, readable_html) if part)
    found: list[dict[str, str]] = []
    seen: set[str] = set()

    for match in OTP_CONTEXT_RE.finditer(combined):
        code = match.group(1)
        if not is_plausible_otp(code):
            continue
        if code in seen:
            continue
        seen.add(code)
        context = combined[max(0, match.start() - 32): match.end() + 32].strip()
        found.append({"code": code, "context": context})

    if not found and has_action_context(combined):
        for match in GENERIC_CODE_RE.finditer(combined):
            code = match.group(0)
            if code in seen:
                continue
            seen.add(code)
            context = combined[max(0, match.start() - 24): match.end() + 24].strip()
            found.append({"code": code, "context": context})
            if len(found) >= 3:
                break

    return found


def extract_snippet(text_body: str) -> str:
    snippet = WHITESPACE_RE.sub(" ", (text_body or "").replace("\n", " ")).strip()
    return snippet[:180]


def prefer_readable_text(text_body: str, html_body: str) -> str:
    candidate = WHITESPACE_RE.sub(" ", (text_body or "")).strip()
    lowered = candidate.lower()
    noise_hits = sum(1 for marker in NOISE_MARKERS if marker in lowered)
    if candidate and noise_hits < 2:
        return text_body.strip()
    if html_body:
        return html_to_text(html_body)
    return text_body.strip()


def is_plausible_otp(code: str) -> bool:
    normalized = str(code or "").strip()
    if not normalized:
        return False
    if normalized.isdigit():
        return 4 <= len(normalized) <= 10
    return (
        4 <= len(normalized) <= 10
        and normalized.upper() == normalized
        and normalized.isalnum()
        and any(character.isdigit() for character in normalized)
        and any(character.isalpha() for character in normalized)
    )


def has_action_context(value: str) -> bool:
    lowered = str(value or "").lower()
    return any(keyword in lowered for keyword in ACTION_CONTEXT_KEYWORDS)


def normalize_link_candidate(value: str) -> str:
    candidate = html.unescape(str(value or "")).strip().strip("\"'<>")
    if not candidate.lower().startswith(("http://", "https://")):
        return ""
    return candidate.rstrip(".,)")


def classify_action_link(url: str) -> str | None:
    try:
        parsed = urlparse(url)
    except Exception:
        return None

    if parsed.scheme not in {"http", "https"}:
        return None

    path = (parsed.path or "").lower()
    combined = " ".join(
        part for part in ((parsed.netloc or "").lower(), path, (parsed.query or "").lower()) if part
    )

    if any(path.endswith(extension) for extension in ASSET_EXTENSIONS):
        return None
    if any(keyword in combined for keyword in ACTION_RESET_KEYWORDS):
        return "reset_password"
    if any(keyword in combined for keyword in ACTION_VERIFY_KEYWORDS):
        return "verify"
    return None


def parse_received_at(message: Message) -> str:
    raw_date = message.get("Date")
    if not raw_date:
        return utc_now().isoformat()
    try:
        return parsedate_to_datetime(raw_date).astimezone().isoformat()
    except Exception:
        return utc_now().isoformat()


def parse_mailbox_received_at(fetch_metadata: bytes | str | None) -> str | None:
    if not fetch_metadata:
        return None
    raw_metadata = fetch_metadata.decode(errors="replace") if isinstance(fetch_metadata, bytes) else str(fetch_metadata)
    match = INTERNALDATE_RE.search(raw_metadata)
    if not match:
        return None
    try:
        return parsedate_to_datetime(match.group(1)).astimezone().isoformat()
    except Exception:
        return None


def collect_headers(message: Message) -> dict[str, Any]:
    return {
        "subject": decode_mime_text(message.get("Subject", "")),
        "from": decode_mime_text(message.get("From", "")),
        "to": message.get("To", ""),
        "cc": message.get("Cc", ""),
        "message_id": message.get("Message-Id", ""),
        "delivered_to": message.get("Delivered-To", ""),
        "x_original_to": message.get("X-Original-To", ""),
    }
