"""‏D596: جدولُ «المعلومات المالية» في صفحة الشركة على «تداول» — الطبقةُ المعتمدة لقوائم السوق كلِّه.

بأمر المالك بعد أن صوّر الجدول: «اجعلها الطريقة المعتمدة لجميع السوق».
قِيس (profile_vs_xbrl_door على 46 ورقة): الجدولُ أحدثُ من ملفّات XBRL في 26، ومثلُها في 14،
وأقدمُ في 6 فقط — وملفّاتُ XBRL متوقّفةٌ عند 2022 لأكثر شركات التأمين. والجدولُ صفحةٌ واحدةٌ
(نحو ثانيةٍ للورقة) لا ثمانيةُ ملفّاتٍ تُحلَّل، ويُحفظ مرّةً فيقرؤه المحرّكُ من المخزن.

البنية (مقيسة · profile_fin_door3): جدولان بالصيغة الموحَّدة — سنويٌّ (ثلاثُ سنوات) وربعيٌّ (أربعةُ أرباع)،
كلٌّ فيه الميزانيةُ ثمّ قائمةُ الدخل ثمّ التدفّقات، و«All Figures in Thousands». والدخلُ للربع نفسِه،
والتدفّقاتُ تراكميةٌ من أوّل السنة. والسالبُ يأتي في خانتين ('' ثمّ '-123') فتُحذف الفارغة.

الدمجُ مع XBRL (`merge`): الفترةُ بتاريخها؛ ما في XBRL يبقى (أوفى بنوداً)، والجدولُ يضيف الفتراتِ
التي لا يملكها XBRL ويملأ الخاناتِ الفارغة — ويُوسَم المصدر.
"""
from __future__ import annotations

import re
from datetime import date

from loguru import logger

STORE = "tfin:{}"
SOURCE = "تداول — المعلومات المالية"
_UNIT = {"thousands": 1e3, "millions": 1e6, "units": 1.0, "billions": 1e9}
# البندُ ← المفتاحُ في مخطّط XBRL نفسِه (فلا يتغيّر قارئٌ واحد)
_LABELS = (
    ("total assets", "total_assets"),
    ("total liabilities and shareholders equity", None),
    ("total liabilities", "total_liabilities"),
    ("total shareholders equity", "equity"),
    ("total revenue", "revenue"),
    ("net profit (loss) before zakat", "pretax_income"),
    ("zakat and income tax", "_zakat"),
    ("net profit (loss) attributable to shareholders", "net_income"),
    ("total comprehensive income", "_comprehensive"),
    ("profit (loss) per share", "eps"),
    ("net cash from operating", "operating_cash_flow"),
    ("net cash from investing", "_cfi"),
    ("net cash from financing", "_cff"),
    ("cash and cash equivalents, end", "ending_cash"),
)
_CUMULATIVE = ("operating_cash_flow", "_cfi", "_cff")       # التدفّقاتُ من أوّل السنة


def _cells(tr: str) -> list[str]:
    return [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c)).strip()
            for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", tr, re.S | re.I)]


def _num(x: str) -> float | None:
    x = (x or "").replace(",", "").strip()
    if x in ("", "-", "—"):
        return None
    try:
        return float(x)
    except ValueError:
        return None


def _key(label: str) -> str | None:
    low = label.lower()
    for tag, key in _LABELS:
        if low.startswith(tag):
            return key
    return None


def parse_table(html_table: str) -> list[dict] | None:
    """جدولٌ بالصيغة الموحَّدة ← فتراتٌ بمخطّط XBRL (بالريال) — أو None إن لم يكن منها."""
    rows = [c for c in (_cells(tr) for tr in re.findall(r"<tr.*?</tr>", html_table, re.S | re.I)) if any(c)]
    if not rows or not rows[0] or rows[0][0].strip().lower() != "balance sheet":
        return None
    if not any(r and r[0].lower().startswith("total shareholders equity (after") for r in rows):
        return None                                  # الصيغةُ القديمة (2022 وما قبلها) لا تُقرأ هنا
    dates = [d for d in rows[0][1:] if re.fullmatch(r"20\d\d-\d\d-\d\d", d)]
    if not dates:
        return None
    # ‏D601: الوحدةُ لكلّ عمودٍ لا للجدول — قِيس: ولاء 2023 بالآلاف و2024–2025 بغيرها، فقُرئت حقوقُها
    # 1.68 مليوناً بدل 1.68 مليار. وعمودٌ وحدتُه مجهولةٌ لا يُقرأ (لا يُفترض).
    units = [1e3] * len(dates)
    for r in rows:
        if r and r[0].lower().startswith("all figures in"):
            vals_u = [v for v in r[1:] if v != ""][:len(dates)]
            units = [_UNIT.get(v.strip().lower()) for v in vals_u] + [None] * (len(dates) - len(vals_u))
    periods = [{"as_of": d, "year": int(d[:4]), "source": SOURCE} for d in dates]   # رقماً كـXBRL (D598)
    for r in rows[1:]:
        if not r:
            continue
        k = _key(r[0])
        if not k:
            continue
        vals = [v for v in r[1:] if v != ""][:len(dates)]
        for p, v, u in zip(periods, vals, units):
            n = _num(v)
            if n is None or (u is None and k != "eps"):
                continue
            p.setdefault(k, n if k == "eps" else n * u)
    return [p for p in periods if len(p) > 3]


def parse_page(html: str) -> dict:
    """صفحةُ الشركة ← {annual, quarterly}: الجدولُ الذي تواريخُه كلُّها نهايةُ سنةٍ سنويّ، وغيرُه ربعيّ."""
    annual: dict[str, dict] = {}
    quarterly: dict[str, dict] = {}
    for t in re.findall(r"<table.*?</table>", html or "", re.S | re.I):
        ps = parse_table(t)
        if not ps:
            continue
        bucket = annual if all(p["as_of"].endswith("-12-31") for p in ps) and len(ps) <= 3 else quarterly
        for p in ps:
            cur = bucket.setdefault(p["as_of"], {})
            for k, v in p.items():
                cur.setdefault(k, v)
    q = sorted(quarterly.values(), key=lambda p: p["as_of"])
    # التدفّقاتُ تراكميةٌ من أوّل السنة ← للربع نفسِه: يُطرح الربعُ السابقُ من السنة نفسِها إن وُجد
    by = {p["as_of"]: p for p in q}
    for p in q:
        y, m = p["as_of"][:4], int(p["as_of"][5:7])
        prev = by.get(f"{y}-{m - 3:02d}-{30 if m - 3 in (6, 9) else 31}") if m > 3 else None
        for k in _CUMULATIVE:
            if k not in p:
                continue
            p["_ytd_" + k] = p[k]
            if m == 3:
                continue
            if prev is not None and ("_ytd_" + k) in prev:
                p[k] = p[k] - prev["_ytd_" + k]
            else:
                p.pop(k)                             # لا يُنسب تراكمُ أشهرٍ لربعٍ واحد
    return {"annual": sorted(annual.values(), key=lambda p: p["as_of"]), "quarterly": q}


def parse_issued_shares(html: str) -> float | None:
    """‏D600: «Total Issued Shares» من ملفّ الشركة في الصفحة نفسِها — حَكَمُ عدد الأسهم بعد المنح والتجزئة.
    قِيس: المتحدة الدولية 75 مليوناً والقوائمُ تقول 25 (فتضخّم سعرُها العادل ثلاثاً)، وأرامكو 242 ملياراً."""
    txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " | ", html or ""))
    m = re.search(r"Total Issued Shares[ |]*([\d,]{4,})", txt)
    if not m:
        return None
    try:
        v = float(m.group(1).replace(",", ""))
    except ValueError:
        return None
    return v if v > 0 else None


def issued_shares(symbol: str) -> float | None:
    v = (read(symbol) or {}).get("issued_shares")
    return float(v) if isinstance(v, (int, float)) and v > 0 else None


def read(symbol: str) -> dict | None:
    from app.services import lastgood
    rec = lastgood.load(STORE.format(str(symbol).replace(".SR", "").strip()))
    return rec if isinstance(rec, dict) else None


def periods(symbol: str, kind: str) -> list[dict]:
    out = []
    for p in (read(symbol) or {}).get(kind) or []:
        p = dict(p)
        if isinstance(p.get("year"), str) and p["year"].isdigit():
            p["year"] = int(p["year"])            # D598: سنةٌ نصّيةٌ تكسر الترتيب مع XBRL
        out.append(p)
    return out


def merge(xbrl: list[dict], prof: list[dict]) -> list[dict]:
    """فتراتُ XBRL والجدول بتاريخها: XBRL يغلب في خاناته، والجدولُ يضيف ويملأ."""
    by = {str(p.get("as_of")): dict(p) for p in xbrl or [] if isinstance(p, dict)}
    for p in prof or []:
        a = str(p.get("as_of"))
        if a not in by:
            by[a] = {k: v for k, v in p.items() if not k.startswith("_ytd_")}
            continue
        cur = by[a]
        for k, v in p.items():
            if not k.startswith("_ytd_") and cur.get(k) is None:
                cur[k] = v
    return sorted(by.values(), key=lambda p: str(p.get("as_of")))


async def read_symbol(symbol: str) -> dict:
    """يقرأ صفحةَ الشركة ويحفظ جدولَها — ولا يمحو فتراتٍ محفوظةً لم تعد في الجدول."""
    from app.services import lastgood
    from app.services.tadawul_http import fetch
    from app.services.tadawul_market import row_for
    from app.services.tadawul_xbrl import ORIGIN
    sym = str(symbol).replace(".SR", "").strip()
    url = (row_for(sym) or {}).get("company_url")
    if not url:
        return {"symbol": sym, "ok": False, "why": "لا رابطَ لصفحة الشركة"}
    st, page = await fetch(ORIGIN + url if url.startswith("/") else url)
    if st != 200 or not page:
        return {"symbol": sym, "ok": False, "why": f"HTTP {st}"}
    got = parse_page(page)
    iss = parse_issued_shares(page)
    del page
    if not got["annual"] and not got["quarterly"]:
        return {"symbol": sym, "ok": False, "why": "لا جدولَ بالصيغة الموحَّدة"}
    old = read(sym) or {}
    rec = {"at": date.today().isoformat()}
    if iss or old.get("issued_shares"):
        rec["issued_shares"] = iss or old.get("issued_shares")
    for kind in ("annual", "quarterly"):
        rec[kind] = merge(got[kind], old.get(kind) or [])
    lastgood.save(STORE.format(sym), rec)
    last = max([p["as_of"] for p in rec["annual"] + rec["quarterly"]] or [None])
    return {"symbol": sym, "ok": True, "latest": last}


async def refresh(symbols: list[str] | None = None, conc: int = 2) -> dict:
    """السوقُ كلُّه (أو رموزٌ بأعيانها) — بتوازٍ خفيف، فالصفحةُ قرابةَ ميجابايت."""
    import asyncio
    if symbols is None:
        from app.data.market_universe import MARKET_UNIVERSE
        from app.data.universe import main_market
        symbols = sorted(main_market(MARKET_UNIVERSE).keys())
    sem = asyncio.Semaphore(conc)
    rep = {"symbols": len(symbols), "ok": 0, "failed": 0, "why": {}}

    async def one(s):
        async with sem:
            try:
                r = await read_symbol(s)
            except Exception as e:                                # noqa: BLE001
                r = {"ok": False, "why": type(e).__name__}
            if r.get("ok"):
                rep["ok"] += 1
            else:
                rep["failed"] += 1
                rep["why"][r.get("why")] = rep["why"].get(r.get("why"), 0) + 1
    await asyncio.gather(*(one(s) for s in symbols))
    logger.info(f"المعلوماتُ المالية من تداول: {rep}")
    return rep
