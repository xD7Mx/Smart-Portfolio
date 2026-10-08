"""عرضُ الأحداث الجوهرية في صفحة الشركة (‏D644 · الإصدار الثاني) — اقتراحُ المالك: «ظلمناها إخبارياً».

يقرأ المستخرِجَ (`material_events` — ضمن ملفّات المحرّك المجمَّدة) ولا يعدّله: العرضُ لا يمسّ رقماً. وقِيس أنّ إدخالَ
العقود في **القيمة** لا يُحسّنها (D633: 17.1٪ ← 17.1٪/17.4٪) فلا تدخلها؛ أمّا المستثمرُ فيراها هنا بنصّها العربيّ
من «تداول»: العقدُ بقيمته ومدّته وما لم يُعدَّ ولماذا، والسلبياتُ الجسيمة (جهةٌ رقابية · خسائرُ متراكمة · قضاء · قيادة)."""
from __future__ import annotations

KIND_AR = {"contract": "عقد", "acquisition": "استحواذ", "losses": "خسائرُ متراكمة",
           "regulator": "جهةٌ رقابية", "litigation": "قضاء", "leadership": "قيادة"}
NEGATIVE = frozenset({"losses", "regulator", "litigation", "leadership"})


async def for_display(symbol: str, limit: int = 12) -> dict:
    """← {events:[{date, kind, kind_ar, negative, title, url, value, months, annual, counted, why_not, counterparty}], …}"""
    from app.services import cache
    from app.services.material_events import events_for
    from app.services.tadawul_disclosure import detail
    sym = "".join(ch for ch in str(symbol or "") if ch.isdigit())[:4]
    ck = f"events:view:v1:{sym}"
    hit = cache.get(ck)
    if hit is not None:
        return hit
    ev = await events_for(sym)
    out = []
    for e in (ev.get("events") or [])[:limit]:
        d = await detail(e["url"]) if e.get("url") else None
        out.append({
            "date": e.get("date"), "kind": e.get("kind"), "kind_ar": KIND_AR.get(e.get("kind"), e.get("kind")),
            "negative": e.get("kind") in NEGATIVE,
            "title": ((d or {}).get("title") or e.get("title") or "").strip(),   # العنوانُ العربيّ من صفحة الإفصاح
            "url": e.get("url"), "value": e.get("value"), "months": e.get("months"), "annual": e.get("annual"),
            "counted": e.get("counted"), "why_not": e.get("why_not"), "counterparty": e.get("counterparty"),
            "pct": e.get("pct"),
        })
    res = {"symbol": sym, "events": out, "backlog_annual": ev.get("backlog_annual"),
           "backlog_ratio": ev.get("backlog_ratio"), "asof": ev.get("asof")}
    cache.set(ck, res, 24 * 60 * 60)
    return res
