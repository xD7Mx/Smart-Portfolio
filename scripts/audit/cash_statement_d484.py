#!/usr/bin/env python3
"""حارسُ D484: كشفُ حساب النقد بصيغة البنك — يُطابَق بكشف الوسيط للفترة نفسها.

    python3 scripts/audit/cash_statement_d484.py
    SP_PG_PORT=55432 SP_PG_HOST=/var/tmp/sppg python3 scripts/audit/cash_statement_d484.py  # + سيناريو حيّ
"""
import os, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
rd = lambda p: open(os.path.join(ROOT, p), encoding="utf-8").read()
C = rd("backend/app/api/v1/endpoints/cash.py")
P = rd("frontend/src/pages/PortfolioPage.tsx")
fail = 0
def check(ok, label):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}")

i = C.find('@router.get("/statement")')
blk = C[i:] if i >= 0 else ""
check(all(k in blk for k in ('"opening"', '"closing"', '"debit"', '"credit"', '"balance"', '"reconciled"'))
      and "db.commit" not in blk,
      "١ الكشفُ: رصيدٌ افتتاحيّ ومدينٌ ودائنٌ ورصيدٌ جارٍ وختاميّ، ومطابقةٌ بالسيولة المخزَّنة — قراءةٌ محضة")
check("date: str | None = None" in C and C.count("data.value_date()") == 2,
      "٢ الإيداعُ والسحبُ يقبلان تاريخَهما الفعليّ لا لحظةَ الإدخال وحدها")
check("<StatementModal onClose=" in P and "exportCsv" in P and "cashApi.statement(" in P
      and "date: valueDate" in P,
      "٣ الواجهةُ: كشفُ الحساب بفترةٍ وتصديرُ CSV وطباعة، وحقلُ تاريخٍ للإيداع والسحب")

port, host = os.environ.get("SP_PG_PORT"), os.environ.get("SP_PG_HOST")
if not port:
    print("SKIP ٤ السيناريو الحيّ على Postgres (عيّن SP_PG_PORT و SP_PG_HOST)")
else:
    db = "sp_d484"
    for q in (f"DROP DATABASE IF EXISTS {db}", f"CREATE DATABASE {db}"):
        subprocess.run(["psql", "-h", host, "-p", port, "-U", "sp", "-d", "postgres", "-qc", q], capture_output=True)
    tmp = tempfile.mkdtemp()
    script = r'''
import asyncio
async def main():
    from app.core.database import init_db, AsyncSessionLocal
    await init_db()
    from app.api.v1.endpoints import transactions as T, cash as C, companies as K
    async def run(fn, *a):
        async with AsyncSessionLocal() as db: return await fn(*a, db=db)
    await run(C.deposit_cash, C.CashDeposit(amount=10000, date="2026-01-02"))
    await run(K.add_company, K.CompanyCreate(symbol="2222", name_ar="x"))
    mk = lambda t,q,p,d: T.TransactionCreate(company_id=1, transaction_type=t, shares=q, price_per_share=p, transaction_date=d)
    await run(T.add_transaction, mk("BUY", 100, 20, "2026-01-10"))
    await run(T.add_transaction, mk("SELL", 40, 25, "2026-02-10"))
    await run(C.withdraw_cash, C.CashDeposit(amount=500, date="2026-03-05"))
    async with AsyncSessionLocal() as db:
        a = (await C.cash_statement(date_from="2026-02-01", date_to="2026-02-28", db=db))["data"]
        b = (await C.cash_statement(db=db))["data"]
    print("RESULT", a["opening"], len(a["rows"]), a["rows"][0]["credit"], a["closing"],
          [r["balance"] for r in b["rows"]], b["reconciled"])
asyncio.run(main())
'''
    env = dict(os.environ, DATABASE_URL=f"postgresql://sp@/{db}?host={host}&port={port}",
               LASTGOOD_PATH=f"{tmp}/lg.json", SP_STATE_DIR=tmp, SP_STATUS_LOG=f"{tmp}/s.log")
    out = subprocess.run([sys.executable, "-c", script], cwd=os.path.join(ROOT, "backend"),
                         env=env, capture_output=True, text=True, timeout=180)
    res = next((l for l in out.stdout.splitlines() if l.startswith("RESULT")), "RESULT ? " + out.stderr[-300:])
    check(res == "RESULT 8000.0 1 1000.0 9000.0 [10000.0, 8000.0, 9000.0, 8500.0] True",
          f"٤ إيداعٌ مؤرَّخٌ يسبق الشراء، ورصيدٌ افتتاحيّ لفبراير 8000 وختاميّ 9000، والكشفُ كلّه ينتهي عند السيولة المخزَّنة — {res}")
    subprocess.run(["psql", "-h", host, "-p", port, "-U", "sp", "-d", "postgres", "-qc",
                    f"DROP DATABASE IF EXISTS {db}"], capture_output=True)
print(f"{'FAIL' if fail else 'PASS'} D484 — كشفُ حساب النقد")
sys.exit(fail)
