#!/usr/bin/env python3
"""حارسُ D614: التجزئةُ المعلنة تُكشف وتُقترح بزرّ — لا خسارةَ وهمية، ولا تعديلَ بلا إذن.

    python3 scripts/audit/split_watch_d614.py
"""
import os, pathlib, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
os.environ["LASTGOOD_PATH"] = str(pathlib.Path(tempfile.mkdtemp()) / "lg.json")
fail = 0
def check(ok, label, det=""):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

from app.services.split_watch import factor_from_text, factor_from_prices, remember_closes, CLOSES
check(factor_from_prices(130.0, 65.2) == 2, "١ سلوشنز: من 130 إلى 65 = تجزئة 2:1", str(factor_from_prices(130.0, 65.2)))
check(factor_from_prices(90, 30.4) == 3, "٢ والثلثُ تجزئة 3:1")
check(factor_from_prices(100, 92) is None, "٣ وهبوطُ سوقٍ عاديّ ليس تجزئة")
check(factor_from_prices(100, 62) is None, "٤ ولا هبوطٌ حادٌّ لا يطابق نسبةً صحيحة (لا تخمين)")
check(factor_from_prices(None, 50) is None and factor_from_prices(100, 0) is None, "٥ وبلا سعرين لا حكم")
check(factor_from_text("تجزئة القيمة الاسمية للسهم من 10 ريالات إلى 5 ريالات") == 2, "٦ النسبةُ من القيمة الاسمية في الإعلان")
check(factor_from_text("تجزئة الأسهم بنسبة 2:1") == 2, "٧ ومن «2:1»")
check(factor_from_text("منح سهمين مقابل كل سهم") == 2, "٨ ومن «سهمين مقابل»")
check(factor_from_text("إعلان عن تجزئة") is None, "٩ وبلا نسبةٍ في النصّ لا نسبة")
from app.services import lastgood
remember_closes({"7202": 130.0}, today="2026-10-06")
remember_closes({"7202": 65.0}, today="2026-10-07")
c = (lastgood.load(CLOSES) or {}).get("7202") or {}
check(c.get("p") == 65.0 and c.get("pp") == 130.0 and c.get("pd") == "2026-10-06",
      "١٠ حفظُ اليوم يُبقي الأمسَ بجانبه — فالكشفُ بعد الإغلاق لا يضيع", str(c))
sw = (ROOT / "backend/app/services/split_watch.py").read_text()
check("Holding.quantity =" not in sw and ".quantity *=" not in sw and "db.add(" not in sw and "commit(" not in sw,
      "١١ الكاشفُ لا يكتب في حيازة المالك — يقترح ولا يعدّل")
tx = (ROOT / "backend/app/api/v1/endpoints/transactions.py").read_text()
check(0 <= tx.find('"/pending-splits"') < tx.find('"/{tx_id}"'), "١٢ مسارُ التجزئات قبل «/{tx_id}» فلا يُبتلع")
pp = (ROOT / "frontend/src/pages/PortfolioPage.tsx").read_text()
sb = (ROOT / "frontend/src/components/portfolio/SplitBanner.tsx").read_text()
check("<SplitBanner />" in pp and 'transaction_type: "SPLIT"' in sb and "confirm_prior_pre_split: true" in sb,
      "١٣ بطاقةُ المحفظة تعرض التجزئة وتطبّقها بزرّ")
import re as _re
check(not _re.search(r"#[0-9a-fA-F]{3,6}\b|rgba?\(", sb) and "var(--warn-ink)" in sb, "١٤ الألوانُ من الرموز لا قيمٌ ثابتة")
sch = (ROOT / "backend/app/scheduler/scheduler.py").read_text()
check('job_split_watch, CronTrigger(day_of_week="sun,mon,tue,wed,thu", hour=10' in sch and "hour=15, minute=40" in sch,
      "١٥ يُفحص بعد الافتتاح وبعد الإغلاق، أيامَ التداول")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
