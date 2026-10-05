# Changelog

### 2026-07-21 13:00 - rebrand_and_git_managed_deploy
- Added: DarkAmbient `DA` monogram, synchronized product identity, and a health-gated Git update script for the VPS.
- Changed: canonical maintenance now uses the independent public `temp.darkambient.co` repository with clean history and local/VPS `origin/main` checkouts.
- Affected files: `logo.svg`, `index.html`, `user.html`, `app.js`, `backend/app`, `backend/tests`, `deploy/darkambient`, `docs`.
- Impact/Risk: medium; active branding and source deployment workflow change, while mail routing, runtime data, DNS, and Google Workspace stay unchanged.

### 2026-07-21 12:00 - deploy_darkambient_temp_mail
- Added: isolated Docker Mailserver/Rspamd deployment for `temp.darkambient.co`, catch-all receive, standalone send, reply, forward, and production runbook.
- Changed: published subdomain DNS/TLS/SPF/DKIM/DMARC while preserving Google Workspace MX at the apex; added cache busting for the admin composer.
- Fixed: excluded runtime credentials/data from the app image and configured exact-subdomain Rspamd DKIM signing.
- Affected files: `backend/app/main.py`, `backend/app/smtp_send.py`, `backend/tests`, `index.html`, `app.js`, `.dockerignore`, `deploy/darkambient`, `docs`.
- Impact/Risk: high deployment impact, isolated to `temp.darkambient.co`; the provider PTR change remains an external deliverability follow-up.

### 2026-07-20 00:00 - expand_admin_mail_full_width
- Changed: admin mail app shell now uses the full desktop viewport width instead of leaving unused space beyond 1600px.
- Affected files: `index.html`.
- Impact/Risk: low; desktop layout capacity increases, mobile behavior unchanged.

### 2026-07-20 00:00 - fix_reader_splitter_drag_snap
- Fixed: admin reader splitter no longer jumps when pressing the resize icon; dragging now uses pointer delta from the current panel width.
- Affected files: `index.html`, `app.js`.
- Impact/Risk: low; desktop-only splitter interaction.

### 2026-07-20 00:00 - align_admin_reader_splitter
- Fixed: admin inbox reader now sits directly beside the message list; the shared panel edge acts as the resize hover handle without leaving an empty gutter.
- Affected files: `index.html`, `style.css`.
- Impact/Risk: low; desktop-only layout refinement for the admin mail reader.

### 2026-07-20 00:00 - add_resizable_admin_reader
- Added: desktop admin inbox reader can be resized by dragging the subtle hover handle between the message list and detail pane.
- Changed: reader width is persisted in `localStorage` and clamped so the message list keeps usable width.
- Affected files: `index.html`, `app.js`, `style.css`.
- Impact/Risk: low; desktop-only UI behavior, mobile reader remains unchanged.

### 2026-07-20 00:00 - add_auto_delete_excluded_aliases
- Added: admin `Tự động xoá` view for excluded aliases that should never enter the inbox.
- Added: backend `excluded_aliases` table and API routes to list, create, and delete excluded aliases.
- Changed: inbound message storage now skips recipients in the excluded list, and adding an alias hides older messages for the same address.
- Affected files: `backend/app/db.py`, `backend/app/main.py`, `index.html`, `app.js`, `style.css`, `backend/tests/test_excluded_aliases.py`.
- Impact/Risk: medium; changes inbound storage behavior for aliases explicitly added by admin.

### 2026-05-13 00:00 - add_admin_sent_mailbox
- Added: admin `Đã gửi` mailbox replacing the old sidebar OTP/link quick filters, with sent rows showing recipients, mode, timestamp, and attachment count.
- Added: persisted `sent_messages` and `sent_message_attachments` storage so reply/forward sends can be searched, opened, deleted, and downloaded from the sent folder.
- Changed: admin detail reader now renders a sent-mail detail view with From/To/CC/Message-ID metadata, copy actions, body, and downloadable attachments.
- Affected files: `backend/app/db.py`, `backend/app/main.py`, `index.html`, `app.js`, `style.css`, `backend/tests/test_sent_messages.py`.
- Impact/Risk: medium; adds SQLite tables and routes for sent mail while leaving inbound IMAP parsing unchanged.

### 2026-05-12 00:00 - attachment_download_and_forward_payloads
- Added: persisted inbound attachment payloads in `message_attachments`, with IMAP fallback fetch for older rows that only had attachment metadata.
- Fixed: admin and user readers now open attachment files from the attachment list, and forwarded emails include the original attachments for all `To`/`CC` recipients.
- Affected files: `backend/app/parser.py`, `backend/app/imap_sync.py`, `backend/app/db.py`, `backend/app/main.py`, `backend/app/mailer.py`, `app.js`, `user.js`, `style.css`, `user.css`.
- Impact/Risk: medium; adds a SQLite table for attachment BLOBs and an on-demand IMAP fallback when old messages are opened or forwarded.

### 2026-05-04 00:00 - add_vps_migration_runbook
- Added: `deploy/scripts/migrate_vps.sh` to install a fresh app checkout on a new VPS and copy runtime `.env` plus `deploy/data` from a source VPS.
- Added: `deploy/MIGRATION.md` with the operator runbook and post-migration checks.
- Changed: `deploy/README.md` now links the migration flow.
- Affected files: deploy/scripts/migrate_vps.sh, deploy/MIGRATION.md, deploy/README.md
- Impact/Risk: low; script is opt-in and does not write to the source VPS.

### 2026-03-21 18:15 - reenable_row_checkbox_without_widening_layout
- Changed: row checkbox is visible again in the admin message list, but it is now positioned as an overlay inside the row instead of taking up horizontal layout space.
- Fixed: restored the checkbox affordance without stretching the admin header or widening the message-list layout.
- Affected files: `style.css`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`, `docs/DECISIONS.md`.
- Impact/Risk: low; row-level selection affordance changed visually, while header/layout proportions remain the same.

### 2026-03-21 18:05 - deploy_admin_delete_all_and_encoding_fixes_to_vps
- Changed: uploaded the current admin UI files and backend delete-all support to the live VPS app directory and rebuilt the running container.
- Fixed: public `https://lush.congmail.top` now serves the admin delete-all UI with the encoding-proof placeholder/tooltip strings instead of the broken mojibake copy.
- Affected files: live `/opt/lush-temp-mail/app/index.html`, live `/opt/lush-temp-mail/app/app.js`, live `/opt/lush-temp-mail/app/style.css`, live `/opt/lush-temp-mail/app/backend/app/db.py`, live `/opt/lush-temp-mail/app/backend/app/main.py`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: medium; production admin behavior now includes the new delete-all route and current header text/layout.

### 2026-03-21 18:02 - make_admin_texts_encoding_proof
- Fixed: replaced the broken admin Vietnamese strings with encoding-proof HTML entities and JavaScript unicode escapes.
- Changed: the latest admin placeholder, delete-all tooltip, and delete-all confirm/toast copy no longer rely on source-file Unicode surviving terminal edits.
- Affected files: `index.html`, `app.js`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; text rendering fix only, with no behavior or layout change.

### 2026-03-21 17:54 - fix_mojibake_on_admin_delete_all_texts
- Fixed: repaired mojibake/encoding corruption on the admin search placeholder, delete-all tooltip, and delete-all confirm/toast copy.
- Changed: normalized the latest admin delete-all strings back to valid UTF-8 Vietnamese text.
- Affected files: `index.html`, `app.js`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; text-only correction with no logic or layout change.

### 2026-03-21 17:41 - restore_admin_header_keep_only_delete_all_icon
- Changed: admin header layout is back to the earlier compact shape with only the search field and one trailing icon action.
- Fixed: removed the added multi-button toolbar strip that stretched and broke the inbox header proportions.
- Affected files: `index.html`, `app.js`, `style.css`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`, `docs/DECISIONS.md`.
- Impact/Risk: low; local admin UI is visually restored while the delete-all confirmation flow is preserved.

### 2026-03-21 17:31 - admin_delete_toolbar_checkbox_and_scope_delete
- Added: admin backend endpoint `DELETE /api/messages` plus database helper to suppress all messages matching the current inbox scope across every page.
- Changed: admin inbox toolbar now uses `Chá»n trang`, `XÃ³a Ä‘Ã£ chá»n`, and `XÃ³a táº¥t cáº£` instead of the old manual refresh button.
- Fixed: checkbox-based multi-select is now visible in the message list, and `XÃ³a táº¥t cáº£` explicitly confirms before deleting the full current inbox/filter/search result set.
- Affected files: `backend/app/db.py`, `backend/app/main.py`, `index.html`, `app.js`, `style.css`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`, `docs/DECISIONS.md`.
- Impact/Risk: medium; destructive admin actions are clearer and broader in scope, so the confirm copy is now part of the safety contract.

### 2026-03-21 15:21 - redeploy_updated_user_html_to_vps
- Changed: the current local `user.html` content was uploaded to the live VPS app directory and included in a fresh app rebuild.
- Fixed: the public user route now serves the latest edited copy from `D:\Lush-Temp-Mail\user.html` instead of the older live HTML.
- Affected files: live `/opt/lush-temp-mail/app/user.html`, running `lushtempmail-app` image/container, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; static user-page content redeploy only.

### 2026-03-21 15:00 - fix_vps_helper_permission_for_set_user
- Changed: `deploy/scripts/lushtempmail.sh` now invokes the credential updater through `bash` for both `set-admin` and `set-user`.
- Fixed: the live VPS helper no longer fails with `Permission denied` when rotating `user` credentials after deploy.
- Affected files: `deploy/scripts/lushtempmail.sh`, live deploy script permissions on VPS, `/usr/local/bin/lushtempmail`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; helper/runtime fix only, with no API or UI contract change.

### 2026-03-21 14:56 - deploy_admin_user_split_to_vps
- Added: live VPS env now includes a real `USER_USERNAME` / `USER_PASSWORD`, and the installed `lushtempmail` helper now exposes `set-user`.
- Changed: the current admin/user split build was uploaded to `/opt/lush-temp-mail/app`, rebuilt, and restarted on VPS `82.197.71.6`.
- Fixed: the public site `https://lush.congmail.top` now serves the deployed role-based flow end-to-end, with `user` entering `user.html` and `admin` remaining on the admin dashboard.
- Affected files: `deploy/.env` on VPS, live app files under `/opt/lush-temp-mail/app`, `/usr/local/bin/lushtempmail`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: medium; production now depends on the new `user` credential being kept local-only and rotated via `lushtempmail set-user` when needed.

### 2026-03-20 16:35 - rule_bootstrap
- Added: root `AGENTS.md` for `D:\Lush-Temp-Mail`.
- Added: project memory docs under `D:\Lush-Temp-Mail\docs\`.
- Changed: documented current static-only state and target temp-mail backend direction.
- Fixed: missing project rules/context baseline before implementation.
- Affected files: `AGENTS.md`, `docs/PROJECT_CONTEXT.md`, `docs/DECISIONS.md`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; documentation/bootstrap only, no runtime behavior changed.

### 2026-03-20 17:20 - temp_mail_backend_and_vps_runtime
- Added: FastAPI backend, SQLite persistence, IMAP sync service, parser tests, Dockerfile, requirements, deploy assets, backend/deploy AGENTS files.
- Changed: root frontend now uses real API/session state instead of mock email data.
- Fixed: implemented catch-all-based alias auto-discovery so arbitrary `@congmail.top` addresses can appear without manual pre-creation.
- Affected files: `index.html`, `app.js`, `style.css`, `.gitignore`, `requirements.txt`, `Dockerfile`, `backend/**`, `deploy/**`, `docs/PROJECT_CONTEXT.md`, `docs/DECISIONS.md`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: medium; app/runtime behavior changed significantly, public DNS for `lush.congmail.top` still pending before final public HTTPS cutover.

### 2026-03-20 17:32 - public_proxy_fix
- Added: documented Docker host-gateway requirement for shared Caddy.
- Changed: reverse proxy target for `lush.congmail.top` from `127.0.0.1:8012` to `host.docker.internal:8012`.
- Fixed: resolved public `502` cause where Caddy container could not reach the temp-mail app bound on the host loopback.
- Affected files: `deploy/Caddyfile.snippet`, `deploy/README.md`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: medium; requires syncing the same proxy fix to the live VPS Caddy stack.

### 2026-03-20 17:36 - shared_proxy_network_fix
- Added: `shared_proxy` network attachment and explicit alias `lushtempmail-app` for the temp-mail app service.
- Changed: Caddy upstream for `lush.congmail.top` now points to `lushtempmail-app:8010`.
- Fixed: removed dependency on host loopback publishing, which still blocked Caddy from reaching the app across containers.
- Affected files: `deploy/docker-compose.vps.yml`, `deploy/Caddyfile.snippet`, `deploy/README.md`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: medium; live VPS compose and Caddy config must be synced together.

### 2026-03-20 17:46 - admin_credential_helper
- Added: `deploy/scripts/set_admin_credentials.sh` for changing temp-mail admin credentials on VPS.
- Changed: `lushtempmail` helper now supports `set-admin`.
- Fixed: removed the need to manually edit `deploy/.env` when rotating temp-mail admin login.
- Affected files: `deploy/scripts/set_admin_credentials.sh`, `deploy/scripts/install_helpers.sh`, `deploy/scripts/lushtempmail.sh`, `deploy/README.md`, `docs/PROJECT_CONTEXT.md`, `docs/DECISIONS.md`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; operational helper only, verified on VPS.

### 2026-03-20 16:55 - imap_live_sync_recovery
- Added: external Docker network attachment `mailstack_default` for the temp-mail app service.
- Changed: deploy defaults/documentation now keep `IMAP_HOST=mail.congmail.top` instead of the broken host-gateway route.
- Fixed: live inbox sync for catch-all addresses such as `hoang123@congmail.top`.
- Affected files: `deploy/docker-compose.vps.yml`, `deploy/.env.example`, `deploy/README.md`, `docs/DECISIONS.md`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; deploy topology changed slightly, but the public `lush.congmail.top` route is unchanged and IMAP sync is now stable.

### 2026-03-20 17:03 - auto_refresh_and_relative_time_ticker
- Added: frontend auto-refresh loop and separate relative-time ticker while the admin page is visible.
- Changed: recommended/live `MAIL_SYNC_INTERVAL_S` from 20 to 10 seconds for quicker inbox import.
- Fixed: mail list and relative time labels no longer require manual refresh to update.
- Affected files: `app.js`, `deploy/.env.example`, `deploy/README.md`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; browser may need a hard refresh to fetch the new frontend bundle from cache.

### 2026-03-20 17:18 - new_mail_emphasis_and_flicker_removal
- Added: `Email má»›i` badge and stronger highlight state for newly arrived messages in `Mail feed`.
- Changed: silent auto-refresh now triggers real sync every 8 seconds, while relative-time labels refresh in place every 10 seconds.
- Fixed: open message detail no longer disappears/reappears during background refresh.
- Affected files: `app.js`, `style.css`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; the browser may still need a hard refresh once to fetch the latest frontend assets.

### 2026-03-20 17:28 - tone_down_new_mail_styling
- Changed: removed the bright row highlight and pulse animation from new-mail styling.
- Fixed: message rows are back to the original neutral look while keeping the `Email má»›i` badge.
- Affected files: `style.css`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; browser may need a hard refresh to fetch the updated stylesheet.

### 2026-03-20 17:35 - publish_repo_to_github
- Added: git publishing step for `D:\Lush-Temp-Mail` to the empty GitHub repository `Lush-Temp-Mail`.
- Changed: local folder becomes the canonical git repo for future commits and pushes.
- Fixed: project is no longer only a filesystem copy; future VPS updates can track GitHub properly.
- Affected files: `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; assumes current local state is the desired initial upstream snapshot.

### 2026-03-20 18:22 - clone_repo_and_run_local_app
- Added: local clone at `C:\Users\PC\Lush-Temp-Mail` and local Python virtual environment `.venv`.
- Changed: installed runtime dependencies and launched the app locally on `127.0.0.1:8010`.
- Fixed: verified the local startup path with a passing `/api/health` response before opening the UI.
- Affected files: `.venv/`, `run.log`, `run.err`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; the app is available locally now, but IMAP sync stays idle until a real `IMAP_PASSWORD` is configured.

### 2026-03-20 18:48 - simplify_local_inbox_layout_for_review
- Added: footer pagination controls for the inbox list area.
- Changed: removed the hero cover, tightened the layout under the topbar, and reduced the sidebar to inbox filters only.
- Fixed: made the mail list scroll independently so navigation and detail panel remain stable during browsing.
- Affected files: `index.html`, `style.css`, `app.js`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: medium; local frontend flow is intentionally simplified and no longer exposes alias management in the UI.

### 2026-03-20 18:57 - trim_topbar_and_add_warm_favicon
- Added: `favicon.svg` for the browser tab with a warm red mail-style icon.
- Changed: removed the sidebar info card plus the topbar sync control and admin identity cluster.
- Fixed: top-level chrome is now visually cleaner for the inbox-focused layout review.
- Affected files: `index.html`, `style.css`, `app.js`, `favicon.svg`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; purely presentational local UI cleanup.

### 2026-03-20 19:00 - redesign_favicon_with_lucide_like_mail_mark
- Changed: favicon now uses a simpler lucide-style mail icon with bolder strokes.
- Fixed: improved readability of the tab icon at very small sizes.
- Affected files: `favicon.svg`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; favicon-only visual refinement.

### 2026-03-20 19:04 - switch_favicon_to_app_logo_mark
- Changed: browser favicon now points to `logo.svg` so the tab uses the same icon mark as the header.
- Fixed: removed the mismatch between header branding and tab branding during local review.
- Affected files: `index.html`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; favicon source swap only.

### 2026-03-20 19:14 - deploy_latest_ui_polish_to_vps
- Changed: synced the latest local inbox-focused UI files to the live VPS app copy.
- Fixed: public `lush.congmail.top` now serves the updated simplified layout after redeploy.
- Affected files: `index.html`, `app.js`, `style.css`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: medium; live container was rebuilt and restarted successfully during the deploy.

### 2026-03-20 19:35 - inbox_interaction_polish_and_faster_sync
- Added: message delete API plus UI hover delete action, and automatic 7-day message cleanup during sync.
- Changed: inbox rows now render alias first, sender second, subject third, with deterministic random avatar colors and alias-aware search.
- Fixed: live inbox refresh is now more responsive via faster frontend polling and `MAIL_SYNC_INTERVAL_S=4` on the VPS runtime.
- Affected files: `app.js`, `style.css`, `index.html`, `backend/app/config.py`, `backend/app/db.py`, `backend/app/main.py`, `backend/app/imap_sync.py`, `backend/app/utils.py`, `deploy/.env.example`, `deploy/README.md`, `docs/DECISIONS.md`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: medium; runtime behavior for inbox refresh and message retention changed on live.

### 2026-03-20 20:17 - important_group_retention_60d_and_composer_polish
- Added: `Quan trá»ng` inbox group, message star toggle API/state, and reply/forward composer UI with `CC` inside the detail panel.
- Changed: alias default lifetime is now `60 ngÃ y`, message auto-cleanup is now `60 ngÃ y`, and row actions use icon-only styling consistent with the app icon language.
- Fixed: important messages can now be pinned and filtered cleanly, while the live UI preserves alias-first ordering and faster inbox review flow.
- Affected files: `AGENTS.md`, `index.html`, `app.js`, `style.css`, `backend/app/config.py`, `backend/app/db.py`, `backend/app/main.py`, `backend/app/imap_sync.py`, `deploy/.env.example`, `deploy/README.md`, `docs/DECISIONS.md`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: medium; DB schema now auto-adds `important`, and live retention/runtime defaults changed from 7 days to 60 days.

### 2026-03-20 20:36 - detail_pane_layout_and_recent_badge_stability
- Added: bottom action bar for `Tráº£ lá»i` / `Chuyá»ƒn tiáº¿p` and a wider reader-shell layout in the desktop email detail pane.
- Changed: removed the old top `Email actions` card, widened the right reading column to fill remaining space, and kept the compose draft inline above the new footer actions.
- Fixed: switching between groups no longer reflags old emails as `Email má»›i`, and unchanged inbox lists no longer re-render every auto-refresh cycle, eliminating the visible hover flicker.
- Affected files: `index.html`, `app.js`, `style.css`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low to medium; frontend-only change, but the desktop reading layout and refresh behavior are noticeably different.

### 2026-03-20 20:40 - viewport_edge_detail_pane
- Changed: the app shell now uses the full viewport width, the inbox list is flexible again, and the desktop detail pane is anchored to the far right with responsive fixed width.
- Fixed: the message detail scrollbar now sits at the right page edge instead of inside a centered shell, so widening the reader no longer compresses the inbox list unnaturally.
- Affected files: `index.html`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; frontend layout-only adjustment for large-screen desktop view.

### 2026-03-20 20:44 - revert_to_centered_reference_layout
- Changed: reverted the last desktop shell change and restored the centered `max-width` layout to match the user's reference image.
- Fixed: inbox list and detail pane proportions are back to the previous centered-shell balance instead of the viewport-edge layout.
- Affected files: `index.html`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; layout-only revert on desktop.

### 2026-03-20 20:48 - match_saved_legacy_layout_file
- Changed: aligned the desktop shell with the user's saved HTML reference, using `main` as `flex-1` and a fixed `420px` detail pane inside the centered `1600px` shell.
- Fixed: the live layout now matches the saved legacy structure instead of the intermediate proportional variants inferred from screenshots.
- Affected files: `index.html`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; desktop layout-only adjustment.

### 2026-03-20 20:53 - detail_viewport_edge_without_layout_shift
- Changed: only the desktop detail panel viewport now extends to the right page edge, while the original `420px` layout slot and inbox column widths stay unchanged.
- Fixed: the detail scrollbar now sits flush with the browser edge without altering the surrounding shell proportions or compressing the email list.
- Affected files: `index.html`, `style.css`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; desktop detail-pane rendering only.

### 2026-03-20 21:01 - remove_mail_body_label
- Changed: removed the `Mail body` heading from the detail content section.
- Affected files: `app.js`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; text-only UI cleanup in the detail pane.

### 2026-03-20 21:11 - sticky_detail_footer_and_compose_jump
- Changed: the detail pane now has a fixed footer action bar, while the content area scrolls independently above it.
- Changed: opening `Tráº£ lá»i` / `Chuyá»ƒn tiáº¿p` now renders the composer at the top of the detail flow instead of below the email body.
- Fixed: clicking reply from the footer no longer requires manual scrolling back up to find the composer form.
- Affected files: `app.js`, `style.css`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: medium; detail-pane interaction model changed, but only within the right reading panel.

### 2026-03-20 21:23 - real_smtp_send_for_reply_forward
- Added: SMTP sending service, send API endpoint, and frontend send integration for reply/forward with `CC`.
- Changed: deploy config now documents `SMTP_*` settings and defaults them to the same central mailbox used by IMAP when appropriate.
- Fixed: real outgoing messages now include the required `Date` header, avoiding the previous `BAD HEADER` rejection from the mail filter.
- Affected files: `app.js`, `backend/app/config.py`, `backend/app/main.py`, `backend/app/mailer.py`, `deploy/.env.example`, `deploy/README.md`, `docs/DECISIONS.md`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: medium; composer send buttons now perform real SMTP delivery from `contact@congmail.top`.

### 2026-03-20 21:40 - flatten_composer_visuals_and_split_send_button_styles
- Added: mode-specific send-button styling so reply and forward can use different visual weight without changing behavior.
- Changed: the composer panel now uses a flat white surface, and form fields use softer neutral borders instead of the orange-tinted look.
- Fixed: `Gá»­i chuyá»ƒn tiáº¿p` is now white, `Gá»­i tráº£ lá»i` remains orange, and the textarea/input outline no longer shows the blurry orange focus treatment from before.
- Affected files: `app.js`, `style.css`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; frontend-only visual polish inside the detail composer.

### 2026-03-20 21:58 - page_scoped_multi_select_and_batch_delete
- Added: `Ctrl/Cmd + click`, `Shift + click`, and `Ctrl/Cmd + A` multi-select support for inbox rows on the current page, plus click-outside to clear batch selection.
- Changed: delete actions now reuse a shared batch delete flow so row-trash and keyboard `Delete` can remove one or many selected emails with the same confirmation logic.
- Fixed: bulk selection behaves more like a desktop file list, and stale multi-select state no longer sticks around after you click away from the inbox rows.
- Affected files: `app.js`, `docs/DECISIONS.md`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: medium; inbox row interaction model changed, but the scope is intentionally limited to the currently visible paginated page.

### 2026-03-20 22:04 - prevent_text_highlight_during_shift_range_select
- Changed: inbox rows now explicitly disable text selection during pointer interaction.
- Fixed: `Shift + click` range selection no longer highlights sender/subject text while still preserving the multi-select behavior.
- Affected files: `app.js`, `style.css`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; frontend-only interaction polish for inbox row selection.

### 2026-03-20 22:10 - translate_message_endpoint_auto_detect_vi
- Added: `POST /api/messages/{message_id}/translate` plus `backend/app/translator.py` for on-demand message translation.
- Changed: subject/body translation now uses auto-detect -> `vi` without adding a new dependency or schema change.
- Fixed: frontend now has a clear translation payload shape with separate `subject` and `body` results plus detected source language.
- Affected files: `backend/app/main.py`, `backend/app/translator.py`, `docs/DECISIONS.md`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: medium; translation depends on an external Google Translate web endpoint, but runtime impact is isolated to the new route.

### 2026-03-20 22:18 - in_panel_google_style_translate_action
- Added: a Google-style translate icon button in the email detail header that translates `subject` and `body` in place.
- Changed: translated content is now cached per message in the frontend and can be toggled against the original email without extra layout shifts.
- Fixed: admins can translate foreign-language emails directly inside the detail pane with default auto-detect -> Vietnamese behavior.
- Affected files: `app.js`, `style.css`, `backend/app/main.py`, `backend/app/translator.py`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: medium; the new UI depends on the backend translation helper and an external Google Translate web endpoint.

### 2026-03-20 22:27 - sync_current_state_to_github
- Changed: the full current tracked project state was prepared for source-control sync on `origin/main`.
- Added: fresh docs entries describing the GitHub sync task itself for parity with the local project memory.
- Affected files: `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; source-control sync only, with runtime log files intentionally left out of the commit.

### 2026-03-21 12:43 - pull_latest_changes_from_origin_main
- Added: a project-memory record for the latest pull operation from GitHub.
- Changed: local branch `main` was fast-forwarded from `2cb069f` to `ef65da9` using `git pull --ff-only origin main`.
- Fixed: local workspace now matches the newest tracked upstream state without an extra merge commit.
- Affected files: `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; source-control sync only, with no manual code changes beyond required project logging.

### 2026-03-21 14:13 - add_user_facing_alias_inbox_page
- Added: `user.html`, `user.css`, and `user.js` for a dedicated user-facing alias inbox with hero intro, fast lookup form, inbox list, detail reader, mobile drawer, and in-panel translation.
- Changed: backend now exposes `/api/public/inbox`, `/api/public/messages/{message_id}`, and `/api/public/messages/{message_id}/translate`, backed by exact-alias normalization helpers and public summary/detail queries.
- Fixed: the new public inbox query no longer truncates silently at 120 emails, and SQLite now has recipient/alias message indexes to keep alias lookup responsive.
- Affected files: `user.html`, `user.css`, `user.js`, `backend/app/main.py`, `backend/app/db.py`, `backend/app/utils.py`, `docs/DECISIONS.md`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: medium; user lookup is intentionally alias-based without a separate account login, so anyone who knows an alias can read that alias inbox on the new public route.

### 2026-03-21 14:33 - simplify_user_inbox_ui_uncodixfy
- Changed: `user.html` now uses a much simpler layout with one lookup form in the top section and a plain results shell below that appears only after lookup.
- Changed: `user.css` now favors flat white panels, normal borders, restrained radii, and a calmer dark hero instead of floating showcase cards and decorative premium effects.
- Fixed: removed extra user-facing UI behavior and visual clutter such as the refresh control, translation action, decorative chips, and the previous oversized rounded floating composition.
- Affected files: `user.html`, `user.css`, `user.js`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; frontend-only simplification of the user route, with backend public lookup APIs left unchanged.

### 2026-03-21 14:46 - split_admin_user_login_flows
- Added: role-aware session handling for both `admin` and `user`, plus deploy env/helper support for `USER_USERNAME` and `USER_PASSWORD`.
- Changed: the shared login page at `/` now routes `admin` into the admin dashboard and `user` into `user.html`, while `/api/public/*` is no longer open without a `user` session.
- Fixed: the user UI now shows `ÄÄƒng xuáº¥t` instead of `Admin`, carries the shared auth cookie on requests, redirects unauthorized access back to `/`, and stays synchronized with the existing app style instead of introducing a separate visual system.
- Affected files: `backend/app/auth.py`, `backend/app/config.py`, `backend/app/db.py`, `backend/app/main.py`, `index.html`, `app.js`, `user.html`, `user.js`, `deploy/.env.example`, `deploy/README.md`, `deploy/scripts/set_admin_credentials.sh`, `deploy/scripts/lushtempmail.sh`, `docs/DECISIONS.md`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: medium; existing deployments must add `USER_USERNAME` / `USER_PASSWORD` and operators should update credentials using the new helper commands to avoid relying on insecure defaults.

### 2026-03-21 16:11 - refine_user_inbox_rows_to_normal_mailbox_style
- Added: sender-based avatar initials in the user inbox so each message row reads like a normal mailbox item instead of an alias card.
- Changed: `user.js` now renders the left list as sender -> subject -> single-line preview, with the time kept on the right and the detail header reusing the same sender display logic.
- Fixed: `user.css` now makes list/detail avatars circular, tightens row spacing, and removes the bulky preview block that made the message list feel raw and technical.
- Affected files: `user.js`, `user.css`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; frontend-only presentation update for the user inbox route, with no API or auth contract changes.

### 2026-03-21 16:17 - auto_scroll_lookup_into_inbox_view
- Added: a dedicated `scrollToLookupResults()` helper so the user route can reposition the viewport after a manual alias lookup.
- Changed: clicking `Kiá»ƒm tra` now smoothly scrolls to the inbox shell with an offset that still leaves the lookup form visible at the top, matching the desired reference behavior.
- Fixed: silent alias bootstrap from the query string no longer triggers the same motion, avoiding unexpected page jumps on first load.
- Affected files: `user.js`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; frontend-only behavior change limited to the user lookup route.

### 2026-03-21 16:22 - rebalance_post_lookup_spacing_and_redeploy
- Changed: `user.js` now scrolls relative to `lookupForm` instead of the inbox shell, so the post-lookup viewport keeps the search input fully visible with a more balanced gap from the browser top.
- Added: a new cache-busting asset version in `user.html` (`user-inbox-scroll-4`) so browsers fetch the updated user-route JavaScript immediately after deploy.
- Fixed: the live VPS build now includes the refined user scroll behavior and serves the new asset version without relying on a hard refresh of stale JS.
- Affected files: `user.js`, `user.html`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; frontend-only scroll-offset adjustment plus static asset version bump on the user route.

### 2026-03-21 16:34 - redeploy_latest_user_js_edit_to_vps
- Changed: production `user.html` now references `user.js?v=20260321-user-js-redeploy-5` so the latest saved JavaScript edit is fetched immediately instead of a cached previous asset.
- Fixed: the live VPS app was rebuilt with the newest local `user.js` and verified healthy after the targeted redeploy.
- Affected files: `user.js`, `user.html`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; targeted frontend redeploy for the user route only, with no backend or auth contract changes.

### 2026-03-21 16:59 - investigate_mail_delay_and_add_sync_on_check
- Added: `POST /api/public/sync` for authenticated `user` sessions and a sync lock inside `MailSyncService` so user-triggered sync can safely coexist with admin refreshes and the background sync loop.
- Changed: `user.js` now calls the new public sync endpoint before loading `/api/public/inbox`, and `user.html` now references `user.js?v=20260321-public-sync-6` to bust stale browser cache.
- Fixed: user lookup no longer waits for the next background IMAP cycle before showing a newly arrived message, and the live investigation confirmed recent Gmail delivery into the mailbox/DB was already near-real-time rather than delayed by the mail server.
- Affected files: `backend/app/imap_sync.py`, `backend/app/main.py`, `user.js`, `user.html`, `docs/DECISIONS.md`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: medium-low; user lookups now perform an IMAP sync on demand, increasing sync calls under heavy user traffic but keeping behavior much closer to â€œcheck and see it immediatelyâ€.
### 2026-03-21 18:34 - align_admin_checkbox_to_avatar_lane
- Added: a more realistic local verification pass that probes checkbox/avatar alignment against a tall multi-line inbox row instead of relying on the empty local inbox shell.
- Changed: the admin row checkbox now anchors to a fixed top offset aligned with the avatar lane, and the leftover `mt-1` utility has been removed from the checkbox label markup.
- Fixed: live inbox rows no longer let the checkbox drift downward when sender/subject/snippet content makes the row taller than the short local test rows.
- Affected files: `app.js`, `style.css`, `index.html`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; inbox row positioning only, with header width and delete-all layout intentionally left untouched.
### 2026-03-21 18:43 - fix_user_lookup_and_decode_mime_subjects
- Added: a shared `decode_mime_text()` helper path in backend mail parsing so MIME-encoded `Subject` and sender display names are normalized before reaching the UI.
- Changed: the alias local-part regex now accepts 2-character aliases like `12@congmail.top`, matching the catch-all inbox behavior already allowed by the product.
- Fixed: the user route no longer rejects valid 2-character aliases, and admin/user inbox rows now decode old and new RFC2047 Vietnamese mail subjects instead of showing raw `=?UTF-8?...` headers.
- Affected files: `backend/app/utils.py`, `backend/app/parser.py`, `backend/app/imap_sync.py`, `backend/app/db.py`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low-medium; backend-only parsing/validation correction, with no API contract shape changes.
### 2026-03-21 20:31 - audit_encoding_and_alias_special_char_support
- Added: a repository-wide mojibake audit pass that checks frontend/backend source files for suspicious UTF-8 corruption byte patterns.
- Changed: the last broken admin multi-select label string in `app.js` has been rewritten as clean UTF-8 text.
- Fixed: validated alias support now covers 2-character aliases and `_` / `-` local parts in the user lookup flow, matching the intended catch-all mailbox behavior.
- Affected files: `app.js`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; text cleanup plus validation audit only, with no new API shape changes.
### 2026-03-21 20:36 - deploy_encoding_and_alias_fix_to_production
- Changed: production now runs the corrected backend parser/validation files from `backend/app/` instead of the stale pre-fix build.
- Fixed: live user lookup now accepts 2-character aliases plus `_` / `-`, and live admin message rows no longer expose undecoded RFC2047 subject/from-name values.
- Affected files: `backend/app/utils.py`, `backend/app/parser.py`, `backend/app/imap_sync.py`, `backend/app/db.py`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; production now matches the already-verified local behavior for alias validation and MIME decoding.
### 2026-03-21 20:44 - allow_trailing_underscore_and_hyphen_in_aliases
- Changed: alias validation now accepts local-parts that end in `_` or `-`, matching real aliases already present in the inbox.
- Fixed: the user lookup route no longer rejects aliases like `1_@congmail.top` or `1-@congmail.top`, while still treating dot-terminated aliases such as `1.@congmail.top` as invalid.
- Affected files: `backend/app/utils.py`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; validation rule widened for real inbox addresses without changing API response shape.
### 2026-03-21 20:49 - expand_alias_support_to_rfc_safe_special_chars
- Changed: alias validation now follows a practical dot-atom rule, accepting common RFC-safe local-part characters such as `_`, `-`, `+`, `=`, `%`, and apostrophe.
- Fixed: user lookup no longer rejects these real-world alias forms, while malformed dot usage like leading/trailing `.` or `..` remains blocked.
- Affected files: `backend/app/utils.py`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low-medium; catch-all lookup is more permissive for real addresses, but still intentionally avoids quoted/space-containing local parts.
### 2026-03-21 21:02 - adopt_imap_idle_with_polling_fallback
- Added: backend support for `IMAP IDLE` runtime mode with capability detection, timeout keepalive, and fallback to polling if `IDLE` is unavailable.
- Changed: admin login still forces an initial IMAP sync, but background admin refresh now reloads DB-backed message data every 2 seconds instead of hitting `/api/sync` on every tick.
- Fixed: mailbox pickup can now become near-realtime without changing alias routing through the central catch-all mailbox.
- Affected files: `backend/app/config.py`, `backend/app/imap_sync.py`, `app.js`, `index.html`, `deploy/.env.example`, `deploy/README.md`, `docs/DECISIONS.md`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: medium; sync behavior changes at runtime, but the fallback polling path remains in place if the live IMAP server does not sustain `IDLE`.
### 2026-03-21 21:40 - add_sse_realtime_refresh_and_stale_user_sync
- Added: backend `SSE` streams for admin/user inbox updates and a shared `/api/mail-sync/status` endpoint exposing watcher heartbeat/staleness.
- Changed: admin tabs now use `SSE` as the primary refresh trigger with timer refresh kept as slower fallback, while the user lookup flow only forces IMAP sync when the backend watcher is stale.
- Fixed: reduced the delay where mail was already in SQLite but admin/user still had to wait for the next manual check or short polling cycle to notice it.
- Affected files: `backend/app/events.py`, `backend/app/imap_sync.py`, `backend/app/main.py`, `backend/app/db.py`, `app.js`, `user.js`, `index.html`, `user.html`, `docs/DECISIONS.md`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: medium; browser realtime now depends on a persistent `EventSource` connection, but normal API flows and manual lookup still work if the stream drops.
### 2026-03-21 21:56 - fix_imap_idle_tag_abort_and_remeasure_live_latency
- Fixed: corrected the `IMAP IDLE` tag handling bug that could trigger `imaplib.IMAP4.abort` when the `IDLE` command completed on production.
- Changed: redeployed the backend with the bytes-safe `IDLE` enter/exit path so the live watcher can stay stable in `mode=idle`.
- Added: a measured live probe result showing a fresh SMTP probe mail reached the user inbox API in about `1.44s` after the fix.
- Affected files: `backend/app/imap_sync.py`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: medium-positive; live pickup should be more stable now, and the current remaining delay is more likely to come from the upstream sender hop than from the app/VPS inbox ingestion path.
### 2026-03-21 22:01 - document_real_timestamp_measurement_caveat
- Added: a documented finding that `messages.received_at` should not be treated as a strict ingestion-latency timestamp during production debugging.
- Changed: latency analysis guidance now prefers mailserver logs, IMAP/Dovecot timing, and direct API visibility checks over comparing UI timing to `received_at` alone.
- Fixed: reduced ambiguity in future investigations of “mail lên chậm” by separating sender-to-mailserver delay from mailbox-to-app delay.
- Affected files: `docs/DECISIONS.md`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; this is an operational debugging clarification, not a runtime behavior change.
### 2026-03-21 22:10 - persist_mailbox_and_ingest_timestamps
- Added: `mailbox_received_at` and `ingested_at` fields for every message, plus an admin debug endpoint `/api/debug/message-timings`.
- Changed: IMAP fetch now requests `INTERNALDATE`, and the DB migration path backfills timing columns for existing rows during startup.
- Fixed: future latency investigations no longer need to infer ingest speed from the less reliable header-derived `received_at` field alone.
- Affected files: `backend/app/db.py`, `backend/app/imap_sync.py`, `backend/app/parser.py`, `backend/app/main.py`, `docs/DECISIONS.md`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low-medium; schema expands in place on startup, but existing APIs stay backward-compatible and timing analysis becomes much more trustworthy.
### 2026-03-21 22:17 - fix_public_inbox_summary_regression_and_error_body_handling
- Fixed: restored `/api/public/inbox` after the timing-column rollout by updating the public summary query to select the new timing columns expected by the row serializer.
- Changed: frontend `api()` helpers now consume failed response bodies only once and parse JSON from that single text payload, avoiding the misleading `body stream already read` browser error.
- Added: new asset version bumps in `user.html` and `index.html` so clients fetch the repaired JS immediately.
- Affected files: `backend/app/db.py`, `user.js`, `app.js`, `user.html`, `index.html`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; this is a targeted regression fix and improves future error visibility when the backend really does fail.
### 2026-03-21 22:22 - verify_live_user_inbox_error_cleared
- Added: a production verification pass for the repaired user lookup path using both direct API checks and a real browser login/search flow.
- Changed: no runtime code; this records that live `user.html` is serving the fixed `user.js?v=20260321-user-sse-8` bundle and that alias lookup for `1_@congmail.top` succeeds on the current build.
- Fixed: confirmed the previously reported live user-route crash is no longer reproducible after the regression fix deploy.
- Affected files: `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; leaves an operational trail that the issue was re-checked on production instead of only assumed fixed.
### 2026-03-21 22:29 - measure_latest_production_mail_timing_with_new_fields
- Added: a real production timing measurement that correlates one fresh Gmail delivery with both the new debug timestamp fields and the mailserver container logs.
- Changed: no runtime code; this entry records the measured split for `1-@congmail.top` / `Message-ID <CAJSR+axPzdoN2Hv7zutQLZXJPHD9MqKLwEHDwp+e6S_BeOw=ZA@mail.gmail.com>`.
- Fixed: operational uncertainty around “mail chậm” is reduced for this sample because the internal `mailbox -> app DB` hop was measured at roughly `0.55s`.
- Affected files: `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; creates a concrete baseline for future latency investigations without changing production behavior.
### 2026-03-22 09:07 - sync_deployed_worktree_to_github
- Added: a source-control sync step that packages the current deployed application state from the local repo and prepares it for GitHub.
- Changed: no runtime behavior; this records that the VPS app path was verified as a non-git deployment directory and that the local repository is the authoritative push source.
- Fixed: reduces deployment/source drift by ensuring the code already running on VPS is also represented in the GitHub repository.
- Affected files: `docs/WORKLOG.md`, `docs/CHANGELOG.md`.
- Impact/Risk: low; metadata/documentation only, but it tracks an important operational sync step.
### 2026-03-23 10:02 - stabilize_html_email_rendering
- Added: HTML email rendering inside sandboxed iframes for both admin and user readers, plus visible attachment metadata sections in the detail pane.
- Changed: HTML-to-text fallback parsing now strips style/script/head noise and prefers cleaned HTML text when the plain-text part looks like CSS or MIME boilerplate.
- Fixed: Transactional emails with buttons, embedded CSS, or attachment parts no longer spill raw `@font-face` / layout CSS into the displayed body content.
- Affected files: backend/app/parser.py, backend/app/imap_sync.py, backend/app/db.py, backend/tests/test_parser.py, app.js, user.js, style.css, user.css
- Impact/Risk: Existing messages without `html_body` still fall back to text rendering; iframe-based HTML display is isolated from app CSS but depends on browser iframe support for final sizing.

### 2026-03-23 10:09 - flatten_email_reader_surface
- Added: No new feature surface; this is a presentation pass to align the reader with the existing flat app shell.
- Changed: Removed the visible text-fallback toggle and flattened the email/attachment presentation so content renders directly on the existing white reader panel.
- Fixed: Nested boxed containers around HTML mail content and attachments no longer make the detail pane feel cramped or visually detached from the rest of the UI.
- Affected files: app.js, user.js, style.css, user.css
- Impact/Risk: Rich HTML emails still rely on the iframe path; attachments remain metadata-only in the reader.

### 2026-03-23 10:20 - fix_user_reader_escapeattribute_regression
- Added: Restored the missing `escapeAttribute()` helper in the user reader bundle.
- Changed: Bumped the `user.js` cache-busting version in `user.html` so browsers fetch the fixed script immediately after redeploy.
- Fixed: The live user detail pane no longer crashes with `escapeAttribute is not defined` when opening HTML emails.
- Affected files: user.js, user.html
- Impact/Risk: Users with an already-open cached tab may still need one hard refresh to replace the old JS bundle.

### 2026-03-23 10:30 - tighten_otp_and_action_link_badges
- Added: Parser regression coverage for lowercase OTP false positives and noisy HTML link extraction.
- Changed: OTP/link extraction now only keeps confident results; generic or asset URLs are dropped, and only one action link per type is retained.
- Fixed: Verification emails no longer surface bogus OTP badges like `rgin` or a row of unrelated `Mở link` actions from HTML/CSS noise.
- Affected files: backend/app/parser.py, backend/app/db.py, backend/tests/test_parser.py
- Impact/Risk: Existing filter counts based on stored extracted JSON may still need a future maintenance pass if strict historical `Có OTP` / `Có link verify` scopes must be perfectly reclassified in bulk.

### 2026-03-23 10:56 - tighten_ui_and_subagent_rules
- Added: A workspace-level `D:\AGENTS.md` file so the personalized operating rules are now stored on disk and reused consistently across future tasks.
- Changed: Workspace and repo rules now explicitly require `uncodixfy` for UI work and require UI edits to align with the existing design system before introducing new patterns.
- Fixed: Reduces repeated UI drift toward nested floating cards and reduces over-eager subagent usage by making evaluation and scope constraints explicit.
- Affected files: D:\AGENTS.md, AGENTS.md
- Impact/Risk: low; no runtime behavior changes, but future UI and delegation behavior is intentionally stricter.

### 2026-03-23 11:21 - preserve_html_translation_and_skip_vi_to_vi
- Added: HTML-aware translation output (`translated_html`) plus translator tests covering layout preservation and Vietnamese skip behavior.
- Changed: Admin and user readers now keep iframe-based HTML layout while translated, and both routes share the same `skip if already Vietnamese` behavior.
- Fixed: Translating an HTML email no longer collapses the layout into plain text, and emails already in Vietnamese no longer show or apply a broken `Ti?ng Vi?t -> Ti?ng Vi?t` translation state.
- Affected files: backend/app/translator.py, backend/app/db.py, backend/tests/test_translator.py, app.js, user.js, user.css, index.html, user.html
- Impact/Risk: low-medium; translation behavior changed on both readers, but syntax and regression tests pass and the fallback path still preserves plain-text emails.

### 2026-05-05 11:35 - add_admin_user_management
- Added: Admin sidebar now has a `Người dùng` tab with create/edit/delete user controls.
- Changed: Auth accounts are now stored in SQLite `users`, seeded from existing env admin/user credentials on first migration; login reads from DB instead of fixed env comparison.
- Fixed: Admin can update username/password/role without editing VPS env, while safeguards block deleting the current account or removing the last admin.
- Affected files: backend/app/db.py, backend/app/main.py, backend/tests/test_users.py, index.html, app.js, style.css
- Impact/Risk: medium; auth storage changed, but env credentials remain the initial seed path and regression tests cover seeding/auth/update.

### 2026-05-09 11:40 - improve_user_mobile_reader
- Added: Concise project memory files for faster future task bootstrap.
- Changed: User mobile lookup now scrolls directly to the results shell, hides the desktop reading pane on mobile, and lets the message list use normal page scroll.
- Fixed: Mobile reader is now the only scroll container while a message is open, with body scroll locked and iframe heights refreshed after the overlay opens.
- Affected files: user.html, user.css, user.js, docs/PROJECT_BRIEF.md, docs/MEMORY_INDEX.md, docs/DECISIONS_INDEX.md, docs/UI_SYSTEM.md
- Impact/Risk: low-medium; only the user inbox mobile layout/scroll behavior changed, desktop layout is intentionally preserved.

### 2026-07-21 13:30 - apply_aurora_teal_theme
- Added: Aurora Teal regression coverage for the Tailwind palette, static asset cache versions, logo color, and removal of the previous brand orange values.
- Changed: Admin, user inbox, dynamic avatars, active/focus states, reader surfaces, and the `DA` monogram now use primary `#0f766e`, hover `#115e59`, and surface `#f0fdfa`.
- Preserved: Mail behavior, API contracts, layout, marine user hero, destructive colors, amber OTP badges, and Google translation colors remain unchanged.
- Affected files: index.html, user.html, style.css, user.css, app.js, user.js, logo.svg, backend/tests/test_branding.py, docs/UI_SYSTEM.md, docs/CHANGELOG.md.
- Impact/Risk: low; this is a visual token migration with cache-busted assets and automated branding coverage.

### 2026-09-07 - design_upstream_mail_capability_sync
- Added: Approved design spec for selectively integrating upstream multi-recipient, sender alias, outgoing attachments, auto-forwarding and summary-list performance.
- Preserved: DarkAmbient branding, Aurora Teal UI, existing API compatibility, production data, isolated VPS stack and apex Google Workspace.
- Affected files: docs/superpowers/specs/2026-09-07-upstream-mail-capability-sync-design.md, docs/DECISIONS_INDEX.md, docs/DECISIONS.md, docs/MEMORY_INDEX.md, docs/PROJECT_CONTEXT.md, docs/CHANGELOG.md.
- Impact/Risk: documentation only; runtime behavior is unchanged until the implementation plan is approved and executed.

### 2026-09-07 - integrate_upstream_mail_capabilities
- Added: Multi-recipient inbox mapping, sender aliases, outgoing attachments, automatic forwarding with per-target retry, summary-list loading, and matching DarkAmbient admin controls.
- Preserved: Aurora Teal branding, public alias isolation, existing SQLite/runtime data, apex Google Workspace and the isolated VPS deployment.
- Affected files: backend mail parser/database/sync/mailer/API, admin UI, regression tests, mail capability docs and deploy runbook.
- Impact/Risk: medium-high; schema migrations are additive and idempotent, while outbound and forwarding paths now perform additional SMTP work.

### 2026-10-05 - change_canonical_github_owner
- Changed: canonical GitHub repository owner from the previous account to `dangcong`; local `origin/main`, project memory, deployment runbook, and active implementation references now point to `https://github.com/dangcong/temp.darkambient.co`.
- Removed: all remaining references to the previous GitHub account name from tracked repository content.
- Affected files: deploy/darkambient/README.md, docs/PROJECT_BRIEF.md, docs/MEMORY_INDEX.md, docs/PROJECT_CONTEXT.md, docs/DECISIONS_INDEX.md, docs/DECISIONS.md, docs/WORKLOG.md, docs/superpowers/plans/2026-09-07-upstream-mail-capability-sync-implementation.md, docs/superpowers/specs/2026-09-07-upstream-mail-capability-sync-design.md, docs/CHANGELOG.md.
- Impact/Risk: documentation and Git routing only; application runtime and API behavior are unchanged.
