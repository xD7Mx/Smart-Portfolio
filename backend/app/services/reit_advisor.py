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


_AR_MONTHS = {"يناير": 1, "فبراير": 2, "مارس": 3, "أبريل": 4, "ابريل": 4, "مايو": 5, "يونيو": 6, "يوليو": 7,
              "أغسطس": 8, "اغسطس": 8, "سبتمبر": 9, "أكتوبر": 10, "اكتوبر": 10, "نوفمبر": 11, "ديسمبر": 12}
_STMT_TITLE = re.compile(r"interim financial statements|interim condensed|annual report|financial statements|"
                         r"القوائم المالية|التقرير السنوي", re.I)


def parse_statement(text: str) -> dict | None:
    """‏D574: ملخّصُ القوائم المالية في إعلان الصندوق ← {as_of, net_assets, net_profit, units, nav, period_return}.

    قِيس (كاشف reit_interim_door): إعلانُ «إتاحة القوائم المالية الأولية» يحمل جدولاً بنهاية الفترة وصافي الأصول
    وصافي الربح وعدد الوحدات وصافي قيمة الوحدة وعائد الفترة — رسميٌّ ولا يصل تبويبَ القوائم في «تداول»."""
    t = text or ""
    t = re.sub(r"المنتهية في\s*[(\s]*م?\s*", "المنتهية في ", t)           # «( م30/06/2026» ← «30/06/2026» (ميفك)
    m = re.search(r"المنتهية في\s*(\d{1,2})[\s-]+([^\s\d-]+?)[\s-]+(20\d\d)", t)
    as_of = None
    if m and m.group(2).rstrip("م") in _AR_MONTHS:
        as_of = f"{int(m.group(3)):04d}-{_AR_MONTHS[m.group(2).rstrip('م')]:02d}-{int(m.group(1)):02d}"
    if not as_of:
        # صيغٌ رقمية (قِيس على سبعة صناديق): 30/06/2026م · 2026/06/30 م · (2026/06/30) · 2026-06-30
        g = re.search(r"المنتهية في\s*\(?\s*(20\d\d)[/-](\d{1,2})[/-](\d{1,2})", t)
        if g:
            as_of = f"{g.group(1)}-{int(g.group(2)):02d}-{int(g.group(3)):02d}"
        else:
            g = re.search(r"المنتهية في\s*\(?\s*(\d{1,2})[/-](\d{1,2})[/-](20\d\d)", t)
            as_of = f"{g.group(3)}-{int(g.group(2)):02d}-{int(g.group(1)):02d}" if g else None

    def num(label):
        mm = re.search(label + r"[^|\n]*\|\s*[%٪]?\s*(\(?-?[0-9][0-9,]*(?:\.[0-9]+)?\)?)", t)
        if not mm:
            return None
        v = mm.group(1)
        neg = v.startswith("(") or v.startswith("-")
        f = _f(v.strip("()-"))
        return -f if (f is not None and neg) else f
    out = {"as_of": as_of, "net_assets": num(r"صافي الأصول"), "net_profit": num(r"صافي الربح"),
           "units": num(r"عدد الوحدات"), "nav": num(r"صافي قيمة الوحدة"), "period_return": num(r"العائد للفترة")}
    return out if as_of and (out["nav"] or out["net_assets"]) else None


def latest_statement(symbol: str) -> dict | None:
    """أحدثُ قوائمٍ أعلنها الصندوق (من إعلاناته) — لبوّابة القِدَم ولقراءة المستشار."""
    raw = cached(symbol) or {}
    st = sorted([x for x in raw.get("stmts") or [] if x.get("as_of")], key=lambda x: x["as_of"])
    return st[-1] if st else None


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
        known_st = {x.get("id"): x for x in old.get("stmts") or []}
        stmts = []
        for it in items:
            title = it.get("title") or ""
            low = title.lower()
            # ‏D574: إعلانُ القوائم المالية (الأولية والسنوية) — ملخّصُه يُقرأ
            if _STMT_TITLE.search(title) and "valuation" not in low and "تقييم" not in title:
                if it.get("id") in known_st:
                    stmts.append(known_st[it["id"]])
                else:
                    det = await D.detail(it["url"])
                    sm = parse_statement((det or {}).get("text") or "")
                    if sm:
                        stmts.append({**sm, "id": it.get("id"), "announced": it.get("date")})
                continue
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
        if not stmts and old.get("stmts"):
            stmts = old["stmts"]
        raw = {"at": date.today().isoformat(), "dists": dists, "vals": [v for v in vals if v], "stmts": stmts}
        if dists:
            lastgood.save(key, raw)
    if not raw.get("dists"):
        return None
    return summarize(raw["dists"], raw.get("vals") or [], price)


def cached(symbol: str) -> dict | None:
    from app.services import lastgood
    raw = lastgood.load(STORE.format(str(symbol).replace(".SR", "").strip())) or {}
    return raw if raw.get("dists") else None
