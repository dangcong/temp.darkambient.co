from backend.app import db
from backend.app.config import settings


def _init_temp_db(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "database_path", tmp_path / "multi-recipient.db")
    monkeypatch.setattr(settings, "admin_username", "admin")
    monkeypatch.setattr(settings, "admin_password", "admin-pass")
    monkeypatch.setattr(settings, "user_username", "user")
    monkeypatch.setattr(settings, "user_password", "user-pass")
    db.init_db()


def _message_payload(uid: int) -> dict:
    return {
        "imap_mailbox": "contact@temp.darkambient.co",
        "imap_uid": uid,
        "message_id": f"<message-{uid}@example.com>",
        "recipient_address": "first@temp.darkambient.co",
        "recipient_addresses": [
            "first@temp.darkambient.co",
            "second@temp.darkambient.co",
        ],
        "from_name": "Example",
        "from_email": "sender@example.com",
        "subject": "Multi recipient",
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


def test_one_message_is_available_for_all_recipient_aliases(monkeypatch, tmp_path):
    _init_temp_db(monkeypatch, tmp_path)

    stored = db.store_message(_message_payload(1))

    assert stored["recipient_address"] == "first@temp.darkambient.co"
    second_inbox = db.list_public_messages(
        recipient_address="second@temp.darkambient.co"
    )
    assert len(second_inbox) == 1
    assert second_inbox[0]["message_id"] == "<message-1@example.com>"
    assert second_inbox[0]["recipient_address"] == "second@temp.darkambient.co"
    assert db.get_message_for_address(
        stored["id"], "second@temp.darkambient.co"
    )["id"] == stored["id"]
    assert db.get_message_for_address(
        stored["id"], "outside@temp.darkambient.co"
    ) is None
    assert {
        (item["message_id"], item["recipient_address"])
        for item in db.list_messages()
    } == {
        ("<message-1@example.com>", "first@temp.darkambient.co"),
        ("<message-1@example.com>", "second@temp.darkambient.co"),
    }


def test_init_db_backfills_recipient_mapping_idempotently(monkeypatch, tmp_path):
    _init_temp_db(monkeypatch, tmp_path)
    stored = db.store_message(_message_payload(2))
    with db._connect() as conn:
        conn.execute("DROP TABLE message_recipients")

    db.init_db()
    db.init_db()

    with db._connect() as conn:
        rows = conn.execute(
            "SELECT recipient_address FROM message_recipients WHERE message_id = ?",
            (stored["id"],),
        ).fetchall()
    assert [row["recipient_address"] for row in rows] == [
        "first@temp.darkambient.co"
    ]
