"""سجلُّ التحقّق — المحرّكُ يُقاس بالزمن لا بالرأي (‏D638).

بطلب المالك بعد تجميد الإصدار الأوّل: «بناءُ محرّكاتٍ لا نحتاج شيئاً بعدها من قوّتها وتطوّرها أيضاً على مدى
الزمن». وكلُّ ما قِسناه حتى الآن يقارن تقديرَنا بأهداف المحلّلين — وهي رأيٌ آخر لا حقيقة. والاختبارُ الصادقُ
لكلمتي «السعر العادل» هو الزمن: هل يتّجه السعرُ إلى ما قدّرناه؟

فيُسجَّل كلَّ يوم تداولٍ تقديرُ كلّ شركة (السعر · القيمة · الثقة · المعايرة · الجودة · القرار · هدفُ المحلّلين ·
بصمةُ المحرّك التي أنتجته)، ثمّ يُقاس بعد 90 و180 و365 يوماً بما حدث فعلاً — والسعرُ اللاحق من السجلّ نفسِه
معدَّلاً بأحداث رأس المال من دفتر التجزئة. وما لا يُسجَّل اليومَ لا يُستعاد غداً: الساعةُ تبدأ الآن.

الملفّاتُ في `/app/data/engine_ledger/<سنة-شهر>.jsonl` — مجلّدٌ مربوطٌ يبقى عبر النشر.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import statistics

HORIZONS = (90, 180, 365)


def _dir(dirpath: str | None = None) -> pathlib.Path:
    d = pathlib.Path(dirpath or os.environ.get("ENGINE_LEDGER_DIR")
                     or ("/app/data/engine_ledger" if os.path.isdir("/app/data") else "data/engine_ledger"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _fingerprint() -> str | None:
    try:
        root = pathlib.Path(__file__).resolve().parents[3]
        base = root / "scripts/audit/engine_baseline.json"
        if not base.exists():
            base = pathlib.Path("/app/scripts/audit/engine_baseline.json")
        return json.loads(base.read_text(encoding="utf-8")).get("fingerprint") if base.exists() else None
    except Exception:                                              # noqa: BLE001
        return None


def current_rows() -> list[dict]:
    """صفوفُ اليوم من مخزن المسحة ولقطة الفرز ومخزن الأحكام — قراءةٌ فقط، لا حساب."""
    from app.data.market_universe import MARKET_UNIVERSE
    from app.data.universe import main_market
    from app.services import lastgood
    from app.services.content_engine import fund_store_load
    from app.services.market_screener import get_cached_screener
    store = fund_store_load()
    deep = lastgood.load("governance:deep") or {}
    scr = {str(r.get("symbol")).replace(".SR", ""): r for r in (get_cached_screener() or [])}
    out = []
    for s, meta in main_market(MARKET_UNIVERSE).items():
        r, st = scr.get(s) or {}, store.get(s) or {}
        px = r.get("price")
        if not isinstance(px, (int, float)) or px <= 0:
            continue
        d = (deep.get(s) or {}).get("decision")
        out.append({"s": s, "sec": meta.get("sector"), "px": px,
                    "fv": st.get("fair_value"), "conf": st.get("fair_value_conf"),
                    "cal": st.get("fair_value_calibrated"), "q": st.get("finance_score"),
                    "dec": (d.get("raw") or d.get("label")) if isinstance(d, dict) else d,
                    "at": r.get("analyst_target")})
    return out


def snapshot(rows: list[dict] | None = None, today: dt.date | None = None, dirpath: str | None = None) -> int:
    """يكتب صفوفَ اليوم مرّةً واحدة (يومٌ مسجَّلٌ لا يُكتب ثانيةً). ← عددُ ما كُتب."""
    today = today or dt.date.today()
    d = _dir(dirpath)
    idx = d / "dates.txt"
    done = set(idx.read_text().split()) if idx.exists() else set()
    if today.isoformat() in done:
        return 0
    rows = current_rows() if rows is None else rows
    if not rows:
        return 0
    fp = _fingerprint()
    with open(d / f"{today:%Y-%m}.jsonl", "a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps({"d": today.isoformat(), "fp": fp, **r}, ensure_ascii=False) + "\n")
    with open(idx, "a") as f:
        f.write(today.isoformat() + "\n")
    return len(rows)


def load(dirpath: str | None = None) -> list[dict]:
    out = []
    for p in sorted(_dir(dirpath).glob("*.jsonl")):
        for ln in p.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(ln))
            except ValueError:
                continue
    return out


def _spearman(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 5:
        return None
    rank = lambda v: {i: r for r, i in enumerate(sorted(range(len(v)), key=lambda k: v[k]))}   # noqa: E731
    rx, ry = rank(xs), rank(ys)
    a, b = [rx[i] for i in range(len(xs))], [ry[i] for i in range(len(ys))]
    ma, mb = statistics.fmean(a), statistics.fmean(b)
    num = sum((p - ma) * (q - mb) for p, q in zip(a, b))
    den = (sum((p - ma) ** 2 for p in a) * sum((q - mb) ** 2 for q in b)) ** 0.5
    return round(num / den, 3) if den else None


def outcomes(rows: list[dict] | None = None, today: dt.date | None = None, factor=None) -> dict:
    """تقديرُ يومٍ مضى عليه الأفقُ ← ما حدث فعلاً. لكلّ أفق: العدد · إصابةُ الاتجاه · ارتباطُ الرتبة بين الصعود المقدَّر
    والعائد المحقَّق · نسبةُ الفجوة التي أُغلقت (وسيط) — والكلُّ مقسومٌ بالثقة والمعايرة.
    `factor(sym, d0, d1)`: معاملُ أحداث رأس المال بين يومين (الافتراضيّ من دفتر التجزئة)."""
    rows = load() if rows is None else rows
    today = today or dt.date.today()
    if factor is None:
        def factor(sym, d0, d1):
            try:
                from app.services.split_watch import factor_after
                return factor_after(sym, d0) / (factor_after(sym, d1) or 1)
            except Exception:                                      # noqa: BLE001
                return 1.0
    by_sym: dict[str, dict[str, float]] = {}
    for r in rows:
        by_sym.setdefault(r["s"], {})[r["d"]] = r["px"]
    res: dict = {}
    for h in HORIZONS:
        pts = []
        for r in rows:
            if not isinstance(r.get("fv"), (int, float)) or not r.get("px"):
                continue
            d0 = dt.date.fromisoformat(r["d"])
            if (today - d0).days < h:
                continue
            series = by_sym.get(r["s"]) or {}
            later = [k for k in series if abs((dt.date.fromisoformat(k) - d0).days - h) <= 5]
            if not later:
                continue
            d1 = min(later, key=lambda k: abs((dt.date.fromisoformat(k) - d0).days - h))
            realized = series[d1] * (factor(r["s"], r["d"], d1) or 1) / r["px"] - 1
            up = r["fv"] / r["px"] - 1
            pts.append({"up": up, "real": realized, "conf": r.get("conf"), "cal": r.get("cal"), "sec": r.get("sec")})
        if not pts:
            continue

        def summ(ps):
            hit = [((p["up"] > 0) == (p["real"] > 0)) for p in ps if abs(p["up"]) > 0.05]
            closed = [p["real"] / p["up"] for p in ps if abs(p["up"]) > 0.05]
            return {"n": len(ps), "hit": round(sum(hit) / len(hit), 3) if hit else None,
                    "rank_corr": _spearman([p["up"] for p in ps], [p["real"] for p in ps]),
                    "gap_closed": round(statistics.median(closed), 3) if closed else None}
        res[h] = {"all": summ(pts),
                  "by_conf": {c: summ([p for p in pts if p["conf"] == c]) for c in ("مرتفعة", "متوسطة", "منخفضة")
                              if any(p["conf"] == c for p in pts)},
                  "uncalibrated": summ([p for p in pts if p["cal"] is False]) if any(p["cal"] is False for p in pts) else None}
    return res
