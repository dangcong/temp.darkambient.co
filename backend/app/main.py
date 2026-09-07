from __future__ import annotations

import asyncio
import base64
import binascii
import json
import logging
import sqlite3
from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import quote

from fastapi import Body, Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import db
from .auth import clear_session, create_session, require_admin, require_session, require_user
from .config import settings
from .events import inbox_events
from .imap_sync import MailSyncService, fetch_message_attachment_payloads
from .mailer import (
    MAX_ATTACHMENT_TOTAL_BYTES,
    send_composed_message,
    validate_outgoing_attachments,
)
from .translator import DEFAULT_TARGET_LANGUAGE, translate_message
from .utils import iso_in_hours, is_valid_local_part, normalize_address, normalize_lookup_address, random_local_part


mail_sync = MailSyncService()
logger = logging.getLogger("lush_temp_mail.api")


def _decode_outgoing_attachments(value: Any) -> list[dict[str, Any]]:
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise ValueError("Danh sách tệp đính kèm không hợp lệ")

    decoded: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError("Tệp đính kèm không hợp lệ")
        filename = str(item.get("filename") or f"attachment-{index + 1}")
        filename = filename.replace("\\", "/").split("/")[-1].replace("\r", "").replace("\n", "")[:255]
        encoded = str(item.get("content_base64") or "")
        if not encoded or len(encoded) > (MAX_ATTACHMENT_TOTAL_BYTES * 2):
            raise ValueError("Nội dung tệp đính kèm không hợp lệ")
        try:
            content = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error) as error:
            raise ValueError(f"Không đọc được tệp {filename}") from error
        content_type = str(item.get("content_type") or "application/octet-stream")
        content_type = content_type.replace("\r", "").replace("\n", "")[:255]
        decoded.append(
            {
                "index": index,
                "filename": filename,
                "content_type": content_type,
                "disposition": "attachment",
                "size_bytes": len(content),
                "content": content,
            }
        )
    return validate_outgoing_attachments(decoded)


def _expires_at_from_hours(hours: int | None) -> str | None:
    if hours is None or hours <= 0:
        return None
    return iso_in_hours(hours)


def _clean_username(value: Any) -> str:
    username = str(value or "").strip()
    if not username:
        raise HTTPException(status_code=400, detail="Tên tài khoản là bắt buộc")
    if any(char.isspace() for char in username):
        raise HTTPException(status_code=400, detail="Tên tài khoản không được chứa khoảng trắng")
    return username


def _clean_role(value: Any) -> str:
    role = str(value or "").strip().lower()
    if role not in {"admin", "user"}:
        raise HTTPException(status_code=400, detail="Role phải là admin hoặc user")
    return role


def _clean_password(value: Any, *, required: bool) -> str | None:
    password = str(value or "")
    if not password:
        if required:
            raise HTTPException(status_code=400, detail="Mật khẩu là bắt buộc")
        return None
    return password


def _resolve_message_attachment(message: dict[str, Any], attachment_index: int) -> dict[str, Any] | None:
    attachment = db.get_message_attachment(message["id"], attachment_index)
    if attachment is not None:
        return attachment

    try:
        fetched_attachments = fetch_message_attachment_payloads(message)
    except Exception as error:
        logger.warning("Failed to fetch attachment payloads for message %s: %s", message.get("id"), error)
        fetched_attachments = []

    if fetched_attachments:
        db.cache_message_attachment_payloads(message["id"], fetched_attachments)
        attachment = db.get_message_attachment(message["id"], attachment_index)
        if attachment is not None:
            return attachment

    return None


def _resolve_message_attachments(message: dict[str, Any]) -> list[dict[str, Any]]:
    attachments = db.list_message_attachment_payloads(message["id"])
    if attachments:
        return attachments

    try:
        fetched_attachments = fetch_message_attachment_payloads(message)
    except Exception as error:
        logger.warning("Failed to fetch attachment payloads for message %s: %s", message.get("id"), error)
        return []

    if not fetched_attachments:
        return []
    db.cache_message_attachment_payloads(message["id"], fetched_attachments)
    return db.list_message_attachment_payloads(message["id"])


def _attachment_response(attachment: dict[str, Any]) -> Response:
    filename = str(attachment.get("filename") or "attachment")
    content_type = str(attachment.get("content_type") or "application/octet-stream")
    disposition = "inline" if content_type == "application/pdf" else "attachment"
    encoded_filename = quote(filename)
    return Response(
        content=attachment.get("content") or b"",
        media_type=content_type,
        headers={
            "Content-Disposition": f"{disposition}; filename*=UTF-8''{encoded_filename}",
            "X-Content-Type-Options": "nosniff",
        },
    )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.init_db()
    mail_sync.start()
    yield
    mail_sync.stop()


app = FastAPI(title="DarkAmbient Temp Mail", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.app_base_url, f"https://{settings.public_domain}", "http://127.0.0.1:8010"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _format_sse(event: str, payload: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def _admin_event_stream(request: Request):
    last_version = inbox_events.get_global_version()
    yield _format_sse("ready", {"version": last_version, "mail_sync": mail_sync.get_status()})
    while True:
        if await request.is_disconnected():
            break
        next_version = await asyncio.to_thread(inbox_events.wait_for_global, last_version, 25.0)
        if await request.is_disconnected():
            break
        if next_version == last_version:
            yield _format_sse("heartbeat", {"version": last_version, "mail_sync": mail_sync.get_status()})
            continue
        last_version = next_version
        yield _format_sse("messages", {"version": last_version, "mail_sync": mail_sync.get_status()})


async def _user_event_stream(request: Request, alias: str):
    last_version = inbox_events.get_alias_version(alias)
    yield _format_sse("ready", {"version": last_version, "alias": alias, "mail_sync": mail_sync.get_status()})
    while True:
        if await request.is_disconnected():
            break
        next_version = await asyncio.to_thread(inbox_events.wait_for_alias, alias, last_version, 25.0)
        if await request.is_disconnected():
            break
        if next_version == last_version:
            yield _format_sse("heartbeat", {"version": last_version, "alias": alias, "mail_sync": mail_sync.get_status()})
            continue
        last_version = next_version
        yield _format_sse("messages", {"version": last_version, "alias": alias, "mail_sync": mail_sync.get_status()})


@app.middleware("http")
async def add_cache_headers(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path in {"/", "/index.html", "/user.html"}:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    elif path in {"/app.js", "/user.js", "/style.css", "/user.css", "/logo.svg"}:
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    return response


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "mail_domain": settings.mail_domain, "public_domain": settings.public_domain}


@app.get("/api/mail-sync/status")
def mail_sync_status(_session=Depends(require_session)) -> dict[str, Any]:
    return {"ok": True, "item": mail_sync.get_status()}


@app.get("/api/events")
async def stream_admin_events(request: Request, _session=Depends(require_admin)):
    return StreamingResponse(
        _admin_event_stream(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/auth/login")
def login(response: Response, payload: dict[str, str] = Body(...)) -> dict[str, Any]:
    username = (payload.get("username") or payload.get("email") or "").strip()
    password = payload.get("password", "")
    user = db.authenticate_user(username, password)
    if user is None:
        raise HTTPException(status_code=401, detail="Sai tài khoản hoặc mật khẩu")
    session = create_session(response, user["username"], user["role"])
    return {
        "ok": True,
        "user": {"username": session["username"], "role": session["role"]},
        "expires_at": session["expires_at"],
    }


@app.post("/api/auth/logout")
def logout(response: Response, session=Depends(require_session)) -> dict[str, bool]:
    clear_session(response, session["token"])
    return {"ok": True}


@app.get("/api/auth/session")
def session(session=Depends(require_session)) -> dict[str, Any]:
    return {"ok": True, "user": {"username": session["username"], "role": session["role"]}, "expires_at": session["expires_at"]}


@app.get("/api/users")
def list_users(_session=Depends(require_admin)) -> dict[str, Any]:
    return {"items": db.list_users()}


@app.post("/api/users")
def create_user(payload: dict[str, Any] = Body(...), _session=Depends(require_admin)) -> dict[str, Any]:
    username = _clean_username(payload.get("username"))
    password = _clean_password(payload.get("password"), required=True)
    role = _clean_role(payload.get("role"))
    try:
        user = db.create_user(username=username, password=password, role=role)
    except sqlite3.IntegrityError as error:
        raise HTTPException(status_code=409, detail="Tên tài khoản đã tồn tại") from error
    return {"item": user}


@app.patch("/api/users/{user_id}")
def update_user(
    user_id: int,
    payload: dict[str, Any] = Body(default={}),
    session=Depends(require_admin),
) -> dict[str, Any]:
    current_user = db.get_user(user_id)
    if current_user is None:
        raise HTTPException(status_code=404, detail="User không tồn tại")

    username = _clean_username(payload.get("username")) if "username" in payload else None
    password = _clean_password(payload.get("password"), required=False) if "password" in payload else None
    role = _clean_role(payload.get("role")) if "role" in payload else None
    if current_user["role"] == "admin" and role == "user" and db.count_admin_users(exclude_user_id=user_id) == 0:
        raise HTTPException(status_code=400, detail="Không thể hạ quyền admin cuối cùng")

    try:
        user = db.update_user(user_id, username=username, password=password, role=role)
    except sqlite3.IntegrityError as error:
        raise HTTPException(status_code=409, detail="Tên tài khoản đã tồn tại") from error
    if user is None:
        raise HTTPException(status_code=404, detail="User không tồn tại")
    if session["username"] == current_user["username"]:
        session["username"] = user["username"]
        session["role"] = user["role"]
    return {"item": user}


@app.delete("/api/users/{user_id}")
def delete_user(user_id: int, session=Depends(require_admin)) -> dict[str, Any]:
    current_user = db.get_user(user_id)
    if current_user is None:
        raise HTTPException(status_code=404, detail="User không tồn tại")
    if current_user["username"] == session["username"]:
        raise HTTPException(status_code=400, detail="Không thể xóa tài khoản đang đăng nhập")
    if current_user["role"] == "admin" and db.count_admin_users(exclude_user_id=user_id) == 0:
        raise HTTPException(status_code=400, detail="Không thể xóa admin cuối cùng")
    return {"item": db.delete_user(user_id)}


@app.get("/api/mailboxes")
def list_mailboxes(
    status: str = Query("visible"),
    search: str = Query(""),
    _session=Depends(require_admin),
) -> dict[str, Any]:
    return {"items": db.list_aliases(search=search, status=status)}


@app.post("/api/mailboxes")
def create_mailbox(payload: dict[str, Any] = Body(default={}), _session=Depends(require_admin)) -> dict[str, Any]:
    requested_local_part = (payload.get("local_part") or "").strip().lower()
    label = (payload.get("label") or "").strip() or None
    raw_expires_in_hours = payload.get("expires_in_hours")
    expires_in_hours = int(raw_expires_in_hours) if raw_expires_in_hours is not None else settings.default_alias_hours

    if requested_local_part:
        if not is_valid_local_part(requested_local_part):
            raise HTTPException(status_code=400, detail="local_part không hợp lệ")
        local_part = requested_local_part
        source = "manual"
    else:
        local_part = random_local_part()
        source = "generated"

    address = f"{local_part}@{settings.mail_domain}"
    mailbox = db.ensure_alias(address, source=source, label=label, expires_at=_expires_at_from_hours(expires_in_hours))
    return {"item": mailbox}


@app.patch("/api/mailboxes/{alias_id}")
def update_mailbox(alias_id: int, payload: dict[str, Any] = Body(default={}), _session=Depends(require_admin)) -> dict[str, Any]:
    label = payload.get("label")
    status = payload.get("status")
    expires_in_hours = payload.get("expires_in_hours")
    expires_at = _expires_at_from_hours(int(expires_in_hours)) if expires_in_hours is not None else None
    mailbox = db.update_alias(alias_id, label=label, expires_at=expires_at, status=status)
    if mailbox is None:
        raise HTTPException(status_code=404, detail="Mailbox không tồn tại")
    return {"item": mailbox}


@app.post("/api/mailboxes/{alias_id}/expire")
def expire_mailbox(alias_id: int, _session=Depends(require_admin)) -> dict[str, Any]:
    mailbox = db.expire_alias(alias_id)
    if mailbox is None:
        raise HTTPException(status_code=404, detail="Mailbox không tồn tại")
    return {"item": mailbox}


@app.post("/api/mailboxes/{alias_id}/reactivate")
def reactivate_mailbox(alias_id: int, payload: dict[str, Any] = Body(default={}), _session=Depends(require_admin)) -> dict[str, Any]:
    raw_hours = payload.get("expires_in_hours")
    hours = int(raw_hours) if raw_hours is not None else settings.default_alias_hours
    mailbox = db.reactivate_alias(alias_id, hours)
    if mailbox is None:
        raise HTTPException(status_code=404, detail="Mailbox không tồn tại")
    return {"item": mailbox}


@app.delete("/api/mailboxes/{alias_id}")
def delete_mailbox(alias_id: int, _session=Depends(require_admin)) -> dict[str, Any]:
    mailbox = db.delete_alias(alias_id)
    if mailbox is None:
        raise HTTPException(status_code=404, detail="Mailbox không tồn tại")
    return {"item": mailbox}


@app.get("/api/excluded-aliases")
def list_excluded_aliases(
    search: str = Query(default=""),
    _session=Depends(require_admin),
) -> dict[str, Any]:
    return {"items": db.list_excluded_aliases(search=search)}


@app.post("/api/excluded-aliases")
def create_excluded_alias(payload: dict[str, Any] = Body(...), _session=Depends(require_admin)) -> dict[str, Any]:
    address = normalize_address(payload.get("address") or "")
    reason = str(payload.get("reason") or "").strip() or None
    try:
        item = db.create_excluded_alias(address, reason=reason)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    inbox_events.publish([item["address"]])
    return {"item": item}


@app.delete("/api/excluded-aliases/{excluded_alias_id}")
def delete_excluded_alias(excluded_alias_id: int, _session=Depends(require_admin)) -> dict[str, Any]:
    item = db.delete_excluded_alias(excluded_alias_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Alias không tồn tại trong danh sách tự động xoá")
    inbox_events.publish([item["address"]])
    return {"item": item}


@app.get("/api/messages")
def list_messages(
    alias_id: int | None = Query(default=None),
    filter_name: str = Query(default="all"),
    search: str = Query(default=""),
    _session=Depends(require_admin),
) -> dict[str, Any]:
    return {"items": db.list_messages(alias_id=alias_id, filter_name=filter_name, search=search)}


@app.post("/api/messages/send")
def send_new_message(payload: dict[str, Any] = Body(...), _session=Depends(require_admin)) -> dict[str, Any]:
    attachments: list[dict[str, Any]] = []
    try:
        attachments = _decode_outgoing_attachments(payload.get("attachments"))
        result = send_composed_message(
            source_message={},
            mode="send",
            from_value=payload.get("from_alias") or None,
            to_value=payload.get("to", ""),
            cc_value=payload.get("cc", ""),
            subject=payload.get("subject", ""),
            body=payload.get("body", ""),
            attachments=attachments,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        logger.exception("Standalone email delivery failed")
        raise HTTPException(
            status_code=502,
            detail="Gửi mail thất bại. Máy chủ gửi mail chưa chấp nhận yêu cầu.",
        ) from error

    sent_item = db.store_sent_message(
        {
            "source_message_id": None,
            "mode": result["mode"],
            "from_email": result["from"],
            "to": result["to"],
            "cc": result["cc"],
            "subject": result["subject"],
            "body": payload.get("body", ""),
            "attachments": attachments,
            "message_id": result["message_id"],
        }
    )

    return {"ok": True, "item": result, "sent_item": sent_item}


@app.get("/api/debug/message-timings")
def list_debug_message_timings(
    limit: int = Query(default=20, ge=1, le=100),
    _session=Depends(require_admin),
) -> dict[str, Any]:
    return {"items": db.list_recent_message_timings(limit=limit)}


@app.delete("/api/messages")
def delete_messages_in_scope(
    alias_id: int | None = Query(default=None),
    filter_name: str = Query(default="all"),
    search: str = Query(default=""),
    _session=Depends(require_admin),
) -> dict[str, Any]:
    result = db.delete_messages_by_scope(alias_id=alias_id, filter_name=filter_name, search=search)
    if result["deleted_count"]:
        inbox_events.publish(result["recipient_addresses"])
    return {"ok": True, "deleted_count": result["deleted_count"]}


@app.get("/api/sent-messages")
def list_sent_messages(
    search: str = Query(default=""),
    _session=Depends(require_admin),
) -> dict[str, Any]:
    return {"items": db.list_sent_messages(search=search)}


@app.delete("/api/sent-messages")
def delete_sent_messages_in_scope(
    search: str = Query(default=""),
    _session=Depends(require_admin),
) -> dict[str, Any]:
    result = db.delete_sent_messages_by_scope(search=search)
    return {"ok": True, "deleted_count": result["deleted_count"]}


@app.get("/api/messages/{message_id}")
def get_message(message_id: int, _session=Depends(require_admin)) -> dict[str, Any]:
    message = db.get_message(message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Email không tồn tại")
    db.mark_message_read(message_id)
    return {"item": db.get_message(message_id)}


@app.get("/api/sent-messages/{sent_message_id}")
def get_sent_message(sent_message_id: int, _session=Depends(require_admin)) -> dict[str, Any]:
    message = db.get_sent_message(sent_message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Email đã gửi không tồn tại")
    return {"item": message}


@app.get("/api/messages/{message_id}/attachments/{attachment_index}")
def download_message_attachment(
    message_id: int,
    attachment_index: int,
    _session=Depends(require_admin),
) -> Response:
    message = db.get_message(message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Email không tồn tại")
    attachment = _resolve_message_attachment(message, attachment_index)
    if attachment is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy dữ liệu tệp đính kèm")
    return _attachment_response(attachment)


@app.get("/api/sent-messages/{sent_message_id}/attachments/{attachment_index}")
def download_sent_message_attachment(
    sent_message_id: int,
    attachment_index: int,
    _session=Depends(require_admin),
) -> Response:
    message = db.get_sent_message(sent_message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Email đã gửi không tồn tại")
    attachment = db.get_sent_message_attachment(sent_message_id, attachment_index)
    if attachment is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy dữ liệu tệp đính kèm")
    return _attachment_response(attachment)


@app.delete("/api/messages/{message_id}")
def delete_message(message_id: int, _session=Depends(require_admin)) -> dict[str, Any]:
    message = db.delete_message(message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Email không tồn tại")
    inbox_events.publish([message["recipient_address"]])
    return {"item": message}


@app.delete("/api/sent-messages/{sent_message_id}")
def delete_sent_message(sent_message_id: int, _session=Depends(require_admin)) -> dict[str, Any]:
    message = db.delete_sent_message(sent_message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Email đã gửi không tồn tại")
    return {"item": message}


@app.patch("/api/messages/{message_id}/important")
def set_message_important(message_id: int, payload: dict[str, Any] = Body(default={}), _session=Depends(require_admin)) -> dict[str, Any]:
    message = db.set_message_important(message_id, bool(payload.get("important")))
    if message is None:
        raise HTTPException(status_code=404, detail="Email không tồn tại")
    return {"item": message}


@app.post("/api/messages/{message_id}/translate")
def translate_email(message_id: int, payload: dict[str, Any] = Body(default={}), _session=Depends(require_admin)) -> dict[str, Any]:
    message = db.get_message(message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Email không tồn tại")

    try:
        result = translate_message(message, target_language=(payload.get("target_language") or DEFAULT_TARGET_LANGUAGE))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Dịch mail thất bại: {error}") from error

    return {"ok": True, "item": {"message_id": message_id, **result}}


@app.post("/api/messages/{message_id}/send")
def send_message(message_id: int, payload: dict[str, Any] = Body(...), _session=Depends(require_admin)) -> dict[str, Any]:
    message = db.get_message(message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Email không tồn tại")
    mode = (payload.get("mode") or "reply").strip().lower()
    original_attachments = _resolve_message_attachments(message) if mode == "forward" else []

    try:
        uploaded_attachments = _decode_outgoing_attachments(payload.get("attachments"))
        attachments = validate_outgoing_attachments(original_attachments + uploaded_attachments)
        result = send_composed_message(
            source_message=message,
            mode=mode,
            from_value=payload.get("from_alias") or None,
            to_value=payload.get("to", ""),
            cc_value=payload.get("cc", ""),
            subject=payload.get("subject", ""),
            body=payload.get("body", ""),
            attachments=attachments,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        logger.exception("Message delivery failed for message %s", message_id)
        raise HTTPException(
            status_code=502,
            detail="Gửi mail thất bại. Máy chủ gửi mail chưa chấp nhận yêu cầu.",
        ) from error

    sent_item = db.store_sent_message(
        {
            "source_message_id": message["id"],
            "mode": result["mode"],
            "from_email": result["from"],
            "to": result["to"],
            "cc": result["cc"],
            "subject": result["subject"],
            "body": payload.get("body", ""),
            "attachments": attachments,
            "message_id": result["message_id"],
        }
    )

    return {"ok": True, "item": result, "sent_item": sent_item}


@app.get("/api/public/inbox")
def public_list_inbox(alias: str = Query(...), _session=Depends(require_user)) -> dict[str, Any]:
    try:
        address = normalize_lookup_address(alias, settings.mail_domain)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    items = db.list_public_messages(recipient_address=address)
    return {"ok": True, "alias": {"address": address, "message_count": len(items)}, "items": items}


@app.get("/api/public/events")
async def stream_user_events(
    request: Request,
    alias: str = Query(...),
    _session=Depends(require_user),
):
    try:
        address = normalize_lookup_address(alias, settings.mail_domain)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return StreamingResponse(
        _user_event_stream(request, address),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/public/sync")
def public_trigger_sync(_session=Depends(require_user)) -> dict[str, Any]:
    synced = mail_sync.sync_once()
    return {"ok": True, "synced": synced}


@app.get("/api/public/messages/{message_id}")
def public_get_message(message_id: int, alias: str = Query(...), _session=Depends(require_user)) -> dict[str, Any]:
    try:
        address = normalize_lookup_address(alias, settings.mail_domain)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    message = db.get_message_for_address(message_id, address)
    if message is None:
        raise HTTPException(status_code=404, detail="Email không tồn tại cho alias này")

    db.mark_message_read(message_id)
    return {"ok": True, "item": db.get_message_for_address(message_id, address)}


@app.get("/api/public/messages/{message_id}/attachments/{attachment_index}")
def public_download_message_attachment(
    message_id: int,
    attachment_index: int,
    alias: str = Query(...),
    _session=Depends(require_user),
) -> Response:
    try:
        address = normalize_lookup_address(alias, settings.mail_domain)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    message = db.get_message_for_address(message_id, address)
    if message is None:
        raise HTTPException(status_code=404, detail="Email không tồn tại cho alias này")
    attachment = _resolve_message_attachment(message, attachment_index)
    if attachment is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy dữ liệu tệp đính kèm")
    return _attachment_response(attachment)


@app.post("/api/public/messages/{message_id}/translate")
def public_translate_email(
    message_id: int,
    alias: str = Query(...),
    payload: dict[str, Any] = Body(default={}),
    _session=Depends(require_user),
) -> dict[str, Any]:
    try:
        address = normalize_lookup_address(alias, settings.mail_domain)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    message = db.get_message_for_address(message_id, address)
    if message is None:
        raise HTTPException(status_code=404, detail="Email không tồn tại cho alias này")

    try:
        result = translate_message(message, target_language=(payload.get("target_language") or DEFAULT_TARGET_LANGUAGE))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Dịch mail thất bại: {error}") from error

    return {"ok": True, "item": {"message_id": message_id, **result}}


@app.post("/api/sync")
def trigger_sync(_session=Depends(require_admin)) -> dict[str, Any]:
    synced = mail_sync.sync_once()
    return {"ok": True, "synced": synced}


app.mount("/", StaticFiles(directory=settings.frontend_dir, html=True), name="static")
