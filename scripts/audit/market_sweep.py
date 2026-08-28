"""مراجعةُ السوق شركةً شركة — أن أقف موقف المالك لا أن أنتظره.

## لماذا وُجد هذا الملفّ

قال المالك: «راجع السوق شركة تلو الشركة، وكن أنت مكاني، ولا تنتظر مني أن
أكتشف هذه الأخطاء فهذا واجبك». وكان محقّاً: كلُّ عطبٍ جوهريّ في المحرّك
اكتُشف حين عرض صورةَ شركةٍ بعينها — تناقضُ المحرّكين (‏D043) في «الراجحي
ريت»، ووسيطُ النماذج المختلفة الأفق (‏D046) في «أماك»، ورأيُ المحللين في
حساب القيمة (‏D047) في «سلوشنز». ثلاثُ شركاتٍ نظر فيها، وثلاثةُ أعطاب.
فكم بقي فيما لم ينظر فيه؟

والفحوصُ الساكنة (‏static.py) تحرس **الشيفرة** ولا ترى **المخرَج**: تمنع
عودةَ عطبٍ عُرف، ولا تكشف عطباً لم يُعرف بعد. وهذا المسحُ يقرأ ما يراه
المالك على الشاشة لكل شركةٍ في السوق، ويسأل عنه ما كان يسأله هو.

## ما الذي يُعدّ عطباً هنا

ليس «رقماً لا يعجبني» — بل **تناقضاً داخلياً** أو **ادّعاءَ دقّةٍ لا
تملكها الأداة**. وكلُّ فحصٍ أدناه وُلد من عطبٍ حقيقيّ وقع فعلاً، أو من
مبدأٍ مكتوبٍ في الميثاق يُخالفه المخرَج.

## التشغيل

    docker exec sp_backend python /app/scripts/audit/market_sweep.py            # المحفظة
    docker exec sp_backend python /app/scripts/audit/market_sweep.py --market   # السوق كلّه
    docker exec sp_backend python /app/scripts/audit/market_sweep.py --market --limit 60

ويُخرج تقريراً مجمَّعاً: كم شركةً فُحصت، وكم بلاغاً من كل صنف، وأمثلةً
مسمّاة. والصمتُ نتيجةٌ صالحة: لا بلاغَ يعني أن المسح لم يجد ما يشكو منه.
"""

from __future__ import annotations

import asyncio
import sys
from collections import defaultdict

sys.path.insert(0, "/app")
sys.path.insert(0, ".")


# ── عتباتُ الحكم، مُعلَنةً ────────────────────────────────────────────────
# التشتّت: أعلى تقديرٍ ÷ أدناه.
#
# وكان الحدّ ‎2.0× فأخرج المسحُ مئةً وثمانين بلاغاً — وهو رقمٌ يخفي أكثرَ
# ممّا يكشف. والسبب أن الفحص كان يقيس بعتبةٍ **غير عتبة المحرّك**: المحرّك
# يمتنع عن النقطة عند ‎3.0× ويعرض المدى (‏D052)، فما بين الاثنين ليس
# مخالفةً لسياسةٍ بل اتّساعُ مدًى مُعلَنٌ في المخرَج أصلاً.
# فالبلاغُ الآن ما **يناقض السياسة**: تشتّتٌ ≥3× ونقطةٌ معروضة رغمه. وما
# بين ‎2× و3× يُعدّ ويُذكر خبراً لا بلاغاً — لأن العدد نفسه معلومةٌ تستحقّ
# أن تُرى، لكنّه ليس عطباً يُلاحق.
SPREAD_LIMIT = 3.0
WIDE_BAND = 2.0
# فجوةُ الحكم: نسبةُ الفرق بين السعر والقيمة التي تجعل «شراء» تناقضاً.
# شُدّت من ‎−15٪ إلى الصفر بعد سقفِ القيمة العادلة: لم يعد لـ«شراء» فوق
# القيمة التي نحسبها عذرٌ ولو بهامشٍ يسير.
OVERVALUED_PCT = 0.0


def _pct(a, b):
    return (a / b - 1) * 100 if (a and b) else None


class Findings:
    def __init__(self) -> None:
        self.by_kind: dict[str, list[str]] = defaultdict(list)
        self.wide: list[tuple[str, float]] = []      # خبرٌ لا بلاغ
        self.abstained: list[tuple[str, float]] = []  # امتناعٌ صحيح

    def add(self, kind: str, symbol: str, detail: str) -> None:
        self.by_kind[kind].append(f"{symbol} — {detail}")

    def note_wide(self, symbol: str, spread: float) -> None:
        self.wide.append((symbol, spread))

    def note_abstain(self, symbol: str, spread: float) -> None:
        self.abstained.append((symbol, spread))


def inspect(sym: str, name: str, a: dict, f: Findings) -> None:
    """يفحص مخرَج شركةٍ واحدة كما يراه المالك على الشاشة."""
    fv = (a or {}).get("fair_value_detail") or {}
    price = (a or {}).get("price")
    value = (a or {}).get("fair_value")
    methods = fv.get("methods") or []
    panel = (a or {}).get("expert_panel") or []
    dec = ((a or {}).get("decision") or {}).get("label")
    score = ((a or {}).get("financial") or {}).get("score")
    evaluable = (a or {}).get("evaluable")
    std = (a or {}).get("governance_standard") or {}

    # ١) رأيٌ في حساب القيمة (‏D047) — لا يعود بعد إخراجه
    if any("المحلل" in (m.get("name") or "") for m in methods):
        f.add("رأيٌ في حساب القيمة", sym, "أهدافُ المحللين مسارٌ في التقدير")

    # ٢) تشتّتٌ يُبطل النقطة (‏D046) — القيمةُ تُعرض رقماً واحداً واثقاً
    # المسارُ الذي استبعده المحرّكُ من حساب النقطة (مضاعفُ القطاع الشاذّ)
    # لا يُحسب في التشتّت هنا أيضاً — وإلّا شكا الفحصُ من سلوكٍ مقصودٍ
    # مُعلَن، وأغرقَ البلاغاتِ الصادقة بضجيجه (وهو عينُ ما وقع في D048).
    _excl = "مضاعف الربحية العادل" if fv.get("excluded") else None
    vals = [m.get("value") for m in methods
            if isinstance(m.get("value"), (int, float)) and m.get("name") != _excl]
    if len(vals) >= 2 and min(vals) > 0:
        spread = max(vals) / min(vals)
        if spread >= SPREAD_LIMIT:
            if value is not None:
                f.add("تشتّتٌ ونقطةٌ معاً", sym,
                      f"{spread:.1f}× ({min(vals):.2f}–{max(vals):.2f}) والقيمة "
                      f"{value} معروضةٌ رغم سياسة الامتناع")
            else:
                f.note_abstain(sym, spread)      # امتناعٌ صحيح
        elif spread >= WIDE_BAND:
            f.note_wide(sym, spread)

    # ٣) القرارُ يناقض السعر — «شراء» وسهمٌ فوق قيمته بوضوح
    up = _pct(value, price)
    if dec in ("شراء", "شراء قوي") and up is not None and up <= OVERVALUED_PCT:
        f.add("قرارٌ يناقض القيمة", sym,
              f"«{dec}» والسعرُ أعلى من القيمة بـ{abs(up):.0f}%")

    # ٤) الدرجةُ تناقض مجلسها — درجةٌ عالية وأكثرُ الخبراء حمر
    # صفوفُ «ما خفض الدرجة» تفسيرٌ لا رأي — تُستثنى من عدّ المجلس، ووجودُها
    # يعني أن الدرجة المنخفضة **مُفسَّرة** فلا تُعدّ مناقِضة.
    judged = [e for e in panel
              if (e.get("tone") or "na") != "na" and e.get("role") != "driver"]
    drivers = [e for e in panel if e.get("role") == "driver"]
    reds = [e for e in judged if e.get("tone") == "red"]
    if score is not None and judged:
        if score >= 75 and len(reds) > len(judged) / 2:
            f.add("درجةٌ تناقض مجلسها", sym,
                  f"درجة {score} وأكثرُ الخبراء سلبيّ ({len(reds)}/{len(judged)})")
        if score <= 45 and not reds and not drivers and len(judged) >= 3:
            f.add("درجةٌ تناقض مجلسها", sym,
                  f"درجة {score} ولا خبيرَ سلبيّ ({len(judged)} حكموا)")

    # ٥) درجةٌ على شاهدٍ واحد (‏D040) — رقمٌ كامل من مؤشّرٍ يتيم
    if score is not None and 0 < len(judged) < 2 and not drivers:
        f.add("درجةٌ على شاهدٍ واحد", sym, f"درجة {score} وخبيرٌ واحد حكم")

    # ٦) حكمُ الدخول يناقض حسابه
    ep, verdict = fv.get("entry_price"), fv.get("entry_verdict")
    if ep is not None and price and verdict:
        if price <= ep and verdict != "دون سعر الدخول":
            f.add("حكمُ الدخول يناقض حسابه", sym,
                  f"السعر {price} ≤ الدخول {ep} والحكم «{verdict}»")
        if price > (value or 0) and verdict == "دون سعر الدخول":
            f.add("حكمُ الدخول يناقض حسابه", sym,
                  f"السعر فوق القيمة والحكم «{verdict}»")

    # ٧) إطارٌ يُعلَن ولا يُقاس (‏D032) — نمطٌ له أركانٌ ولا ركن
    arch = std.get("archetype")
    if arch in ("bank", "insurance", "financial", "reit") and not (std.get("metrics") or []):
        f.add("إطارٌ بلا أركان", sym, f"نمط «{arch}» بلا ركنٍ مقيس")

    # ٨) خصمُ تدفّقٍ حيث لا يصحّ (‏D039)
    if arch in ("bank", "insurance", "financial", "reit") and fv.get("has_dcf"):
        f.add("خصمٌ حيث لا يصحّ", sym, f"نموذجُ خصمٍ في نمط «{arch}»")

    # ٩) قيمةٌ بلا سعرِ دخول — التقديرُ لا يقول متى يُدخَل
    if value is not None and fv.get("entry_price") is None:
        f.add("قيمةٌ بلا سعرِ دخول", sym, "قيمةٌ معروضة بلا هامش أمان")

    # ١٠) امتناعٌ مع درجة — البوّابة تمتنع والرقم يُعرض
    if evaluable is False and score is not None:
        f.add("امتناعٌ مع درجة", sym, f"امتنع المجلس والدرجة {score} معروضة")

    # ١٢) درجتان في مخرَجٍ واحد — شارةُ الترويسة وبطاقةُ التقييم
    gscore = ((a or {}).get("governance") or {}).get("score")
    if gscore is not None and score is not None and round(gscore) != round(score):
        f.add("درجتان لشركةٍ واحدة", sym,
              f"الشارة {round(gscore)} والبطاقة {round(score)}")

    # ١١) وسمُ الشريط يناقض حكمَ الدخول — «مبخس» و«بلا هامش أمان» معاً
    # (رآه المالك في «الراجحي ريت»: الشريطُ يقول اشترِ والحكمُ يقول لا).
    # (‏D048 صحّح الشريط فصار يقرأ ما يقرأه الحكم: سعرُ الدخول والقيمة، لا
    # نسبةَ الصعود وحدها. وكان هذا الفحصُ يحفظ منطقَ الشريط القديم فأخرج
    # خمسةً وثلاثين بلاغاً كاذباً على مخرَجٍ صحيح — فحصٌ يحرس عطباً عولج
    # أسوأ من لا فحص، لأنه يُغرق البلاغات الصادقة في ضجيجه.)
    if ep is not None and price and value:
        bargain = price <= ep       # وسمُ «تقييم مبخس» بعد D048
        if bargain and verdict and verdict != "دون سعر الدخول":
            f.add("وسمٌ يناقض حكمه", sym,
                  f"الشريطُ «مبخس» (السعر {price} ≤ الدخول {ep}) والحكم «{verdict}»")


async def sweep(market: bool, limit: int) -> int:
    from app.services.analysis import analyze_company
    from app.core.database import AsyncSessionLocal

    if market:
        from app.data.market_universe import MARKET_UNIVERSE
        from app.api.v1.endpoints.holdings import yahoo_symbol
        pairs = [(yahoo_symbol(s), m.get("name_ar") or s)
                 for s, m in list(MARKET_UNIVERSE.items())[:limit]]
    else:
        from sqlalchemy import select
        from app.models.portfolio import Company, Holding
        async with AsyncSessionLocal() as db:
            rows = (await db.execute(
                select(Company.symbol, Company.company_name)
                .join(Holding, Holding.company_id == Company.id).distinct())).all()
        pairs = [(s, n) for s, n in rows]

    # ══ المسحُ لا يأكل حصّةَ المالك ══
    # مسحةُ السوق تمرّ على ٣٩٧ شركة، ولكلٍّ سعرٌ وملخَّصٌ وتاريخ — فتتجاوز
    # حصّةَ ياهو اليومية (٥٠٠) وحدَها. وأثرُها لا يظهر في المسح بل في
    # التطبيق بعده: يفتح المالك رمزاً لم يُخزَّن فيقرأ «لا توجد بيانات»،
    # وهو حدُّ حصّتنا لا نقصٌ في الورقة. رآه على «صندوق البلاد التقني»
    # وهو مسعَّرٌ على ياهو في اللحظة نفسها.
    # فيُحجز للمالك احتياطيّ: يقف المسحُ حين يبقى أقلّ منه، ويقول كم فحص
    # وكم بقي — مراجعةٌ ناقصةٌ معلومةُ الحدّ خيرٌ من تطبيقٍ أعمى بقيّة اليوم.
    from app.services.usage_tracker import usage as _usage, limit_for as _limit
    RESERVE = 120
    f = Findings()
    checked = skipped = 0
    stopped_at = None
    # ما يسقط بـ429 يُعاد بعد مهلة — المصدرُ يحدّ النداء ولا ينفيه.
    # وكان يُعدّ «بلا بيانات» فيبقى خارج المراجعة بلا سبب حقيقيّ.
    retry: list[tuple[str, str]] = []
    async with AsyncSessionLocal() as db:
        for sym, name in list(pairs):
            u = _usage("yahoo")
            lim = u.get("daily_limit") or _limit("yahoo")
            if lim and lim - u.get("daily_used", 0) <= RESERVE:
                stopped_at = (checked, u.get("daily_used"), lim)
                break
            try:
                a = await analyze_company(sym, name, db=db,
                                          allow_supplement=not market)
            except Exception as e:                                # noqa: BLE001
                f.add("تعذّر الفحص", sym, str(e)[:70])
                continue
            if not a:
                retry.append((sym, name))
                continue
            checked += 1
            inspect(sym, name, a, f)

        if retry:
            print(f"‏{len(retry)} شركةً بلا بيانات — إعادةُ محاولةٍ بعد دقيقة…")
            await asyncio.sleep(60)
            for sym, name in retry:
                try:
                    a = await analyze_company(sym, name, db=db,
                                              allow_supplement=not market)
                except Exception:                                 # noqa: BLE001
                    a = None
                if not a:
                    skipped += 1
                    continue
                checked += 1
                inspect(sym, name, a, f)

    if stopped_at:
        done, used, lim = stopped_at
        print(f"\n⏸ وقف المسحُ عند {done} شركةً: الحصّةُ المتبقّية بلغت "
              f"الاحتياطيَّ المحجوز للتطبيق ({used}/{lim}، احتياطي {RESERVE}). "
              f"يُستأنف غداً أو برفع الحدّ في الإعدادات.")
    print("═" * 62)
    print(f"مراجعةُ {'السوق' if market else 'المحفظة'} — "
          f"{checked} شركةً فُحصت · {skipped} بلا بيانات")
    print("═" * 62)
    # ══ الخبرُ يُفصَّل ولا يُخلط ══
    # طُبع أوّلَ مرّة سطرٌ واحد يقول «بين 2× و3×» ثم يسرد 18.4× — لأن
    # الامتناعَ الصحيح (‏≥3× بلا نقطة) كان يقع في السلّة نفسها. وسطرٌ
    # يناقض مثالَه أسوأ من لا سطر: يُشكِّك في التقرير كلّه.
    if f.abstained:
        worst = sorted(f.abstained, key=lambda x: -x[1])[:3]
        print(f"\nامتناعٌ صحيح: {len(f.abstained)} شركةً تشتّتُها "
              f"≥{SPREAD_LIMIT:.0f}× فامتنعت القيمةُ وعُرض المدى — "
              "وأوسعُها: " + " · ".join(f"{s} {v:.1f}×" for s, v in worst))
    if f.wide:
        worst = sorted(f.wide, key=lambda x: -x[1])[:3]
        print(f"مدًى واسع: {len(f.wide)} شركةً بين {WIDE_BAND:.0f}× "
              f"و{SPREAD_LIMIT:.0f}× — نقطتُها معروضةٌ ومداها معها، "
              "وأوسعُها: " + " · ".join(f"{s} {v:.1f}×" for s, v in worst))
    if not f.by_kind:
        print("\n✔ لا بلاغ — لم يجد المسحُ تناقضاً في أيّ شركة.")
        return 0
    total = sum(len(v) for v in f.by_kind.values())
    print(f"\n{total} بلاغاً في {len(f.by_kind)} صنفاً:\n")
    for kind, items in sorted(f.by_kind.items(), key=lambda kv: -len(kv[1])):
        print(f"  ✖ {kind} — {len(items)}")
        for line in items[:5]:
            print(f"      {line}")
        if len(items) > 5:
            print(f"      … و{len(items) - 5} غيرها")
        print()
    return 1


if __name__ == "__main__":
    args = sys.argv[1:]
    market = "--market" in args
    limit = 400
    if "--limit" in args:
        limit = int(args[args.index("--limit") + 1])
    sys.exit(asyncio.run(sweep(market, limit)))
