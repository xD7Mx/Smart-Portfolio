#!/usr/bin/env python3
"""حارسُ D791 — ويدجت الآيفون: نقطةُ ملخّصٍ برمزٍ مستقلّ، وأرقامُها أرقامُ التطبيق (بأمر المالك 2026-11-24).

قال المالك: «أريد على الآيفون ويدجت كبقية التطبيقات لتطبيق المحفظة الذكية». وويدجت الآيفون الأصيلُ لا يصنعه إلا تطبيقٌ أصيلٌ (‏Xcode
على ماك)، فالطريقُ الذي يعمل اليوم تطبيقُ «Scriptable» المجانيّ يقرأ نقطةَ ‏/widget/summary. والحارسُ يحرس الأمانَ والصدق:
  · الرمزُ لا يُخزَّن نصّاً (مُجزَّأٌ ‏sha256)، ويُقارَن بزمنٍ ثابت، ويُرسَل في ترويسةٍ لا في الرابط؛ والخاطئُ والمُلغى ‏401.
  · الأرقامُ من مصدرها الموحّد: الثروةُ وصافي الربح وعائدُ المحفظة كما يحسبها ‏compute_net_profit — لا تعريفٌ ثانٍ؛ و«كلّ المحافظ» جمعُ
    كلٍّ من مرشِّحها؛ وما لا مصدرَ له «غيرُ متوفّر» (‏None) لا صفر.

    python3 scripts/audit/widget_d791.py
    SP_PG_PORT=55432 SP_PG_HOST=/var/tmp/sppg python3 scripts/audit/widget_d791.py
"""
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
fail = 0


def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))


W = (ROOT / "backend/app/api/v1/endpoints/widget.py").read_text(encoding="utf-8")
R = (ROOT / "backend/app/api/v1/router.py").read_text(encoding="utf-8")
S = (ROOT / "frontend/src/lib/widgetScript.ts").read_text(encoding="utf-8")
check('@public_router.get("/summary")' in W and "hmac.compare_digest" in W and "hashlib.sha256" in W and "Header(default=None)" in W
      and 'api_router.include_router(widget.public_router, prefix="/widget"' in R and 'protected.include_router(widget.router, prefix="/widget"' in R
      and "compute_net_profit" in W,
      "١ الملخّصُ عامٌّ برمز الويدجت وحده (ترويسةٌ، مُجزَّأٌ، بزمنٍ ثابت)، وإنشاءُ الرمز وإلغاؤه خلف جلسة المالك، والأرقامُ من المقياس الموحّد")
check('"X-Widget-Token": t' in S and "Keychain.set(KEY, t)" in S and "__ORIGIN__" in S and "spw_" not in S.replace('"spw_…"', ""),
      "٢ السكربتُ يرسل الرمزَ في ترويسة ويحفظه في سلسلة مفاتيح الآيفون — ولا رمزَ مكتوباً فيه")

port, host = os.environ.get("SP_PG_PORT"), os.environ.get("SP_PG_HOST")
if not port:
    print("SKIP ٣–٧ السيناريو الحيّ على Postgres (عيّن SP_PG_PORT و SP_PG_HOST)")
else:
    db = "sp_d791"
    for q in (f"DROP DATABASE IF EXISTS {db}", f"CREATE DATABASE {db}"):
        subprocess.run(["psql", "-h", host, "-p", port, "-U", "sp", "-d", "postgres", "-qc", q], capture_output=True)
    tmp = tempfile.mkdtemp()
    script = r'''
import asyncio, json
from fastapi import HTTPException
async def main():
    from app.core.database import init_db, AsyncSessionLocal
    from sqlalchemy import text
    await init_db()
    from app.services.market_data import market_service, PriceData
    PX = {"2222.SR": 27.5, "1120.SR": 60.0, "^TASI.SR": 11500.0}
    CH = {"2222.SR": 1.0, "1120.SR": -2.0, "^TASI.SR": 0.5}
    async def fake_price(sym):
        return PriceData(sym, PX[sym], 0.0, CH[sym]).to_dict() if sym in PX else None
    market_service.get_price = fake_price
    from app.services import cache
    for s, c in CH.items():                                  # تغيّرُ اليوم يُقرأ من مخزن السعر — كما في التطبيق
        cache.set(f"price:yahoo:{s}", PriceData(s, PX[s], 0.0, c), 900)
    from app.core.portfolio_scope import set_scope, reset_scope
    from app.api.v1.endpoints import transactions as T, cash as C, companies as K, portfolios as PF, widget as WG
    from app.services.portfolio_return import compute_net_profit
    out = {}
    async def S(fn, *a, **k):
        async with AsyncSessionLocal() as d:
            try:
                r = await fn(*a, db=d, **k)
                return (r.get("data") if isinstance(r, dict) else None) or "OK"
            except HTTPException as e:
                await d.rollback(); return f"HTTP{e.status_code}"
    async with AsyncSessionLocal() as d:
        pid1 = (await d.execute(text("select id from portfolio order by id limit 1"))).scalar()
    set_scope(pid1, False)
    await S(C.deposit_cash, C.CashDeposit(amount=10000))
    a = await S(K.add_company, K.CompanyCreate(symbol="2222", name_ar="أرامكو"))
    b = await S(K.add_company, K.CompanyCreate(symbol="1120", name_ar="الراجحي"))
    mk = lambda cid, q, p: T.TransactionCreate(company_id=cid, transaction_type="BUY", shares=q, price_per_share=p, transaction_date="2026-07-01")
    await S(T.add_transaction, mk(a["id"], 100, 25.0))
    await S(T.add_transaction, mk(b["id"], 50, 55.0))
    reset_scope()
    # قاعدةٌ جديدة: المحفظةُ الرئيسية «غيرُ مؤرشفة» صراحةً، والافتراضيةُ هي هي — لا محفظةً رئيسيةً ثانية
    from app.core.portfolio_context import _default_portfolio_id
    async with AsyncSessionLocal() as d:
        arch = (await d.execute(text("select is_archived from portfolio where id = :i"), {"i": pid1})).scalar()
        dflt = await _default_portfolio_id(d)
        nps = (await d.execute(text("select count(*) from portfolio"))).scalar()
    out["boot"] = [arch, dflt == pid1, nps]
    # محفظةٌ ثانية: إيداعٌ وحده
    p2 = await S(PF.create_portfolio, PF.PortfolioCreate(name="الثانية"))
    set_scope(p2["id"], False)
    await S(C.deposit_cash, C.CashDeposit(amount=2000))
    reset_scope()
    out["none"] = await S(WG.widget_summary, None, None)
    tok = await S(WG.token_create)
    out["tok_shape"] = isinstance(tok, dict) and str(tok.get("token", "")).startswith("spw_") and len(tok["token"]) > 40
    async with AsyncSessionLocal() as d:
        raw = (await d.execute(text("select value from settings where key='widget_token'"))).scalar()
    out["plain_stored"] = tok["token"] in (raw or "")
    out["wrong"] = await S(WG.widget_summary, None, "spw_wrong")
    one = await S(WG.widget_summary, None, tok["token"])
    # المرجعُ بعد الملخّص: الملخّصُ يحدّث الأسعارَ ويحفظها كما تفعل صفحةُ الحيازات، فيقرأ المقياسُ الموحّد القيمَ نفسَها
    set_scope(pid1, False)
    async with AsyncSessionLocal() as d:
        ref = await compute_net_profit(d)
    reset_scope()
    out["one"] = {k: one.get(k) for k in ("wealth", "market_value", "cash", "net_profit", "return_pct", "day_change", "day_change_pct", "count")}
    out["one_tasi"] = one.get("tasi")
    out["ref"] = ref
    out["movers"] = [m["symbol"] for m in one.get("movers", [])]
    allp = await S(WG.widget_summary, "all", tok["token"])
    out["all"] = {k: allp.get(k) for k in ("wealth", "net_profit", "portfolio")}
    # عبر الخادم نفسِه (لا الدالّةِ وحدها): الملخّصُ برمز الويدجت بلا جلسة، والرمزُ في الرابط مرفوض، وإدارةُ الرمز خلف الجلسة
    import httpx
    from main import app
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t/api/v1", timeout=120) as c:
        r1 = await c.get("/widget/summary", headers={"X-Widget-Token": tok["token"]})
        r2 = await c.get("/widget/summary", params={"x_widget_token": tok["token"], "token": tok["token"]})
        r3 = await c.post("/widget/token")
        r4 = await c.get("/widget/token")
    out["http"] = [r1.status_code, ((r1.json() or {}).get("data") or {}).get("wealth"), r2.status_code, r3.status_code, r4.status_code]
    st = await S(WG.token_status)
    out["status"] = [st.get("active"), st.get("hint") == tok["token"][-4:], bool(st.get("used"))]
    await S(WG.token_revoke)
    out["revoked"] = await S(WG.widget_summary, None, tok["token"])
    # الأسعارُ تُطلب معاً لا سهماً بعد سهم (قِيس على الخادم 13.4 ثانية لعشر حيازات) — وكلُّ سعرٍ يقع على سهمه
    from sqlalchemy import select as _sel
    from sqlalchemy.orm import selectinload as _sil
    from app.models.portfolio import Holding as _H
    from app.api.v1.endpoints.holdings import refresh_holdings_prices as _rhp
    fl = {"now": 0, "max": 0}
    async def slow_price(sym):
        fl["now"] += 1
        fl["max"] = max(fl["max"], fl["now"])
        await asyncio.sleep(0.2)
        fl["now"] -= 1
        return PriceData(sym, PX[sym] + 1, 0.0, CH[sym]).to_dict() if sym in PX else None
    market_service.get_price = slow_price
    set_scope(pid1, False)
    async with AsyncSessionLocal() as d:
        hs = [h for h in (await d.execute(_sel(_H).options(_sil(_H.company)))).scalars().all() if float(h.quantity or 0) > 0]
        await _rhp(d, hs)
        out["conc"] = [fl["max"], len(hs), sorted([h.company.symbol, float(h.last_price)] for h in hs)]
    reset_scope()
    market_service.get_price = fake_price
    print("RESULT " + json.dumps(out, ensure_ascii=False, default=str))
asyncio.run(main())
'''
    env = dict(os.environ, DATABASE_URL=f"postgresql://sp@/{db}?host={host}&port={port}",
               LASTGOOD_PATH=f"{tmp}/lg.json", SP_STATE_DIR=tmp, SP_STATUS_LOG=f"{tmp}/s.log")
    pr = subprocess.run([sys.executable, "-c", script], cwd=str(ROOT / "backend"), env=env, capture_output=True, text=True, timeout=300)
    line = next((ln for ln in pr.stdout.splitlines() if ln.startswith("RESULT ")), None)
    if not line:
        check(False, "٣ السيناريو الحيّ لم يكتمل", (pr.stderr.strip().splitlines() or ["?"])[-1][:300])
    else:
        import json
        o = json.loads(line[7:])
        print("  ", o)
        check(o["none"] == "HTTP401" and o["wrong"] == "HTTP401" and o["revoked"] == "HTTP401" and o["tok_shape"] and not o["plain_stored"],
              "٣ بلا رمزٍ أو برمزٍ خاطئٍ أو مُلغى: ‏401؛ والرمزُ لا يُخزَّن نصّاً (مُجزَّأ) ويُعرض مرّةً عند إنشائه")
        one, ref = o["one"], o["ref"]
        # ‏2222: 100 × 27.5 = 2,750 · ‏1120: 50 × 60 = 3,000 · النقد 10,000 − 2,500 − 2,750 = 4,750 ⇐ الثروة 10,500
        check(one["wealth"] == ref["wealth"] == 10500.0 and one["net_profit"] == ref["net_profit"] == 500.0
              and one["return_pct"] == ref["capital_growth_pct"] and one["market_value"] == 5750.0 and one["cash"] == 4750.0 and one["count"] == 2,
              "٤ الثروةُ وصافي الربح وعائدُ المحفظة هي أرقامُ المقياس الموحّد نفسُها (10,500 · ‏+500 · 500 ÷ 5,250)", str(one))
        # تغيّرُ اليوم: 2,750 × 1 ÷ 101 + 3,000 × (−2) ÷ 98 = 27.23 − 61.22 = −33.99
        exp = round(2750 * 1 / 101 + 3000 * -2 / 98, 2)
        check(abs((one["day_change"] or 0) - exp) < 0.02 and one["day_change_pct"] is not None and o["movers"][0] == "1120"
              and o["one_tasi"] == {"price": 11500.0, "change_pct": 0.5},
              "٥ تغيّرُ اليوم بالريال من نسبة كلّ سهمٍ وقيمته، والأكثرُ تحرّكاً أوّلاً، وتاسي من مصدر الأسعار", f"{one['day_change']} · {exp} · {o['movers']}")
        check(o["all"]["wealth"] == 12500.0 and o["all"]["net_profit"] == 500.0 and o["all"]["portfolio"] == "كلّ المحافظ",
              "٦ «كلّ المحافظ» (‏pf=all) جمعُ كلّ محفظةٍ من مرشِّحها: 10,500 + 2,000 (وصافي ربح الثانية صفر)", str(o["all"]))
        check(o["status"] == [True, True, True], "٧ حالُ الرمز في الإعدادات: نافذ، وتلميحُ آخر أربعة أحرف، ووقتُ آخر استعمال", str(o["status"]))
        # قبل الإصلاح: ‏[None, False, 2] — العمودُ بلا قيمةٍ فتختفي الرئيسيةُ من كلّ مرشِّح ويُنشئ الافتراضيُّ محفظةً ثانية
        check(o["boot"] == [False, True, 1],
              "٨ قاعدةٌ جديدة: المحفظةُ الرئيسية «غيرُ مؤرشفة» صراحةً وهي الافتراضية — لا تختفي من القوائم ولا تُنشأ رئيسيةٌ ثانية", str(o["boot"]))
        h = o.get("http") or [None] * 5
        check(h[0] == 200 and h[1] == 10500.0 and h[2] == 401 and h[3] in (401, 403) and h[4] in (401, 403),
              "٩ عبر الخادم: الملخّصُ برمز الويدجت وحده بلا جلسة (‏200)، والرمزُ في الرابط مرفوض، وإنشاءُ الرمز وحالُه بلا جلسةٍ مرفوضان", str(h))
        # قبل الإصلاح: ‏[1, 2, …] — سهمٌ بعد سهم
        check(o.get("conc") == [2, 2, [["1120", 61.0], ["2222", 28.5]]],
              "١٠ تحديثُ الأسعار يطلبها معاً لا سهماً بعد سهم (المتزامنُ 2 من 2)، وكلُّ سعرٍ يقع على سهمه", str(o.get("conc")))
    subprocess.run(["psql", "-h", host, "-p", port, "-U", "sp", "-d", "postgres", "-qc", f"DROP DATABASE IF EXISTS {db}"],
                   capture_output=True)
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
