import pytest
from fastapi import HTTPException

from backend.app import db, main
from backend.app.config import settings


def _init_temp_db(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "database_path", tmp_path / "forwarding.db")
    monkeypatch.setattr(settings, "mail_domain", "temp.darkambient.co")
    monkeypatch.setattr(settings, "central_mailbox", "contact@temp.darkambient.co")
    monkeypatch.setattr(settings, "admin_username", "admin")
    monkeypatch.setattr(settings, "admin_password", "admin-pass")
    monkeypatch.setattr(settings, "user_username", "user")
    monkeypatch.setattr(settings, "user_password", "user-pass")
    db.init_db()


def _message_payload(uid: int, recipient: str = "first@temp.darkambient.co") -> dict:
    return {
        "imap_mailbox": "contact@temp.darkambient.co",
        "imap_uid": uid,
        "message_id": f"<message-{uid}@example.com>",
        "recipient_address": recipient,
        "recipient_addresses": [recipient],
        "from_name": "Example",
        "from_email": "sender@example.com",
        "subject": "Forwarding test",
        "snippet": "Body",
        "text_body": "Body",
        "html_body": "",
        "attachments": [],
        "attachment_payloads": [],
        "extracted_links": [],
        "extracted_otps": [],
        "raw_headers": {},
        "received_at": "2026-09-07T00:00:00+00:00",
    }


def test_rule_only_enqueues_new_messages_and_never_duplicates(monkeypatch, tmp_path):
    _init_temp_db(monkeypatch, tmp_path)
    db.store_message(_message_payload(1))
    db.create_forwarding_rule("first@temp.darkambient.co", "owner@gmail.com")

    with db._connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM forwarding_deliveries").fetchone()[0] == 0

    db.store_message(_message_payload(2))
    db.store_message(_message_payload(2))

    with db._connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM forwarding_deliveries").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM forwarding_delivery_targets").fetchone()[0] == 1


def test_forwarding_rule_supports_multiple_sources_and_targets(monkeypatch, tmp_path):
    _init_temp_db(monkeypatch, tmp_path)

    rule = db.create_forwarding_rule(
        ["first@temp.darkambient.co", "second@temp.darkambient.co"],
        ["owner@gmail.com", "backup@outlook.com"],
    )

    assert rule["source_addresses"] == [
        "first@temp.darkambient.co",
        "second@temp.darkambient.co",
    ]
    assert rule["target_addresses"] == ["backup@outlook.com", "owner@gmail.com"]
    assert len(db.list_forwarding_rules(search="backup@outlook")) == 1

    db.store_message(_message_payload(3, recipient="second@temp.darkambient.co"))
    with db._connect() as conn:
        targets = conn.execute(
            "SELECT target_address FROM forwarding_delivery_targets ORDER BY target_address"
        ).fetchall()
    assert [row["target_address"] for row in targets] == [
        "backup@outlook.com",
        "owner@gmail.com",
    ]


def test_disabling_rule_cancels_pending_delivery_and_delete_cascades(monkeypatch, tmp_path):
    _init_temp_db(monkeypatch, tmp_path)
    rule = db.create_forwarding_rule("first@temp.darkambient.co", "owner@gmail.com")
    db.store_message(_message_payload(4))

    updated = db.update_forwarding_rule(rule["id"], enabled=False)
    assert updated["enabled"] is False
    with db._connect() as conn:
        status = conn.execute(
            "SELECT status FROM forwarding_deliveries WHERE rule_id = ?", (rule["id"],)
        ).fetchone()["status"]
    assert status == "cancelled"

    deleted = db.delete_forwarding_rule(rule["id"])
    assert deleted["id"] == rule["id"]
    with db._connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM forwarding_deliveries").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM forwarding_delivery_targets").fetchone()[0] == 0


def test_forwarding_api_rejects_internal_destination(monkeypatch):
    monkeypatch.setattr(settings, "mail_domain", "temp.darkambient.co")

    with pytest.raises(HTTPException) as raised:
        main.create_forwarding_rule(
            {
                "source_address": "first@temp.darkambient.co",
                "target_address": "loop@temp.darkambient.co",
            },
            _session={"role": "admin"},
        )

    assert raised.value.status_code == 400
    assert "tránh vòng lặp" in raised.value.detail


def test_source_alias_cannot_belong_to_two_rules(monkeypatch, tmp_path):
    _init_temp_db(monkeypatch, tmp_path)
    db.create_forwarding_rule("first@temp.darkambient.co", "owner@gmail.com")

    with pytest.raises(ValueError, match="đã thuộc quy tắc"):
        db.create_forwarding_rule(
            ["first@temp.darkambient.co", "second@temp.darkambient.co"],
            "backup@outlook.com",
        )


def test_init_db_backfills_legacy_delivery_targets_idempotently(monkeypatch, tmp_path):
    _init_temp_db(monkeypatch, tmp_path)
    rule = db.create_forwarding_rule("first@temp.darkambient.co", "owner@gmail.com")
    message = db.store_message(_message_payload(5))
    with db._connect() as conn:
        delivery = conn.execute(
            "SELECT id FROM forwarding_deliveries WHERE rule_id = ? AND message_id = ?",
            (rule["id"], message["id"]),
        ).fetchone()
        conn.execute("DROP TABLE forwarding_delivery_targets")

    db.init_db()
    db.init_db()

    with db._connect() as conn:
        targets = conn.execute(
            "SELECT target_address FROM forwarding_delivery_targets WHERE delivery_id = ?",
            (delivery["id"],),
        ).fetchall()
    assert [row["target_address"] for row in targets] == ["owner@gmail.com"]
