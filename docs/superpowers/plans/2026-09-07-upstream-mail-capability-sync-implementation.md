# DarkAmbient Upstream Mail Capability Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tích hợp multi-recipient, sender alias, outgoing attachments, auto-forwarding và lightweight list loading từ upstream vào DarkAmbient mà không làm thay đổi branding, dữ liệu hiện có hoặc stack mail độc lập.

**Architecture:** Port từng capability theo lát dọc bằng migration SQLite additive, FastAPI API tương thích ngược và UI vanilla hiện hữu. Một message gốc ánh xạ tới nhiều recipient alias; forwarding queue tách từng target để retry độc lập; list endpoints trả summary còn detail tải theo nhu cầu.

**Tech Stack:** Python 3, FastAPI, SQLite stdlib, IMAP, SMTP, vanilla HTML/CSS/JavaScript, pytest, Docker Compose, Nginx.

**Spec:** `docs/superpowers/specs/2026-09-07-upstream-mail-capability-sync-design.md`

## Global Constraints

- Canonical local checkout: `C:\Users\Cong-PC\Dropbox\Tool-YTB\temp.darkambient.co`.
- Canonical VPS checkout: `/opt/darkambient-temp-mail/app`; remote vận hành duy nhất là `origin` của `dangcong/temp.darkambient.co`.
- Giữ FastAPI + SQLite + vanilla HTML/CSS/JS; không thêm ORM hoặc frontend bundler.
- Giữ branding DarkAmbient và Aurora Teal: primary `#0f766e`, hover `#115e59`, surface `#f0fdfa`.
- Giữ apex `darkambient.co` trên Google Workspace; không thay MX/DNS hoặc recreate Docker Mailserver/Rspamd.
- API mới là additive; payload cũ không bắt buộc gửi `from_alias` hoặc `attachments`.
- Migration chỉ additive/idempotent; giữ `messages.id`, alias ID, sent-message ID và các cột recipient legacy.
- Outgoing attachments: tối đa 10 tệp, tổng decoded payload tối đa 18 MB.
- Tất cả chuỗi UI tiếng Việt lưu và render UTF-8.
- Mỗi task backend/behavior đi theo RED → GREEN → regression test → commit.

---

### Task 1: Multi-recipient parser, schema và inbox identity

**Files:**
- Modify: `backend/app/parser.py:200-217`
- Modify: `backend/app/db.py:26-300,320-386,955-1051,1052-1134,1157-1226,1227-1310`
- Modify: `backend/app/imap_sync.py:1-30,145-184,266-320`
- Modify: `backend/tests/test_parser.py:1-40`
- Create: `backend/tests/test_multi_recipient.py`

**Interfaces:**
- Produces: `extract_recipients(message: Message, domain: str, central_mailbox: str) -> list[str]`.
- Preserves: `extract_recipient(...) -> str | None` trả recipient đầu tiên cho caller cũ.
- Extends: `store_message(payload)` đọc `recipient_addresses: list[str]`, fallback `recipient_address`.
- Produces: `message_recipients(message_id, recipient_address, alias_id)` và recipient-aware `get_message_for_address()`.

- [ ] **Step 1: Viết parser test thất bại cho nhiều alias**

```python
def test_extract_recipients_keeps_all_matching_aliases():
    message = message_from_string(
        "From: service@example.com\n"
        "To: first@temp.darkambient.co, outside@example.com\n"
        "Cc: second@temp.darkambient.co\n"
        "X-Original-To: first@temp.darkambient.co\n\nBody"
    )
    assert extract_recipients(
        message, "temp.darkambient.co", "contact@temp.darkambient.co"
    ) == ["first@temp.darkambient.co", "second@temp.darkambient.co"]
```

- [ ] **Step 2: Chạy RED parser test**

Run: `python -m pytest backend/tests/test_parser.py::test_extract_recipients_keeps_all_matching_aliases -q`

Expected: FAIL vì `extract_recipients` chưa tồn tại.

- [ ] **Step 3: Implement parser tối thiểu và compatibility wrapper**

Thu thập theo thứ tự từ `X-Original-To`, `Delivered-To`, `Envelope-To`, `To`, `Cc`; normalize, bỏ central mailbox, bỏ ngoài domain và de-duplicate ổn định. `extract_recipient` gọi `extract_recipients` rồi trả phần tử đầu hoặc `None`.

- [ ] **Step 4: Chạy parser tests tới GREEN**

Run: `python -m pytest backend/tests/test_parser.py -q`

Expected: PASS toàn bộ parser tests.

- [ ] **Step 5: Viết DB migration/storage tests thất bại**

`backend/tests/test_multi_recipient.py` phải chứng minh bằng SQLite thật:

```python
stored = db.store_message({
    **message_payload,
    "recipient_address": "first@temp.darkambient.co",
    "recipient_addresses": [
        "first@temp.darkambient.co",
        "second@temp.darkambient.co",
    ],
})
assert [item["recipient_address"] for item in db.list_public_messages(
    recipient_address="second@temp.darkambient.co"
)] == ["second@temp.darkambient.co"]
assert db.get_message_for_address(stored["id"], "outside@temp.darkambient.co") is None
```

Thêm migration test tạo DB legacy chỉ có primary recipient, gọi `init_db()` hai lần và assert đúng một mapping được backfill.

- [ ] **Step 6: Chạy RED DB tests**

Run: `python -m pytest backend/tests/test_multi_recipient.py -q`

Expected: FAIL vì chưa có `message_recipients` hoặc alias thứ hai không truy cập được.

- [ ] **Step 7: Implement additive schema, backfill và recipient-aware queries**

Tạo `message_recipients`, index address, `INSERT OR IGNORE` primary-recipient backfill. `store_message` resolve/auto-create mọi alias, lưu một `messages` row và nhiều mapping rows trong cùng transaction. Admin list join mapping để trả một summary per recipient; public list/detail dùng `EXISTS`/mapping thay vì chỉ `messages.recipient_address`.

- [ ] **Step 8: Cập nhật IMAP parse/sync**

`_parse_message()` ghi cả `recipient_address` đầu tiên và `recipient_addresses`; `sync_once()` publish SSE cho mọi recipient của message đã lưu.

- [ ] **Step 9: Chạy GREEN và regression suite**

Run: `python -m pytest backend/tests/test_multi_recipient.py backend/tests/test_parser.py backend/tests/test_excluded_aliases.py -q`

Expected: PASS.

- [ ] **Step 10: Commit**

```bash
git add backend/app/parser.py backend/app/db.py backend/app/imap_sync.py backend/tests/test_parser.py backend/tests/test_multi_recipient.py
git commit -m "feat: support multi-recipient inbox delivery"
```

### Task 2: Lightweight message/sent lists và cache contract

**Files:**
- Modify: `backend/app/db.py:320-430,1052-1185`
- Modify: `backend/app/main.py:167-177,381-390,446-479`
- Modify: `backend/tests/test_excluded_aliases.py:61-end`
- Modify: `backend/tests/test_sent_messages.py:1-end`
- Create: `backend/tests/test_cache_headers.py`

**Interfaces:**
- Preserves: `row_to_message(row)` và `row_to_sent_message(row)` cho detail.
- Produces: `row_to_sent_message_summary(row) -> dict[str, Any]`.
- Guarantees: list responses không có `text_body`, `html_body`, `raw_headers` hoặc attachment binary content.

- [ ] **Step 1: Viết failing tests cho summary list**

Thêm assertions trên response thật từ DB:

```python
listed = db.list_sent_messages(search="receiver")
assert "text_body" not in listed[0]
assert "html_body" not in listed[0]
assert listed[0]["attachment_count"] == 1
assert db.get_sent_message(item["id"])["text_body"] == "Please see attachments."
```

Message-list test phải assert list giữ `has_links`, `has_otps`, recipient identity nhưng không có full body/header.

- [ ] **Step 2: Chạy RED summary tests**

Run: `python -m pytest backend/tests/test_sent_messages.py backend/tests/test_excluded_aliases.py -q`

Expected: FAIL vì sent list đang trả detail payload.

- [ ] **Step 3: Implement sent summary mapper và giữ detail routes**

`row_to_sent_message_summary` trả `id`, `kind`, `mode`, `from_email`, `to`, `cc`, `subject`, `snippet`, `sent_at`, `received_at`, `attachment_count`, `unread`, `important`, `can_translate`; `list_sent_messages` dùng mapper này, còn `get_sent_message` giữ full payload.

- [ ] **Step 4: Viết RED cache-header tests qua FastAPI client**

```python
assert client.get("/").headers["cache-control"] == "no-cache"
assert "immutable" in client.get("/app.js?v=20260907-mail-capabilities").headers["cache-control"]
```

- [ ] **Step 5: Implement cache policy và chạy GREEN**

`add_cache_headers` đặt `no-cache` cho HTML shell; chỉ versioned JS/CSS/SVG nhận `public, max-age=31536000, immutable`.

Run: `python -m pytest backend/tests/test_sent_messages.py backend/tests/test_excluded_aliases.py backend/tests/test_cache_headers.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/db.py backend/app/main.py backend/tests/test_excluded_aliases.py backend/tests/test_sent_messages.py backend/tests/test_cache_headers.py
git commit -m "perf: load mailbox lists from summaries"
```

### Task 3: Sender alias và outgoing attachments backend

**Files:**
- Modify: `backend/app/mailer.py:1-end`
- Modify: `backend/app/main.py:1-113,391-424,551-590`
- Modify: `backend/tests/test_mailer.py:1-end`
- Modify: `backend/tests/test_new_message.py:1-end`
- Modify: `backend/tests/test_sent_messages.py`

**Interfaces:**
- Produces: `validate_outgoing_attachments(attachments) -> list[dict[str, Any]]`.
- Produces: `_decode_outgoing_attachments(value) -> list[dict[str, Any]]`.
- Extends: `send_composed_message(..., from_value: str | None = None, attachments=None)`.
- Extends: both send routes accept optional `from_alias`, `attachments[]`.

- [ ] **Step 1: Viết RED mailer tests**

```python
result = mailer.send_composed_message(
    source_message={}, mode="send",
    from_value="news@temp.darkambient.co",
    to_value="receiver@example.com", cc_value="",
    subject="Update", body="Attached",
    attachments=[{"filename": "note.txt", "content_type": "text/plain", "content": b"hello"}],
)
assert sent["message"]["From"].endswith("<news@temp.darkambient.co>")
assert sent["from_addr"] == mailer.settings.smtp_from_address
assert result["attachment_count"] == 1
```

Thêm test alias ngoài `temp.darkambient.co` bị `ValueError`, 11 tệp bị từ chối và tổng content lớn hơn `18 * 1024 * 1024` bị từ chối.

- [ ] **Step 2: Chạy RED mailer tests**

Run: `python -m pytest backend/tests/test_mailer.py -q`

Expected: FAIL ở `from_value`/validation chưa tồn tại.

- [ ] **Step 3: Implement mailer GREEN**

Dùng alias normalized cho visible `From`; luôn truyền `settings.smtp_from_address` vào `send_message(..., from_addr=...)`; thêm `Reply-To` khi visible sender khác envelope; attach bytes bằng MIME type; giữ reply threading headers.

- [ ] **Step 4: Viết RED route tests cho base64 và compatibility**

Gọi `send_new_message` và `send_message` với:

```python
{
    "from_alias": "news@temp.darkambient.co",
    "attachments": [{
        "filename": "note.txt",
        "content_type": "text/plain",
        "content_base64": "aGVsbG8=",
    }],
}
```

Assert mailer nhận `content == b"hello"`, sent storage giữ payload, invalid base64 trả `400`; payload cũ không có field mới vẫn gửi được.

- [ ] **Step 5: Implement decode/send routes và chạy GREEN**

Forward lấy attachment gốc từ cache/IMAP, gộp tệp upload mới rồi validate tổng; reply chỉ dùng tệp upload mới. Chỉ store sent item sau SMTP success.

Run: `python -m pytest backend/tests/test_mailer.py backend/tests/test_new_message.py backend/tests/test_sent_messages.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/mailer.py backend/app/main.py backend/tests/test_mailer.py backend/tests/test_new_message.py backend/tests/test_sent_messages.py
git commit -m "feat: send from aliases with attachments"
```

### Task 4: Forwarding rule schema, queue và admin API

**Files:**
- Modify: `backend/app/db.py:26-300,430-520,900-1051`
- Modify: `backend/app/main.py:1-113,352-380`
- Create: `backend/tests/test_forwarding_rules.py`

**Interfaces:**
- Produces: `list_forwarding_rules(search="")`, `create_forwarding_rule(source_addresses, target_addresses)`, `update_forwarding_rule(rule_id, *, enabled=None, source_addresses=None, target_addresses=None)`, `delete_forwarding_rule(rule_id)`.
- Produces: `_enqueue_forwarding_deliveries(conn, *, message_id, recipient_addresses)`.
- Produces routes: `GET/POST/PATCH/DELETE /api/forwarding-rules`.

- [ ] **Step 1: Viết RED CRUD/migration tests bằng SQLite thật**

Test create nhiều source/target, search khớp từng row, update, disable, delete, source conflict và chạy migration hai lần. Ví dụ:

```python
rule = db.create_forwarding_rule(
    ["first@temp.darkambient.co", "second@temp.darkambient.co"],
    ["one@example.com", "two@example.com"],
)
assert rule["source_addresses"] == [
    "first@temp.darkambient.co", "second@temp.darkambient.co"
]
assert rule["target_addresses"] == ["one@example.com", "two@example.com"]
```

- [ ] **Step 2: Chạy RED forwarding DB tests**

Run: `python -m pytest backend/tests/test_forwarding_rules.py -q`

Expected: FAIL vì schema/functions chưa tồn tại.

- [ ] **Step 3: Implement schema và CRUD tối thiểu**

Tạo `forwarding_rules`, `forwarding_deliveries`, `forwarding_delivery_targets`, indexes và JSON-array backfill. Normalize/dedupe input; source phải thuộc mail domain; target phải là email hợp lệ nằm ngoài `@temp.darkambient.co`; reject source-target intersection và source overlap giữa rule. Khi disable rule, chuyển các delivery `pending`/`retrying` sang `cancelled`; foreign keys cascade delivery khi xóa rule.

- [ ] **Step 4: Viết RED enqueue/per-target tests**

Store message sau khi rule tồn tại; assert đúng một parent delivery và hai target rows. Store lại cùng mailbox/UID; assert không duplicate. Tạo rule sau message; assert không enqueue lịch sử.

- [ ] **Step 5: Implement enqueue trong transaction store_message**

Chỉ gọi `_enqueue_forwarding_deliveries` khi `messages` insert mới thành công; match bằng tập recipient mappings; dùng unique keys để idempotent.

- [ ] **Step 6: Viết RED API contract tests**

Dùng FastAPI client/admin dependency override để assert response wrappers `{"items": ...}`/`{"item": ...}` và status `400`, `404`, `409` đúng trường hợp.

- [ ] **Step 7: Implement API normalization/routes và chạy GREEN**

Run: `python -m pytest backend/tests/test_forwarding_rules.py backend/tests/test_multi_recipient.py -q`

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/app/db.py backend/app/main.py backend/tests/test_forwarding_rules.py
git commit -m "feat: manage automatic forwarding rules"
```

### Task 5: Forwarding worker và deliverability

**Files:**
- Modify: `backend/app/mailer.py`
- Modify: `backend/app/db.py`
- Modify: `backend/app/imap_sync.py:1-30,58-265`
- Modify: `backend/tests/test_mailer.py`
- Modify: `backend/tests/test_forwarding_rules.py`

**Interfaces:**
- Produces: `send_automatic_forward(*, source_message, target_address, attachments=None)`.
- Produces: `list_due_forwarding_deliveries(limit=20)`, `mark_forwarding_delivery_success(id)`, `mark_forwarding_delivery_failure(id, error)`.
- Produces: `MailSyncService._process_pending_forwards() -> None`.

- [ ] **Step 1: Viết RED deliverability test**

```python
result = mailer.send_automatic_forward(
    source_message={
        "recipient_address": "first@temp.darkambient.co",
        "from_name": "Original Sender",
        "from_email": "sender@example.com",
        "subject": "Original subject",
        "text_body": "Original body",
        "html_body": "<p>Original body</p>",
        "received_at": "2026-09-07T00:00:00+00:00",
    },
    target_address="target@example.com",
)
assert sent["from_addr"] == mailer.settings.smtp_from_address
assert sent["message"]["Reply-To"] == "first@temp.darkambient.co"
assert sent["message"]["X-Forwarded-To"] == "first@temp.darkambient.co"
assert result["subject"] == "Original subject"
```

- [ ] **Step 2: Chạy RED mailer test, implement và chạy GREEN**

Run RED/GREEN: `python -m pytest backend/tests/test_mailer.py -q`

Implementation giữ subject/HTML/attachments, thêm khối thông tin thư gốc trong text body và dùng envelope sender mặc định.

- [ ] **Step 3: Viết RED independent retry tests**

Hai target cùng parent: fake SMTP thành công target A và fail target B. Assert A ở `forwarded`, B ở `retrying`, `attempt_count == 1`, `next_attempt_at` tăng; lần claim sau không trả A. Backoff là `min(3600, 30 * 2**min(attempt-1, 7))`.

- [ ] **Step 4: Implement queue claim/status aggregation**

Network I/O chạy ngoài transaction. Success/failure update target row riêng; parent thành `forwarded` chỉ khi mọi target đã forward. Error được truncate 500 ký tự và không chứa secret/payload.

- [ ] **Step 5: Viết RED worker audit test rồi implement worker**

Worker lấy cached attachments, gọi `send_automatic_forward`, lưu sent audit row với mode `auto-forward`, rồi mark success; SMTP exception chỉ mark failure và không crash sync loop.

- [ ] **Step 6: Chạy GREEN/regression tests**

Run: `python -m pytest backend/tests/test_forwarding_rules.py backend/tests/test_mailer.py backend/tests/test_sent_messages.py -q`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/mailer.py backend/app/db.py backend/app/imap_sync.py backend/tests/test_mailer.py backend/tests/test_forwarding_rules.py
git commit -m "feat: forward mail with per-target retry"
```

### Task 6: Admin composer và forwarding management UI

**Files:**
- Modify: `index.html:1-end`
- Modify: `app.js:1-end`
- Modify: `style.css:1-end`
- Modify: `backend/tests/test_new_message.py`
- Modify: `backend/tests/test_branding.py`

**Interfaces:**
- Consumes: forwarding CRUD routes, mailbox list, `from_alias`, `attachments[]`.
- Produces UI state: `forwardingRules`, `forwardingSearch`, `forwardingEditId`, `newMessageAttachments`, `composeDraft.attachments`.
- Produces helpers: `serializeAttachment(file)`, `renderAttachmentSelection(items)`, `loadForwardingRules()`, `renderForwardingRules()`, `saveForwardingRule()`.

- [ ] **Step 1: Tạo failing UI shell acceptance test**

Qua FastAPI TestClient, request `/` và assert DOM shell có accessible forwarding navigation/panel, alias selector, file input `multiple` và asset version `20260907-mail-capabilities`. Test branding tiếp tục assert logo `DarkAmbient`, Aurora Teal và không có wordmark `LushMail`.

- [ ] **Step 2: Chạy RED UI shell tests**

Run: `python -m pytest backend/tests/test_new_message.py backend/tests/test_branding.py -q`

Expected: FAIL vì controls/panel/version mới chưa tồn tại.

- [ ] **Step 3: Implement HTML/CSS shell theo UI system**

Thêm forwarding folder/panel vào sidebar/admin content hiện tại; composer thêm native alias select và file picker/list phẳng. Dùng token Aurora Teal hiện có, red cho delete, slate cho secondary; không thêm decorative cards hoặc nested panels.

- [ ] **Step 4: Implement composer behavior**

`FileReader.readAsDataURL` tạo `content_base64` không gồm prefix; cập nhật/remove attachment theo index; preflight 10 files/18 MB; submit `from_alias` và attachments cho send/reply/forward. Modal chỉ đóng khi `event.target === backdrop`.

- [ ] **Step 5: Implement forwarding CRUD behavior**

Load/search/render rule rows; form nhận nhiều source/target, edit cả hai, toggle enabled, delete có confirm. Hiển thị last status/error rút gọn, không hiển thị raw SMTP response hoặc internal IDs.

- [ ] **Step 6: Sửa sent mode labels và detail cache identity**

Hiển thị `Gửi mới`, `Trả lời`, `Chuyển tiếp`, `Tự động chuyển tiếp`; cache inbound detail bằng `${message.id}:${message.recipient_address}` để multi-recipient row không dùng nhầm active alias.

- [ ] **Step 7: Chạy GREEN/syntax tests**

Run:

```bash
python -m pytest backend/tests/test_new_message.py backend/tests/test_branding.py -q
node --check app.js
```

Expected: PASS, không có syntax error.

- [ ] **Step 8: Browser QA local**

Chạy app local, kiểm tra desktop và mobile: open/close composer, alias select, add/remove file, reply/forward, forwarding create/edit/search/toggle/delete, loading/empty/error state, modal backdrop và UTF-8.

- [ ] **Step 9: Commit**

```bash
git add index.html app.js style.css backend/tests/test_new_message.py backend/tests/test_branding.py
git commit -m "feat: add forwarding and attachment controls"
```

### Task 7: Public inbox recipient identity và integration regression

**Files:**
- Modify: `backend/app/main.py:591-691`
- Modify: `user.js:1-end`
- Modify: `user.html:1-end`
- Modify: `backend/tests/test_multi_recipient.py`
- Modify: `backend/tests/test_branding.py`
- Modify: `docs/UI_SYSTEM.md`
- Modify: `docs/MEMORY_INDEX.md`
- Modify: `docs/PROJECT_BRIEF.md`
- Modify: `docs/CHANGELOG.md`

**Interfaces:**
- Consumes: recipient-aware `list_public_messages()` và `get_message_for_address()`.
- Guarantees: public detail/attachments/translation chỉ trả message khi query alias có mapping.
- Guarantees: admin/user detail hiển thị alias đang được chọn, không chỉ primary recipient legacy.

- [ ] **Step 1: Viết RED public authorization/detail tests**

Tạo một message có hai recipient. Với user session, cả hai alias đọc được inbox/detail/attachment; alias thứ ba nhận `404`. Response detail cho alias hai phải có `recipient_address == "second@temp.darkambient.co"`.

- [ ] **Step 2: Chạy RED public tests**

Run: `python -m pytest backend/tests/test_multi_recipient.py -q`

Expected: FAIL nếu detail vẫn trả primary recipient hoặc authorization chỉ kiểm tra legacy field.

- [ ] **Step 3: Implement recipient-aware public routes/UI**

Mọi public detail/attachment/translation route normalize alias và gọi recipient-aware query. `user.js` giữ alias query khi mở/tải attachment và render active recipient từ detail response.

- [ ] **Step 4: Cập nhật docs và changelog**

Ghi capability/schema/routes mới, canonical local/VPS checkout, vận hành forwarding và giới hạn attachment. Changelog chỉ ghi một entry ngắn cho toàn bộ implementation.

- [ ] **Step 5: Chạy full local verification**

Run:

```bash
python -m pytest backend/tests -q
node --check app.js
node --check user.js
git diff --check
```

Expected: toàn bộ tests PASS; JS syntax PASS; không whitespace error.

- [ ] **Step 6: Browser regression QA**

Kiểm tra admin và user desktop/mobile: login role redirect, inbox, multi-recipient detail, translation, attachments, sent, delete scope, users management, SSE refresh và branding DarkAmbient/Aurora Teal.

- [ ] **Step 7: Commit**

```bash
git add backend/app/main.py user.js user.html backend/tests/test_multi_recipient.py backend/tests/test_branding.py docs/UI_SYSTEM.md docs/MEMORY_INDEX.md docs/PROJECT_BRIEF.md docs/CHANGELOG.md
git commit -m "test: cover integrated mail capability sync"
```

### Task 8: Merge, push và production deployment

**Files:**
- Verify: `deploy/darkambient/update.sh`
- Verify: `deploy/darkambient/compose.yaml`
- Verify: `/opt/darkambient-temp-mail/app`

**Interfaces:**
- Consumes: feature branch đã pass toàn bộ local verification.
- Produces: `origin/main` và VPS checkout cùng một verified commit.

- [ ] **Step 1: Rà soát branch và secret safety**

Run:

```bash
git status --short
git log --oneline --decorate main..HEAD
git diff --check main...HEAD
git diff --name-only main...HEAD
```

Xác minh không có `.env`, DB, mailbox data, password, DKIM/TLS private key hoặc upstream branding/deploy config trong diff.

- [ ] **Step 2: Chạy verification cuối**

Run:

```bash
python -m pytest backend/tests -q
node --check app.js
node --check user.js
```

Expected: PASS toàn bộ.

- [ ] **Step 3: Merge fast-forward vào local main và push**

```bash
git checkout main
git merge --ff-only codex/upstream-mail-capabilities
git push origin main
```

- [ ] **Step 4: Predeploy VPS checks và SQLite backup**

Trên VPS, xác minh `/opt/darkambient-temp-mail/app` sạch, branch `main`, remote đúng `dangcong/temp.darkambient.co`, ghi current commit và tạo backup nhất quán của runtime SQLite trước pull.

- [ ] **Step 5: Pull và rebuild riêng app**

```bash
cd /opt/darkambient-temp-mail/app
git pull --ff-only origin main
sudo bash deploy/darkambient/update.sh
```

Không chạy down có xóa volume và không recreate mailserver/Rspamd.

- [ ] **Step 6: Production health/smoke/E2E**

Xác minh health endpoint, login, DarkAmbient branding, inbox, gửi mới từ alias, reply, forward, attachment, forwarding rule và multi-recipient. Kiểm tra Docker service/log không có migration, IMAP, SMTP hoặc forwarding loop error.

- [ ] **Step 7: Rollback nếu health gate thất bại**

Disable forwarding rules nếu lỗi chỉ ở worker. Nếu app regression, checkout production commit đã ghi ở Step 4 và rebuild. Chỉ restore predeploy DB backup khi xác nhận migration làm sai dữ liệu; giữ bản DB lỗi để điều tra.
