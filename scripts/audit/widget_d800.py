#!/usr/bin/env python3
"""حارسُ D800 — ويدجت قائمة المراقبة كويدجت تريدنق فيو (بأمر المالك 2026-11-24).

قال المالك: «أريد في الويدجت — بجانب المحفظة — الشركاتِ اللي حاطّها في القائمة… مثل ويدجت تريدنق فيو: عشرُ شركاتٍ أو أكثر تتوزّع يميناً ويساراً».
‏GET /widget/watchlist برمز الويدجت وحده:
  ١ بلا رمزٍ ‏401، وقائمةٌ لا وجودَ لها ‏404 برسالةٍ تدلّ على الصواب.
  ٢ «محفظتي» (‏list فارغٌ أو ‏mine): شركاتُ الحيازات القائمة وحدها (لا المصفّاة) بترتيبها.
  ٣ قائمةٌ باسمها أو برقمها: شركاتُها بترتيبها، بأسعارها من الباب الذي تقرأ منه غرفةُ التداول (‏get_prices)، وما لا سعرَ له ‏None لا صفر،
    وشعارُ كلٍّ من بابنا العامّ (‏/market/logo — والسعوديُّ بلاحقته).
  ٤ أسماءُ القوائم كلِّها معها (لتُكتب في خانة Parameter)، وعبر الخادم نفسِه بلا جلسة: ‏200.

    SP_PG_PORT=55432 SP_PG_HOST=/var/tmp/sppg python3 scripts/audit/widget_d800.py
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
check('@public_router.get("/watchlist")' in W and "await _check(db, x_widget_token)" in W.split('@public_router.get("/watchlist")')[1][:1600],
      "٠ نقطةُ القائمة عامّةٌ برمز الويدجت وحده — يُفحص قبل أيّ قراءة")

port, host = os.environ.get("SP_PG_PORT"), os.environ.get("SP_PG_HOST")
if not port:
    print("SKIP ١–٤ السيناريو الحيّ على Postgres (عيّن SP_PG_PORT و SP_PG_HOST)")
else:
    db = "sp_d800"
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
    from app.services.market_data import market_service
    PX = {"2222.SR": (26.28, 0.14, 0.54), "1120.SR": (60.95, -0.2, -0.33), "^TASI.SR": (9957.68, 20.42, 0.21)}
    seen = []
    async def fake_prices(syms):
        seen.append(list(syms))
        return {s: {"price": PX[s][0], "change": PX[s][1], "change_pct": PX[s][2]} for s in syms if s in PX}
    market_service.get_prices = fake_prices
    async def fake_price(sym):
        return {"price": PX[sym][0], "change": PX[sym][1], "change_pct": PX[sym][2]} if sym in PX else None
    market_service.get_price = fake_price
    from app.core.portfolio_scope import set_scope, reset_scope
    from app.api.v1.endpoints import transactions as T, cash as C, companies as K, market as M, widget as WG
    out = {}
    async def S(fn, *a, **k):
        async with AsyncSessionLocal() as d:
            try:
                r = await fn(*a, db=d, **k)
                return (r.get("data") if isinstance(r, dict) else None) or "OK"
            except HTTPException as e:
                await d.rollback(); return f"HTTP{e.status_code}:{e.detail}"
    async with AsyncSessionLocal() as d:
        pid1 = (await d.execute(text("select id from portfolio order by id limit 1"))).scalar()
    set_scope(pid1, False)
    await S(C.deposit_cash, C.CashDeposit(amount=10000))
    a = await S(K.add_company, K.CompanyCreate(symbol="2222", name_ar="أرامكو"))
    b = await S(K.add_company, K.CompanyCreate(symbol="1120", name_ar="الراجحي"))
    mk = lambda cid, q, p, t="BUY": T.TransactionCreate(company_id=cid, transaction_type=t, shares=q, price_per_share=p, transaction_date="2026-07-01")
    await S(T.add_transaction, mk(a["id"], 100, 25.0))
    await S(T.add_transaction, mk(b["id"], 10, 55.0))
    await S(T.add_transaction, mk(b["id"], 10, 58.0, "SELL"))       # مصفّاة ⇒ لا تظهر في «محفظتي»
    await S(M.create_watchlist_group, {"name": "السوق السعودي"})
    async with AsyncSessionLocal() as d:
        gid = (await d.execute(text("select id from watchlist_groups where name = 'السوق السعودي'"))).scalar()
    for sym in ("^TASI.SR", "1120", "4190"):
        await S(M.add_watchlist, {"symbol": sym, "group_id": gid})
    reset_scope()
    out["none"] = await S(WG.widget_watchlist, None, None)
    tok = await S(WG.token_create)
    t = tok["token"]
    mine = await S(WG.widget_watchlist, None, t)
    out["mine"] = {"list": mine.get("list"), "syms": [i["symbol"] for i in mine.get("items", [])], "logo": [i["logo"] for i in mine.get("items", [])],
                   "lists": [l["name"] for l in mine.get("lists", [])]}
    byname = await S(WG.widget_watchlist, "السوق السعودي", t)
    out["byname"] = {"list": byname.get("list"), "items": [[i["symbol"], i["price"], i["change"], i["logo"]] for i in byname.get("items", [])]}
    byid = await S(WG.widget_watchlist, str(gid), t)
    out["byid"] = [i["symbol"] for i in byid.get("items", [])]
    out["missing"] = await S(WG.widget_watchlist, "قائمةٌ لا وجودَ لها", t)
    import httpx
    from main import app
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t/api/v1", timeout=120) as c:
        r1 = await c.get("/widget/watchlist", params={"list": "السوق السعودي"}, headers={"X-Widget-Token": t})
    out["http"] = [r1.status_code, len((r1.json().get("data") or {}).get("items") or [])]
    print("RESULT " + json.dumps(out, ensure_ascii=False, default=str))
asyncio.run(main())
'''
    env = dict(os.environ, DATABASE_URL=f"postgresql://sp@/{db}?host={host}&port={port}",
               LASTGOOD_PATH=f"{tmp}/lg.json", SP_STATE_DIR=tmp, SP_STATUS_LOG=f"{tmp}/s.log")
    pr = subprocess.run([sys.executable, "-c", script], cwd=str(ROOT / "backend"), env=env, capture_output=True, text=True, timeout=300)
    line = next((ln for ln in pr.stdout.splitlines() if ln.startswith("RESULT ")), None)
    if not line:
        check(False, "١ السيناريو الحيّ لم يكتمل", (pr.stderr.strip().splitlines() or ["?"])[-1][:300])
    else:
        import json
        o = json.loads(line[7:])
        print("  ", o)
        check(str(o["none"]).startswith("HTTP401") and str(o["missing"]).startswith("HTTP404") and "list" in str(o["missing"]),
              "١ بلا رمزٍ ‏401، وقائمةٌ لا وجودَ لها ‏404 برسالةٍ تدلّ على الصواب", f"{o['none']} · {o['missing']}")
        check(o["mine"]["list"] == "محفظتي" and o["mine"]["syms"] == ["2222"] and o["mine"]["logo"] == ["/market/logo/2222.SR"],
              "٢ «محفظتي»: شركاتُ الحيازات القائمة وحدها (المصفّاةُ لا تظهر)، وشعارُها بلاحقة السوق", str(o["mine"]))
        it = o["byname"]["items"]
        check(o["byname"]["list"] == "السوق السعودي" and [x[0] for x in it] == ["^TASI.SR", "1120", "4190"] and it[1][1:3] == [60.95, -0.2]
              and it[2][1] is None and it[2][2] is None and it[0][3] == "/market/logo/^TASI.SR" and o["byid"] == ["^TASI.SR", "1120", "4190"],
              "٣ قائمةٌ باسمها أو برقمها بترتيبها وأسعارها من باب الغرفة، وما لا سعرَ له ‏None لا صفر، وشعارُ كلٍّ من بابنا", str(it))
        check(o["mine"]["lists"] == ["محفظتي", "السوق السعودي"] and o["http"] == [200, 3],
              "٤ أسماءُ القوائم معها لخانة Parameter، وعبر الخادم بلا جلسة ‏200", f"{o['mine']['lists']} · {o['http']}")
    subprocess.run(["psql", "-h", host, "-p", port, "-U", "sp", "-d", "postgres", "-qc", f"DROP DATABASE IF EXISTS {db}"], capture_output=True)
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
