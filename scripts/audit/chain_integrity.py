#!/usr/bin/env python3
"""سلسلةُ المعلومة من مصدرها إلى الشاشة — حلقةً حلقةً (D402).

    docker exec sp_backend python /app/scripts/audit/chain_integrity.py
    python3 scripts/audit/chain_integrity.py        # ما لا يحتاج شبكةً

سأل المالك وهو بعيدٌ عن الخادم: «هل تستطيع إكمالَ المشروع بالتوجيه
والتأكّدِ من ضمان البنية المعلوماتية بدون قصور؟». والضمانُ لا يكون
بكلمة: يكون بفحصٍ يمشي على **كلّ حلقةٍ** في الطريق من المُصدِر إلى
عين المستثمر، ويقف عند أوّل حلقةٍ مكسورةٍ ويسمّيها.

## الحلقاتُ العشر — وكلٌّ تُقاس لا تُدَّعى

   ١· الدليلُ الرسميّ: 273 شركةً · 22 قطاعاً · صفرُ «نمو»
   ٢· اللقطةُ الحيّة: رموزٌ · سعرٌ · قطاعٌ رسميٌّ لكلّ رمز
   ٣· الصنفُ يُقرأ من القطاع الرسميّ ويعود للدليل احتياطاً
   ٤· لكلّ صنفٍ خريطةُ تقييمٍ في المواصفة — لا صنفَ بلا خريطة
   ٥· القوائمُ المحفوظة: تغطيةٌ وعمرٌ لكلّ بندٍ مطلوب
   ٦· الإكمالُ: كلُّ حقلٍ يحمل مصدرَه ولا يُستبدَل منشورٌ بمشتقّ
   ٧· محرّكُ الجودة: درجةٌ لكلّ ورقةٍ لها قوائم
   ٨· محرّكُ السعر العادل: قيمةٌ أو سببُ امتناعٍ معلَن — لا صمت
   ٩· المخزَنُ الواحد: ما يقرؤه الفرزُ هو ما حسبه المحرّك
  ١٠· الشاشةُ: كلُّ رقمٍ يحمل عمرَه ومصدرَه باسمه

وما لا يُقاس في بيئةٍ (لا شبكةَ · لا واجهة) يُعلَن «لم يُقَس» ولا
يُحسَب نجاحاً ولا إخفاقاً — فنقصُ البيئة ليس عطباً في المنتَج (D375).
"""
from __future__ import annotations

import asyncio
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

fail = 0
skipped = 0


def ok(label: str, detail: str = "") -> None:
    print(f"✔ {label}" + (f" — {detail}" if detail else ""))


def bad(label: str, detail: str = "") -> None:
    global fail
    fail = 1
    print(f"✘ {label}" + (f" — {detail}" if detail else ""))


def skip(label: str, why: str) -> None:
    global skipped
    skipped += 1
    print(f"⚠ {label} — لم يُقَس: {why}")


def _find(*rel: str) -> pathlib.Path | None:
    for base in (ROOT, pathlib.Path("/app"), pathlib.Path.cwd()):
        for r in rel:
            c = base / r
            if c.exists():
                return c
    return None


async def main() -> int:
    print("═══ سلسلةُ المعلومة — حلقةً حلقةً ═══\n")

    # ── ١ · الدليلُ الرسميّ ───────────────────────────────────────────
    try:
        from app.data.market_universe import MARKET_UNIVERSE
        from app.data.universe import main_market
        mm = main_market(MARKET_UNIVERSE)
        secs = {(m or {}).get("sector") for m in mm.values()} - {None}
        nomu = [s for s in mm if str(s).startswith("9")]
        (ok if (len(mm) >= 270 and len(secs) >= 20 and not nomu) else bad)(
            "١ الدليلُ الرسميّ",
            f"{len(mm)} شركة · {len(secs)} قطاعاً · نمو={len(nomu)}")
    except ModuleNotFoundError as e:
        skip("١ الدليلُ الرسميّ", f"حزمةٌ غيرُ منصَّبة: {e.name}")
        print("\n(تُشغَّل بقيّةُ الحلقات داخل حاوية الخادم)")
        return 0

    # ── ٢ · اللقطةُ الحيّة ────────────────────────────────────────────
    from app.services import tadawul_market as tm
    rows, live, at = tm.usable_rows()
    if not rows:
        try:
            await tm.refresh()
            rows, live, at = tm.usable_rows()
        except Exception as e:                                    # noqa: BLE001
            skip("٢ اللقطةُ الحيّة", f"{type(e).__name__}")
            rows = {}
    if rows:
        main_rows = {s: r for s, r in rows.items() if not s.startswith("9")}
        with_sec = sum(1 for r in main_rows.values() if (r or {}).get("sector_en"))
        with_px = sum(1 for r in main_rows.values() if (r or {}).get("price"))
        (ok if (with_sec == len(main_rows) and with_px >= len(main_rows) - 5)
         else bad)(
            "٢ اللقطةُ الحيّة",
            f"رئيسيّ={len(main_rows)} · له قطاعٌ={with_sec}"
            f" · له سعرٌ={with_px} · حيّة={live} · {at}")
    else:
        skip("٢ اللقطةُ الحيّة", "لا شبكةَ في هذه البيئة")

    # ── ٣ · الصنفُ من القطاع الرسميّ ──────────────────────────────────
    from app.services.statement_merge import archetype_of, official_sector
    _probe = [s for s in (rows or {}) if not s.startswith("9")][:60]
    # ══ ونجاحٌ على عيّنةٍ فارغةٍ ليس نجاحاً ══ (D402)
    # مرّت حلقاتُ 3 و4 و5 خضراءَ على «0/0» في بيئةٍ بلا لقطة — وذاك
    # ادّعاءُ سلامةٍ على لا شيء. فما لا عيّنةَ له يُعلَن «لم يُقَس».
    if not _probe:
        skip("٣ الصنفُ لكلّ ورقة", "لا عيّنةَ — اللقطةُ فارغة")
        skip("٤ خريطةُ التقييم", "لا عيّنةَ — اللقطةُ فارغة")
        skip("٥ القوائمُ المحفوظة", "لا عيّنةَ — اللقطةُ فارغة")
    no_arch = [s for s in _probe if not archetype_of(s)]
    from_off = sum(1 for s in _probe if official_sector(s))
    if _probe:
        (ok if not no_arch else bad)(
            "٣ الصنفُ لكلّ ورقةٍ في العيّنة",
            f"عيّنةٌ={len(_probe)} · بلا صنف={len(no_arch)}"
            f" · قطاعُها رسميٌّ={from_off}")

    # ── ٤ · لكلّ صنفٍ خريطةُ تقييم ────────────────────────────────────
    from app.data.archetype_spec import VALUATION
    used = {archetype_of(s) for s in _probe} - {None}
    nomap = [a for a in used if not (VALUATION.get(a) or {}).get("weights")
             and a != "fund"]
    if _probe:
        (ok if not nomap else bad)(
            "٤ خريطةُ تقييمٍ لكلّ صنفٍ مستعمَل",
            f"أصنافٌ={len(used)}"
            + (f" · بلا خريطة: {nomap}" if nomap else ""))

    # ── ٥ · القوائمُ المحفوظة ─────────────────────────────────────────
    from app.services import statement_merge as SM
    from app.services import tadawul_xbrl as X
    have, ages = 0, []
    for s in _probe:
        per = (X.for_symbol(s, "quarterly") or []) + (X.for_symbol(s, "annual") or [])
        if per:
            have += 1
            ds = [str(p.get("as_of") or "") for p in per if p.get("as_of")]
            if ds:
                from datetime import date
                try:
                    ages.append((date.today()
                                 - date.fromisoformat(max(ds)[:10])).days)
                except ValueError:
                    pass
    _med = sorted(ages)[len(ages) // 2] if ages else None
    if _probe:
        (ok if have >= len(_probe) * 0.85 else bad)(
            "٥ القوائمُ المحفوظة",
            f"لها قوائمُ={have}/{len(_probe)}"
            + (f" · وسيطُ العمر={_med} يوماً" if _med is not None else ""))

    # ── ٦ · الإكمالُ يحمل مصادرَه ─────────────────────────────────────
    _p = [{"as_of": "2025-12-31", "year": 2025, "total_assets": 1e9,
           "total_liabilities": 6e8, "net_income": 5e7, "eps": 0.5}]
    _done = SM.complete("2222", [dict(x) for x in _p])
    _src = (_done[0] if _done else {}).get("field_sources") or {}
    (ok if (_done and _done[0].get("equity") and _src) else bad)(
        "٦ الإكمالُ يشتقّ ويُسمّي مصدرَه",
        f"حقوقٌ={(_done[0] if _done else {}).get('equity')}"
        f" · مصادرٌ={len(_src)}")

    # ── ٧ و ٨ · المحرّكان على عيّنةٍ حيّة ──────────────────────────────
    from app.services.analysis import analyze_company
    sample = _probe[:6]
    sc = fv = why = 0
    for s in sample:
        try:
            a = await analyze_company(f"{s}.SR", allow_supplement=False) or {}
        except Exception:                                         # noqa: BLE001
            continue
        if ((a.get("financial") or {}).get("score")) is not None:
            sc += 1
        if a.get("fair_value") is not None:
            fv += 1
        elif (a.get("fair_value_detail") or {}).get("unavailable_reason"):
            why += 1
    if sample:
        (ok if sc == len(sample) else bad)(
            "٧ محرّكُ الجودة", f"درجةٌ={sc}/{len(sample)}")
        (ok if (fv + why) == len(sample) else bad)(
            "٨ محرّكُ السعر العادل — قيمةٌ أو سببٌ معلَن",
            f"قيمةٌ={fv} · امتناعٌ مُعلَّلٌ={why} · صامتٌ={len(sample) - fv - why}")
    else:
        skip("٧ و٨ المحرّكان", "لا عيّنةَ — اللقطةُ فارغة")

    # ── ٩ · المخزَنُ الواحد ───────────────────────────────────────────
    try:
        from app.services.content_engine import fund_store_load
        st = fund_store_load()
        n_fv = sum(1 for v in st.values() if v.get("fair_value") is not None)
        n_sc = sum(1 for v in st.values() if v.get("finance_score") is not None)
        n_un = sum(1 for v in st.values() if v.get("fair_value_unavailable"))
        (ok if (n_fv + n_un) >= 200 else bad)(
            "٩ المخزَنُ الذي يقرؤه الفرز",
            f"رموزٌ={len(st)} · سعرٌ عادل={n_fv} · درجة={n_sc}"
            f" · امتناعٌ معلَّل={n_un}"
            + ("  ← شغّل مسحةَ التقييم" if (n_fv + n_un) < 200 else ""))
    except Exception as e:                                        # noqa: BLE001
        skip("٩ المخزَن", f"{type(e).__name__}")

    # ── ١٠ · الشاشةُ تحمل العمرَ والمصدر ──────────────────────────────
    _mk = _find("frontend/src/pages/MarketPage.tsx")
    _pn = _find("frontend/src/components/analysis/AnalysisPanel.tsx")
    if not (_mk and _pn):
        skip("١٠ الشاشة", "لا مجلَّدَ واجهةٍ في هذه البيئة")
    else:
        t1, t2 = _mk.read_text("utf-8"), _pn.read_text("utf-8")
        need = [("عمرُ الدرجة في السوق", "r.stmt_asof" in t1),
                ("عمرُ الأرقام في التحليل", 'prov["تاريخ الأرقام"]' in t2),
                ("اسمُ السعر العادل لصاحبه", "analyst_target" in t2)]
        badl = [n for n, c in need if not c]
        (ok if not badl else bad)("١٠ الشاشةُ تحمل العمرَ والاسمَ",
                                  " · ".join(badl) or "الثلاثةُ حاضرة")

    print("\n" + ("✘ في السلسلة حلقةٌ مكسورة — تُصلَح قبل التسليم"
                  if fail else
                  "✔ السلسلةُ متّصلةٌ من المُصدِر إلى الشاشة")
          + (f" · حلقاتٌ لم تُقَس في هذه البيئة: {skipped}" if skipped else ""))
    return fail


raise SystemExit(asyncio.run(main()))
