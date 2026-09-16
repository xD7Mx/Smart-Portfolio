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

print(("FAIL" if fail else "PASS") + " D255 — ثلاثُ طبقاتٍ بترتيبٍ واحد")
raise SystemExit(fail)
