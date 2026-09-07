from __future__ import annotations

import imaplib
import logging
import select
import threading
import time
from email import message_from_bytes
from email.message import Message
from email.utils import getaddresses

from . import db
from .config import settings
from .events import inbox_events
from .parser import (
    collect_headers,
    decode_mime_text,
    extract_attachment_payloads,
    extract_attachments,
    extract_links,
    extract_otps,
    extract_recipients,
    extract_snippet,
    extract_text_parts,
    parse_mailbox_received_at,
    parse_received_at,
    prefer_readable_text,
)
from .utils import iso_days_ago, utc_now_iso


logger = logging.getLogger("lush_temp_mail.sync")


def fetch_message_attachment_payloads(source_message: dict) -> list[dict]:
    if not settings.imap_password:
        return []

    imap_uid = source_message.get("imap_uid")
    if not imap_uid:
        return []

    with imaplib.IMAP4_SSL(settings.imap_host, settings.imap_port) as client:
        client.login(settings.imap_username, settings.imap_password)
        client.select("INBOX")
        status, fetched = client.uid("fetch", str(imap_uid), "(RFC822)")
        if status != "OK" or not fetched or not fetched[0]:
            return []
        raw_message = fetched[0][1]
        message = message_from_bytes(raw_message)
        return extract_attachment_payloads(message)


class IdleUnavailableError(RuntimeError):
    pass


class MailSyncService:
    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._sync_lock = threading.Lock()
        self._idle_disabled = False
        self._status_lock = threading.Lock()
        self._status: dict[str, str | bool | int | None] = {
            "mode": "stopped",
            "idle_enabled": settings.idle_enabled,
            "idle_active": False,
            "last_heartbeat_at": None,
            "last_sync_started_at": None,
            "last_sync_finished_at": None,
            "last_sync_success_at": None,
            "last_error": None,
            "sync_interval_s": settings.sync_interval_s,
            "idle_timeout_s": settings.idle_timeout_s,
        }
        self._last_heartbeat_ts: float | None = None

    def start(self) -> None:
        if not settings.sync_enabled:
            logger.info("Mail sync disabled by config")
            self._set_status(mode="disabled", idle_active=False, last_error="MAIL_SYNC_ENABLED is false")
            return
        if not settings.imap_password:
            logger.warning("IMAP password missing; mail sync will stay idle")
            self._set_status(mode="disabled", idle_active=False, last_error="IMAP password missing")
            return
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._set_status(mode="starting", idle_active=False, last_error=None)
        self._thread = threading.Thread(target=self._loop, name="mail-sync", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)
        self._set_status(mode="stopped", idle_active=False)

    def _loop(self) -> None:
        should_force_initial_sync = True
        while not self._stop_event.is_set():
            try:
                if settings.idle_enabled and not self._idle_disabled:
                    self._touch_heartbeat(mode="idle", idle_active=False, last_error=None)
                    if should_force_initial_sync:
                        synced = self.sync_once()
                        if synced:
                            logger.info("Mail sync imported %s message(s)", synced)
                        should_force_initial_sync = False
                    activity = self._wait_for_idle_activity()
                    if activity and not self._stop_event.is_set():
                        synced = self.sync_once()
                        if synced:
                            logger.info("Mail sync imported %s message(s) after IMAP IDLE notification", synced)
                    continue

                self._touch_heartbeat(mode="polling", idle_active=False, last_error=None)
                synced = self.sync_once()
                if synced:
                    logger.info("Mail sync imported %s message(s)", synced)
            except Exception as exc:
                should_force_initial_sync = True
                if isinstance(exc, IdleUnavailableError):
                    self._idle_disabled = True
                    self._set_status(mode="polling", idle_active=False, last_error=str(exc))
                    logger.warning("IMAP IDLE unavailable; falling back to polling every %ss (%s)", settings.sync_interval_s, exc)
                else:
                    self._set_status(last_error=str(exc), idle_active=False)
                    logger.exception("Mail sync failed: %s", exc)
                self._stop_event.wait(settings.sync_interval_s)
                continue
            self._stop_event.wait(settings.sync_interval_s)

    def sync_once(self) -> int:
        with self._sync_lock:
            self._touch_heartbeat()
            self._set_status(last_sync_started_at=utc_now_iso(), last_error=None)
            db.cleanup_expired_aliases(utc_now_iso())
            if settings.message_retention_days > 0:
                db.cleanup_old_messages(iso_days_ago(settings.message_retention_days))
            if not settings.sync_enabled or not settings.imap_password:
                self._set_status(last_sync_finished_at=utc_now_iso())
                return 0

            last_uid = int(db.get_state("imap_last_uid", "0") or "0")
            synced = 0
            changed_aliases: set[str] = set()

            with imaplib.IMAP4_SSL(settings.imap_host, settings.imap_port) as client:
                client.login(settings.imap_username, settings.imap_password)
                client.select("INBOX")
                search_criteria = "ALL" if last_uid == 0 else f"UID {last_uid + 1}:*"
                status, data = client.uid("search", None, search_criteria)
                if status != "OK" or not data or not data[0]:
                    self._set_status(last_sync_finished_at=utc_now_iso())
                    return 0

                uids = [int(value) for value in data[0].split() if value]
                for uid in uids:
                    status, fetched = client.uid("fetch", str(uid), "(RFC822 INTERNALDATE)")
                    if status != "OK" or not fetched or not fetched[0]:
                        continue
                    fetch_metadata = fetched[0][0]
                    raw_message = fetched[0][1]
                    message = message_from_bytes(raw_message)
                    payload = self._parse_message(uid, message, fetch_metadata=fetch_metadata)
                    db.set_state("imap_last_uid", str(uid))
                    if payload is None:
                        continue
                    stored = db.store_message(payload)
                    if stored is not None:
                        synced += 1
                        changed_aliases.update(
                            payload.get("recipient_addresses")
                            or [stored["recipient_address"]]
                        )

            finished_at = utc_now_iso()
            self._set_status(last_sync_finished_at=finished_at, last_sync_success_at=finished_at, last_error=None)
            if changed_aliases:
                inbox_events.publish(changed_aliases)
            return synced

    def _wait_for_idle_activity(self) -> bool:
        self._touch_heartbeat(mode="idle", idle_active=True, last_error=None)
        with imaplib.IMAP4_SSL(settings.imap_host, settings.imap_port) as client:
            client.login(settings.imap_username, settings.imap_password)
            client.select("INBOX")
            if not self._supports_idle(client):
                raise IdleUnavailableError("server does not advertise IDLE")
            activity_detected = self._idle_until_activity(client)
        self._set_status(idle_active=False)
        return activity_detected

    def _supports_idle(self, client: imaplib.IMAP4_SSL) -> bool:
        status, data = client.capability()
        if status != "OK":
            raise IdleUnavailableError("CAPABILITY failed")
        advertised = b" ".join(data or []).upper()
        return b"IDLE" in advertised

    def _idle_until_activity(self, client: imaplib.IMAP4_SSL) -> bool:
        tag = client._new_tag()
        tag_bytes = tag if isinstance(tag, bytes) else tag.encode()
        client.send(tag_bytes + b" IDLE\r\n")
        continuation = client.readline()
        if not continuation.startswith(b"+"):
            raise IdleUnavailableError(f"IDLE not accepted: {continuation!r}")

        sock = getattr(client, "sock", None)
        if sock is None:
            raise IdleUnavailableError("IMAP socket unavailable")

        deadline = time.monotonic() + max(settings.idle_timeout_s, 30)
        activity_detected = False
        last_heartbeat_refresh = time.monotonic()
        while not self._stop_event.is_set():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            if time.monotonic() - last_heartbeat_refresh >= 10:
                self._touch_heartbeat(mode="idle", idle_active=True)
                last_heartbeat_refresh = time.monotonic()
            readable, _, _ = select.select([sock], [], [], min(1.0, remaining))
            if not readable:
                continue
            line = client.readline()
            if not line:
                break
            text = line.decode(errors="replace").strip().upper()
            if any(token in text for token in ("EXISTS", "RECENT", "EXPUNGE")):
                activity_detected = True
                break

        client.send(b"DONE\r\n")
        while True:
            line = client.readline()
            if not line:
                break
            if line.startswith(tag_bytes):
                break

        return activity_detected

    def get_status(self) -> dict[str, str | bool | int | None]:
        with self._status_lock:
            payload = dict(self._status)
            last_heartbeat_ts = self._last_heartbeat_ts
        stale_after_s = max(settings.sync_interval_s * 3, 20)
        payload["stale_after_s"] = stale_after_s
        payload["is_stale"] = last_heartbeat_ts is None or (time.time() - last_heartbeat_ts) > stale_after_s
        return payload

    def _touch_heartbeat(self, **changes: str | bool | int | None) -> None:
        now_iso = utc_now_iso()
        with self._status_lock:
            self._last_heartbeat_ts = time.time()
            self._status["last_heartbeat_at"] = now_iso
            for key, value in changes.items():
                self._status[key] = value

    def _set_status(self, **changes: str | bool | int | None) -> None:
        with self._status_lock:
            for key, value in changes.items():
                self._status[key] = value

    def _parse_message(self, uid: int, message: Message, *, fetch_metadata: bytes | str | None = None) -> dict | None:
        recipients = extract_recipients(message, settings.mail_domain, settings.central_mailbox)
        if not recipients:
            return None
        recipient = recipients[0]

        sender_name = ""
        sender_email = ""
        sender_candidates = getaddresses(message.get_all("From", []))
        if sender_candidates:
            sender_name, sender_email = sender_candidates[0]
            sender_name = decode_mime_text(sender_name)

        raw_text_body, html_body = extract_text_parts(message)
        text_body = prefer_readable_text(raw_text_body, html_body)
        return {
            "imap_mailbox": settings.imap_username,
            "imap_uid": uid,
            "message_id": message.get("Message-Id", ""),
            "recipient_address": recipient,
            "recipient_addresses": recipients,
            "from_name": sender_name or sender_email or "Unknown Sender",
            "from_email": sender_email,
            "subject": decode_mime_text(message.get("Subject", "(No subject)")) or "(No subject)",
            "snippet": extract_snippet(text_body),
            "text_body": text_body,
            "html_body": html_body,
            "attachments": extract_attachments(message),
            "attachment_payloads": extract_attachment_payloads(message),
            "extracted_links": extract_links(text_body, html_body),
            "extracted_otps": extract_otps(text_body, html_body),
            "raw_headers": collect_headers(message),
            "received_at": parse_received_at(message),
            "mailbox_received_at": parse_mailbox_received_at(fetch_metadata),
            "ingested_at": utc_now_iso(),
        }
