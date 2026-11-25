"""‏D586: المكتبةُ موادُّ الطيار الآليّ الدراسية — من كلّ كتابٍ مبادئُه الاستثمارية بأرقام صفحاتها.

بأمر المالك: «كتبٌ في المكتبة، أريده أن يشربها ويفكّر كأنه متخرّج وكانت المكتبةُ موادَّه الدراسية».
فيُستخلص من نصّ كلّ كتابٍ (المستخرَج عند رفعه) مبادئُه في القيمة والتوقيت والمخاطر والسلوك وبناء المحفظة —
جملةً قصيرةً لكلّ مبدأ مع رقم الصفحة التي جاء منها — وتُحفظ مرّةً، ويستشهد بها الطيارُ الآليّ.
لا اختلاق: المبدأ من نصّ الكتاب وحده، ورقمُ صفحته يُتحقَّق من وجوده.
"""
from __future__ import annotations

from loguru import logger

STORE = "lib:wisdom:{}"
MAX_CHARS = 180_000          # نحو ستّين ألفَ رمز — في سعة النموذج بارتياح


def _sample(pages: list[str]) -> str:
    """الكتابُ كلُّه إن اتّسع، وإلا صفحاتٌ موزّعةٌ بانتظام على طوله — كلٌّ بعلامة رقمها."""
    marked = [(i + 1, " ".join((p or "").split())) for i, p in enumerate(pages)]
    marked = [(n, t) for n, t in marked if len(t) > 200]
    total = sum(len(t) for _, t in marked)
    if total > MAX_CHARS and marked:
        step = total / MAX_CHARS
        keep, acc = [], 0.0
        for n, t in marked:
            acc += 1
            if acc >= step:
                keep.append((n, t))
                acc -= step
        marked = keep
    out, size = [], 0
    for n, t in marked:
        if size + len(t) > MAX_CHARS:
            break
        out.append(f"[صفحة {n}] {t}")
        size += len(t)
    return "\n".join(out)


async def digest(book) -> dict | None:
    """يستخلص مبادئ كتابٍ واحد ويحفظها — أو يعيد المحفوظ."""
    from app.services import lastgood
    from app.services.library_service import _read_pages
    key = STORE.format(book.id)
    old = lastgood.load(key)
    if old and old.get("principles"):
        return old
    pages = _read_pages(book.id)
    from app.services.library_service import _looks_garbled
    good = [p for p in pages if len((p or "").strip()) > 200 and not _looks_garbled(p)]
    # ‏D586 بأمر المالك: «بعضُ الكتب صورٌ لا يخرج نصُّها، وبعضُها رموز» — فتُقرأ بصرياً
    if not pages or len(good) < 0.3 * max(1, len(pages)) or sum(len(p) for p in good) < 20_000:
        return await digest_visual(book, len(pages))
    pages = [p if (p in good) else "" for p in pages]
    text = _sample(pages)
    if len(text) < 2000:
        return None
    from app.services.ai_content import _generate_obj
    prompt = f"""أنت طالبُ استثمارٍ متفوّق تدرس كتاب «{book.title}»{f' لـ{book.author}' if book.author else ''}.
استخلص منه المبادئَ التي يعمل بها مديرُ محفظةٍ محترف: التقييمُ والقيمة، وتوقيتُ الدخول والخروج، والمخاطرُ وحمايةُ رأس المال،
وسلوكُ المستثمر وأخطاؤه، وبناءُ المحفظة والتنويعُ والتركيز، والتوزيعاتُ والعائدُ المركّب.

قواعدُ ملزمة:
- كلُّ مبدأ من نصّ الكتاب أدناه وحده، لا من معرفتك العامة. وإن لم تجد في النصّ مبدأً لصنفٍ فلا تكتب له شيئاً.
- كلُّ مبدأ جملةٌ واحدةٌ قصيرة (لا تزيد على عشرين كلمة)، بصيغة قاعدةٍ تُطبَّق: «لا تشترِ…»، «اشترِ حين…».
- اذكر رقمَ الصفحة التي جاء منها كما في علامة [صفحة N].
- بين اثني عشر وعشرين مبدأ، الأهمُّ أوّلاً.

النصّ:
{text}

أعد JSON فقط:
{{"principles": [{{"p": "المبدأ", "page": 12, "kind": "قيمة|توقيت|مخاطر|سلوك|محفظة|توزيعات"}}]}}"""
    obj = await _generate_obj(prompt, f"ai:libwisdom:v1:{book.id}", 365 * 24 * 3600)
    items = (obj or {}).get("principles") or []
    valid_pages = {i + 1 for i, p in enumerate(pages) if len((p or "").strip()) > 200}
    clean = []
    for it in items:
        p = " ".join(str((it or {}).get("p") or "").split())
        try:
            pg = int((it or {}).get("page"))
        except (TypeError, ValueError):
            continue
        if p and pg in valid_pages and len(p.split()) <= 26:
            clean.append({"p": p, "page": pg, "kind": (it or {}).get("kind") or ""})
    if not clean:
        logger.warning(f"المكتبة: لم يُستخلص مبدأٌ موثَّقٌ من «{book.title}»")
        return None
    rec = {"book_id": book.id, "title": book.title, "author": book.author, "principles": clean[:20]}
    lastgood.save(key, rec)
    return rec


async def digest_all() -> dict:
    """كلُّ كتابٍ جاهزٍ بنصّه لم يُدرَس بعد — يُدرَس مرّةً ويبقى."""
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.market import LibraryBook
    async with AsyncSessionLocal() as db:
        books = (await db.execute(select(LibraryBook).where(LibraryBook.ready.is_(True), LibraryBook.has_text.is_(True))
                                  .execution_options(skip_portfolio_scope=True))).scalars().all()
    rep = {"books": len(books), "digested": 0, "failed": [], "saqr": 0, "saqr_failed": []}
    for b in books:
        try:
            r = await digest(b)
            if r:
                rep["digested"] += 1
            else:
                rep["failed"].append(b.title)
        except Exception as e:                                    # noqa: BLE001
            rep["failed"].append(f"{b.title}: {type(e).__name__}")
        try:                                                      # ‏D833: وصقرٌ يدرس الكتابَ نفسَه بعين المتداول
            if await saqr_digest(b):
                rep["saqr"] += 1
            else:
                rep["saqr_failed"].append(b.title)
        except Exception as e:                                    # noqa: BLE001
            rep["saqr_failed"].append(f"{b.title}: {type(e).__name__}")
    logger.info(f"المكتبة — المبادئ: {rep}")
    return rep


VISUAL_MAX_MB = 45                 # حدُّ «ملفّات» النموذج للـPDF خمسون — ويُترك هامش


async def digest_visual(book, n_pages: int = 0, prompt: str | None = None, store: str = STORE, keep: int = 20) -> dict | None:
    """قراءةٌ بصريةٌ لكتابٍ مصوَّرٍ أو نصُّه طلاسم — بطريقة القارئ البصريّ الخفيفة نفسِها (D565):
    يُرفع الملفُّ من القرص قطعاً فلا يُحمَل في الذاكرة، ويُحذف بعد القراءة، ولا يبدأ إن ضاقت الذاكرة."""
    import os
    from app.services import lastgood
    from app.services.library_service import pdf_path
    from app.services.file_reader import _upload, _forget, _trim, MIN_FREE_MB
    from app.services.tadawul_pdf import mem_available_mb
    from app.core.config import settings
    from app.services.usage_tracker import can_call, record
    path = str(pdf_path(book.id))
    if not os.path.exists(path):
        return None
    if os.path.getsize(path) > VISUAL_MAX_MB * 1024 * 1024:
        logger.warning(f"المكتبة: «{book.title}» أكبر من {VISUAL_MAX_MB}MB — لا يُقرأ بصرياً")
        return None
    free = mem_available_mb()
    if free is not None and free < MIN_FREE_MB:
        logger.warning(f"المكتبة: الذاكرة {free}MB — تُؤجَّل قراءة «{book.title}»")
        return None
    if not settings.AI_API_KEY or not can_call("gemini"):
        return None
    import httpx
    from app.services.ai_content import _extract_json_obj
    uri, fname = await _upload(path, f"book-{book.id}")
    if not uri:
        return None
    prompt = prompt or (f"اقرأ كتاب «{book.title}» (الملفّ المرفق) قراءةَ طالبِ استثمارٍ متفوّق، واستخلص منه بين اثني عشر وعشرين مبدأً "
              "يعمل بها مديرُ محفظة: القيمة، والتوقيت، والمخاطر، والسلوك، وبناء المحفظة، والتوزيعات. "
              "كلُّ مبدأٍ من الكتاب وحده، جملةٌ قصيرةٌ (عشرون كلمةً على الأكثر) بصيغة قاعدة، برقم صفحته في الملفّ. "
              'أعد JSON فقط: {"principles": [{"p": "المبدأ", "page": 12, "kind": "قيمة|توقيت|مخاطر|سلوك|محفظة|توزيعات"}]}')
    body = {"contents": [{"parts": [{"file_data": {"mime_type": "application/pdf", "file_uri": uri}}, {"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 3000}}
    obj = None
    try:
        record("gemini")
        async with httpx.AsyncClient(timeout=240) as c:
            r = await c.post(f"https://generativelanguage.googleapis.com/v1beta/models/{settings.AI_MODEL}:generateContent"
                             f"?key={settings.AI_API_KEY}", json=body)
        if r.status_code == 200:
            obj = _extract_json_obj(r.json()["candidates"][0]["content"]["parts"][0]["text"])
        else:
            logger.warning(f"المكتبة البصرية «{book.title}»: HTTP {r.status_code}")
    except Exception as e:                                        # noqa: BLE001
        logger.warning(f"المكتبة البصرية «{book.title}»: {type(e).__name__}")
    finally:
        await _forget(fname)
        _trim()
    pages_max = n_pages or (book.page_count or 0) or 10_000
    clean = []
    for it in (obj or {}).get("principles") or []:
        p = " ".join(str((it or {}).get("p") or "").split())
        try:
            pg = int((it or {}).get("page"))
        except (TypeError, ValueError):
            continue
        if p and 1 <= pg <= pages_max and len(p.split()) <= 26:
            clean.append({"p": p, "page": pg, "kind": (it or {}).get("kind") or ""})
    if not clean:
        return None
    rec = {"book_id": book.id, "title": book.title, "author": book.author, "principles": clean[:keep], "visual": True}
    lastgood.save(store.format(book.id), rec)
    return rec


def principles(limit: int = 30) -> list[dict]:
    """مبادئُ المكتبة كلِّها للطيار الآليّ — بالتناوب بين الكتب، كلٌّ باسم كتابه وصفحته."""
    from app.services import lastgood
    books = [lastgood.load(k) or {} for k in lastgood.keys_with_prefix("lib:wisdom:")]
    books = [b for b in books if b.get("principles")]
    out, i = [], 0
    while len(out) < limit and any(i < len(b["principles"]) for b in books):
        for b in books:
            if i < len(b["principles"]) and len(out) < limit:
                p = b["principles"][i]
                out.append({**p, "book": b.get("title")})
        i += 1
    return out


# ══ ‏D833 — صقرٌ يتعلّم من المكتبة (المالك 2026-11-25) ══
# «خلِّ صقر برضو يتعلّم من المكتبة كتغذيةٍ أكاديميةٍ علمية… خلّها داخليةً لا تخرج عندي — داخليةً عنده، يتشرّب جميعَ المعلومات من الكتب
# التي وضعتُها وانتقيتُها بعناية». فيدرس صقرٌ كلَّ كتابٍ بعين المتداول (للسوقين): المسارُ والرسمُ والحجمُ والخياراتُ والمخاطرُ والسلوكُ والأساس —
# مبدأً موثَّقاً برقم صفحته (لا اختلاق: من نصّ الكتاب وحده) — ويستحضرها حين يزن شواهدَه لكلّ صفقة وحين يجيب المالك، ولا يذكرها ولا يذكر كتاباً.
SAQR_STORE = "lib:saqr:{}"
SAQR_KEEP = 24
SAQR_KINDS = ("مسار", "رسم", "حجم", "خيارات", "مخاطر", "سلوك", "أساس", "أحداث")
_SAQR_ASK = ("استخلص منه المبادئَ التي يعمل بها متداولٌ ومحلّلٌ محترفٌ في سوق الأسهم (السعوديّ والأمريكيّ) وعقود الخيارات: المسارُ والاتجاه، "
             "والرسمُ ومستوياتُ الدعم والمقاومة ونقاطُ الدخول، والحجمُ والسيولة، والخياراتُ (الأجلُ والسعرُ التنفيذيّ والتآكلُ والتذبذب)، "
             "والمخاطرُ (الوقفُ وحجمُ المركز وحمايةُ رأس المال)، والسلوكُ والانضباطُ وأخطاءُ المتداول، والأساسُ (النتائجُ والتقييم)، والأخبارُ والأحداث.")
_SAQR_FMT = ('أعد JSON فقط:\n{"principles": [{"p": "المبدأ", "page": 12, "kind": "' + "|".join(SAQR_KINDS) + '"}]}')


async def saqr_digest(book) -> dict | None:
    """مبادئُ كتابٍ واحدٍ لصقر — تُستخلص مرّةً وتُحفظ (‏lib:saqr:{id})، أو يعاد المحفوظ."""
    from app.services import lastgood
    from app.services.library_service import _looks_garbled, _read_pages
    key = SAQR_STORE.format(book.id)
    old = lastgood.load(key)
    if old and old.get("principles"):
        return old
    pages = _read_pages(book.id)
    good = [p for p in pages if len((p or "").strip()) > 200 and not _looks_garbled(p)]
    by = f" لـ{book.author}" if book.author else ""
    if not pages or len(good) < 0.3 * max(1, len(pages)) or sum(len(p) for p in good) < 20_000:
        vp = (f"اقرأ كتاب «{book.title}»{by} (الملفّ المرفق) قراءةَ متداولٍ محترف. {_SAQR_ASK} "
              "كلُّ مبدأٍ من الكتاب وحده، جملةٌ قصيرةٌ (عشرون كلمةً على الأكثر) بصيغة قاعدةٍ تُطبَّق، برقم صفحته في الملفّ؛ "
              f"وما لم يتناوله الكتابُ من الأصناف فلا تكتب له شيئاً. بين اثني عشر وأربعةٍ وعشرين مبدأ، الأهمُّ أوّلاً. {_SAQR_FMT}")
        return await digest_visual(book, len(pages), prompt=vp, store=SAQR_STORE, keep=SAQR_KEEP)
    pages = [p if (p in good) else "" for p in pages]
    text = _sample(pages)
    if len(text) < 2000:
        return None
    from app.services.ai_content import _generate_obj
    prompt = f"""أنت «صقر» — متداولٌ ومحلّلٌ محترف — تدرس كتاب «{book.title}»{by} ليصير علماً تعمل به.
{_SAQR_ASK}

قواعدُ ملزمة:
- كلُّ مبدأ من نصّ الكتاب أدناه وحده، لا من معرفتك العامة. وإن لم تجد في النصّ مبدأً لصنفٍ فلا تكتب له شيئاً.
- كلُّ مبدأ جملةٌ واحدةٌ قصيرة (لا تزيد على عشرين كلمة)، بصيغة قاعدةٍ تُطبَّق: «لا تدخل…»، «اخرج حين…».
- اذكر رقمَ الصفحة التي جاء منها كما في علامة [صفحة N].
- بين اثني عشر وأربعةٍ وعشرين مبدأ، الأهمُّ أوّلاً.

النصّ:
{text}

{_SAQR_FMT}"""
    obj = await _generate_obj(prompt, f"ai:libsaqr:v1:{book.id}", 365 * 24 * 3600)
    valid_pages = {i + 1 for i, p in enumerate(pages) if len((p or "").strip()) > 200}
    clean = []
    for it in (obj or {}).get("principles") or []:
        p = " ".join(str((it or {}).get("p") or "").split())
        try:
            pg = int((it or {}).get("page"))
        except (TypeError, ValueError):
            continue
        if p and pg in valid_pages and len(p.split()) <= 26:
            clean.append({"p": p, "page": pg, "kind": (it or {}).get("kind") or ""})
    if not clean:
        logger.warning(f"المكتبة/صقر: لم يُستخلص مبدأٌ موثَّقٌ من «{book.title}»")
        return None
    rec = {"book_id": book.id, "title": book.title, "author": book.author, "principles": clean[:SAQR_KEEP]}
    lastgood.save(key, rec)
    return rec


def saqr_knowledge(limit: int = 24) -> list[dict]:
    """علمُ صقر من المكتبة كلِّها بالتناوب بين الكتب — الأهمُّ من كلّ كتابٍ أوّلاً، وفي كلّ دورةٍ مبادئُه بعين المتداول قبل مبادئ الاستثمار —
    كلٌّ بكتابه وصفحته (داخلياً)."""
    from app.services import lastgood
    books = []
    for pre in ("lib:saqr:", "lib:wisdom:"):
        for k in lastgood.keys_with_prefix(pre):
            b = lastgood.load(k) or {}
            if b.get("principles"):
                books.append(b)
    out, seen, i = [], set(), 0
    while len(out) < limit and any(i < len(b["principles"]) for b in books):
        for b in books:
            if i < len(b["principles"]) and len(out) < limit:
                p = b["principles"][i]
                if p["p"] not in seen:
                    seen.add(p["p"])
                    out.append({**p, "book": b.get("title")})
        i += 1
    return out


def saqr_titles() -> list[str]:
    """عناوينُ الكتب التي درسها صقر — لحارس التسرّب وحده (لا تُعرض)."""
    from app.services import lastgood
    ts = set()
    for pre in ("lib:saqr:", "lib:wisdom:"):
        for k in lastgood.keys_with_prefix(pre):
            t = (lastgood.load(k) or {}).get("title")
            if t and len(str(t).strip()) >= 3:
                ts.add(str(t).strip())
    return sorted(ts)


def saqr_block(limit: int = 24) -> tuple[str, str]:
    """كتلةُ المعرفة في توجيه النموذج ⇐ (النصّ، بصمتُه) — والنصُّ فارغٌ إن لم يدرس صقرٌ كتاباً بعد. داخليةٌ: لا كتبَ ولا صفحاتٍ فيها."""
    import hashlib
    ks = saqr_knowledge(limit)
    if not ks:
        return "", ""
    lines = "\n".join(f"• {k['p']}" for k in ks)
    txt = ("علمُك الأكاديميّ (درستَه من مكتبة المالك — داخليٌّ لك وحدك): زِن به الشواهدَ وتعارضَها كما يزنها المتخرّجُ المتمرّس، "
           "ولا تذكره ولا تذكر كتاباً ولا مكتبةً ولا تقتبس منه رقماً — فأرقامُك من الشواهد وحدها.\n" + lines + "\n")
    return txt, hashlib.md5(lines.encode()).hexdigest()[:10]


def scrub(t: str, titles: list[str] | None = None) -> str:
    """حارسُ التسرّب: جملةٌ تذكر كتاباً أو المكتبةَ أو عنوانَ كتابٍ درسه صقر تُحذف — فالعلمُ داخليّ (‏D833). وما لا ذكرَ فيه يعود كما هو بأسطره."""
    if not t:
        return t
    import re
    titles = [x for x in (titles if titles is not None else saqr_titles()) if x]
    bad = ("كتاب", "الكتب", "المكتبة", "مكتبة المالك", "مؤلّف", "مؤلف")
    hit = lambda x: any(b in x for b in bad) or any(tt in x for tt in titles)   # noqa: E731
    if not hit(t):
        return t
    out = []
    for line in t.split("\n"):
        if not hit(line):
            out.append(line)
            continue
        keep = [x for x in re.split(r"(?<=[.!؟?])\s+", line) if not hit(x)]
        if keep:
            out.append(" ".join(keep))
    return "\n".join(out).strip()
