"""توزيعاتُ الشركة من صفحتها الرسمية في «تداول» (D444).

قِيس بكاشف `company_dividends_table.py`: صفحةُ الشركة تحمل جدولَ
`companyDividends` مرسوماً في HTML نفسِه — آخرُ خمسة توزيعاتٍ بتاريخ الإعلان
والأحقية والتوزيع والمبلغ (4030: ‏1.50 · أحقية 10/09/2026 · توزيع 27/09/2026).

وكانت التوزيعاتُ في صفحة السهم من ياهو وحدَه، فتغيب متى نفدت حصّتُه. فالرسميُّ
أوّلاً، وما قبل أقدمِ صفٍّ رسميٍّ يُكمَل من ياهو ليطول السجلُّ عشرَ سنوات.
"""
from __future__ import annotations

import html as _html
import re
from datetime import date
from typing import Optional

_CELL = re.compile(r"<t[hd][^>]*>(.*?)</t[hd]>", re.S)
_ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
_TTL = 12 * 3600


def _txt(c: str) -> str:
    return _html.unescape(re.sub(r"<[^>]+>|\s+", " ", c)).strip()


def _iso(d: str) -> Optional[str]:
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})$", d.strip())
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None


def _amt(s: str) -> Optional[float]:
    m = re.search(r"\d+(?:\.\d+)?", s.replace(",", ""))
    return float(m.group(0)) if m else None


def parse_table(body: str) -> list[dict]:
    """صفوفُ جدول `companyDividends` ← [{announced, eligibility, paid, amount}]."""
    i = (body or "").find('id="companyDividends"')
    if i < 0:
        return []
    seg = body[i:body.find("</table>", i)]
    out = []
    for r in _ROW.findall(seg):
        c = [_txt(x) for x in _CELL.findall(r)]
        if len(c) < 5:
            continue
        el, amount = _iso(c[1]), _amt(c[4])
        if not el or amount is None or amount <= 0:
            continue
        out.append({"announced": _iso(c[0]), "eligibility": el,
                    "paid": _iso(c[2]), "method": c[3] or None, "amount": amount})
    return sorted(out, key=lambda x: x["eligibility"])


def shape(rows: list[dict], today: date | None = None) -> Optional[dict]:
    """بشكل `get_dividends` نفسِه كي تقرأه الشاشةُ والمحرّكاتُ بلا تغيير."""
    if not rows:
        return None
    today = today or date.today()
    hist = [{"date": r["eligibility"], "year": int(r["eligibility"][:4]),
             "amount": round(r["amount"], 4)} for r in rows]
    nxt = next((r for r in rows if r["eligibility"] >= today.isoformat()), None)
    ref = nxt or rows[-1]
    return {"history": hist, "ex_date": ref["eligibility"], "pay_date": ref["paid"],
            "announced": ref["announced"], "source": "تداول", "official": rows}


async def read(symbol: str) -> Optional[dict]:
    from app.services import cache, lastgood
    sym = str(symbol).replace(".SR", "")
    ck = f"div:tadawul:{sym}"
    hit = cache.get(ck)
    if hit is not None:
        return hit or None
    try:
        from app.services.tadawul_ownership import company_page
        rows = parse_table(await company_page(sym) or "")
    except Exception:                                             # noqa: BLE001
        rows = []
    if rows:
        lastgood.save(f"div:tadawul:{sym}", {"rows": rows})
    else:
        rows = ((lastgood.load(f"div:tadawul:{sym}") or {}).get("rows")) or []
    out = shape(rows)
    cache.set(ck, out or {}, _TTL if out else 3600)
    return out


def merge(official: Optional[dict], yahoo: Optional[dict]) -> Optional[dict]:
    """الرسميُّ يتقدّم، وياهو يُكمِل ما قبل أقدم صفٍّ رسميّ فقط."""
    if not official:
        return yahoo
    hist = list(official["history"])
    first = hist[0]["date"] if hist else "9999"
    older = [h for h in (yahoo or {}).get("history") or [] if str(h.get("date")) < first]
    out = {**(yahoo or {}), **official, "history": older + hist}
    from collections import Counter
    yrs = [h["year"] for h in out["history"] if h["year"] >= date.today().year - 5]
    counts = sorted(Counter(yrs).values())
    if counts:
        med = counts[len(counts) // 2]
        out["frequency"] = {4: "ربع سنوي", 2: "نصف سنوي", 1: "سنوي",
                            3: "ثلاث مرات سنوياً"}.get(med, "غير منتظم")
    return out
