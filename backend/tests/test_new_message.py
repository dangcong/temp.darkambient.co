from pathlib import Path
import base64

import pytest
from fastapi import HTTPException

from backend.app import main


ROOT = Path(__file__).resolve().parents[2]


def test_standalone_send_endpoint_sends_and_stores_message(monkeypatch):
    assert hasattr(main, "send_new_message"), "Standalone send endpoint is missing"

    captured = {}

    def fake_send_composed_message(**kwargs):
        captured.update(kwargs)
        return {
            "mode": kwargs["mode"],
            "to": ["receiver@example.com"],
            "cc": [],
            "subject": kwargs["subject"],
            "from": "contact@temp.darkambient.co",
            "message_id": "<new-message@temp.darkambient.co>",
            "attachment_count": 0,
        }

    def fake_store_sent_message(payload):
        captured["stored"] = payload
        return {"id": 1, **payload}

    monkeypatch.setattr(main, "send_composed_message", fake_send_composed_message)
    monkeypatch.setattr(main.db, "store_sent_message", fake_store_sent_message)

    result = main.send_new_message(
        {
            "from_alias": "sales@temp.darkambient.co",
            "to": "receiver@example.com",
            "cc": "",
            "subject": "Fresh message",
            "body": "Hello from DarkAmbient.",
        },
        _session={"username": "admin", "role": "admin"},
    )

    assert result["ok"] is True
    assert captured["source_message"] == {}
    assert captured["mode"] == "send"
    assert captured["from_value"] == "sales@temp.darkambient.co"
    assert captured["attachments"] == []
    assert captured["stored"]["source_message_id"] is None
    assert captured["stored"]["mode"] == "send"


def test_standalone_send_decodes_and_stores_attachments(monkeypatch):
    captured = {}

    def fake_send_composed_message(**kwargs):
        captured.update(kwargs)
        return {
            "mode": "send",
            "to": ["receiver@example.com"],
            "cc": [],
            "subject": "Có tệp",
            "from": "sales@temp.darkambient.co",
            "message_id": "<attachment@temp.darkambient.co>",
            "attachment_count": 1,
        }

    monkeypatch.setattr(main, "send_composed_message", fake_send_composed_message)
    monkeypatch.setattr(main.db, "store_sent_message", lambda payload: captured.setdefault("stored", payload) or {"id": 2})

    result = main.send_new_message(
        {
            "from_alias": "sales@temp.darkambient.co",
            "to": "receiver@example.com",
            "subject": "Có tệp",
            "body": "Nội dung",
            "attachments": [
                {
                    "filename": "invoice.pdf",
                    "content_type": "application/pdf",
                    "content_base64": base64.b64encode(b"%PDF-test").decode(),
                }
            ],
        },
        _session={"username": "admin", "role": "admin"},
    )

    assert result["ok"] is True
    assert captured["attachments"][0]["content"] == b"%PDF-test"
    assert captured["stored"]["attachments"][0]["filename"] == "invoice.pdf"


def test_standalone_send_rejects_invalid_attachment_base64(monkeypatch):
    monkeypatch.setattr(main, "send_composed_message", lambda **_kwargs: pytest.fail("SMTP should not be called"))

    with pytest.raises(HTTPException) as raised:
        main.send_new_message(
            {
                "to": "receiver@example.com",
                "subject": "Invalid attachment",
                "body": "Body",
                "attachments": [
                    {
                        "filename": "bad.txt",
                        "content_type": "text/plain",
                        "content_base64": "not-valid-base64!",
                    }
                ],
            },
            _session={"username": "admin", "role": "admin"},
        )

    assert raised.value.status_code == 400


def test_forward_route_uses_alias_and_combines_uploaded_attachments(monkeypatch):
    captured = {}
    original = {
        "index": 0,
        "filename": "original.pdf",
        "content_type": "application/pdf",
        "content": b"original",
    }

    monkeypatch.setattr(
        main.db,
        "get_message",
        lambda _message_id: {"id": 12, "recipient_address": "sales@temp.darkambient.co"},
    )
    monkeypatch.setattr(main, "_resolve_message_attachments", lambda _message: [original])

    def fake_send_composed_message(**kwargs):
        captured.update(kwargs)
        return {
            "mode": "forward",
            "to": ["receiver@example.com"],
            "cc": [],
            "subject": "Fwd: Files",
            "from": "sales@temp.darkambient.co",
            "message_id": "<forward@temp.darkambient.co>",
            "attachment_count": 2,
        }

    monkeypatch.setattr(main, "send_composed_message", fake_send_composed_message)
    monkeypatch.setattr(main.db, "store_sent_message", lambda payload: {"id": 5, **payload})

    result = main.send_message(
        12,
        {
            "mode": "forward",
            "from_alias": "sales@temp.darkambient.co",
            "to": "receiver@example.com",
            "subject": "Fwd: Files",
            "body": "Files attached",
            "attachments": [
                {
                    "filename": "new.txt",
                    "content_type": "text/plain",
                    "content_base64": base64.b64encode(b"new").decode(),
                }
            ],
        },
        _session={"username": "admin", "role": "admin"},
    )

    assert result["ok"] is True
    assert captured["from_value"] == "sales@temp.darkambient.co"
    assert [item["filename"] for item in captured["attachments"]] == [
        "original.pdf",
        "new.txt",
    ]


def test_admin_ui_exposes_new_message_composer():
    index_html = (ROOT / "index.html").read_text(encoding="utf-8")
    app_js = (ROOT / "app.js").read_text(encoding="utf-8")

    assert 'id="newMessageBtn"' in index_html
    assert 'id="newMessageModal"' in index_html
    assert 'id="newMessageFrom"' in index_html
    assert 'id="newMessageAttachmentInput"' in index_html
    assert 'id="forwardingTabBtn"' in index_html
    assert 'id="forwardingSearchInput"' in index_html
    assert 'id="forwardingEditModal"' in index_html
    assert 'app.js?v=20260907-mail-capabilities' in index_html
    assert 'style.css?v=20260907-mail-capabilities' in index_html
    assert "function openNewMessageComposer()" in app_js
    assert "function sendNewMessage(event)" in app_js
    assert "serializeAttachmentFiles" in app_js
    assert "data-edit-forwarding-rule" in app_js
    assert "'/api/forwarding-rules'" in app_js
    assert "from_alias: dom.newMessageFrom.value" in app_js
    assert "return 'Mới';" in app_js
    assert "'/api/messages/send'" in app_js
    assert "LushMail" not in index_html
    assert "LushMail" not in app_js
