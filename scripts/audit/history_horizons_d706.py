#!/usr/bin/env python3
"""حارسُ D706 — المحرّكُ يُحكم عليه بالتاريخ على آفاق 90 و180 و365 يوماً، ولا يُنتظر المستقبل (بأمر المالك 2026-10-14).

قال المالك: «لا يُفترض الانتظارُ تسعين يوماً قادمةً لانتهاء المحرّك وتجهيزه — يُفترض القياسُ على 90 و180 و365 سابقة؛ فبياناتُ
التاريخ جوهرُ توقّعات المستقبل». وكان الاختبارُ التاريخيّ على أفقَي ستّة أشهرٍ واثني عشر منذ 2023 وحدها. فالحارسُ يمنع العودة:
  · الآفاقُ الثلاثة في الاختبار، وتقريرٌ لكلّ أفق: العادلُ والمستهدف ونصفا التاريخ وكلُّ سنةٍ وإصابةُ «رخيص» و«غالٍ» وفارقُ الخُمسين.
  · وتاريخٌ أطول بمهمّةٍ مستقلّة (‏history_ab · منذ 2019) للأساس والمرشَّح على البيانات نفسِها — ومقاييسُ الحارس من 2023 كما هي.
  · وأفقُ التسعين محروسٌ في حارس التجميد.

    python3 scripts/audit/history_horizons_d706.py
"""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
fail = 0


def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))


bt = open(os.path.join(ROOT, "scripts/audit/fv_backtest_d699.py"), encoding="utf-8").read()
m = re.search(r"^H = \(([^)]*)\)", bt, re.M)
check(m and [int(x) for x in m.group(1).split(",") if x.strip()] == [3, 6, 12], "١ الاختبارُ التاريخيّ على 90 و180 و365 يوماً",
      m and m.group(0))
src = bt[bt.index("_FIRST_ENV ="):bt.index("STEP = 3")]
for env, want in (("2019-03", "2019-03"), ("", "2023-03"), ("1999-01; rm", "2023-03")):
    ns = {"os": type("O", (), {"environ": {"SP_BT_FIRST": env}})(), "re": re}
    exec(src, ns)
    if ns["FIRST"] != want:
        check(False, "٢ أوّلُ تاريخٍ يُمدّ بـ‎SP_BT_FIRST ويُرفض غيرُ الصالح", f"{env!r} ← {ns['FIRST']}")
        break
else:
    check(True, "٢ أوّلُ تاريخٍ يُمدّ بـ‎SP_BT_FIRST (منذ 2019) ويُرفض غيرُ الصالح، و2023 افتراضاً لمقاييس الحارس")
check("def horizon_report" in bt and "@@HORIZON@@" in bt and "horizon_report(obs, anchors)" in bt and "بالسنة" in bt,
      "٣ وتقريرٌ لكلّ أفق: العادلُ والمستهدف ونصفا التاريخ وكلُّ سنةٍ وإصابةُ «رخيص» و«غالٍ» وفارقُ الخُمسين")
ops = open(os.path.join(ROOT, ".github/workflows/ops.yml"), encoding="utf-8").read()
blk = ops[ops.find("            history_ab)"):ops.find("            candidate_ab)")]
check("- history_ab" in ops and blk.count("SP_BT_FIRST=2019-03") == 2 and "SP_CODE_ROOT=/tmp/control -e SP_BT_FIRST=2019-03" in blk,
      "٤ ومهمّةُ التاريخ الطويل تقيس الأساسَ (طريقةَ متوسّط النماذج) والمرشَّحَ معاً على البيانات نفسِها")
fz = open(os.path.join(ROOT, "scripts/audit/engine_freeze_d635.py"), encoding="utf-8").read()
check('"o_ic3": (+1' in fz, "٥ وأفقُ التسعين محروسٌ في حارس التجميد")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
