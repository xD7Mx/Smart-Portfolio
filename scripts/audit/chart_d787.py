#!/usr/bin/env python3
"""حارسُ D787 (الخادم) — دليلُ «تداول» الحيّ للبحث، وشعارُ السعوديّ المنقول بين السوقين (بأمر المالك 2026-11-23).

قال المالك: «في السوق السعودي وطني للحديد والصلب ما وجدتُ لها رمزاً — لدينا وصولٌ إلى تداول، شوف رمزه موجودٌ في تداول وجيبه. وصورةُ الشركة
ما هي موجودة، ونفسُ الكلام في الفرص». والسببُ الجذريّ: قائمةُ البحث في الواجهة ثابتةٌ تُبنى مع التطبيق، وفيها «حديد وطني» برمزها القديم 9513
في «نمو»، وقد نُقلت إلى الرئيسية برمز 1325 (قيس على الخادم: نتيجةُ «أرقام» لـ1325 باسم «حديد وطني») — فلا يجدها البحث، ولا شعارَ لرمزها
الجديد في الخريطة. والخادمُ يحفظ دليلَ «تداول» كما نشرته (‏tadawul_sync.directory)، فيُرسَل للبحث، والشعارُ يُطلب من خادمنا.

    python3 scripts/audit/chart_d787.py
"""
import asyncio
import os
import pathlib
import sys
import tempfile

_SB = tempfile.mkdtemp()
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
fail = 0


def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))


# ١ نقطةُ الدليل: ما نشرته «تداول» اليوم (الرئيسيةُ و«نمو») بأسمائه — والجديدُ والمنقولُ فيه
import app.services.tadawul_sync as TS   # noqa: E402
FAKE = {"at": "2026-11-23T06:00:00+00:00", "main": {f"{1000 + i}": {"name": f"شركة {i}", "sector": "المواد الأساسية"} for i in range(240)},
        "nomu": {"9510": {"name": "نمو ما", "sector": "السلع الرأسمالية"}}, "gone": {}}
FAKE["main"]["1325"] = {"name": "وطني للحديد والصلب", "name_en": "Watani Iron Steel Co.", "sector": "المواد الأساسية"}   # كما في دليل «تداول» (قِيس)
o_dir = TS.directory
TS.directory = lambda: FAKE
from app.api.v1.endpoints import market as EP   # noqa: E402
import json   # noqa: E402


def data_of(res):
    return json.loads(res.body)["data"] if hasattr(res, "body") else (res or {}).get("data")


d = data_of(asyncio.run(EP.saudi_directory_live()))
row = next((r for r in (d or {}).get("rows") or [] if r["symbol"] == "1325"), None)
check(d and d["complete"] and row and row["name_ar"] == "وطني للحديد والصلب" and row["market"] == "main" and any(r["market"] == "nomu" for r in d["rows"]),
      "١ «تداول» تنشر «حديد وطني» برمز 1325 في الرئيسية — والخادمُ يرسل دليلَها الحيَّ للبحث (الرئيسيةُ و«نمو» بأسمائهما) فيجدها المالكُ برمزها الجديد",
      json.dumps(row, ensure_ascii=False))
TS.directory = lambda: {}
d0 = data_of(asyncio.run(EP.saudi_directory_live()))
check(d0["rows"] == [] and not d0["complete"], "١ب ودليلٌ لم يُقرأ بعدُ لا يُخفي شيئاً من القائمة الثابتة (غيرُ كامل) — لا يُخمَّن")
TS.directory = o_dir

# ٢ الشعار: المنقولُ بين السوقين يأخذ شعارَ اسمه في الدليل (‏9513 ⇐ 1325)، والسعوديُّ يُبحث في «تداول» برمزه
from app.data import saudi_directory as SD   # noqa: E402
from app.services import symbol_logo as SL   # noqa: E402
had = dict(SD.SAUDI_DIRECTORY.get("1325") or {})
SD.SAUDI_DIRECTORY["1325"] = {"name": "حديد وطني", "sector": "المواد الأساسية"}
lg = SL._sa_logo_by_name("1325")
old = (SD.SAUDI_DIRECTORY.get("9513") or {}).get("logo")
SD.SAUDI_DIRECTORY["1325"] = had or SD.SAUDI_DIRECTORY.pop("1325")
src = (ROOT / "backend/app/services/symbol_logo.py").read_text(encoding="utf-8")
check(old and lg == old and "watani" in lg and '"TADAWUL" if sa else ""' in src and SL._sa_logo_by_name("0000") is None and 'ck = f"SA2_' in src,
      "٢ شعارُ 1325 من الدليل باسمها («حديد وطني» شعارُها على رمزها القديم 9513)، وغيرُ المعروف يُبحث في «تداول» بتريدنق فيو برمزه — لا يُخترع", lg or "None")

# ٣ الواجهة: الشعارُ السعوديُّ يُطلب من خادمنا قبل parqet، والبحثُ يدمج الدليلَ الحيّ ويُخفي ما غاب عن الصفحتين
logo = (ROOT / "frontend/src/components/common/CompanyLogo.tsx").read_text(encoding="utf-8")
sc = (ROOT / "frontend/src/data/saudiCompanies.ts").read_text(encoding="utf-8")
iss = (ROOT / "frontend/src/components/market/InlineStockSearch.tsx").read_text(encoding="utf-8")
check("TV_LOGOS[base] ? null : `${API_BASE}/market/logo/${base}.SR`" in logo and "export function mergeDirectory" in sc and "!HIDDEN.has(c.symbol)" in sc
      and "marketApi.saudiDirectory()" in iss and "mergeDirectory(d.rows, !!d.complete)" in iss,
      "٣ الواجهةُ تطلب شعارَ السعوديّ غيرِ المعروف من خادمنا، وبحثُها يدمج دليلَ «تداول» الحيّ ويُخفي الرمزَ القديم الذي غاب عن الصفحتين")

# ٤ الفرص بلا مرشّح المدّة (المالك: «ما لها داعي»)، وحولَ صقر لا شرحَ لأنظمته
opps = (ROOT / "frontend/src/components/saqr/SaqrOpps.tsx").read_text(encoding="utf-8")
desk = (ROOT / "frontend/src/components/saqr/SaqrDesk.tsx").read_text(encoding="utf-8")
hub = desk[desk.index("function Hub("):desk.index("function Stat(")]
check('data-role="so-h"' not in opps and "H_OPTS" not in opps and 'data-role="so-code"' in opps and "guide={guideOf(chainFor)}" in opps
      and "sq-nt" not in hub and "sq-nd" not in hub and "title=" not in hub and "n.t" not in hub and "n.d" not in hub and '"sq-tick"' in hub and 'data-role="sq-node"' in hub,
      "٤ «الفرص» بلا مرشّح المدّة وبرمزٍ يُنسخ وسلسلةٍ بدليل الفرصة؛ وحولَ صقر قرصُ أداةٍ بأنوارٍ بلا أسماءٍ ولا تلميحات — لا يُفضح ما يفعل")
print("\nالنتيجة:", "نظيف ✔" if not fail else "فشل ✘")
sys.exit(fail)
