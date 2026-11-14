#!/usr/bin/env python3
"""حارسُ D730 (المالك 2026-11-14): «أنا أضع عدد الأسهم… والتطبيق يحسب مباشرةً كم نصيبها من إعادة الاستثمار… بالسعر الذي
نفّذتُ به… بدون الحاجة لإدخال نوع التمويل… لازم نخرج بصفر أخطاء، المعاملةُ شيءٌ خطيرٌ وجوهريّ».

الحالُ قبله: المالكُ يختار «ضخ» أو «إعادة استثمار» للشراء كلّه — فإن اشترى 372 سهماً نصيبُ الحوض منها 7 وسمها كلَّها
فاستهلك من الحوض 372 سهماً، أو لم يسمها فبقي الحوضُ منتفخاً. والوسمُ للصفّ كلّه لا لشقٍّ منه.

الثغراتُ التي يسدّها الحلّ (ويقيسها هذا الحارس على Postgres حقيقيّ):
  · سعرُ التنفيذ غيرُ آخر إغلاق ← الأسهمُ من نصيب الريالات ÷ سعر التنفيذ.
  · المعاينةُ والحفظُ حسابان ← دالّةٌ واحدة، والعددُ المعروضُ يُرسَل فإن خالفه الحفظُ رُفض ولم يُحفظ شيء.
  · شراءٌ بتاريخٍ ماضٍ ← لا يأخذ من الحوض ما يُنقص تمويلَ شراءٍ موسومٍ بعده.
  · تعديلٌ لاحقٌ للسعر أو الكمية أو حفظُ الوسم كما هو ← الشقُّ أسهمٌ يتبعها المبلغ، ولا يتّسع بصمت.
  · الكشفُ والأهدافُ والحوضُ ورأسُ المال المدفوع ← مصدرٌ واحد (‏reinvested_amount) للشقّ الموسوم.

    python3 scripts/audit/auto_funding_d730.py
    SP_PG_PORT=55432 SP_PG_HOST=/var/tmp/sppg python3 scripts/audit/auto_funding_d730.py
"""
import json, os, pathlib, re, subprocess, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parents[2]
fail = 0


def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))


B = ROOT / "backend/app"
fn = B / "services/funding.py"
if not fn.exists():
    check(False, "١ دالّةُ التمويل المشتركة موجودة", "لا services/funding.py")
    print("\nالنتيجة: عطب ✖")
    sys.exit(1)
F = fn.read_text(encoding="utf-8")
T = (B / "api/v1/endpoints/transactions.py").read_text(encoding="utf-8")
PR = (B / "services/portfolio_return.py").read_text(encoding="utf-8")
G = (B / "api/v1/endpoints/goals.py").read_text(encoding="utf-8")
A = (B / "api/v1/endpoints/allocation.py").read_text(encoding="utf-8")
check("reinvest_qty = Column(Numeric(18, 6))" in (B / "models/transaction.py").read_text(encoding="utf-8")
      and "ADD COLUMN IF NOT EXISTS reinvest_qty" in (B / "core/database.py").read_text(encoding="utf-8"),
      "١ الشقُّ الممَوَّل من الحوض عمودٌ في العملية (أسهماً)، والقاعدةُ تُرحَّل بلا مساسٍ بصفٍّ قائم")
# كلُّ من يجمع المشتريات الموسومة يقرأ المصدرَ الواحد — لا جمعَ لإجماليّ الصفّ الموسوم في مكانٍ آخر
_raw = re.compile(r"total_amount[^\n]{0,160}\n?[^\n]{0,160}funding_source in \(", re.S)
offenders = [p.name for p in B.rglob("*.py") if p.name != "funding.py" and _raw.search(p.read_text(encoding="utf-8"))]
check(not offenders and "reinvested_amount(t)" in PR and "reinvested_amount(t) for t in txs" in G
      and "profit_reinvested += reinvested_amount(t)" in T,
      "٢ الحوضُ والأهدافُ وإعادةُ التشغيل يقرؤون الشقَّ الموسوم من مصدرٍ واحد — لا إجماليَّ الصفّ", str(offenders))
check("def split_need(" in A and "split_need(tw, investable, held(h), pool)" in A and "async def company_reinvest_share" in A,
      "٣ ونصيبُ الشركة بالريال من دالّة الجدول نفسِها — لا حسابٌ ثانٍ يخالف «التوزيع النسبي»")
UI = [(ROOT / "frontend/src/pages/PortfolioPage.tsx").read_text(encoding="utf-8"),
      (ROOT / "frontend/src/pages/CompanyPage.tsx").read_text(encoding="utf-8")]
def _fn(u, k):
    i = u.index(k)
    j = min([x for x in (u.find("\nfunction ", i + 10), u.find("\nexport function ", i + 10), u.find("\nexport default function ", i + 10)) if x > 0] or [len(u)])
    return u[i:j]
mods = [_fn(UI[0], "function TransactionModal"), _fn(UI[1], "function TxModal")]
hook = (ROOT / "frontend/src/components/portfolio/FundingSplit.tsx")
hook = hook.read_text(encoding="utf-8") if hook.exists() else ""
check(all('funding_source = "AUTO"' in m and "expect_reinvest_qty = fs.split?.reinvest_qty" in m and "useFundingSplit(" in m
          and "<FundingSplit" in m and "FUNDING_SOURCES.map" not in m and "setFundingSource" not in m
          and '(type !== "BUY" || !!fs.split)' in m for m in mods) and "transactionsApi.fundingPreview" in hook,
      "٤ نافذتا المعاملة: لا اختيارَ يدويَّ للتمويل — المعاينةُ من الخادم، والعددُ المعروض يُرسَل للحفظ")

port, host = os.environ.get("SP_PG_PORT"), os.environ.get("SP_PG_HOST")
if not port:
    print("SKIP ٥ السيناريو الحيّ على Postgres (عيّن SP_PG_PORT و SP_PG_HOST)")
else:
    db = "sp_d730"
    for q in (f"DROP DATABASE IF EXISTS {db}", f"CREATE DATABASE {db}"):
        subprocess.run(["psql", "-h", host, "-p", port, "-U", "sp", "-d", "postgres", "-qc", q], capture_output=True)
    tmp = tempfile.mkdtemp()
    script = r'''
import asyncio, json, datetime as _dtm
from fastapi import HTTPException
async def main():
    from app.core.database import init_db, AsyncSessionLocal
    from sqlalchemy import text
    await init_db()
    from app.api.v1.endpoints import transactions as T, cash as C, companies as K, allocation as AL
    from app.services.portfolio_return import compute_reinvestment_pool
    from app.services.integrity import run_integrity_check
    R = {}
    async def S(fn, *a, **k):
        async with AsyncSessionLocal() as d:
            try:
                r = await fn(*a, db=d, **k)
                return ("OK", json.loads(r.body) if hasattr(r, "body") else r)
            except HTTPException as e:
                await d.rollback(); return ("REJ%d" % e.status_code, str(e.detail))
    async def Q(sql):
        async with AsyncSessionLocal() as d:
            return [tuple(float(x) if isinstance(x, (int, float)) or hasattr(x, "as_tuple") else x for x in r)
                    for r in (await d.execute(text(sql))).all()]
    async def pool():
        async with AsyncSessionLocal() as d:
            return await compute_reinvestment_pool(d)
    today = (_dtm.datetime.utcnow() + _dtm.timedelta(hours=3)).date().isoformat()
    await S(C.deposit_cash, C.CashDeposit(amount=20000))
    await S(K.add_company, K.CompanyCreate(symbol="1120", name_ar="الراجحي"))
    await S(K.add_company, K.CompanyCreate(symbol="2222", name_ar="أرامكو"))
    mk = lambda c,t,q,p,d,**k: T.TransactionCreate(company_id=c, transaction_type=t, shares=q, price_per_share=p, transaction_date=d, **k)
    await S(T.add_transaction, mk(1, "BUY", 100, 50, "2026-09-01"))
    await S(T.add_transaction, mk(2, "BUY", 100, 50, "2026-09-01"))
    await S(T.add_transaction, mk(2, "SELL", 50, 60, "2026-10-01"))        # حصيلة 3,000 تدخل الحوض
    await S(AL.set_targets, AL.TargetsUpdate(items=[AL.TargetItem(company_id=1, target_weight=60), AL.TargetItem(company_id=2, target_weight=40)]))
    al = (await S(AL.get_allocation))[1]["data"]
    R["alloc_share"] = next(x for x in al["items"] if x["company_id"] == 1)["reinvest_share"]
    R["pool0"] = (await pool())["pool"]
    # المعاينةُ بسعر تنفيذٍ غيرِ آخر إغلاق (52.5)
    pv = (await S(T.funding_preview, company_id=1, quantity=40, price=52.5, transaction_date=today))[1]["data"]
    R["preview"] = pv
    cash0 = (await Q("select available_cash from cash"))[0][0]
    n0 = (await Q("select count(*) from transactions"))[0][0]
    # عددٌ قديمٌ في المعاينة ⇒ 409 ولا يُحفظ شيء
    R["stale"] = (await S(T.add_transaction, mk(1, "BUY", 40, 52.5, today, funding_source="AUTO", expect_reinvest_qty=pv["reinvest_qty"] + 1)))[0]
    R["stale_nothing"] = [(await Q("select count(*) from transactions"))[0][0] == n0, (await Q("select available_cash from cash"))[0][0] == cash0]
    ok = await S(T.add_transaction, mk(1, "BUY", 40, 52.5, today, funding_source="AUTO", expect_reinvest_qty=pv["reinvest_qty"]))
    R["saved"] = [ok[0], ok[1]["data"]["split"]["reinvest_qty"] if ok[0] == "OK" else None]
    tid = ok[1]["data"]["id"] if ok[0] == "OK" else None
    R["row"] = (await Q(f"select funding_source, reinvest_qty, quantity, total_amount from transactions where id={tid}"))[0]
    R["cash_after"] = cash0 - (await Q("select available_cash from cash"))[0][0]
    p1 = await pool()
    R["pool1"] = p1["pool"]; R["consumed1"] = p1["already_reinvested"]
    R["hold"] = (await Q("select quantity from holdings where company_id=1"))[0][0]
    # حفظُ الوسم كما هو (نافذةُ التحرير ترسله دائماً) مع تعديل السعر ⇒ الشقُّ أسهمُه نفسُها ومبلغُه بالسعر الجديد
    pa = await S(T.patch_transaction, tid, T.TransactionPatch(price=52.0, funding_source="REINVEST", set_funding_source=True))
    R["patch_price"] = [pa[0], (await Q(f"select reinvest_qty from transactions where id={tid}"))[0][0], (await pool())["already_reinvested"]]
    # كميةٌ دون الشقّ ⇒ يُقصّ إليها
    pb = await S(T.patch_transaction, tid, T.TransactionPatch(quantity=3))
    R["patch_qty"] = [pb[0], (await Q(f"select reinvest_qty from transactions where id={tid}"))[0][0]]
    pc = await S(T.patch_transaction, tid, T.TransactionPatch(quantity=40))
    # شراءٌ مؤرَّخٌ قبل دخول الحصيلة ⇒ الحوضُ يومَها صفر ⇒ كلُّه من السيولة
    pv_old = (await S(T.funding_preview, company_id=1, quantity=10, price=50, transaction_date="2026-09-15"))[1]["data"]
    old = await S(T.add_transaction, mk(1, "BUY", 10, 50, "2026-09-15", funding_source="AUTO", expect_reinvest_qty=pv_old["reinvest_qty"]))
    R["old"] = [pv_old["reinvest_qty"], pv_old["headroom"], old[0]]
    # شراءٌ مؤرَّخٌ بين الحصيلة والشراء الموسوم اليوم ⇒ لا يأخذ ما يُنقص تمويلَ ذلك الشراء
    pv_mid = (await S(T.funding_preview, company_id=2, quantity=100, price=50, transaction_date="2026-10-15"))[1]["data"]
    mid = await S(T.add_transaction, mk(2, "BUY", 100, 50, "2026-10-15", funding_source="AUTO", expect_reinvest_qty=pv_mid["reinvest_qty"]))
    p2 = await pool()
    R["mid"] = [mid[0], pv_mid["reinvest_qty"], pv_mid["headroom"], [d["excess"] for d in p2["tagged_detail"]]]
    st = (await S(C.cash_statement, date_from="2026-01-01", date_to=today))[1]["data"]
    R["label"] = [r["label"] for r in st["rows"] if r.get("ref") and "إعادة استثمار" in r["label"]]
    u = await S(T.untag_transactions, T.UntagRequest(ids=[tid]))
    R["untag"] = (await Q(f"select funding_source, reinvest_qty from transactions where id={tid}"))[0]
    async with AsyncSessionLocal() as d:
        r = await run_integrity_check(d)
    R["bad"] = [c["name"] for c in r["checks"] if not c.get("ok")]
    print("RESULT " + json.dumps(R, ensure_ascii=False, default=str))
asyncio.run(main())
'''
    env = dict(os.environ, DATABASE_URL=f"postgresql://sp@/{db}?host={host}&port={port}",
               LASTGOOD_PATH=f"{tmp}/lg.json", SP_STATE_DIR=tmp, SP_STATUS_LOG=f"{tmp}/s.log")
    pr = subprocess.run([sys.executable, "-c", script], cwd=str(ROOT / "backend"), env=env, capture_output=True, text=True, timeout=300)
    line = next((l for l in pr.stdout.splitlines() if l.startswith("RESULT ")), None)
    if not line:
        check(False, "٥ السيناريو الحيّ يعمل", (pr.stderr.strip().splitlines() or ["?"])[-1][:300])
    else:
        R = json.loads(line[7:])
        pv = R["preview"]
        print("  ", {k: R[k] for k in ("alloc_share", "pool0", "saved", "row", "pool1", "consumed1", "patch_price", "patch_qty", "old", "mid", "untag", "bad")})
        exp_rq = int(R["alloc_share"] // 52.5)
        check(pv["company_share"] == R["alloc_share"] and pv["reinvest_qty"] == min(40, exp_rq) and 0 < pv["reinvest_qty"] < 40,
              "٥ المعاينةُ: نصيبُ الشركة بالريال هو رقمُ «التوزيع النسبي» نفسُه، والأسهمُ ⌊نصيب ÷ سعر التنفيذ 52.5⌋",
              f"{pv['company_share']} ÷ 52.5 ⇒ {pv['reinvest_qty']} من 40")
        check(R["stale"] == "REJ409" and R["stale_nothing"] == [True, True],
              "٦ عددٌ في المعاينة يخالف حسابَ لحظة الحفظ ⇒ رفضٌ (409) ولا يُحفظ شيء — لا صفَّ ولا نقد")
        rq = pv["reinvest_qty"]
        check(R["saved"] == ["OK", rq] and R["row"][0] == "REINVEST" and R["row"][1] == rq and R["row"][2] == 40 and R["row"][3] == 2100
              and abs(R["cash_after"] - 2100) < 1e-6 and R["hold"] == 140,
              "٧ صفٌّ واحدٌ لتنفيذٍ واحد: 40 سهماً بـ2,100 من النقد، منها شقٌّ من الحوض بأسهمه — والحيازةُ 140", str(R["row"]))
        check(abs(R["consumed1"] - rq * 52.5) < 0.01 and abs(R["pool0"] - R["pool1"] - rq * 52.5) < 0.01,
              "٨ والحوضُ ينقص بشقّه وحده (أسهمُه × سعر التنفيذ) — لا بالشراء كلّه", f"{R['pool0']} ← {R['pool1']}")
        check(R["patch_price"][0] == "OK" and R["patch_price"][1] == rq and abs(R["patch_price"][2] - rq * 52.0) < 0.01,
              "٩ تعديلُ السعر مع حفظ الوسم كما هو: الشقُّ أسهمُه نفسُها ومبلغُه بالسعر الجديد — لا يتّسع للشراء كلّه بصمت")
        check(R["patch_qty"] == ["OK", 3.0] if rq > 3 else R["patch_qty"][0] == "OK",
              "١٠ وكميةٌ دون الشقّ تقصّه إليها — لا شقَّ أكبرُ من الشراء")
        check(R["old"] == [0, 0.0, "OK"], "١١ شراءٌ مؤرَّخٌ قبل دخول الحصيلة: الحوضُ يومَها صفر ⇒ كلُّه من السيولة", str(R["old"]))
        check(R["mid"][0] == "OK" and all(e <= 0.01 for e in R["mid"][3]),
              "١٢ شراءٌ مؤرَّخٌ قبل شراءٍ موسومٍ لاحق: يأخذ ما بقي بعده فقط — ولا يصير تمويلُ اللاحق «مستحيلاً»",
              f"سعة {R['mid'][2]} · فوائض {R['mid'][3]}")
        check(any("منها" in l and "سهم إعادة استثمار" in l for l in R["label"]),
              "١٣ وكشفُ الحساب يقول الشقَّ بأسهمه (‏«منها N سهم إعادة استثمار»)", str(R["label"][:2]))
        check(R["untag"] == [None, None], "١٤ وإزالةُ الوسم تزيل الشقَّ معه")
        check(R["bad"] == [], "١٥ وفحصُ السلامة نظيفٌ بعد ذلك كلّه — النقدُ والحيازاتُ والسجلّ متطابقة", str(R["bad"]))
    subprocess.run(["psql", "-h", host, "-p", port, "-U", "sp", "-d", "postgres", "-qc", f"DROP DATABASE IF EXISTS {db}"],
                   capture_output=True)
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
