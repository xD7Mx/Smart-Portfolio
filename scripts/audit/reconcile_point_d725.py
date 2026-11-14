#!/usr/bin/env python3
"""حارسُ D725 — تصحيحُ المالك للمركز نقطةُ مطابقةٍ في السجل، لا رقمٌ يمحوه أوّلُ تعديل.

قِيس على خادم المالك (‏integrity_door): الألبان 45 سهماً مخزَّنةً والسجلُّ 22 (شراء 23 · بيع 1). كان «تعديلُ المركز» يكتب الكميةَ
رقماً نهائياً ويحفظ فارقَ التكلفة وحدَه، فـ: (١) فحصُ السلامة يعدّه خطأً (شريطٌ أحمر)، (٢) أوّلُ عمليةٍ لاحقةٍ تُعيد بناءَ الحيازة من
السجل فتمحو التصحيحَ إلى 22 بصمت، (٣) بوّابةُ الثوابت ترفض بيعَ أكثر من 22 «أسهماً غيرَ مملوكة». فالحارس:
  · سكونيّاً: إعادةُ التشغيل تطبّق النقطةَ في موضعها، والتصحيحُ يكتبها، والإقلاعُ يثبّت القديمَ مرّةً، والقاعدةُ تُرحَّل.
  · سلوكاً على Postgres حقيقيّ (‏SP_PG_PORT · SP_PG_HOST): حالُ الخادم تُعاد، ثمّ شراءٌ وبيعٌ فوق السجل وتجزئةٌ وتصحيحٌ جديد.

    python3 scripts/audit/reconcile_point_d725.py
    SP_PG_PORT=55432 SP_PG_HOST=/var/tmp/sppg python3 scripts/audit/reconcile_point_d725.py
"""
import os, pathlib, subprocess, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parents[2]
fail = 0


def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))


T = (ROOT / "backend/app/api/v1/endpoints/transactions.py").read_text(encoding="utf-8")
rp = T[T.index("async def _replay"):T.index("async def _apply")]
H = (ROOT / "backend/app/api/v1/endpoints/holdings.py").read_text(encoding="utf-8")
up = H[H.index("async def update_holding"):H.index("class ReconcileItem")]
check("cp_pending" in rp and "Holding.reconciled_at" in rp and "t.executed_at > cp_at" in rp,
      "١ إعادةُ التشغيل تطبّق نقطةَ المطابقة في موضعها الزمنيّ — قبل أوّل عمليةٍ بعدها")
check("h.reconciled_at =" in up and "h.reconciled_quantity = qty" in up and "h.cost_basis_adjustment = 0" in up,
      "٢ وتصحيحُ المركز يكتب نقطةً مؤرَّخة (الكمية والتكلفة) لا رقماً نهائياً")
db_src = (ROOT / "backend/app/core/database.py").read_text(encoding="utf-8")
mn = (ROOT / "backend/main.py").read_text(encoding="utf-8")
check(all(f"ADD COLUMN IF NOT EXISTS {c}" in db_src for c in ("reconciled_at", "reconciled_quantity", "reconciled_invested"))
      and "adopt_quantity_corrections" in mn,
      "٣ والقاعدةُ تُرحَّل، والإقلاعُ يثبّت التصحيحَ القديمَ مرّةً كما هو")

port, host = os.environ.get("SP_PG_PORT"), os.environ.get("SP_PG_HOST")
if not port:
    print("SKIP ٤ السيناريو الحيّ على Postgres (عيّن SP_PG_PORT و SP_PG_HOST)")
else:
    db = "sp_d725"
    for q in (f"DROP DATABASE IF EXISTS {db}", f"CREATE DATABASE {db}"):
        subprocess.run(["psql", "-h", host, "-p", port, "-U", "sp", "-d", "postgres", "-qc", q], capture_output=True)
    tmp = tempfile.mkdtemp()
    script = r'''
import asyncio
from fastapi import HTTPException
async def main():
    from app.core.database import init_db, AsyncSessionLocal
    from sqlalchemy import text
    await init_db()
    from app.api.v1.endpoints import transactions as T, cash as C, companies as K, holdings as HD
    from app.services.reconcile_adopt import adopt_quantity_corrections
    from app.services.integrity import run_integrity_check
    async def S(fn, *a, **k):
        async with AsyncSessionLocal() as d:
            try: await fn(*a, db=d, **k); return "OK"
            except HTTPException as e: await d.rollback(); return "REJ"
    async def Q(sql):
        async with AsyncSessionLocal() as d:
            return (await d.execute(text(sql))).first()
    async def bad():
        async with AsyncSessionLocal() as d:
            r = await run_integrity_check(d)
        return [c["name"] for c in r["checks"] if not c.get("ok")]
    await S(C.deposit_cash, C.CashDeposit(amount=50000))
    await S(K.add_company, K.CompanyCreate(symbol="2270", name_ar="الألبان"))
    import datetime as _dtm
    today = (_dtm.datetime.utcnow() + _dtm.timedelta(hours=3)).date().isoformat()
    mk = lambda t,q,p,d,**k: T.TransactionCreate(company_id=1, transaction_type=t, shares=q, price_per_share=p, transaction_date=d, **k)
    out = []
    out.append(await S(T.add_transaction, mk("BUY", 23, 261.05, "2026-07-05")))
    out.append(await S(T.add_transaction, mk("SELL", 1, 278.6, "2026-07-05")))
    # حالُ الخادم قبل الإصلاح: تصحيحٌ قديمٌ كتب الكميةَ رقماً نهائياً وفارقَ التكلفة وحدَه
    async with AsyncSessionLocal() as d:
        await d.execute(text("update holdings set quantity=45, invested_amount=9990, average_cost=222, cost_basis_adjustment=9990-(select 22*261.05+0)"))
        await d.commit()
    async with AsyncSessionLocal() as d:
        n = await adopt_quantity_corrections(d)
    r1 = await Q("select quantity, invested_amount from holdings")
    b1 = await bad()
    async with AsyncSessionLocal() as d:
        n2 = await adopt_quantity_corrections(d)          # مرّةً واحدة: لا يُعاد
    back = await S(T.add_transaction, mk("BUY", 3, 250, "2026-08-01"))   # قبل النقطة ⇒ يُرفض
    out.append(await S(T.add_transaction, mk("BUY", 5, 200, today)))
    r2 = await Q("select quantity, invested_amount from holdings")
    out.append(await S(T.add_transaction, mk("SELL", 30, 210, today)))   # فوق الـ22 في السجل
    r3 = await Q("select quantity from holdings")
    out.append(await S(T.add_transaction, mk("SPLIT", 2, 0, today, factor=2, confirm_prior_pre_split=True)))
    r4 = await Q("select quantity from holdings")
    async with AsyncSessionLocal() as d:
        await HD.update_holding(1, HD.HoldingUpdate(quantity=41, average_cost=100), db=d)
    out.append(await S(T.add_transaction, mk("BUY", 4, 50, today)))
    r5 = await Q("select quantity, invested_amount from holdings")
    b5 = await bad()
    print("RESULT", ",".join(out), back, n, n2, [float(x) for x in r1], b1, [float(x) for x in r2], float(r3[0]), float(r4[0]),
          [float(x) for x in r5], b5)
asyncio.run(main())
'''
    env = dict(os.environ, DATABASE_URL=f"postgresql://sp@/{db}?host={host}&port={port}",
               LASTGOOD_PATH=f"{tmp}/lg.json", SP_STATE_DIR=tmp, SP_STATUS_LOG=f"{tmp}/s.log")
    pr = subprocess.run([sys.executable, "-c", script], cwd=str(ROOT / "backend"), env=env, capture_output=True, text=True, timeout=240)
    res = next((l for l in pr.stdout.splitlines() if l.startswith("RESULT")), "RESULT ? " + pr.stderr.strip().splitlines()[-1][:200] if pr.stderr.strip() else "RESULT ?")
    print("  ", res)
    try:
        parts = eval("[" + res.split("RESULT ", 1)[1].replace(" [", ",[").replace("] ", "],").replace(" ", ",", 2) + "]") if False else None
    except Exception:
        parts = None
    check(res.startswith("RESULT OK,OK,OK,OK,OK,OK REJ 1 0 [45.0, 9990.0] []"),
          "٤ حالُ الخادم: التصحيحُ القديم (45 · 9,990) يُثبَّت نقطةً مرّةً واحدة كما هو، وفحصُ السلامة نظيف")
    check("[50.0, 10990.0]" in res, "٥ وشراءٌ لاحقٌ يُبنى على المصحَّح (45 + 5 = 50) — لا يُعاد إلى 22؛ وشراءٌ مؤرَّخٌ قبل النقطة يُرفض")
    check(" 20.0 40.0 " in res, "٦ وبيعُ 30 (فوق الـ22 في السجل) يُقبل فيبقى 20، والتجزئةُ تضاعفها 40")
    check("[45.0, 4300.0] []" in res, "٧ وتصحيحٌ جديد (41 بمتوسط 100) ثمّ شراء 4 بـ50 ← 45 بتكلفة 4,300، وفحصُ السلامة نظيف")
    subprocess.run(["psql", "-h", host, "-p", port, "-U", "sp", "-d", "postgres", "-qc", f"DROP DATABASE IF EXISTS {db}"],
                   capture_output=True)
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
