# Mail Capabilities

## Scope
- Canonical domain: `temp.darkambient.co`.
- Inbound catch-all aliases do not require pre-creation.
- Admin supports send, reply, manual forward and automatic forward; user inbox remains read-only.

## Recipient identity
- `messages.recipient_address` remains the legacy primary recipient.
- `message_recipients(message_id, recipient_address)` is the canonical many-to-many lookup for every parsed `To`/`Cc` alias.
- `list_public_messages()` and `get_message_for_address()` must filter through this mapping and return the requested alias as `recipient_address`.
- Admin rows use `(message.id, recipient_address)` as the display identity; detail requests pass the selected recipient so reply/forward keep the correct sender alias.
- `init_db()` backfills legacy rows idempotently.

## Outgoing messages and attachments
- `POST /api/messages/send` sends a standalone message.
- `POST /api/messages/{message_id}/send` handles `reply` and `forward`.
- `from_alias` must belong to `@temp.darkambient.co`; SMTP envelope sender remains the configured mailbox so SPF/DKIM behavior is unchanged.
- Attachment payloads use base64 at the API boundary, then bytes internally. Maximum: 10 files and 18 MB total. Manual forward combines original and newly uploaded attachments under the same limit.
- Client-facing SMTP failures are generic; full exception detail is server-log only.

## Automatic forwarding
- Admin CRUD: `GET/POST /api/forwarding-rules`, `PATCH/DELETE /api/forwarding-rules/{rule_id}`.
- `forwarding_rules` stores source/target lists and enabled state.
- `forwarding_deliveries` provides one idempotent parent job per `(rule_id, message_id)`.
- `forwarding_delivery_targets` tracks status, attempts, error and next retry independently for every target.
- A rule only enqueues messages stored after the rule is enabled. Disabling cancels pending/retrying work; deleting cascades delivery history.
- Internal targets under `@temp.darkambient.co` are rejected to prevent loops.
- Retry delay doubles from 30 seconds and is capped at one hour.
- A dedicated forwarding scheduler polls due targets independently from IMAP polling/IDLE, so retries do not wait for another inbound message.

## Performance and caching
- Admin inbox/sent list rows use summary serializers and do not load full body or attachment payload content.
- Versioned static assets receive immutable caching; HTML and API responses remain revalidatable/no-cache as appropriate.
- Schema creation, additive migration and backfill run in one SQLite transaction; a migration failure rolls back the whole attempt.

## Verification
```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
node --check .\app.js
node --check .\user.js
git diff --check
```
