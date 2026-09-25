#!/usr/bin/env python3
"""حارسُ D482: بوّابةُ الثوابت المحاسبية — تُفحص العمليةُ قبل حفظها لا بعده.

    python3 scripts/audit/tx_invariants_d482.py
    SP_PG_PORT=55432 SP_PG_HOST=/var/tmp/sppg python3 scripts/audit/tx_invariants_d482.py  # + سيناريو حيّ
"""
import os, re, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T = open(os.path.join(ROOT, "backend/app/api/v1/endpoints/transactions.py"), encoding="utf-8").read()
fail = 0
def check(ok, label):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}")

g = T[T.find("async def _ledger_gate"):T.find("async def _get_cash")]
check("before[\"cash_ok\"] and not after[\"cash_ok\"]" in g and "clipped" in g
      and 'after["qty"] < -TOL' in g and "available_cash" in g,
      "١ البوّابة تفحص مطابقةَ النقد والبيعَ فوق المملوك زمنياً والكميةَ والسيولةَ السالبتين")
for name in ("add_transaction", "patch_transaction", "delete_transaction"):
    body = T[T.find(f"async def {name}"):]
    body = body[:body.find("\n@router.", 10)]
    check("_before = await _ledger_state(" in body
          and re.search(r"await _ledger_gate\([^)]*\)\n\s*await db\.commit\(\)", body) is not None,
          f"٢ {name}: الحالةُ تُلتقط قبل التغيير والبوّابةُ قبل الحفظ مباشرةً")

# ٤ سياسةُ التكلفة الثابتة: المتوسط المرجّح في إعادة التشغيل وفي التطبيق الأمامي،
#   ومعلنةٌ في الميثاق (IFRS 9 · IAS 8)
rp = T[T.find("async def _replay"):T.find("async def _apply")]
G = open(os.path.join(ROOT, "docs/GOVERNANCE.md"), encoding="utf-8").read()
check("avg = (invested / qty) if qty else 0" in rp and "invested = max(0, invested - sell_qty * avg)" in rp
      and "بالمتوسط المرجّح" in G and "IAS 8" in G,
      "٤ التكلفةُ بالمتوسط المرجّح في إعادة التشغيل، والسياسةُ معلنةٌ ثابتةً في الميثاق")
port, host = os.environ.get("SP_PG_PORT"), os.environ.get("SP_PG_HOST")
if not port:
    print("SKIP ٣ السيناريو الحيّ على Postgres (عيّن SP_PG_PORT و SP_PG_HOST)")
else:
    db = "sp_d482"
    for q in (f"DROP DATABASE IF EXISTS {db}", f"CREATE DATABASE {db}"):
        subprocess.run(["psql", "-h", host, "-p", port, "-U", "sp", "-d", "postgres", "-qc", q], capture_output=True)
    tmp = tempfile.mkdtemp()
    script = r'''
import asyncio, sys
from fastapi import HTTPException
async def main():
    from app.core.database import init_db, AsyncSessionLocal
    from sqlalchemy import text
    await init_db()
    from app.api.v1.endpoints import transactions as T, cash as C, companies as K
    async def S(fn, *a, **k):
        async with AsyncSessionLocal() as db:
            try: await fn(*a, db=db, **k); return "OK"
            except HTTPException: await db.rollback(); return "REJ"
    await S(C.deposit_cash, C.CashDeposit(amount=10000))
    await S(K.add_company, K.CompanyCreate(symbol="2222", name_ar="x"))
    mk = lambda t,q,p,d: T.TransactionCreate(company_id=1, transaction_type=t, shares=q, price_per_share=p, transaction_date=d)
    r = [await S(T.add_transaction, mk("BUY",100,20,"2026-01-10")),
         await S(T.add_transaction, mk("SELL",100,25,"2026-02-10")),
         await S(T.add_transaction, mk("BUY",10,30,"2026-03-01")),
         await S(T.add_transaction, mk("SELL",5,22,"2026-01-05"))]
    async with AsyncSessionLocal() as db:
        avg = float((await db.execute(text("select average_cost from holdings"))).scalar())
        n = (await db.execute(text("select count(*) from transactions"))).scalar()
    print("RESULT", ",".join(r), round(avg, 6), n)
asyncio.run(main())
'''
    env = dict(os.environ, DATABASE_URL=f"postgresql://sp@/{db}?host={host}&port={port}",
               LASTGOOD_PATH=f"{tmp}/lg.json", SP_STATE_DIR=tmp, SP_STATUS_LOG=f"{tmp}/s.log")
    out = subprocess.run([sys.executable, "-c", script], cwd=os.path.join(ROOT, "backend"),
                         env=env, capture_output=True, text=True, timeout=180).stdout
    res = next((l for l in out.splitlines() if l.startswith("RESULT")), "RESULT ?")
    check(res == "RESULT OK,OK,OK,REJ 30.0 3",
          f"٣ بيعٌ مؤرَّخٌ قبل امتلاك أي سهم يُرفض ولا يُحفظ، والشراءُ بعد الإغلاق بمتوسطه (30) — {res}")
    subprocess.run(["psql", "-h", host, "-p", port, "-U", "sp", "-d", "postgres", "-qc",
                    f"DROP DATABASE IF EXISTS {db}"], capture_output=True)
print(f"{'FAIL' if fail else 'PASS'} D482 — بوّابةُ الثوابت المحاسبية")
sys.exit(fail)
