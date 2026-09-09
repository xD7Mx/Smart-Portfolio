#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D212 — القيمةُ النسبيةُ تمتنع حيث يجب، ولا تُقارَن الشركةُ بنفسها.
#
# الخطرُ في هذا النموذج ليس في حسابه بل في **صمته**: يمرّ برقمٍ مقبولِ
# الشكل حيث كان الواجبَ الامتناع. فتُقاس هنا القراراتُ لا الصياغة —
# بمعطياتٍ مُصطنَعةٍ معلومةِ الجواب سلفاً.
#
# ويُفحص خاصّةً استبعادُ الشركة من وسيط قطاعها: بدونه تُسحَب النتيجةُ نحو
# السعر الحاليّ فيصير كلُّ سهمٍ «عادلاً» — عيبٌ صامتٌ لا يظهر بالنظر.
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os as _os, tempfile as _tf
# رملةُ الحالة قبل أيّ استيراد — شرطُ اللجنة على كلّ فحوصها (‏audit_sandbox).
# والوحدةُ هنا خالصةُ الحساب لا تمسّ مخزناً، لكنّ الشرطَ يُلتزم بلا استثناء:
# استثناءٌ «لأنّ هذه آمنة» هو أوّلُ ثقبٍ في القاعدة.
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

from app.services.relative_value import (MIN_PEERS, SectorTable,  # noqa: E402
                                         relative_value)

fail = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))


def rows(sector: str, pes: list[float], pbs: list[float]) -> list[dict]:
    return [{"sector": sector, "pe": pe, "pb": pb} for pe, pb in zip(pes, pbs)]


# ── ١ · قطاعٌ رقيقٌ ⇒ امتناع ──────────────────────────────────────────
thin = SectorTable(rows("رقيق", [10, 11, 12], [1, 1.1, 1.2]))
r = relative_value(sector="رقيق", price=50, pe=10, pb=1.0,
                   book_value=10, table=thin)
check(r["value"] is None and "نظائر" in (r["why"] or ""),
      f"١ أقلُّ من {MIN_PEERS} نظائرَ ⇒ امتناعٌ مُعلَّل", r["why"] or "—")

# ── ٢ · الشركةُ لا تُقارَن بنفسها ────────────────────────────────────
# ستُّ شركاتٍ مكرّرُها ‎10 وواحدةٌ ‎30. لو دخلت الثلاثون في الوسيط لسحبته؛
# واستبعادُها يُبقيه ‎10 فتظهر الشركةُ مبالغاً في سعرها — وهو الصواب.
sec = SectorTable(rows("قطاع", [10, 10, 10, 10, 10, 10, 30],
                       [1, 1, 1, 1, 1, 1, 3]))
own = relative_value(sector="قطاع", price=300, pe=30, pb=3,
                     book_value=100, table=sec)
# ربحيةُ السهم = 300/30 = 10 ⇒ قيمةٌ بمكرّر القطاع 10 × 10 = 100
check(own["value"] is not None and abs(own["paths"]["مكرر الربحية"]["value"] - 100) < 1e-6,
      "٢ مضاعفُ الشركة يُنزَع من وسيط قطاعها",
      f"قيمةُ مسار المكرّر {own['paths']['مكرر الربحية']['value']:.1f} (السعر 300)")

# ── ٣ · خسارةٌ تُبطل المكرّر ولا تُبطل الدفترية ──────────────────────
loss = relative_value(sector="قطاع", price=50, pe=-8, pb=1.0,
                      book_value=20, table=sec)
check(loss["value"] is not None and "مكرر الربحية" not in loss["paths"]
      and "مضاعف القيمة الدفترية" in loss["paths"],
      "٣ الخاسرةُ تُقيَّم بالدفترية وحدَها", f"مسارات: {list(loss['paths'])}")

# ── ٤ · لا مقياسَ موجب ⇒ امتناع ──────────────────────────────────────
none_m = relative_value(sector="قطاع", price=50, pe=None, pb=None,
                        book_value=None, table=sec)
check(none_m["value"] is None, "٤ بلا مقياسٍ موجب ⇒ امتناع", none_m["why"] or "—")

# ── ٥ · قطاعٌ غيرُ مصنّف ⇒ امتناع ────────────────────────────────────
nosec = relative_value(sector=None, price=50, pe=10, pb=1,
                       book_value=10, table=sec)
check(nosec["value"] is None, "٥ قطاعٌ غيرُ مصنّفٍ ⇒ امتناع", nosec["why"] or "—")

# ── ٦ · مسارٌ واحدٌ لا يبلغ ثقةً مرتفعة ──────────────────────────────
check(loss["confidence"] != "مرتفعة",
      "٦ المسارُ الواحد لا يبلغ «مرتفعة»", f"الثقة {loss['confidence']}")

# ── ٧ · النطاقُ يحيط بالقيمة ─────────────────────────────────────────
check(own["low"] <= own["value"] <= own["high"],
      "٧ النطاقُ يحيط بالقيمة",
      f"[{own['low']:.1f} · {own['value']:.1f} · {own['high']:.1f}]")

# ── ٨ · تشتّتٌ واسعٌ يخفض الثقة ──────────────────────────────────────
wide = SectorTable(rows("واسع", [4, 8, 15, 30, 60, 90], [0.4, 1, 2, 4, 8, 12]))
w = relative_value(sector="واسع", price=100, pe=20, pb=2,
                   book_value=50, table=wide)
tight = SectorTable(rows("ضيق", [10, 10.5, 11, 11.5, 12, 12.5],
                         [1, 1.05, 1.1, 1.15, 1.2, 1.25]))
t = relative_value(sector="ضيق", price=100, pe=11, pb=1.1,
                   book_value=90, table=tight)
order = {"منخفضة": 0, "متوسطة": 1, "مرتفعة": 2}
check(order[w["confidence"]] < order[t["confidence"]],
      "٨ القطاعُ المتباعدُ أقلُّ ثقةً من المتقارب",
      f"واسع {w['confidence']} · ضيّق {t['confidence']}")

print()
print("النتيجة:", "فيه ملاحظات ✘" if fail else "نظيف ✔")
raise SystemExit(fail)
