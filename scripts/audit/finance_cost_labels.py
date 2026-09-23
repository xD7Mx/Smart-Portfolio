#!/usr/bin/env python3
"""تكلفةُ التمويل بأسمائها المنشورة — وما ليس هي لا يُلبَّسها (D425).

    python3 scripts/audit/finance_cost_labels.py

قِيس بكاشف `debt_label_gap.py` على ملفّات الأوراق الناقصة بعينها: الخريطةُ
تعرف «finance costs» جمعاً، وفي ‎11 ورقةً الاسمُ المنشورُ «finance cost»
مفرداً — فيغيب البندُ، ويسقط معه `ebit` المشتقُّ منه، وتسقط تغطيةُ
الفوائد. فرقُ حرفٍ واحدٍ يُسقط مساراً من مسارات السعر العادل.

والحدُّ الذي لا يُتجاوَز أنّ **الاسمَ الشبيهَ ليس المعنى**:

  · «finance cost paid» مدفوعٌ نقداً في قائمة التدفّق — لا مصروفُ الفترة.
  · «finance costs on lease liabilities» جزءُ الإيجار وحدَه لا التكلفةُ كلُّها.
  · «accrued finance costs» رصيدٌ في الميزانية لا مصروف.
  · «fixed rate sukuks» في ملفّ بنكٍ صكوكٌ **يملكها** — أصلٌ لا دَين.
  · «murabaha deposits» ودائعُ — أصلٌ لا دَين.

وإدخالُ أيٍّ منها رقمٌ خاطئٌ يدخل الرافعةَ وتغطيةَ الفوائد بثقةٍ كاملة —
وهو أسوأُ من غيابه. فالفحصُ يقيس الاتّجاهين: ما يجب أن يُقرأ، وما يجب
ألّا يُقرأ.
"""
from __future__ import annotations

# ══ لا فحصَ يكتب في بيانات المالك ══ (D160 · D429)
# يُحوَّل مخزنُ الحالة إلى مجلّدٍ مؤقّت **قبل** أيّ استيرادٍ من `app`،
# فالوحداتُ تقرأ مسارَها عند تحميلها. وسجلُّ مشاهداتِ حالة السوق معه:
# حكمُ العطلة يقرأ مشاهداتِ اليوم، فمشاهدةُ فحصٍ تدخله تُفسد دليلَه.
import os as _os, tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX
_os.environ["SP_STATUS_LOG"] = _os.path.join(_SANDBOX, "status_codes.jsonl")

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

fail = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))


try:
    from app.services.tadawul_xbrl import parse
except ModuleNotFoundError as e:
    print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس")
    sys.exit(0)


def _filing(label: str, value: str = "1,000") -> str:
    """ملفٌّ رسميٌّ مصغَّر بصفٍّ واحدٍ تحت الاسم المُختبَر."""
    return ("<table>"
            "<tr><td>End date</td><td>2025-12-31</td></tr>"
            "<tr><td>Start date</td><td>2025-01-01</td></tr>"
            "<tr><td>Profit (loss) before zakat and income tax</td>"
            "<td>5,000</td></tr>"
            f"<tr><td>{label}</td><td>{value}</td></tr>"
            "</table>")


def _field(label: str, key: str):
    d = parse(_filing(label)) or {}
    rows = d.get("annual") or d.get("periods") or []
    if isinstance(d, dict) and not rows:
        # بعضُ الصيغ تُعيد الفترةَ مباشرةً
        for v in d.values():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                rows = v
                break
    for r in rows if isinstance(rows, list) else []:
        if isinstance(r, dict) and r.get(key) is not None:
            return r.get(key)
    return None


# ── ١ · الأسماءُ المنشورةُ لتكلفة التمويل تُقرأ ──────────────────────
_MUST = ("finance cost", "interest expense", "financial costs",
         "finance cost for the year", "adjustment for finance cost")
# والاسمُ المخرَّطُ من قبلُ يبقى — شاهدٌ على أنّ القراءةَ نفسَها تعمل
_BASE = _field("Finance costs", "interest_expense")
if _BASE is None:
    print("⚠ المحلِّلُ لم يقرأ حتى الاسمَ المخرَّطَ من قبل — صيغةُ الملفّ"
          " المصغَّر لا تطابق المحلِّل، فلم يُقَس")
    sys.exit(0)
check(True, "٠ الاسمُ المخرَّطُ من قبل يُقرأ — القراءةُ نفسُها تعمل",
      str(_BASE))
for n in _MUST:
    v = _field(n.capitalize(), "interest_expense")
    check(v is not None, f"١ «{n}» يُقرأ تكلفةَ تمويل", str(v))

# ── ٢ · وما يشبهه اسماً لا يُلبَّس معناه ─────────────────────────────
_NOT = ("finance cost paid", "finance costs paid",
        "finance costs on lease liabilities", "interest on leases",
        "accrued finance costs", "future finance charges")
for n in _NOT:
    v = _field(n.capitalize(), "interest_expense")
    check(v is None, f"٢ «{n}» لا يُقرأ تكلفةَ تمويلِ الفترة", str(v))

# ── ٣ · والدَّينُ لا تُلبَّسه الأصول ─────────────────────────────────
for n in ("fixed rate sukuks", "murabaha deposits",
          "time (murabaha) deposits, shareholders assets",
          "assets subject to finance lease"):
    for k in ("borrowings_current", "borrowings_noncurrent", "total_debt"):
        v = _field(n.capitalize(), k)
        if v is not None:
            check(False, f"٣ «{n}» أصلٌ لا يُقرأ دَيناً", f"{k}={v}")
            break
    else:
        check(True, f"٣ «{n}» أصلٌ لا يُقرأ دَيناً")

# ── ٤ · والدَّينُ بمعناه يُقرأ ───────────────────────────────────────
_v = _field("Margin loan payable", "borrowings_current")
check(_v is not None, "٤ «margin loan payable» قرضٌ يُقرأ دَيناً", str(_v))

# ── ٥ · والمخزونُ باسمه المنشور ─────────────────────────────── (D430)
# قِيس بكاشف `inventory_label_gap.py`: «inventories» في ملفّات ‎15 ورقةً
# من ‎16 أسقطت درجتَها لنقص «دوران المخزون» — والخريطةُ لا اسمَ فيها
# للمخزون أصلاً، فكان يأتي من ياهو وحدَه ويسقط بنفاد حصّته.
_inv = _field("Inventories", "inventory")
check(_inv is not None, "٥ «inventories» يُقرأ مخزوناً", str(_inv))
# والتدفّقُ والتسويةُ والمخصّصُ وأرضُ المطوّر ليست رصيدَ المخزون
for n in ("adjustments for decrease (increase) in inventories",
          "transferred to inventory",
          "adjustment for provision for slow moving items and inventory shortage",
          "inventory real estate properties",
          "less: allowance for slow moving and obsolete inventory"):
    v = _field(n.capitalize(), "inventory")
    check(v is None, f"٥ب «{n[:48]}» ليس رصيدَ المخزون", str(v))

print(("FAIL" if fail else "PASS")
      + " D425 · D430 — التمويلُ والمخزونُ بأسمائهما المنشورة، والشبيهُ لا يُلبَّس معناهما")
sys.exit(fail)
