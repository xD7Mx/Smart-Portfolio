"""مستشارُ الريت (D554) — ما نشره الصندوقُ نفسُه في «تداول»، لا نماذجُ الشركات.

قال المالك: «الريت نشر تقييمَ أصوله … والتطبيقُ لديه اطّلاعٌ على هذا النشر؛ أريده أن
يملك قدرةَ المستشار المالي». وقِيس (كاشفا reit_census وreit_door):

  · محرّكُ السعر العادل لا يُنتج قيمةً لـ17 ريتاً من 19 (لا XBRL للصناديق)، ولسدكو
    ريت +222٪، والمعروضُ للراجحي ريت (5.80) من المحرّك القديم بمضاعف دفتريّةٍ تاريخيّ
    — أي دون صافي أصوله المنشور بنحو 30٪.
  · وكلُّ إعلان توزيعٍ في «تداول» يحمل: قيمةَ التوزيع للوحدة، ونسبتَه من صافي قيمة
    الأصول، وتاريخَ ذلك الصافي، وتاريخَ الأحقية. فصافي قيمة الأصول للوحدة
    = التوزيع ÷ نسبته — رقمُ المقيِّمَين المعتمدَين نفسُه، بلا اختلاق.
  · وتقاريرُ التقييم النصف سنوية تُعلَن بتواريخها.

فالمستشارُ يجمع: التوزيعاتِ كلَّها بأحقّيتها، وصافيَ الأصول وتاريخَه واتّجاهَه،
والعلاوةَ أو الخصمَ عليه، وعائدَ اثني عشر شهراً، وإيقاعَ التوزيع وموعدَ القادم —
وينبّه إن تأخّر توزيعٌ عن إيقاعه المعتاد.
"""
from __future__ import annotations

import re
import statistics
from datetime import date, timedelta

STORE = "reit:{}"
TTL_DAYS = 1

_NUM = r"([0-9][0-9,]*(?:\.[0-9]+)?)"


def _f(x):
    try:
        return float(str(x).replace(",", ""))
    except (TypeError, ValueError):
        return None


def parse_distribution(text: str) -> dict | None:
    """متنُ إعلان التوزيع ← {amount, nav_pct, nav_date, eligibility, period, total, units}."""
    t = text or ""

    def grab(label, pat=_NUM):
        m = re.search(label + r"[^|\n]*\|\s*[%٪]?\s*" + pat, t)
        return m.group(1) if m else None

    amount = _f(grab(r"قيمة الربح الموزع لكل وحدة"))
    pct = _f(grab(r"نسبة التوزيع من صافي قيمة الأصول \(%\)"))
    def greg(label):
        # التاريخُ الميلاديُّ بعد «الموافق» — لا الهجريُّ الذي يسبقه
        m = re.search(label + r"[^|\n]*\|([^\n]*)", t)
        ds = re.findall(r"(\d{4}-\d{2}-\d{2})", m.group(1)) if m else []
        g = [x for x in ds if x[:2] in ("19", "20")]
        return g[-1] if g else None
    nav_d = greg(r"نسبة التوزيع من صافي قيمة الأصول كما في تاريخ")
    elig = greg(r"أحقية التوزيعات")
    per = re.search(r"فترة استحقاق الأرباح\s*\|\s*([^\n|]+)", t)
    if not amount:
        return None
    nav = round(amount / (pct / 100), 3) if pct and pct > 0 else None
    return {"amount": amount, "nav_pct": pct, "nav": nav,
            "nav_date": nav_d,
            "eligibility": elig,
            "period": per.group(1).strip() if per else None,
            "total": _f(grab(r"إجمالي الأرباح الموزعة")),
            "units": _f(grab(r"عدد الوحدات القائمة"))}


def summarize(dists: list[dict], valuations: list[str], price: float | None, today: date | None = None) -> dict:
    """دالّةٌ نقيّة: التوزيعاتُ وتقاريرُ التقييم ← قراءةُ المستشار."""
    today = today or date.today()
    ds = sorted([d for d in dists if d.get("eligibility")], key=lambda d: d["eligibility"])
    out: dict = {"distributions": ds, "valuations": sorted(valuations, reverse=True)}
    navs = sorted([(d["nav_date"], d["nav"]) for d in ds if d.get("nav") and d.get("nav_date")])
    by_date = {}
    for dte, v in navs:
        by_date[dte] = v
    navs = sorted(by_date.items())
    if navs:
        out["nav_date"], out["nav"] = navs[-1]
        out["nav_history"] = [{"d": d, "v": v} for d, v in navs]
        if len(navs) >= 2:
            out["nav_change"] = round((navs[-1][1] / navs[-2][1] - 1) * 100, 1)
        if price:
            out["premium"] = round((price / navs[-1][1] - 1) * 100, 1)
    cut = (today - timedelta(days=365)).isoformat()
    ttm = [d["amount"] for d in ds if d["eligibility"] > cut and d["eligibility"] <= today.isoformat()]
    if ttm:
        out["ttm"] = round(sum(ttm), 4)
        if price:
            out["yield"] = round(sum(ttm) / price * 100, 2)
    if len(ds) >= 3:
        gaps = [(date.fromisoformat(b["eligibility"]) - date.fromisoformat(a["eligibility"])).days
                for a, b in zip(ds, ds[1:])]
        cad = statistics.median(gaps)
        out["cadence_days"] = int(cad)
        last = date.fromisoformat(ds[-1]["eligibility"])
        out["next_expected"] = (last + timedelta(days=int(cad))).isoformat()
        out["overdue"] = (today - last).days > cad * 1.5
        amts = [d["amount"] for d in ds[-4:]]
        out["last_amount"] = ds[-1]["amount"]
        out["trend"] = ("صاعد" if amts[-1] > amts[0] else "هابط" if amts[-1] < amts[0] else "مستقرّ") if len(amts) >= 2 else None
    return out


async def build(symbol: str, price: float | None = None, force: bool = False) -> dict | None:
    """يقرأ إفصاحاتِ الصندوق في «تداول» (توزيعاتٌ وتقاريرُ تقييم) ويحفظها يوماً."""
    from app.services import lastgood
    from app.services import tadawul_disclosure as D
    sym = str(symbol).replace(".SR", "").strip()
    key = STORE.format(sym)
    old = lastgood.load(key) or {}
    if not force and old.get("at") and (date.today() - date.fromisoformat(old["at"])).days < TTL_DAYS:
        raw = old
    else:
        items = await D.list_for(sym, size=80)
        dists, vals = [], []
        known = {d.get("id"): d for d in old.get("dists") or []}
        for it in items:
            title = it.get("title") or ""
            low = title.lower()
            if "تقييم" in title or "valuation" in low:
                vals.append(it.get("date"))
            if "توزيع" not in title and "distribut" not in low and "dividend" not in low:
                continue
            if it.get("id") in known:
                dists.append(known[it["id"]])
                continue
            det = await D.detail(it["url"])
            d = parse_distribution((det or {}).get("text") or "")
            if d:
                dists.append({**d, "id": it.get("id"), "announced": it.get("date")})
        if not dists and old.get("dists"):
            dists, vals = old["dists"], old.get("vals") or []
        raw = {"at": date.today().isoformat(), "dists": dists, "vals": [v for v in vals if v]}
        if dists:
            lastgood.save(key, raw)
    if not raw.get("dists"):
        return None
    return summarize(raw["dists"], raw.get("vals") or [], price)


def cached(symbol: str) -> dict | None:
    from app.services import lastgood
    raw = lastgood.load(STORE.format(str(symbol).replace(".SR", "").strip())) or {}
    return raw if raw.get("dists") else None
