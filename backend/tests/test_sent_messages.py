from backend.app import db
from backend.app.config import settings


def setup_temp_db(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "database_path", tmp_path / "sent.db")
    monkeypatch.setattr(settings, "admin_username", "admin")
    monkeypatch.setattr(settings, "admin_password", "admin-pass")
    monkeypatch.setattr(settings, "user_username", "user")
    monkeypatch.setattr(settings, "user_password", "user-pass")
    db.init_db()


def test_store_sent_message_keeps_recipients_and_attachment_payload(monkeypatch, tmp_path):
    setup_temp_db(monkeypatch, tmp_path)

    item = db.store_sent_message(
        {
            "source_message_id": None,
            "mode": "forward",
            "from_email": "contact@lushmedia.net",
            "to": ["receiver@example.com"],
            "cc": ["copy@example.com"],
            "subject": "Fwd: invoice",
            "body": "Please see attachments.",
            "message_id": "<sent@example.com>",
            "attachments": [
                {
                    "index": 0,
                    "filename": "invoice.pdf",
                    "content_type": "application/pdf",
                    "content": b"%PDF-1.4",
                    "size_bytes": 8,
                }
            ],
        }
    )

    assert item["kind"] == "sent"
    assert item["to"] == ["receiver@example.com"]
    assert item["cc"] == ["copy@example.com"]
    assert item["attachments"][0]["filename"] == "invoice.pdf"
    assert "content" not in item["attachments"][0]

    listed = db.list_sent_messages(search="receiver")
    assert [message["id"] for message in listed] == [item["id"]]
    assert "text_body" not in listed[0]
    assert "html_body" not in listed[0]
    assert "attachments" not in listed[0]
    assert listed[0]["attachment_count"] == 1

    detail = db.get_sent_message(item["id"])
    assert detail["text_body"] == "Please see attachments."
    assert detail["attachments"][0]["filename"] == "invoice.pdf"

    attachment = db.get_sent_message_attachment(item["id"], 0)
    assert attachment["filename"] == "invoice.pdf"
    assert attachment["content_type"] == "application/pdf"
    assert attachment["content"] == b"%PDF-1.4"

