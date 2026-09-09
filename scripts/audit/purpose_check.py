#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# البند ٣٠ — لكلّ ميزةٍ غرضٌ مكتوب، وفحصٌ للاتّجاه المعاكس.
#
# ## لماذا وُجد هذا الحارس
# سُنَّ البندُ بعد عطب جدول التوزيع: جدولٌ غرضُه التوازن كان يزيد الاختلال،
# ومرّ لأنّ كلَّ فحوصه سألت عن **النقص** ولا واحدةٌ سألت عن **التجاوز**.
# وقاعدةٌ في وثيقةٍ بلا حارسٍ تُنسى يومَ يكثر العمل — وهو اليوم الذي
# تُسلَّم فيه حزمةٌ معطوبة.
#
# ## ما يفحصه
# لكلّ ميزةٍ في `purpose.json`:
#   ١· غرضٌ مكتوبٌ في جملة، واتّجاهٌ معاكسٌ مُعلَن
#   ٢· ملفُّ فحصٍ موجود، وهو **مشغَّلٌ في اللجنة** لا متروكٌ على القرص
#   ٣· وفي الفحص شاهدٌ نصّيٌّ يخصّ الاتّجاه المعاكس — لا فحصٌ يسمّي نفسه
#      باسم الميزة ويسأل عن الاتّجاه المألوف وحدَه
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os as _os, tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SPEC = ROOT / "scripts" / "audit" / "purpose.json"
RUN = ROOT / "scripts" / "audit" / "run.sh"

fail = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))


spec = json.loads(SPEC.read_text(encoding="utf-8"))
feats = spec.get("features") or []
run_sh = RUN.read_text(encoding="utf-8")

check(len(feats) >= 5, "قلبُ التطبيق موصوفٌ بالغايات", f"{len(feats)} ميزةً")

for f in feats:
    name = f.get("الميزة", "؟")
    parts_ok = all(f.get(k) for k in ("الغرض", "الاتجاه المألوف", "الاتجاه المعاكس"))
    check(parts_ok, f"«{name}» غرضُها واتّجاهاها مكتوبة",
          "" if parts_ok else "نقصٌ في الوصف")

    path = ROOT / str(f.get("الفحص") or "")
    exists = path.is_file()
    check(exists, f"«{name}» لها ملفُّ فحص", str(f.get("الفحص")))
    if not exists:
        continue

    # الفحصُ الموجودُ على القرص ولا يُشغَّل لا يحرس شيئاً (البند ٣١).
    wired = pathlib.Path(str(f.get("الفحص"))).name in run_sh
    check(wired, f"«{name}» فحصُها مشغَّلٌ في اللجنة",
          "" if wired else "موجودٌ ولا يُستدعى")

    # وشاهدُ الاتّجاه المعاكس مكتوبٌ في الفحص نفسِه.
    body = path.read_text(encoding="utf-8", errors="replace")
    token = str(f.get("شاهد") or "")
    # ══ شاهدٌ يخصّ الاتّجاه المعاكس لا كلمةً عامّة ══
    # كُتب شاهدُ «قرار التطبيق» كلمةَ «قرار» — وهي في كلّ ملفّ، فيمرّ الفحصُ
    # بلا معنى. وذلك بعينه ما حرّمه البند ٣١، ووقعتُ فيه وأنا أسنّه.
    # فيُشترط طولٌ يميّز: شاهدٌ من كلمتين فأكثر وعشرةِ حروفٍ فصاعداً.
    specific = len(token.strip()) >= 10 and len(token.split()) >= 2
    check(specific, f"«{name}» شاهدُها يخصّ الاتّجاه المعاكس لا كلمةٌ عامّة",
          f"«{token}»")
    has = bool(token) and token in body
    check(has, f"«{name}» فحصُها يسأل عن الاتّجاه المعاكس", f"«{token}»")

print()
print("النتيجة:", "فيه ملاحظات ✘" if fail else "نظيف ✔")
raise SystemExit(fail)
