"""
المكتبة — تخزين كتب PDF واستخراج نصّها مرّة واحدة، ثم توليد «نبذة اليوم»
منها بالذكاء (جيميناي) مع بديل قاعدي دائم الحضور.

مبدأ المشروع محفوظ: لا اختلاق. النبذة تُشتقّ من نصّ الكتاب الفعلي فقط،
ومستشهَدة برقم الصفحة؛ إن غاب جيميناي أو نفدت الحصّة يعمل البديل القاعدي
باقتباسٍ مباشر من الكتاب. النصّ يُستخرج مرّة واحدة عند الرفع (لا نُعيد قراءة
ملفٍ ضخم في كل ضغطة) ويُخزَّن بجوار الـPDF على قرص الفوليوم.
"""

import hashlib
import json
import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

from loguru import logger

# توقيت مكة (UTC+3، بلا توقيت صيفي فالإزاحة ثابتة) — «نبذة اليوم» تُنسَب ليومٍ
# بتوقيت مكة لا UTC، فتتبدّل تمامًا منتصف الليل بمكة لا الساعة الثالثة فجرًا.
_KSA_TZ = timezone(timedelta(hours=3))


def _ksa_today() -> str:
    return datetime.now(_KSA_TZ).date().isoformat()

# علامة فاصلة صريحة بين الصفحات داخل ملف النصّ — لاستعادة رقم الصفحة عند الاستشهاد.
_PAGE_SEP = "\n<<<PAGE>>>\n"

# مجلد التخزين: على السيرفر /app/data/library (فوليوم يبقى، خارج git والحزمة)،
# وفي التطوير مجلد data محلي بجوار الحزمة.
LIBRARY_DIR = Path(
    os.environ.get("LIBRARY_DIR")
    or ("/app/data/library" if os.path.isdir("/app/data") else
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                     "data", "library"))
)


def _paths(book_id: int) -> tuple[Path, Path]:
    """مسارا ملف الـPDF وملف النصّ المستخرَج لكتابٍ ما."""
    return LIBRARY_DIR / f"{book_id}.pdf", LIBRARY_DIR / f"{book_id}.txt"


def pdf_path(book_id: int) -> Path:
    return _paths(book_id)[0]


def cover_path(book_id: int) -> Path:
    return LIBRARY_DIR / f"{book_id}.jpg"


_COVER_WIDTH = 480  # عرض صورة الغلاف — كافٍ للبطاقة وخفيف على القرص/الشبكة


def save_cover(book_id: int) -> bool:
    """يصيّر أول صفحة من الكتاب صورةَ غلافٍ (JPEG) تُعرَض في مقدّمة البطاقة.
    غير قاتل: إن فشل تُستخدَم واجهة افتراضية في الواجهة."""
    try:
        import fitz
        from PIL import Image
        pdf = pdf_path(book_id)
        doc = fitz.open(str(pdf))
        page = doc[0]
        scale = _COVER_WIDTH / max(1.0, page.rect.width)
        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale),
                              colorspace=fitz.csRGB, alpha=False)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        doc.close()
        tmp = cover_path(book_id).with_suffix(".jpg.tmp")
        img.save(str(tmp), "JPEG", quality=82, optimize=True)
        tmp.rename(cover_path(book_id))
        return True
    except Exception as e:
        logger.warning(f"توليد غلاف الكتاب {book_id} فشل (غير قاتل): {e}")
        return False


def compress_pdf_to_temp(book_id: int):
    """يضغط الـPDF **بلا إتلاف** عبر PyMuPDF (تجميع نفايات + deflate + تنظيف)
    إلى ملفٍ مؤقّت دون لمس الأصل. مهم: لا يُعيد ترميز الخطوط ولا يخفّض دقّة
    الصور — فيحافظ على النصّ العربي سليماً تماماً (ضغط Ghostscript `/ebook`
    كان يُفسد الخطوط العربية فتظهر طلاسم). يعيد (مسار المؤقّت, الحجم) عند
    النجاح، أو (None, None) إن تعذّر/لم يصغر. الاستبدال يتمّ بعد اكتمال الاستخراج."""
    pdf = pdf_path(book_id)
    if not pdf.exists():
        return None, None
    try:
        import fitz
    except Exception:
        return None, None
    out = pdf.with_suffix(".pdf.z")
    try:
        doc = fitz.open(str(pdf))
        # حفظ لاسلكيّ الإتلاف: إزالة التكرار وضغط التدفّقات مع الحفاظ على
        # الخطوط والصور كما هي (garbage=4 أقوى تجميع، clean يُصلح البنية).
        doc.save(str(out), garbage=4, deflate=True, deflate_images=True,
                 deflate_fonts=True, clean=True)
        doc.close()
        if out.exists() and 0 < out.stat().st_size < pdf.stat().st_size:
            return out, out.stat().st_size
        out.unlink(missing_ok=True)  # لم يصغر (مضغوط أصلاً) — نُبقي الأصل
        return None, None
    except Exception as e:
        logger.warning(f"ضغط الكتاب {book_id} فشل (غير قاتل): {e}")
        try:
            out.unlink(missing_ok=True)
        except OSError:
            pass
        return None, None


def reader_pages(book_id: int) -> list[str]:
    """صفحات نصّ الكتاب (لوضع «القارئ» الخفيف) — فقط الصفحات ذات المحتوى."""
    return [p.strip() for p in _read_pages(book_id) if p.strip()]


def save_cover_from_bytes(book_id: int, data: bytes) -> bool:
    """يحفظ صورة غلاف مخصّصة يرفعها المالك (بدل الغلاف التلقائي) — يحوّلها JPEG
    ويصغّرها لعرض البطاقة. غير قاتل: يعيد False عند فشل قراءة الصورة."""
    try:
        import io
        from PIL import Image
        img = Image.open(io.BytesIO(data))
        img = img.convert("RGB")
        if img.width > _COVER_WIDTH:
            h = max(1, int(img.height * _COVER_WIDTH / img.width))
            img = img.resize((_COVER_WIDTH, h))
        LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
        tmp = cover_path(book_id).with_suffix(".jpg.tmp")
        img.save(str(tmp), "JPEG", quality=85, optimize=True)
        tmp.rename(cover_path(book_id))
        return True
    except Exception as e:
        logger.warning(f"غلاف مخصّص للكتاب {book_id} فشل: {e}")
        return False


def storage_bytes() -> int:
    """إجمالي حجم ملفات المكتبة على القرص (PDF + نصّ + أغلفة) — لفرض حدّ المساحة."""
    if not LIBRARY_DIR.exists():
        return 0
    return sum(f.stat().st_size for f in LIBRARY_DIR.glob("*") if f.is_file())


def save_pdf(book_id: int, content: bytes) -> None:
    LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
    pdf, _ = _paths(book_id)
    tmp = pdf.with_suffix(".pdf.tmp")
    tmp.write_bytes(content)
    tmp.rename(pdf)  # ذرّي: لا يترك ملفاً نصفَ مكتوب


async def stream_save_upload(upload, max_bytes: int) -> tuple[Path, int]:
    """يحفظ ملفاً مرفوعاً إلى القرص **بالتدفّق (chunks)** بلا تحميله كاملاً في
    الذاكرة — يمنع إنهاك ذاكرة الإنستنس على الكتب الكبيرة (سبب فشل «الحفظ»).
    يُطبّق حدّ الحجم أثناء التدفّق فيُجهض فوراً عند التجاوز. يعيد (مسار مؤقّت,
    الحجم). على المستدعي نقلُه لاسمه النهائي أو حذفه."""
    LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
    import uuid
    tmp = LIBRARY_DIR / f"upload-{uuid.uuid4().hex}.tmp"
    size = 0
    try:
        with open(tmp, "wb") as f:
            while True:
                chunk = await upload.read(1 << 20)  # 1MB
                if not chunk:
                    break
                size += len(chunk)
                if size > max_bytes:
                    f.close()
                    tmp.unlink(missing_ok=True)
                    raise ValueError("OVER_LIMIT")
                f.write(chunk)
    except ValueError:
        raise
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    return tmp, size


def promote_upload(tmp: Path, book_id: int) -> None:
    """ينقل ملفاً مؤقّتاً مرفوعاً إلى اسم الكتاب النهائي <id>.pdf ذرّياً."""
    tmp.replace(pdf_path(book_id))


# حدّ أدنى لطول نصّ الطبقة في الصفحة كي نعدّها «نصّية»؛ دون ذلك (صفحة مصوّرة
# أو غنيّة بالرسوم بلا طبقة نصّ) نلجأ للـOCR العربي.
_MIN_LAYER_CHARS = 120
_OCR_DPI = 300           # دقّة تصيير الصفحة للـOCR — توازن الجودة/السرعة
_OCR_MAX_PAGES = 40      # سقف صفحات الـOCR (يكفي لتدوير نبذة يومية شهوراً؛ يحمي من كتب ضخمة معطوبة)


def _looks_garbled(t: str) -> bool:
    """يكشف طبقة نصّ عربية معطوبة تُخرِج طلاسم: نصّ مخزَّن بأشكال العرض العربية
    (Arabic Presentation Forms) بلا خريطة Unicode سليمة، أو تكرار حرفٍ مكثّف.
    مثل هذه الطبقة نتجاوزها ونعتمد OCR للصفحة (يقرأ الصورة فينتج عربية سليمة)."""
    if not t:
        return False
    letters = 0
    pres = 0        # أحرف أشكال العرض العربية (FB50–FDFF, FE70–FEFF)
    for ch in t:
        o = ord(ch)
        if ch.isalpha():
            letters += 1
        if 0xFB50 <= o <= 0xFDFF or 0xFE70 <= o <= 0xFEFF:
            pres += 1
    if letters and pres / letters > 0.12:
        return True
    # تكرار حرفٍ واحد بكثافة شاذّة (طلاسم «ﻤﻤﻤﻤ»).
    import re as _re
    if _re.search(r"(.)\1{6,}", t):
        return True
    return False


def _ocr_workers() -> int:
    """عدد خيوط الـOCR المتوازية — بعدد الأنوية (بحدّ 4 حمايةً للذاكرة). كل
    خيط يشغّل عملية tesseract فرعية تتوازى فعلياً عبر الأنوية (لا يقيّدها GIL)."""
    try:
        import os as _os
        env = _os.environ.get("LIBRARY_OCR_WORKERS")
        if env:
            return max(1, int(env))
        return max(1, min((_os.cpu_count() or 2), 4))
    except Exception:
        return 2


def _ocr_page_at(pdf_str: str, index: int) -> tuple[int, str]:
    """يفتح الكتاب (نسخة مستقلّة لكل خيط — fitz ليست آمنة للمشاركة)، يصيّر
    الصفحة صورةً، ويقرأ نصّها عبر Tesseract العربي/الإنجليزي. آمن للتوازي."""
    try:
        import fitz
        import pytesseract
        from PIL import Image
        d = fitz.open(pdf_str)
        page = d[index]
        pix = page.get_pixmap(matrix=fitz.Matrix(_OCR_DPI / 72, _OCR_DPI / 72),
                              colorspace=fitz.csRGB, alpha=False)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        d.close()
        return index, (pytesseract.image_to_string(img, lang="ara+eng") or "").strip()
    except Exception as e:
        logger.warning(f"OCR صفحة {index} فشل (غير قاتل): {e}")
        return index, ""


def extract_text(book_id: int) -> tuple[int, bool]:
    """يستخرج **طبقة نصّ كل صفحة** إلى ملف <id>.txt عبر PyMuPDF — فوريّ ويغطّي
    الكتاب كاملاً للكتب ذات الطبقة النصّية السليمة (بلا OCR إطلاقاً). الصفحات
    المعطوبة (طلاسم) أو المصوّرة (بلا نصّ) تُعالَج بـOCR **عند الطلب صفحةً بصفحة**
    وقت اختيارها للنبذة (انظر daily_insight) وتُخزَّن — فالتغطية تشمل أي صفحة في
    الكتاب دون OCR جماعي بطيء. يعيد (عدد الصفحات, has_text). لا يُفشل الرفع."""
    pdf, txt = _paths(book_id)
    try:
        import fitz  # PyMuPDF — استخراج عربي أنظف من pypdf
    except Exception:
        logger.warning("PyMuPDF غير مثبّت — يُستخرج النصّ لاحقاً بعد إعادة بناء صورة backend.")
        return 0, False
    try:
        doc = fitz.open(str(pdf))
        pages = [(p.get_text("text") or "").strip() for p in doc]
        n = doc.page_count
        doc.close()
        txt.write_text(_PAGE_SEP.join(pages), encoding="utf-8")
        # has_text=True ما دام للكتاب صفحات — النبذة متاحة (OCR عند الطلب للمعطوب).
        return n, n > 0
    except Exception as e:
        logger.warning(f"استخراج نصّ الكتاب {book_id} فشل: {e}")
        return 0, False


def page_count(book_id: int) -> int:
    """عدد صفحات الكتاب (سريع عبر PyMuPDF) — يُضبط مبكّراً كي يعمل القارئ فوراً."""
    try:
        import fitz
        doc = fitz.open(str(pdf_path(book_id)))
        n = doc.page_count
        doc.close()
        return n
    except Exception:
        return 0


def render_page_image(book_id: int, index: int, scale: float = 2.0) -> bytes | None:
    """يرسم صفحةً واحدة صورةَ JPEG عبر محرّك MuPDF (يعرض الخطوط العربية أقوى من
    PDF.js) — هذا أساس «القراءة»: يتجاوز مشاكل تفكّك الحروف في متصفّح المستخدم.
    يُستدعى عند الطلب صفحةً بصفحة (كسول) ويُخبّئه المتصفح. None خارج النطاق."""
    try:
        import fitz
        doc = fitz.open(str(pdf_path(book_id)))
        if index < 0 or index >= doc.page_count:
            doc.close()
            return None
        page = doc[index]
        s = max(1.0, min(4.0, scale))
        pix = page.get_pixmap(matrix=fitz.Matrix(s, s), colorspace=fitz.csRGB, alpha=False)
        data = pix.tobytes("jpeg", jpg_quality=82)
        doc.close()
        return data
    except Exception as e:
        logger.warning(f"رسم صفحة الكتاب {book_id}/{index} فشل: {e}")
        return None


def _write_page_cache(book_id: int, index: int, text: str) -> None:
    """يحدّث نصّ صفحةٍ واحدة داخل <id>.txt (بعد OCRها عند الطلب) كي لا يُعاد OCRها
    مستقبلاً — فتتراكم التغطية تدريجياً على كامل الكتاب."""
    _, txt = _paths(book_id)
    try:
        parts = txt.read_text(encoding="utf-8").split(_PAGE_SEP) if txt.exists() else []
        while len(parts) <= index:
            parts.append("")
        parts[index] = text
        txt.write_text(_PAGE_SEP.join(parts), encoding="utf-8")
    except Exception as e:
        logger.warning(f"تحديث كاش صفحة الكتاب {book_id}/{index} فشل: {e}")


def _read_pages(book_id: int) -> list[str]:
    _, txt = _paths(book_id)
    if not txt.exists():
        return []
    return txt.read_text(encoding="utf-8").split(_PAGE_SEP)


def delete_files(book_id: int) -> None:
    for p in (*_paths(book_id), cover_path(book_id)):
        try:
            p.unlink()
        except OSError:
            pass


# ── نبذة اليوم ────────────────────────────────────────────────

# صفحات «حواشي النشر» التي لا تصلح كنبذة يومية (إحراج): حقوق الطبع/الناشر/
# الإيداع/الفهرس/الإهداء. تُستبعَد من ترشيح النبذة حتى لا تُعرَض «نبذة» عن
# حقوق المؤلف أو قائمة المحتويات بدل فكرة حقيقية من متن الكتاب.
_BOILERPLATE_MARKERS = (
    "جميع الحقوق محفوظة", "حقوق الطبع", "حقوق النشر", "حقوق محفوظة",
    "حقوق الملكية", "رقم الإيداع", "ردمك", "isbn", "دار النشر", "دار للنشر",
    "الطبعة الأولى", "الطبعة الثانية", "الطبعة الثالثة", "الطبعة الرابعة",
    "لا يجوز إعادة", "لا يُسمح", "لا يسمح بإعادة", "يُمنع نسخ", "all rights reserved",
    "copyright", "مكتبة الملك فهد الوطنية", "فهرسة أثناء النشر", "الترقيم الدولي",
)


def _is_boilerplate(text: str) -> bool:
    """صفحة حواشي نشر (حقوق/إيداع/ناشر) أو فهرس محتويات — لا تصلح للنبذة."""
    t = (text or "").lower()
    if any(m in t for m in _BOILERPLATE_MARKERS):
        return True
    # فهرس المحتويات: أسطر كثيرة تنتهي برقم صفحة أو بها نقاط ربط (........)
    lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
    if lines:
        toc_like = sum(1 for ln in lines if ".." in ln or re.search(r"\d{1,4}$", ln))
        if len(lines) >= 6 and toc_like / len(lines) >= 0.6:
            return True
    return False


def _candidate_indices(pages: list[str]) -> list[int]:
    """فهارس الصفحات المرشّحة للنبذة — تغطّي متن الكتاب (لا حواشي النشر):
    - صفحات ذات طبقة نصّ سليمة كافية وليست حقوق طبع/فهرس (المسار الأمثل).
    - إن غابت (كتاب معطوب/ممسوح) → صفحات ذات حبرٍ كافٍ (نصّ معطوب طويل).
    - إن لم يوجد نصّ إطلاقاً (ممسوح خالص) → كل الصفحات عدا القليلة الأولى/الأخيرة
      (تُقرأ بالـOCR عند الطلب)."""
    good = [i for i, t in enumerate(pages)
            if len(t) >= 400 and not _looks_garbled(t) and not _is_boilerplate(t)]
    if good:
        return good
    inky = [i for i, t in enumerate(pages) if len(t) >= 200 and not _is_boilerplate(t)]
    if inky:
        return inky
    n = len(pages)
    return list(range(2, n - 2)) if n > 4 else list(range(n))


_INSIGHT_SLOTS = 3


def _slot_page(cands: list[int], book_id: int, slot: int, slots: int = _INSIGHT_SLOTS) -> int:
    """صفحة الفرصة (slot) — نطاقات منفصلة تضمن عدم تكرار نفس الصفحة بين الفرص
    الثلاث وتغطية عرض الكتاب. المرشّحات مرتّبة تصاعديّاً، فالنطاق ٠ بداية الكتاب،
    و١ وسطه، و٢ نهايته. الاختيار داخل النطاق حتميّ يوميّاً."""
    n = len(cands)
    slot = max(0, int(slot))
    if n <= slots:
        return cands[slot % n]   # مرشّحات قليلة: لا مفرّ من الدوران
    band = n // slots
    lo = slot * band
    hi = (slot + 1) * band if slot < slots - 1 else n
    seg = cands[lo:hi] or cands
    seed = int(hashlib.sha256(f"{book_id}:{_ksa_today()}:{slot}".encode()).hexdigest(), 16)
    return seg[seed % len(seg)]


def _trim_passage(text: str) -> str:
    snippet = text[:1800]
    m = re.search(r"[\.!؟\n]\s", snippet[600:])
    if m:
        snippet = snippet[: 600 + m.start() + 1]
    return snippet.strip()


def _rule_based_insight(title: str, passage: str, page: int) -> dict:
    """بديل قاعديّ دائم الحضور: يقتبس من الكتاب حرفياً ويؤطّره — بلا اختلاق
    وبلا اعتماد على أي API. يعمل حين يغيب جيميناي أو تنفد الحصّة."""
    sentences = [s.strip() for s in re.split(r"(?<=[\.!؟])\s+|\n+", passage) if len(s.strip()) >= 30]
    points = sentences[:3]
    idea = sentences[0] if sentences else passage[:160]
    return {
        "idea": idea,
        "points": points,
        "reflection": "كيف تُطبّق فكرة اليوم من هذا الكتاب على قرار استثماري تواجهه الآن؟",
        "quote": passage,
        "page": page,
        "source": "rule",
    }


async def daily_insight(book, slot: int = 0) -> dict:
    """نبذة اليوم لكتابٍ ما — مخبوءة ليومٍ كامل لكل «فرصة» (slot). ثلاث فرص
    يوميّاً (لمبات) تختار **صفحاتٍ مختلفة** من كامل الكتاب، كي يعوّض المستخدم أي
    نبذةٍ وقعت على صفحةٍ غير مفيدة (غلاف/فهرس/ناشر). تغطّي الكتاب كاملاً؛ الصفحات
    المعطوبة/الممسوحة تُقرأ بالـOCR عند الطلب وتُخزَّن. جيميناي أولاً وبديل قاعدي."""
    import asyncio
    from app.services import cache

    slot = max(0, int(slot))
    ck = f"library:insight:{book.id}:{_ksa_today()}:{slot}"
    cached = cache.get(ck)
    if cached is not None:
        return cached

    pages = _read_pages(book.id)
    cands = _candidate_indices(pages)
    if not cands:
        return {"idea": "لم يُستخرَج نصّ هذا الكتاب بعد.", "points": [], "reflection": "",
                "quote": "", "page": 0, "source": "none", "title": book.title}

    # اختيار صفحة الفرصة: نقسّم المرشّحات إلى ثلاث نطاقات منفصلة (بداية/وسط/
    # نهاية الكتاب) ونختار صفحةً من نطاق الـslot — فالنبذ الثلاث **من صفحات
    # مختلفة حتماً** (لا تكرار لنفس الصفحة) وتغطّي الكتاب بعرضه.
    idx = _slot_page(cands, book.id, slot)
    text = pages[idx] if idx < len(pages) else ""

    # إن كان نصّ الصفحة معطوباً أو قصيراً → OCR لهذه الصفحة فقط عند الطلب + تخزين.
    if _looks_garbled(text) or len(text) < 200:
        try:
            _, ocr = await asyncio.to_thread(_ocr_page_at, str(pdf_path(book.id)), idx)
        except Exception:
            ocr = ""
        if ocr and (len(ocr) > len(text) or _looks_garbled(text)):
            text = ocr
            _write_page_cache(book.id, idx, ocr)  # تتراكم التغطية

    passage = _trim_passage(text)
    page = idx + 1
    if not passage:
        return {"idea": "لم يُستخرَج نصّ هذه الصفحة.", "points": [], "reflection": "",
                "quote": "", "page": page, "source": "none", "title": book.title}

    result = await _gemini_insight(book.title, passage, page)
    if result is None:
        result = _rule_based_insight(book.title, passage, page)
    result["title"] = book.title
    result["slot"] = slot
    cache.set(ck, result, 60 * 60 * 24)  # يوم كامل
    return result


async def _gemini_insight(title: str, passage: str, page: int) -> dict | None:
    """يلخّص المقطع بجيميناي إلى نبذة عربية عملية. يعيد None عند غياب المفتاح/
    الحصّة/أي فشل كي يتولّى البديل القاعدي."""
    import httpx
    from app.core.config import settings

    if not settings.AI_API_KEY:
        return None
    from app.services.usage_tracker import can_call, record
    if not can_call("gemini"):
        logger.warning("Gemini: بلغت الحصّة اليومية — نبذة المكتبة تُبنى قاعدياً.")
        return None

    prompt = f"""أنت مُرشد قراءة محترف. بين يديك مقطع حرفيّ من كتاب «{title}» (صفحة {page}).
اقرأ المقطع واستخرج «نبذة اليوم» مفيدة تنير عقل القارئ وتُسرّع تعلّمه، مستندة إلى
المقطع فقط دون أي إضافة من خارجه. أعد JSON فقط بلا أي شرح بهذا الشكل:
{{"idea": "فكرة اليوم في جملة واحدة قوية", "points": ["نقطة عملية 1", "نقطة 2", "نقطة 3"], "reflection": "سؤال تأمّل واحد يربط الفكرة بقرار عملي"}}

المقطع:
\"\"\"{passage}\"\"\""""

    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{settings.AI_MODEL}:generateContent?key={settings.AI_API_KEY}")
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.5, "maxOutputTokens": 1024}}
    try:
        record("gemini")
        async with httpx.AsyncClient(timeout=40) as client:
            r = await client.post(url, json=body)
        if r.status_code != 200:
            logger.warning(f"نبذة المكتبة: HTTP {r.status_code} — {r.text[:150]}")
            return None
        text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            return None
        obj = json.loads(m.group(0))
        idea = str(obj.get("idea") or "").strip()
        points = [str(p).strip() for p in (obj.get("points") or []) if str(p).strip()]
        if not idea:
            return None
        return {
            "idea": idea,
            "points": points[:3],
            "reflection": str(obj.get("reflection") or "").strip(),
            "quote": passage,
            "page": page,
            "source": "gemini",
        }
    except Exception as e:
        logger.warning(f"نبذة المكتبة عبر جيميناي فشلت: {e}")
        return None
