#!/usr/bin/env python3
"""حارسُ D483: المطابقةُ مع كشف الوسيط — الخطأُ الذي لا يكشفه نظامٌ وحده.

    python3 scripts/audit/broker_reconcile_d483.py
    SP_PG_PORT=55432 SP_PG_HOST=/var/tmp/sppg python3 scripts/audit/broker_reconcile_d483.py  # + سيناريو حيّ
"""
import os, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
rd = lambda p: open(os.path.join(ROOT, p), encoding="utf-8").read()
H = rd("backend/app/api/v1/endpoints/holdings.py")
P = rd("frontend/src/pages/PortfolioPage.tsx")
fail = 0
def check(ok, label):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}")

i = H.find('@router.post("/reconcile")')
blk = H[i:H.find("@router.", i + 10)] if i >= 0 else ""
check(bool(blk) and "db.commit" not in blk and "db.add" not in blk and ".quantity =" not in blk,
      "١ المطابقةُ قراءةٌ محضة: لا تحفظ ولا تصحّح شيئاً تلقائياً")
check('"ledger"' in blk and '"cash"' in blk and '"diff"' in blk,
      "٢ تعرض الفرقَ لكل شركةٍ وللنقد، وكميةَ إعادة التشغيل بجانب المخزَّنة")
check("<ReconcileModal holdings={holdings}" in P and "holdingsApi.reconcile(" in P,
      "٣ شاشةُ المطابقة متاحةٌ من المحفظة")

port, host = os.environ.get("SP_PG_PORT"), os.environ.get("SP_PG_HOST")
if not port:
    print("SKIP ٤ السيناريو الحيّ على Postgres (عيّن SP_PG_PORT و SP_PG_HOST)")
else:
    db = "sp_d483"
    for q in (f"DROP DATABASE IF EXISTS {db}", f"CREATE DATABASE {db}"):
        subprocess.run(["psql", "-h", host, "-p", port, "-U", "sp", "-d", "postgres", "-qc", q], capture_output=True)
    tmp = tempfile.mkdtemp()
    script = r'''
import asyncio
async def main():
    from app.core.database import init_db, AsyncSessionLocal
    from sqlalchemy import text
    await init_db()
    from app.api.v1.endpoints import transactions as T, cash as C, companies as K, holdings as H
    async with AsyncSessionLocal() as db: await C.deposit_cash(C.CashDeposit(amount=10000), db=db)
    async with AsyncSessionLocal() as db: await K.add_company(K.CompanyCreate(symbol="2222", name_ar="x"), db=db)
    async with AsyncSessionLocal() as db:
        await T.add_transaction(T.TransactionCreate(company_id=1, transaction_type="BUY", shares=100,
                                price_per_share=20, transaction_date="2026-01-10"), db=db)
    async with AsyncSessionLocal() as db:
        before = (await db.execute(text("select count(*) from transaction_audit"))).scalar()
        a = (await H.reconcile(H.ReconcileRequest(items=[H.ReconcileItem(company_id=1, quantity=100)], cash=8000), db=db))["data"]
        b = (await H.reconcile(H.ReconcileRequest(items=[H.ReconcileItem(company_id=1, quantity=110)], cash=7990), db=db))["data"]
        await db.commit()
        after = (await db.execute(text("select count(*) from transaction_audit"))).scalar()
        q = float((await db.execute(text("select quantity from holdings"))).scalar())
    print("RESULT", a["ok"], b["ok"], b["items"][0]["diff"], b["cash"]["diff"], before == after, q)
asyncio.run(main())
'''
    env = dict(os.environ, DATABASE_URL=f"postgresql://sp@/{db}?host={host}&port={port}",
               LASTGOOD_PATH=f"{tmp}/lg.json", SP_STATE_DIR=tmp, SP_STATUS_LOG=f"{tmp}/s.log")
    out = subprocess.run([sys.executable, "-c", script], cwd=os.path.join(ROOT, "backend"),
                         env=env, capture_output=True, text=True, timeout=180)
    res = next((l for l in out.stdout.splitlines() if l.startswith("RESULT")), "RESULT ? " + out.stderr[-300:])
    check(res == "RESULT True False 10.0 -10.0 True 100.0",
          f"٤ كشفٌ مطابق ← مطابق؛ وكشفٌ بفرق 10 أسهم و−10 ريالات ← يُظهرهما ولا يغيّر شيئاً — {res}")
    subprocess.run(["psql", "-h", host, "-p", port, "-U", "sp", "-d", "postgres", "-qc",
                    f"DROP DATABASE IF EXISTS {db}"], capture_output=True)
print(f"{'FAIL' if fail else 'PASS'} D483 — المطابقةُ مع كشف الوسيط")
sys.exit(fail)
