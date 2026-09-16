#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D251 — المصدرُ يتقدّم المزوّد: مكرّرُ «تداول» لا مكرّرُنا المشتقّ.
#
# أربعةُ أعطابٍ سابقةٍ (‏D239 · D244 · D246 · D247) كانت كلُّها خلافاتِ
# **اشتقاق**: نحسب المكرّرَ ومضاعفَ الدفترية من سعرٍ ومقياسٍ من ياهو،
# فيختلف المسارانِ في الترتيب أو المدى أو الزمن. وبعد عبور الحماية صار
# السوقُ يُقرأ من مُصدِره: هذه الحقولُ **منشورةٌ** فيه.
#
# وخطرُ ذلك مصدرٌ ثالثٌ يتنازع: لقطةٌ شائخةٌ تُقرأ سعراً حاضراً، أو جلبٌ
# فاشلٌ يُقرأ سوقاً تقلّص. فيُقاس السلوك:
#   ٠· صفوفُ «تداول» تُطبَّع بأسمائنا
#   ١· والأصفارُ والفراغُ لا تُكتب مفاتيحَ كاذبة
#   ٢· وقائمةٌ قصيرةٌ تُرفَض ولا تُحفَظ
#   ٣· ولقطةٌ شائخةٌ لا تُقرأ
#   ٤· والمكرّرُ المنشورُ يتقدّم المشتقَّ من السعر
#   ٥· وحيث لا لقطةَ يبقى الاشتقاقُ كما كان (لا انكسار)
#   ٦· وحدّا العام من المصدر، ويتّسعان لسعر اليوم
#   ٧· وسعرُ الفرز يأخذها بعد الكاش الحيّ ولقطةِ المحرّكين
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os as _os
import tempfile as _tf

_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

import asyncio  # noqa: E402
from loguru import logger  # noqa: E402
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
from app.services import tadawul_market as tm  # noqa: E402
from app.services.valuation_fields import resolve_display  # noqa: E402


def raw(sym="2030", **kw):
    """صفٌّ على شكل مخرَج «تداول» — قِيست مفاتيحُه على الخادم."""
    r = {"companyRef": int(sym), "sectorName": "Energy", "lastTradePrice": 54.85,
         "PER": 21.5, "PBR": 3.25, "marketCap": 1234567890.0,
         "high52WeekPrice": 60.0, "low52WeekPrice": 40.0,
         "previousClosePrice": 54.0, "precentChange": 1.57}
    r.update(kw)
    return r


# ── ٠ · التطبيع ─────────────────────────────────────────────────────────
t = tm.normalize([raw()])
check(t.get("2030", {}).get("pe_ratio") == 21.5
      and t["2030"].get("price_to_book") == 3.25
      and t["2030"].get("week52_high") == 60.0
      and t["2030"].get("price") == 54.85,
      "٠ صفوفُ «تداول» تُطبَّع بأسمائنا", str(t.get("2030"))[:120])

# ── ١ · الأصفارُ ليست قيماً ──────────────────────────────────────────────
t0 = tm.normalize([raw(PER=0, PBR=None, high52WeekPrice=0)])
check("pe_ratio" not in t0["2030"] and "price_to_book" not in t0["2030"]
      and "week52_high" not in t0["2030"] and t0["2030"].get("price") == 54.85,
      "١ الصفرُ والفراغُ لا يُكتبان مفاتيحَ كاذبة", str(t0["2030"])[:120])

# ── ٢ · قائمةٌ قصيرةٌ تُرفَض ولا تُحفَظ ─────────────────────────────────────
async def _few():
    return [raw(str(2000 + i)) for i in range(5)], None


_REAL_FETCH_ROWS = tm.fetch_rows      # يُستعاد في الفحص ١١ (D357)
tm.fetch_rows = _few                                             # type: ignore[assignment]
rec = asyncio.run(tm.refresh())
check(rec.get("count") == 0 and "الحدّ" in str(rec.get("error")) and not tm.snapshot(),
      "٢ قائمةٌ دون الحدّ جلبٌ فشل — تُرفَض ولا تُحفَظ", str(rec)[:90])


async def _many():
    return [raw(str(1000 + i)) for i in range(220)], None


tm.fetch_rows = _many                                            # type: ignore[assignment]
rec = asyncio.run(tm.refresh())
check(rec.get("count") == 220 and len(tm.snapshot()) == 220,
      "٢ب وقائمةٌ كاملةٌ تُحفَظ وتُقرأ", str(rec.get("count")))

# ── ٣ · اللقطةُ الشائخةُ لا تُقرأ ──────────────────────────────────────────
import time as _time  # noqa: E402

from app.services import lastgood  # noqa: E402

cache.set(tm.STORE_KEY, None, 0)
lastgood.save(tm.STORE_KEY, {"at": "2020-01-01", "rows": {"1000": {"price": 9.0}}})
_saved = lastgood.load
lastgood.load = lambda k, max_age_seconds=None: (                # type: ignore[assignment]
    None if max_age_seconds is not None else _saved(k))
try:
    aged = tm.snapshot()
finally:
    lastgood.load = _saved                                       # type: ignore[assignment]
check(aged == {}, "٣ لقطةٌ أقدمُ من ربع ساعةٍ ليست سعراً حاضراً", str(aged)[:60])

# ── ٤ · المنشورُ يتقدّم المشتقّ ───────────────────────────────────────────
cache.set(tm.STORE_KEY, {"at": "now", "rows": {"2030": {
    "pe_ratio": 21.5, "price_to_book": 3.25,
    "week52_high": 60.0, "week52_low": 40.0}}}, 900)
out = resolve_display("2030", 50.0, fund={"eps": 2.0, "book_value": 10.0,
                                          "pe_ratio": 40.0})
check(out.get("pe_ratio") == 21.5 and out.get("price_to_book") == 3.25,
      "٤ مكرّرُ «تداول» يتقدّم مكرّرَ المزوّد والمشتقَّ من السعر",
      f"{out.get('pe_ratio')} · {out.get('price_to_book')}")

# ── ٥ · بلا لقطةٍ يبقى السلوكُ القديم ─────────────────────────────────────
cache.set(tm.STORE_KEY, {"at": "now", "rows": {}}, 900)
out2 = resolve_display("2030", 50.0, fund={"eps": 2.0, "book_value": 10.0})
check(out2.get("pe_ratio") == 25.0 and out2.get("price_to_book") == 5.0,
      "٥ وحيث لا لقطةَ يبقى الاشتقاقُ كما كان",
      f"{out2.get('pe_ratio')} · {out2.get('price_to_book')}")

# ── ٦ · حدّا العام من المصدر ويتّسعان لسعر اليوم ───────────────────────────
cache.set(tm.STORE_KEY, {"at": "now", "rows": {"2030": {
    "week52_high": 60.0, "week52_low": 40.0}}}, 900)
out3 = resolve_display("2030", 65.0, fund={"week52_high": 55.0, "week52_low": 30.0})
check(out3.get("high_52w") == 65.0 and out3.get("low_52w") == 40.0,
      "٦ حدّا العام من المصدر، والأعلى يتّسع لسعر اليوم",
      f"{out3.get('high_52w')} · {out3.get('low_52w')}")

# ── ٧ · ترتيبُ سعر الفرز ────────────────────────────────────────────────
from app.services import market_screener as ms  # noqa: E402

cache.set(tm.STORE_KEY, {"at": "now", "rows": {"1111": {"price": 28.0},
                                               "2222": {"price": 33.0}}}, 900)
ms._movers_prices = lambda: {"2222": 31.0}                       # type: ignore[assignment]
rows = asyncio.run(ms.refresh_derived([
    {"symbol": "1111", "name": "أ", "price": 20.0},
    {"symbol": "2222", "name": "ب", "price": 20.0},
]))
by = {r["symbol"]: r for r in rows}
check(by["1111"].get("price") == 28.0 and by["1111"].get("price_source") == "tadawul",
      "٧ من لا سعرَ له في كاشٍ ولا مسحٍ يأخذ سعرَ «تداول»",
      f"{by['1111'].get('price')} · {by['1111'].get('price_source')}")
# ══ انعكاسٌ مقصود ══ (D255) كان هذا الفحصُ يشترط تقدُّمَ لقطة المحرّكين
# على «تداول». وأمرَ المالك بترتيب الطبقات: «تداول ثمّ أرقام ثمّ ياهو».
# فصارت «تداول» رأسَ الترتيب حتى حيث توجد لقطةُ مسحٍ لها سعرٌ آخر.
check(by["2222"].get("price") == 33.0 and by["2222"].get("price_source") == "tadawul",
      "٧ب و«تداول» تتقدّم لقطةَ المحرّكين — المُصدِرُ قبل المزوّد",
      f"{by['2222'].get('price')} · {by['2222'].get('price_source')}")

# ── ٨ · مَعبرٌ واحدٌ لـ«تداول» — لا httpx في خدمةٍ تناديها ──────────────
# قِيس على خادم المالك: خدمةُ الإفصاحات كانت تنادي «تداول» بـ`httpx`
# برؤوسٍ كاملةٍ وجلسةٍ مسخَّنة، فتردّ **403 Access Denied** (475 حرفاً) في
# كلّ نداء — فلا إفصاحَ واحدٌ يصل، والمفكرةُ والأخبارُ وبحثُ الصفقات تُبنى
# على الفراغ بصمت. والقياسُ في D250 كان قد أبطل الاعتقادَ المكتوبَ فيها:
# الرؤوسُ الكاملةُ مع httpx ⇒ 403، ونفسُها مع انتحال البصمة ⇒ 200 (D312).
import pathlib as _pl  # noqa: E402

_SVC = _pl.Path(ROOT) / "backend" / "app" / "services"
_GATEWAY = {"tadawul_http.py"}          # المَعبرُ وحدَه يملك سقوطَ httpx
_bad = []
for _f in sorted(_SVC.glob("*.py")):
    _src = _f.read_text(encoding="utf-8", errors="ignore")
    if "saudiexchange.sa" not in _src or _f.name in _GATEWAY:
        continue
    if "httpx.AsyncClient" in _src:
        _bad.append(_f.name)
check(not _bad,
      "٨ كلُّ خدمةٍ تنادي «تداول» تمرّ بالمَعبر المنتحِل — لا جلسةَ httpx ثانية",
      "خارجَ المَعبر: " + "، ".join(_bad) if _bad else "")

_ANN = (_SVC / "tadawul_announcements.py").read_text(encoding="utf-8")
check("from app.services.tadawul_http import fetch" in _ANN,
      "٨ب وخدمةُ الإفصاحات بعينها تستعمله — وهي التي قِيس ردُّها 403")

# ── ١١ · وسوقانِ في اللقطة: الرئيسيُّ و«نمو» (D357) ──────────────────────
# قِيس بالكاشف `other_boards.py`: الخدمةُ هي هي، والجدولُ يتبع **الصفحةَ**
# لا اسمَ الخدمة — فصفحةُ «نمو» تُخرج 124 صفّاً فيها 123 من الـ136 التي
# لم نكن نسألها. ويُقاس السلوكُ لا النصّ: أيَّ صفحةٍ يطلب · وهل يُدمَج ·
# وهل يُزاح رمزٌ من الرئيسيّ · وهل يُسقِط تعذّرُ «نمو» اللقطةَ كلَّها.
_asked_pages: list[str] = []


def _mk_rows(pfx: str, n: int) -> list:
    return [{"symbol": f"{pfx}{i:03d}", "companyName": "ش", "lastTradePrice": "10",
             "changePercent": "1", "volumeTraded": "5"} for i in range(n)]


async def _fake_fetch(url, *, params=None, referer=None, timeout=45):
    _asked_pages.append(url)
    if "nomuc-market-watch" in url and params is None:
        return 200, '<base href="https://x/nomu/"><a>p0/A=NJgetMainNomucMarketDetails=/</a>'
    if "main-market-watch" in url and params is None:
        return 200, '<base href="https://x/main/"><a>p0/A=NJgetMainNomucMarketDetails=/</a>'
    if url.startswith("https://x/nomu/"):
        return 200, _json.dumps({"data": _mk_rows("9", 124)})
    if url.startswith("https://x/main/"):
        return 200, _json.dumps({"data": _mk_rows("1", 272)})
    return 404, ""


import json as _json  # noqa: E402
import app.services.tadawul_http as _http  # noqa: E402

# ══ ويُستعاد الجالبُ الحقيقيُّ أوّلاً ══
# فحصٌ سابقٌ أبدل `tm.fetch_rows` ببديلٍ يردّ 220 صفّاً، فلو قِيس
# التحديثُ فوقه لقِستُ بديلي لا شفرتي — وهو العطبُ الذي وقعتُ فيه
# مرّاتٍ وسُجّل. فالاستعادةُ شرطُ صدقِ هذا الفحص.
tm.fetch_rows = _REAL_FETCH_ROWS                                 # type: ignore[assignment]
_keep_fetch = _http.fetch
_http.fetch = _fake_fetch                                        # type: ignore[assignment]
_rep = asyncio.run(tm.refresh())
_http.fetch = _keep_fetch                                        # type: ignore[assignment]
check(any("nomuc-market-watch" in u for u in _asked_pages),
      "١١ صفحةُ «نمو» تُطلَب كما تُطلَب الرئيسية — بابٌ لسوقَين",
      f"{len(_asked_pages)} طلباً")
check(_rep.get("count") == 396 and _rep.get("nomu") == 124,
      "١١ب واللقطةُ تجمع السوقَين — 272 + 124",
      f"{_rep.get('count')} رمزاً · «نمو» {_rep.get('nomu')}")
_rows_now = (tm.usable_rows()[0] or {})
check(any(k.startswith("9") for k in _rows_now)
      and any(k.startswith("1") for k in _rows_now),
      "١١ج ورموزُ السوقَين معاً في المحفوظ — لا يُزيح أحدُهما الآخر")

# وبالاتّجاه المعاكس: تعذّرُ «نمو» لا يُسقِط اللقطةَ
_asked_pages.clear()


async def _nomu_dead(url, *, params=None, referer=None, timeout=45):
    if "nomuc-market-watch" in url:
        return 500, ""
    return await _fake_fetch(url, params=params, referer=referer)


_http.fetch = _nomu_dead                                         # type: ignore[assignment]
_rep2 = asyncio.run(tm.refresh())
_http.fetch = _keep_fetch                                        # type: ignore[assignment]
check(_rep2.get("count") == 272 and _rep2.get("nomu") == 0,
      "١١د وتعذّرُ «نمو» يُعلَن ولا يُسقِط الرئيسيَّ — بابٌ ثانٍ لا نقطةُ انكسار",
      f"{_rep2.get('count')} رمزاً")

# ── ١١ه · ساقُ «نمو» تُعاد محاولتُها، والتقلّصُ يُعلَن (D361) ────────────
# قِيس على خادم المالك: لقطةٌ 396 عند 18:29 ثمّ 272 عند 18:46 — ساقُ
# «نمو» سقطت في تجديدٍ لاحقٍ بصمتٍ فضاع ثلثُ السوق.
_tries = {"n": 0}


async def _flaky(url, *, params=None, referer=None, timeout=45):
    if "nomuc-market-watch" in url and params is None:
        _tries["n"] += 1
        if _tries["n"] == 1:
            return 500, ""                     # أوّلُ محاولةٍ تسقط
    return await _fake_fetch(url, params=params, referer=referer)


_http.fetch = _flaky                                             # type: ignore[assignment]
_rep3 = asyncio.run(tm.refresh())
_http.fetch = _keep_fetch                                        # type: ignore[assignment]
check(_tries["n"] >= 2 and _rep3.get("nomu") == 124,
      "١١ه سقوطٌ عارضٌ لـ«نمو» تُعاد محاولتُه فتعود 124 — لا يُسلَّم لأوّل تعذّر",
      f"محاولات={_tries['n']} · «نمو»={_rep3.get('nomu')}")
_rec3 = (lastgood.load(tm.STORE_KEY) or {})
check((_rec3.get("boards") or {}).get("nomu") == 124
      and (_rec3.get("boards") or {}).get("main") == 272,
      "١١و واللقطةُ تحفظ عددَ كلّ بورصةٍ — فالتقلّصُ يُقارَن لا يُظَنّ",
      str(_rec3.get("boards")))

# وبالاتّجاه المعاكس: بورصةٌ كانت تُقرأ وسقطت ⇒ تحذيرٌ باسمها
_warns: list[str] = []
_sink = logger.add(lambda m: _warns.append(str(m)), level="WARNING")
_http.fetch = _nomu_dead                                         # type: ignore[assignment]
asyncio.run(tm.refresh())
_http.fetch = _keep_fetch                                        # type: ignore[assignment]
logger.remove(_sink)
check(any("نمو" in w and "سقطت" in w for w in _warns),
      "١١ز وبورصةٌ كانت تُقرأ ثمّ سقطت تُسمّى بالاسم — لا نقصٌ يمرّ بصمت",
      f"{len(_warns)} تحذيراً")

print(("FAIL" if fail else "PASS") + " D251 — لقطةُ السوق من مُصدِره")
raise SystemExit(fail)
