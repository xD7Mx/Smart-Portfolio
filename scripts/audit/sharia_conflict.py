#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D214 — عند تعارض مصدرَي الشرعية يُؤخذ الأشدّ، ويُعلَن التعارض.
#
# رأى المالكُ «المملكة» (‏4280) **مختلطة** وهي **غيرُ متوافقة** عند أرقام.
# والأولويةُ (المقاصد ← أرقام) كانت تأخذ الأوّلَ صامتةً فيُخفى الخلاف.
#
# وقِيس مداه قبل العلاج: ‎54 اختلافاً بين المصدرين على ‎206 شركةٍ مشتركة،
# في ‎52 منها المقاصدُ أشدّ — فالأولويةُ تعمل صواباً — وفي **اثنين فقط**
# أرقامُ أشدّ (‏4280 · 4072). فالعلاجُ جراحيّ لا انقلابٌ على الأولوية.
#
# ونصُّ الميثاق: «عند الشك يُخفَّض التقييم لا يُرفَع». وحكمٌ شرعيٌّ أخفُّ
# من أحد مصدرَيه ليس ترجيحاً بل تساهلٌ في أخطرِ ما يعرضه هذا التطبيق.
#
# يُقاس السلوكُ على البيانات الحقيقية لا على نصّ الدالّة.
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os as _os, tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

from app.services import maqasid  # noqa: E402

RANK = {"COMPLIANT": 0, "MIXED": 1, "NON_COMPLIANT": 2}
DATA = ROOT / "backend" / "app" / "data"
fail = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))


m = json.loads((DATA / "maqasid_ratings.json").read_text(encoding="utf-8"))["ratings"]
a = json.loads((DATA / "argaam_ratings.json").read_text(encoding="utf-8"))["ratings"]

# ── ١ · لا حكمَ معروضٌ أخفُّ من أشدِّ مصدرَيه ───────────────────────────
soft = []
for sym in m:
    if sym not in a:
        continue
    r = maqasid.rating(sym) or {}
    strictest = max(RANK.get(m[sym].get("status"), 0), RANK.get(a[sym].get("status"), 0))
    if RANK.get(r.get("status"), 0) < strictest:
        soft.append(sym)
check(not soft, "١ لا حكمَ معروضٌ أخفُّ من أشدِّ مصدرَيه",
      f"{len(soft)} مخالفاً" + (f": {soft[:6]}" if soft else ""))

# ── ٢ · «المملكة» غيرُ متوافقة ─────────────────────────────────────────
# الشاهدُ الذي رآه المالك — يُثبَّت بعينه فلا يعود بصمت.
r4280 = maqasid.rating("4280") or {}
check(r4280.get("status") == "NON_COMPLIANT",
      "٢ «المملكة» (‏4280) غيرُ متوافقة", str(r4280.get("status")))

# ── ٣ · التعارضُ يُعلَن ولا يُخفى ──────────────────────────────────────
check(bool(r4280.get("note")) and "المقاصد" in (r4280.get("source") or "") + (r4280.get("note") or ""),
      "٣ التعارضُ معلَنٌ بمصدريه", f"{r4280.get('source')} · {r4280.get('note')}")

# ── ٤ · لا تطهيرَ لِما حُكم بعدم توافقه ────────────────────────────────
# مبلغُ التطهير معنىً خاصٌّ بالمختلطة؛ بقاؤه مع «غير متوافقة» يناقضها.
check(r4280.get("purification") is None,
      "٤ لا مبلغَ تطهيرٍ مع «غير متوافقة»", str(r4280.get("purification")))

# ── ٥ · الأولويةُ باقيةٌ حيث لا تعارض ──────────────────────────────────
# ‎52 حالةً المقاصدُ فيها أشدّ — يجب أن تبقى كما هي، فالعلاجُ لم يقلب
# الأولوية بل قيّدها بالتشدّد وحدَه.
kept = [s for s in m if s in a
        and RANK.get(m[s].get("status"), 0) > RANK.get(a[s].get("status"), 0)
        and (maqasid.rating(s) or {}).get("status") == m[s].get("status")]
harsher_maq = [s for s in m if s in a
               and RANK.get(m[s].get("status"), 0) > RANK.get(a[s].get("status"), 0)]
check(len(kept) == len(harsher_maq),
      "٥ حكمُ المقاصد باقٍ حيث هو الأشدّ", f"{len(kept)} من {len(harsher_maq)}")

# ── ٦ · ولا يتغيّر حكمٌ متّفَقٌ عليه ───────────────────────────────────
agreed = [s for s in m if s in a and m[s].get("status") == a[s].get("status")]
same = [s for s in agreed if (maqasid.rating(s) or {}).get("status") == m[s].get("status")]
check(len(same) == len(agreed), "٦ المتّفَقُ عليه لا يتغيّر",
      f"{len(same)} من {len(agreed)}")

print()
print("النتيجة:", "فيه ملاحظات ✘" if fail else "نظيف ✔")
raise SystemExit(fail)
