# UI System

## Product Language
- DarkAmbient uses a clean mail-workspace style with a white content surface, slate borders/text, and Aurora Teal `lush-500` actions.
- Brand surfaces use the compact teal `DA` monogram and the `DarkAmbient` wordmark without changing established layout density.
- Admin is a dense inbox workspace. User mode is a simpler lookup-and-read flow.

## Layout Patterns
- Desktop user inbox: search hero, alias summary, message list beside a reading pane.
- Mobile user inbox: compact search hero, message list in normal page flow, full-screen reader overlay after selecting a message.
- Avoid nested scroll regions on mobile unless the region is the active full-screen reader.

## Components
- Primary actions use Aurora Teal `#0f766e`; hover uses `#115e59`; subtle brand surfaces use `#f0fdfa`.
- Semantic rose/red, amber OTP, Google translation colors, and the marine user hero remain independent of the brand palette.
- Message rows use simple borders, avatar, sender, subject, preview, and relative time.
- Detail views use sender meta, subject, timestamp, then rendered email body.
- The admin composer is a focused modal with sender alias, recipients, subject, body and a compact attachment list; it must remain usable within one viewport on mobile.
- Automatic forwarding is a first-level admin view. Rules use the same restrained list-row pattern as auto-delete and users, with visible active/paused state and per-rule edit controls.

## Constraints
- Preserve Vietnamese text as UTF-8.
- Keep border radii and decoration restrained.
- Do not add decorative cards or marketing sections to operational mail screens.
- Keep `send`, `reply`, `forward` and forwarding-rule errors actionable without exposing raw SMTP exception text.

