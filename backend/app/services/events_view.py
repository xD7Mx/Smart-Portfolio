"""عرضُ الأحداث الجوهرية في صفحة الشركة (‏D644 · الإصدار الثاني) — اقتراحُ المالك: «ظلمناها إخبارياً».

يقرأ المستخرِجَ (`material_events` — ضمن ملفّات المحرّك المجمَّدة) ولا يعدّله: العرضُ لا يمسّ رقماً. وقِيس أنّ إدخالَ
العقود في **القيمة** لا يُحسّنها (D633: 17.1٪ ← 17.1٪/17.4٪) فلا تدخلها؛ أمّا المستثمرُ فيراها هنا بنصّها العربيّ
من «تداول»: العقدُ بقيمته ومدّته وما لم يُعدَّ ولماذا، والسلبياتُ الجسيمة (جهةٌ رقابية · خسائرُ متراكمة · قضاء · قيادة)."""
from __future__ import annotations

import re

# ‏ملاحظةُ المالك (2026-10-09): «هناك تكرارٌ في الأحداث» — الصفقةُ الواحدة تُعلَن ثمّ تُحدَّث («آخرُ التطورات بشأن…») فتظهر
# ثلاثَ مرّات. فإعلاناتُ الحدث الواحد تُجمع في بندٍ واحد: أحدثُها بتاريخه ورابطه، ومعه تاريخُ أوّل إعلان.
_NOISE = {"آخر", "التطورات", "بشأن", "تحديث", "تعلن", "شركة", "عن", "على", "من", "في", "the", "of",
          "announces", "announcement", "latest", "developments", "regarding", "update", "on", "to", "and", "a", "an",
          "with", "for", "company", "co", "its"}
_TASHKEEL = re.compile(r"[\u064B-\u0652\u0640]")


def _words(t: str) -> set[str]:
    t = _TASHKEEL.sub("", str(t or "").lower())
    t = re.sub(r"\([^)]*\)", " ", t)                                  # (غازكو) · (Gasco)
    return {w for w in re.findall(r"[\w٪%]+", t) if len(w) > 1 and w not in _NOISE}


def same_event(a: dict, b: dict) -> bool:
    """إعلانان للحدث نفسِه: النوعُ واحد، والقيمةُ واحدةٌ إن ذُكرت في الاثنين، وكلماتُ الأقصر في الأطول ≥ 80٪."""
    if a.get("kind") != b.get("kind"):
        return False
    va, vb = a.get("value"), b.get("value")
    if isinstance(va, (int, float)) and isinstance(vb, (int, float)) and abs(va - vb) > 0.01 * max(va, vb):
        return False
    wa, wb = _words(a.get("title")), _words(b.get("title"))
    if not wa or not wb:
        return False
    return len(wa & wb) / min(len(wa), len(wb)) >= 0.8


def dedupe(events: list[dict]) -> list[dict]:
    """الأحدثُ أوّلاً: كلُّ إعلانٍ لاحقٍ لحدثٍ ظهر يُضمّ إليه (يُحمل تاريخُ أوّل إعلانٍ وعددُها)."""
    kept: list[dict] = []
    for e in sorted(events, key=lambda x: str(x.get("date") or ""), reverse=True):
        twin = next((k for k in kept if same_event(k, e)), None)
        first = e.get("first_date") or e.get("date")
        if twin is None:
            kept.append({**e, "first_date": first, "filings": e.get("filings") or 1})
        else:
            twin["filings"] += e.get("filings") or 1
            twin["first_date"] = min(str(twin.get("first_date") or first), str(first or ""))
    return kept


KIND_AR = {"contract": "عقد", "acquisition": "استحواذ", "losses": "خسائرُ متراكمة",
           "regulator": "جهةٌ رقابية", "litigation": "قضاء", "leadership": "قيادة"}
NEGATIVE = frozenset({"losses", "regulator", "litigation", "leadership"})


async def for_display(symbol: str, limit: int = 12) -> dict:
    """← {events:[{date, kind, kind_ar, negative, title, url, value, months, annual, counted, why_not, counterparty}], …}"""
    from app.services import cache
    from app.services.material_events import events_for
    from app.services.tadawul_disclosure import detail
    sym = "".join(ch for ch in str(symbol or "") if ch.isdigit())[:4]
    ck = f"events:view:v2:{sym}"                                      # v2: الحدثُ الواحد بندٌ واحد
    hit = cache.get(ck)
    if hit is not None:
        return hit
    ev = await events_for(sym)
    out = []
    for e in dedupe(ev.get("events") or [])[:limit]:
        d = await detail(e["url"]) if e.get("url") else None
        out.append({
            "date": e.get("date"), "kind": e.get("kind"), "kind_ar": KIND_AR.get(e.get("kind"), e.get("kind")),
            "negative": e.get("kind") in NEGATIVE,
            "title": ((d or {}).get("title") or e.get("title") or "").strip(),   # العنوانُ العربيّ من صفحة الإفصاح
            "url": e.get("url"), "value": e.get("value"), "months": e.get("months"), "annual": e.get("annual"),
            "counted": e.get("counted"), "why_not": e.get("why_not"), "counterparty": e.get("counterparty"),
            "pct": e.get("pct"),
            "first_date": e.get("first_date") if e.get("filings", 1) > 1 else None, "filings": e.get("filings", 1),
        })
    # والعنوانُ العربيّ قد يكشف تكراراً لم يكشفه الإنجليزيّ
    out = dedupe(out)
    res = {"symbol": sym, "events": out, "backlog_annual": ev.get("backlog_annual"),
           "backlog_ratio": ev.get("backlog_ratio"), "asof": ev.get("asof")}
    # ‏D656: صفرُ أحداثٍ قد يكون تعذّرَ جلبٍ لحظيّاً من «تداول» لا غياباً — قِيس: «الغاز» صفرٌ في 16:59 وثلاثةٌ في 17:01،
    # وكان الصفرُ يُحفظ يوماً فتختفي البطاقة. فما وصل يُحفظ لقطةً، والصفرُ لا يُحفظ إلا دقائق ويُعاد جلبُه، ويُعرض آخرُ ما عُرف
    # إن كان حديثاً (أسبوعاً) — فلا يبدو حدثٌ محذوفاً وهو لم يُحذف.
    from app.services import lastgood
    snap = f"events:view:{sym}"
    if out:
        lastgood.save(snap, res)
        cache.set(ck, res, 24 * 60 * 60)
        return res
    cache.expire_keys([f"events:v1:{sym}"], ttl=60)
    prev = lastgood.load(snap)
    try:
        import datetime as _dt
        fresh = isinstance(prev, dict) and prev.get("events") and \
            (_dt.date.today() - _dt.date.fromisoformat(str(prev.get("asof"))[:10])).days <= 7
    except ValueError:
        fresh = False
    if fresh:
        res = {k: v for k, v in prev.items() if not str(k).startswith("_")}
    cache.set(ck, res, 10 * 60)
    return res
