#!/usr/bin/env python3
"""حارسُ D481: سجلُّ تدقيق العمليات — إلحاقيٌّ لا يُمحى، من قاعدة البيانات نفسها.

    python3 scripts/audit/tx_audit_d481.py
    SP_PG_PORT=55432 SP_PG_HOST=/var/tmp/sppg python3 scripts/audit/tx_audit_d481.py   # + اختبارٌ حيّ على Postgres
"""
import os, re, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
rd = lambda p: open(os.path.join(ROOT, p), encoding="utf-8").read()
D = rd("backend/app/core/database.py")
T = rd("backend/app/api/v1/endpoints/transactions.py")
B = rd("backend/app/services/backup_service.py")
fail = 0
def check(ok, label):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}")

i = D.find("سجلّ تدقيق العمليات (D481")
end = D.find("FOR EACH STATEMENT EXECUTE FUNCTION sp_tx_audit_lock()", i)
blk = D[i:end + 80] if 0 <= i < end else ""
stmts = [a or b for a, b in re.findall(r'await _safe\("""(.*?)"""\)|await _safe\("([^"]*)"\)', blk, re.S)]
check(any("CREATE TABLE IF NOT EXISTS transaction_audit" in s for s in stmts),
      "١ جدولُ تدقيق العمليات يُنشأ عند الإقلاع")
check(any("AFTER INSERT OR UPDATE OR DELETE ON transactions" in s for s in stmts)
      and any("AFTER TRUNCATE ON transactions" in s for s in stmts),
      "٢ كلُّ إضافةٍ وتعديلٍ وحذفٍ وتفريغٍ للعمليات يُقيَّد من قاعدة البيانات لا من الكود")
check(any("BEFORE UPDATE OR DELETE ON transaction_audit" in s for s in stmts)
      and any("BEFORE TRUNCATE ON transaction_audit" in s for s in stmts),
      "٣ السجلُّ إلحاقيٌّ: تعديلُه وحذفُه وتفريغُه مرفوض")
check("await _audit_reason(db, reason)" in T and "await _audit_reason(db, data.reason)" in T
      and '@router.get("/audit")' in T and T.find('@router.get("/audit")') < T.find('@router.get("/{tx_id}")'),
      "٤ الحذفُ والتعديلُ يحملان سببَهما، ومسارُ /audit يُقرأ قبل /{tx_id}")
C = rd("frontend/src/pages/CompanyPage.tsx"); P = rd("frontend/src/pages/PortfolioPage.tsx")
check("<TxAuditLog companyId=" in C and "transactionsApi.remove(t.id, reason)" in C
      and "transactionsApi.remove(id, reason)" in P,
      "٥أ الواجهةُ تسأل عن سبب الحذف وتعرض سجلّ التغييرات في صفحة الشركة")
check(B.count("sp.audit_reason") >= 2, "٥ الاستعادةُ والفورماتُ يُقيَّدان بسببهما")

port, host = os.environ.get("SP_PG_PORT"), os.environ.get("SP_PG_HOST")
if not port:
    print("SKIP ٦ الاختبارُ الحيّ على Postgres (عيّن SP_PG_PORT و SP_PG_HOST)")
else:
    def psql(sql, db="sp_d481"):
        r = subprocess.run(["psql", "-h", host, "-p", port, "-U", "sp", "-d", db, "-v", "ON_ERROR_STOP=1",
                            "-qAt", "-c", sql], capture_output=True, text=True)
        return r.returncode, (r.stdout + r.stderr).strip()
    psql("DROP DATABASE IF EXISTS sp_d481", "postgres"); psql("CREATE DATABASE sp_d481", "postgres")
    psql("CREATE TABLE transactions (id SERIAL PRIMARY KEY, company_id INT, transaction_type TEXT, "
         "quantity NUMERIC, price NUMERIC, realized_gain NUMERIC)")
    errs = [o for s in stmts for c, o in [psql(s)] if c]
    for _ in range(2):  # الإقلاعُ يتكرّر: كل جملةٍ يجب أن تكون متكرّرةً بأمان
        errs += [o for s in stmts for c, o in [psql(s)] if c]
    check(not errs, "٦ جملُ الترحيل تنفَّذ على Postgres حقيقيّ وتتكرّر بأمان" + (f" — {errs[:1]}" if errs else ""))
    psql("INSERT INTO transactions (company_id, transaction_type, quantity, price) VALUES (7,'BUY',10,20)")
    psql("UPDATE transactions SET realized_gain = 5")  # حقلٌ مشتقّ — لا يُقيَّد
    psql("BEGIN; SELECT set_config('sp.audit_reason','تصحيح السعر',true); UPDATE transactions SET price=21; COMMIT;")
    psql("DELETE FROM transactions")
    _, log = psql("SELECT op||'|'||coalesce(company_id::text,'')||'|'||coalesce(reason,'')||'|'||"
                  "coalesce(old_row->>'price','')||'>'||coalesce(new_row->>'price','') FROM transaction_audit ORDER BY id")
    check(log.splitlines() == ["INSERT|7||>20", "UPDATE|7|تصحيح السعر|20>21", "DELETE|7||21>"],
          "٧ الإضافةُ والتعديلُ (بسببه وبصورتيه) والحذفُ مقيَّدة، وتغيّرُ الربح المشتقّ وحده لا يُقيَّد — " + log.replace("\n", " · "))
    c1, _ = psql("DELETE FROM transaction_audit")
    c2, _ = psql("UPDATE transaction_audit SET reason='x'")
    c3, _ = psql("TRUNCATE transaction_audit")
    _, n = psql("SELECT count(*) FROM transaction_audit")
    check(c1 and c2 and c3 and n == "3", "٨ محاولةُ حذف السجلّ أو تعديله أو تفريغه تُرفض ويبقى كاملاً")
    psql("TRUNCATE transactions")
    _, last = psql("SELECT op FROM transaction_audit ORDER BY id DESC LIMIT 1")
    check(last == "TRUNCATE", "٩ تفريغُ جدول العمليات نفسه يُقيَّد")
    psql("DROP DATABASE IF EXISTS sp_d481", "postgres")
print(f"{'FAIL' if fail else 'PASS'} D481 — سجلُّ تدقيق العمليات")
sys.exit(fail)
