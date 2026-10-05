# Decisions Index

| ID | Decision | Status | Scope | Impact |
| --- | --- | --- | --- | --- |
| DEC-001 | Keep the app as FastAPI backend plus vanilla root HTML/CSS/JS; do not introduce a frontend bundler by default. | Active | app architecture | High |
| DEC-002 | User lookup must support aliases that were never pre-created because inbound mail can auto-discover recipients. | Active | mail flow | High |
| DEC-003 | Mobile user inbox uses a single page scroll for search/list and a separate full-screen reader overlay for message detail. | Active | user mobile UI | Medium |
| DEC-004 | Run an isolated Docker Mailserver/Rspamd stack for `temp.darkambient.co`, preserve apex Google Workspace, and use exact-subdomain DKIM signing with `use_esld=false`. | Active | deployment / mail flow | High |
| DEC-005 | Publish DarkAmbient under `dangcong/temp.darkambient.co` with a clean history; local and VPS checkouts track only `origin/main`. | Active | repository / operations | High |
| DEC-006 | Port upstream mail capabilities selectively while preserving DarkAmbient contracts, branding, data and isolated deployment. | Active | app architecture / mail flow | High |

