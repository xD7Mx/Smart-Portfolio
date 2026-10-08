"""الأحداثُ الجوهرية من إفصاحات «تداول» — اقتراحُ المالك: «حصرناها مالياً وظلمناها إخبارياً».

القوائمُ المالية لا تسجّل العقدَ إلا حين يُسلَّم، والمحلّلُ يحسب سجلَّ الأعمال يومَ يُوقَّع. فقيس على
القطاعات الساقطة: أبعدُ شركات التطوير عن المحلّلين أكبرُها عقوداً معلنة (رتال · مسار · مكة).

والحدثُ يدخل **رقماً في موضعه** لا نقاطَ مزاج: السعرُ يتحرّك على الخبر في دقائق فالمزاجُ عدٌّ مكرّر،
والعقدُ يظهر في القوائم لاحقاً فما لا ينقضي أثرُه عدٌّ مكرّرٌ ثانٍ، وما لا يُقاس اختلاق.

ويُقرأ من الحقول المهيكلة «بند | توضيح» قبل إخلاء المسؤولية وحدها — ما بعده حشوُ الصفحة (قِيس:
«تسهيلات… بقيمة 880 مليون» من الشريط الجانبيّ حُسب عقداً). وأربعةُ فخاخٍ قِيست على النصوص:
  · التجديدُ ليس نموّاً — «الحفارات ذاتها التي كانت تعمل» · «ليحل محل العقد السابق»
  · الترسيةُ ثمّ التوقيعُ عقدٌ واحد — علم/المواصفات: ترسيةٌ في يوليو وتوقيعٌ في سبتمبر
  · قيمةُ التحالف ليست حصّةَ الشركة — رتال 3.2 مليار «لتحالف تقوده»، ومكة ومسار 6 مليارات لثلاث شركات
  · القيمةُ نسبةٌ من الإيراد — «يقارب 15% من إجمالي إيرادات الشركة… لعام 2025م»
  · الشركةُ مالكةُ المشروع لا منفّذتُه — مسار: «ترسية عقود… على المقاول الرئيسي» 4.1 مليار إنفاقٌ لا إيراد
وما لا رقمَ صريحاً له يُقال عنه «غير مفصَح» ولا يُقدَّر.
"""
from __future__ import annotations

import re

_DISCLAIMER = "لا تتحمل أي من هيئة السوق المالية"
_AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩٫٬", "0123456789.,")
_WORD_N = {"سنة": 1, "سنتين": 2, "سنتان": 2, "عامين": 2, "عامان": 2, "ثلاث": 3, "ثلاثة": 3, "أربع": 4, "أربعة": 4,
           "خمس": 5, "خمسة": 5, "ست": 6, "ستة": 6, "سبع": 7, "سبعة": 7, "ثمان": 8, "ثماني": 8, "ثمانية": 8,
           "تسع": 9, "تسعة": 9, "عشر": 10, "عشرة": 10}

# عناوينُ القائمة تصل بالإنجليزية (حقلُ SHORT_DESC) — قِيس: صفرٌ مصنَّفٌ بأنماطٍ عربية في 70 شركة
_FIN = re.compile(r"facilit|financing|loan|sukuk|murabaha|تسهيلات|تمويل", re.I)
KINDS = (
    ("contract", re.compile(r"contract|award|purchase order|signing of an? (?:agreement|memorandum)", re.I)),
    ("acquisition", re.compile(r"acqui|merger|purchase of (?:a )?stake", re.I)),
    ("losses", re.compile(r"accumulated loss", re.I)),
    ("regulator", re.compile(r"violation|penalt|\bfine[sd]?\b|letter from the (?:insurance authority|capital market|cma)|"
                             r"suspen|qualified|going concern", re.I)),
    ("litigation", re.compile(r"lawsuit|court|ruling|claim", re.I)),
    ("leadership", re.compile(r"resign\w* (?:of )?(?:an? |the )?(?:ceo|chief executive|chairman)|"
                              r"(?:ceo|chief executive|chairman)\w*\s+resign", re.I)),
)


def kind_of(title: str) -> str | None:
    t = title or ""
    for k, rx in KINDS:
        if k == "contract" and _FIN.search(t):
            continue
        if rx.search(t):
            return k
    return None


def rows(text: str) -> dict[str, str]:
    """حقولُ «بند | توضيح» قبل إخلاء المسؤولية — المفتاحُ الأوّلُ يُحفظ ولا يُكتب فوقه."""
    out: dict[str, str] = {}
    for ln in (text or "").split(_DISCLAIMER)[0].split("\n"):
        if "|" not in ln:
            continue
        k, _, v = ln.partition("|")
        k, v = k.strip(), v.strip()
        if k and k not in out:
            out[k] = v
    return out


def money(s: str, revenue_by_year: dict[int, float] | None = None) -> tuple[float | None, str]:
    """المبلغُ بالريال من نصّ حقل القيمة ← (القيمة، الأساس). ما لا رقمَ صريحاً له ← (None, السبب)."""
    t = (s or "").translate(_AR_DIGITS)
    if not t.strip():
        return None, "غير مفصَح"
    m = re.search(r"(\d+(?:\.\d+)?)\s*%\s*من\s*إجمالي\s*إيرادات", t)
    if m:
        y = re.search(r"(20\d\d)", t[m.end():])
        rev = (revenue_by_year or {}).get(int(y.group(1))) if y else None
        if rev:
            return float(m.group(1)) / 100 * rev, f"{m.group(1)}٪ من إيرادات {y.group(1)}"
        return None, "نسبةٌ من الإيراد بلا إيرادِ سنتها"
    best = None
    for m in re.finditer(r"(\d[\d,]*(?:\.\d+)?)\)?\s*(مليارات|مليار|ملايين|مليون|ألف|الف)?", t):
        try:
            v = float(m.group(1).replace(",", ""))
        except ValueError:
            continue
        u = m.group(2) or ""
        v *= 1e9 if u.startswith("مليار") else 1e6 if u.startswith("مل") else 1e3 if u in ("ألف", "الف") else 1
        if v >= 1e6:
            best = v if best is None else best + v      # «الحزمة (أ) 3.2 مليار… والحزمة (ب) 899 مليون» عقدان
    return (best, "مفصَح") if best else (None, "غير مفصَح")


def months(s: str) -> int | None:
    t = (s or "").translate(_AR_DIGITS)
    m = re.search(r"(\d+)\s*\)?\s*(شهر|أشهر|شهرا|شهراً)", t)
    if m:
        return int(m.group(1))
    m = re.search(r"\(?(\d+)\)?\s*(سنة|سنوات|سنين|عام|أعوام)", t)
    if m:
        return 12 * int(m.group(1))
    for w, n in _WORD_N.items():
        if re.search(rf"(?:^|\s){w}(?:\s|$)", t) and re.search(r"سن|عام", t):
            return 12 * n
    return None


_RENEWAL = re.compile(r"يحل محل|ذاتها التي كانت|تجديد|تمديد العقد|امتداد(?:اً)? للعقد")
_CONSORTIUM = re.compile(r"تحالف|ائتلاف")
_NO_IMPACT = re.compile(r"لا\s*يمكن\s*تحديد\s*الأثر")
_CLIENT = re.compile(r"على\s+المقاول|المقاول\s+الرئيسي|عن\s+قيام\s+\S+(?:\s+\S+){0,12}\s+بترسية")


def contract(title: str, text: str, revenue_by_year: dict[int, float] | None = None) -> dict:
    """عقدٌ واحدٌ ← حقولُه وحكمُ عدّه. لا يُعدّ في سجلّ الأعمال إلا موقَّعٌ مفصَحُ القيمة لا تجديدٌ ولا حصّةُ تحالف."""
    r = rows(text)
    get = lambda *ks: next((r[k] for k in r for kk in ks if kk in k), "")   # noqa: E731
    raw_val = get("قيمة العقد", "قيمة الترسية", "قيمة المشروع")
    val, basis = money(raw_val, revenue_by_year)
    dur = months(get("مدة العقد"))
    whole = " ".join(r.values())
    ev = {
        "value": val, "basis": basis, "months": dur,
        "counterparty": get("الجهة التي تم توقيع العقد معها", "الطرف الاخر", "الطرف الآخر"),
        "impact": get("الأثر المالي"), "related": get("أطراف ذات علاقة"),
        "signed": bool(get("تاريخ توقيع العقد")) or "توقيع" in (get("مقدمة") or ""),
        "renewal": bool(_RENEWAL.search(whole)),
        "consortium": bool(_CONSORTIUM.search(whole)),
        "project_value_only": not get("قيمة العقد") and bool(get("قيمة المشروع")),
        "no_impact": bool(_NO_IMPACT.search(whole)),
        "client": bool(_CLIENT.search(whole)),
    }
    why = None
    if val is None:
        why = basis
    elif ev["client"]:
        why = "الشركةُ مالكةُ المشروع تُرسيه على مقاول — إنفاقٌ لا إيراد"
    elif ev["renewal"]:
        why = "تجديدٌ لعقدٍ قائم — يحفظ الإيرادَ ولا يزيده"
    elif ev["consortium"] or ev["project_value_only"]:
        why = "قيمةُ مشروعٍ أو تحالف — حصّةُ الشركة غير مفصَحة"
    elif ev["no_impact"]:
        why = "الشركةُ لم تحدّد الأثرَ المالي"
    elif not ev["signed"]:
        why = "ترسيةٌ لم تُوقَّع بعد"
    elif not dur:
        why = "مدّةُ العقد غير مفصَحة"
    ev["counted"] = why is None
    ev["why_not"] = why
    ev["annual"] = round(val / (dur / 12), 2) if ev["counted"] else None
    return ev


def losses_pct(title: str) -> float | None:
    """«… Accumulated Losses to 47.5 % of the Capital» ← 47.5"""
    m = re.search(r"accumulated loss\w*\s+(?:to|of|reach\w*)\s+(\d+(?:\.\d+)?)\s*%", title or "", re.I)
    return float(m.group(1)) if m else None


def _revenue_by_year(sym: str) -> dict[int, float]:
    try:
        from app.services.tadawul_xbrl import for_symbol as X
        out = {}
        for p in X(sym, "annual") or []:
            y = p.get("year") or str(p.get("as_of") or "")[:4]
            r = p.get("revenue")
            if y and isinstance(r, (int, float)) and r > 0:
                out[int(y)] = float(r)
        return out
    except Exception:                                              # noqa: BLE001
        return {}


async def events_for(symbol: str, days: int = 365) -> dict:
    """أحداثُ الشركة الجوهرية لسنةٍ من «تداول» ← {events, backlog_annual, backlog_ratio, flags}.

    يُخزَّن يوماً: الإفصاحُ لا يتغيّر بعد نشره، والجديدُ يصل مع المسحة الليلية."""
    import datetime as dt
    from app.services import cache
    from app.services.tadawul_disclosure import list_for, detail
    sym = re.sub(r"\D", "", str(symbol or ""))[:4]
    ck = f"events:v1:{sym}"
    hit = cache.get(ck)
    if hit is not None:
        return hit
    since = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    revs = _revenue_by_year(sym)
    rev_last = revs[max(revs)] if revs else None
    events, seen = [], set()
    for a in await list_for(sym, 60):
        if (a.get("date") or "") < since:
            continue
        k = kind_of(a.get("title") or "")
        if not k:
            continue
        ev = {"kind": k, "date": a.get("date"), "title": a.get("title"), "url": a.get("url")}
        if k == "contract":
            d = await detail(a["url"]) or {}
            ev.update(contract(a.get("title") or "", d.get("text") or "", revs))
            key = (round(ev["value"] or 0, -5), (ev.get("counterparty") or "")[:24])
            if ev["value"] and key in seen:          # الترسيةُ ثمّ التوقيعُ عقدٌ واحد — والقائمةُ الأحدثُ أوّلاً
                continue
            seen.add(key)
        elif k == "losses":
            ev["pct"] = losses_pct(a.get("title") or "")
        events.append(ev)
    # ‏D633: عقدٌ إيرادُه السنويّ فوق ضعفَي إيراد الشركة قراءةٌ معطوبة لا صفقة — قِيس في المحاكاة: أسمنت نجران
    # «14220٪ من الإيراد» والأبحاثُ والإعلام «386 تريليوناً». فلا يُعدّ، ويُعلَّم للمراجعة.
    for e in events:
        if e.get("counted") and (not rev_last or e["annual"] > 2 * rev_last):
            e.update({"counted": False, "why_not": "قيمةٌ غيرُ معقولةٍ مقابل إيراد الشركة — تُراجَع ولا تُعدّ", "annual": None})
    counted = [e for e in events if e.get("counted")]
    annual = sum(e["annual"] for e in counted)
    flags = sorted({e["kind"] for e in events if e["kind"] in ("losses", "regulator", "litigation", "leadership")})
    res = {"symbol": sym, "events": events, "backlog_annual": round(annual, 2) if counted else None,
           "backlog_ratio": round(annual / rev_last, 4) if counted and rev_last else None,
           "revenue_last": rev_last, "flags": flags, "asof": dt.date.today().isoformat()}
    cache.set(ck, res, 24 * 60 * 60)
    return res
