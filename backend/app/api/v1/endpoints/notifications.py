from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.core.database import get_db
from app.core.response import success_response
from app.models.market import Notification, NotificationStatus
from datetime import datetime, timezone

router = APIRouter()

@router.get("")
async def get_notifications(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Notification).where(Notification.status != NotificationStatus.ARCHIVED).order_by(Notification.created_at.desc()).limit(50))
    items = result.scalars().all()
    return success_response(data=[{"id": n.id, "title": n.title, "message": n.message, "priority": n.priority, "status": n.status, "created_at": n.created_at.isoformat() if n.created_at else None} for n in items])

# Bulk actions — declared BEFORE the /{notif_id} routes so the literal
# path segments ("read-all", "read") are never captured as an id.
@router.patch("/read-all")
async def mark_all_read(db: AsyncSession = Depends(get_db)):
    """Mark every currently-unread notification as read in one call."""
    res = await db.execute(
        update(Notification)
        .where(Notification.status == NotificationStatus.UNREAD)
        .values(status=NotificationStatus.READ, read_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return success_response(message="تمّت قراءة الكل.", data={"count": res.rowcount})

@router.delete("/read")
async def delete_read(db: AsyncSession = Depends(get_db)):
    """Archive only the already-read notifications — keeps unread ones."""
    res = await db.execute(
        update(Notification)
        .where(Notification.status == NotificationStatus.READ)
        .values(status=NotificationStatus.ARCHIVED)
    )
    await db.commit()
    return success_response(message="تم حذف المقروءة.", data={"count": res.rowcount})

@router.delete("")
async def delete_all(db: AsyncSession = Depends(get_db)):
    """Archive every non-archived notification (unread + read) at once."""
    res = await db.execute(
        update(Notification)
        .where(Notification.status != NotificationStatus.ARCHIVED)
        .values(status=NotificationStatus.ARCHIVED)
    )
    await db.commit()
    return success_response(message="تم حذف الكل.", data={"count": res.rowcount})

@router.patch("/{notif_id}/read")
async def mark_as_read(notif_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Notification).where(Notification.id == notif_id))
    n = result.scalar_one_or_none()
    if n:
        n.status = NotificationStatus.READ
        n.read_at = datetime.now(timezone.utc)
        await db.commit()
    return success_response(message="Marked as read.")

@router.delete("/{notif_id}")
async def delete_notification(notif_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Notification).where(Notification.id == notif_id))
    n = result.scalar_one_or_none()
    if n:
        n.status = NotificationStatus.ARCHIVED
        await db.commit()
    return success_response(message="Notification archived.")
