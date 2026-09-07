from __future__ import annotations

import json
import hashlib
import hmac
import secrets
import sqlite3
from email.utils import getaddresses
from typing import Any

from .config import settings
from .parser import decode_mime_text, extract_links, extract_otps, html_to_text
from .translator import DEFAULT_TARGET_LANGUAGE, infer_language_hint, should_offer_translation
from .utils import iso_in_hours, iso_in_seconds, normalize_address, split_address, utc_now_iso


PASSWORD_HASH_ITERATIONS = 260_000


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(settings.database_path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _execute_statements(connection: sqlite3.Connection, script: str) -> None:
    statement = ""
    for line in script.splitlines():
        statement += f"{line}\n"
        if sqlite3.complete_statement(statement):
            connection.execute(statement)
            statement = ""
    if statement.strip():
        raise sqlite3.OperationalError("Incomplete SQL migration statement")


def init_db() -> None:
    with _connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        _execute_statements(
            conn,
            """
            CREATE TABLE IF NOT EXISTS aliases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT NOT NULL UNIQUE,
                local_part TEXT NOT NULL,
                domain TEXT NOT NULL,
                label TEXT,
                source TEXT NOT NULL DEFAULT 'manual',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                expires_at TEXT,
                last_message_at TEXT,
                last_sender TEXT,
                message_count INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                imap_mailbox TEXT NOT NULL DEFAULT 'legacy',
                imap_uid INTEGER NOT NULL,
                message_id TEXT,
                alias_id INTEGER,
                recipient_address TEXT NOT NULL,
                from_name TEXT,
                from_email TEXT,
                subject TEXT,
                snippet TEXT,
                text_body TEXT,
                html_body TEXT,
                attachments_json TEXT NOT NULL DEFAULT '[]',
                extracted_links_json TEXT NOT NULL DEFAULT '[]',
                extracted_otps_json TEXT NOT NULL DEFAULT '[]',
                raw_headers_json TEXT NOT NULL DEFAULT '{}',
                received_at TEXT NOT NULL,
                mailbox_received_at TEXT,
                ingested_at TEXT,
                unread INTEGER NOT NULL DEFAULT 1,
                suppressed INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(alias_id) REFERENCES aliases(id)
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'admin',
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('admin', 'user')),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_login_at TEXT
            );

            CREATE TABLE IF NOT EXISTS app_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sent_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_message_id INTEGER,
                mode TEXT NOT NULL,
                from_email TEXT NOT NULL,
                to_json TEXT NOT NULL DEFAULT '[]',
                cc_json TEXT NOT NULL DEFAULT '[]',
                subject TEXT NOT NULL,
                text_body TEXT NOT NULL,
                attachments_json TEXT NOT NULL DEFAULT '[]',
                message_id TEXT,
                sent_at TEXT NOT NULL,
                suppressed INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(source_message_id) REFERENCES messages(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS excluded_aliases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT NOT NULL UNIQUE,
                local_part TEXT NOT NULL,
                domain TEXT NOT NULL,
                reason TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS forwarding_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_address TEXT NOT NULL UNIQUE,
                target_address TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_messages_recipient_received_at
            ON messages(recipient_address, received_at DESC);

            CREATE INDEX IF NOT EXISTS idx_messages_alias_received_at
            ON messages(alias_id, received_at DESC);

            CREATE INDEX IF NOT EXISTS idx_sent_messages_sent_at
            ON sent_messages(sent_at DESC);

            CREATE INDEX IF NOT EXISTS idx_excluded_aliases_address
            ON excluded_aliases(address);
            """
        )
        _ensure_message_mailbox_namespace(conn)
        _execute_statements(
            conn,
            """
            CREATE TABLE IF NOT EXISTS forwarding_deliveries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                source_address TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending',
                attempt_count INTEGER NOT NULL DEFAULT 0,
                last_error TEXT,
                next_attempt_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                forwarded_at TEXT,
                UNIQUE(rule_id, message_id),
                FOREIGN KEY(rule_id) REFERENCES forwarding_rules(id) ON DELETE CASCADE,
                FOREIGN KEY(message_id) REFERENCES messages(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_forwarding_deliveries_due
            ON forwarding_deliveries(status, next_attempt_at);
            """
        )
        forwarding_rule_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(forwarding_rules)").fetchall()
        }
        if "source_addresses_json" not in forwarding_rule_columns:
            conn.execute(
                "ALTER TABLE forwarding_rules ADD COLUMN source_addresses_json TEXT NOT NULL DEFAULT '[]'"
            )
        if "target_addresses_json" not in forwarding_rule_columns:
            conn.execute(
                "ALTER TABLE forwarding_rules ADD COLUMN target_addresses_json TEXT NOT NULL DEFAULT '[]'"
            )
        conn.execute(
            """
            UPDATE forwarding_rules
            SET source_addresses_json = json_array(source_address)
            WHERE source_addresses_json = '[]' OR source_addresses_json IS NULL
            """
        )
        conn.execute(
            """
            UPDATE forwarding_rules
            SET target_addresses_json = json_array(target_address)
            WHERE target_addresses_json = '[]' OR target_addresses_json IS NULL
            """
        )
        delivery_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(forwarding_deliveries)").fetchall()
        }
        if "target_address" not in delivery_columns:
            conn.execute(
                "ALTER TABLE forwarding_deliveries ADD COLUMN target_address TEXT NOT NULL DEFAULT ''"
            )
        if "source_address" not in delivery_columns:
            conn.execute(
                "ALTER TABLE forwarding_deliveries ADD COLUMN source_address TEXT NOT NULL DEFAULT ''"
            )
        if "target_addresses_json" not in delivery_columns:
            conn.execute(
                "ALTER TABLE forwarding_deliveries ADD COLUMN target_addresses_json TEXT NOT NULL DEFAULT '[]'"
            )
        conn.execute(
            """
            UPDATE forwarding_deliveries
            SET target_address = (
                    SELECT target_address FROM forwarding_rules
                    WHERE forwarding_rules.id = forwarding_deliveries.rule_id
                ),
                target_addresses_json = (
                    SELECT target_addresses_json FROM forwarding_rules
                    WHERE forwarding_rules.id = forwarding_deliveries.rule_id
                )
            WHERE target_address = '' OR target_addresses_json = '[]' OR target_addresses_json IS NULL
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS forwarding_delivery_targets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                delivery_id INTEGER NOT NULL,
                target_address TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                attempt_count INTEGER NOT NULL DEFAULT 0,
                last_error TEXT,
                next_attempt_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                forwarded_at TEXT,
                UNIQUE(delivery_id, target_address),
                FOREIGN KEY(delivery_id) REFERENCES forwarding_deliveries(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_forwarding_delivery_targets_due
            ON forwarding_delivery_targets(status, next_attempt_at)
            """
        )
        _backfill_forwarding_delivery_targets(conn)
        message_columns = {row["name"] for row in conn.execute("PRAGMA table_info(messages)").fetchall()}
        if "important" not in message_columns:
            conn.execute("ALTER TABLE messages ADD COLUMN important INTEGER NOT NULL DEFAULT 0")
        if "mailbox_received_at" not in message_columns:
            conn.execute("ALTER TABLE messages ADD COLUMN mailbox_received_at TEXT")
        if "ingested_at" not in message_columns:
            conn.execute("ALTER TABLE messages ADD COLUMN ingested_at TEXT")
        if "attachments_json" not in message_columns:
            conn.execute("ALTER TABLE messages ADD COLUMN attachments_json TEXT NOT NULL DEFAULT '[]'")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS message_attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER NOT NULL,
                attachment_index INTEGER NOT NULL,
                filename TEXT NOT NULL,
                content_type TEXT NOT NULL,
                disposition TEXT NOT NULL DEFAULT 'attachment',
                size_bytes INTEGER NOT NULL DEFAULT 0,
                content BLOB NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(message_id, attachment_index),
                FOREIGN KEY(message_id) REFERENCES messages(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sent_message_attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sent_message_id INTEGER NOT NULL,
                attachment_index INTEGER NOT NULL,
                filename TEXT NOT NULL,
                content_type TEXT NOT NULL,
                disposition TEXT NOT NULL DEFAULT 'attachment',
                size_bytes INTEGER NOT NULL DEFAULT 0,
                content BLOB NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(sent_message_id, attachment_index),
                FOREIGN KEY(sent_message_id) REFERENCES sent_messages(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS message_recipients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER NOT NULL,
                recipient_address TEXT NOT NULL,
                alias_id INTEGER,
                UNIQUE(message_id, recipient_address),
                FOREIGN KEY(message_id) REFERENCES messages(id) ON DELETE CASCADE,
                FOREIGN KEY(alias_id) REFERENCES aliases(id)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_message_recipients_address
            ON message_recipients(recipient_address)
            """
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO message_recipients(message_id, recipient_address, alias_id)
            SELECT id, recipient_address, alias_id
            FROM messages
            WHERE alias_id IS NOT NULL
            """
        )
        _backfill_message_recipient_maps(conn)
        _backfill_forwarding_delivery_sources(conn)
        for alias_row in conn.execute("SELECT id FROM aliases").fetchall():
            _refresh_alias_stats(conn, alias_row["id"])
        conn.execute("UPDATE messages SET mailbox_received_at = COALESCE(mailbox_received_at, received_at) WHERE mailbox_received_at IS NULL")
        conn.execute("UPDATE messages SET ingested_at = COALESCE(ingested_at, received_at) WHERE ingested_at IS NULL")
        session_columns = {row["name"] for row in conn.execute("PRAGMA table_info(sessions)").fetchall()}
        if "role" not in session_columns:
            conn.execute("ALTER TABLE sessions ADD COLUMN role TEXT NOT NULL DEFAULT 'admin'")
        _seed_default_users(conn)


def _message_has_global_uid_unique(conn: sqlite3.Connection) -> bool:
    for index in conn.execute("PRAGMA index_list(messages)").fetchall():
        if not index["unique"]:
            continue
        columns = [row["name"] for row in conn.execute(f"PRAGMA index_info({index['name']})").fetchall()]
        if columns == ["imap_uid"]:
            return True
    return False


def _ensure_message_mailbox_namespace(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(messages)").fetchall()}
    needs_rebuild = "imap_mailbox" not in columns or _message_has_global_uid_unique(conn)
    if not needs_rebuild:
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_mailbox_uid
            ON messages(imap_mailbox, imap_uid)
            """
        )
        return

    conn.execute("ALTER TABLE messages RENAME TO messages_uid_migration_old")
    _execute_statements(
        conn,
        """
        CREATE TABLE messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            imap_mailbox TEXT NOT NULL DEFAULT 'legacy',
            imap_uid INTEGER NOT NULL,
            message_id TEXT,
            alias_id INTEGER,
            recipient_address TEXT NOT NULL,
            from_name TEXT,
            from_email TEXT,
            subject TEXT,
            snippet TEXT,
            text_body TEXT,
            html_body TEXT,
            attachments_json TEXT NOT NULL DEFAULT '[]',
            extracted_links_json TEXT NOT NULL DEFAULT '[]',
            extracted_otps_json TEXT NOT NULL DEFAULT '[]',
            raw_headers_json TEXT NOT NULL DEFAULT '{}',
            received_at TEXT NOT NULL,
            mailbox_received_at TEXT,
            ingested_at TEXT,
            unread INTEGER NOT NULL DEFAULT 1,
            suppressed INTEGER NOT NULL DEFAULT 0,
            important INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(alias_id) REFERENCES aliases(id)
        );
        """
    )
    old_columns = {row["name"] for row in conn.execute("PRAGMA table_info(messages_uid_migration_old)").fetchall()}
    selectable = [
        "id",
        "imap_uid",
        "message_id",
        "alias_id",
        "recipient_address",
        "from_name",
        "from_email",
        "subject",
        "snippet",
        "text_body",
        "html_body",
        "attachments_json",
        "extracted_links_json",
        "extracted_otps_json",
        "raw_headers_json",
        "received_at",
        "mailbox_received_at",
        "ingested_at",
        "unread",
        "suppressed",
        "important",
    ]
    select_parts = []
    for column in selectable:
        if column in old_columns:
            select_parts.append(column)
        elif column == "attachments_json":
            select_parts.append("'[]' AS attachments_json")
        elif column == "extracted_links_json":
            select_parts.append("'[]' AS extracted_links_json")
        elif column == "extracted_otps_json":
            select_parts.append("'[]' AS extracted_otps_json")
        elif column == "raw_headers_json":
            select_parts.append("'{}' AS raw_headers_json")
        elif column in {"unread"}:
            select_parts.append("1 AS unread")
        elif column in {"suppressed", "important"}:
            select_parts.append("0 AS " + column)
        else:
            select_parts.append("NULL AS " + column)
    conn.execute(
        f"""
        INSERT INTO messages(
            {', '.join(['imap_mailbox'] + selectable)}
        )
        SELECT 'legacy', {', '.join(select_parts)}
        FROM messages_uid_migration_old
        """
    )
    conn.execute("DROP TABLE messages_uid_migration_old")
    _execute_statements(
        conn,
        """
        CREATE INDEX IF NOT EXISTS idx_messages_recipient_received_at
        ON messages(recipient_address, received_at DESC);

        CREATE INDEX IF NOT EXISTS idx_messages_alias_received_at
        ON messages(alias_id, received_at DESC);

        CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_mailbox_uid
        ON messages(imap_mailbox, imap_uid);
        """
    )


def row_to_alias(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "id": row["id"],
        "address": row["address"],
        "local_part": row["local_part"],
        "domain": row["domain"],
        "label": row["label"],
        "source": row["source"],
        "status": row["status"],
        "created_at": row["created_at"],
        "expires_at": row["expires_at"],
        "last_message_at": row["last_message_at"],
        "last_sender": row["last_sender"],
        "message_count": row["message_count"],
    }


def row_to_message(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    from_name = decode_mime_text(row["from_name"] or "")
    subject = decode_mime_text(row["subject"] or "")
    text_body = row["text_body"] or ""
    html_body = row["html_body"] or ""
    readable_text = text_body or (html_to_text(html_body) if html_body else "")
    extracted_links = extract_links(text_body, html_body)
    extracted_otps = extract_otps(text_body, html_body)
    language_hint = infer_language_hint(subject, readable_text)
    return {
        "id": row["id"],
        "imap_mailbox": row["imap_mailbox"] if "imap_mailbox" in row.keys() else "legacy",
        "imap_uid": row["imap_uid"],
        "message_id": row["message_id"],
        "alias_id": row["alias_id"],
        "recipient_address": row["recipient_address"],
        "from_name": from_name,
        "from_email": row["from_email"],
        "subject": subject,
        "snippet": row["snippet"],
        "text_body": text_body,
        "html_body": html_body,
        "attachments": json.loads(row["attachments_json"] or "[]"),
        "extracted_links": extracted_links,
        "extracted_otps": extracted_otps,
        "raw_headers": json.loads(row["raw_headers_json"] or "{}"),
        "received_at": row["received_at"],
        "mailbox_received_at": row["mailbox_received_at"] or row["received_at"],
        "ingested_at": row["ingested_at"] or row["received_at"],
        "unread": bool(row["unread"]),
        "important": bool(row["important"]),
        "suppressed": bool(row["suppressed"]),
        "language_hint": language_hint,
        "can_translate": should_offer_translation(
            subject,
            readable_text,
            target_language=DEFAULT_TARGET_LANGUAGE,
            html_body=html_body,
        ),
    }


def row_to_message_summary(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    from_name = decode_mime_text(row["from_name"] or "")
    subject = decode_mime_text(row["subject"] or "")
    return {
        "id": row["id"],
        "message_id": row["message_id"],
        "alias_id": row["alias_id"],
        "recipient_address": row["recipient_address"],
        "from_name": from_name,
        "from_email": row["from_email"],
        "subject": subject,
        "snippet": row["snippet"],
        "received_at": row["received_at"],
        "mailbox_received_at": row["mailbox_received_at"] or row["received_at"],
        "ingested_at": row["ingested_at"] or row["received_at"],
        "unread": bool(row["unread"]),
        "important": bool(row["important"]),
        "has_links": bool(row["has_links"]),
        "has_otps": bool(row["has_otps"]),
    }


def row_to_attachment(row: sqlite3.Row | None, *, include_content: bool = False) -> dict[str, Any] | None:
    if row is None:
        return None
    payload = {
        "index": row["attachment_index"],
        "filename": row["filename"],
        "content_type": row["content_type"],
        "disposition": row["disposition"],
        "size_bytes": row["size_bytes"],
    }
    if include_content:
        payload["content"] = bytes(row["content"])
    return payload


def row_to_sent_message(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    subject = decode_mime_text(row["subject"] or "")
    text_body = row["text_body"] or ""
    return {
        "id": row["id"],
        "kind": "sent",
        "source_message_id": row["source_message_id"],
        "mode": row["mode"],
        "from_email": row["from_email"],
        "to": json.loads(row["to_json"] or "[]"),
        "cc": json.loads(row["cc_json"] or "[]"),
        "subject": subject,
        "snippet": text_body[:240],
        "text_body": text_body,
        "html_body": "",
        "attachments": json.loads(row["attachments_json"] or "[]"),
        "message_id": row["message_id"],
        "sent_at": row["sent_at"],
        "received_at": row["sent_at"],
        "unread": False,
        "important": False,
        "suppressed": bool(row["suppressed"]),
        "can_translate": False,
    }


def row_to_sent_message_summary(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    subject = decode_mime_text(row["subject"] or "")
    return {
        "id": row["id"],
        "kind": "sent",
        "source_message_id": row["source_message_id"],
        "mode": row["mode"],
        "from_email": row["from_email"],
        "to": json.loads(row["to_json"] or "[]"),
        "cc": json.loads(row["cc_json"] or "[]"),
        "subject": subject,
        "snippet": row["snippet"] or "",
        "attachment_count": int(row["attachment_count"] or 0),
        "message_id": row["message_id"],
        "sent_at": row["sent_at"],
        "received_at": row["sent_at"],
        "unread": False,
        "important": False,
        "suppressed": bool(row["suppressed"]),
    }


def row_to_excluded_alias(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "id": row["id"],
        "address": row["address"],
        "local_part": row["local_part"],
        "domain": row["domain"],
        "reason": row["reason"] or "",
        "created_at": row["created_at"],
    }


def row_to_forwarding_rule(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    keys = set(row.keys())
    source_addresses = _decode_forwarding_addresses(
        row["source_addresses_json"] if "source_addresses_json" in keys else "",
        row["source_address"],
    )
    target_addresses = _decode_forwarding_addresses(
        row["target_addresses_json"] if "target_addresses_json" in keys else "",
        row["target_address"],
    )
    return {
        "id": row["id"],
        "source_address": ", ".join(source_addresses),
        "target_address": ", ".join(target_addresses),
        "source_addresses": source_addresses,
        "target_addresses": target_addresses,
        "enabled": bool(row["enabled"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "last_status": row["last_status"] if "last_status" in keys else None,
        "last_error": (row["last_error"] or "") if "last_error" in keys else "",
        "last_forwarded_at": row["last_forwarded_at"] if "last_forwarded_at" in keys else None,
    }


def _decode_forwarding_addresses(value: Any, fallback: Any = "") -> list[str]:
    try:
        parsed = json.loads(value or "[]")
    except (TypeError, ValueError):
        parsed = []
    candidates = parsed if isinstance(parsed, list) else []
    if not candidates:
        candidates = str(fallback or "").split(",")
    addresses: list[str] = []
    for candidate in candidates:
        address = normalize_address(str(candidate))
        if address and address not in addresses:
            addresses.append(address)
    return addresses


def _normalize_forwarding_values(value: Any) -> list[str]:
    values = value if isinstance(value, list) else str(value or "").split(",")
    addresses: list[str] = []
    for value_item in values:
        address = normalize_address(str(value_item))
        if address and address not in addresses:
            addresses.append(address)
    return sorted(addresses)


def _backfill_forwarding_delivery_targets(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        "SELECT id, target_address, target_addresses_json, status, attempt_count, "
        "last_error, next_attempt_at, created_at, updated_at, forwarded_at "
        "FROM forwarding_deliveries"
    ).fetchall()
    for row in rows:
        targets = _decode_forwarding_addresses(
            row["target_addresses_json"], row["target_address"]
        )
        for target in targets:
            conn.execute(
                """
                INSERT OR IGNORE INTO forwarding_delivery_targets(
                    delivery_id, target_address, status, attempt_count, last_error,
                    next_attempt_at, created_at, updated_at, forwarded_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["id"],
                    target,
                    row["status"],
                    row["attempt_count"],
                    row["last_error"],
                    row["next_attempt_at"],
                    row["created_at"],
                    row["updated_at"],
                    row["forwarded_at"],
                ),
            )


def _backfill_forwarding_delivery_sources(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        """
        SELECT deliveries.id, deliveries.message_id, rules.source_address,
               rules.source_addresses_json
        FROM forwarding_deliveries AS deliveries
        JOIN forwarding_rules AS rules ON rules.id = deliveries.rule_id
        WHERE deliveries.source_address = '' OR deliveries.source_address IS NULL
        """
    ).fetchall()
    for row in rows:
        sources = _decode_forwarding_addresses(
            row["source_addresses_json"], row["source_address"]
        )
        recipients = conn.execute(
            "SELECT recipient_address FROM message_recipients WHERE message_id = ? ORDER BY id",
            (row["message_id"],),
        ).fetchall()
        matched_source = next(
            (
                recipient["recipient_address"]
                for recipient in recipients
                if recipient["recipient_address"] in sources
            ),
            sources[0] if sources else "",
        )
        conn.execute(
            "UPDATE forwarding_deliveries SET source_address = ? WHERE id = ?",
            (matched_source, row["id"]),
        )


def _attachment_metadata(attachment: dict[str, Any], fallback_index: int) -> dict[str, Any]:
    return {
        "index": int(attachment.get("index", fallback_index)),
        "filename": attachment.get("filename") or "Unnamed attachment",
        "content_type": attachment.get("content_type") or "application/octet-stream",
        "disposition": attachment.get("disposition") or "attachment",
        "size_bytes": int(attachment.get("size_bytes") or len(bytes(attachment.get("content") or b""))),
    }


def _store_attachment_payloads(
    conn: sqlite3.Connection,
    message_id: int,
    attachments: list[dict[str, Any]],
) -> None:
    if not attachments:
        return
    now = utc_now_iso()
    for fallback_index, attachment in enumerate(attachments):
        content = attachment.get("content")
        if content is None:
            continue
        content_bytes = bytes(content)
        attachment_index = int(attachment.get("index", fallback_index))
        conn.execute(
            """
            INSERT OR REPLACE INTO message_attachments(
                message_id, attachment_index, filename, content_type, disposition, size_bytes, content, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                message_id,
                attachment_index,
                attachment.get("filename") or "Unnamed attachment",
                attachment.get("content_type") or "application/octet-stream",
                attachment.get("disposition") or "attachment",
                int(attachment.get("size_bytes") or len(content_bytes)),
                content_bytes,
                now,
            ),
        )


def _store_sent_attachment_payloads(
    conn: sqlite3.Connection,
    sent_message_id: int,
    attachments: list[dict[str, Any]],
) -> None:
    if not attachments:
        return
    now = utc_now_iso()
    for fallback_index, attachment in enumerate(attachments):
        content = attachment.get("content")
        if content is None:
            continue
        content_bytes = bytes(content)
        metadata = _attachment_metadata(attachment, fallback_index)
        conn.execute(
            """
            INSERT OR REPLACE INTO sent_message_attachments(
                sent_message_id, attachment_index, filename, content_type, disposition, size_bytes, content, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sent_message_id,
                metadata["index"],
                metadata["filename"],
                metadata["content_type"],
                metadata["disposition"],
                metadata["size_bytes"],
                content_bytes,
                now,
            ),
        )


def hash_password(password: str) -> str:
    salt = secrets.token_urlsafe(18)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_HASH_ITERATIONS,
    ).hex()
    return f"pbkdf2_sha256${PASSWORD_HASH_ITERATIONS}${salt}${password_hash}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations_raw, salt, expected_hash = password_hash.split("$", 3)
        iterations = int(iterations_raw)
    except (ValueError, TypeError):
        return False
    if algorithm != "pbkdf2_sha256" or iterations < 1 or not salt or not expected_hash:
        return False
    actual_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    ).hex()
    return hmac.compare_digest(actual_hash, expected_hash)


def row_to_user(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "id": row["id"],
        "username": row["username"],
        "role": row["role"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "last_login_at": row["last_login_at"],
    }


def _insert_user(conn: sqlite3.Connection, *, username: str, password: str, role: str) -> dict[str, Any]:
    now = utc_now_iso()
    cursor = conn.execute(
        """
        INSERT INTO users(username, password_hash, role, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (username, hash_password(password), role, now, now),
    )
    row = conn.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return row_to_user(row)


def _seed_default_users(conn: sqlite3.Connection) -> None:
    existing_count = conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"]
    if existing_count:
        return
    _insert_user(conn, username=settings.admin_username, password=settings.admin_password, role="admin")
    _insert_user(conn, username=settings.user_username, password=settings.user_password, role="user")


def list_users() -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM users
            ORDER BY CASE role WHEN 'admin' THEN 0 ELSE 1 END, username COLLATE NOCASE ASC
            """
        ).fetchall()
    return [row_to_user(row) for row in rows]


def get_user(user_id: int) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return row_to_user(row)


def count_admin_users(*, exclude_user_id: int | None = None) -> int:
    query = "SELECT COUNT(*) AS count FROM users WHERE role = 'admin'"
    params: tuple[Any, ...] = ()
    if exclude_user_id is not None:
        query += " AND id != ?"
        params = (exclude_user_id,)
    with _connect() as conn:
        row = conn.execute(query, params).fetchone()
    return int(row["count"] if row else 0)


def create_user(*, username: str, password: str, role: str) -> dict[str, Any]:
    with _connect() as conn:
        return _insert_user(conn, username=username, password=password, role=role)


def update_user(
    user_id: int,
    *,
    username: str | None = None,
    password: str | None = None,
    role: str | None = None,
) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if row is None:
            return None

        old_username = row["username"]
        next_username = username if username is not None else row["username"]
        next_role = role if role is not None else row["role"]
        next_password_hash = hash_password(password) if password is not None else row["password_hash"]
        now = utc_now_iso()
        conn.execute(
            """
            UPDATE users
            SET username = ?, password_hash = ?, role = ?, updated_at = ?
            WHERE id = ?
            """,
            (next_username, next_password_hash, next_role, now, user_id),
        )
        if next_username != old_username or next_role != row["role"]:
            conn.execute(
                "UPDATE sessions SET username = ?, role = ? WHERE username = ?",
                (next_username, next_role, old_username),
            )
        updated = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return row_to_user(updated)


def delete_user(user_id: int) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if row is None:
            return None
        conn.execute("DELETE FROM sessions WHERE username = ?", (row["username"],))
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    return row_to_user(row)


def authenticate_user(username: str, password: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if row is None or not verify_password(password, row["password_hash"]):
            return None
        now = utc_now_iso()
        conn.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (now, row["id"]))
        updated = conn.execute("SELECT * FROM users WHERE id = ?", (row["id"],)).fetchone()
    return row_to_user(updated)


def create_session(token: str, username: str, role: str, expires_at: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO sessions(token, username, role, expires_at, created_at) VALUES (?, ?, ?, ?, ?)",
            (token, username, role, expires_at, utc_now_iso()),
        )


def get_session(token: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT token, username, role, expires_at FROM sessions WHERE token = ?",
            (token,),
        ).fetchone()
    if row is None:
        return None
    return dict(row)


def delete_session(token: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))


def delete_expired_sessions(now_iso: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM sessions WHERE expires_at <= ?", (now_iso,))


def get_state(key: str, default: str = "") -> str:
    with _connect() as conn:
        row = conn.execute("SELECT value FROM app_state WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_state(key: str, value: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO app_state(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )


def _refresh_alias_stats(conn: sqlite3.Connection, alias_id: int) -> None:
    conn.execute(
        """
        UPDATE aliases
        SET
            last_message_at = (
                SELECT MAX(messages.received_at)
                FROM messages
                JOIN message_recipients ON message_recipients.message_id = messages.id
                WHERE message_recipients.alias_id = aliases.id AND messages.suppressed = 0
            ),
            last_sender = (
                SELECT COALESCE(messages.from_email, messages.from_name, '')
                FROM messages
                JOIN message_recipients ON message_recipients.message_id = messages.id
                WHERE message_recipients.alias_id = aliases.id AND messages.suppressed = 0
                ORDER BY messages.received_at DESC, messages.id DESC
                LIMIT 1
            ),
            message_count = (
                SELECT COUNT(DISTINCT messages.id)
                FROM messages
                JOIN message_recipients ON message_recipients.message_id = messages.id
                WHERE message_recipients.alias_id = aliases.id AND messages.suppressed = 0
            )
        WHERE id = ?
        """,
        (alias_id,),
    )


def _ensure_alias_for_connection(conn: sqlite3.Connection, address: str) -> sqlite3.Row | None:
    normalized = normalize_address(address)
    try:
        local_part, domain = split_address(normalized)
    except ValueError:
        return None
    now_iso = utc_now_iso()
    conn.execute(
        """
        INSERT INTO aliases(address, local_part, domain, source, status, created_at, expires_at)
        VALUES (?, ?, ?, 'inbound', 'active', ?, ?)
        ON CONFLICT(address) DO NOTHING
        """,
        (normalized, local_part, domain, now_iso, _default_alias_expires_at()),
    )
    return conn.execute("SELECT * FROM aliases WHERE address = ?", (normalized,)).fetchone()


def _backfill_message_recipient_maps(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        "SELECT id, recipient_address, raw_headers_json FROM messages"
    ).fetchall()
    domain_suffix = f"@{settings.mail_domain.lower()}"
    central_address = normalize_address(settings.central_mailbox)
    for row in rows:
        addresses: list[str] = [normalize_address(row["recipient_address"])]
        try:
            headers = json.loads(row["raw_headers_json"] or "{}")
        except (TypeError, ValueError):
            headers = {}
        header_values = [
            headers.get("x_original_to", ""),
            headers.get("delivered_to", ""),
            headers.get("to", ""),
            headers.get("cc", ""),
        ]
        for _display_name, address in getaddresses(
            [str(value or "") for value in header_values]
        ):
            candidate = normalize_address(address)
            if (
                candidate.endswith(domain_suffix)
                and candidate != central_address
                and candidate not in addresses
            ):
                addresses.append(candidate)
        for address in addresses:
            alias = conn.execute(
                "SELECT id, status FROM aliases WHERE address = ?", (address,)
            ).fetchone()
            if alias is None:
                alias = _ensure_alias_for_connection(conn, address)
            if alias is None or alias["status"] != "active":
                continue
            conn.execute(
                """
                INSERT OR IGNORE INTO message_recipients(message_id, recipient_address, alias_id)
                VALUES (?, ?, ?)
                """,
                (row["id"], address, alias["id"]),
            )


def ensure_alias(
    address: str,
    *,
    source: str,
    label: str | None = None,
    expires_at: str | None = None,
) -> dict[str, Any]:
    normalized = normalize_address(address)
    local_part, domain = split_address(normalized)
    now_iso = utc_now_iso()

    with _connect() as conn:
        row = conn.execute("SELECT * FROM aliases WHERE address = ?", (normalized,)).fetchone()
        if row:
            updates: list[str] = []
            values: list[Any] = []
            if label is not None:
                updates.append("label = ?")
                values.append(label)
            if expires_at is not None:
                updates.append("expires_at = ?")
                values.append(expires_at)
            if source != "inbound" and row["source"] == "inbound":
                updates.append("source = ?")
                values.append(source)
            if updates:
                values.extend([normalized])
                conn.execute(f"UPDATE aliases SET {', '.join(updates)} WHERE address = ?", values)
                row = conn.execute("SELECT * FROM aliases WHERE address = ?", (normalized,)).fetchone()
            return row_to_alias(row)

        conn.execute(
            """
            INSERT INTO aliases(address, local_part, domain, label, source, status, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, 'active', ?, ?)
            """,
            (normalized, local_part, domain, label, source, now_iso, expires_at),
        )
        row = conn.execute("SELECT * FROM aliases WHERE address = ?", (normalized,)).fetchone()
        return row_to_alias(row)


def list_aliases(search: str = "", status: str = "visible") -> list[dict[str, Any]]:
    query = "SELECT * FROM aliases WHERE 1=1"
    values: list[Any] = []
    if status == "visible":
        query += " AND status != 'deleted'"
    elif status != "all":
        query += " AND status = ?"
        values.append(status)
    if search:
        pattern = f"%{search.lower()}%"
        query += " AND (LOWER(address) LIKE ? OR LOWER(COALESCE(label, '')) LIKE ?)"
        values.extend([pattern, pattern])
    query += " ORDER BY CASE status WHEN 'active' THEN 0 WHEN 'expired' THEN 1 ELSE 2 END, COALESCE(last_message_at, created_at) DESC"
    with _connect() as conn:
        rows = conn.execute(query, values).fetchall()
    return [row_to_alias(row) for row in rows]


def get_alias(alias_id: int) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM aliases WHERE id = ?", (alias_id,)).fetchone()
    return row_to_alias(row)


def get_alias_by_address(address: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM aliases WHERE address = ?", (normalize_address(address),)).fetchone()
    return row_to_alias(row)


def update_alias(alias_id: int, *, label: str | None = None, expires_at: str | None = None, status: str | None = None) -> dict[str, Any] | None:
    updates: list[str] = []
    values: list[Any] = []
    if label is not None:
        updates.append("label = ?")
        values.append(label)
    if expires_at is not None:
        updates.append("expires_at = ?")
        values.append(expires_at)
    if status is not None:
        updates.append("status = ?")
        values.append(status)
    if not updates:
        return get_alias(alias_id)
    values.append(alias_id)
    with _connect() as conn:
        conn.execute(f"UPDATE aliases SET {', '.join(updates)} WHERE id = ?", values)
        row = conn.execute("SELECT * FROM aliases WHERE id = ?", (alias_id,)).fetchone()
    return row_to_alias(row)


def expire_alias(alias_id: int) -> dict[str, Any] | None:
    return update_alias(alias_id, status="expired")


def delete_alias(alias_id: int) -> dict[str, Any] | None:
    return update_alias(alias_id, status="deleted")


def reactivate_alias(alias_id: int, additional_hours: int | None = None) -> dict[str, Any] | None:
    expires_at = iso_in_hours(additional_hours) if additional_hours else None
    return update_alias(alias_id, status="active", expires_at=expires_at)


def list_excluded_aliases(search: str = "") -> list[dict[str, Any]]:
    query = "SELECT * FROM excluded_aliases"
    values: list[Any] = []
    if search:
        pattern = f"%{search.lower()}%"
        query += " WHERE LOWER(address) LIKE ? OR LOWER(local_part) LIKE ? OR LOWER(COALESCE(reason, '')) LIKE ?"
        values.extend([pattern, pattern, pattern])
    query += " ORDER BY created_at DESC, id DESC"
    with _connect() as conn:
        rows = conn.execute(query, values).fetchall()
    return [row_to_excluded_alias(row) for row in rows]


def get_excluded_alias_by_address(address: str) -> dict[str, Any] | None:
    normalized = normalize_address(address)
    with _connect() as conn:
        row = conn.execute("SELECT * FROM excluded_aliases WHERE address = ?", (normalized,)).fetchone()
    return row_to_excluded_alias(row)


def is_excluded_alias(address: str) -> bool:
    return get_excluded_alias_by_address(address) is not None


def suppress_messages_for_address(address: str) -> int:
    normalized = normalize_address(address)
    with _connect() as conn:
        alias_rows = conn.execute(
            """
            SELECT DISTINCT alias_id
            FROM messages
            WHERE recipient_address = ? AND alias_id IS NOT NULL
            """,
            (normalized,),
        ).fetchall()
        cursor = conn.execute(
            "UPDATE messages SET suppressed = 1 WHERE suppressed = 0 AND recipient_address = ?",
            (normalized,),
        )
        for row in alias_rows:
            _refresh_alias_stats(conn, row["alias_id"])
    return cursor.rowcount


def create_excluded_alias(address: str, reason: str | None = None) -> dict[str, Any]:
    normalized = normalize_address(address)
    local_part, domain = split_address(normalized)
    if not local_part or not domain:
        raise ValueError("alias không hợp lệ")

    created_at = utc_now_iso()
    clean_reason = (reason or "").strip() or None
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO excluded_aliases(address, local_part, domain, reason, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(address) DO UPDATE SET reason = excluded.reason
            """,
            (normalized, local_part, domain, clean_reason, created_at),
        )
        row = conn.execute("SELECT * FROM excluded_aliases WHERE address = ?", (normalized,)).fetchone()
    suppress_messages_for_address(normalized)
    return row_to_excluded_alias(row)


def delete_excluded_alias(excluded_alias_id: int) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM excluded_aliases WHERE id = ?", (excluded_alias_id,)).fetchone()
        if row is None:
            return None
        conn.execute("DELETE FROM excluded_aliases WHERE id = ?", (excluded_alias_id,))
    return row_to_excluded_alias(row)


def list_forwarding_rules(search: str = "") -> list[dict[str, Any]]:
    with _connect() as conn:
        query = """
            SELECT
                rules.*,
                (
                    SELECT deliveries.status
                    FROM forwarding_deliveries AS deliveries
                    WHERE deliveries.rule_id = rules.id
                    ORDER BY deliveries.id DESC
                    LIMIT 1
                ) AS last_status,
                (
                    SELECT deliveries.last_error
                    FROM forwarding_deliveries AS deliveries
                    WHERE deliveries.rule_id = rules.id
                    ORDER BY deliveries.id DESC
                    LIMIT 1
                ) AS last_error,
                (
                    SELECT MAX(deliveries.forwarded_at)
                    FROM forwarding_deliveries AS deliveries
                    WHERE deliveries.rule_id = rules.id
                      AND deliveries.status = 'forwarded'
                ) AS last_forwarded_at
            FROM forwarding_rules AS rules
        """
        values: list[Any] = []
        if search.strip():
            pattern = f"%{search.strip().lower()}%"
            query += " WHERE LOWER(rules.source_address) LIKE ? OR LOWER(rules.target_address) LIKE ?"
            values.extend([pattern, pattern])
        query += " ORDER BY rules.created_at DESC, rules.id DESC"
        rows = conn.execute(query, values).fetchall()
    return [row_to_forwarding_rule(row) for row in rows]


def create_forwarding_rule(source_addresses: Any, target_addresses: Any) -> dict[str, Any]:
    sources = _normalize_forwarding_values(source_addresses)
    targets = _normalize_forwarding_values(target_addresses)
    if not sources or not targets:
        raise ValueError("Alias và email chuyển tiếp không được để trống")
    source = ",".join(sources)
    target = ",".join(targets)
    now = utc_now_iso()
    with _connect() as conn:
        existing_rows = conn.execute(
            "SELECT id, source_addresses_json, source_address FROM forwarding_rules"
        ).fetchall()
        source_set = set(sources)
        for existing in existing_rows:
            existing_sources = set(
                _decode_forwarding_addresses(
                    existing["source_addresses_json"], existing["source_address"]
                )
            )
            if existing_sources.intersection(source_set):
                raise ValueError("Một alias đã thuộc quy tắc chuyển tiếp khác")
        conn.execute(
            """
            INSERT INTO forwarding_rules(
                source_address, target_address, source_addresses_json, target_addresses_json,
                enabled, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, 1, ?, ?)
            """,
            (source, target, json.dumps(sources), json.dumps(targets), now, now),
        )
        row = conn.execute(
            "SELECT * FROM forwarding_rules WHERE source_address = ?", (source,)
        ).fetchone()
    return row_to_forwarding_rule(row)


def update_forwarding_rule(
    rule_id: int,
    *,
    enabled: bool | None = None,
    source_addresses: Any | None = None,
    target_addresses: Any | None = None,
) -> dict[str, Any] | None:
    with _connect() as conn:
        current = conn.execute(
            "SELECT * FROM forwarding_rules WHERE id = ?", (rule_id,)
        ).fetchone()
        if current is None:
            return None
        sources = _normalize_forwarding_values(
            source_addresses
            if source_addresses is not None
            else _decode_forwarding_addresses(
                current["source_addresses_json"], current["source_address"]
            )
        )
        targets = _normalize_forwarding_values(
            target_addresses
            if target_addresses is not None
            else _decode_forwarding_addresses(
                current["target_addresses_json"], current["target_address"]
            )
        )
        if not sources or not targets:
            raise ValueError("Alias và email chuyển tiếp không được để trống")
        source = ",".join(sources)
        target = ",".join(targets)
        source_set = set(sources)
        existing_rows = conn.execute(
            "SELECT id, source_addresses_json, source_address FROM forwarding_rules WHERE id != ?",
            (rule_id,),
        ).fetchall()
        for existing in existing_rows:
            existing_sources = set(
                _decode_forwarding_addresses(
                    existing["source_addresses_json"], existing["source_address"]
                )
            )
            if existing_sources.intersection(source_set):
                raise ValueError("Một alias đã thuộc quy tắc chuyển tiếp khác")
        cursor = conn.execute(
            """
            UPDATE forwarding_rules
            SET source_address = ?, target_address = ?, source_addresses_json = ?,
                target_addresses_json = ?, enabled = COALESCE(?, enabled), updated_at = ?
            WHERE id = ?
            """,
            (
                source,
                target,
                json.dumps(sources),
                json.dumps(targets),
                None if enabled is None else int(enabled),
                utc_now_iso(),
                rule_id,
            ),
        )
        if cursor.rowcount == 0:
            return None
        if enabled is False:
            conn.execute(
                "UPDATE forwarding_deliveries SET status = 'cancelled', updated_at = ? "
                "WHERE rule_id = ? AND status IN ('pending', 'retrying')",
                (utc_now_iso(), rule_id),
            )
            conn.execute(
                """
                UPDATE forwarding_delivery_targets
                SET status = 'cancelled', updated_at = ?
                WHERE delivery_id IN (
                    SELECT id FROM forwarding_deliveries WHERE rule_id = ?
                ) AND status IN ('pending', 'retrying')
                """,
                (utc_now_iso(), rule_id),
            )
        row = conn.execute(
            "SELECT * FROM forwarding_rules WHERE id = ?", (rule_id,)
        ).fetchone()
    return row_to_forwarding_rule(row)


def delete_forwarding_rule(rule_id: int) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM forwarding_rules WHERE id = ?", (rule_id,)
        ).fetchone()
        if row is None:
            return None
        conn.execute("DELETE FROM forwarding_rules WHERE id = ?", (rule_id,))
    return row_to_forwarding_rule(row)


def _enqueue_forwarding_deliveries(
    conn: sqlite3.Connection,
    *,
    message_id: int,
    recipient_addresses: list[str],
) -> None:
    now = utc_now_iso()
    recipients = list(
        dict.fromkeys(
            normalize_address(address) for address in recipient_addresses if address
        )
    )
    rules = conn.execute(
        "SELECT id, source_address, source_addresses_json, target_address, "
        "target_addresses_json FROM forwarding_rules WHERE enabled = 1"
    ).fetchall()
    for rule in rules:
        sources = _decode_forwarding_addresses(
            rule["source_addresses_json"], rule["source_address"]
        )
        source_address = next(
            (recipient for recipient in recipients if recipient in sources), None
        )
        if source_address is None:
            continue
        targets = _decode_forwarding_addresses(
            rule["target_addresses_json"], rule["target_address"]
        )
        if not targets:
            continue
        target = ",".join(targets)
        conn.execute(
            """
            INSERT OR IGNORE INTO forwarding_deliveries(
                rule_id, message_id, source_address, target_address, target_addresses_json,
                status, attempt_count, next_attempt_at, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, 'pending', 0, ?, ?, ?)
            """,
            (
                rule["id"],
                message_id,
                source_address,
                target,
                json.dumps(targets),
                now,
                now,
                now,
            ),
        )
        delivery = conn.execute(
            "SELECT id FROM forwarding_deliveries WHERE rule_id = ? AND message_id = ?",
            (rule["id"], message_id),
        ).fetchone()
        if delivery is None:
            continue
        for target_address in targets:
            conn.execute(
                """
                INSERT OR IGNORE INTO forwarding_delivery_targets(
                    delivery_id, target_address, status, attempt_count, next_attempt_at,
                    created_at, updated_at
                )
                VALUES (?, ?, 'pending', 0, ?, ?, ?)
                """,
                (delivery["id"], target_address, now, now, now),
            )


def list_due_forwarding_deliveries(limit: int = 20) -> list[dict[str, Any]]:
    now = utc_now_iso()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT
                delivery_targets.id AS target_delivery_id,
                deliveries.id AS delivery_id,
                delivery_targets.attempt_count AS delivery_attempt_count,
                deliveries.source_address AS forwarding_source_address,
                delivery_targets.target_address AS forwarding_target_address,
                messages.*
            FROM forwarding_delivery_targets AS delivery_targets
            JOIN forwarding_deliveries AS deliveries
              ON deliveries.id = delivery_targets.delivery_id
            JOIN forwarding_rules AS rules ON rules.id = deliveries.rule_id
            JOIN messages ON messages.id = deliveries.message_id
            WHERE delivery_targets.status IN ('pending', 'retrying')
              AND deliveries.status IN ('pending', 'retrying')
              AND delivery_targets.next_attempt_at <= ?
              AND rules.enabled = 1
              AND messages.suppressed = 0
            ORDER BY delivery_targets.next_attempt_at ASC, delivery_targets.id ASC
            LIMIT ?
            """,
            (now, max(1, int(limit))),
        ).fetchall()

    deliveries: list[dict[str, Any]] = []
    for row in rows:
        message = row_to_message(row)
        if message is None:
            continue
        deliveries.append(
            {
                "id": row["target_delivery_id"],
                "parent_id": row["delivery_id"],
                "attempt_count": row["delivery_attempt_count"],
                "source_address": row["forwarding_source_address"],
                "target_address": row["forwarding_target_address"],
                "message": message,
            }
        )
    return deliveries


def mark_forwarding_delivery_success(delivery_id: int) -> None:
    now = utc_now_iso()
    with _connect() as conn:
        target = conn.execute(
            "SELECT delivery_id FROM forwarding_delivery_targets WHERE id = ?",
            (delivery_id,),
        ).fetchone()
        if target is None:
            return
        conn.execute(
            """
            UPDATE forwarding_delivery_targets
            SET status = 'forwarded', attempt_count = attempt_count + 1,
                last_error = NULL, updated_at = ?, forwarded_at = ?
            WHERE id = ?
            """,
            (now, now, delivery_id),
        )
        remaining = conn.execute(
            "SELECT COUNT(*) AS count FROM forwarding_delivery_targets "
            "WHERE delivery_id = ? AND status != 'forwarded'",
            (target["delivery_id"],),
        ).fetchone()["count"]
        if remaining == 0:
            conn.execute(
                "UPDATE forwarding_deliveries SET status = 'forwarded', "
                "attempt_count = attempt_count + 1, last_error = NULL, "
                "updated_at = ?, forwarded_at = ? WHERE id = ?",
                (now, now, target["delivery_id"]),
            )
        else:
            retrying = conn.execute(
                "SELECT COUNT(*) AS count FROM forwarding_delivery_targets "
                "WHERE delivery_id = ? AND status = 'retrying'",
                (target["delivery_id"],),
            ).fetchone()["count"]
            conn.execute(
                "UPDATE forwarding_deliveries SET status = ?, updated_at = ? WHERE id = ?",
                ("retrying" if retrying else "pending", now, target["delivery_id"]),
            )


def mark_forwarding_delivery_failure(delivery_id: int, error: str) -> None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT delivery_id, attempt_count FROM forwarding_delivery_targets WHERE id = ?",
            (delivery_id,),
        ).fetchone()
        if row is None:
            return
        next_attempt_count = int(row["attempt_count"] or 0) + 1
        retry_delay = min(3600, 30 * (2 ** min(next_attempt_count - 1, 7)))
        clean_error = str(error or "Forwarding failed")[:500]
        conn.execute(
            """
            UPDATE forwarding_delivery_targets
            SET status = 'retrying', attempt_count = ?, last_error = ?,
                next_attempt_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                next_attempt_count,
                clean_error,
                iso_in_seconds(retry_delay),
                utc_now_iso(),
                delivery_id,
            ),
        )
        conn.execute(
            "UPDATE forwarding_deliveries SET status = 'retrying', last_error = ?, "
            "updated_at = ? WHERE id = ?",
            (clean_error, utc_now_iso(), row["delivery_id"]),
        )


def cleanup_expired_aliases(now_iso: str) -> int:
    if settings.default_alias_hours <= 0:
        return 0
    with _connect() as conn:
        cursor = conn.execute(
            "UPDATE aliases SET status = 'expired' WHERE status = 'active' AND expires_at IS NOT NULL AND expires_at <= ?",
            (now_iso,),
        )
    return cursor.rowcount


def cleanup_old_messages(cutoff_iso: str) -> int:
    with _connect() as conn:
        alias_rows = conn.execute(
            """
            SELECT DISTINCT alias_id
            FROM messages
            WHERE suppressed = 0 AND received_at < ? AND alias_id IS NOT NULL
            """,
            (cutoff_iso,),
        ).fetchall()
        cursor = conn.execute(
            "UPDATE messages SET suppressed = 1 WHERE suppressed = 0 AND received_at < ?",
            (cutoff_iso,),
        )
        for row in alias_rows:
            _refresh_alias_stats(conn, row["alias_id"])
    return cursor.rowcount


def _default_alias_expires_at() -> str | None:
    if settings.default_alias_hours <= 0:
        return None
    return iso_in_hours(settings.default_alias_hours)


def store_message(payload: dict[str, Any]) -> dict[str, Any] | None:
    raw_recipients = payload.get("recipient_addresses") or [payload["recipient_address"]]
    recipient_addresses: list[str] = []
    for raw_recipient in raw_recipients:
        recipient = normalize_address(str(raw_recipient))
        if (
            recipient
            and recipient not in recipient_addresses
            and not is_excluded_alias(recipient)
        ):
            recipient_addresses.append(recipient)
    if not recipient_addresses:
        return None

    imap_mailbox = str(payload.get("imap_mailbox") or settings.imap_username or settings.central_mailbox or "default")
    recipient_aliases: list[tuple[str, dict[str, Any]]] = []
    for recipient_address in recipient_addresses:
        alias = get_alias_by_address(recipient_address)
        if alias is None:
            alias = ensure_alias(
                recipient_address,
                source="inbound",
                expires_at=_default_alias_expires_at(),
            )
        if alias["status"] == "active":
            recipient_aliases.append((recipient_address, alias))
    if not recipient_aliases:
        return None

    recipient_address, primary_alias = recipient_aliases[0]

    attachment_payloads = payload.get("attachment_payloads", [])

    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO messages(
                imap_mailbox, imap_uid, message_id, alias_id, recipient_address, from_name, from_email, subject,
                snippet, text_body, html_body, attachments_json, extracted_links_json, extracted_otps_json, raw_headers_json,
                received_at, mailbox_received_at, ingested_at, unread, suppressed
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0)
            """,
            (
                imap_mailbox,
                payload["imap_uid"],
                payload.get("message_id", ""),
                primary_alias["id"],
                recipient_address,
                payload.get("from_name", ""),
                payload.get("from_email", ""),
                payload.get("subject", ""),
                payload.get("snippet", ""),
                payload.get("text_body", ""),
                payload.get("html_body", ""),
                json.dumps(payload.get("attachments", []), ensure_ascii=False),
                json.dumps(payload.get("extracted_links", []), ensure_ascii=False),
                json.dumps(payload.get("extracted_otps", []), ensure_ascii=False),
                json.dumps(payload.get("raw_headers", {}), ensure_ascii=False),
                payload["received_at"],
                payload.get("mailbox_received_at") or payload["received_at"],
                payload.get("ingested_at") or utc_now_iso(),
            ),
        )
        row = conn.execute(
            "SELECT * FROM messages WHERE imap_mailbox = ? AND imap_uid = ?",
            (imap_mailbox, payload["imap_uid"]),
        ).fetchone()
        if row is not None:
            for mapped_address, alias in recipient_aliases:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO message_recipients(message_id, recipient_address, alias_id)
                    VALUES (?, ?, ?)
                    """,
                    (row["id"], mapped_address, alias["id"]),
                )
                _refresh_alias_stats(conn, alias["id"])
        if row is not None and cursor.rowcount > 0:
            _store_attachment_payloads(conn, row["id"], attachment_payloads)
            _enqueue_forwarding_deliveries(
                conn,
                message_id=row["id"],
                recipient_addresses=[
                    address for address, _alias in recipient_aliases
                ],
            )
    return row_to_message(row)


def _build_message_scope(
    *,
    alias_id: int | None = None,
    filter_name: str = "all",
    search: str = "",
    include_recipient_mappings: bool = False,
) -> tuple[str, list[Any]]:
    query = """
        FROM messages
        LEFT JOIN aliases ON aliases.id = messages.alias_id
    """
    if include_recipient_mappings:
        query += """
            JOIN message_recipients ON message_recipients.message_id = messages.id
            LEFT JOIN aliases AS mapped_aliases ON mapped_aliases.id = message_recipients.alias_id
        """
    query += """
        WHERE messages.suppressed = 0
    """
    if include_recipient_mappings:
        query += " AND COALESCE(mapped_aliases.status, 'active') != 'deleted'"
    else:
        query += " AND COALESCE(aliases.status, 'active') != 'deleted'"
    values: list[Any] = []
    if alias_id is not None:
        if include_recipient_mappings:
            query += " AND message_recipients.alias_id = ?"
        else:
            query += " AND EXISTS (SELECT 1 FROM message_recipients WHERE message_recipients.message_id = messages.id AND message_recipients.alias_id = ?)"
        values.append(alias_id)
    if filter_name == "unread":
        query += " AND unread = 1"
    elif filter_name == "important":
        query += " AND important = 1"
    elif filter_name == "otp":
        query += " AND extracted_otps_json != '[]'"
    elif filter_name == "links":
        query += " AND extracted_links_json != '[]'"
    if search:
        pattern = f"%{search.lower()}%"
        query += """
            AND (
                LOWER(COALESCE(messages.recipient_address, '')) LIKE ?
                OR EXISTS (
                    SELECT 1
                    FROM message_recipients AS search_recipients
                    WHERE search_recipients.message_id = messages.id
                      AND LOWER(search_recipients.recipient_address) LIKE ?
                )
                OR LOWER(COALESCE(aliases.address, '')) LIKE ?
                OR LOWER(COALESCE(aliases.local_part, '')) LIKE ?
                OR LOWER(COALESCE(subject, '')) LIKE ?
                OR LOWER(COALESCE(from_name, '')) LIKE ?
                OR LOWER(COALESCE(from_email, '')) LIKE ?
                OR LOWER(COALESCE(snippet, '')) LIKE ?
            )
        """
        values.extend([pattern, pattern, pattern, pattern, pattern, pattern, pattern, pattern])
    return query, values


def list_messages(*, alias_id: int | None = None, filter_name: str = "all", search: str = "", limit: int = 200) -> list[dict[str, Any]]:
    scope_query, values = _build_message_scope(
        alias_id=alias_id,
        filter_name=filter_name,
        search=search,
        include_recipient_mappings=True,
    )
    query = f"""
        SELECT
            messages.id,
            messages.message_id,
            message_recipients.alias_id,
            message_recipients.recipient_address,
            messages.from_name,
            messages.from_email,
            messages.subject,
            messages.snippet,
            messages.received_at,
            messages.mailbox_received_at,
            messages.ingested_at,
            messages.unread,
            messages.important,
            CASE WHEN messages.extracted_links_json != '[]' THEN 1 ELSE 0 END AS has_links,
            CASE WHEN messages.extracted_otps_json != '[]' THEN 1 ELSE 0 END AS has_otps
        {scope_query}
    """
    query += " ORDER BY received_at DESC LIMIT ?"
    values.append(limit)
    with _connect() as conn:
        rows = conn.execute(query, values).fetchall()
    return [row_to_message_summary(row) for row in rows]


def delete_messages_by_scope(*, alias_id: int | None = None, filter_name: str = "all", search: str = "") -> dict[str, Any]:
    scope_query, values = _build_message_scope(
        alias_id=alias_id,
        filter_name=filter_name,
        search=search,
        include_recipient_mappings=True,
    )
    query = (
        "SELECT messages.id, message_recipients.alias_id, "
        f"message_recipients.recipient_address {scope_query}"
    )

    with _connect() as conn:
        rows = conn.execute(query, values).fetchall()
        if not rows:
            return {"deleted_count": 0, "recipient_addresses": []}

        message_ids = sorted({row["id"] for row in rows})
        alias_ids = sorted({row["alias_id"] for row in rows if row["alias_id"] is not None})
        recipient_addresses = sorted({row["recipient_address"] for row in rows if row["recipient_address"]})
        placeholders = ", ".join("?" for _ in message_ids)
        conn.execute(f"UPDATE messages SET suppressed = 1 WHERE id IN ({placeholders})", message_ids)
        for alias_id_value in alias_ids:
            _refresh_alias_stats(conn, alias_id_value)
    return {"deleted_count": len(message_ids), "recipient_addresses": recipient_addresses}


def _build_sent_message_scope(*, search: str = "") -> tuple[str, list[Any]]:
    query = """
        FROM sent_messages
        WHERE suppressed = 0
    """
    values: list[Any] = []
    if search:
        pattern = f"%{search.lower()}%"
        query += """
            AND (
                LOWER(COALESCE(from_email, '')) LIKE ?
                OR LOWER(COALESCE(to_json, '')) LIKE ?
                OR LOWER(COALESCE(cc_json, '')) LIKE ?
                OR LOWER(COALESCE(subject, '')) LIKE ?
                OR LOWER(COALESCE(text_body, '')) LIKE ?
                OR LOWER(COALESCE(attachments_json, '')) LIKE ?
            )
        """
        values.extend([pattern, pattern, pattern, pattern, pattern, pattern])
    return query, values


def store_sent_message(payload: dict[str, Any]) -> dict[str, Any] | None:
    attachments = payload.get("attachments") or []
    attachment_metadata = [_attachment_metadata(attachment, index) for index, attachment in enumerate(attachments)]
    sent_at = payload.get("sent_at") or utc_now_iso()
    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO sent_messages(
                source_message_id, mode, from_email, to_json, cc_json, subject, text_body,
                attachments_json, message_id, sent_at, suppressed
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (
                payload.get("source_message_id"),
                payload.get("mode") or "reply",
                payload.get("from_email") or settings.smtp_from_address,
                json.dumps(payload.get("to") or [], ensure_ascii=False),
                json.dumps(payload.get("cc") or [], ensure_ascii=False),
                payload.get("subject") or "",
                payload.get("body") or "",
                json.dumps(attachment_metadata, ensure_ascii=False),
                payload.get("message_id") or "",
                sent_at,
            ),
        )
        sent_message_id = cursor.lastrowid
        _store_sent_attachment_payloads(conn, sent_message_id, attachments)
        row = conn.execute("SELECT * FROM sent_messages WHERE id = ?", (sent_message_id,)).fetchone()
    return row_to_sent_message(row)


def list_sent_messages(*, search: str = "", limit: int = 200) -> list[dict[str, Any]]:
    scope_query, values = _build_sent_message_scope(search=search)
    query = f"""
        SELECT id, source_message_id, mode, from_email, to_json, cc_json,
               subject, substr(text_body, 1, 240) AS snippet,
               json_array_length(attachments_json) AS attachment_count,
               message_id, sent_at, suppressed
        {scope_query}
        ORDER BY sent_at DESC LIMIT ?
    """
    values.append(limit)
    with _connect() as conn:
        rows = conn.execute(query, values).fetchall()
    return [row_to_sent_message_summary(row) for row in rows]


def delete_sent_messages_by_scope(*, search: str = "") -> dict[str, Any]:
    scope_query, values = _build_sent_message_scope(search=search)
    query = f"SELECT id {scope_query}"
    with _connect() as conn:
        rows = conn.execute(query, values).fetchall()
        if not rows:
            return {"deleted_count": 0}
        sent_message_ids = [row["id"] for row in rows]
        placeholders = ", ".join("?" for _ in sent_message_ids)
        conn.execute(f"UPDATE sent_messages SET suppressed = 1 WHERE id IN ({placeholders})", sent_message_ids)
    return {"deleted_count": len(sent_message_ids)}


def list_public_messages(*, recipient_address: str) -> list[dict[str, Any]]:
    normalized_recipient = normalize_address(recipient_address)
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT
                messages.id,
                messages.message_id,
                messages.alias_id,
                messages.recipient_address,
                messages.from_name,
                messages.from_email,
                messages.subject,
                messages.snippet,
                messages.received_at,
                messages.mailbox_received_at,
                messages.ingested_at,
                messages.unread,
                messages.important,
                CASE WHEN messages.extracted_links_json != '[]' THEN 1 ELSE 0 END AS has_links,
                CASE WHEN messages.extracted_otps_json != '[]' THEN 1 ELSE 0 END AS has_otps
            FROM messages
            JOIN message_recipients AS recipient_map
              ON recipient_map.message_id = messages.id
             AND recipient_map.recipient_address = ?
            LEFT JOIN aliases AS mapped_alias ON mapped_alias.id = recipient_map.alias_id
            WHERE messages.suppressed = 0
              AND COALESCE(mapped_alias.status, 'active') != 'deleted'
            ORDER BY messages.received_at DESC
            """,
            (normalized_recipient,),
        ).fetchall()
    items = [row_to_message_summary(row) for row in rows]
    for item in items:
        item["recipient_address"] = normalized_recipient
    return items


def list_recent_message_timings(*, limit: int = 20) -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT
                id,
                imap_uid,
                message_id,
                recipient_address,
                from_email,
                subject,
                received_at,
                mailbox_received_at,
                ingested_at
            FROM messages
            WHERE suppressed = 0
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    items: list[dict[str, Any]] = []
    for row in rows:
        items.append(
            {
                "id": row["id"],
                "imap_uid": row["imap_uid"],
                "message_id": row["message_id"],
                "recipient_address": row["recipient_address"],
                "from_email": row["from_email"],
                "subject": decode_mime_text(row["subject"] or ""),
                "received_at": row["received_at"],
                "mailbox_received_at": row["mailbox_received_at"] or row["received_at"],
                "ingested_at": row["ingested_at"] or row["received_at"],
            }
        )
    return items


def get_message(message_id: int) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
    return row_to_message(row)


def get_sent_message(sent_message_id: int) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM sent_messages WHERE id = ? AND suppressed = 0",
            (sent_message_id,),
        ).fetchone()
    return row_to_sent_message(row)


def get_message_attachment(message_id: int, attachment_index: int) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM message_attachments
            WHERE message_id = ? AND attachment_index = ?
            """,
            (message_id, attachment_index),
        ).fetchone()
    return row_to_attachment(row, include_content=True)


def get_sent_message_attachment(sent_message_id: int, attachment_index: int) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM sent_message_attachments
            WHERE sent_message_id = ? AND attachment_index = ?
            """,
            (sent_message_id, attachment_index),
        ).fetchone()
    return row_to_attachment(row, include_content=True)


def list_message_attachment_payloads(message_id: int) -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM message_attachments
            WHERE message_id = ?
            ORDER BY attachment_index ASC
            """,
            (message_id,),
        ).fetchall()
    return [row_to_attachment(row, include_content=True) for row in rows]


def cache_message_attachment_payloads(message_id: int, attachments: list[dict[str, Any]]) -> None:
    with _connect() as conn:
        _store_attachment_payloads(conn, message_id, attachments)


def get_message_for_address(message_id: int, recipient_address: str) -> dict[str, Any] | None:
    normalized_recipient = normalize_address(recipient_address)
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT messages.*
            FROM messages
            JOIN message_recipients AS recipient_map
              ON recipient_map.message_id = messages.id
             AND recipient_map.recipient_address = ?
            LEFT JOIN aliases AS mapped_alias ON mapped_alias.id = recipient_map.alias_id
            WHERE messages.id = ?
              AND messages.suppressed = 0
              AND COALESCE(mapped_alias.status, 'active') != 'deleted'
            """,
            (normalized_recipient, message_id),
        ).fetchone()
    message = row_to_message(row)
    if message is not None:
        message["recipient_address"] = normalized_recipient
    return message


def mark_message_read(message_id: int) -> dict[str, Any] | None:
    with _connect() as conn:
        conn.execute("UPDATE messages SET unread = 0 WHERE id = ?", (message_id,))
        row = conn.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
    return row_to_message(row)


def delete_sent_message(sent_message_id: int) -> dict[str, Any] | None:
    with _connect() as conn:
        existing = conn.execute(
            "SELECT * FROM sent_messages WHERE id = ? AND suppressed = 0",
            (sent_message_id,),
        ).fetchone()
        if existing is None:
            return None
        conn.execute("UPDATE sent_messages SET suppressed = 1 WHERE id = ?", (sent_message_id,))
        row = conn.execute("SELECT * FROM sent_messages WHERE id = ?", (sent_message_id,)).fetchone()
    return row_to_sent_message(row)


def set_message_important(message_id: int, important: bool) -> dict[str, Any] | None:
    with _connect() as conn:
        conn.execute("UPDATE messages SET important = ? WHERE id = ?", (1 if important else 0, message_id))
        row = conn.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
    return row_to_message(row)


def delete_message(message_id: int) -> dict[str, Any] | None:
    with _connect() as conn:
        existing = conn.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
        if existing is None:
            return None
        conn.execute("UPDATE messages SET suppressed = 1 WHERE id = ?", (message_id,))
        if existing["alias_id"] is not None:
            _refresh_alias_stats(conn, existing["alias_id"])
        row = conn.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
    return row_to_message(row)
