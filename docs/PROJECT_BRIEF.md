# Project Brief

## Purpose
- `DarkAmbient` is a FastAPI + vanilla HTML/CSS/JS temp-mail app for checking inboxes at `@temp.darkambient.co`.
- The core user flow is: enter an email alias, sync/list inbound messages, open message detail, inspect OTP/link/content quickly.
- Admin flow manages users and the broader inbox; user flow is a focused public-style lookup workspace behind login.

## System Shape
- Root static files (`index.html`, `app.js`, `style.css`) implement the admin shell.
- Root user files (`user.html`, `user.js`, `user.css`) implement the user inbox lookup and reader.
- `backend/app/` contains FastAPI routes, auth/session, SQLite persistence, IMAP sync, parsing, translation, and send helpers.
- `deploy/` contains VPS runtime scripts/config.

## Mail Capabilities
- One inbound message can belong to every parsed `To`/`Cc` alias through `message_recipients`; admin and user views preserve the active recipient identity.
- Admin can send a new message, reply, or forward using an `@temp.darkambient.co` alias and up to 10 attachments / 18 MB total.
- Forwarding rules accept multiple source aliases and external targets. New inbound messages enqueue one delivery per target with idempotency and exponential retry.
- Message list endpoints return summaries; full bodies and attachment payloads remain detail-only.

## Build / Test / Run
- Dev server: `.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8010 --reload`
- Tests: `.\.venv\Scripts\python.exe -m pytest -q`
- Python syntax: `Get-ChildItem .\backend\app\*.py | ForEach-Object { .\.venv\Scripts\python.exe -m py_compile $_.FullName }`
- Frontend syntax: `node --check .\app.js` and `node --check .\user.js`

## Global Invariants
- Keep the app vanilla: no bundler or frontend framework unless there is a clear reason.
- Do not require users to pre-create aliases before receiving mail; inbound mail must still auto-discover aliases.
- Preserve UTF-8 Vietnamese UI text.
- Keep UI changes close to the current DarkAmbient mail-workspace visual language and avoid broad layout rewrites.
- Treat the public `temp.darkambient.co` repository as the only operational Git origin; local and VPS maintenance use its `main` branch.
- Never allow an automatic-forward target inside `@temp.darkambient.co`; this prevents forwarding loops.

