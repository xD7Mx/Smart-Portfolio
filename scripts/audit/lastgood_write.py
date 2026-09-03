#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D168 — الحفظةُ لا تُسلسل المخزنَ كلَّه، ولا تحجب حلقةَ الأحداث.
#
# كانت كلُّ حفظةٍ تكتب الملفَّ بأكمله. وبلغ على الخادم ‎7.8 ميجابايت
# و‎1077 مفتاحاً، فقِيست الحفظةُ الواحدة **1.277 ثانية**، ومسحُ السوق
# يحفظ نحو أربعِ مئةِ مرّة. وهي تُنادى من شيفرةٍ لا متزامنة، فثانيةٌ
# وربعٌ من دخلٍ/خرجٍ حاجب تُجمّد كلَّ طلبٍ معها — وذلك بطءُ الصفحات
# مقيساً.
#
# فحصٌ بالزمن لا بقراءة الرمز: يُبنى مخزنٌ ضخمٌ حقيقيّ في مجلّدٍ مؤقّت،
# ثمّ تُقاس مئةُ حفظة. لو بقيت كلُّ حفظةٍ تكتب الملفَّ لظهر الزمنُ خطّياً
# في عدد الحفظات. ويُتحقَّق أن البياناتِ تبلغ القرصَ فعلاً بعد الإفراغ —
# فالسرعةُ التي تفقد البياناتِ ليست إصلاحاً.
# ─────────────────────────────────────────────────────────────────────────
import json
import os
import pathlib
import sys
import tempfile
import time

TMP = tempfile.mkdtemp(prefix="lastgood-probe-")
os.environ["LASTGOOD_PATH"] = os.path.join(TMP, "lastgood.json")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "backend"))

from app.services import lastgood  # noqa: E402

fail = 0


def say(ok, label, detail=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}{(' — ' + detail) if detail else ''}")


# مخزنٌ ضخمٌ يشبه الخادم: ألفُ مفتاحٍ بحمولةٍ معتبرة.
payload = {"periods": [{"year": 2000 + i, "revenue": 1234567.89, "note": "ح" * 200}
                       for i in range(12)]}
for i in range(1000):
    lastgood.save(f"seed:{i}", payload)
lastgood.flush()
size_mb = os.path.getsize(os.environ["LASTGOOD_PATH"]) / 1048576
say(size_mb > 2, "١ بُني مخزنٌ ضخمٌ يشبه الخادم", f"{size_mb:.1f} MB")

N = 100
a = time.perf_counter()
for i in range(N):
    lastgood.save(f"probe:{i}", payload)
elapsed = time.perf_counter() - a
per = elapsed / N
say(per < 0.02, f"٢ الحفظةُ الواحدة لا تُسلسل المخزنَ كلَّه",
    f"{per * 1000:.2f} ms للحفظة · {elapsed:.2f} s لمئة")

# والبياناتُ تبلغ القرصَ — سرعةٌ تفقد البياناتِ ليست إصلاحاً.
lastgood.flush()
with open(os.environ["LASTGOOD_PATH"], encoding="utf-8") as f:
    on_disk = json.load(f)
say(all(f"probe:{i}" in on_disk for i in range(N)),
    "٣ كلُّ ما حُفظ بلغ القرصَ بعد الإفراغ", f"{len(on_disk)} مفتاحاً")

# والقراءةُ لا تنتظر القرصَ أصلاً — تخدمها الذاكرة فوراً.
lastgood.save("fresh", {"x": 1})
say((lastgood.load("fresh") or {}).get("x") == 1,
    "٤ القراءةُ ترى الحفظةَ فوراً بلا انتظارِ كتابة")

for f_ in pathlib.Path(TMP).glob("*"):
    f_.unlink()
os.rmdir(TMP)

print()
print("النتيجة:", "نظيف ✔" if not fail else "فيه ملاحظات ✘")
sys.exit(fail)
