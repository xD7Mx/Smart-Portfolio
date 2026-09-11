#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D236 — عمودٌ عمودٌ: فرزُ السوق مقابلَ صفحة السهم على بياناتٍ حقيقية.
#
# بأمر المالك: «افحص جميع الأعمدة… ستكتشفها أنت بنفسك». وقد أُصلح عمودان
# بالاسم (‏D223 التوزيعات · D226 الجودة) — والباقي لم يُقَس قطُّ.
#
# فهذا مسبارٌ **على الخادم** حيث البيانات: يقرأ صفوفَ الفرز المخدومة
# (بعد الإنعاش) ويشغّل `analyze_company` — منتِجَ صفحة السهم — لكلّ رمزٍ
# في العيّنة، ثم يقارن عموداً عموداً ويطبع كلَّ خلافٍ بالرمز والرقمين.
#
#   docker exec sp_backend python /app/scripts/audit/screener_columns.py
#   docker exec sp_backend python /app/scripts/audit/screener_columns.py 40
#
# لا يكتب شيئاً ولا يحكم بنجاحٍ على فراغ: إن لم تصل صفوفٌ أو تعذّر
# التحليلُ قال ذلك وامتنع.
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import asyncio
import sys

for _p in ("/app", "backend", "."):
    if _p not in sys.path:
        sys.path.insert(0, _p)

N = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 15
TOL = {          # ما يُعدّ خلافاً: النسبةُ تُقاس بالنقاط، والسعرُ بالهللة
    "price": 0.01,
    "change_pct": 0.05,
    "dividend_yield": 0.05,
    "finance_score": 0.5,
    "pe_ratio": 0.05,
    "price_to_book": 0.02,
    "fair_value": 0.01,
    "high_52w": 0.01,
    "low_52w": 0.01,
    "rel_value": 0.01,
}


def _num(x):
    return x if isinstance(x, (int, float)) and not isinstance(x, bool) else None


async def main() -> int:
    from app.services.market_screener import get_cached_screener, refresh_derived
    from app.services.analysis import analyze_company

    rows = get_cached_screener()
    if not rows:
        print("… لا صفوفَ فرزٍ مخدومة (لم يُبنَ المسحُ بعد) — لا حكم.")
        return 0
    rows = [dict(r) for r in rows[:N]]
    print(f"العيّنة: {len(rows)} شركةً من {len(get_cached_screener() or [])}\n")

    # ══ الترتيبُ ليس تفصيلاً ══ (صُحّح بعد أوّل تشغيل)
    # المسبارُ عمليةٌ منفصلةٌ عن الخادم، وكاشُ الأسعار والأساسيات **في
    # الذاكرة** لا على القرص — فيبدأ فارغاً. فلو أُنعشت الصفوفُ أوّلاً
    # لقُرئت من كاشٍ خاوٍ ثمّ حلّلنا الشركاتَ فملأناه، فيُقاس فرقٌ سبَبُه
    # ترتيبُ المسبار لا عطبُ التطبيق. وفي الخادم يجري العكسُ طبعاً:
    # الصفحةُ تُفتح فيُملأ الكاش، ثم يُخدَم الفرزُ من المملوء.
    # فيُحلَّل أوّلاً ثم يُنعَش — كترتيب الخادم لا كترتيب الملفّ.
    # ══ ولا يُقاس تحليلٌ محفوظٌ من أمس ══ (صُحّح بعد التشغيل الثالث)
    # التحليلُ مُكيَّشٌ أربعاً وعشرين ساعةً ومحفوظٌ على القرص. فمسبارٌ
    # يُشغَّل بعد تركيبٍ جديدٍ يقرأ نتيجةَ الشيفرة **القديمة** ويسمّيها
    # خلافاً — فيُبطَل مفتاحُ الشركة قبل تحليلها.
    from app.services import cache as _c
    analyses: dict[str, dict] = {}
    for r in rows:
        sym = str(r.get("symbol"))
        try:
            # المفتاحُ يحمل نسخةَ القواعد — يُقرأ منها لا يُخمَّن.
            from app.services.governance_rules import rules_version as _rv
            _c.set(f"analysis:{sym}.SR:{_rv()}", None, 0)
            a = await analyze_company(f"{sym}.SR", r.get("name") or sym)
        except Exception as e:                                    # noqa: BLE001
            print(f"  ‏{sym}: تعذّر التحليل — {type(e).__name__}")
            continue
        if a:
            analyses[sym] = a
    rows = await refresh_derived(rows)

    diffs: dict[str, list[str]] = {}
    absent: dict[str, int] = {}
    done = 0
    for r in rows:
        sym = str(r.get("symbol"))
        a = analyses.get(sym)
        if not a:
            continue
        done += 1
        f = a.get("fundamentals") or {}
        page = {
            "price": _num((a.get("price") or {}).get("price")
                          if isinstance(a.get("price"), dict) else a.get("price")),
            "change_pct": _num((a.get("price") or {}).get("change_pct")
                               if isinstance(a.get("price"), dict) else a.get("change_pct")),
            "dividend_yield": _num(f.get("dividend_yield")),
            "finance_score": _num((a.get("financial") or {}).get("score")),
            "pe_ratio": _num(f.get("pe_ratio")),
            "price_to_book": _num(f.get("price_to_book")),
            "fair_value": _num(f.get("target_mean_price")),
            "high_52w": _num(f.get("week52_high")),
            "low_52w": _num(f.get("week52_low")),
            "rel_value": _num(a.get("rel_value")),
        }
        for col, tol in TOL.items():
            row_v, page_v = _num(r.get(col)), page.get(col)
            if row_v is None and page_v is None:
                continue
            if row_v is None or page_v is None:
                absent[col] = absent.get(col, 0) + 1
                diffs.setdefault(col, []).append(
                    f"{sym}: الفرز {row_v} · الصفحة {page_v}")
                continue
            if abs(row_v - page_v) > tol:
                diffs.setdefault(col, []).append(
                    f"{sym}: الفرز {row_v} · الصفحة {page_v}")
        # ══ الحكمُ الشرعيّ خارج نطاق هذه المقارنة ══ (صُحّح بعد أوّل تشغيل)
        # قال المسبارُ «‏37 خلافاً» وكلُّها «الصفحة None» — وليس ذاك عطباً
        # في التطبيق بل في المسبار: `analyze_company` لا يُخرج حكماً
        # شرعياً أصلاً (مصدرُه `maqasid` ويُعرض بمسارٍ آخر). ومقارنةُ حقلٍ
        # لا وجودَ له تُنتج ضجيجاً يُخفي الأعطابَ الحقيقية.
        if a.get("sharia_status") and (r.get("sharia") or None) != a["sharia_status"]:
            diffs.setdefault("sharia", []).append(
                f"{sym}: الفرز {r.get('sharia')} · الصفحة {a['sharia_status']}")

    if not done:
        print("… لم يكتمل تحليلُ أيّ شركة — لا يُقاس التطابق، ولا يُعدّ نجاحاً.")
        return 0

    print(f"قِيست {done} شركةً.\n")
    if not diffs:
        print("لا خلافَ في أيّ عمود ✔")
        return 0
    for col, items in sorted(diffs.items(), key=lambda kv: -len(kv[1])):
        print(f"✘ «{col}» — {len(items)} خلافاً"
              + (f" (منها {absent[col]} غيابٌ في أحد الطرفين)" if col in absent else ""))
        for line in items[:6]:
            print(f"    {line}")
    print("\nالخلافُ في عمودٍ مشتقٍّ من السعر يعني أن الإنعاشَ لم يشمله؛"
          "\nوالخلافُ في عمودٍ مخزَّنٍ يعني مصدرَين لا مصدراً واحداً.")
    return 1


raise SystemExit(asyncio.run(main()))
