from pathlib import Path

import pytest
from fastapi import HTTPException

from backend.app import db, main
from backend.app.config import settings


ROOT = Path(__file__).resolve().parents[2]


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


def test_admin_list_keeps_distinct_rows_when_rfc_message_id_is_reused(monkeypatch, tmp_path):
    _init_temp_db(monkeypatch, tmp_path)
    first = _message_payload(10)
    second = _message_payload(11)
    second["message_id"] = first["message_id"]
    db.store_message(first)
    db.store_message(second)

    rows = [
        item
        for item in db.list_messages()
        if item["recipient_address"] == "first@temp.darkambient.co"
    ]

    assert {item["id"] for item in rows} == {1, 2}


def test_recipient_alias_status_is_scoped_to_the_selected_mapping(monkeypatch, tmp_path):
    _init_temp_db(monkeypatch, tmp_path)
    stored = db.store_message(_message_payload(12))
    first_alias = db.get_alias_by_address("first@temp.darkambient.co")
    second_alias = db.get_alias_by_address("second@temp.darkambient.co")

    db.delete_alias(second_alias["id"])
    assert db.get_message_for_address(stored["id"], "second@temp.darkambient.co") is None
    assert db.get_message_for_address(stored["id"], "first@temp.darkambient.co") is not None

    db.reactivate_alias(second_alias["id"])
    db.delete_alias(first_alias["id"])
    assert db.list_public_messages(recipient_address="first@temp.darkambient.co") == []
    assert len(db.list_public_messages(recipient_address="second@temp.darkambient.co")) == 1


def test_delete_scope_uses_mapped_alias_and_counts_messages_once(monkeypatch, tmp_path):
    _init_temp_db(monkeypatch, tmp_path)
    stored = db.store_message(_message_payload(13))
    first_alias = db.get_alias_by_address("first@temp.darkambient.co")
    second_alias = db.get_alias_by_address("second@temp.darkambient.co")
    db.delete_alias(first_alias["id"])

    result = db.delete_messages_by_scope(alias_id=second_alias["id"])

    assert result["deleted_count"] == 1
    assert db.get_message(stored["id"])["suppressed"] is True


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


def test_public_routes_authorize_every_mapped_recipient(monkeypatch, tmp_path):
    _init_temp_db(monkeypatch, tmp_path)
    payload = _message_payload(3)
    payload["attachments"] = [
        {
            "index": 0,
            "filename": "result.txt",
            "content_type": "text/plain",
            "disposition": "attachment",
            "size_bytes": 4,
        }
    ]
    payload["attachment_payloads"] = [
        {
            **payload["attachments"][0],
            "content": b"test",
        }
    ]
    stored = db.store_message(payload)

    detail = main.public_get_message(
        stored["id"], alias="second@temp.darkambient.co", _session={}
    )
    attachment = main.public_download_message_attachment(
        stored["id"], 0, alias="second@temp.darkambient.co", _session={}
    )

    assert detail["item"]["recipient_address"] == "second@temp.darkambient.co"
    assert attachment.body == b"test"

    for route in (
        lambda: main.public_get_message(
            stored["id"], alias="outside@temp.darkambient.co", _session={}
        ),
        lambda: main.public_download_message_attachment(
            stored["id"], 0, alias="outside@temp.darkambient.co", _session={}
        ),
    ):
        with pytest.raises(HTTPException) as error:
            route()
        assert error.value.status_code == 404


def test_admin_detail_can_preserve_the_selected_recipient_alias(monkeypatch, tmp_path):
    _init_temp_db(monkeypatch, tmp_path)
    stored = db.store_message(_message_payload(5))

    detail = main.get_message(
        stored["id"],
        recipient_address="second@temp.darkambient.co",
        _session={"role": "admin"},
    )

    assert detail["item"]["recipient_address"] == "second@temp.darkambient.co"


def test_public_translation_uses_active_recipient_identity(monkeypatch, tmp_path):
    _init_temp_db(monkeypatch, tmp_path)
    stored = db.store_message(_message_payload(4))
    captured = {}

    def fake_translate(message, target_language):
        captured.update(message)
        return {"translated_text": "Xin chào", "target_language": target_language}

    monkeypatch.setattr(main, "translate_message", fake_translate)

    result = main.public_translate_email(
        stored["id"],
        alias="second@temp.darkambient.co",
        payload={"target_language": "vi"},
        _session={},
    )

    assert result["ok"] is True
    assert captured["recipient_address"] == "second@temp.darkambient.co"

    with pytest.raises(HTTPException) as error:
        main.public_translate_email(
            stored["id"],
            alias="outside@temp.darkambient.co",
            payload={"target_language": "vi"},
            _session={},
        )
    assert error.value.status_code == 404


def test_user_reader_keeps_active_alias_on_detail_actions():
    user_js = (ROOT / "user.js").read_text(encoding="utf-8")

    assert "state.currentAlias = payload.alias?.address" in user_js
    assert "?alias=${encodeURIComponent(state.currentAlias)}" in user_js
    assert "new URLSearchParams({ alias: state.currentAlias })" in user_js


def test_admin_flag_updates_preserve_each_row_recipient_identity():
    app_js = (ROOT / "app.js").read_text(encoding="utf-8")

    assert "function mergeMessageFlags(existing, updated)" in app_js
    assert "item.id === messageId ? mergeMessageFlags(item, updated) : item" in app_js
    assert "state.selectedMessageCache = mergeMessageFlags" in app_js
    assert "item.id === messageId ? updated : item" not in app_js
