#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D257 — بيتا مقيسةٌ من سوقنا، منزوعةُ الرافعة، بوسيطِ قطاعٍ لا بمتوسّطه.
#
# محرّكُ القيمة العادلة يطلب بيتا قطاعيةً **غيرَ مرفوعة**، وما في ملفّ
# المعايير من جدول أسواقٍ ناشئةٍ أجنبيةٍ معلَّمٍ «غيرُ موثَّق» — يُنزِل
# الثقةَ في كلّ مخرَجٍ ويمنع الاعتماد. و«أرقام» تنشر بيتا لكلّ شركة
# مقيسةً من تاسي (قِيست التغطيةُ على الخادم ‎30/30).
#
# وخطرُ الاستعمال المباشر أن تُنسَخ بيتا **مرفوعةٌ** في خانةٍ تطلب غيرَ
# المرفوعة — فتُحسب رافعةُ الشركة مرّتين. فيُقاس السلوك:
#   ٠· نزعُ الرافعة بهامادا يصحّ عدداً
#   ١· وبلا دَينٍ تبقى البيتا كما هي
#   ٢· وبلا رافعةٍ مقروءةٍ لا يُنزَع شيءٌ ولا تُفترَض صفرية
#   ٣· والشاذُّ يُستبعَد (سالبةٌ · فوق ثلاثة)
#   ٤· والقطاعُ وسيطٌ لا متوسّط — شاذٌّ واحدٌ لا يُزيحه
#   ٥· وقطاعٌ دون حدّ النظائر لا يُوثَّق
#   ٦· والحدّان من ملفّ المعايير يُطبَّقان
#   ٧· والمحرّكُ يقرأ المقيسَ ويعلن توثيقَه، وبغيابه يعود للملفّ بعلامته
#   ٨· والجدولُ يشيخ فيسقط التوثيق
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os as _os
import tempfile as _tf

_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

import datetime as _dt  # noqa: E402
import pathlib  # noqa: E402
import sys  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

fail = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))


from app.services import lastgood  # noqa: E402
from app.services import sector_betas as sb  # noqa: E402

TAX = 0.20

# ── ٠ · ١ · ٢ · نزعُ الرافعة ─────────────────────────────────────────────
bu = sb.unlever(1.20, 40.0, 100.0, TAX)
expect = 1.20 / (1 + 0.8 * 0.4)
check(bu is not None and abs(bu - expect) < 1e-9,
      "٠ هامادا يصحّ عدداً", f"{bu:.4f} · المتوقَّع {expect:.4f}")
check(abs(sb.unlever(1.20, 0.0, 100.0, TAX) - 1.20) < 1e-9,
      "١ وبلا دَينٍ تبقى البيتا كما هي")
check(sb.unlever(1.20, None, 100.0, TAX) is None
      and sb.unlever(1.20, 40.0, 0.0, TAX) is None,
      "٢ وبلا رافعةٍ مقروءةٍ لا يُنزَع شيءٌ ولا تُفترَض صفرية")
check(sb.unlever(-0.5, 10.0, 100.0, TAX) is None
      and sb.unlever(4.0, 10.0, 100.0, TAX) is None,
      "٣ والشاذُّ يُستبعَد — سالبةٌ أو فوق ثلاثة")

# ── ٤ · ٥ · ٦ · جدولُ القطاعات ───────────────────────────────────────────
# أرقامُ البيتا من حصادِ الخادم الحقيقيّ (‏1010: 0.97 · 1020: 1.15 …).
betas = {"1010": 0.97, "1020": 1.15, "1030": 0.84, "1050": 1.08,
         "1060": 0.80, "9999": 2.95,            # شاذٌّ داخل المعقول لكنه طرف
         "2010": 1.02, "2020": 0.82}            # قطاعٌ بشركتين فقط
sectors = {s: "البنوك" for s in ("1010", "1020", "1030", "1050", "1060", "9999")}
sectors.update({"2010": "المواد الأساسية", "2020": "المواد الأساسية"})
lev = {s: (0.0, 100.0) for s in betas}          # بلا دَين: βu = βl
table, rep = sb.build_table(betas, lev, sectors, tax=TAX, floor=0.60, cap=2.00)

check("البنوك" in table and table["البنوك"]["n"] == 6,
      "٤ القطاعُ يُبنى من نظرائه", str(table.get("البنوك")))
check(abs(table["البنوك"]["beta"] - 1.025) < 1e-6,
      "٤ب ووسيطٌ لا متوسّط — الشاذُّ الطرفيُّ لا يُزيحه",
      f"وسيط {table['البنوك']['beta']} · متوسّط {sum([0.97,1.15,0.84,1.08,0.80,2.95])/6:.3f}")
check("المواد الأساسية" not in table and rep.get("قطاعاتٌ دون الحدّ") == 1,
      "٥ وقطاعٌ بشركتين لا يُوثَّق — وسيطُ اثنين ليس قطاعاً", str(rep))

hi = {"1010": 2.9, "1020": 2.8, "1030": 2.95}
t2, _ = sb.build_table(hi, {s: (0.0, 100.0) for s in hi},
                       {s: "البنوك" for s in hi}, tax=TAX, floor=0.60, cap=2.00)
check(t2["البنوك"]["beta"] == 2.00, "٦ والحدُّ الأعلى من ملفّ المعايير يُطبَّق",
      str(t2["البنوك"]["beta"]))

# ── ٧ · ٨ · ما يراه المحرّك ─────────────────────────────────────────────
from app.services.fair_value_engine.params import load_params  # noqa: E402

P = load_params(allow_unverified=True, allow_stale=True)
b_file, ver_file = P.unlevered_beta("البنوك")
check(ver_file is False and abs(b_file - 0.75) < 1e-9,
      "٧ بلا جدولٍ مقيسٍ يعود المحرّكُ لملفّه بعلامة «غير موثَّق»",
      f"{b_file} · موثَّق={ver_file}")

lastgood.save(sb.STORE_KEY, {"as_of": _dt.date.today().isoformat(),
                             "sectors": {"البنوك": {"beta": 1.025, "n": 6}}})
b_live, ver_live = P.unlevered_beta("البنوك")
check(abs(b_live - 1.025) < 1e-9 and ver_live is True,
      "٧ب ومع الجدول المقيس يقرؤه ويُعلن توثيقَه", f"{b_live} · موثَّق={ver_live}")
check(P.provenance().get("betas_measured_sectors") == 1,
      "٧ج والأثرُ يحمل عددَ القطاعات المقيسة")
b_other, ver_other = P.unlevered_beta("الطاقة")
check(ver_other is False and abs(b_other - 0.90) < 1e-9,
      "٧د وقطاعٌ لم يُقَس يبقى على الملفّ بعلامته — لا يرث توثيقَ غيره",
      f"{b_other} · موثَّق={ver_other}")

old = (_dt.date.today() - _dt.timedelta(days=sb.MAX_AGE_DAYS + 3)).isoformat()
lastgood.save(sb.STORE_KEY, {"as_of": old,
                             "sectors": {"البنوك": {"beta": 1.025, "n": 6}}})
b_aged, ver_aged = P.unlevered_beta("البنوك")
check(sb.reading() is None and ver_aged is False and abs(b_aged - 0.75) < 1e-9,
      f"٨ وجدولٌ أقدمُ من {sb.MAX_AGE_DAYS} يوماً يسقط توثيقُه", f"{b_aged}")

# ── ٩ · الرافعةُ تُقرأ من مفتاح القوائم الحقيقيّ ────────────────────────
# أوّلُ تشغيلٍ على الخادم قال «بلا رافعة: 268 من 268» — صفرٌ مطلقٌ علامةُ
# مفتاحٍ خاطئ لا سوقٍ ناقص. فيُقاس أن الدالّةَ تجد ما يضعه التطبيقُ فعلاً.
import asyncio  # noqa: E402

from app.services import cache as _c  # noqa: E402

for _s in ("1010", "1020", "1030"):
    _c.set(f"stmt:{_s}.SR", {"periods": [{"equity": 100.0, "debt_ratio": 40.0}]}, 3600)


async def _h(syms):
    return {s: 1.2 for s in syms}


import app.services.argaam_beta as _ab  # noqa: E402
_ab.harvest = _h                                                 # type: ignore[assignment]
rec = asyncio.run(sb.refresh(["1010", "1020", "1030"]))
rep = rec.get("تقرير") or (rec.get("تقرير") if isinstance(rec, dict) else {}) or {}
check(rep.get("دخلت") == 3 and rep.get("بلا رافعة") == 0,
      "٩ الرافعةُ تُقرأ من مفتاح القوائم الحقيقيّ — لا من مفتاحٍ مخترَع",
      str(rep))

print(("FAIL" if fail else "PASS") + " D257 — بيتا قطاعيةٌ مقيسةٌ من سوقنا")
raise SystemExit(fail)
