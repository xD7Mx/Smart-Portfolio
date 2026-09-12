"""هيكلُ الملكية — بالمتصفّح، وبالاكتشاف لا بمسارٍ محفوظ (D270).

## لماذا بالمتصفّح

قِيس أن صفحاتِ «أرقام» لهذه البنود تعود **200 وصفرَ صفوف**: الجدولُ
يُرسَم بجافاسكربت بعد وصول الصفحة. وانتحالُ بصمة TLS يعبر الحمايةَ ولا
**ينفّذ سكربتاً** — هذا حدُّه الطبيعيّ وقد بلغناه (‏D265). فالمتصفّحُ هو
الوسيلةُ الباقية، مقيَّداً كما في `browser_fetch`.

## ولماذا بالاكتشاف

مساراتُ تبويبات «أرقام» تدور، ومسارٌ محفوظٌ في الشيفرة يصمت يوم يدور —
صمتاً لا يُميَّز عن «لا بيانات». فتُقرأ الروابطُ من صفحة الشركة نفسِها
بأسمائها العربية، كما نقرأ نقاطَ تداول من `<base href>`.

## والقاعدةُ التي لا تُخرَق

**الجهلُ ليس حكماً**: بندٌ لم يُقرأ **يغيب** من المخرَج، ولا يُكتب صفراً
ولا يُملأ بأقرب شبيه. ونسبةٌ لا تُفهَم تُترك. وما قُرئ يُحفظ بتاريخه
وبرابطه، فيُقال في الشاشة مصدرُه — أو «غير متوفّر».
"""
from __future__ import annotations

import re
from datetime import date, datetime, timezone

from loguru import logger

STORE_KEY = "ownership:{sym}"
MAX_AGE_DAYS = 30          # هذه البياناتُ شهريةُ التغيّر — لا يوميّة
MAX_ROWS = 60

# ══ الأسماءُ كما وردت، لا كما افترضتُها ══
# القياسُ ردّ ثلاثةً من أربعة: كتبتُ «الملكية الأجنبية» والصفحةُ تقول
# «ملكية الأجانب»، وكتبتُ «صفقات كبار المساهمين» وهي «الصفقات الخاصة»،
# وكتبتُ «تقديرات المحلّلين» وهي «توصيات المحللين». فصار المعوَّلُ على
# **المسار** أوّلاً — وهو أثبتُ من نصٍّ يُصاغ — والنصُّ سندٌ ثانٍ.
#
# ويُشترط أن يكون الرابطُ **خاصّاً بالشركة**: في الصفحة روابطُ سوقٍ عامّةٌ
# بالأسماء نفسِها (‏`/ar/monitors/market-ownership/3`)، ولو أُخذت لعُرض
# جدولُ السوق تحت اسم الشركة — رقمٌ صحيحٌ في مكانٍ خاطئٍ أسوأُ من الغياب.
TABS = {
    "major_holders": (re.compile(r"/shareholder/major-shareholders/company/"),
                      re.compile(r"كبار\s+الم(ساهمين|لاك)")),
    "insider_deals": (re.compile(r"/major-shareholders/company-deals/"),
                      re.compile(r"(الصفقات\s+الخاصة|صفقات\s+كبار)")),
    "foreign": (re.compile(r"/foreignownershipdetails/"),
                re.compile(r"ملكية\s+الأجانب|(الملكية|التملّك|التملك)\s+الأجنبي")),
    "estimates": (re.compile(r"/analystestimates/analystrecomendations"),
                  re.compile(r"(توصيات|توقعات|تقديرات)\s+المحلّ?لين")),
}

_TAG = re.compile(r"<[^>]+>")
_PCT = re.compile(r"(-?\d{1,3}(?:[.,]\d{1,3})?)\s*%")
# ما يُنزَع من نصّ الصفّ ليبقى الاسم: النسبةُ وأرقامُها وعلاماتُ الترقيم.
_NAME_CLEAN = re.compile(r"-?\d[\d.,]*\s*%|[\d.,]{4,}")


def _text(s: str) -> str:
    return re.sub(r"\s+", " ", _TAG.sub(" ", s or "")).strip()


def _pct(s: str) -> float | None:
    """نسبةٌ مئويةٌ مفهومة — أو None. ولا يُقرأ رقمٌ بلا علامة نسبة."""
    m = _PCT.search(str(s or ""))
    if not m:
        return None
    try:
        v = float(m.group(1).replace(",", "."))
    except ValueError:
        return None
    return v if -100.0 <= v <= 100.0 else None


def tables(html: str) -> list[list[list[str]]]:
    """كلُّ جدولٍ في الصفحة صفوفاً من خلايا نصّية."""
    out = []
    for tb in re.findall(r"<table[^>]*>(.*?)</table>", html or "", re.S | re.I):
        rows = []
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", tb, re.S | re.I):
            cells = [_text(c) for c in
                     re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S | re.I)]
            if any(cells):
                rows.append(cells)
        if rows:
            out.append(rows)
    return out


def tab_links(html: str, base: str, company_id: str | None = None) -> dict[str, str]:
    """اسمُ البند ← رابطُه، مقروءاً من الصفحة. وما لم يوجد يغيب.

    المسارُ يحكم، والنصُّ يسند. ورابطٌ لا يحمل معرِّفَ الشركة **يُرفض**
    حين يكون المعرِّفُ معلوماً: صفحةُ السوق ليست صفحةَ الشركة.
    """
    found: dict[str, str] = {}
    for href, label in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
                                  html or "", re.S | re.I):
        url = href.replace("&amp;", "&")
        txt = _text(label)
        for key, (by_path, by_text) in TABS.items():
            if key in found:
                continue
            if not (by_path.search(url) or (txt and by_text.search(txt))):
                continue
            if company_id and not re.search(rf"(?:^|/|=){re.escape(company_id)}(?:/|$|&)",
                                            url):
                continue        # رابطُ سوقٍ عامٌّ لا يُعرض تحت اسم شركة
            found[key] = url if url.startswith("http") else base + url
    return found


def holders_from(rows: list[list[str]]) -> list[dict]:
    """صفوفُ «اسمٌ · نسبة». وصفٌّ بلا نسبةٍ مفهومةٍ يُترك — لا يُصفَّر."""
    out = []
    for cells in rows:
        if len(cells) < 2:
            continue
        pct = next((p for p in (_pct(c) for c in cells[1:]) if p is not None), None)
        name = cells[0].strip()
        if pct is None or not name or _pct(name) is not None:
            continue
        out.append({"name": name, "percent": pct})
        if len(out) >= MAX_ROWS:
            break
    return out


_TAGS = re.compile(r"<(/?)(tr|li|div)\b[^>]*?(/?)>", re.I)
_DROP = re.compile(r"<(script|style|noscript)[^>]*>.*?</\1>", re.S | re.I)


def blocks(html: str) -> list[str]:
    """كتلُ العناصر بمطابقة فتحٍ وإغلاق — لا بتعبيرٍ يعجز عن التداخل.

    أوّلُ محاولةٍ استعملت تعبيراً يرفض التداخل، فالتقط **الأعمقَ فقط**
    (اسمٌ وحدَه، ونسبةٌ وحدَها) ولم يلتقط الصفَّ الذي يجمعهما — فعاد صفراً
    على الشكل الحقيقيّ نفسِه الذي جاء يقرؤه. والكتلُ تُبنى بمكدَّس.
    """
    out: list[str] = []
    stack: list[tuple[str, int]] = []
    for m in _TAGS.finditer(html or ""):
        closing, name, selfclose = m.group(1), m.group(2).lower(), m.group(3)
        if selfclose:
            continue
        if not closing:
            stack.append((name, m.start()))
            continue
        for i in range(len(stack) - 1, -1, -1):
            if stack[i][0] == name:
                out.append(html[stack[i][1]:m.end()])
                del stack[i:]
                break
    return out


def rows_from_divs(html: str) -> list[dict]:
    """صفوفٌ من `div`/`li` حين لا يكون في الصفحة جدول (D275).

    قِيس أن «أرقام» تنشر هذه البنودَ **بلا `<table>` واحد** (‏0 جداولَ في
    509 ألفَ حرف). فقارئُ الجداول وحدَه يعود صفراً دائماً — وصفرٌ مطلقٌ
    علامةُ قارئٍ يقرأ في المكان الخطأ، لا علامةُ مصدرٍ فارغ (الدرسُ نفسُه
    الذي علّمنيه مفتاحُ القوائم في D257).

    والقاعدةُ لا تتغيّر: يُقرأ الصفُّ الذي يحمل **اسماً ونسبةً مفهومة**،
    وما عداه يُترك.
    """
    out: list[dict] = []
    seen: set[str] = set()
    # الأصغرُ فالأكبر: الصفُّ أصغرُ كتلةٍ تجمع الاسمَ والنسبة، وأخذُ الأكبرِ
    # يبتلع الصفحةَ كلَّها في «صفٍّ» واحدٍ بلا معنى.
    for block in sorted(blocks(_DROP.sub(" ", html or "")), key=len):
        if block.count("%") != 1:
            continue
        txt = _text(block)
        pct = _pct(txt)
        if pct is None:
            continue
        name = _NAME_CLEAN.sub(" ", txt).strip(" ·-—،:")
        name = re.sub(r"\s+", " ", name)
        if len(name) < 3 or len(name) > 90 or name in seen:
            continue
        if not re.search(r"[A-Za-zء-ي]{3}", name):
            continue                       # اسمٌ بلا حروفٍ ليس اسمَ مساهم
        seen.add(name)
        out.append({"name": name, "percent": pct})
        if len(out) >= MAX_ROWS:
            break
    return out


def parse(html: str) -> list[dict]:
    """أوسعُ جدولٍ يحمل نسباً مفهومة، وإلّا فصفوفُ الحاويات. وإلّا فارغ."""
    best: list[dict] = []
    for rows in tables(html):
        got = holders_from(rows)
        if len(got) > len(best):
            best = got
    return best or rows_from_divs(html)


async def refresh(symbol: str) -> dict:
    """يقرأ ما أمكن لشركةٍ ويحفظه. ولا يكتب شيئاً إن لم يُقرأ شيء."""
    from app.services import lastgood
    from app.services.argaam_calendar import BASE, _company_id, _company_url
    from app.services.browser_fetch import BrowserUnavailable, render

    sym = str(symbol or "").replace(".SR", "").strip()
    cid = await _company_id(sym)
    if not cid:
        return {"error": "لا معرِّفَ للشركة في «أرقام»"}

    try:
        pages = await render([_company_url(cid)])
    except BrowserUnavailable as e:
        # غيابُ المتصفّح ليس غيابَ بيانات — ويُقال باسمه.
        return {"error": f"المتصفّحُ غيرُ متاح: {e}"}
    home = next(iter(pages.values()), "")
    links = tab_links(home, BASE, company_id=cid)
    if not links:
        return {"error": "لم يُكتشف تبويبٌ بأسماء البنود في صفحة الشركة"}

    rendered = await render(list(links.values()))
    rec: dict = {"symbol": sym, "as_of": datetime.now(timezone.utc).date().isoformat(),
                 "source": "أرقام — بالمتصفّح", "urls": links}
    for key, url in links.items():
        rows = parse(rendered.get(url, ""))
        if rows:                      # وما لم يُقرأ يغيب، ولا يُكتب فارغاً
            rec[key] = rows
    body = [k for k in TABS if k in rec]
    if not body:
        return {"error": "التبويباتُ فُتحت ولم يُقرأ فيها صفٌّ مفهوم",
                "urls": links}
    lastgood.save(STORE_KEY.format(sym=sym), rec)
    logger.info("هيكلُ الملكية {}: {}", sym, ", ".join(body))
    return {"ok": True, "symbol": sym, "sections": body}


def reading(symbol: str) -> dict | None:
    """المحفوظُ لشركةٍ — أو None إن غاب أو شاخ."""
    from app.services import lastgood
    sym = str(symbol or "").replace(".SR", "").strip()
    rec = lastgood.load(STORE_KEY.format(sym=sym))
    if not isinstance(rec, dict):
        return None
    try:
        age = (date.today() - date.fromisoformat(str(rec.get("as_of")))).days
    except Exception:                                             # noqa: BLE001
        return None
    return None if age > MAX_AGE_DAYS else rec
