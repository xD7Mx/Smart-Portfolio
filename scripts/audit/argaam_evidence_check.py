#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D218 — شواهدُ «أرقام» بيّنةٌ لا حَكَم.
#
# صار عندنا وصولٌ محدَّثٌ إلى «أرقام»، وأمر المالكُ أن يستند إليه رأيُ
# الذكاء — **بشرط ألّا ينشأ حكمٌ ثانٍ**: القرارُ يخرج من محرّك القواعد
# وحدَه (‏D166)، والرأيُ يشرحه.
#
# والخطرُ هنا دقيق: توصيةُ بيت خبرةٍ «شراء» نصٌّ حاسمُ اللهجة. فإن دخلت
# ملخَّصةً («الشواهد إيجابية») صارت حكماً منافساً؛ وإن أُخفيت حين تخالف،
# كذبنا بالسكوت. فالقاعدة: تُذكر كما هي بأسمائها وتواريخها، ويُلزَم
# التوجيهُ بإعلان الخلاف بوصفه واقعة.
#
# يُقاس السلوكُ: بناءُ الأسطر من شواهدَ مُصطنَعة، ووجودُ قيد «بيّنةٌ لا
# حكم» في التوجيه، وبقاءُ الحكم للمحرّك في نقطة النهاية.
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

from app.services.argaam_evidence import evidence_lines  # noqa: E402

fail = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))


EV = {
    "recommendations": [
        {"house": "الراجحي المالية", "verdict": "شراء", "target": 88.0, "date": "2026-08-12"},
        {"house": "أوبار كابيتال", "verdict": "احتفاظ", "target": None, "date": "2026-07-26"},
    ],
    "ratios": {"car": 19.4, "npl": 1.2},
    "calendar": [{"date": "2026-10-20", "title": "إعلان نتائج"}],
}
lines = evidence_lines(EV)

# ── ١ · التوصياتُ تُذكر بأسمائها لا ملخَّصةً في حكم ────────────────────
joined = " ".join(lines)
check("الراجحي المالية" in joined and "أوبار كابيتال" in joined
      and "شراء" in joined and "احتفاظ" in joined,
      "١ كلُّ توصيةٍ باسم بيتها وحكمها", f"{len(lines)} سطراً")

# ── ٢ · ولا تُختزل في وصفٍ جامع ────────────────────────────────────────
# «الشواهد إيجابية» حكمٌ ثانٍ متنكّرٌ في صيغة وصف.
banned = ("إيجابية عموماً", "الشواهد إيجابية", "الشواهد سلبية", "إجماع")
check(not any(b in joined for b in banned),
      "٢ لا خلاصةَ حاكمةً في الشواهد", joined[:60] + "…")

# ── ٣ · ويُعلَن أنها بيّنةٌ لا حكم ─────────────────────────────────────
check("بيّنةٌ لا حكم" in joined, "٣ الشواهدُ موسومةٌ «بيّنةٌ لا حكم»")

# ── ٤ · التواريخُ تصحب التوصيات ────────────────────────────────────────
check("2026-08-12" in joined, "٤ تاريخُ كلّ توصيةٍ معها — توصيةٌ بلا تاريخٍ لا عمرَ لها")

# ── ٥ · النِّسَبُ الرقابيةُ بأسمائها العربية ───────────────────────────
check("كفاية رأس المال" in joined and "19.4" in joined,
      "٥ النِّسَبُ الرقابيةُ بأسمائها لا بمفاتيحها")

# ── ٦ · الغيابُ لا يُنتج سطراً فارغاً ─────────────────────────────────
check(evidence_lines({}) == [], "٦ بلا شواهدَ لا أسطر", str(evidence_lines({})))

# ── ٧ · التوجيهُ يُلزم بإعلان الخلاف ولا يُطاوع الأعلى صوتاً ──────────
ai = (ROOT / "backend/app/services/ai_content.py").read_text(encoding="utf-8")
check("بيّنةٌ لا حكم" in ai and "خالفت" in ai and "قراراً ثانياً" in ai,
      "٧ التوجيهُ يُلزم بإعلان الخلاف لا بإخفائه")

# ── ٨ · والحكمُ يبقى للمحرّك في نقطة النهاية ──────────────────────────
# القاعدةُ الأقدم (‏D166) لا يجوز أن تنكسر بإدخال مصدرٍ جديد.
ep = (ROOT / "backend/app/api/v1/endpoints/ai.py").read_text(encoding="utf-8")
check('opinion["sentiment_label"] = unified' in ep,
      "٨ حكمُ الشاشة يُستبدَل بقرار المحرّك مهما قالت الشواهد")

# ── ٩ · صقرٌ ورأيُ الذكاء من مَعينٍ واحد ──────────────────────────────
# بأمر المالك: مصدرُ معلوماتهما واحدٌ فيتطابق مخرَجُهما. ولو استقى كلٌّ
# من موضعٍ لاختلف تقريرُ التلغرام عن بطاقة الشاشة في واقعةٍ منشورة —
# وهو بعينه ما مُنع في القرار (‏D166) فيُمنع في الشاهد.
analyst = (ROOT / "backend/app/services/ai_analyst.py").read_text(encoding="utf-8")
both = ("argaam_evidence" in analyst and "evidence_lines" in analyst
        and "argaam_evidence" in ep and "evidence_lines" in ep)
check(both, "٩ صقرٌ ورأيُ الذكاء يستدعيان جامعَ الشواهد نفسَه",
      "المَعين واحد" if both else "مصدران منفصلان")

# ── ١٠ · وصقرٌ لا يبني خلاصتَه على توصية بيت خبرة ─────────────────────
# الشاهدُ يُعرض في قسمه، والخلاصةُ تبقى من إشارات التطبيق نفسِها.
i_ev = analyst.find("شواهد من «أرقام»")
i_verdict = analyst.find("verdict = _verdict(")
check(i_ev != -1 and i_verdict != -1 and i_ev < i_verdict,
      "١٠ الشواهدُ قسمٌ مستقلٌّ قبل الخلاصة لا مدخلٌ فيها")

print()
print("النتيجة:", "فيه ملاحظات ✘" if fail else "نظيف ✔")
raise SystemExit(fail)
