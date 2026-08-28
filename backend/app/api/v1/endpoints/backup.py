import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.response import success_response
from app.core.auth import require_owner
from app.models.market import Backup
from app.services.backup_service import build_dump, write_backup_file, restore_dump

router = APIRouter()


@router.get("", dependencies=[Depends(require_owner)])
async def get_backups(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Backup).order_by(Backup.created_at.desc()).limit(10))
    items = result.scalars().all()
    return success_response(data=[{"id": b.id, "name": b.backup_name, "type": b.backup_type, "size": b.file_size, "created_at": b.created_at.isoformat() if b.created_at else None} for b in items])


@router.get("/download", dependencies=[Depends(require_owner)])
async def download_backup(db: AsyncSession = Depends(get_db)):
    """Build a full JSON snapshot of the portfolio's data and stream it back
    as a real, downloadable file — also records it in the backups list."""
    # نسخة التنزيل تُضمّن ملفات الكتب (PDF/الغلاف/النصّ) كي تعود المكتبة كاملة
    # عند الاستعادة على سيرفر جديد — بخلاف النسخ الليلية الخفيفة على القرص.
    dump = await build_dump(db, include_files=True)
    payload = json.dumps(dump, ensure_ascii=False, indent=2).encode("utf-8")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    name = f"smart-portfolio-backup-{stamp}.json"

    db.add(Backup(backup_name=name, backup_type="FULL", file_size=len(payload), checksum=dump["checksum"]))
    await db.commit()

    return StreamingResponse(
        iter([payload]),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@router.post("/create")
async def create_backup(db: AsyncSession = Depends(get_db)):
    """Write a real backup file to the server's backup volume (same engine
    as the nightly 02:00 automatic backup) — no longer just a metadata row."""
    info = await write_backup_file(db)
    return success_response(message="Backup created.", data=info)


@router.post("/restore")
async def restore_backup(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    """Restore the portfolio's data from a JSON file produced by /download.
    Verifies the embedded checksum first (nothing is touched on failure),
    replaces all rows in one transaction, then resets the id sequences so
    the next insert can't collide with a restored primary key."""
    raw = await file.read()
    try:
        dump = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="ملف النسخة الاحتياطية غير صالح")

    try:
        await restore_dump(db, dump)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"تعذّرت الاستعادة: {e}")

    return success_response(message="تمت استعادة البيانات بنجاح.")


@router.post("/factory-reset", dependencies=[Depends(require_owner)])
async def factory_reset_endpoint(payload: dict, db: AsyncSession = Depends(get_db)):
    """فورمات كامل: نسخة أمان تلقائية ثم مسح كل بيانات المستخدم وإعادة
    التطبيق لوضعه الأساسي. يتطلب إرسال {"confirm": "فورمات"} حرفياً —
    حاجز أخير ضد الاستدعاء الخاطئ. ملفات النسخ الاحتياطية تبقى سليمة
    وتُستعاد لاحقاً من شاشة الاستعادة."""
    if (payload or {}).get("confirm") != "فورمات":
        raise HTTPException(status_code=400, detail="أرسل كلمة التأكيد «فورمات» للمتابعة.")
    from app.services.backup_service import factory_reset
    try:
        result = await factory_reset(db)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"تعذّر الفورمات: {e}")
    return success_response(
        data=result,
        message="تمت إعادة الضبط. نسخة أمان محفوظة: " + result["safety_backup"],
    )
