from email import message_from_string

from backend.app.parser import (
    extract_attachment_payloads,
    extract_attachments,
    extract_links,
    extract_otps,
    extract_recipient,
    extract_recipients,
    html_to_text,
    prefer_readable_text,
)


def test_extract_recipient_prefers_original_alias_over_central_mailbox():
    message = message_from_string(
        "From: service@example.com\n"
        "To: contact@congmail.top\n"
        "Delivered-To: abc123@congmail.top\n"
        "Subject: Test\n\n"
        "Body"
    )
    assert extract_recipient(message, "congmail.top", "contact@congmail.top") == "abc123@congmail.top"


def test_extract_recipient_from_darkambient_catch_all_header():
    message = message_from_string(
        "From: sender@example.net\n"
        "To: contact@temp.darkambient.co\n"
        "X-Original-To: launch-742@temp.darkambient.co\n"
        "Subject: verification\n\n"
        "Code 123456"
    )
    assert (
        extract_recipient(message, "temp.darkambient.co", "contact@temp.darkambient.co")
        == "launch-742@temp.darkambient.co"
    )


def test_extract_recipients_keeps_all_matching_aliases():
    message = message_from_string(
        "From: service@example.com\n"
        "To: first@temp.darkambient.co, outside@example.com\n"
        "Cc: second@temp.darkambient.co\n"
        "X-Original-To: first@temp.darkambient.co\n"
        "Delivered-To: contact@temp.darkambient.co\n"
        "Subject: Test\n\n"
        "Body"
    )

    assert extract_recipients(
        message,
        "temp.darkambient.co",
        "contact@temp.darkambient.co",
    ) == ["first@temp.darkambient.co", "second@temp.darkambient.co"]


def test_extract_links_and_otps():
    text = "Ma xac nhan cua ban la 847291. Xac minh tai https://service.example/verify?token=abc"
    links = extract_links(text, "")
    otps = extract_otps(text, "")
    assert links[0]["type"] == "verify"
    assert any(item["code"] == "847291" for item in otps)


def test_html_to_text_strips_style_blocks():
    html = (
        "<html><head><style>.btn{color:red} body{font-family:Arial}</style></head>"
        "<body><p>Ma ChatGPT cua ban la 559331</p><a href='https://example.com'>Mo link</a></body></html>"
    )
    text = html_to_text(html)
    assert "font-family" not in text
    assert ".btn" not in text
    assert "Ma ChatGPT cua ban la 559331" in text


def test_prefer_readable_text_falls_back_to_html_when_plain_text_is_css_noise():
    noisy_text = (
        "@font-face { font-family: Soehne; src: url(font.woff2); } "
        ".ExternalClass { width:100%; } #bodyTable { max-width:560px }"
    )
    html = "<html><body><p>Nhap ma xac minh tam thoi 123456</p></body></html>"
    preferred = prefer_readable_text(noisy_text, html)
    assert "123456" in preferred
    assert "font-family" not in preferred


def test_extract_attachments_returns_attachment_metadata():
    message = message_from_string(
        "From: service@example.com\n"
        "To: contact@congmail.top\n"
        "Delivered-To: abc123@congmail.top\n"
        "Subject: Attachment test\n"
        "MIME-Version: 1.0\n"
        "Content-Type: multipart/mixed; boundary=abc\n\n"
        "--abc\n"
        "Content-Type: text/plain; charset=utf-8\n\n"
        "Body\n"
        "--abc\n"
        "Content-Type: application/pdf\n"
        "Content-Disposition: attachment; filename=\"invoice.pdf\"\n"
        "Content-Transfer-Encoding: base64\n\n"
        "JVBERi0xLjQ=\n"
        "--abc--\n"
    )
    attachments = extract_attachments(message)
    assert len(attachments) == 1
    assert attachments[0]["filename"] == "invoice.pdf"
    assert attachments[0]["content_type"] == "application/pdf"
    assert "content" not in attachments[0]

    payloads = extract_attachment_payloads(message)
    assert payloads[0]["index"] == 0
    assert payloads[0]["content"] == b"%PDF-1.4"


def test_extract_otps_rejects_lowercase_false_positive_from_generic_code_context():
    text = "OpenAI Your ChatGPT code is 271686 Enter this temporary verification code to continue."
    html = '<html><body><a href="https://auth.openai.com/email-verification?code=rgin">Continue</a></body></html>'
    otps = extract_otps(text, html)
    assert [item["code"] for item in otps] == ["271686"]


def test_extract_links_keeps_only_confident_action_links():
    text = "Open the verification page at https://auth.openai.com/email-verification?ticket=abc and ignore https://cdn.openai.com/assets/logo.png"
    html = (
        '<html><body>'
        '<a href="https://auth.openai.com/email-verification?ticket=abc">Verify</a>'
        '<a href="https://cdn.openai.com/common/logo.png">Logo</a>'
        '<a href="https://status.openai.com/history">Status</a>'
        '</body></html>'
    )
    links = extract_links(text, html)
    assert links == [
        {
            "url": "https://auth.openai.com/email-verification?ticket=abc",
            "type": "verify",
        }
    ]
