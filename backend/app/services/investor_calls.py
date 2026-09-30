"""مؤتمراتُ المحلّلين والمستثمرين (D559) — من إعلانات «تداول» نفسِها.

قال المالك: «هناك ميزةٌ خطيرة لدى تداول — جوهرةٌ ثمينة — مكالماتُ المستثمرين لدى الشركات
… فنّانةٌ في تغذية تحليل التطبيق ورأي الذكاء والتقارير ومستخدم التطبيق».

وقِيس (كاشف investor_calls_door): البحثُ في إعلانات السوق بعبارة «conference call» يعيد
303 إعلاناً (العربيةُ لا تُطابق: القائمةُ تُخدَم بالإنجليزية). والإعلانُ نوعان:
  · **قبل المؤتمر** — موعدُه بالهجريّ والميلاديّ وساعتُه، ومن يمثّل الشركة، ورابطُ التسجيل.
  · **بعده** — «عقدت مؤتمراً … وناقشت النتائج»، ورابطُ العرض التقديميّ في موقع الشركة.
ولا تسجيلَ صوتيّاً ولا نصّاً مفرَّغاً في «تداول» — فلا يُدّعى وجودُهما.

فيُجمع هنا: الموعدُ والحالةُ (قادمٌ/عُقد) والفترةُ المناقشة ورابطا الحضور والعرض.
"""
from __future__ import annotations

import json
import re
from datetime import date

from loguru import logger

STORE = "calls:market"
KEEP_DAYS = 3 * 365
_JOIN = re.compile(r"webex|zoom\.|teams\.|register|gotowebinar|meet\.|livestorm|webinar|bigmarker|on24", re.I)
_MONTHS = {m: i for i, m in enumerate(("january", "february", "march", "april", "may", "june", "july", "august",
                                        "september", "october", "november", "december"), 1)}


def _greg(text: str) -> str | None:
    """تاريخُ المؤتمر الميلاديّ — بعد «corresponding to» أو بصيغة يوم/شهر/سنة ميلادية."""
    t = text or ""
    for m in re.finditer(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})\s*(?:G|AD|م)?", t):
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 2000 <= y <= 2100 and 1 <= mo <= 12 and 1 <= d <= 31:
            return f"{y:04d}-{mo:02d}-{d:02d}"
    m = re.search(r"(\d{1,2})(?:st|nd|rd|th)?\s+(January|February|March|April|May|June|July|August|September|"
                  r"October|November|December),?\s+(20\d\d)", t, re.I)
    if m:
        return f"{int(m.group(3)):04d}-{_MONTHS[m.group(2).lower()]:02d}-{int(m.group(1)):02d}"
    return None


_ORD = {"first": 1, "second": 2, "third": 3, "fourth": 4}
_QAR = {1: "الربع الأول", 2: "الربع الثاني", 3: "الربع الثالث", 4: "الربع الرابع"}


def _period_ar(t: str) -> str | None:
    """الفترةُ المناقشة بالعربية — من صيغ الإعلان الإنجليزية الشائعة، وإلا لا شيء."""
    m = re.search(r"\b(first|second|third|fourth)\s+quarter\b[^.]*?(20\d\d)|\bQ([1-4])\s*(20\d\d)|\b([1-4])Q\s*(20\d\d)", t, re.I)
    if m:
        q = _ORD.get((m.group(1) or "").lower()) or int(m.group(3) or m.group(5))
        return f"{_QAR[q]} {m.group(2) or m.group(4) or m.group(6)}"
    m = re.search(r"\b(first|second)\s+half\b[^.]*?(20\d\d)|\bH([12])\s*(20\d\d)", t, re.I)
    if m:
        h = 1 if (m.group(1) or "").lower() == "first" or m.group(3) == "1" else 2
        return f"{'النصف الأول' if h == 1 else 'النصف الثاني'} {m.group(2) or m.group(4)}"
    m = re.search(r"\b(?:fiscal|financial)\s+year\b[^.]*?(20\d\d)|\byear ended[^.]*?(20\d\d)", t, re.I)
    if m:
        return f"السنة المالية {m.group(1) or m.group(2)}"
    m = re.search(r"\b(?:period|months?)\s+ended\s+(\d{1,2})\s+(\w+)\s+(20\d\d)", t, re.I)
    if m and m.group(2).lower() in _MONTHS:
        return f"الفترة المنتهية في {m.group(3)}-{_MONTHS[m.group(2).lower()]:02d}-{int(m.group(1)):02d}"
    return None


def parse(text: str, announced: str | None, today: date | None = None) -> dict:
    """متنُ الإعلان ← {date, time, status, join, deck, summary}."""
    today = today or date.today()
    t = re.split(r"The Capital Market Authority and Saudi Exchange take no responsibility", text or "")[0]
    t = re.sub(r"^Announcement Detail \|\s*", "", t.strip())
    d = _greg(t)
    tm = re.search(r"(\d{1,2}[:.]\d{2})\s*([AaPp]\.?[Mm]\.?)", t)
    urls = [u.rstrip(".,;)") for u in re.findall(r"https?://[^\s\"<>]+", t) if "saudiexchange" not in u]
    join = next((u for u in urls if _JOIN.search(u)), None)
    deck = next((u for u in urls if u != join), None)
    past = bool(re.search(r"\b(held|conducted|has organized|organized a conference call.*?\bon\b|was held|hosted)\b", t, re.I)
                and not re.search(r"\b(will|intention|intends|to be held|invites)\b", t, re.I))
    status = "held" if past or (d and d < today.isoformat()) else "upcoming"
    per = _period_ar(t)
    first = re.split(r"(?<=[.!])\s", t, maxsplit=1)[0]
    return {"date": d or announced, "time": (tm.group(1).replace(".", ":") + " " + tm.group(2).upper().replace(".", "")) if tm else None,
            "status": status, "join": join if status == "upcoming" else None, "deck": deck,
            "period": per, "summary": first[:320]}


def load() -> dict:
    from app.services import lastgood
    return lastgood.load(STORE) or {}


def for_symbol(symbol: str, limit: int = 8) -> list[dict]:
    sym = str(symbol).replace(".SR", "").strip()
    rows = [c for c in (load().get("calls") or {}).values() if c.get("symbol") == sym]
    return sorted(rows, key=lambda c: c.get("date") or "", reverse=True)[:limit]


def upcoming(symbols: list[str] | None = None, today: date | None = None) -> list[dict]:
    t = (today or date.today()).isoformat()
    want = {str(s).replace(".SR", "") for s in symbols} if symbols else None
    rows = [c for c in (load().get("calls") or {}).values()
            if (c.get("date") or "") >= t and (want is None or c.get("symbol") in want)]
    return sorted(rows, key=lambda c: c.get("date") or "")


def lines(symbol: str) -> list[str]:
    """سطورُ عقل التطبيق: آخرُ مؤتمرٍ عُقد والقادمُ إن وُجد."""
    out = []
    rows = for_symbol(symbol, 12)
    up = [c for c in rows if c.get("status") == "upcoming" and (c.get("date") or "") >= date.today().isoformat()]
    held = [c for c in rows if c.get("status") == "held"]
    if up:
        c = up[-1]
        out.append(f"مؤتمرُ المحلّلين القادم {c['date']}" + (f" الساعة {c['time']}" if c.get("time") else "")
                   + (f" لمناقشة {c['period']}" if c.get("period") else ""))
    if held:
        c = held[0]
        out.append(f"آخرُ مؤتمرٍ للمحلّلين عُقد {c['date']}" + (f" لمناقشة {c['period']}" if c.get("period") else "")
                   + (" — والعرضُ التقديميُّ منشورٌ في موقع الشركة" if c.get("deck") else ""))
    if len(held) >= 3:
        out.append(f"الشركةُ تعقد مؤتمراتِ المحلّلين بانتظام ({len(held)} مؤتمراتٍ مسجّلة) — إفصاحٌ جيّدٌ للمستثمر")
    return out


async def refresh(pages: int = 2, max_details: int = 60) -> dict:
    """يقرأ صفحاتِ البحث الأحدث، ويفتح تفاصيلَ الجديد فقط (حتى `max_details`)."""
    from app.services import lastgood
    from app.services import tadawul_disclosure as D
    from app.services.tadawul_http import fetch, smart_fetch
    rec = load()
    calls = dict(rec.get("calls") or {})
    ep = await D._endpoint()
    rep = {"seen": 0, "new": 0}
    if not ep:
        rep["err"] = "لا نقطةَ بيانات"
        return rep
    rows: list[dict] = []
    for pg in range(1, pages + 1):
        form = {"annoucmentType": "1_-1", "symbol": "", "sectorDpId": "", "searchType": "", "fromDate": "",
                "toDate": "", "datePeriod": "", "productType": "", "advisorsList": "", "textSearch": "conference call",
                "pageNumberDb": str(pg), "pageSize": "50"}
        try:
            st, raw = await smart_fetch(ep, method="POST", data=form, referer=D.PAGE, warm=D.PAGE,
                                        headers={"X-Requested-With": "XMLHttpRequest"})
            got = (json.loads(raw) or {}).get("announcementList") or [] if st == 200 else []
        except Exception as e:                                    # noqa: BLE001
            logger.debug("مؤتمرات المحلّلين ص{}: {}", pg, e)
            got = []
        rows += got
        if len(got) < 50:
            break
    rep["seen"] = len(rows)
    for r in rows:
        rid = str(r.get("announcementNumber") or r.get("PRESS_REL_ID") or "")
        if not rid or rid in calls or not r.get("announcementUrl"):
            continue
        if not re.search(r"conference call|earnings call|analyst", r.get("SHORT_DESC") or "", re.I):
            continue
        if rep["new"] >= max_details:
            break
        url = D.O + r["announcementUrl"]
        try:
            st, h = await fetch(url)
            det = D.parse_detail(h or "") or {}
        except Exception:                                         # noqa: BLE001
            continue
        if not det.get("text"):
            continue
        c = parse(det["text"], D._date(r.get("PR_DATE")))
        calls[rid] = {**c, "id": rid, "symbol": str(r.get("SYMBOL")), "announced": D._date(r.get("PR_DATE")),
                      "title": (r.get("SHORT_DESC") or "")[:200], "url": url}
        rep["new"] += 1
    cut = date.fromordinal(date.today().toordinal() - KEEP_DAYS).isoformat()
    calls = {k: v for k, v in calls.items() if (v.get("date") or v.get("announced") or "9") >= cut}
    # قادمٌ مضى موعدُه صار «عُقد» — بلا فتحٍ جديد
    t = date.today().isoformat()
    for v in calls.values():
        if v.get("status") == "upcoming" and (v.get("date") or "9") < t:
            v["status"], v["join"] = "held", None
    if rep["new"] or calls != (rec.get("calls") or {}):
        lastgood.save(STORE, {"calls": calls, "at": t})
    rep["total"] = len(calls)
    return rep
