#!/usr/bin/env python3
"""حارسُ D789 — السهمُ الأمريكيّ في المحفظة نفسِها: السعرُ بالدولار، والمالُ كلُّه بالريال (بأمر المالك 2026-11-23).

قال المالك: «هل المحفظةُ تدعم شركاتٍ أمريكية؟ هل المعاملاتُ ستكون صحيحة؟ هل ستدعمها الرسوم؟ أبغاها تدعم السوقين كاملَين —
البحثَ والمحفظةَ نفسَها». والسببُ الجذريّ: لا تحويلَ للعملة في أيّ موضع — سهمٌ أمريكيٌّ يُضاف يُجمع دولارُه مع الريال كأنهما
عملةٌ واحدة: شراءُ 10 أسهمٍ بـ190 دولاراً يُنقص النقدَ 1,900 «ريال» لا 7,125، وقيمتُه السوقيةُ ربعُ حقيقتها، ونصيبُه من التوازن
أسهمٌ بثلاثة أضعاف ونصف ما يُشترى فعلاً.

والقاعدة: كلُّ مالٍ يُخزَّن بالريال (التكلفةُ والنقدُ والقيمةُ والتوزيعات) فتبقى مواضعُ الجمع والقيدُ المزدوج كما هي، والدولارُ
في السعر وحده؛ والعمليةُ تحمل سعرَ صرف يومها، والقيمةُ بصرف اليوم. والسعوديُّ سعرُ صرفه واحدٌ تماماً فلا يتغيّر رقمٌ بتّاً بتّاً.

    python3 scripts/audit/us_stocks_d789.py
    SP_PG_PORT=55432 SP_PG_HOST=/var/tmp/sppg python3 scripts/audit/us_stocks_d789.py
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


rd = lambda p: (ROOT / p).read_text(encoding="utf-8")   # noqa: E731
FXS, T, H = rd("backend/app/services/fx.py"), rd("backend/app/api/v1/endpoints/transactions.py"), rd("backend/app/api/v1/endpoints/holdings.py")
DB, K = rd("backend/app/core/database.py"), rd("backend/app/api/v1/endpoints/companies.py")
rp = T[T.index("async def _replay"):T.index("async def _apply")]
ap = T[T.index("async def _apply"):T.index('@router.get("")')]

# ١ المصدرُ مسمّى ومحروسٌ بنطاق الربط، والأعمدةُ تُضاف فارغة
check('"SAR=X"' in FXS and "PEG = 3.75" in FXS and "BAND = (3.70, 3.80)" in FXS and '"peg": "السعرُ الرسميّ المثبَّت"' in FXS
      and all(f"ADD COLUMN IF NOT EXISTS {c}" in DB for c in ("fx_rate NUMERIC(18,8)", "invested_native", "reconciled_invested_native")),
      "١ سعرُ الصرف من ياهو SAR=X في نطاق ربط الريال وحده، وتعذّرُه آخرُ سعرٍ مقروءٍ ثمّ السعرُ الرسميّ 3.75 مسمّىً — والأعمدةُ تُضاف فارغة")
# ٢ إعادةُ التشغيل والتطبيقُ الأماميّ بسعر صرف العملية
check("invested += (qf * price + fees) * fx" in rp and "t.realized_gain = sell_qty * (price * fx - avg) - fees * fx" in rp
      and "total = (tx.quantity * tx.price + tx.fees) * fx" in ap and "proceeds = (tx.quantity * tx.price - tx.fees) * fx" in ap
      and "amount = amount_n * fx" in ap and "h.market_value = qty * lp * fx if lp else inv" in T,
      "٢ التكلفةُ والنقدُ والربحُ المحقّقُ والتوزيعُ بالريال بسعر صرف العملية (إعادةُ التشغيل والتطبيقُ الأماميّ معاً)، والقيمةُ بصرف اليوم")
# ٣ العملةُ من السوق، والقيمةُ في تحديث الأسعار بصرف اليوم
check('return "USD" if FX.is_us_symbol(self.symbol) else "SAR"' in K and "currency=data.resolved_currency()" in K
      and 'h.market_value = qty * float(p["price"]) * fxs.get(h.company_id, ("SAR", 1.0, False))[1]' in H,
      "٣ عملةُ الشركة من سوقها (الرمزُ الأمريكيّ بالدولار وسهمُ «تداول» بالريال)، وتحديثُ الأسعار يضع القيمةَ بالريال")

port, host = os.environ.get("SP_PG_PORT"), os.environ.get("SP_PG_HOST")
if not port:
    print("SKIP ٤–١٢ السيناريو الحيّ على Postgres (عيّن SP_PG_PORT و SP_PG_HOST)")
else:
    db = "sp_d789"
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
    import app.services.fx as FX
    from app.services.market_data import market_service, PriceData
    async def fake_fx():
        return {"rate": 3.75, "source": "live", "at": "fixed"}
    FX.usd_sar = fake_fx                                   # سعرُ صرفٍ ثابتٌ للقياس — بلا شبكة
    PX = {"AAPL": 200.0, "MSFT": 400.0, "2222.SR": 27.5}
    async def fake_price(sym):                             # كما يعيدها ‏MarketDataService: قاموسٌ لا كائن
        return PriceData(sym, PX[sym], 0.0, 0.0).to_dict() if sym in PX else None
    market_service.get_price = fake_price
    from app.api.v1.endpoints import transactions as T, cash as C, companies as K, holdings as HD, dividends as DV
    from app.api.v1.endpoints import liquidity as LQ
    from app.services.integrity import run_integrity_check
    out = {}
    async def S(fn, *a, **k):
        async with AsyncSessionLocal() as d:
            try:
                r = await fn(*a, db=d, **k)
                if hasattr(r, "body"):
                    return json.loads(r.body).get("data") or "OK"
                return (r.get("data") if isinstance(r, dict) else None) or "OK"
            except HTTPException as e:
                await d.rollback(); return "REJ:" + str(e.detail)[:60]
    async def Q(sql):
        async with AsyncSessionLocal() as d:
            return (await d.execute(text(sql))).first()
    async def bad():
        async with AsyncSessionLocal() as d:
            r = await run_integrity_check(d)
        return [c["name"] for c in r["checks"] if not c.get("ok")]
    await S(C.deposit_cash, C.CashDeposit(amount=100000))
    sa = await S(K.add_company, K.CompanyCreate(symbol="2222", name_ar="أرامكو"))
    us = await S(K.add_company, K.CompanyCreate(symbol="aapl", name="Apple", currency="SAR", exchange="NASDAQ"))
    out["cur"] = [sa["currency"], us["symbol"], us["currency"]]
    sid, uid = sa["id"], us["id"]
    mk = lambda cid, t, q, p, d, **k: T.TransactionCreate(company_id=cid, transaction_type=t, shares=q, price_per_share=p, transaction_date=d, **k)
    # ── السعوديّ: الأرقامُ نفسُها بالصيغة القديمة حرفاً ──
    await S(T.add_transaction, mk(sid, "BUY", 100, 27.35, "2026-07-01", fees=5.47))
    await S(T.add_transaction, mk(sid, "SELL", 30, 28.1, "2026-07-02", fees=1.69))
    await S(T.add_transaction, T.TransactionCreate(company_id=sid, transaction_type="DIVIDEND", amount=35.0, transaction_date="2026-07-03"))
    inv = 100 * 27.35 + 5.47; avg = inv / 100
    exp_gain = 30 * (28.1 - avg) - 1.69; exp_inv = max(0, inv - 30 * avg)
    r = await Q(f"select invested_amount, quantity, invested_native from holdings where company_id={sid}")
    g = await Q(f"select realized_gain, fx_rate from transactions where company_id={sid} and transaction_type='SELL'")
    out["sa"] = [round(float(r[0]), 6) == round(exp_inv, 6), float(r[1]), r[2], round(float(g[0]), 6) == round(exp_gain, 6), g[1]]
    # ── الأمريكيّ: شراءٌ وبيعٌ بصرف يومهما، وتوزيعٌ بصرف اليوم ──
    out["buy"] = await S(T.add_transaction, mk(uid, "BUY", 10, 190.0, "2026-07-01", fees=1.0, fx_rate=3.752))
    out["sell"] = await S(T.add_transaction, mk(uid, "SELL", 4, 200.0, "2026-07-02", fees=1.0, fx_rate=3.751))
    out["div"] = await S(T.add_transaction, T.TransactionCreate(company_id=uid, transaction_type="DIVIDEND", price=0.25, transaction_date="2026-07-03"))
    tx = (await Q(f"select string_agg(transaction_type||':'||round(total_amount::numeric,4)||':'||coalesce(fx_rate::text,'-'), ' ' order by id) from transactions where company_id={uid}"))[0]
    out["tx"] = tx
    hh = await Q(f"select quantity, invested_amount, invested_native from holdings where company_id={uid}")
    out["h"] = [float(hh[0]), round(float(hh[1]), 4), round(float(hh[2]), 4)]
    dv = await Q(f"select dividend_per_share, received_amount from dividends where company_id={uid}")
    out["dv"] = [float(dv[0]), round(float(dv[1]), 4)]
    cash = await Q("select available_cash from cash limit 1")
    out["cash"] = round(float(cash[0]), 4)
    lst = await S(HD.get_holdings)
    a = next(x for x in lst if x["company_id"] == uid)
    out["list"] = [a["currency"], a["fx_rate"], round(a["market_value"], 4), round(a["average_cost_native"], 4), a["last_price"], a["fx_legacy"]]
    out["bad1"] = await bad()
    # ── سعرُ صرفٍ غيرُ معقول يُرفض، والمعاينةُ بالريال ──
    out["sane"] = await S(T.add_transaction, mk(uid, "BUY", 1, 190.0, "2026-07-04", fx_rate=37.5))
    pv = await S(T.funding_preview, company_id=uid, quantity=2, price=190.0, fees=2.0, fx_rate=3.75)
    out["pv"] = pv["unit_cost"] if isinstance(pv, dict) else pv
    # ── القديمُ بلا سعر صرف: لا يُضرب في سعر اليوم بلا طلب، ولا يُخلط بجديد، ويُكمَل بالتحرير ──
    ms = await S(K.add_company, K.CompanyCreate(symbol="MSFT", name="Microsoft"))
    mid = ms["id"]
    async with AsyncSessionLocal() as d:
        await d.execute(text(f"insert into transactions (company_id, portfolio_id, transaction_type, quantity, price, fees, total_amount, executed_at) values ({mid}, (select portfolio_id from holdings where company_id={mid}), 'BUY', 5, 380, 0, 1900, '2026-06-01')"))
        await d.execute(text("update cash set available_cash = available_cash - 1900, total_cash = total_cash - 1900"))
        await d.commit()
    async with AsyncSessionLocal() as d:
        await T.recompute_holding(d, mid); await d.commit()
    lst = await S(HD.get_holdings)
    m = next(x for x in lst if x["company_id"] == mid)
    out["legacy"] = [m["fx_legacy"], m["fx_rate"], round(m["market_value"], 2), round(m["invested_amount"], 2)]
    out["mix"] = (await S(T.add_transaction, mk(mid, "BUY", 1, 400.0, "2026-07-05")))[:4]
    lid = (await Q(f"select id from transactions where company_id={mid}"))[0]
    out["fix"] = await S(T.patch_transaction, lid, T.TransactionPatch(fx_rate=3.75, reason="سعرُ صرف كشف الوسيط"))
    out["fixed"] = [round(float(x), 2) for x in await Q(f"select total_amount, (select invested_amount from holdings where company_id={mid}) from transactions where id={lid}")]
    out["mix2"] = await S(T.add_transaction, mk(mid, "BUY", 1, 400.0, "2026-07-05"))
    out["bad2"] = await bad()
    # ── خطّةُ السيولة: الأسهمُ بسعرها بالريال ──
    class P: share_pct = 100.0; t1 = True; t2 = t3 = t4 = t5 = False; price_override = None; exec_tranches = 0
    class Hh: last_price = 200.0; market_value = 0
    class Cc: id = uid; symbol = "AAPL"; company_name = "Apple"; currency = "USD"
    row = LQ._row(P(), Hh(), Cc(), 7500.0, 100.0, 3.75)
    out["lq"] = [row["shares"], row["spent"], row["currency"]]
    async with AsyncSessionLocal() as d:
        rates = await FX.rates_for(d, [sid, uid])
    out["rates"] = [rates[sid], rates[uid]]
    print("RESULT " + json.dumps(out, ensure_ascii=False))
asyncio.run(main())
'''
    env = dict(os.environ, DATABASE_URL=f"postgresql://sp@/{db}?host={host}&port={port}",
               LASTGOOD_PATH=f"{tmp}/lg.json", SP_STATE_DIR=tmp, SP_STATUS_LOG=f"{tmp}/s.log")
    pr = subprocess.run([sys.executable, "-c", script], cwd=str(ROOT / "backend"), env=env, capture_output=True, text=True, timeout=300)
    line = next((ln for ln in pr.stdout.splitlines() if ln.startswith("RESULT ")), None)
    if not line:
        check(False, "٤ السيناريو الحيّ لم يكتمل", (pr.stderr.strip().splitlines() or ["?"])[-1][:300])
    else:
        import json
        o = json.loads(line[7:])
        print("  ", o)
        check(o["cur"] == ["SAR", "AAPL", "USD"],
              "٤ «aapl» يُحفظ AAPL بالدولار ولو أُرسل بالريال (عملتُه من سوقه)، وأرامكو بالريال", str(o["cur"]))
        check(o["sa"] == [True, 70.0, None, True, None],
              "٥ السعوديُّ بالصيغة القديمة حرفاً — التكلفةُ والربحُ المحقّقُ يطابقان الحسابَ القديم، وبلا سعر صرفٍ ولا تكلفةٍ بعملة", str(o["sa"]))
        # شراء: (10×190+1)×3.752 = 7,132.552 · بيع: (4×200−1)×3.751 = 2,997.049 · توزيع: 0.25×6×3.75 = 5.625
        check(o["tx"] == "BUY:7132.5520:3.75200000 SELL:2997.0490:3.75100000 DIVIDEND:5.6250:3.75000000",
              "٦ الشراءُ والبيعُ بصرف يومهما والتوزيعُ بصرف اليوم — الإجماليُّ بالريال وسعرُ الصرف محفوظٌ مع العملية", o["tx"])
        # الباقي: 6 أسهم · بالريال 7,132.552 × 6/10 = 4,279.5312 · بالدولار 1,901 × 6/10 = 1,140.6
        check(o["h"] == [6.0, 4279.5312, 1140.6] and o["dv"] == [0.25, 5.625],
              "٧ المركزُ بالريال (4,279.53) وبالدولار (1,140.60 ⇐ متوسّطٌ 190.10)، ونصيبُ السهم من التوزيع بالدولار ومبلغُه بالريال", str(o["h"] + o["dv"]))
        # النقد: 100,000 − 2,740.47 + 841.3 (بيع أرامكو) + 35 − 7,132.552 + 2,997.049 + 5.625
        exp_cash = round(100000 - (100 * 27.35 + 5.47) + (30 * 28.1 - 1.69) + 35 - 7132.552 + 2997.049 + 5.625, 4)
        check(abs(o["cash"] - exp_cash) < 1e-6 and o["bad1"] == [],
              "٨ النقدُ بالريال يطابق مجموعَ حركاته، وفحصُ السلامة كلُّه نظيف (مطابقةُ النقد وإعادةُ تشغيل الحيازات)", f"{o['cash']} · {exp_cash} · {o['bad1']}")
        # القيمة: 6 × 200 × 3.75 = 4,500
        check(o["list"] == ["USD", 3.75, 4500.0, 190.1, 200.0, False],
              "٩ قائمةُ الحيازات: السعرُ بالدولار (200) والقيمةُ بالريال بصرف اليوم (4,500)، ومتوسّطُ التكلفة بالدولار (190.10)", str(o["list"]))
        check(str(o["sane"]).startswith("REJ:سعرُ الصرف 37.5") and abs(o["pv"] - (190 * 3.75 + 2 * 3.75 / 2)) < 1e-6,
              "١٠ سعرُ صرفٍ غيرُ معقول (37.5) يُرفض، ومعاينةُ التمويل تحسب سعرَ السهم بالريال", f"{o['sane']} · {o['pv']}")
        check(o["legacy"] == [True, 1.0, 2000.0, 1900.0] and o["mix"] == "REJ:" and isinstance(o["fix"], dict)
              and o["fixed"] == [7125.0, 7125.0] and isinstance(o["mix2"], dict) and o["bad2"] == [],
              "١١ القديمُ بلا سعر صرف يبقى كما سُجّل (لا يُضرب في سعر اليوم بلا طلب)، والجديدُ لا يُخلط به، وإكمالُ سعر صرفه بالتحرير يحوّله ثمّ يُقبل الجديد",
              f"{o['legacy']} · {o['mix']} · {o['fixed']} · {o['bad2']}")
        # 7,500 ريال ÷ (200 × 3.75 = 750) = 10 أسهم
        check(o["lq"] == [10, 7500.0, "USD"] and o["rates"] == [1.0, 3.75],
              "١٢ خطّةُ السيولة تحسب الأسهمَ بسعرها بالريال (7,500 ÷ 750 = 10 لا 37)، وسعرُ الصرف لكلّ شركةٍ واحدٌ للسعوديّ", str(o["lq"] + o["rates"]))
    subprocess.run(["psql", "-h", host, "-p", port, "-U", "sp", "-d", "postgres", "-qc", f"DROP DATABASE IF EXISTS {db}"],
                   capture_output=True)
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
