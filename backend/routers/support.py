"""Support ticket router: create, view, reply, manage status."""
from fastapi import APIRouter, HTTPException, Depends, Query
from datetime import datetime, timezone
from typing import Optional
import logging

from database import db
from utils import generate_id
from dependencies import require_operator, require_admin
from audit import log_audit

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Support"])

VALID_STATUSES = {"open", "in_progress", "resolved", "closed"}
VALID_PRIORITIES = {"low", "medium", "high", "urgent"}


# ─── Operator/Staff Endpoints ──────────────────────────────────────────────────

@router.post("/operator/support/tickets")
async def create_ticket(
    data: dict,
    current_user: dict = Depends(require_operator),
):
    """Create a support ticket."""
    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()
    priority = data.get("priority", "medium")

    if not title:
        raise HTTPException(status_code=400, detail="Title is required")
    if not description:
        raise HTTPException(status_code=400, detail="Description is required")
    if priority not in VALID_PRIORITIES:
        raise HTTPException(status_code=400, detail=f"Priority must be one of {VALID_PRIORITIES}")

    now = datetime.now(timezone.utc)
    ticket_id = generate_id()
    ticket = {
        "id": ticket_id,
        "operator_id": current_user["operator_id"],
        "created_by_user_id": current_user["id"],
        "created_by_name": current_user["name"],
        "created_by_role": current_user["role"],
        "title": title,
        "description": description,
        "priority": priority,
        "status": "open",
        "reply_count": 0,
        "last_reply_at": None,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "deleted_at": None,
    }
    await db.support_tickets.insert_one(ticket)
    ticket.pop("_id", None)
    return ticket


@router.get("/operator/support/tickets")
async def list_operator_tickets(
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
    current_user: dict = Depends(require_operator),
):
    query = {"operator_id": current_user["operator_id"], "deleted_at": None}
    if status and status in VALID_STATUSES:
        query["status"] = status
    tickets = await db.support_tickets.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    total = await db.support_tickets.count_documents(query)
    return {"tickets": tickets, "total": total}


@router.get("/operator/support/tickets/{ticket_id}")
async def get_ticket_detail(
    ticket_id: str,
    current_user: dict = Depends(require_operator),
):
    ticket = await db.support_tickets.find_one(
        {"id": ticket_id, "operator_id": current_user["operator_id"], "deleted_at": None},
        {"_id": 0},
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    replies = await db.support_replies.find({"ticket_id": ticket_id}, {"_id": 0}).sort("created_at", 1).to_list(200)
    return {**ticket, "replies": replies}


@router.post("/operator/support/tickets/{ticket_id}/reply")
async def add_operator_reply(
    ticket_id: str,
    data: dict,
    current_user: dict = Depends(require_operator),
):
    message = (data.get("message") or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")

    ticket = await db.support_tickets.find_one(
        {"id": ticket_id, "operator_id": current_user["operator_id"], "deleted_at": None},
        {"_id": 0},
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if ticket["status"] == "closed":
        raise HTTPException(status_code=400, detail="Cannot reply to a closed ticket")

    now = datetime.now(timezone.utc)
    reply = {
        "id": generate_id(),
        "ticket_id": ticket_id,
        "operator_id": current_user["operator_id"],
        "author_id": current_user["id"],
        "author_name": current_user["name"],
        "author_role": current_user["role"],
        "message": message,
        "created_at": now.isoformat(),
    }
    await db.support_replies.insert_one(reply)
    reply.pop("_id", None)

    await db.support_tickets.update_one(
        {"id": ticket_id},
        {"$set": {"last_reply_at": now.isoformat(), "updated_at": now.isoformat()}, "$inc": {"reply_count": 1}},
    )
    return reply


# ─── Admin Endpoints ───────────────────────────────────────────────────────────

@router.get("/admin/support/tickets")
async def admin_list_tickets(
    skip: int = 0,
    limit: int = 25,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    operator_id: Optional[str] = None,
    search: Optional[str] = None,
    current_user: dict = Depends(require_admin),
):
    query: dict = {"deleted_at": None}
    if status and status in VALID_STATUSES:
        query["status"] = status
    if priority and priority in VALID_PRIORITIES:
        query["priority"] = priority
    if operator_id:
        query["operator_id"] = operator_id
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
        ]

    tickets = await db.support_tickets.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    total = await db.support_tickets.count_documents(query)

    # Enrich with company_name
    enriched = []
    for t in tickets:
        op = await db.operators.find_one({"id": t["operator_id"]}, {"_id": 0, "company_name": 1})
        enriched.append({**t, "company_name": (op or {}).get("company_name", "Unknown")})

    return {"tickets": enriched, "total": total}


@router.get("/admin/support/tickets/stats")
async def admin_ticket_stats(current_user: dict = Depends(require_admin)):
    open_count = await db.support_tickets.count_documents({"status": "open", "deleted_at": None})
    in_progress = await db.support_tickets.count_documents({"status": "in_progress", "deleted_at": None})
    resolved = await db.support_tickets.count_documents({"status": "resolved", "deleted_at": None})
    urgent = await db.support_tickets.count_documents({"priority": "urgent", "status": {"$nin": ["closed", "resolved"]}, "deleted_at": None})
    return {"open": open_count, "in_progress": in_progress, "resolved": resolved, "urgent": urgent}


@router.get("/admin/support/tickets/{ticket_id}")
async def admin_get_ticket(
    ticket_id: str,
    current_user: dict = Depends(require_admin),
):
    ticket = await db.support_tickets.find_one({"id": ticket_id, "deleted_at": None}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    replies = await db.support_replies.find({"ticket_id": ticket_id}, {"_id": 0}).sort("created_at", 1).to_list(200)
    op = await db.operators.find_one({"id": ticket["operator_id"]}, {"_id": 0, "company_name": 1, "email": 1, "phone": 1})
    return {**ticket, "replies": replies, "operator_info": op or {}}


@router.post("/admin/support/tickets/{ticket_id}/reply")
async def admin_reply_ticket(
    ticket_id: str,
    data: dict,
    current_user: dict = Depends(require_admin),
):
    message = (data.get("message") or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")

    ticket = await db.support_tickets.find_one({"id": ticket_id, "deleted_at": None}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if ticket["status"] == "closed":
        raise HTTPException(status_code=400, detail="Cannot reply to a closed ticket")

    now = datetime.now(timezone.utc)
    reply = {
        "id": generate_id(),
        "ticket_id": ticket_id,
        "operator_id": ticket["operator_id"],
        "author_id": current_user["id"],
        "author_name": current_user["name"],
        "author_role": "admin",
        "message": message,
        "created_at": now.isoformat(),
    }
    await db.support_replies.insert_one(reply)
    reply.pop("_id", None)

    # Auto-update status to in_progress if still open
    new_status = "in_progress" if ticket["status"] == "open" else ticket["status"]
    await db.support_tickets.update_one(
        {"id": ticket_id},
        {"$set": {"status": new_status, "last_reply_at": now.isoformat(), "updated_at": now.isoformat()}, "$inc": {"reply_count": 1}},
    )

    await log_audit(
        current_user["id"], current_user["name"], "admin",
        "reply", "support_tickets", ticket_id, {"preview": message[:80]},
        operator_id=ticket["operator_id"],
    )
    return {**reply, "ticket_status": new_status}


@router.put("/admin/support/tickets/{ticket_id}/status")
async def admin_update_ticket_status(
    ticket_id: str,
    data: dict,
    current_user: dict = Depends(require_admin),
):
    new_status = data.get("status")
    if new_status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Status must be one of {VALID_STATUSES}")

    ticket = await db.support_tickets.find_one({"id": ticket_id, "deleted_at": None}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    now = datetime.now(timezone.utc)
    await db.support_tickets.update_one(
        {"id": ticket_id},
        {"$set": {"status": new_status, "updated_at": now.isoformat()}},
    )
    await log_audit(
        current_user["id"], current_user["name"], "admin",
        "update", "support_tickets", ticket_id, {"status": new_status},
        operator_id=ticket["operator_id"],
    )
    return {"id": ticket_id, "status": new_status}
