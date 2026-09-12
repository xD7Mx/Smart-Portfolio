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

# أسماءُ التبويبات كما تُكتب في الصفحة. ويُقرأ الاسمُ لا المسار.
TABS = {
    "major_holders": re.compile(r"كبار\s+المساهمين"),
    "insider_deals": re.compile(r"صفقات\s+(كبار\s+المساهمين|المطّلعين|المطلعين)"),
    "foreign": re.compile(r"(الملكية|التملّك|التملك)\s+الأجنبي"),
    "estimates": re.compile(r"تقديرات\s+المحلّ?لين"),
}

_TAG = re.compile(r"<[^>]+>")
_PCT = re.compile(r"(-?\d{1,3}(?:[.,]\d{1,3})?)\s*%")


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


def tab_links(html: str, base: str) -> dict[str, str]:
    """اسمُ البند ← رابطُه، مقروءاً من الصفحة. وما لم يوجد يغيب."""
    found: dict[str, str] = {}
    for href, label in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
                                  html or "", re.S | re.I):
        txt = _text(label)
        if not txt:
            continue
        for key, rx in TABS.items():
            if key not in found and rx.search(txt):
                found[key] = href if href.startswith("http") else base + href
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


def parse(html: str) -> list[dict]:
    """أوسعُ جدولٍ يحمل نسباً مفهومة. وبلا واحدٍ تعود قائمةٌ فارغة."""
    best: list[dict] = []
    for rows in tables(html):
        got = holders_from(rows)
        if len(got) > len(best):
            best = got
    return best


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
    links = tab_links(home, BASE)
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
