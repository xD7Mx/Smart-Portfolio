#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# البند ٣١ — فحصٌ لا يعمل أسوأُ من غيابه.
#
# كُتبت ثمانيةُ فحوصٍ لعطب جدول التوزيع فلم تُشغَّل: استبدالٌ نصّيٌّ فشل بلا
# تحقّق، فبقي الملفُّ كما كان وطبعت اللجنةُ «نظيف ✔» عن لا شيء. والغائبُ
# يُعرف غيابُه، والصامتُ يُطمئن كاذباً — وهو أخطر.
#
# فتُحصى الفحوصُ المنفَّذة في كلّ تشغيلة وتُقارَن بالمُسجَّل في
# `census.json`. ونقصانُ العدد **عطبٌ في اللجنة** يُوقف التسليم: إمّا حُذف
# فحصٌ بلا قرار، وإمّا سكت وهو يظنّ نفسه يعمل.
#
# والزيادةُ مقبولةٌ وتُحدَّث بـ`--bless` بعد النظر: العددُ يرتفع مع كلّ عطبٍ
# يُولَد له حارس، ولا ينزل إلا بقرار.
#
#   python3 scripts/audit/check_census.py <ملفّ مخرَج اللجنة>
#   python3 scripts/audit/check_census.py <ملفّ> --bless     # يُسجّل العدد
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
CENSUS = ROOT / "scripts" / "audit" / "census.json"
LINE = re.compile(r"^(PASS|FAIL)\b", re.M)


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    bless = "--bless" in sys.argv
    if not args:
        print("… لا ملفَّ مخرَج — لا إحصاء.")
        return 0
    log = pathlib.Path(args[0])
    if not log.exists():
        print(f"… تعذّر: {log} غير موجود.")
        return 0
    text = log.read_text(encoding="utf-8", errors="replace")
    count = len(LINE.findall(text))

    prev = {}
    if CENSUS.exists():
        try:
            prev = json.loads(CENSUS.read_text(encoding="utf-8"))
        except Exception:                                         # noqa: BLE001
            prev = {}
    floor = int(prev.get("min_checks") or 0)

    # ══ البركةُ تُؤخذ من العدّ نفسِه لا من ملفٍّ خارجيّ ══
    # سُجّل الحدُّ أوّلَ مرّةٍ من مخرَجٍ يحوي سطرَ الإحصاء نفسَه، فصار أعلى
    # بواحدٍ من أيّ تشغيلةٍ ممكنة فسقطت اللجنةُ أبداً. والعدّادُ يقرأ الملفَّ
    # قبل أن يكتب سطرَه، فالعددُ هنا هو الصحيح دائماً.
    if bless:
        CENSUS.write_text(json.dumps(
            {"min_checks": count,
             "_": "أدنى عددِ فحوصٍ تُنفّذها اللجنة. ينزل بقرارٍ لا بصمت (البند ٣١)."},
            ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"سُجِّل: {count} فحصاً هو الحدُّ الأدنى.")
        return 0

    ok = count >= floor
    print(f"{'PASS' if ok else 'FAIL'} اللجنةُ نفّذت {count} فحصاً"
          f" (الحدّ المسجَّل {floor})")
    if not ok:
        print("     نقصانُ العدد يعني فحصاً حُذف أو سكت وهو يظنّ نفسه يعمل.")
        print("     إن كان الحذفُ مقصوداً فسجّله: --bless")
    print()
    print("النتيجة:", "نظيف ✔" if ok else "فيه ملاحظات ✘")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
