"""
المكتبة — كتب PDF مع معاينة/تحميل + «زر الذكاء» الذي يعطي نبذة يومية مستقاة
من نصّ الكتاب نفسه (استُخرج مرّة واحدة عند الرفع). لا اختلاق: كل نبذة
مستشهَدة بصفحة فعلية، وللبديل القاعدي عند غياب جيميناي.
"""

import asyncio
import os

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from loguru import logger

from app.core.database import get_db, AsyncSessionLocal
from app.core.response import success_response
from app.models.market import LibraryBook
from app.services import library_service as lib

router = APIRouter()


async def _process_book(book_id: int) -> None:
    """معالجة خلفية على مرحلتين كي لا يعلَق الكتاب في «جارٍ التحضير»:
      (١) الغلاف + الضغط اللاإتلافي (سريع) → ready=True فوراً، فتُتاح القراءة
          والتحميل حالاً (لا يحتاجان النصّ إطلاقاً — يعرضان صفحات الـPDF).
      (٢) استخراج النصّ/OCR (قد يطول للكتب المعطوبة) → has_text لاحقاً، وهو
          المطلوب فقط لـ«نبذة اليوم». الضغط لاإتلافي فالاستخراج من المضغوط مطابق.
    كلّ عمل ثقيل في خيط منفصل كي لا يحجب حلقة الأحداث."""
    import asyncio
    # ── المرحلة ١: قابل للقراءة فوراً ──
    try:
        await asyncio.to_thread(lib.save_cover, book_id)
    except Exception as e:
        logger.warning(f"غلاف الكتاب {book_id} فشل: {e}")
    new_size = None
    try:
        ctmp, csize = await asyncio.to_thread(lib.compress_pdf_to_temp, book_id)
        if ctmp is not None:
            ctmp.replace(lib.pdf_path(book_id))
            new_size = csize
            logger.info(f"الكتاب {book_id}: ضُغط إلى {csize} بايت.")
    except Exception as e:
        logger.warning(f"ضغط الكتاب {book_id} فشل: {e}")
    try:
        pc = await asyncio.to_thread(lib.page_count, book_id)
    except Exception:
        pc = 0
    async with AsyncSessionLocal() as db:
        book = (await db.execute(select(LibraryBook).where(LibraryBook.id == book_id))).scalar_one_or_none()
        if book is None:
            return
        if new_size:
            book.file_size = new_size
        if pc:
            book.page_count = pc   # كي يعمل القارئ فوراً (صور الصفحات)
        book.ready = True   # القراءة/التحميل متاحة الآن
        await db.commit()

    # ── المرحلة ٢: استخراج النصّ للنبذة (لا يعيق القراءة) ──
    try:
        pages, has_text = await asyncio.to_thread(lib.extract_text, book_id)
    except Exception as e:
        logger.warning(f"استخراج نصّ الكتاب {book_id} فشل: {e}")
        pages, has_text = 0, False
    async with AsyncSessionLocal() as db:
        book = (await db.execute(select(LibraryBook).where(LibraryBook.id == book_id))).scalar_one_or_none()
        if book is None:
            return
        book.page_count = pages or None
        book.has_text = has_text
        await db.commit()

# ── حدود واضحة تحمي السيرفر (قابلة للضبط بمتغيّرات بيئة) ──────────────
MAX_FILE_MB = int(os.environ.get("LIBRARY_MAX_FILE_MB", "60"))      # حجم الكتاب الواحد
MAX_BOOKS = int(os.environ.get("LIBRARY_MAX_BOOKS", "50"))          # عدد الكتب
MAX_TOTAL_MB = int(os.environ.get("LIBRARY_MAX_TOTAL_MB", "256"))   # إجمالي مساحة المكتبة (256 لكل نسخة — آمن على قرص ضيّق)
MAX_BYTES = MAX_FILE_MB * 1024 * 1024
MAX_TOTAL_BYTES = MAX_TOTAL_MB * 1024 * 1024


def _book_dto(b: LibraryBook) -> dict:
    return {
        "id": b.id,
        "title": b.title,
        "author": b.author,
        "page_count": b.page_count,
        "file_size": b.file_size,
        "has_text": bool(b.has_text),
        "has_cover": lib.cover_path(b.id).exists(),
        # نسخة الغلاف (mtime) لكسر كاش المتصفح عند تغييره.
        "cover_ver": int(lib.cover_path(b.id).stat().st_mtime) if lib.cover_path(b.id).exists() else 0,
        "ready": bool(b.ready),
        "created_at": b.created_at.isoformat() if b.created_at else None,
    }


@router.get("")
async def list_books(db: AsyncSession = Depends(get_db)):
    # الترتيب اليدوي أولاً (position تصاعدياً) ثم الأحدث للمتساوين/الجدد.
    rows = (await db.execute(
        select(LibraryBook).order_by(LibraryBook.position.asc(), LibraryBook.created_at.desc())
    )).scalars().all()
    used = lib.storage_bytes()
    return success_response(data={
        "books": [_book_dto(b) for b in rows],
        "limits": {
            "count": len(rows), "max_books": MAX_BOOKS,
            "used_mb": round(used / 1024 / 1024, 1), "max_total_mb": MAX_TOTAL_MB,
            "max_file_mb": MAX_FILE_MB,
        },
    })


@router.post("/upload")
async def upload_book(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    author: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="الملف يجب أن يكون PDF.")
    if not (title or "").strip():
        raise HTTPException(status_code=400, detail="عنوان الكتاب مطلوب.")

    # حدّ العدد قبل قبول أي بايت.
    count = (await db.execute(select(func.count(LibraryBook.id)))).scalar() or 0
    if count >= MAX_BOOKS:
        raise HTTPException(status_code=409, detail=f"بلغت المكتبة الحدّ الأقصى للكتب ({MAX_BOOKS}). احذف كتاباً أولاً.")

    # حفظ متدفّق للقرص بلا تحميل الملف كاملاً في الذاكرة (يمنع فشل الحفظ/نفاد
    # الذاكرة على الكتب الكبيرة). يُطبَّق حدّ الحجم أثناء التدفّق.
    try:
        tmp_path, size = await lib.stream_save_upload(file, MAX_BYTES)
    except ValueError:
        raise HTTPException(status_code=413, detail=f"حجم الكتاب يتجاوز الحدّ المسموح ({MAX_FILE_MB}MB).")
    if size == 0:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="الملف فارغ.")
    if lib.storage_bytes() + size > MAX_TOTAL_BYTES:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=409, detail=f"لا مساحة كافية في المكتبة (الحدّ {MAX_TOTAL_MB}MB). احذف كتباً أولاً.")

    # نُنشئ الصفّ للحصول على id ثابت، ثم ننقل الملف المؤقّت لاسمه النهائي.
    book = LibraryBook(title=title.strip(), author=(author or "").strip() or None,
                       filename="", file_size=size, ready=False)
    db.add(book)
    await db.flush()  # يملأ book.id دون إنهاء المعاملة
    lib.promote_upload(tmp_path, book.id)
    book.filename = f"{book.id}.pdf"
    await db.commit()
    await db.refresh(book)

    # كل ما يطول (غلاف + استخراج + ضغط) في الخلفية — الرفع يعود فوراً بعد
    # حفظ البايتات، فلا يفشل «الحفظ» ولا يعلَق الوسيط.
    background.add_task(_process_book, book.id)
    return success_response(data=_book_dto(book), message="تمت إضافة الكتاب — يُجهَّز الآن.")


@router.post("/reorder")
async def reorder_books(payload: dict, db: AsyncSession = Depends(get_db)):
    """يضبط الترتيب اليدوي للكتب من قائمة معرّفات مرتَّبة كما يريدها المالك."""
    ids = (payload or {}).get("ids")
    if not isinstance(ids, list) or not ids:
        raise HTTPException(status_code=400, detail="قائمة الترتيب غير صالحة.")
    rows = (await db.execute(select(LibraryBook))).scalars().all()
    by_id = {b.id: b for b in rows}
    pos = 0
    for bid in ids:
        b = by_id.get(bid)
        if b is not None:
            b.position = pos
            pos += 1
    # أي كتب غير مذكورة (نادر) تُوضَع بعدها بترتيبها الحالي.
    for b in rows:
        if b.id not in ids:
            b.position = pos
            pos += 1
    await db.commit()
    return success_response(message="تم حفظ الترتيب.")


@router.get("/{book_id}/file")
async def book_file(book_id: int, download: bool = False, db: AsyncSession = Depends(get_db)):
    book = (await db.execute(
        select(LibraryBook).where(LibraryBook.id == book_id)
    )).scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=404, detail="الكتاب غير موجود.")
    path = lib.pdf_path(book_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="ملف الكتاب غير موجود على القرص.")
    # ترويسات HTTP تقبل latin-1 فقط؛ اسم الكتاب العربي يكسر الاستجابة. نستخدم
    # اسماً ASCII احتياطياً + النسخة المُرمَّزة UTF-8 (RFC 5987) للاسم العربي.
    from urllib.parse import quote
    disposition = "attachment" if download else "inline"
    utf8_name = quote(f"{(book.title or f'book-{book_id}')}.pdf")
    cd = f"{disposition}; filename=\"book-{book_id}.pdf\"; filename*=UTF-8''{utf8_name}"
    return FileResponse(str(path), media_type="application/pdf",
                        headers={"Content-Disposition": cd})


@router.post("/{book_id}/cover")
async def set_cover(book_id: int, file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    """رفع صورة غلاف مخصّصة من جهاز المالك تحلّ محلّ الغلاف التلقائي."""
    book = (await db.execute(
        select(LibraryBook).where(LibraryBook.id == book_id)
    )).scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=404, detail="الكتاب غير موجود.")
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(status_code=400, detail="الملف يجب أن يكون صورة.")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="الصورة فارغة.")
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="حجم الصورة كبير (الحدّ 15MB).")
    if not lib.save_cover_from_bytes(book_id, data):
        raise HTTPException(status_code=400, detail="تعذّرت معالجة الصورة — جرّب صورة أخرى.")
    return success_response(data=_book_dto(book), message="تم تحديث الغلاف.")


@router.get("/{book_id}/cover")
async def book_cover(book_id: int, db: AsyncSession = Depends(get_db)):
    path = lib.cover_path(book_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="لا غلاف لهذا الكتاب.")
    return FileResponse(str(path), media_type="image/jpeg",
                        headers={"Cache-Control": "public, max-age=86400"})


@router.get("/{book_id}/reader")
async def book_reader(book_id: int, db: AsyncSession = Depends(get_db)):
    """وضع «القارئ»: صفحات نصّ الكتاب خفيفةً وقابلة لإعادة التدفّق — تصفّح
    سلس وسريع على الجوّال بلا تحميل الـPDF الثقيل."""
    book = (await db.execute(
        select(LibraryBook).where(LibraryBook.id == book_id)
    )).scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=404, detail="الكتاب غير موجود.")
    if not book.ready:
        raise HTTPException(status_code=409, detail="الكتاب قيد التحضير.")
    pages = lib.reader_pages(book_id)
    if not pages:
        raise HTTPException(status_code=422, detail="لا نصّ متاح لهذا الكتاب للقراءة.")
    return success_response(data={"title": book.title, "author": book.author, "pages": pages})


@router.get("/{book_id}/page/{page_no}")
async def book_page(book_id: int, page_no: int, scale: float = 2.0, db: AsyncSession = Depends(get_db)):
    """صورة صفحةٍ مرسومة خادمياً عبر MuPDF (أساس «القراءة» — عرض عربي أقوى من
    PDF.js يتجاوز تفكّك الحروف). كسول + يُخبّئه المتصفح."""
    import asyncio
    exists = (await db.execute(
        select(LibraryBook.id).where(LibraryBook.id == book_id)
    )).scalar_one_or_none()
    if not exists:
        raise HTTPException(status_code=404, detail="الكتاب غير موجود.")
    data = await asyncio.to_thread(lib.render_page_image, book_id, page_no - 1, scale)
    if not data:
        raise HTTPException(status_code=404, detail="الصفحة غير متاحة.")
    return Response(content=data, media_type="image/jpeg",
                    headers={"Cache-Control": "public, max-age=86400"})


@router.get("/{book_id}/insight")
async def book_insight(book_id: int, slot: int = 0, db: AsyncSession = Depends(get_db)):
    book = (await db.execute(
        select(LibraryBook).where(LibraryBook.id == book_id)
    )).scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=404, detail="الكتاب غير موجود.")
    if not book.has_text:
        try:
            pages, has = await asyncio.to_thread(lib.extract_text, book_id)
        except Exception:
            pages, has = 0, False
        if has:
            book.page_count = pages or book.page_count
            book.has_text = True
            await db.commit()
    # لا نُفشل الطلب أبداً — daily_insight تُرجع نتيجةً دائماً (OCR عند الطلب
    # + بديل قاعدي)؛ أي استثناء يُترجَم لرسالة لطيفة بدل «تعذّر تحميل النبذة».
    try:
        data = await lib.daily_insight(book, slot=slot)
    except Exception as e:
        logger.warning(f"نبذة الكتاب {book_id} فشلت: {e}")
        data = {"idea": "تعذّر تجهيز نبذة اليوم — أعد المحاولة بعد قليل.",
                "points": [], "reflection": "", "quote": "", "page": 0,
                "source": "none", "title": book.title}
    return success_response(data=data)


@router.delete("/{book_id}")
async def delete_book(book_id: int, db: AsyncSession = Depends(get_db)):
    book = (await db.execute(
        select(LibraryBook).where(LibraryBook.id == book_id)
    )).scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=404, detail="الكتاب غير موجود.")
    await db.delete(book)
    await db.commit()
    lib.delete_files(book_id)
    return success_response(message="تم حذف الكتاب.")
