"""مخرَجُ شركةٍ كاملاً — كلُّ ما تراه الشاشة وما وراءه، في نصٍّ واحد.

## لماذا

قال المالك: «أعطني أمراً يجمع الدرجات والقيمة العادلة وغيرها من السيرفر
ليفحصها مراجعٌ خارجيّ فحصاً شاملاً». والمراجعُ لا يرى شاشتَنا ولا
شيفرتَنا — فيلزمه **المخرَج بمدخلاته**: الرقمُ وما بُني عليه، لا الرقمُ
وحده. فبلا المدخلات يبقى نقدُه رأياً، ومعها يصير تشخيصاً.

ويُخرج لكل رمز:
  · الهويّة والقطاع الخام والمحلول والنمط — من المحرّكين معاً، فإن
    اختلفا ظهر ذلك (وهو عطبٌ رآه المالك: ريتٌ يُقاس بركنٍ سلعيّ)
  · درجةُ الحوكمة القديمة بأركانها الأربعة وما اشتعل من قواعد
  · درجةُ المواصفة الجديدة بمؤشّراتها وأوزانها ودرجةِ كلٍّ منها
  · مجلسَ الخبراء كاملاً
  · القيمةَ العادلة بكلّ مسارٍ ومدخلاته ووزنه، وسعرَ الدخول والثقة
  · القرارَ وسببَه، والسماتِ الخام التي بُني عليها كلُّ ذلك

## التشغيل

    docker exec sp_backend python /app/scripts/audit/dump.py 4340
    docker exec sp_backend python /app/scripts/audit/dump.py 4340 1120 2222
    docker exec sp_backend python /app/scripts/audit/dump.py --portfolio

والمخرَجُ نصٌّ عاديّ يُنسخ كما هو.
"""

from __future__ import annotations

import asyncio
import sys

sys.path.insert(0, "/app")
sys.path.insert(0, ".")

LINE = "─" * 66


def _p(label, value, unit=""):
    if value is None:
        return
    if isinstance(value, float):
        value = f"{value:,.2f}"
    print(f"  {label:38} {value}{unit}")


async def dump(symbols: list[str]) -> int:
    from app.services.analysis import analyze_company
    from app.core.database import AsyncSessionLocal
    from app.data.saudi_directory import name_of, sector_of
    from app.services.four_scores import resolve_sector, build_company_features
    from app.services.governance_rules import load_rules
    from app.services.market_data import market_service
    from app.services import spec_score

    rules_arch = load_rules().get("sector_archetype", {})

    async with AsyncSessionLocal() as db:
        for raw in symbols:
            sym = raw if raw.endswith(".SR") else f"{raw}.SR"
            base = raw.replace(".SR", "")
            print("\n" + "═" * 66)
            print(f"  {base} — {name_of(base) or ''}")
            print("═" * 66)

            a = await analyze_company(sym, db=db)
            if not a:
                print("  لم تصل بيانات.")
                continue

            # ── الهويّة والنمط: مصدرُ أعطابٍ متكرّر ──
            raw_sector = (a.get("fundamentals") or {}).get("sector")
            dir_sector = sector_of(base)
            resolved = resolve_sector(raw_sector, sym)
            print("\n" + LINE)
            print("  الهويّة والنمط")
            print(LINE)
            _p("قطاعُ المصدر (خام)", raw_sector)
            _p("قطاعُ الدليل", dir_sector)
            _p("القطاعُ المحلول", resolved)
            _p("النمطُ في القواعد", rules_arch.get(resolved) or rules_arch.get(dir_sector))
            spec = a.get("spec") or (a.get("financial") or {}).get("spec") or {}
            _p("النمطُ في المواصفة", spec.get("archetype"))
            _p("السعر", a.get("price"))
            _p("التغيّر اليوميّ", a.get("change_pct"), "%")

            # ── درجةُ الحوكمة القديمة ──
            fin = a.get("financial") or {}
            sc = a.get("scores") or {}
            print("\n" + LINE)
            print("  المحرّك القديم")
            print(LINE)
            _p("الدرجة المعروضة", fin.get("score"))
            _p("قابلٌ للتقييم", a.get("evaluable"))
            for k, ar in (("quality", "الجودة"), ("safety", "الأمان"),
                          ("valuation", "التقييم"), ("timing", "التوقيت")):
                row = sc.get(k) or {}
                cov = row.get("coverage")
                _p(f"  {ar}", row.get("score"),
                   f"   (تغطية {cov})" if cov is not None else "")
                for h in (row.get("hits") or [])[:8]:
                    kind = h.get("kind")
                    mark = "＋" if kind == "bonus" else "－"
                    print(f"        {mark} {h.get('points')} · {h.get('message')}")

            # ── درجةُ المواصفة ──
            print("\n" + LINE)
            print("  محرّك المواصفة (اثنا عشر نمطاً)")
            print(LINE)
            if not spec:
                print("  لم يُحسب.")
            else:
                _p("الدرجة", spec.get("score"))
                _p("التغطية", spec.get("coverage"))
                _p("يمنع الشراء", spec.get("blocks_buy"))
                if spec.get("abstain_reason"):
                    _p("الامتناع", spec["abstain_reason"])
                for m in spec.get("metrics") or []:
                    print(f"     {m['tone'][:1]}  {m['label']:34} "
                          f"{m['value']:>10,.2f}  →  {m['score']:>3}/100  "
                          f"(وزن {m['weight']})")
                if spec.get("missing"):
                    print(f"     غاب: {' · '.join(spec['missing'])}")

            # ── مجلس الخبراء ──
            print("\n" + LINE)
            print("  ميزان الخبراء")
            print(LINE)
            for e in (fin.get("expert_panel") or a.get("expert_panel") or []):
                role = "  [تفسير]" if e.get("role") == "driver" else ""
                print(f"     {str(e.get('tone'))[:1]}  {e.get('expert','')} · "
                      f"{e.get('metric','')} = {e.get('reading','')} — "
                      f"{e.get('verdict','')}{role}")

            # ── القيمة العادلة ──
            fv = a.get("fair_value_detail") or {}
            print("\n" + LINE)
            print("  القيمة العادلة")
            print(LINE)
            _p("القيمة", a.get("fair_value"))
            _p("الصعود", a.get("fair_value_upside_pct"), "%")
            _p("المدى", f"{fv.get('low')} – {fv.get('high')}")
            _p("الثقة", fv.get("confidence"))
            _p("هامش الأمان", fv.get("margin_of_safety_pct"), "%")
            _p("سعر الدخول", fv.get("entry_price"))
            _p("حكم الدخول", fv.get("entry_verdict"))
            _p("مساراتٌ مُسقَطة بحدّ العقل", fv.get("dropped_paths"))
            _p("تعذّر", fv.get("unavailable_reason"))
            _p("استُبعد", fv.get("excluded"))
            for m in fv.get("methods") or []:
                print(f"     · {m.get('name','')} = {m.get('value')}")
                print(f"          {m.get('inputs','')}")
            if fv.get("weighting"):
                _p("الأوزان", str(fv["weighting"]))
            for k, v in (fv.get("assumptions") or {}).items():
                _p(f"  {k}", v)
            _p("تاريخ الأساسيات", fv.get("asof"))
            _p("عمر الأرقام (يوماً)", fv.get("age_days"))

            # ── القرار ──
            dec = a.get("decision") or {}
            print("\n" + LINE)
            print("  القرار")
            print(LINE)
            _p("الحكم", dec.get("label"))
            _p("السبب", dec.get("reason"))

            # ── السماتُ الخام ──
            try:
                stmt = await market_service.get_financials(sym)
                periods = (stmt or {}).get("periods") or []
                feats, info, _q = build_company_features(
                    periods, info=a.get("fundamentals"), sector=resolved)
                print("\n" + LINE)
                print(f"  السماتُ الخام ({len(periods)} فترة مالية)")
                print(LINE)
                for k in sorted(feats):
                    if k.startswith("_"):
                        continue
                    v = feats[k]
                    v = v.get("value") if isinstance(v, dict) else v
                    if isinstance(v, (int, float)):
                        print(f"     {k:34} {v:,.3f}")
            except Exception as e:                                # noqa: BLE001
                print(f"  تعذّر استخراج السمات: {e}")
    return 0


if __name__ == "__main__":
    args = [x for x in sys.argv[1:] if not x.startswith("--")]
    if "--portfolio" in sys.argv:
        async def _pf():
            from sqlalchemy import select
            from app.core.database import AsyncSessionLocal
            from app.models.portfolio import Company, Holding
            async with AsyncSessionLocal() as db:
                rows = (await db.execute(
                    select(Company.symbol).join(
                        Holding, Holding.company_id == Company.id).distinct())).all()
            return [r[0] for r in rows]
        args = asyncio.run(_pf())
    if not args:
        print("الاستعمال: dump.py 4340 [1120 …]  |  dump.py --portfolio")
        sys.exit(2)
    sys.exit(asyncio.run(dump(args)))
