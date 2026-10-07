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
# D619: التجزئةُ تُبطل التقييماتِ المحفوظة (قِيس: سلوشنز 307 على 103.6 = قيمةُ ما قبل التجزئة)
os.environ["SP_STATE_DIR"] = tempfile.mkdtemp()
from app.services import cache
cache.set("analysis:7202.SR:r:v", {"fair_value": 307}, 7 * 24 * 3600)
cache.set("analysis:72020.SR:r:v", {"fair_value": 9}, 7 * 24 * 3600)
n = cache.expire_prefix("analysis:7202.SR:")
check(n == 1 and cache.get("analysis:7202.SR:r:v") is None and cache.get("analysis:72020.SR:r:v") == {"fair_value": 9},
      "١٦ إبطالُ تحليل الشركة بشاهد قبرٍ لا يمسّ غيرَها", str(n))
sw2 = (ROOT / "backend/app/services/split_watch.py").read_text()
check("def invalidate_valuations" in sw2 and "invalidate_valuations(s)" in sw2 and "sweep([s])" in sw2,
      "١٧ الكاشفُ يُبطل التقييمَ عند كشف التجزئة ويُعيد حسابه")
check("invalidate_valuations(_sym)" in tx, "١٨ وتسجيلُ المالك للتجزئة يُبطله كذلك")
# D621: سجلُّ أحداث رأس المال يقرؤه المحرّك — إعادةُ الحساب وحدها أعطت 307 كما كانت
from app.services.split_watch import record_split, factor_after
record_split("7202.SR", "2026-10-07", 2)
check(factor_after("7202", "2026-06-30") == 2 and factor_after("7202", "2026-10-08") == 1 and factor_after("2222", "2026-06-30") == 1,
      "١٩ التجزئةُ بعد آخر قوائم تُضاعف عددَ الأسهم، وما بعدها أو لغيرها لا")
fvm = (ROOT / "backend/app/services/fair_value_models.py").read_text()
check("factor_after(sym, _last)" in fvm and "1 / 1.5 <= shares / _sh0 <= 1.5" in fvm and "_fa(sym, str(h.get(\"date\"))[:10])" in fvm,
      "٢٠ المحرّكُ يطبّقها على عدد الأسهم (ما لم يصحّحه حَكَمُ السوق) وعلى التوزيعات قبلها")
cache.set("fvm:v37:7202", {"value": 307}, 6 * 3600)
cache.set("fvm:v37:72020", {"value": 9}, 6 * 3600)
from app.services.split_watch import invalidate_valuations
invalidate_valuations("7202")
check(cache.get("fvm:v37:7202") is None and cache.get("fvm:v37:72020") == {"value": 9},
      "٢١ والتجزئةُ تُبطل كاشَ نماذج القيمة العادلة للشركة (كان يُعيد 307)")
# D622: «تداول» مصدرُ الحدث — الأسهمُ المصدرة ليلةً بليلة
from app.services.split_watch import ratio_of, issued_watch, ISSUED
import app.services.tadawul_financials as TF
check(ratio_of(120e6, 240e6) == 2 and ratio_of(100e6, 110e6) == 1.1 and ratio_of(100e6, 117e6) is None and ratio_of(100e6, 100e6) is None,
      "٢٢ نسبةُ تجزئةٍ أو منحةٍ معروفة من الأسهم المصدرة، ولا تخمين")
from app.services import lastgood as _lg
_lg.save(ISSUED, {"7202": {"n": 120e6, "d": "2026-10-06"}, "2222": {"n": 242e9, "d": "2026-10-06"}})
_orig = TF.issued_shares
TF.issued_shares = lambda s: {"7202": 240e6, "2222": 242e9}.get(s)
try:
    ev = issued_watch(today="2026-10-07")
finally:
    TF.issued_shares = _orig
check([(e["symbol"], e["factor"]) for e in ev] == [("7202", 2.0)] and factor_after("7202", "2026-06-30") >= 2,
      "٢٣ تضاعفُ أسهم «سلوشنز» في «تداول» يُسجّل تجزئتها تلقائياً، وما لم يتغيّر لا", str(ev))
sch2 = (ROOT / "backend/app/scheduler/scheduler.py").read_text()
check("issued_watch()" in sch2, "٢٤ ويُفحص كلَّ ليلةٍ بعد قراءة صفحات «تداول»")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
