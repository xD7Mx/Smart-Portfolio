"""كاشف D674 (قراءةٌ فقط): من يخالف عددُ أسهم قوائمه عددَ السوق بين 15٪ ومرّةٍ ونصف — وما شاهدُ نوع الزيادة؟

حدُّ 15٪ يلتقط المنحَ (الرمز 0.70) ولا يميّز الاكتتابَ (أسهمٌ ونقدٌ معاً — ميدغلف 104.8 ← 138.2 مليوناً). فلكلّ شركةٍ في
النطاق: النسبة، وتاريخُ آخر قوائم، ونموُّ الحقوق بين آخر فترتين (الاكتتابُ يرفعها بحصيلته والمنحةُ لا)، وأحداثُ رأس المال
المسجّلة (سجلُّ التجزئة · مفكرةُ السوق في القاعدة) — ليُبنى التمييزُ على شاهدٍ مقيسٍ لا على ظنّ.

    docker exec sp_backend python /app/scripts/audit/d674_shares_door.py
"""
import asyncio
import sys

sys.path.insert(0, "/app")


async def main():
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.market import MarketEvent
    from app.data.market_universe import MARKET_UNIVERSE
    from app.data.universe import main_market
    from app.services import tadawul_market as TM, lastgood
    from app.services.tadawul_xbrl import for_symbol as X
    from app.services.tadawul_financials import issued_shares
    from app.services.fair_value_models import _shares_of, _n
    rows = TM.usable_rows()[0] or {}
    ledger = lastgood.load("split:ledger") or {}
    issued_hist = lastgood.load("split:issued") or {}
    since = datetime.now(timezone.utc) - timedelta(days=730)
    async with AsyncSessionLocal() as db:
        evs = (await db.execute(select(MarketEvent).where(MarketEvent.event_date >= since))).scalars().all()
    cap_ev: dict[str, list] = {}
    for e in evs:
        t = str(getattr(e.event_type, "value", e.event_type))
        if t in ("BONUS", "RIGHTS_ISSUE", "SPLIT") or any(
                w in str(e.description or "") for w in ("منحة", "حقوق أولوية", "زيادة رأس", "تخفيض رأس")):
            cap_ev.setdefault(str(e.company_symbol or "").replace(".SR", ""), []).append(
                f"{t} {str(e.event_date)[:10]} {str(e.description or '')[:70]}")
    n_in, n_all = 0, 0
    for s, meta in sorted(main_market(MARKET_UNIVERSE).items()):
        me = rows.get(s) or {}
        px = _n(me.get("price"))
        annual, quarterly = X(s, "annual") or [], X(s, "quarterly") or []
        st = _shares_of(annual, quarterly) if annual or quarterly else None
        iss = issued_shares(s)
        mc = _n(me.get("market_cap"))
        mkt = iss or (mc / px if mc and px else None)
        if not (st and mkt):
            continue
        n_all += 1
        r = mkt / st
        if not (1.15 < r < 1.5 or 1 / 1.5 < r < 1 / 1.15):
            continue
        n_in += 1
        per = sorted(quarterly + annual, key=lambda p: str(p.get("as_of") or f"{p.get('year')}-12-31"))
        eq = [(str(p.get("as_of") or p.get("year"))[:10], _n(p.get("equity"))) for p in per if _n(p.get("equity"))]
        g = (eq[-1][1] / eq[-2][1] - 1) if len(eq) >= 2 and eq[-2][1] else None
        # ‏شاهدُ الشركة نفسِها: ربحُ آخر إعلان نتائج ÷ ربحيةِ سهمه — هل يقول عددَ السوق (تغيّرٌ حقيقيّ) أم عددَ القوائم (تعريفُ ربح)؟
        try:
            from app.services.results_announcements import latest as _ra
            _q = ((_ra(s) or {}).get("quarter") or {})
            _ni, _eps = _n(_q.get("net_income")), _n(_q.get("eps"))
            ann = abs(_ni / _eps) if _ni and _eps and abs(_eps) > 0.01 else None
            ann_at = (_ra(s) or {}).get("as_of")
        except Exception:                                          # noqa: BLE001
            ann, ann_at = None, None
        print(f"{s} {meta.get('name_ar')} ({meta.get('sector')}) · القوائم {st / 1e6:,.1f}م · السوق {mkt / 1e6:,.1f}م · ×{r:.3f}"
              f" · الإعلان {('%.1fم' % (ann / 1e6)) if ann else '—'} ({ann_at or '—'})"
              f" · آخرُ قوائم {eq[-1][0] if eq else '—'} · نموُّ الحقوق {('%+.1f%%' % (g * 100)) if g is not None else '—'}"
              f" ({eq[-2][0] if len(eq) >= 2 else '—'})")
        if ledger.get(s):
            print(f"     سجلُّ التجزئة: {ledger[s]}")
        if issued_hist.get(s):
            print(f"     الأسهمُ المصدرة المحفوظة: {issued_hist[s]}")
        for x in (cap_ev.get(s) or [])[:4]:
            print(f"     حدث: {x}")
    print(f"\n@@D674@@ في النطاق {n_in} من {n_all} · أحداثُ رأس مال في القاعدة (سنتان) لـ{len(cap_ev)} شركة")


asyncio.run(main())
