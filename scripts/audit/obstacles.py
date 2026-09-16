#!/usr/bin/env python3
"""مسحُ العقبات كلِّها في تشغيلةٍ واحدة — مرتَّبةً ومسمَّاةً بأوراقها (D342).

    docker exec sp_backend python /app/scripts/audit/obstacles.py
    docker exec sp_backend python /app/scripts/audit/obstacles.py --n 120 --probe 12

قال المالك: «اعطني مسحاً لجميع العقبات التي تواجهك مرّةً واحدةً
لنختصر». فكانت أدواتُ القياس متفرّقةً (غربلةُ المدخلات · مساراتُ السعر
العادل · بنودُ الملفّ · طبقاتُ الصناديق)، وكلُّ واحدةٍ تُشغَّل بأمرٍ
وتُقرأ وحدَها — فهذا يجمعها في بابٍ واحدٍ يُخرج **جدولَ عقباتٍ
مرتَّباً**: كلُّ عقبةٍ وعددُ الأوراق التي تحجبها وأسماؤها والطبقةُ
المكمِّلةُ المرشَّحةُ لها.

## ثلاثةُ قيودٍ تمنع المسحَ أن يصير رأياً

  · **لا يُعدّ ما ليس في اللقطة**: أوراقٌ خارجَ لقطةِ السوق تُعَدّ
    «بلا ملفّات» وهي لم تُسأل أصلاً — فالنطاقُ يُقصَّ على اللقطة
    ويُعلَن ما استُبعد. (عطبٌ قِيس في تشغيلةٍ سابقةٍ عند المالك.)
  · **جنسُ العقبة يُفصَل**: نقصُ بابٍ أو خريطةٍ شيءٌ، وخطأُ تصنيفٍ
    عندنا شيءٌ آخر، وتضارُبُ مساراتٍ صادقٍ ثالثٌ — وخلطُها يُنتج
    «إصلاحاً» في غير موضعه.
  · **الطبقةُ المرشَّحةُ مرشَّحةٌ لا وعد**: تُكتَب بوصفها فرضيةً
    تُقاس، ولا تُسجَّل حلاًّ قبل أن يُقاس أثرُها.

ولا يكتب حرفاً في قاعدة البيانات: قراءةٌ وقياسٌ فقط.
"""
from __future__ import annotations

import asyncio
import sys
from collections import Counter

sys.path.insert(0, "/app")
sys.path.insert(0, "backend")

N = 60          # عيّنةُ السوق فوق أوراق المحفظة
PROBE = 8       # كم ورقةً بلا صفوفٍ محفوظةٍ تُسأل عن ملفّاتها فعلاً


def _arg(flag: str, default: int) -> int:
    if flag in sys.argv:
        i = sys.argv.index(flag)
        try:
            return int(sys.argv[i + 1])
        except (IndexError, ValueError):
            return default
    return default


ETF_SEC = "صناديق المؤشرات المتداولة"
REIT_SEC = "الصناديق العقارية المتداولة"

# الطبقةُ المكمِّلةُ المرشَّحةُ لكلّ عقبة — فرضيّاتٌ تُقاس لا وعود
CANDIDATE = {
    "تصنيف/ETF": "لا شريكَ لها: قيمتُها صافي أصولها وهو سعرُها تقريباً —"
                 " تُعرَّف ورقةً مؤشِّرةً ويُرفَع عنها محرّكُ الشركات",
    "تصنيف/ريت": "«تداول» من بابٍ آخر: ملفُّها الرسميُّ إن وُجد (أسماءٌ"
                 " تُنقَل بالحرف) وإلا بابُ الصناديق في نداءات صفحتها،"
                 " ومسارُ عائدِ التوزيع بدل خصمِ التدفّق الصناعيّ",
    "بلا ملفّاتٍ رسمية": "قائمةُ الإفصاحات لهذه الورقة — وإن لم تنشر"
                         " فلقطةُ السوق ومضاعفاتُها وحدَها، ويُعلَن الحدّ",
    "بنودٌ ناقصةٌ بعد الطبقات": "أسماءُ البنود تُنقَل بالحرف من مخرَج"
                                " `xbrl_labels.py` — أكثرُها اسمٌ لم"
                                " يُطابَق لا رقمٌ لم يُنشَر",
    "تضارُبُ المسارات": "خلافٌ قد يكون صادقاً: يُفتَح بـ`fv_paths.py`"
                        " فإن كان مدخلُ مسارٍ معطوباً أُصلِح، وإلا بقي"
                        " الامتناعُ صواباً ولا تُخفَّف العتبة",
    "وحدةٌ سُوّيت": "لا عقبة: مِرساةُ لقطةِ «تداول» عملت (‏D339)",
    "فرقُ عددٍ أُعلِن": "لا عقبة: المنشورُ باقٍ والفرقُ مسمّىً (‏D339)",
    "صندوقٌ غائبٌ عن لقطةِ السوق": "لقطتُنا تُقرأ من جدول مراقبة"
                                   " السوق الرئيسيّ — والصناديقُ لها"
                                   " جدولٌ آخرُ يُكتشَف من نداءات صفحتها",
    "امتناعٌ بلا سببٍ معلَن": "عطبٌ في المحرّك لا في البيانات: كلُّ"
                             " امتناعٍ يجب أن يحمل سببَه — وإلا لم"
                             " يُعرَف ما يُصلَح",
    "الحوكمةُ لم تُحسَم (لا نعمَ ولا لا)": "المحرّكُ لم يُجب لهذه الورقة"
                                          " — يُفصَل عن الامتناع كي لا"
                                          " تُقرأ بيئةٌ معطوبةٌ صحّةً",
    "وحدةٌ بلا مِرساة": "لقطةٌ لهذه الورقة (قيمةٌ سوقيةٌ وسعر) — فبها"
                        " تُسوّى الوحدةُ، وبدونها يبقى المنعُ صواباً",
}


async def main() -> int:
    global N, PROBE
    N, PROBE = _arg("--n", N), _arg("--probe", PROBE)

    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.data.market_universe import MARKET_UNIVERSE as U
    from app.models.portfolio import Company, Holding
    from app.services import statement_merge as SM
    from app.services import tadawul_market as tm
    from app.services import tadawul_xbrl as X
    from app.services.analysis import analyze_company
    from app.services.market_data import market_service as svc

    rows_snap, live, at = tm.usable_rows()
    # المحفظةُ مدخلٌ **إضافيّ** لا شرطٌ للمسح: قاعدةٌ متعذّرةٌ تُعلَن
    # ولا تُسقِط القياسَ كلَّه — وإلا لم تُقَس عقبةٌ إلا على خادمٍ كامل.
    mine: set[str] = set()
    db_err = None
    try:
        async with AsyncSessionLocal() as db:
            res = await db.execute(
                select(Company.symbol)
                .join(Holding, Holding.company_id == Company.id)
                .where(Holding.quantity > 0))
            mine = {str(s).replace(".SR", "") for (s,) in res.all()}
    except Exception as e:                                        # noqa: BLE001
        db_err = f"{type(e).__name__}: {e}"[:90]

    from app.data.universe import main_market
    sample = [str(s).replace(".SR", "") for s in main_market(U).keys()][:N]
    # ══ والقطاعانِ المسؤولُ عنهما يُضافانِ صريحاً ══
    # قِيس: صناديقُ المؤشرات **ليست في السوق الرئيسيّ أصلاً** (0 من 10)،
    # والريتاتُ في مؤخّرة الدليل — فعيّنةُ «أوّلِ N» لا تبلغهما، فتُمسَح
    # العقبةُ التي سُئلتُ عنها بصمتٍ. فتُضاف أوراقُهما كلُّها بأعيانها.
    funds = [str(s).replace(".SR", "") for s, m in U.items()
             if str((m or {}).get("sector") or "") in (ETF_SEC, REIT_SEC)]
    want = sorted(mine | set(sample) | set(funds))

    # ══ النطاقُ يُقصَّ على اللقطة — إلا الصناديقَ فغيابُها هو الخبر ══
    # ورقةٌ خارجَ اللقطة لم تُسأل أصلاً فلا تُعَدّ «بلا ملفّات». لكنّ
    # صندوقاً غائباً عن اللقطة عقبةٌ بنفسه (لا سعرَ ولا قيمةَ سوقيةً
    # تُسوّى بها وحدةٌ ولا يُقدَّر بها صافي أصول) — فيُقاس ويُسمّى.
    _f = set(funds)
    scoped = [s for s in want if s in rows_snap or s in _f]
    outside = [s for s in want if s not in rows_snap and s not in _f]
    fund_gone = [s for s in funds if s not in rows_snap]

    print(f"═ مسحُ العقبات ═ لقطةُ «تداول»: {len(rows_snap)} رمزاً ·"
          f" حيّةٌ={live} · {at}")
    print(f"  المطلوبُ قياسُه: {len(want)} (محفظةٌ {len(mine)} + عيّنةٌ"
          f" {len(sample)} + صناديقُ وريتاتٌ {len(funds)})")
    if db_err:
        print(f"  ⚠ أوراقُ المحفظة لم تُقرأ — {db_err}. المسحُ يمضي على"
              " العيّنة والصناديق، ولا يُقال إن المحفظةَ سليمة.")
    print(f"  داخلَ اللقطة: {len(scoped)} · خارجَها فلا تُسأل: {len(outside)}"
          + (f" — {' · '.join(outside[:14])}" if outside else ""))

    ob: dict[str, list[str]] = {}
    miss_field: Counter = Counter()
    miss_who: dict[str, list[str]] = {}
    gov_out: list[str] = []
    src_cnt: Counter = Counter()
    detail: list[str] = []
    probed = 0

    def hit(key: str, sym: str) -> None:
        ob.setdefault(key, []).append(sym)

    for s in fund_gone:
        hit("صندوقٌ غائبٌ عن لقطةِ السوق", s)

    for sym in scoped:
        sec = str((U.get(sym) or U.get(f"{sym}.SR") or {}).get("sector") or "—")
        if sec == ETF_SEC:
            hit("تصنيف/ETF", sym)
        elif sec == REIT_SEC:
            hit("تصنيف/ريت", sym)

        try:
            fin = await svc.get_financials(f"{sym}.SR", allow_supplement=False) or {}
        except Exception as e:                                    # noqa: BLE001
            fin = {}
            hit(f"تعذّر: {type(e).__name__}", sym)
        periods = fin.get("periods") or []
        # ══ ومصدرُ القوائم يُسمّى ══ (D345)
        # قرأتُ جدولاً يعدّ القوائمَ فاستدللتُ به على **المصدر** فأخطأتُ:
        # قوائمُ الريتات كانت من ياهو وظننتُها من «تداول». فالعددُ لا
        # يدلّ على المصدر — والمصدرُ يُطبَع صريحاً.
        src_cnt[str(fin.get("source") or "لا شيء") if periods else "لا قوائم"] += 1

        if not periods:
            saved = X.for_symbol(sym, "annual")
            if not saved and probed < PROBE:
                probed += 1
                try:
                    files = await X.filings_for(f"{sym}.SR")
                except Exception:                                 # noqa: BLE001
                    files = []
                hit("بلا ملفّاتٍ رسمية" if not files
                    else "ملفٌّ موجودٌ ولا يُقرأ", sym)
            elif not saved:
                hit("بلا صفوفٍ محفوظةٍ (لم تُسأل في هذه التشغيلة)", sym)
        else:
            for k in SM.missing(periods):
                miss_field[k] += 1
                miss_who.setdefault(k, []).append(sym)
            # ودلائلُ تسويةِ الوحدة كما وقعت فعلاً (‏D339)
            if any(p.get("scale_fix") for p in periods):
                hit("وحدةٌ سُوّيت", sym)
            if any(p.get("shares_unit_gap") for p in periods):
                hit("وحدةٌ بلا مِرساة", sym)
            if any(p.get("shares_mismatch") for p in periods):
                hit("فرقُ عددٍ أُعلِن", sym)

        try:
            an = await analyze_company(f"{sym}.SR", allow_supplement=False) or {}
        except Exception as e:                                    # noqa: BLE001
            hit(f"تعذّر التحليل: {type(e).__name__}", sym)
            continue
        # والامتناعُ يُفصَل عن **عدمِ الحسم**: `evaluable = None` يعني أن
        # المحرّكَ لم يُجب، فلو عُدَّ سليماً قرأنا بيئةً معطوبةً صحّةً.
        if an.get("evaluable") is False:
            gov_out.append(sym)
        elif an.get("evaluable") is None:
            hit("الحوكمةُ لم تُحسَم (لا نعمَ ولا لا)", sym)
        det = an.get("fair_value_detail") or {}
        if det.get("value") is None:
            why = str(det.get("unavailable_reason") or "")
            key = ("تضارُبُ المسارات" if "تشتّت" in why or "×" in why
                   else why.split("—")[0].strip()[:46]
                   or "امتناعٌ بلا سببٍ معلَن")
            hit(key, sym)
            lo, hi = det.get("low"), det.get("high")
            if lo and hi:
                detail.append(f"{sym}: {lo}–{hi}"
                              + (f" · تشتُّت {det.get('dispersion')}"
                                 if det.get("dispersion") else ""))
        # ودليلُ أن التسويةَ نفعت: قيمةٌ للسهم في نطاقٍ رياليّ
        bv = next((p.get("book_value_per_share") for p in reversed(periods)
                   if p.get("book_value_per_share") is not None), None)
        if isinstance(bv, (int, float)) and 0 < bv < 0.5:
            hit("قيمةُ سهمٍ دفتريةٌ دون نصفِ ريال (شبهةُ وحدة)", sym)

    print("\n═════ العقباتُ مرتَّبةً بعدد الأوراق التي تحجبها ═════")
    for key, syms in sorted(ob.items(), key=lambda kv: -len(kv[1])):
        print(f"\n  ▸ {key} — {len(syms)} ورقة")
        print(f"    {' · '.join(syms[:18])}" + (" …" if len(syms) > 18 else ""))
        cand = CANDIDATE.get(key)
        if cand:
            print(f"    الطبقةُ المرشَّحة: {cand}")

    print("\n═════ مصادرُ القوائم — لا يُستدَلّ عليها بالعدد (D345) ═════")
    for k, n in src_cnt.most_common():
        print(f"  {n:>4}  {k}")

    print("\n═════ البنودُ الناقصةُ بعد كلّ الطبقات — مرتَّبةً ═════")
    for k, n in miss_field.most_common(14):
        who = miss_who.get(k) or []
        print(f"  {n:>4}  {k:<22} {' · '.join(who[:10])}"
              + (" …" if len(who) > 10 else ""))
    if not miss_field:
        print("  لا بندَ ناقصاً في الأوراق التي لها قوائم.")

    print(f"\n═ الحوكمةُ تمتنع في: {len(gov_out)} ورقة"
          + (f" — {' · '.join(gov_out[:14])}" if gov_out else ""))
    if detail:
        print("\n═ مدياتُ الممتنعين (لِتُقرأ سعةُ الخلاف) ═")
        for d in detail[:14]:
            print(f"  {d}")

    print("\nالحكم: يُصلَح **أعلى العقبات** أوّلاً، وكلُّ عقبةٍ تُقابَل"
          " بطبقةٍ تملكها — لا بتخفيف عتبةٍ ولا بجملةِ اعتذار. وما لا"
          " تملكه طبقةٌ يُقال إنه ليس عندنا، وما كان خطأَ تصنيفٍ عندنا"
          " يُصلَح عندنا لا بشريكٍ جديد.")
    return 0


raise SystemExit(asyncio.run(main()))
