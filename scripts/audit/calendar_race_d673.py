#!/usr/bin/env python3
"""حارسُ D673: بنّاءُ المفكرة الذي ينتظر الشبكةَ بين قراءة المخزن وحفظه لا يمحو ما كتبه غيرُه في أثناء انتظاره.

الحالُ قبل الإصلاح: بنّاءا التوزيعات والنتائج يقرآن المخزنَ ثمّ يمرّان على عشرات الشركات من المزوّد (دقائق) ثمّ يحفظان
نسختَهما — فكلُّ ما حفظه بنّاءٌ آخر في تلك الدقائق (إفصاحاتُ «تداول» كلَّ نصف ساعة، و«أرقام» كلَّ ربع ساعة) يُمحى بصمت.
وكُشف حين لم تثبت إفصاحاتُ «تداول» في المخزن بعد نشر D670.

    python3 scripts/audit/calendar_race_d673.py
"""
import asyncio, os, pathlib, re, sys, tempfile
_SB = tempfile.mkdtemp(prefix="sp-audit-")
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


src = (ROOT / "backend/app/services/content_engine.py").read_text(encoding="utf-8")
bad = []
for m in re.finditer(r"\nasync def (build_market_calendar_\w+)\(", src):
    j = src.find("\nasync def ", m.end())
    body = src[m.end():j if j > 0 else len(src)]
    li, si = body.find("_cal_load_store()"), body.find("_cal_prune_and_save(store)")
    if li < 0:
        continue
    waits = li >= 0 and si > li and re.search(r"\bawait\b", body[li:si])
    if waits:
        bad.append(m.group(1))
check(not bad, "١ لا بنّاءَ ينتظر الشبكةَ بين قراءة المخزن وحفظه ثمّ يحفظ نسختَه القديمة", str(bad))

from app.services import content_engine as C   # noqa: E402
from app.services import lastgood   # noqa: E402
ev = lambda k, src_: {"id": k, "type": "OTHER", "title": f"عنوان {k}", "symbol": "1010", "date": "2099-01-01",   # noqa: E731
                      "date_kind": "event", "source": src_}
import datetime as dt   # noqa: E402
d = (dt.date.today() + dt.timedelta(days=5)).isoformat()
lastgood.save(C._CAL_STORE_KEY, {"k1": {**ev("k1", "أرقام"), "date": d}})
store = C._cal_load_store()
base = dict(store)
# في أثناء الانتظار: بنّاءٌ آخر يحفظ حدثاً جديداً
mid = C._cal_load_store()
mid["k2"] = {**ev("k2", "تداول"), "title": "حدثٌ كتبه غيري", "date": d}
C._cal_prune_and_save(mid)
# ثمّ يحفظ صاحبُ الانتظار ما أضافه هو
store["k3"] = {**ev("k3", "بيانات السوق"), "title": "حدثٌ أضفتُه", "date": d}
C._cal_save_merged(store, base)
after = {e.get("title") for e in C._cal_load_store().values()}
check({"حدثٌ كتبه غيري", "حدثٌ أضفتُه"} <= after, "٢ والحفظُ يدمج: ما كتبه غيرُه في أثناء الانتظار يبقى، وما أضافه هو يُضاف", str(sorted(after)))
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
