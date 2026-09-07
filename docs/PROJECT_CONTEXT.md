# Project Context

- Project: `DarkAmbient Temp Mail`.
- Public app and catch-all domain: `temp.darkambient.co`.
- Mail hostname: `mx.temp.darkambient.co`; central mailbox: `contact@temp.darkambient.co`.
- VPS: `89.117.21.223`; app binds only `127.0.0.1:8012`, Nginx terminates HTTPS, and Docker Mailserver exposes SMTP port `25`.
- Apex `darkambient.co` continues to use Google Workspace MX records and is outside this deployment.
- Backend uses FastAPI, SQLite, IMAP sync, SMTP send/reply/forward, alias auto-discovery, OTP/link extraction, and user/admin sessions.
- Canonical repository: public `https://github.com/shinemusicllc/temp.darkambient.co` with clean history, branch `main`, and a single operational remote `origin`.
- Canonical checkouts: `C:\Users\Cong-PC\Dropbox\Tool-YTB\temp.darkambient.co` locally and `/opt/darkambient-temp-mail/app` on the VPS.
- Runtime `.env`, credentials, database, mailbox data, DKIM private keys, and TLS private keys must remain ignored and outside Git.
