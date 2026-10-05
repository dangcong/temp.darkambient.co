# Worklog

## 2026-05-13 00:00 - Add admin sent mailbox

- Re-read the project rules, memory index, and UI system, then kept the admin mailbox layout flat and consistent with the existing LushMail visual language.
- Replaced the visible `Có OTP` / `Có link verify` sidebar shortcuts with `Đã gửi`, backed by new `sent_messages` and `sent_message_attachments` tables that are populated after reply/forward SMTP sends complete.
- Added sent-list and sent-detail rendering in `app.js`: rows show `Đến: ...`, send mode, timestamp, and attachment count; details show From/To/CC/Message-ID, body, copy actions, and download links for stored sent attachments.
- Verified with `node --check app.js`, `python -m py_compile backend/app/db.py backend/app/main.py backend/app/mailer.py`, and the full backend test suite.

## 2026-03-21 18:15 - Re-enable row checkbox without widening admin layout

- Re-read project memory/rules and kept the existing compact admin header untouched, because the user only wanted checkbox selection restored inside the email rows, not another toolbar expansion.
- Re-enabled the existing row checkbox DOM in `app.js` by removing the forced-hide behavior in `style.css`, then changed the checkbox styling to an absolute overlay anchored inside the left padding of each row so it no longer consumes list width.
- Verified on the local admin route with a Playwright-injected sample message that the checkbox is visible again at the start of the row while the search/header layout remains unchanged.

## 2026-03-21 18:05 - Deploy admin delete-all and encoding fixes to VPS

- Re-read project memory/rules, then uploaded the current admin UI files (`index.html`, `app.js`, `style.css`) together with backend delete-all support (`backend/app/db.py`, `backend/app/main.py`) to `/opt/lush-temp-mail/app` on VPS `82.197.71.6`.
- Rebuilt and restarted the live Docker stack from `/opt/lush-temp-mail/app/deploy`, bringing `lushtempmail-app` back up successfully after the image rebuild.
- Verified the public site at `https://lush.congmail.top/` now serves the updated admin HTML containing the entity-based search placeholder and delete-all tooltip, and re-checked `https://lush.congmail.top/api/health` returning `status: ok`.

## 2026-03-21 18:02 - Make admin Vietnamese strings encoding-proof with entities and unicode escapes

- Re-read project memory/rules, then switched the latest admin text fixes to encoding-proof representations because direct Vietnamese literals had already been degraded into `?` during prior edits.
- Replaced the admin search placeholder and delete-all tooltip in `index.html` with HTML entities, and rewrote the delete-all confirm/toast strings in `app.js` using `\\u` escapes so browser rendering no longer depends on terminal/source code page behavior.
- Verified with `node --check app.js` plus a browser run on `http://127.0.0.1:8010/` that `#mainSearch.placeholder` resolves to `TÃ¬m theo alias, sender, subject...` and `#deleteAllBtn.title` resolves to `XÃ³a táº¥t cáº£ email trong inbox hiá»‡n táº¡i`.

## 2026-03-21 17:54 - Fix mojibake on admin delete-all texts

- Re-read project memory/rules, then traced the broken admin copy to mojibake introduced in the last toolbar edits rather than a browser rendering issue.
- Corrected the visible admin header strings around `mainSearch` and `deleteAllBtn`, plus the delete-all confirm/toast copy in `app.js`, so those user-facing texts are back to valid Vietnamese UTF-8.
- Verified syntax again with `node --check app.js` after the text-only corrections.

## 2026-03-21 17:41 - Restore admin header layout and keep only delete-all icon

- Re-read project memory/rules, then rolled back the over-expanded admin toolbar after the user clarified that the header should keep the previous layout and only swap the old refresh icon for a delete-all icon.
- Restored the compact header structure in `index.html` so the admin list area is back to `title + count + search + one icon button` instead of the added multi-action strip.
- Kept the new delete-all behavior with confirm in `app.js`, but downgraded the extra checkbox-selection affordance to a visual no-op so the prior row layout is preserved while the broader backend delete-by-scope API remains available.
- Verified locally with `node --check app.js` and a Playwright admin login smoke that the toolbar now renders with search plus a single delete-all icon button and no `select-page` / `delete-selected` controls.

## 2026-03-21 17:31 - Redesign admin delete actions with checkbox selection and full-scope delete-all

- Re-read project memory/rules, re-used the existing admin palette/components, and applied the `uncodixfy` constraint so the inbox toolbar stayed flat and utility-first instead of turning into another decorative action strip.
- Added a new backend delete-all path for admin inbox scope by introducing `db.delete_messages_by_scope(...)` plus `DELETE /api/messages`, which removes every message matching the current `filter/search` query instead of only the current client page.
- Reworked the admin toolbar to replace the old manual refresh button with `Chá»n trang`, `XÃ³a Ä‘Ã£ chá»n`, and `XÃ³a táº¥t cáº£`, while adding explicit confirm text before `XÃ³a táº¥t cáº£` runs.
- Added checkbox affordances at the start of each email row and wired them into the existing page-scoped multi-select state so the checkbox flow now matches the earlier keyboard shortcuts instead of hiding that behavior behind `Ctrl/Shift/Delete`.
- Verified with `node --check app.js`, `python -m py_compile backend/app/db.py backend/app/main.py`, a `TestClient` smoke for `DELETE /api/messages`, and a local Playwright login smoke that the new toolbar buttons render on the admin route.

## 2026-03-21 15:21 - Redeploy updated user.html to VPS

- Re-read project memory/rules, then uploaded the locally edited `user.html` directly to `/opt/lush-temp-mail/app/user.html` on VPS `82.197.71.6`.
- Rebuilt and restarted the live Docker stack from `/opt/lush-temp-mail/app/deploy` so the static user route picked up the new HTML content.
- Verified the public `https://lush.congmail.top/user.html` response now serves the updated user-facing copy, including the revised meta description and hero text from the local file.

## 2026-03-21 16:11 - Refine user inbox rows to normal mailbox style

- Re-read project memory/rules and reapplied the `uncodixfy` constraint so the inbox list stayed simple, flat, and aligned with the existing admin app instead of drifting into decorative card styling.
- Reworked `user.js` list rendering to prioritize sender name, subject, and a single-line preview, while changing avatar initials to derive from the sender instead of the alias so each row reads like a normal inbox message.
- Updated `user.css` so list/detail avatars are circular, row spacing is tighter, hover/selected states are calmer, and the message metadata hierarchy matches a familiar mailbox layout.
- Verified the frontend with `node --check user.js`, then used the local route at `http://127.0.0.1:8010/user.html` plus injected sample data in Playwright to confirm the new row structure and detail header render correctly.

## 2026-03-21 16:17 - Auto-scroll lookup into inbox view

- Re-read project memory/rules, then adjusted the user lookup flow so a manual `Kiá»ƒm tra` now scrolls the page down to the results shell after data loads.
- Added a dedicated `scrollToLookupResults()` helper in `user.js` that positions the viewport above the list/detail area with a fixed offset, intentionally leaving the alias input still visible at the top instead of hiding the entire hero block.
- Kept silent bootstraps from query params unchanged so only direct user-triggered lookups perform the smooth scroll.
- Verified with `node --check user.js` and a Playwright local smoke that the viewport lands with the form still visible (`formBottom = 59`) while the inbox shell is already in view (`shellTop = 171`).

## 2026-03-21 16:22 - Rebalance post-lookup spacing and redeploy

- Paused the in-progress VPS redeploy, then refined the user-route auto-scroll again after reviewing the user's screenshot: the previous offset hid too much of the lookup form and made the gap to the browser chrome feel cramped.
- Updated `user.js` so `scrollToLookupResults()` now anchors to `lookupForm` with a smaller top offset, which keeps the full input area visible while the inbox shell still appears immediately underneath.
- Bumped the cache-busting asset version in `user.html` to `user-inbox-scroll-4`, uploaded the refreshed `user.html` / `user.js` to `/opt/lush-temp-mail/app`, and rebuilt the live Docker stack from `/opt/lush-temp-mail/app/deploy`.
- Verified production with `https://lush.congmail.top/api/health` returning `status: ok` and `https://lush.congmail.top/user.html` serving the new asset version `user.js?v=20260321-user-inbox-scroll-4`.

## 2026-03-21 16:34 - Redeploy latest user.js edit to VPS

- Re-read project memory/rules, then picked up the latest local `user.js` edit exactly as saved by the user for a targeted VPS deploy.
- Bumped the static asset version in `user.html` from `user-inbox-scroll-4` to `user-js-redeploy-5` so production browsers would not keep serving a cached copy of the previous JavaScript file.
- Uploaded the refreshed `user.js` and `user.html` to `/opt/lush-temp-mail/app`, rebuilt the Docker stack from `/opt/lush-temp-mail/app/deploy`, and confirmed container `lushtempmail-app` came back up successfully.
- Verified live that `https://lush.congmail.top/user.html` now references `user.js?v=20260321-user-js-redeploy-5` and that `https://lush.congmail.top/api/health` still returns `status: ok`.

## 2026-03-21 16:59 - Investigate mail delay and add sync-on-check for user route

- Investigated the live path end-to-end: code review showed `/api/public/inbox` reads directly from SQLite with no backend cache, `received_at` was being derived from the email `Date` header, and the app container was polling IMAP every 4 seconds from the mailbox.
- Verified on VPS that recent Gmail samples were not arriving slowly into the central mailbox: for example UID `21` (`pearhoang99g@gmail.com -> test2@congmail.top`) had IMAP `INTERNALDATE` `21-Mar-2026 10:43:38 +0100`, while SQLite already held the same mail as message `26084` with `received_at` `2026-03-21T09:43:29+00:00`, a gap of only about 9 seconds.
- Identified the real user-path weakness: manual user lookup only queried `/api/public/inbox`, so it could miss up to one IMAP polling cycle if the message had reached the mailbox just after the previous background sync.
- Implemented a serialized sync path by adding a lock inside `MailSyncService.sync_once()`, exposing `POST /api/public/sync` for role `user`, and updating `user.js` so clicking `Kiá»ƒm tra` now triggers a live IMAP sync before reading the inbox.
- Deployed the backend/frontend changes to VPS, bumped the `user.js` asset version to `20260321-public-sync-6`, and verified production with `POST /api/public/sync` under the `user` session returning `{\"ok\":true,\"synced\":1}` plus `api/health` staying `ok`.

## 2026-03-21 15:00 - Fix VPS helper permission issue for set-user

- Reproduced the live VPS error where `lushtempmail set-user ...` failed with `Permission denied` because the helper invoked `deploy/scripts/set_admin_credentials.sh` directly while that file lacked an execute bit after deploy.
- Fixed the immediate runtime issue on VPS by restoring execute permission on the deploy scripts and reinstalling the global `lushtempmail` helper.
- Patched `deploy/scripts/lushtempmail.sh` locally to invoke the credential script via `bash` for both `set-admin` and `set-user`, preventing future deploys from depending on file execute bits.
- Verified on VPS by running `lushtempmail set-user --username user --password 1234`, confirming `.env` updated and the app redeployed successfully, then smoke-tested live login for `user`.

## 2026-03-21 14:56 - Deploy admin/user split to VPS

- Re-read project memory/rules, then packaged the current local runtime diff and uploaded the updated frontend, backend, deploy scripts, and project docs directly to `/opt/lush-temp-mail/app` on VPS `82.197.71.6`.
- Added `USER_USERNAME=user` and a new production `USER_PASSWORD` into the live `deploy/.env` by running the updated `set_admin_credentials.sh --role user ...`, which also rebuilt and restarted the Docker stack.
- Reinstalled the global `lushtempmail` helper from the live repo so the VPS command set now includes `set-user` in addition to the existing admin commands.
- Verified container health from inside the live stack via `/api/health`, then smoke-tested `https://lush.congmail.top` with Playwright: `user` now lands on `user.html` and sees `ÄÄƒng xuáº¥t`, while `admin` still lands on `/`.
- Updated local-only password notes in `deploy/LOCAL_PASSWORDS.md` so the new production `user` credential is available on this machine without committing it to git.

## 2026-03-20 16:35 - Rule Bootstrap

- Scanned `D:\Lush-Temp-Mail` and confirmed repo currently contains only static UI files with no backend/toolchain.
- Created root `AGENTS.md` with current repo rules and regression checklist.
- Created project memory docs: `PROJECT_CONTEXT.md`, `DECISIONS.md`, `WORKLOG.md`, `CHANGELOG.md`.
- Recorded target domain `lush.congmail.top` and the catch-all requirement for arbitrary `@congmail.top` addresses.

## 2026-03-20 17:20 - Backend + VPS runtime

- Added FastAPI backend under `backend/` with admin session auth, SQLite persistence, IMAP sync loop, alias auto-discovery, OTP/link extraction, and API endpoints for alias/message management.
- Replaced static mock frontend data with real API-driven admin UI in root `index.html`, `app.js`, `style.css`.
- Added repo hygiene and toolchain files: `.gitignore`, `requirements.txt`, `Dockerfile`, `backend/AGENTS.md`, `deploy/AGENTS.md`.
- Added VPS deploy assets under `deploy/`: `.env.example`, `docker-compose.vps.yml`, helper scripts, Caddy snippet, README.
- Verified local syntax/tests: `python -m py_compile`, `node --check app.js`, `pytest backend/tests/test_parser.py` pass.
- Created `.venv` locally and installed runtime/test dependencies for verification.
- Uploaded app to VPS at `/opt/lush-temp-mail/app`, created runtime `.env`, installed `lushtempmail` helper, and started container on `127.0.0.1:8012`.
- Enabled live catch-all on mail stack by updating `postfix-virtual.cf` to route `@congmail.top` into `contact@congmail.top`, preserving existing direct addresses/aliases.
- Updated shared Caddy config on VPS to add internal route for `lush.congmail.top`.
- Verified live technical flow with a real probe mail: unknown alias `probed1ef7ec7@congmail.top` was auto-created from inbound mail, message stored, OTP `482911` and verify link extracted correctly.
- Remaining external step: add DNS record for `lush.congmail.top -> 82.197.71.6` so Caddy can obtain public TLS cert and serve the app publicly.

## 2026-03-20 17:32 - Public proxy fix

- Diagnosed public `502` after DNS cutover: shared Caddy for `spoticheck` runs inside Docker, so upstream `127.0.0.1:8012` pointed to the Caddy container itself instead of the temp-mail app on the host.
- Updated deploy config to use `host.docker.internal:8012` and added `extra_hosts: host.docker.internal:host-gateway` for the Caddy service.
- Synced the same fix into `deploy/Caddyfile.snippet` and `deploy/README.md` of `Lush-Temp-Mail` to avoid future redeploy regressions.

## 2026-03-20 17:36 - Shared proxy network fix

- Confirmed `host.docker.internal` resolved from Caddy but still failed because temp-mail app was published only on host loopback `127.0.0.1:8012`.
- Switched deploy strategy to the cleaner cross-compose approach: app now joins external Docker network `shared_proxy` with alias `lushtempmail-app`.
- Updated Caddy upstream target to `lushtempmail-app:8010`, removing the need for a host-published app port.

## 2026-03-20 17:46 - Admin credential helper

- Added `deploy/scripts/set_admin_credentials.sh` to update `ADMIN_USERNAME` and `ADMIN_PASSWORD` inside `deploy/.env` then redeploy the app automatically.
- Extended `lushtempmail` helper with `set-admin` subcommand and installed the updated helper on VPS.
- Verified on VPS: `bash -n`, `lushtempmail --help`, `lushtempmail set-admin --help`, and a no-op credential update using the current admin values all succeeded.
- Prepared user-facing cheat-sheet update so admin login and the new command are easy to find.

## 2026-03-20 16:55 - IMAP live sync recovery

- Reproduced the live issue where mail to `hoang123@congmail.top` reached the mail server but did not appear in the temp-mail dashboard.
- Confirmed the temp-mail container was using a stale IMAP path and that the host/public route for `mail.congmail.top` was not a reliable way to reach the mailserver from this container stack.
- Updated deploy defaults/docs to keep `IMAP_HOST=mail.congmail.top` and changed `deploy/docker-compose.vps.yml` so `lushtempmail-app` joins external network `mailstack_default` in addition to `shared_proxy`.
- Synced the deploy files to VPS, redeployed the app, and verified on the live UI that alias `hoang123@congmail.top` and message `opt` are now visible.

## 2026-03-20 17:03 - Auto refresh and relative time ticker

- Added frontend auto-refresh while the admin tab is visible, with a silent refresh path that preserves the currently opened message instead of resetting the detail pane.
- Added a separate relative-time ticker so labels like `Vá»«a xong` and `14 phÃºt trÆ°á»›c` update on screen without requiring a manual refresh.
- Lowered the recommended backend IMAP sync interval from 20s to 10s in deploy defaults, then applied the same setting on the live VPS runtime.
- Synced the updated `app.js` and deploy docs to VPS, redeployed `lushtempmail-app`, and prepared the live app for a hard-reload test in the browser.

## 2026-03-20 17:18 - New mail emphasis and flicker removal

- Reworked the temp-mail frontend refresh flow so silent auto-refresh now performs a real `/api/sync` cycle every 8 seconds while the tab is visible.
- Added recent-message tracking on the client, with a visible `Email má»›i` badge and stronger row highlight for newly arrived mail in `Mail feed`.
- Replaced the old list re-render used by the relative-time ticker with DOM-only label updates, and stopped re-fetching/re-rendering the open message detail during silent refresh to remove the flicker effect.
- Synced the new `app.js` and `style.css` to VPS and redeployed `lushtempmail-app`.

## 2026-03-20 17:28 - Tone down new-mail styling

- Removed the bright row highlight and pulse animation from new-mail styling in the message list.
- Kept only the `Email má»›i` badge so the inbox returns to the previous neutral look.
- Synced the updated `style.css` to VPS and redeployed `lushtempmail-app`.

## 2026-03-20 17:35 - Publish repo to GitHub

- Prepared the local folder `D:\Lush-Temp-Mail` to become the source git repository for `Lush-Temp-Mail`.
- Verified the target GitHub remote is empty and re-checked `.gitignore` so runtime-only files like `deploy/.env`, `deploy/LOCAL_PASSWORDS.md`, `.venv/`, and `data/` stay out of version control.
- Proceeded to initialize git locally, commit the current application/deploy/docs state, and push it to GitHub.

## 2026-03-20 18:22 - Clone repo and run local app

- Cloned the `Lush-Temp-Mail` repository into `C:\Users\PC\Lush-Temp-Mail`.
- Read project rules/context from `AGENTS.md`, `docs/PROJECT_CONTEXT.md`, `docs/DECISIONS.md`, and `docs/WORKLOG.md` before local runtime setup.
- Created local virtual environment at `.venv` and installed dependencies from `requirements.txt`.
- Started the FastAPI app locally with `uvicorn backend.app.main:app --host 127.0.0.1 --port 8010`.
- Verified local health endpoint at `http://127.0.0.1:8010/api/health` returned status `ok`.
- Opened the local app URL in the default browser for immediate access.

## 2026-03-20 18:48 - Simplify local inbox layout for review

- Removed the orange hero cover and pulled the working layout directly under the sticky topbar.
- Removed alias management UI from the local dashboard sidebar and client-side logic, keeping the local review flow focused on inbox reading only.
- Added fixed footer pagination to the mail list area and implemented client-side page switching for the fetched message list.
- Kept the email list in its own scrollable pane so the topbar, filters, footer pagination, and detail pane stay stable while browsing mail.
- Verified frontend syntax with `node --check app.js` and reloaded the local app to confirm the simplified layout renders successfully.

## 2026-03-20 18:57 - Trim topbar and add warm favicon

- Removed the temporary `Mail Console` info card from the sidebar to keep only the inbox filter actions.
- Removed the topbar sync button and the admin avatar/name cluster so the header stays minimal around the logo only.
- Added a dedicated `favicon.svg` with a warm background and red mail icon, then linked it in the page head.
- Re-ran frontend syntax check and reloaded the local app to confirm the simplified chrome renders without JS errors.

## 2026-03-20 19:00 - Redesign favicon with lucide-like mail mark

- Reworked `favicon.svg` into a cleaner mail icon with thicker strokes and a simpler warm tile so it remains legible at tiny browser-tab sizes.
- Kept the visual language aligned with the app palette while reducing decorative details that made the previous favicon look noisy when scaled down.
- Reloaded the local app after the icon update to make the new tab asset available for preview.

## 2026-03-20 19:04 - Switch favicon to app logo mark

- Updated the page head so the browser tab now uses `logo.svg` directly as the favicon instead of the temporary custom `favicon.svg`.
- Aligned the tab icon with the exact logo mark already shown in the app header for a more consistent brand feel.

## 2026-03-20 19:14 - Deploy latest UI polish to VPS

- Connected to VPS `82.197.71.6` as `root` and confirmed the live app repo is at `/opt/lush-temp-mail/app`.
- Uploaded the current local UI files (`index.html`, `app.js`, `style.css`) plus updated project logs to the live repo copy on the server.
- Rebuilt and restarted the live Docker stack from `/opt/lush-temp-mail/app/deploy` with `docker compose --env-file .env -f docker-compose.vps.yml up -d --build`.
- Verified container `lushtempmail-app` came back healthy and that `/api/health` returned `status: ok` from inside the container.
- Verified the public app at `https://lush.congmail.top` reflects the new layout after login, including the simplified topbar/sidebar and working inbox pagination.

## 2026-03-20 19:35 - Inbox interaction polish and faster sync

- Updated backend message search so the main search now matches alias/recipient address in addition to sender, subject, and snippet.
- Added backend message deletion endpoint and frontend hover delete button, plus automatic suppression of messages older than 7 days during sync cleanup.
- Reworked the inbox row layout to show alias first, sender second, subject third, and switched avatar colors to deterministic random palettes per message seed.
- Reduced frontend auto-sync polling to 3 seconds while the tab is visible and changed live VPS runtime `MAIL_SYNC_INTERVAL_S` to `4` for faster IMAP pickup.
- Synced the updated frontend/backend files to VPS, rebuilt `lushtempmail-app`, and verified on the public app that alias search and the new row layout are live.

## 2026-03-20 20:17 - Important inbox group, 60-day retention, and composer polish

- Added `Quan trá»ng` filter end-to-end: SQLite auto-migration for `messages.important`, API toggle endpoint, hover star action in the inbox row, and star persistence in the live UI.
- Changed inbox row actions so the delete control now uses the same icon-only visual language as the mail tab icon, while OTP rows keep the star visible and the alias-first ordering remains intact.
- Added reply/forward composer UI inside the email detail pane with `To`, `CC`, `Subject`, and `Message` fields styled to match the current Tailwind-based shell.
- Changed alias lifetime defaults to `60 ngÃ y` (`DEFAULT_ALIAS_HOURS=1440`) and message cleanup to `60 ngÃ y` (`MESSAGE_RETENTION_DAYS=60`) for both local code and live VPS runtime.
- Updated root `AGENTS.md` build/test commands to be repo-relative instead of the stale `D:` path from the older local workspace.
- Verified locally with `node --check .\\app.js` and Python compile checks, then verified live at `https://lush.congmail.top` after login that `Quan trá»ng`, star toggle, icon-only delete, and the composer panel are present and working.

## 2026-03-20 20:36 - Detail pane layout polish and recent-badge stability

- Reworked the desktop reading pane to use the remaining right-side width instead of the old fixed 420px column, with a wider centered reader shell and calmer card spacing.
- Removed the awkward `Email actions` card from the top of the mail content and moved `Tráº£ lá»i` / `Chuyá»ƒn tiáº¿p` into a dedicated action bar at the bottom of the detail flow.
- Adjusted the compose panel so reply/forward drafts now open inline above the bottom action bar, keeping `CC` and the Tailwind visual language intact.
- Changed recent-message tracking from per-filter comparison to session-wide seen-message tracking so switching between `Táº¥t cáº£ email` and `CÃ³ OTP` no longer marks old rows as `Email má»›i` again.
- Added render suppression for unchanged inbox lists, which keeps the same DOM rows across auto-refresh cycles and removes the hover flicker caused by unnecessary re-renders.
- Verified locally with `node --check .\\app.js`, then redeployed the frontend to VPS and confirmed on the live inbox that the detail pane is wider, the action bar sits at the bottom, filter switching keeps `Email má»›i` stable, and the first row node stays unchanged across auto-refresh when data does not change.

## 2026-03-20 20:40 - Push detail scroll to viewport edge and restore message-list width

- Removed the centered/max-width shell around the live app content so the desktop workspace now spans the full viewport width.
- Restored the message-list column to flexible width and changed the detail pane to a fixed responsive width anchored on the far right of the viewport.
- Kept the detail pane scroll on `#emailDetail`, which now sits flush with the page edge so the scrollbar is no longer stealing space from the email list side.
- Redeployed the updated `index.html` to VPS and verified on the live app that the detail pane reaches the viewport edge (`detailRightGap = 0`) while the email list regains its wider layout.

## 2026-03-20 20:44 - Revert desktop shell to centered layout from reference image

- Reverted the previous viewport-edge layout change after it diverged from the user's reference screenshot.
- Restored the centered desktop shell with `max-width: 1600px`, the inbox list back to the narrower fixed-width middle column, and the detail pane filling the remaining width inside that centered shell.
- Redeployed the reverted `index.html` to VPS and verified live that the shell is back to `1600px` wide with centered gutters, `mainWidth = 560`, and `detailWidth = 752`, matching the intended proportions more closely.

## 2026-03-20 20:48 - Match saved legacy layout file exactly

- Opened the user's saved reference file at `C:\Users\PC\Downloads\html lang=viscript src=chrome-exten.html` and compared the actual classes instead of estimating from screenshots.
- Confirmed the legacy proportions are `main = flex-1` and `#emailDetail = w-[420px]`, with the centered `max-w-[1600px]` shell preserved.
- Updated `index.html` to match that layout model exactly, then redeployed the app to VPS.
- Verified live after login that the shell is `1600px`, the inbox list is `892px`, and the detail pane is back to a fixed `420px`, which matches the saved legacy file structure.

## 2026-03-20 20:53 - Extend only detail viewport to page edge

- Kept the saved legacy shell proportions intact (`main = flex-1`, detail slot = `420px`) and limited the new change to the detail panel only.
- Wrapped the detail content in a dedicated fixed viewport layer so the visual panel extends from the old detail left edge all the way to the right edge of the browser.
- Preserved the inner content width at `420px` to avoid changing the reading layout itself, while moving the actual scrollbar to the far-right viewport edge.
- Verified locally and on the live site that `mainWidth` stays `892`, the original detail slot stays `420`, the rendered detail viewport expands to `580` on a `1920px` screen, and `panelRightGap = 0`.

## 2026-03-20 21:01 - Remove `Mail body` label from detail pane

- Removed the extra English heading `Mail body` from the email content section in the detail pane.
- Kept the Vietnamese section kicker `Ná»™i dung email` and left the rest of the detail layout unchanged.
- Rebuilt and redeployed the live app so the label disappears immediately after refresh.

## 2026-03-20 21:11 - Pin detail reply actions to footer and jump into composer

- Reworked the detail pane into a two-part shell: a scrollable content region and a fixed footer action bar for `Tráº£ lá»i` / `Chuyá»ƒn tiáº¿p`.
- Moved the active composer to the top of the detail flow so reply/forward mode becomes the primary context instead of appearing below the original email body.
- Added automatic scroll-to-top plus input focus when opening the composer, so clicking `Tráº£ lá»i` from the footer immediately lands the user in the reply form.
- Verified on the live app with a long `Undeliverable` email that the footer stays fixed while only the detail content scrolls, and that reply mode resets `scrollTop` to `0` with the composer visible near the top of the panel.

## 2026-03-20 21:23 - Enable real SMTP send for reply/forward composer

- Confirmed on the VPS that SMTP auth succeeds against `mail.congmail.top` with both `STARTTLS 587` and `SSL 465`, reusing the central mailbox credential already present for IMAP.
- Added backend SMTP config defaults/fallbacks plus a new `backend/app/mailer.py` service to send composed messages with `To`, `CC`, `Subject`, `Body`, and reply threading headers when available.
- Added `POST /api/messages/{message_id}/send` and connected the frontend composer send button to that API, including loading state, success toast, and composer close-on-success.
- Fixed a real delivery issue by adding the missing `Date` header after the first smoke test was rejected by the mail content filter as `BAD HEADER`.
- Verified end-to-end on the live app: forwarded a real email to alias `codexsend1774016575967@congmail.top`, saw `ÄÃ£ gá»­i chuyá»ƒn tiáº¿p`, and confirmed the forwarded message appeared back in the inbox on the first refresh cycle.

## 2026-03-20 21:40 - Flatten composer visuals and split send-button styles

- Kept the composer logic and SMTP send flow intact, but separated the visual treatment of the send buttons by mode.
- Changed `Gá»­i chuyá»ƒn tiáº¿p` to a white button with a light neutral border, while keeping `Gá»­i tráº£ lá»i` on the existing orange primary style.
- Removed the orange-tinted composer surface and switched the form fields to a flatter white treatment with a soft neutral border and no orange glow on focus.
- Redeployed only the updated frontend files to VPS and verified live that forward is white, reply remains orange, the composer background is flat white, and the textarea/input outline no longer looks blurry.

## 2026-03-20 21:48 - Add keyboard Delete shortcut for selected email

- Added a global `keydown` handler in the frontend so pressing `Delete` removes the currently selected email row through the same delete flow used by the hover trash icon.
- Guarded the shortcut so it does nothing while focus is inside `input`, `textarea`, `select`, or editable content, avoiding accidental deletes during reply/forward editing.
- Redeployed the updated `app.js` to VPS and verified live that selecting a row then pressing `Delete` opens the existing confirm dialog `XÃ³a email nÃ y khá»i dashboard?`.

## 2026-03-20 21:58 - Add page-scoped multi-select like desktop file lists

- Extended inbox row selection to support `Ctrl/Cmd + click` toggle, `Shift + click` range selection, and `Ctrl/Cmd + A` to select all rows on the current paginated inbox page.
- Unified row-trash delete and keyboard `Delete` into the same batch delete flow, so multiple selected emails now confirm once with a count-aware message before removal.
- Added click-outside clearing for multi-select mode: clicking anywhere outside inbox rows now drops the selection and resets the detail pane instead of leaving stale batch state behind.
- Verified live that `Ctrl + click` selected 2 rows, `Shift + click` expanded the range to 3 rows, `Ctrl + A` selected all 12 visible rows on the page, `Delete` opened the batch confirm dialog, and clicking outside reduced the selection back to `0`.

## 2026-03-20 22:04 - Prevent text highlight during Shift range select

- Added `user-select: none` to inbox rows so mail list text no longer gets highlighted during desktop-style multi-select gestures.
- Added a `mousedown` guard for row interactions when `Shift`, `Ctrl`, or `Cmd` is held, preventing the browser's native text-selection behavior before the range-toggle logic runs.
- Redeployed the updated frontend and verified live that `Shift + click` still selects 4 rows correctly while `window.getSelection()` stays empty.

## 2026-03-20 22:10 - Add email translation endpoint

- Added `POST /api/messages/{message_id}/translate` in `backend/app/main.py` for auto-detect -> `vi` translation of subject and body.
- Added `backend/app/translator.py` to call the Google Translate web endpoint with `httpx` and shape a frontend-friendly payload.
- Chose not to add a new dependency or schema/config change; translation now runs as a lightweight on-demand backend helper.
- Verified the new backend files with `py_compile` and a local smoke test that mocked the translation response shape.

## 2026-03-20 22:18 - Add in-panel Google-style translate action for email detail

- Added an icon-only translate action at the far right of the detail meta row so subject/body can be translated in place without leaving the reader panel.
- Wired the detail pane to call the new translation endpoint on demand, cache the translated subject/body per message, and toggle between translated Vietnamese content and the original email.
- Styled the translate control with a Google-inspired multicolor ring, loading spinner state, and a small translation status chip under the subject for better readability.
- Verified local translation logic with `py_compile`, `node --check`, and a live backend smoke test that returned `source_language = en`, `target_language = vi`, plus translated subject/body.

## 2026-03-20 22:27 - Sync current project state to GitHub

- Reviewed the git worktree, confirmed the active branch is `main`, and kept runtime-only files like `run.err` / `run.log` out of the commit.
- Prepared a single source-control sync for the current live/local state so GitHub matches the deployed inbox, composer, multi-select, and translation features.
- Proceeded to stage, commit, and push the tracked application/backend/docs files to `origin/main`.

## 2026-03-21 12:43 - Pull latest changes from origin/main

- Re-read root rules and project memory before running the source-control sync task, per project process.
- Confirmed `D:\Lush-Temp-Mail` was on branch `main` with a clean worktree tracking `origin/main`.
- Pulled remote updates with `git pull --ff-only origin main`, moving the repo from `2cb069f` to `ef65da9` without creating a merge commit.
- Synced upstream changes across frontend, backend, deploy docs, and project memory files, then re-checked that the worktree stayed clean after the pull.

## 2026-03-21 14:13 - Add user-facing alias inbox page

- Added a separate user-facing route at `user.html` with a premium lookup hero, alias-driven inbox list, right-side reading pane, mobile detail drawer, and styling aligned to the current admin app's fonts, Tailwind palette, and Lucide icon language.
- Added `user.js` to handle exact-alias lookup, fast summary-list loading, detail fetching, translation toggle, auto-refresh for the active alias, URL query sync, and empty/loading/toast states without reusing admin-only logic.
- Extended the backend with `/api/public/inbox`, `/api/public/messages/{message_id}`, and `/api/public/messages/{message_id}/translate`, plus exact-alias normalization helpers and SQLite queries optimized for public summary/detail reads.
- Added SQLite indexes for `recipient_address` / `received_at` and `alias_id` / `received_at`, and removed the silent 120-message truncation from the new public inbox query so the user flow can return the full alias history.
- Verified locally with `py_compile`, `node --check app.js`, `node --check user.js`, and a Playwright smoke pass on `http://127.0.0.1:8010/user.html` for desktop + mobile empty-state behavior.

## 2026-03-21 14:33 - Simplify user inbox UI with Uncodixfy rules

- Read `C:\Users\Admin\.codex\skills\uncodixfy\Uncodixfy.md` and rebuilt the user-facing UI to remove floating premium-dashboard patterns, oversized radii, decorative sections, badges, refresh controls, and translate actions.
- Reworked `user.html` into a simpler structure: dark top hero with one lookup form, then a plain white results shell that only shows after lookup, with message list on the left and detail pane on the right.
- Rewrote `user.css` around flat panels, normal borders, restrained radii, and a cleaner white content area while keeping the admin app's font stack and orange accent color.
- Simplified `user.js` so the user flow is now just alias lookup -> message list -> open detail, with mobile detail drawer retained and all extra UI behavior removed.
- Re-verified locally with `node --check user.js`, `py_compile`, and a Playwright smoke pass on desktop + mobile for the simplified empty-state layout.

## 2026-03-21 14:46 - Split login into admin and user flows

- Re-read project memory, root/subfolder rules, and reapplied `Uncodixfy.md` so the user route stayed visually aligned with the existing admin app instead of drifting into a new UI pattern.
- Extended backend auth/config/session handling to support both `admin` and `user`, including shared session cookies, role-aware `/api/auth/session`, shared logout, and protection of `/api/public/*` behind `require_user`.
- Updated the root login flow so username `admin` stays on the admin dashboard while username `user` redirects to `user.html`; the login form copy is now generic instead of admin-only.
- Replaced the top-right `Admin` button on `user.html` with `ÄÄƒng xuáº¥t`, and updated `user.js` to require a `user` session, include cookies on inbox requests, redirect unauthorized access back to `/`, and clear stale detail cache between alias lookups.
- Updated deploy docs/helpers for the new credential contract by adding `USER_USERNAME` / `USER_PASSWORD` to `.env.example`, documenting the new flow in `deploy/README.md`, and extending the helper to support both `lushtempmail set-admin` and `lushtempmail set-user`.
- Verified with `py_compile`, `node --check .\\app.js`, `node --check .\\user.js`, a FastAPI `TestClient` auth smoke covering both roles, and a Playwright browser smoke on `http://127.0.0.1:8011/` confirming `user` redirects into `user.html` and shows the `ÄÄƒng xuáº¥t` button while `admin` remains on `/`.
## 2026-03-21 18:34 - Align admin checkbox to avatar lane

- Re-read repo rules, project memory, and the existing admin checkbox decision before touching the inbox row layout.
- Traced the live/local mismatch to the checkbox being vertically centered against the full row height, which only looked acceptable on short local sample rows but drifted downward on the taller real inbox rows rendered on VPS.
- Updated the admin inbox markup/CSS so the checkbox no longer carries the extra `mt-1` class and is pinned to a fixed top offset aligned to the avatar lane instead of `top: 50%`.
- Re-verified with `node --check app.js`, local `api/health`, and a Playwright DOM probe using a multi-line synthetic inbox row to confirm the checkbox center now matches the avatar center while the header and list width stay unchanged.
## 2026-03-21 18:43 - Fix alias lookup for 2-char local parts and decode MIME headers

- Re-read project memory and traced the two regressions separately instead of assuming they came from the checkbox/layout change.
- Confirmed `/api/public/inbox?alias=12@congmail.top` was returning `400` because the local-part regex only allowed length `1` or `>=3`, accidentally rejecting 2-character aliases that already existed in the inbox.
- Updated backend parsing so MIME-encoded `Subject` and `From` display names are decoded both at IMAP import time and again when rows are read back from SQLite, which fixes existing stored rows without needing a manual resync.
- Re-verified with `py_compile`, a FastAPI `TestClient` login + public inbox smoke test returning `200` for `12@congmail.top`, and a direct SQLite read test showing decoded RFC2047 `from_name`/`subject` values.
## 2026-03-21 20:31 - Audit Vietnamese text encoding and alias character support

- Re-ran a source scan across root frontend files and `backend/app/*.py` using escaped-byte detection to catch mojibake patterns such as `\xc3`, `\xc4`, and `\xc2`; after fixing the remaining bad admin multi-select label in `app.js`, no suspicious source lines remained.
- Verified locally that alias lookup now accepts 2-character local parts plus `_` and `-` forms such as `ab@congmail.top`, `a_b@congmail.top`, and `a-b@congmail.top` through both direct normalization and authenticated `/api/public/inbox` requests.
- Confirmed the MIME decode path still works for RFC2047 Vietnamese subjects/display names during this audit, while noting the current live VPS was still on the older regex until the next deploy.
## 2026-03-21 20:36 - Deploy encoding and alias-validation fixes to VPS

- Synced the corrected backend files into the proper VPS path `backend/app/` after catching an initial bad upload target that had left production on the old regex.
- Rebuilt the live container and verified public alias lookup on production for `12@congmail.top`, `ab@congmail.top`, `a_b@congmail.top`, and `a-b@congmail.top`, all returning `200` after deploy.
- Verified the live admin API with the current production admin credentials and confirmed `raw_count = 0` for message rows whose `subject` or `from_name` would previously have shown undecoded MIME headers.
## 2026-03-21 20:44 - Allow trailing underscore and hyphen in alias lookup

- Followed up on a new real-world alias example from production where `1_@congmail.top` existed in the admin inbox but the user lookup flow still rejected it.
- Confirmed the regex had only been relaxed for 2-character aliases and internal `_` / `-`, while still forcing the final character to be alphanumeric.
- Updated alias validation so local-parts may end in `_` or `-` but still cannot end in `.`; verified with direct normalization plus authenticated `/api/public/inbox` tests for `1_@congmail.top`, `1-@congmail.top`, and `1.@congmail.top`.
## 2026-03-21 20:49 - Expand alias lookup to RFC-safe special characters

- Broadened the alias validation rule from the previous `_` / `-`-focused patch to a practical dot-atom pattern that accepts common email local-part special characters used on real sites.
- Verified local lookup acceptance for aliases containing `_`, `-`, `+`, `=`, `%`, and apostrophe, while still rejecting malformed dot cases such as leading `.`, trailing `.`, or consecutive `..`.
- Rechecked the authenticated user inbox route so these aliases return `200` through `/api/public/inbox` instead of being blocked by frontend-facing validation errors.
## 2026-03-21 21:02 - Switch mail sync toward IMAP IDLE with polling fallback

- Compared the current architecture against a direct mail-server hook and chose `IMAP IDLE` because it keeps catch-all delivery unchanged, avoids coupling mail acceptance to app uptime, and still provides near-realtime pickup from the central mailbox.
- Added backend runtime support for `MAIL_IDLE_ENABLED` / `MAIL_IDLE_TIMEOUT_S`, plus an `IMAP IDLE` wait loop with capability detection and automatic fallback to the existing polling path if the server drops or does not support `IDLE`.
- Changed the admin frontend refresh behavior so login still performs one force sync, but the steady-state auto refresh now polls only the app database every 2 seconds instead of forcing a full IMAP sync on each tick.
- Updated deploy docs/example env for the new runtime knobs and bumped the admin asset version so browsers fetch the new `app.js` immediately after deploy.

## 2026-03-21 21:40 - Add SSE inbox refresh and stale-only user sync

- Re-read project memory/rules, kept the new `IMAP IDLE` backend in place, and added a lightweight in-memory event broker so backend inbox mutations can notify browser tabs without introducing WebSocket complexity or changing the mail path.
- Extended the backend with `/api/events`, `/api/public/events`, and `/api/mail-sync/status`; `MailSyncService` now exposes heartbeat/status data, publishes alias/global events after imported mail, and admin delete flows publish inbox change events too.
- Updated `app.js` so admin tabs open an `EventSource` stream for near-immediate list refresh, while reducing timer-based refresh to a slower fallback instead of the primary mechanism.
- Updated `user.js` so manual lookup checks backend liveness first and only calls `/api/public/sync` when the mail watcher is stale; once an alias is open, the user page now listens to alias-scoped `SSE` updates and refreshes the inbox without requiring another click.
- Verified locally with `py_compile`, `node --check`, a direct async smoke on the new SSE generators, then deployed the changed files to VPS and re-verified `health`, asset versions, `/api/mail-sync/status`, `/api/events`, and `/api/public/events` on `https://lush.congmail.top`.

## 2026-03-21 21:56 - Fix IMAP IDLE tag handling and measure live pickup latency

- Investigated live production after the user reported slower mail appearance, and found a real backend issue in `IMAP IDLE`: the code was sending the raw `imaplib` tag through Python string formatting, which turned a bytes tag into a literal like `b'CIJC4'` and caused `imaplib.IMAP4.abort` when `IDLE` completed.
- Patched `backend/app/imap_sync.py` to handle `imaplib` tags as bytes correctly for both entering `IDLE` and waiting for the tagged completion response, then rebuilt and redeployed the app container on VPS.
- Re-checked live watcher status after deploy: `mode=idle`, `idle_active=true`, `is_stale=false`, with no fresh `IMAP4.abort` trace in the recent logs.
- Ran a production probe by sending a fresh SMTP message from the VPS mail credentials into a brand-new alias and polling the live user inbox API; the message became visible through `https://lush.congmail.top/api/public/inbox` in about `1.44s`, showing the current `mailbox -> app -> DB -> API` path is fast after the fix.

## 2026-03-21 22:01 - Measure real timestamps against Gmail and production logs

- Pulled recent real Gmail deliveries from the live mailserver logs and matched them by `Message-ID` with rows in the production SQLite database.
- Confirmed the mailserver side is very fast once Gmail hands the message to the VPS: recent Gmail samples from `hoangleea99@gmail.com` were accepted, filtered, and stored into Dovecot `INBOX` in roughly `100-200ms` on the mail stack.
- Found an important metric caveat: the app's `messages.received_at` is not a strict mailbox-ingest timestamp, so it can differ by a couple of seconds from Dovecot store time because it reflects parsed message time from the email itself.
- Measured a fresh end-to-end production probe on a new alias via the public inbox API and saw it become visible in about `1.44s`, which indicates the current post-mailbox path is fast and that any remaining long waits are more likely upstream at the sender hop than inside the app/UI path.

## 2026-03-21 22:10 - Persist mailbox and ingest timestamps for future latency debugging

- Added two explicit message timing fields to the data model: `mailbox_received_at` from IMAP `INTERNALDATE`, and `ingested_at` for the moment the app writes the message into SQLite.
- Updated the SQLite bootstrap/migration path in `backend/app/db.py` to add both columns for existing deployments and backfill old rows with best-effort values so production can migrate in-place on restart.
- Changed the IMAP fetch path in `backend/app/imap_sync.py` to request `INTERNALDATE`, parse it, and store it alongside the existing header-derived `received_at`.
- Added a lightweight admin-only debug endpoint `/api/debug/message-timings` so recent timing rows can be inspected over HTTPS without SSHing into the VPS database manually.
- Verified locally with `py_compile` and `TestClient`, then deployed to VPS and confirmed a fresh production probe mail recorded distinct timing fields, including `ingested_at` one second after `mailbox_received_at`.

## 2026-03-21 22:17 - Fix public inbox regression after timing-column rollout

- Investigated the user-facing crash `Failed to execute 'text' on 'Response': body stream already read` and traced it to two stacked issues introduced by the timing-column rollout.
- Fixed the real backend regression first: `list_public_messages()` still selected the old summary column set, while `row_to_message_summary()` had already started reading `mailbox_received_at` / `ingested_at`, which caused a production `IndexError` and a `500` on `/api/public/inbox`.
- Hardened both frontend `api()` helpers (`user.js`, `app.js`) to read error bodies exactly once, so future backend failures surface the real response detail instead of the misleading browser error about an already-read body stream.
- Bumped the static asset versions in `user.html` and `index.html`, redeployed the app, and verified live that `GET /api/public/inbox?alias=1_@congmail.top` now returns `200` again with the updated JS bundle references.

## 2026-03-21 22:22 - Verify live user inbox error is cleared

- Re-read project memory, then re-checked production after the user reported the earlier `body stream already read` crash screenshot.
- Verified directly on live API that `POST /api/auth/login` for role `user` still succeeds and `GET /api/public/inbox?alias=1_@congmail.top` now returns `200` with inbox data instead of `500`.
- Opened the real browser flow on `https://lush.congmail.top/user.html`, logged in as `user`, searched `1_@congmail.top`, and confirmed the message list plus reading pane render normally with no remaining runtime error on the lookup path.

## 2026-03-21 22:29 - Measure latest production mail timing with new timestamp fields

- Re-read project memory, then queried the live admin debug endpoint `/api/debug/message-timings?limit=8` to identify the newest real Gmail delivery currently in production.
- Matched the latest row (`id=33598`, alias `1-@congmail.top`, `Message-ID=<CAJSR+axPzdoN2Hv7zutQLZXJPHD9MqKLwEHDwp+e6S_BeOw=ZA@mail.gmail.com>`) against `docker logs` from `mailstack-mailserver-1` to get precise postfix/amavis/dovecot receive/store timestamps.
- Confirmed the concrete timing split for this real message: mailserver accepted/processed it around `2026-03-21 15:18:06Z`, Dovecot stored it at `2026-03-21 15:18:06.411Z`, and the app inserted it into SQLite at `2026-03-21 15:18:06.964953Z`, so the `mailbox -> app DB` hop took roughly `0.55s`.
- Recorded that the currently measurable slow/fast boundary is now clear: the internal mailserver + app ingestion path is fast for this sample, while any larger wait still has to come from the sender-side handoff before the VPS receives the message.

## 2026-03-22 09:07 - Sync deployed worktree to GitHub

- Re-read project memory and checked both local repo state plus the live VPS app path before pushing, to avoid assuming the deployed server folder was itself a git checkout.
- Confirmed `/opt/lush-temp-mail/app` on VPS is not a git repository, so the correct push source is the local repo worktree that already contains the deployed code and the latest project memory updates.
- Re-ran backend/frontend syntax checks, excluded scratch files like `.tmp_*` from version control, and prepared a single git commit that captures the current deployed backend, frontend, deploy helper, and docs state for GitHub.

## 2026-03-23 10:02 - Stabilize HTML email rendering and attachment display

- Re-read project memory/rules, then traced the broken email detail view to two separate problems: CSS-heavy transactional emails were contaminating the plain-text fallback, and the UI was still forcing most messages through a text-only renderer even when a valid HTML body existed.
- Hardened backend parsing in `backend/app/parser.py` and `backend/app/imap_sync.py` so `<head>/<style>/<script>` noise is stripped from HTML-to-text conversion, CSS-looking plain-text fallbacks are replaced with readable HTML-derived text, and attachment metadata is extracted during IMAP import.
- Extended SQLite persistence in `backend/app/db.py` to store `attachments_json`, keeping attachment metadata available to the detail APIs without changing the existing message identity or alias contracts.
- Reworked both readers in `app.js` and `user.js` to render HTML mail bodies inside sandboxed iframes, auto-size those frames, keep a collapsible text fallback, and show a dedicated attachment list instead of letting MIME-heavy content leak into the main body copy.
- Added matching reader styles in `style.css` and `user.css`, then verified with `node --check`, `py_compile`, `pytest backend/tests/test_parser.py`, and a live browser injection on the local admin route showing CTA buttons, OTP, links, and attachment metadata rendering without layout bleed.

## 2026-03-23 10:09 - Flatten email detail reader surface

- Re-read project memory/rules and the `uncodixfy` skill again after the user clarified the visual direction: the HTML email should feel like part of the existing reader panel, not like a separate card nested inside more cards.
- Removed the visible `text fallback` affordance from both readers in `app.js` and `user.js`, keeping HTML rendering as the primary display path whenever an email already has a valid `html_body`.
- Simplified reader styling in `style.css` and `user.css` so the iframe sits directly on the white panel background, and attachment rows now use simple list dividers instead of boxed mini-cards.
- Verified with `node --check` and a fresh browser injection on `http://127.0.0.1:8010/` that the fallback UI is gone, the iframe still renders the sample CTA mail correctly, and attachments now inherit the flatter app-native look.

## 2026-03-23 10:20 - Fix user reader runtime regression after deploy

- Re-read project memory/rules, then investigated the live user screenshot showing the detail pane stuck on skeleton with toast `escapeAttribute is not defined`.
- Traced the regression to `user.js`: the new iframe-based HTML reader called `escapeAttribute(frameDocument)` but the helper had only been added in `app.js`, not in the user bundle.
- Added `escapeAttribute()` to `user.js`, bumped the `user.js` asset version in `user.html` to `20260323-user-reader-fix-9`, and redeployed the updated files to `/opt/lush-temp-mail/app` on VPS.
- Re-verified live that `https://lush.congmail.top/api/health` still returns `ok` and that the served `user.js` bundle now contains both `function escapeAttribute` and the new cache-busted script reference.

## 2026-03-23 10:30 - Tighten OTP and action-link badges

- Re-read project memory/rules, then investigated the false-positive badge report where an OpenAI verification email surfaced a bogus OTP like `rgin` and too many `Mở link` actions from unrelated HTML/CSS URLs.
- Tightened `backend/app/parser.py` so OTP extraction now validates only plausible codes, reads HTML through cleaned text instead of raw markup for OTP context, and limits action links to confident verification/reset URLs extracted from real anchor `href`s or plain-text URLs.
- Updated `backend/app/db.py` so message detail responses recompute `extracted_otps` and `extracted_links` with the latest heuristics on read, which fixes existing stored messages without needing those emails to be re-imported.
- Added regression tests for lowercase false positives and noisy HTML asset links in `backend/tests/test_parser.py`, then redeployed the backend parser/db fixes to VPS and re-checked live health at `https://lush.congmail.top/api/health`.

## 2026-03-23 10:56 - Tighten UI and subagent operating rules

- Re-read project memory/rules, reviewed the current workspace/repo rule files, and ran Rule Bootstrap against the active repo structure (`requirements.txt`, `Dockerfile`, `backend/AGENTS.md`) before changing any rule documents.
- Created `D:\AGENTS.md` so the personalized working agreements now exist as a workspace-level rule file instead of living only in chat context.
- Added explicit UI rules at the workspace level that require the `uncodixfy` skill for every UI task and require UI changes to inspect and align with the existing design language before introducing any new structure.
- Updated `D:\Lush-Temp-Mail\AGENTS.md` with repo-specific UI discipline that rejects nested/floating card patterns and requires edits to stay visually consistent with the current admin/user shell.
- Tightened subagent guidance at both levels so delegation must be explicitly evaluated first, stays focused on exploration/read-only investigation by default, and only delegates implementation when the work is truly independent and allowed by the current tooling policy.

## 2026-03-23 11:21 - Preserve HTML layout during translation and add user translation flow

- Re-read project memory/rules, kept the UI pass aligned with `uncodixfy`, and traced the regression to the admin translator rendering only `translated_body` text instead of a translated HTML document, which destroyed the original mail layout and CTA structure.
- Reworked `backend/app/translator.py` so translation now supports `translated_html`, preserves HTML structure by translating text nodes instead of flattening the whole document, and skips translation entirely when the message is already Vietnamese.
- Enriched `backend/app/db.py` detail payloads with `language_hint` and `can_translate`, then updated `app.js` so admin keeps iframe-based HTML rendering while translated and automatically hides translation affordances for Vietnamese mail.
- Ported the same translation flow into `user.js` and `user.css`, including the translate toggle, translated HTML iframe rendering, same-language skip behavior, and cache-busted asset references in `index.html` / `user.html`.
- Verified with `node --check` for both frontend bundles, `py_compile` for backend files, and `.venv\Scripts\python.exe -m pytest -q backend/tests/test_parser.py backend/tests/test_translator.py` passing `10/10`.

## 2026-05-05 11:35 - Add admin user management tab

- User requested a new admin sidebar tab to manage the two current app accounts and future users directly from the mail app UI, with only username, password, and role fields.
- Added a SQLite `users` table seeded from existing `ADMIN_USERNAME/ADMIN_PASSWORD` and `USER_USERNAME/USER_PASSWORD` on first migration, then changed login to authenticate against that table.
- Added admin-only `/api/users` CRUD endpoints with safeguards for the current logged-in account and the last remaining admin.
- Added the `Người dùng` tab to the existing LushMail admin shell, plus a compact list row with edit/delete icon buttons and a simple create/edit modal matching the current light UI language.
- Verified with `python -m pytest -q`, backend `py_compile`, and `node --check app.js`.

## 2026-05-09 11:40 - Improve mobile user inbox reader

- User reported the mobile reader had nested/competing scroll areas: the email body could not scroll fully and the page scroll stopped before the end of the message.
- Added concise bootstrap memory files (`PROJECT_BRIEF`, `MEMORY_INDEX`, `DECISIONS_INDEX`, `UI_SYSTEM`) because this repo still only had the older long context docs.
- Reworked the user mobile flow so search results use normal page scroll, the desktop reading pane is hidden under `1024px`, and opening a message locks body scroll while the full-screen reader overlay handles all detail scrolling.
- Updated `user.js` to scroll mobile lookups to the result shell and re-measure email iframe heights after the mobile overlay opens, including image load callbacks.
- Verified with `node --check user.js`, `node --check app.js`, `pytest -q` passing `12/12`, and a Playwright/Chrome mobile smoke confirming `bodyOverflow=hidden`, desktop pane hidden, list overflow visible, and reader scroll working.
