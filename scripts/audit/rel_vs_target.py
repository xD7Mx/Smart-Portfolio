#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D213 — القيمةُ النسبيةُ تملأ الفراغَ ولا تستبدل رأيَ محلّل.
#
# خطرُ وصلِ محرّكٍ تقديريٍّ بالفرز أن يزحف على حقلٍ قائم: فيرى المستخدمُ
# رقماً في خانة «القيمة العادلة» ويظنّه رأيَ بيوت الخبرة وهو مضاعفُ قطاع.
# والفرقُ ليس تسميةً بل مصدرَ حكمٍ يُبنى عليه قرارُ شراء.
#
# فيُقاس السلوكُ لا الصياغة: يُشغَّل مسارُ الإثراء على صفّين — واحدٌ له
# هدفُ محلّلين وآخرُ بلا هدف — ويُشترط:
#   ١· صاحبُ الهدف: `fair_value` هدفُه، و`rel_value` فارغةٌ تماماً
#   ٢· الذي بلا هدف: `fair_value` تبقى None، والقيمةُ النسبية في حقلها
#   ٣· وكلُّ قيمةٍ نسبيةٍ تحمل تسميتَها ودرجةَ ثقتها — لا رقمَ عارياً
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os as _os, tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

from app.services.relative_value import SectorTable, relative_value  # noqa: E402

fail = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))


# قطاعٌ من عشرِ شركاتٍ مضاعفاتُه معلومة، تُبنى منه مائدةُ النظائر.
peers = [{"sector": "قطاع", "pe": 10 + i * 0.3, "pb": 1 + i * 0.03}
         for i in range(10)]
table = SectorTable(peers)


def enrich(target, pe, pb, bv, price):
    """محاكاةُ ما يفعله الفرز: الهدفُ أوّلاً، والنسبيةُ حيث لا هدف.

    تُكتب هنا القاعدةُ نفسُها لا الشيفرةُ نفسُها — والفحصُ يقيس القاعدة.
    """
    row: dict = {"fair_value": target, "rel_value": None, "rel_conf": None,
                 "rel_basis": None}
    if target is None:
        r = relative_value(sector="قطاع", price=price, pe=pe, pb=pb,
                           book_value=bv, table=table)
        if r["value"] is not None:
            row["rel_value"] = r["value"]
            row["rel_conf"] = r["confidence"]
            row["rel_basis"] = r["basis"]
    return row


# ── ١ · صاحبُ الهدف لا تُحسب له نسبية ────────────────────────────────
a = enrich(target=55.0, pe=11, pb=1.1, bv=40, price=50)
check(a["fair_value"] == 55.0 and a["rel_value"] is None,
      "١ حيث وُجد هدفُ المحلّلين لا تُحسب قيمةٌ نسبية",
      f"fair_value={a['fair_value']} · rel_value={a['rel_value']}")

# ── ٢ · الذي بلا هدفٍ تُحسب له، ولا تُدسّ في حقل الهدف ───────────────
b = enrich(target=None, pe=11, pb=1.1, bv=40, price=50)
check(b["fair_value"] is None and b["rel_value"] is not None,
      "٢ حيث لا هدفَ تُحسب النسبيةُ في حقلها، ويبقى حقلُ الهدف فارغاً",
      f"fair_value={b['fair_value']} · rel_value={b['rel_value']:.2f}")

# ── ٣ · لا رقمَ عارياً: تسميةٌ ودرجةُ ثقةٍ مع كلّ قيمة ────────────────
check(bool(b["rel_basis"]) and bool(b["rel_conf"]),
      "٣ كلُّ قيمةٍ نسبيةٍ تحمل تسميتَها ودرجةَ ثقتها",
      f"«{b['rel_basis']}» · {b['rel_conf']}")

# ── ٤ · التسميةُ «السعر العادل» بأمر المالك ──────────────────────────
# ══ قاعدةٌ نُقضت بقرارِ مالكٍ لا بسهو ══ (D237)
# كان الشرطُ عكسَ هذا: ألّا تدّعي التسميةُ «قيمةً عادلة» — حفظاً لاسمٍ
# كان محجوزاً لتقدير المحرّك المغلق (‏D175 · D176). وقال المالك: «المحرّكُ
# يستحقّ اللقب بسبب شموليته… وفي الآخر هي اجتهادات، والسعرُ العادل عندي
# ليس كغيري». فصار الاسمُ له، ولا يبقى اسمانِ لمعنًى واحد: من يحمل
# اللقبَ يحكم به القرارُ أيضاً (فحصُ decision_fv_gate).
check((b["rel_basis"] or "") == "السعر العادل",
      "٤ التسميةُ «السعر العادل» — لقبٌ واحدٌ لا اسمانِ", b["rel_basis"] or "—")

# ── ٥ · مسارُ الفرز نفسُه يستدعي المحرّك حيث لا هدف ──────────────────
# فحصُ بنيةٍ واحدٌ لا غنى عنه: القاعدةُ أعلاه تُحاكي، وهذا يتأكّد أنّ
# الفرزَ موصولٌ فعلاً — وإلا فحصنا قاعدةً لا تعمل في التطبيق.
src = (ROOT / "backend/app/services/market_screener.py").read_text(encoding="utf-8")
wired = "_relative_value(" in src and 'r["rel_value"]' in src
check(wired, "٥ الفرزُ موصولٌ بالمحرّك", "استدعاءٌ وحقلٌ موجودان" if wired else "غير موصول")

# ── ٦ · التغطيةُ شاملةٌ للتطبيق ──────────────────────────────────────
# بأمر المالك: القيمةُ النسبيةُ تصل «تحليل الذكاء» كما وصلت الفرزَ وصفحةَ
# السهم. وشاشةٌ غرضُها التقييمُ تعرض شركةً بلا رقمِ تقييمٍ عطبٌ في التغطية.
movers = (ROOT / "backend/app/services/market_movers.py").read_text(encoding="utf-8")
ai = (ROOT / "frontend/src/pages/AIPage.tsx").read_text(encoding="utf-8")
check('"rel_value": result.get("rel_value")' in movers,
      "٦ صفُّ تحليل الذكاء يحمل القيمةَ النسبية")
check("c.rel_value" in ai and "السعر العادل" in ai,
      "٧ وتُعرض باسمها لا في خانة هدف المحلّلين")
# والاتّجاه المعاكس: لا تُعرض حيث يوجد هدف — الشرطُ نفسُه في الشاشات كلِّها.
check("c.fair_value != null ? c.fair_value.toFixed(2)" in ai,
      "٨ وحيث وُجد الهدفُ يُعرض هو لا هي")

print()
print("النتيجة:", "فيه ملاحظات ✘" if fail else "نظيف ✔")
raise SystemExit(fail)
