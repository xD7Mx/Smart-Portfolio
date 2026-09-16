#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D255 — ثلاثُ طبقاتٍ بترتيبٍ واحدٍ معلَن: تداول ← أرقام ← ياهو.
#
# بأمر المالك: «اجعل مصدره تداول ثمّ أرقام ثمّ ياهو، كلٌّ حسب ميزته…
# فلا نحتاج ياهو الآن إلا للضرورة». وميزةُ كلٍّ مقيسةٌ لا مُدّعاة:
#   · «تداول» مُصدِرُ السعر — لقطةٌ واحدةٌ تغطّي السوق كلَّه بزمنٍ محروس.
#   · «أرقام» نتائجُ الأرباع (‏D253).
#   · ياهو للتاريخ ولمن غاب عن الأولَيْن.
#
# وأثقلُ مستهلكٍ لياهو كان **مسحُ المحرّكين**: نداءٌ لكلّ رمزٍ في الكون كلَّ
# ساعة — وهو الذي أنفد الحصّةَ مرّتين. فصار يُبنى من لقطة «تداول».
# وخطرُ ذلك: أن يُصنَع تغيّرٌ من إغلاقٍ غائب، أو يُهجَر ياهو لمن يحتاجه.
# فيُقاس السلوك:
#   ٠· لقطةٌ كاملةٌ ⇒ **صفرُ نداءاتٍ** لياهو، والصفوفُ تُبنى منها
#   ١· ونسبةُ التغيّر تُشتقّ من الإغلاق السابق حين لا تُنشَر
#   ٢· وبلا سعرٍ ولا إغلاقٍ لا يُصنَع صفّ
#   ٣· ومن غاب عن اللقطة يُسأل عنه ياهو — وحدَه لا السوقُ كلُّه
#   ٤· وبلا لقطةٍ يعود المسحُ كما كان (لا انكسار)
#   ٥· وترتيبُ سعر الفرز: تداول ← ياهو ← لقطةُ المسح ← إغلاقُ البناء
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os as _os
import tempfile as _tf

_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

import asyncio  # noqa: E402
import pathlib  # noqa: E402
import sys  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

fail = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))


from app.services import cache  # noqa: E402
from app.services import market_movers as mm  # noqa: E402
from app.services import tadawul_market as tm  # noqa: E402
from app.data.market_universe import MARKET_UNIVERSE  # noqa: E402
from app.data.universe import main_market  # noqa: E402

SYMS = list(main_market(MARKET_UNIVERSE).keys())
# الصناديقُ تُسعَّر في المسحة نفسِها وإن لم تدخل الإحصاء — فمن أرادَ «صفرَ
# نداءات» عليه أن يغطّيها في اللقطة أيضاً، وإلا سُئل عنها المزوّدُ بحقّ.
FUNDS = [s for s, m in MARKET_UNIVERSE.items()
         if m.get("sector") == "صناديق المؤشرات المتداولة"]
ALL = SYMS + FUNDS
asked: list[list[str]] = []


class _FakeService:
    async def get_prices(self, syms):
        asked.append(list(syms))
        return {s: {"price": 11.0, "change_pct": 1.0, "volume": 5} for s in syms}


import app.services.market_data as _md  # noqa: E402
_md.market_service = _FakeService()                              # type: ignore[assignment]


def snap(rows):
    cache.set(tm.STORE_KEY, {"at": "now", "rows": rows}, 900)


def run():
    asked.clear()
    return asyncio.run(mm.compute_market_movers())


# ── ٠ · لقطةٌ كاملةٌ ⇒ لا نداءَ لياهو ─────────────────────────────────────
snap({s: {"price": 20.0 + i * 0.01, "change_pct": 1.5, "volume": 1000}
      for i, s in enumerate(ALL)})
out = run()
check(bool(out) and not asked,
      "٠ لقطةٌ كاملةٌ ⇒ صفرُ نداءاتٍ لياهو في مسح السوق",
      f"نداءات: {len(asked)} · رموزُ اللقطة: {len(ALL)}")
prices = (out or {}).get("prices") or {}
check(len(prices) >= len(SYMS) - 5 and abs(prices.get(SYMS[0], 0) - 20.0) < 1e-6,
      "٠ب والصفوفُ تُبنى من اللقطة نفسِها", f"{len(prices)} رمزاً")

# ── ١ · نسبةُ التغيّر تُشتقّ من الإغلاق السابق ─────────────────────────────
snap({s: {"price": 22.0, "prev_close": 20.0, "volume": 10} for s in ALL})
out = run()
row = next((r for r in ((out or {}).get("gainers") or [])
            if isinstance(r, dict) and r.get("change_pct") is not None), None)
check(row is not None and abs((row or {}).get("change_pct", 0) - 10.0) < 0.01,
      "١ نسبةُ التغيّر من الإغلاق السابق حين لا تُنشَر",
      f"{(row or {}).get('change_pct')}")

# ── ٢ · بلا إغلاقٍ ولا نسبةٍ لا يُصنَع صفّ ──────────────────────────────────
snap({s: {"price": 22.0} for s in ALL})
out = run()
check(bool(asked) and len(asked[0]) >= len(SYMS),
      "٢ سعرٌ بلا إغلاقٍ ولا نسبةٍ لا يُصنَع منه صفّ — يُسأل المزوّد",
      f"سُئل عن {len(asked[0]) if asked else 0} رمزاً")

# ── ٣ · من غاب عن اللقطة وحدَه يُسأل ──────────────────────────────────────
part = {s: {"price": 20.0, "change_pct": 1.0, "volume": 3} for s in ALL[:-7]}
snap(part)
out = run()
check(bool(asked) and 0 < len(asked[0]) <= 14,
      "٣ من غاب عن اللقطة يُسأل عنه ياهو وحدَه لا السوقُ كلُّه",
      f"سُئل عن {len(asked[0]) if asked else 0} من {len(SYMS)}")

# ── ٤ · بلا لقطةٍ يعود المسحُ كما كان ─────────────────────────────────────
snap({})
out = run()
check(bool(out) and bool(asked) and len(asked[0]) >= len(SYMS),
      "٤ وبلا لقطةٍ يعود المسحُ إلى ياهو كاملاً — لا انكسار",
      f"سُئل عن {len(asked[0]) if asked else 0} رمزاً")

# ── ٥ · ترتيبُ سعر الفرز ────────────────────────────────────────────────
from app.services import market_screener as ms  # noqa: E402

snap({"1111": {"price": 40.0}})
ms._movers_prices = lambda: {"1111": 31.0}                       # type: ignore[assignment]
cache.set("price:yahoo:1111.SR", None, 0)
r1 = asyncio.run(ms.refresh_derived([{"symbol": "1111", "name": "أ", "price": 20.0}]))[0]
check(r1.get("price_source") == "tadawul" and r1.get("price") == 40.0,
      "٥ «تداول» رأسُ الترتيب في الفرز", f"{r1.get('price')} · {r1.get('price_source')}")
snap({})
r2 = asyncio.run(ms.refresh_derived([{"symbol": "1111", "name": "أ", "price": 20.0}]))[0]
check(r2.get("price_source") == "movers" and r2.get("price") == 31.0,
      "٥ب وبغيابها تُقرأ الطبقةُ التالية بترتيبها",
      f"{r2.get('price')} · {r2.get('price_source')}")

# ── ٦ · وسلسلةُ سعرِ الشركة نفسُها: «تداول» أوّلاً (D330) ────────────────
# قال المالك: «يكون تداول مصدراً أوّلَ وياهو احتياطياً، والتطبيقُ بالكامل
# يعرض آخرَ سعرٍ لكلّ شركةٍ وما يُبنى عليه». وكانت `get_price` تنادي ياهو
# وسهمك **فقط** — و«تداول» ليست في السلسلة أصلاً. وقِيس في سجلّ خادمه
# عشراتُ `daily quota reached` في إقلاعٍ واحدٍ بينما اللقطةُ حاضرةٌ
# بـ٢٧٢ رمزاً بلا حصّة. ويُقاس هنا **السلوك**: من يُنادى ومن لا يُنادى.
_asked: list[str] = []


class _Prov:
    """مزوّدٌ محكوم: يسجّل كلَّ نداءٍ ويردّ سعراً مختلفاً عن اللقطة."""

    def __init__(self, tag):
        self.tag = tag

    async def get_price(self, sym):
        _asked.append(f"{self.tag}:{sym}")

        class _D:
            @staticmethod
            def to_dict():
                return {"symbol": str(sym), "price": 99.0, "change": 0.0,
                        "change_pct": 0.0, "volume": 0, "day_low": None,
                        "day_high": None, "prev_close": None}
        return _D()

    async def get_prices(self, syms):
        for s in syms:
            _asked.append(f"{self.tag}:bulk:{s}")
        return {s: {"symbol": s, "price": 99.0} for s in syms}


# نسخةٌ **حقيقيةٌ** من الخدمة: مخزنُ الوحدة استُبدل بمزيّفٍ أعلاه لقياس
# المحرّكين، والمقيسُ هنا سلسلةُ السعر نفسُها — فتُبنى الخدمةُ الأصلية
# ويُستبدل مزوّداها وحدَهما.
_svc = _md.MarketDataService()
_keep = (_svc.primary, _svc.secondary)
_svc.primary, _svc.secondary = _Prov("prim"), _Prov("sec")
snap({"2010": {"price": 70.5, "change_pct": 0.4, "prev_close": 70.2,
               "volume": 1234, "day_high": 71.0, "day_low": 70.0}})
try:
    _asked.clear()
    _one = asyncio.run(_svc.get_price("2010"))
    check(_one and _one.get("price") == 70.5 and _one.get("source") == "تداول"
          and not _asked,
          "٦ سعرُ الشركة من لقطة «تداول» أوّلاً — صفرُ نداءٍ للمزوّد",
          f"{_one and _one.get('price')} · نداءات={_asked}")
    check(_one and _one.get("prev_close") == 70.2
          and _one.get("change") == 0.3 and _one.get("day_high") == 71.0,
          "٦ب ومعه الإغلاقُ السابقُ وحدّا اليوم — لا حقلَ يضيع في النقل",
          str({k: _one.get(k) for k in ("prev_close", "change", "day_high")}))

    _asked.clear()
    _miss = asyncio.run(_svc.get_price("9999"))
    check(_miss and _miss.get("price") == 99.0 and _asked,
          "٦ج ومن غاب عن اللقطة يُسأل عنه المزوّد — لا «غيرُ متوفّر» بحجّة"
          " الترتيب", f"نداءات={_asked[:2]}")

    _asked.clear()
    _idx = asyncio.run(_svc.get_price("^TASI"))
    check(_asked and all("sec:" not in a for a in _asked),
          "٦د والمؤشّراتُ والنفطُ تبقى للمزوّد — ليست في لقطة السوق",
          f"نداءات={_asked[:2]}")

    _asked.clear()
    _many = asyncio.run(_svc.get_prices(["2010", "9999"]))
    check(_many.get("2010", {}).get("price") == 70.5
          and _many.get("9999", {}).get("price") == 99.0
          and [a for a in _asked if "2010" in a] == [],
          "٦ه والجمعُ كذلك: اللقطةُ لما تحمله والمزوّدُ لما بقي — لا نداءٌ"
          " لرمزٍ في اليد", f"نداءات={_asked}")
finally:
    _svc.primary, _svc.secondary = _keep

# ── ٧ · وكلُّ طبقةٍ تَسِمُ مخرَجَها، والمنشأُ يُقرأ لا يُكتَب (D334) ──────
# قِيس على خادم المالك بأداة الغربلة: تسعٌ من عشرٍ في محفظته قوائمُها من
# «تداول — XBRL»، وواحدةٌ بأربع فتراتٍ **ومصدرُها يُطبع «لا شيء»** لأن
# طبقةَ ياهو لا تضع `source`. وأثقلُ منه: بندُ «مصدر الأساسيات» في
# مخرَج التحليل كان **نصّاً ثابتاً «ياهو»** لكلّ شركةٍ — فالثقةُ تُبنى
# على نسبةٍ خاطئة. (عقدٌ نصّيٌّ يُقاس على الشيفرة: البديلُ تشغيلُ سلسلةِ
# تحليلٍ كاملةٍ بقاعدةٍ وشبكةٍ — وذاك مسبارٌ على الخادم لا حارسُ لجنة.)
_MD = (ROOT / "backend" / "app" / "services"
       / "market_data.py").read_text(encoding="utf-8")
_MARK = 'out["source"] = "ياهو"'
check(_MD.count(_MARK) >= 2,
      "٧ طبقةُ ياهو تَسِمُ مخرَجَها بمصدرها — سنويّاً وربعيّاً",
      f"{_MD.count(_MARK)} موضعاً")
_AN = (ROOT / "backend" / "app" / "services"
       / "analysis.py").read_text(encoding="utf-8")
check('"مصدر الأساسيات": "ياهو"' not in _AN,
      "٧ب ولا مصدرَ مكتوباً نصّاً في بيان المنشأ — لا «ياهو» لكلّ شركة")
check('(_stmt or {}).get("source")' in _AN,
      "٧ج والمنشأُ يُقرأ من الطبقة التي أجابت فعلاً")
check('"غير متوفّر"' in _AN,
      "٧د وبلا قوائمَ يُقال «غير متوفّر» — لا يُنسَب رقمٌ لمصدرٍ لم يُجب")

# ── ٨ · والنقصُ يُكمَّل لا يُعلَن — بالحقل ومع مصدره (D336) ──────────────
# بأمر المالك: «النقصُ ليس اعتذاراً يُعلَن وإنما اكتشافُ البديل المكمِّل
# لندمجَه مع المصدر الأساسيّ». وقِيس على ملفّ أرامكو: أصولٌ والتزاماتٌ
# بلا «حقوق»، وربحٌ وربحيةُ سهمٍ بلا «عددِ أسهم»، وقروضٌ متداولةٌ وغيرُ
# متداولةٍ بلا «إجماليّ دَين». والهويّاتُ المحاسبيةُ تُخرجها كلَّها.
from app.services import statement_merge as SM  # noqa: E402

_ROWS = [{"year": 2025, "net_income": 350210000000.0, "eps": 1.44,
          "total_assets": 2679259000000.0, "total_liabilities": 1109801000000.0,
          "operating_cash_flow": 510798000000.0,
          "pretax_income": 500000000000.0, "interest_expense": 10000000000.0,
          "borrowings_current": 46871000000.0,
          "borrowings_noncurrent": 308365000000.0}]
_M = SM.complete("2222", _ROWS,
                 yahoo_periods=[{"year": 2025, "capex": 100000000000.0},
                                {"year": 2024, "capex": 1.0}],
                 snapshot_row={"market_cap": 6220000000000.0,
                               "price_to_book": 4.0},
                 price=25.68)[0]
_S = _M.get("field_sources") or {}
check(_M.get("equity") == 1569458000000.0
      and "أصولٌ − التزامات" in _S.get("equity", ""),
      "٨ حقوقُ الملكية تُشتقّ بهويّةٍ محاسبية — وهي رقمُ الملفّ بالحرف",
      f"{_M.get('equity')} ← {_S.get('equity')}")
check(round(_M.get("shares_outstanding") or 0) == 243201388889
      and "ربحية السهم" in _S.get("shares_outstanding", ""),
      "٨ب وعددُ الأسهم من الربح ÷ ربحية السهم — لا من رأس المال ظنّاً",
      str(_M.get("shares_outstanding")))
check(_M.get("total_debt") == 355236000000.0,
      "٨ج وإجماليُّ الدَّين مجموعُ القروض المقروءة — لا جزءٌ منها",
      str(_M.get("total_debt")))
check(_M.get("capex") == 100000000000.0 and _S.get("capex") == "ياهو",
      "٨د وما لا يُنشَر رسمياً يُكمَل من طبقةٍ تملكه — بمطابقة السنة",
      f"{_M.get('capex')} ← {_S.get('capex')}")
check(_M.get("free_cash_flow") == 410798000000.0,
      "٨ه ويُعاد الاشتقاقُ بعد الإكمال — فالتدفّقُ الحرُّ صار ممكناً")

# ولا يُستبدَل منشورٌ بمكمِّل، ولا تُخلَط سنةٌ بأخرى
_M2 = SM.complete("X", [{"year": 2025, "capex": 7.0, "total_assets": 10.0,
                         "total_liabilities": 4.0}],
                  yahoo_periods=[{"year": 2025, "capex": 999.0},
                                 {"year": 2024, "total_assets": 111.0}])[0]
check(_M2.get("capex") == 7.0,
      "٨و والمنشورُ لا يُستبدَل بمكمِّلٍ — الإكمالُ للفراغ وحدَه")
check(_M2.get("equity") == 6.0,
      "٨ز والفترةُ تُكمَّل من سنتها لا من جارتها")
check(SM.missing([{"year": 2025, "revenue": 1.0}]),
      "٨ح وما بقي غائباً بعد الطبقات يُقال ولا يُختلق",
      str(SM.missing([{"year": 2025, "revenue": 1.0}]))[:60])
_MD2 = (ROOT / "backend" / "app" / "services"
        / "market_data.py").read_text(encoding="utf-8")
check("self._complete(" in _MD2 and "statement_merge" in _MD2,
      "٨ط والبابُ الواحدُ يُكمِل لكلّ شاشةٍ ومحرّك — لا في مسارٍ واحد")
# البوّابةُ نفسُها، ووسيطُ المسطرة أُضيف إليها لاحقاً (D349) — فيُقاس
# الشرطُ بمقدّمته لا بحرفيّة سطرٍ قديم، و٩س يحرس الوسيطَ وحدَه.
check("if SM.missing(rows" in _MD2,
      "٨ي وياهو لا يُنادى إن لم يبقَ بندٌ ناقص — لا حصّةٌ تُحرَق بلا حاجة")

# ── ٩ · ووحدةُ المال تُسوّى بمِرساةٍ لا بالهويّة وحدَها (D339) ───────────
# قِيس على خادم المالك: بعد مطابقة «عدد الأسهم» بالاسم صار مدى حالةٍ
# **0.04–0.14** ريالاً. والسببُ وحدةٌ غيرُ مسوّاة، والهويّةُ `EPS = الربح
# ÷ الأسهم` تكشف أن أحدَ الطرفين أخطأ ولا تقول أيَّهما — فأوّلُ صياغةٍ
# حكمت بها وحدَها فقسمت مالاً مسوّىً على ألف. والفاصلُ مِرساةٌ مستقلّةٌ
# عن تقريب الملفّ: قيمةُ لقطةِ «تداول» السوقيةُ ÷ السعر.
_NI, _EPS, _SH = 350210000000.0, 1.44, 243201388889.0
_EQ, _PX = 1569458000000.0, 25.68
_SNAP = {"market_cap": _SH * _PX}
_BASE = {"year": 2025, "eps": _EPS}


def _one(**kw):
    snap, px = kw.pop("snapshot_row", None), kw.pop("price", None)
    return SM.complete("T", [dict(_BASE, **kw)],
                       snapshot_row=snap, price=px)[0]


_U1 = _one(net_income=_NI / 1000, equity=_EQ / 1000, shares_outstanding=_SH,
           snapshot_row=_SNAP, price=_PX)
check(_U1.get("scale_fix") == 1000.0 and _U1.get("net_income") == _NI
      and _U1.get("equity") == _EQ,
      "٩ مالٌ بالآلاف تُسوّى وحدتُه بالمِرساة — لا يبقى أصغرَ ألفَ مرّة",
      f"{_U1.get('scale_fix')} · {_U1.get('net_income')}")
check(_U1.get("book_value_per_share") == 6.4533,
      "٩ب وقيمةُ السهم الدفتريةُ تصير رياليةً لا 0.006",
      str(_U1.get("book_value_per_share")))
_U2 = _one(net_income=_NI, equity=_EQ, shares_outstanding=_SH / 1000,
           snapshot_row=_SNAP, price=_PX)
check(_U2.get("shares_outstanding") == round(_SH, 0)
      and _U2.get("scale_fix") is None
      and "وحدةُ العدد سُوّيت" in (_U2.get("field_sources") or {}).get(
          "shares_outstanding", ""),
      "٩ج وعددٌ بالآلاف تُسوّيه المِرساةُ — ولا يُقسَم المالُ بدلاً عنه",
      f"{_U2.get('shares_outstanding')} · {_U2.get('scale_fix')}")
_U3 = _one(net_income=_NI, equity=_EQ, shares_outstanding=_SH,
           snapshot_row=_SNAP, price=_PX)
check(_U3.get("scale_fix") is None and _U3.get("net_income") == _NI
      and _U3.get("shares_outstanding") == _SH,
      "٩د وملفٌّ سليمُ الوحدة لا يُمَسّ — لا تسويةَ على غير عطب",
      f"{_U3.get('net_income')} · {_U3.get('shares_outstanding')}")
_U4 = _one(net_income=_NI / 1000, equity=_EQ / 1000, shares_outstanding=_SH)
check(_U4.get("shares_unit_gap") == 1000.0
      and _U4.get("shares_outstanding") == _SH
      and _U4.get("book_value_per_share") is None,
      "٩ه وبلا مِرساةٍ يُعلَن الفرقُ ولا يُختلَق — ولا قيمةَ سهمٍ عليه",
      f"{_U4.get('shares_unit_gap')} · {_U4.get('book_value_per_share')}")
# وفرقُ **العدد** ليس فرقَ وحدة: المنشورُ عددُ المُصدَر والقسمةُ تُخرج
# المتوسّطَ المرجَّح لأساس ربحيةِ السهم، واختلافُهما مشروع. وصياغةٌ لي
# كانت تستبدل المنشورَ هنا فأحمرَ عليها العقدُ ٧ب في `tadawul_xbrl.py`
# — فالمنشورُ يبقى بالحرف في الحالين، مع مِرساةٍ وبلا مِرساة.
_U5 = _one(net_income=_NI, shares_outstanding=150000000000.0,
           snapshot_row={"market_cap": 150000000000.0 * _PX}, price=_PX)
check(_U5.get("shares_outstanding") == 150000000000.0
      and _U5.get("shares_mismatch") == 1.62,
      "٩و وفرقُ عددٍ لا يُستبدَل به المنشورُ — يُسمّى الخلافُ فقط",
      f"{_U5.get('shares_outstanding')} · {_U5.get('shares_mismatch')}")
_U6 = _one(net_income=_NI, shares_outstanding=150000000000.0)
check(_U6.get("shares_outstanding") == 150000000000.0
      and _U6.get("shares_mismatch") == 1.62,
      "٩ز وبلا مِرساةٍ كذلك — لا يُستبدَل منشورٌ بمشتقٍّ بحالٍ",
      f"{_U6.get('shares_outstanding')} · {_U6.get('shares_mismatch')}")

# ── ٩ح · ولا رقمَ للسهم على عددٍ مخالف (D347) ────────────────────────────
# قِيس على خادم المالك بعد D339: مدى 2290 صار 0.04–0.14 ريالاً وهي في
# قائمة «فرقُ عددٍ أُعلِن». فالتسميةُ لا تكفي — يجب أن يمتنع الحسابُ.
_U7 = _one(net_income=_NI, equity=_EQ, shares_outstanding=150000000000.0)
check(_U7.get("shares_mismatch") == 1.62
      and _U7.get("book_value_per_share") is None,
      "٩ح وفرقُ العدد يمنع قيمةَ السهم كما يمنعها فرقُ الوحدة",
      f"{_U7.get('shares_mismatch')} · {_U7.get('book_value_per_share')}")

# والمحرّكُ نفسُه يتخطّى الفترةَ الموسومةَ ولا يقسم عليها
from app.services.fair_value import _dcf                          # noqa: E402

_FP = [{"year": 2023, "operating_cash_flow": 1.0e9, "capex": 1.0e8,
        "net_income": 9.0e8, "total_debt": 0.0, "ending_cash": 1.0e8,
        "shares_outstanding": 1.0e8},
       {"year": 2024, "operating_cash_flow": 1.1e9, "capex": 1.0e8,
        "net_income": 9.5e8, "total_debt": 0.0, "ending_cash": 1.0e8,
        "shares_outstanding": 1.0e8},
       {"year": 2025, "operating_cash_flow": 1.2e9, "capex": 1.0e8,
        "net_income": 1.0e9, "total_debt": 0.0, "ending_cash": 1.0e8,
        "shares_outstanding": 1.0e8}]
_ok = _dcf([dict(p) for p in _FP], {"beta": 1.0}, 30.0, 0.09)
_bad = _dcf([dict(p, shares_mismatch=1.6) for p in _FP],
            {"beta": 1.0}, 30.0, 0.09)
check(_ok is not None and _bad is None,
      "٩ط والمحرّكُ يمتنع على عددٍ موسومٍ بدل أن يقسم عليه",
      f"سليم={None if _ok is None else 'قيمة'} · موسوم={_bad}")

# ── ٩ي · المسطرةُ القطاعية: ما لا يُنشَر في صنفٍ ليس ناقصاً (D349) ───────
# قِيس على خادم المالك: `interest_expense` غائبٌ في ٣٢ من ٩٠ ومعه `ebit`،
# وعشرُ الأولى بنوكٌ لا تنشر البندَ أصلاً (دخلُها عمولةٌ صافية). فالبندُ
# غيرُ ذي معنى في نموذجها لا ناقصٌ من مصدرها — ولا تُحرَق له حصّةُ مزوّد.
_ROWS9 = [{"year": 2025, "revenue": 1.0}]
# والحارسُ يُبلّغ ولا ينفجر: غيابُ الواجهة نفسِها غيابُ السلوك، فيُقرأ
# أحمرَ مطبوعاً لا انهياراً يُسكِت ما بعده.
_nm = getattr(SM, "not_meaningful", lambda *_a, **_k: ())
_ar = getattr(SM, "archetype_of", lambda *_a, **_k: None)


def _miss(rows, sym=None):
    try:
        return SM.missing(rows, sym) if sym else SM.missing(rows)
    except TypeError:                     # واجهةٌ بلا وسيط الصنف
        return SM.missing(rows)


_NM_B = _nm("1010")
check(_ar("1010") == "bank"
      and "interest_expense" in _NM_B and "ebit" in _NM_B
      and "interest_expense" not in _miss(_ROWS9, "1010"),
      "٩ي تكلفةُ تمويلِ بنكٍ تُعلَن غيرَ ذي معنى — لا ناقصةً تُطلَب",
      f"نمط={_ar('1010')} · غيرُ ذي معنى={len(_NM_B)}")
check(_ar("9400") == "fund"
      and _miss(_ROWS9, "9400") == []
      and len(_nm("9400")) == len(SM.NEEDED),
      "٩ك وصندوقُ المؤشّر لا يُطلَب منه بندٌ — لا قوائمَ له بطبيعته",
      f"ناقص={len(_miss(_ROWS9, '9400'))}")
check(len(_miss(_ROWS9, "2222")) == len(SM.missing(_ROWS9))
      and _nm("2222") == (),
      "٩ل وشركةٌ عاديةٌ لا تُعفى من شيءٍ — لا إعفاءَ يتسلّل بالمسطرة",
      f"{len(_miss(_ROWS9, '2222'))} بنداً")
check(_ar("4330") == "reit" and "capex" in _nm("4330"),
      "٩م والريتُ يشتري عقاراتٍ لا آلاتٍ — فالرأسماليُّ غيرُ ذي معنى له")

# والمحرّكُ يمتنع للورقة المؤشِّرة **بسببها لا بسبب شركة**
from app.services.fair_value import compute as _fv                # noqa: E402

_F9 = _fv({}, 34.0, symbol="9400", periods=[])
_why9 = str((_F9 or {}).get("unavailable_reason") or "")
check(_F9.get("value") is None and "ورقةٌ مؤشِّرة" in _why9
      and "لم تصلنا" not in _why9,
      "٩ن وامتناعُ الورقة المؤشِّرة بسببها — لا بجملةِ «نقصٍ في وصول قوائم»",
      _why9[:58])
_MD9 = (ROOT / "backend" / "app" / "services"
        / "market_data.py").read_text(encoding="utf-8")
check("SM.missing(rows, symbol)" in _MD9,
      "٩س وبوّابةُ المزوّد تقرأ مسطرةَ الصنف — لا حصّةَ لبندٍ بلا معنى")

print(("FAIL" if fail else "PASS") + " D255 — ثلاثُ طبقاتٍ بترتيبٍ واحد")
raise SystemExit(fail)
