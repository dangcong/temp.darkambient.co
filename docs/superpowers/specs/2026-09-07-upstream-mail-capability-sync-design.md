# DarkAmbient Upstream Mail Capability Sync Design

## Trạng thái

- Ngày: 2026-09-07
- Trạng thái: Đã duyệt thiết kế hội thoại, chờ duyệt bản spec được ghi vào repo
- Repo đích: `dangcong/temp.darkambient.co`
- Upstream tham khảo: `lushmediadev/Lush-Temp-Mail` tại commit `10e66c9`
- Phương án được chọn: port chọn lọc theo capability

## Bối cảnh

DarkAmbient là sản phẩm độc lập, có branding, domain, lịch sử Git và stack deploy riêng. Upstream tiếp tục phát triển thêm multi-recipient, sender alias, outgoing attachments, auto-forwarding và tối ưu tải inbox. Mục tiêu của đợt này là đưa các capability đó vào DarkAmbient mà không biến repo thành fork, không nhập branding LushMail và không thay đổi mail routing của apex `darkambient.co` đang dùng Google Workspace.

## Mục tiêu

1. Nhận đúng một email cho mọi alias `@temp.darkambient.co` xuất hiện trong danh sách người nhận.
2. Cho admin chọn alias gửi và đính kèm tệp khi gửi mới, reply hoặc forward.
3. Cung cấp quản lý auto-forwarding gồm tạo, sửa, bật/tắt, tìm kiếm và xóa rule.
4. Retry từng địa chỉ forward độc lập và dùng header/envelope phù hợp cho deliverability.
5. Giảm payload và thời gian tải inbox/sent bằng summary API, chỉ tải detail khi người dùng mở email.
6. Giữ nguyên DarkAmbient Aurora Teal, luồng admin/user, Google Workspace apex và stack VPS hiện tại.

## Ngoài phạm vi

- Không merge Git history hoặc đặt upstream làm remote vận hành.
- Không sao chép logo, tên, màu sắc, domain hay deploy config của LushMail.
- Không đổi MX của `darkambient.co`, tài khoản Google Workspace hoặc subdomain ngoài `temp.darkambient.co`.
- Không thay SQLite bằng database khác, không thêm frontend bundler và không viết lại UI framework.
- Không replay auto-forward cho email lịch sử.
- Không tạo mailbox vật lý cho từng alias; catch-all trung tâm và IMAP sync vẫn là nguồn nhận mail.

## Các phương án đã cân nhắc

### 1. Merge/copy toàn bộ upstream

Nhanh ở lần đầu nhưng rủi ro ghi đè branding, auth, translation, mobile reader, deploy stack và các chỉnh sửa riêng của DarkAmbient. Diff lớn ở `db.py`, `main.py`, `app.js`, HTML và CSS làm khả năng regression cao.

### 2. Port chọn lọc theo capability — được chọn

Đưa từng capability qua lớp dữ liệu, backend, test và UI; giữ nguyên contract cũ nếu có thể. Cách này tốn công tích hợp hơn nhưng kiểm soát được migration, cho phép TDD theo từng lát dọc và giữ DarkAmbient độc lập.

### 3. Theo dõi upstream lâu dài bằng fork/subtree

Giảm công lấy thay đổi tương lai nhưng xung đột với quyết định repo độc lập, lịch sử sạch và yêu cầu không liên hệ vận hành với repo tham khảo.

## Nguyên tắc tương thích

- API hiện có tiếp tục hoạt động; field mới là additive hoặc optional.
- `messages.id`, alias ID, sent-message ID và dữ liệu hiện có không bị tái tạo.
- Các cột legacy như `messages.recipient_address` và `messages.alias_id` vẫn được giữ để code cũ và rollback code đọc được.
- Migration dùng `CREATE TABLE IF NOT EXISTS`, kiểm tra `PRAGMA table_info`, `ALTER TABLE` additive và `INSERT OR IGNORE` backfill.
- Mọi endpoint quản trị mới tiếp tục yêu cầu admin session.
- UI dùng vanilla HTML/CSS/JS và visual language được ghi trong `docs/UI_SYSTEM.md`.

## Kiến trúc dữ liệu

### Multi-recipient

Thêm bảng `message_recipients`:

| Field | Ý nghĩa |
| --- | --- |
| `id` | Primary key |
| `message_id` | Liên kết tới một email gốc trong `messages` |
| `recipient_address` | Alias normalized thuộc `temp.darkambient.co` |
| `alias_id` | Liên kết tới alias được auto-create hoặc đã tồn tại |

Unique key `(message_id, recipient_address)` ngăn ghi trùng cùng alias. Index theo `recipient_address` phục vụ public inbox và filter admin. Một email gốc tiếp tục lưu một lần trong `messages`; admin có thể hiển thị một summary row cho mỗi recipient mapping, còn detail được truy cập bằng cặp `message_id + recipient_address` khi cần phân biệt alias đang xem.

Migration backfill mọi email hiện có từ `messages.recipient_address` và `messages.alias_id` sang `message_recipients`. Không thay primary recipient legacy.

### Outgoing attachments

Giữ metadata trong `attachments_json` và lưu payload nhị phân trong:

- `message_attachments` cho inbound/original attachments được cache từ IMAP.
- `sent_message_attachments` cho tệp đã gửi.

Payload API từ browser dùng danh sách object `filename`, `content_type`, `content_base64`. Backend decode và validate trước khi SMTP send. Giới hạn chuẩn:

- Tối đa 10 tệp cho một email.
- Tổng payload decoded tối đa 18 MB.
- Forward gộp attachment gốc và attachment upload mới rồi áp cùng giới hạn.
- Reply không tự động đính kèm attachment gốc.

### Forwarding rules và delivery queue

Giữ cấu trúc tương thích upstream:

- `forwarding_rules`: rule, source/target legacy, JSON arrays cho nhiều nguồn/đích, trạng thái enabled và timestamps.
- `forwarding_deliveries`: một lần rule khớp với một message, unique `(rule_id, message_id)`.
- `forwarding_delivery_targets`: một hàng cho mỗi địa chỉ đích với status, attempt count, error và thời điểm retry riêng.

Một source alias chỉ thuộc tối đa một rule definition để tránh rule chồng chéo khó dự đoán. Mọi target phải nằm ngoài `@temp.darkambient.co`; source và target trong cùng rule cũng không được trùng nhau. Xóa rule cascade các delivery liên quan; disable rule hủy các delivery chưa hoàn tất của rule đó.

## Data flow

### Nhận email

1. IMAP IDLE hoặc polling phát hiện UID mới trong mailbox catch-all.
2. Parser đọc toàn bộ địa chỉ trong các recipient header hợp lệ, normalize và chỉ giữ `@temp.darkambient.co`; mailbox trung tâm không được coi là temp alias nếu chỉ là đích catch-all nội bộ.
3. Hệ thống auto-create/resolve từng alias.
4. Transaction lưu một `messages` row và các `message_recipients` rows.
5. Cùng transaction enqueue những forwarding rule enabled khớp ít nhất một recipient.
6. Sau commit, SSE thông báo inbox thay đổi; list API trả summary và detail chỉ tải khi row được mở.

Nếu email đã tồn tại theo mailbox namespace/UID hoặc message identity hiện có, insert và enqueue phải idempotent, không tạo delivery thứ hai.

### Gửi mới, reply và forward

1. Composer lấy danh sách alias hiện có và cho phép chọn `from_alias` thuộc `temp.darkambient.co`.
2. Browser encode attachment, hiển thị tên/kích thước và chặn count/size hiển nhiên trước khi submit.
3. Backend normalize người nhận, alias gửi và decode/validate lại attachment.
4. SMTP message dùng alias đã chọn trong visible `From`/`Reply-To` khi phù hợp, nhưng dùng tài khoản SMTP đã cấu hình làm envelope sender để giữ authentication và deliverability.
5. Reply giữ `In-Reply-To`/`References`; forward giữ attachment gốc cộng attachment mới; gửi mới dùng alias đã chọn.
6. Sau SMTP success, lưu sent message và attachment payload. Nếu SMTP fail, trả `502` và không ghi sent item giả.

Để tương thích client cũ, `from_alias` là optional. Khi không có, gửi mới fallback về `SMTP_FROM_ADDRESS`; reply/forward fallback theo hành vi hiện tại. UI mới luôn gửi lựa chọn rõ ràng.

### Auto-forward

1. Worker lấy các target delivery có status `pending` hoặc `retrying` và `next_attempt_at <= now`.
2. Mỗi target được gửi độc lập; failure của một target không chặn target khác.
3. Email forward giữ subject gốc, kèm phần thông tin thư gốc, HTML body và attachments.
4. SMTP envelope dùng `SMTP_FROM_ADDRESS`; `Reply-To` và `X-Forwarded-To` dùng source alias để người nhận biết và reply đúng ngữ cảnh.
5. Success chuyển target sang `forwarded`; failure lưu error tối đa hợp lý và retry exponential backoff, bắt đầu 30 giây và cap 1 giờ.
6. Parent delivery chỉ thành `forwarded` khi mọi target hoàn tất; nếu còn target lỗi/pending thì phản ánh trạng thái tổng hợp tương ứng.

## API contract

### API được bổ sung

| Method | Route | Contract chính |
| --- | --- | --- |
| `GET` | `/api/forwarding-rules?search=` | Trả `{"items": [...]}` |
| `POST` | `/api/forwarding-rules` | Nhận `source_addresses[]`, `target_addresses[]`; trả `{"item": rule}` |
| `PATCH` | `/api/forwarding-rules/{rule_id}` | Sửa cả source/target hoặc chỉ `enabled`; trả rule mới |
| `DELETE` | `/api/forwarding-rules/{rule_id}` | Xóa rule; trả rule đã xóa |

Validation trả `400` cho payload/domain/state không hợp lệ, `404` khi rule không tồn tại và `409` khi source alias chồng với rule khác.

### API được mở rộng tương thích

- `POST /api/messages/send`: nhận optional `from_alias` và `attachments[]`.
- `POST /api/messages/{message_id}/send`: nhận optional `from_alias` và `attachments[]`; `mode` vẫn là `reply` hoặc `forward`.
- Message/sent list trả summary, không trả full bodies hoặc attachment payload.
- Detail và attachment download routes giữ nguyên; public detail phải xác minh recipient mapping trước khi trả message.
- Detail response có recipient đang được chọn để UI hiển thị đúng alias đối với email multi-recipient.
- HTML shell trả `Cache-Control: no-cache`; CSS, JS và logo có version query được cache dài hạn với `public, max-age=31536000, immutable`.

## UI/UX

UI mới phải nối tiếp layout phẳng, mật độ và Aurora Teal hiện có:

- Compose modal thêm alias selector và attachment picker/list; không tạo nested card hoặc panel trang trí mới.
- Forwarding management nằm trong admin navigation hiện tại, có search, danh sách rule, trạng thái, edit, enable/disable và delete confirmation.
- Primary action, focus ring, selected state dùng Aurora Teal; destructive action giữ màu semantic đỏ.
- Tiếng Việt phải hiển thị UTF-8 đúng ở HTML, JS, error message và test fixture.
- Modal backdrop chỉ đóng modal khi click đúng backdrop, không đóng do click vào phần tử con.
- Inbox/sent hiển thị summary ngay; loading detail không làm mất selection và cache detail theo identity phù hợp.
- Sent list dùng nhãn mode rõ ràng cho send/reply/forward/auto-forward mà không đưa chi tiết SMTP thô lên giao diện.
- Không hiển thị raw SMTP delivery internals cho người dùng cuối.

## Migration và an toàn dữ liệu

Migration chạy khi app startup và phải hoàn toàn idempotent:

1. Tạo bảng/index còn thiếu.
2. Thêm additive columns vào bảng hiện hữu sau khi kiểm tra schema.
3. Backfill JSON arrays của forwarding rule legacy nếu có.
4. Backfill per-target delivery rows nếu có delivery legacy.
5. Backfill `message_recipients` từ primary recipient hiện tại bằng `INSERT OR IGNORE`.
6. Chạy trong transaction; lỗi migration làm startup fail rõ ràng thay vì chạy với schema nửa vời.

Trước production deploy, tạo backup SQLite nhất quán. Vì schema chỉ additive, rollback code có thể bỏ qua bảng/cột mới; chỉ restore DB backup nếu migration gây lỗi dữ liệu thực tế.

## Error handling và quan sát vận hành

- Không trả stack trace, SMTP credential hoặc raw SMTP response nhạy cảm cho client.
- Log failure gồm delivery/rule/message identifier và target cần thiết, không log attachment content hoặc secret.
- SMTP failure của gửi thủ công trả thông báo người dùng ổn định và `502`.
- Forwarding failure được giữ trong queue để retry và hiển thị trạng thái/lỗi rút gọn trong admin.
- IMAP ingest và queue processing không được giữ SQLite transaction mở trong thời gian network I/O SMTP.

## Kế hoạch kiểm thử

### Backend unit/integration

- Parser tìm đủ nhiều alias, loại duplicate và bỏ recipient ngoài domain.
- Migration trên DB cũ tạo schema mới và backfill đúng; chạy lần hai không thay đổi kết quả.
- Một message multi-recipient chỉ lưu một message row nhưng xuất hiện đúng cho từng alias.
- Public inbox/detail không đọc được message qua alias không thuộc recipient mapping.
- Forwarding rule CRUD, search, conflict, enable/disable và cascade delete.
- Enqueue không replay hoặc duplicate; retry từng target độc lập với backoff đúng.
- Alias sender, envelope sender, `Reply-To`, `X-Forwarded-To`, subject và threading headers.
- Attachment count/size/base64 validation; send/reply/forward và sent attachment download.
- Message list và sent list không chứa full body/content nhưng detail vẫn đầy đủ.

### Frontend

- `node --check app.js` và `node --check user.js`.
- Regression test cho branding DarkAmbient/Aurora Teal và asset cache version.
- Browser QA desktop/mobile cho compose, attachment list, forwarding rules, empty/loading/error states, modal backdrop và multi-recipient detail.
- Kiểm tra tiếng Việt không có mojibake.

### End-to-end trước production

- Nhận một email gửi đồng thời tới ít nhất hai alias `@temp.darkambient.co`.
- Gửi mới từ alias, reply và forward ra mailbox ngoài; xác minh SPF/DKIM/DMARC bằng received headers.
- Gửi attachment nhỏ và kiểm tra tải lại từ Sent.
- Tạo rule nhiều nguồn/nhiều đích, xác minh từng đích nhận và retry không nhân bản target đã thành công.
- Chạy full pytest suite và health check local trước khi push/deploy.

## Triển khai

1. Implement trên feature branch/worktree từ checkout canonical local.
2. Chạy migration/test trên DB tạm hoặc bản sao production, không dùng production DB cho thử nghiệm.
3. Merge vào `main`, push `origin/main` của `dangcong/temp.darkambient.co`.
4. Trên VPS `/opt/darkambient-temp-mail/app`, xác minh clean checkout và remote đúng repo này.
5. Backup DB, pull fast-forward và chạy `deploy/darkambient/update.sh` để rebuild riêng app service.
6. Xác minh health endpoint, login, inbox, send/reply/forward, forwarding worker và production UI.

Không recreate Docker Mailserver/Rspamd, không xóa volume, không thay DNS và không chạm apex Google Workspace trong deployment này.

## Rollback

- Revert application commit hoặc checkout commit production trước đó rồi rebuild app service.
- Giữ nguyên database nếu migration additive đã hoàn tất và dữ liệu hợp lệ.
- Nếu migration gây sai dữ liệu, dừng app, lưu bản DB lỗi phục vụ điều tra, restore backup predeploy rồi chạy code cũ.
- Disable forwarding rules là safety switch đầu tiên nếu chỉ forwarding worker có sự cố.

## Tiêu chí chấp nhận

1. Tất cả capability trong mục Mục tiêu hoạt động trên local và production.
2. Toàn bộ test cũ và test mới pass; không regression auth, translation, SSE/IMAP IDLE, delete scope hoặc mobile reader.
3. API cũ tiếp tục nhận payload cũ; client cũ không buộc gửi field mới.
4. Dữ liệu production được giữ nguyên và migration chạy lại an toàn.
5. Giao diện chỉ mang thương hiệu DarkAmbient/Aurora Teal và không chứa dấu vết vận hành LushMail.
6. Apex `darkambient.co` tiếp tục dùng Google Workspace; chỉ stack `temp.darkambient.co` bị thay đổi.
