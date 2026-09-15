#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D272 · D273 — ما جُمع ولم يُعرَض ليس مُسلَّماً، وما طُلب ولم يُبنَ ليس منسيّاً.
#
# سألني المالكُ أن أتأكّد أنّي لم أسهُ عن شيءٍ طلبه. فوجدتُ اثنين:
#
#   · **عمقُ السوق**: قُرئ أفضلُ طلبٍ وعرضٍ في لقطة «تداول» (‏D262) وبقي
#     في اللقطة **بلا بابٍ ولا شاشة** — وقلتُ له «سُلّم». والتسليمُ أن
#     يصل العين.
#   · **الصفقاتُ الخاصة**: طلبها صراحةً ولم تُبنَ أصلاً.
#
#   ٠· العمقُ يُقرأ من اللقطة ويُسمّى بعدد مستوياته
#   ١· وطرفٌ ناقصٌ يغيب ولا يُصفَّر
#   ٢· وبلا لقطةٍ حاضرةٍ يُقال «غير متوفّر» — لا صفرٌ ولا اختلاق
#   ٣· والبابُ موصولٌ بالشاشة فعلاً — لا مسارٌ لا يناديه أحد
#   ٤· والصفقةُ بلا أركانها الثلاثة ليست صفقةً تُعرض
#   ٥· وأسماءُ الحقول مرشَّحاتٌ تُقاس، وما لم يوجد يغيب
#   ٦· ويومٌ بلا صفقاتٍ لا يمحو المحفوظ
#   ٧· ولا تُجلب في مسار طلبِ المستخدم — الجلبُ في الجدولة
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os as _os
import tempfile as _tf

_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

import asyncio  # noqa: E402
import datetime as _dt2  # noqa: E402
import json  # noqa: E402
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


from app.api.v1.endpoints import market as M  # noqa: E402
from app.services import cache, special_deals as sd, tadawul_market as tm  # noqa: E402


def _snap(rows: dict) -> None:
    # ══ لقطةٌ حيّةٌ تُختم بالآن ══ (D298)
    # كان الزمنُ تاريخاً مطلقاً، فصار الفحصُ يشيخ مع الأيّام: اللقطةُ
    # الحيّةُ تُقاس بزمنها المُعلَن، وتاريخٌ ثابتٌ يصير قديماً بعد أيّام
    # فيسقط الفحصُ لا لعطبٍ في الشيفرة بل لمرور الوقت.
    cache.set(tm.STORE_KEY,
              {"at": _dt2.datetime.now(_dt2.timezone.utc)
                     .isoformat(timespec="seconds"), "rows": rows},
              tm.MAX_AGE_SECONDS)


def _data(res) -> dict:
    return (res.get("data") if isinstance(res, dict) else {}) or {}


# ── ٠ · ١ · ٢ · العمق ───────────────────────────────────────────────────
_snap({"2010": {"price": 70.0, "bid": 69.8, "bid_qty": 1200,
                "ask": 70.2, "ask_qty": 800, "trades": 940,
                "prev_close": 69.5}})
d = _data(asyncio.run(M.get_market_depth("2010")))
check(d.get("available") and d.get("levels") == 1
      and d["bids"][0] == {"price": 69.8, "quantity": 1200}
      and d["asks"][0] == {"price": 70.2, "quantity": 800},
      "٠ العمقُ يُقرأ من اللقطة ويُسمّى بعدد مستوياته", str(d.get("levels")))
check(abs((d.get("spread") or 0) - 0.4) < 1e-9,
      "٠ب والفارقُ يُشتقّ من الطرفين لا يُنسَخ", str(d.get("spread")))
check(d.get("levels") == 1 and "20" not in str(d.get("note") or ""),
      "٠ج ولا يُوعَد بعشرين مستوًى لا نملكها", str(d.get("note"))[:40])

_snap({"2010": {"price": 70.0, "bid": 69.8, "ask": 70.2, "ask_qty": 800}})
d2 = _data(asyncio.run(M.get_market_depth("2010")))
check(d2.get("bids") == [] and len(d2.get("asks") or []) == 1,
      "١ طرفٌ بلا كمّيةٍ يغيب — ولا يُصفَّر", str(d2.get("bids")))

cache.set(tm.STORE_KEY, None, 0)
d3 = _data(asyncio.run(M.get_market_depth("2010")))
check(d3.get("available") is False and d3.get("levels") == 0
      and d3.get("bids") == [],
      "٢ وبلا لقطةٍ حاضرةٍ: «غير متوفّر» — لا صفرٌ يُقرأ سعراً", str(d3)[:60])

# ── ٣ · البابُ موصولٌ بالشاشة فعلاً ──────────────────────────────────────
API = (ROOT / "frontend" / "src" / "services" / "api.ts").read_text(encoding="utf-8")
DEPTH = (ROOT / "frontend" / "src" / "components" / "market"
         / "MarketDepth.tsx").read_text(encoding="utf-8")
check("/market/depth/" in API and "marketApi.depth(" in DEPTH,
      "٣ المسارُ له نداءٌ في الواجهة — لا بابٌ لا يطرقه أحد")
for screen in ("components/market/StockView.tsx", "pages/CompanyPage.tsx"):
    src = (ROOT / "frontend" / "src" / screen).read_text(encoding="utf-8")
    check("<MarketDepth" in src,
          f"٣ب والبطاقةُ مركّبةٌ في {screen.split('/')[-1]} — لا مكوّنٌ يتيم")
check("غير متوفّر" in DEPTH,
      "٣ج والغيابُ يُقال في الشاشة لا تُطوى البطاقةُ فيُظنّ أنها لم تُبنَ")

# ── ٤ · ٥ · الصفقاتُ الخاصة ─────────────────────────────────────────────
ROWS = [
    {"symbol": "2010", "companyName": "سابك", "dealPrice": "71.50",
     "quantity": "1,000,000", "dealDate": "2026-09-12"},
    {"symbol": "1120", "price": 88.0, "volume": 250000},      # بلا قيمةٍ ولا تاريخ
    {"symbol": "4030", "price": 0, "quantity": 5000},         # سعرٌ غيرُ موجب
    {"companyName": "بلا رمز", "price": 10.0, "quantity": 100},
    {"symbol": "1010", "price": 30.0},                        # بلا كمّية
]
deals = sd.normalize(ROWS)
check([x["symbol"] for x in deals] == ["2010", "1120"],
      "٤ الصفقةُ بلا رمزٍ أو سعرٍ موجبٍ أو كمّيةٍ ليست صفقةً تُعرض",
      str([x["symbol"] for x in deals]))
check(deals[0]["price"] == 71.5 and deals[0]["quantity"] == 1_000_000.0
      and deals[0]["value"] == 71_500_000.0,
      "٥ والأسماءُ مرشَّحاتٌ تُطابَق، والفاصلةُ لا تكسر الرقم", str(deals[0]))
check("at" not in deals[1] and "name" not in deals[1],
      "٥ب وحقلٌ لم يوجد يغيب — لا يُملأ بفراغٍ ولا بشبيه", str(deals[1]))
check(sd.normalize([{"symbol": "2010", "price": 1, "quantity": 1}] * 500).__len__()
      <= sd.MAX_ROWS, "٥ج وسقفُ الصفوف يُحترَم")

# ── ٦ · يومٌ بلا صفقاتٍ لا يمحو المحفوظ ─────────────────────────────────
from app.services import lastgood  # noqa: E402
lastgood.save(sd.STORE_KEY,
              {"at": _dt2.datetime.now(_dt2.timezone.utc)
                     .isoformat(timespec="seconds"), "deals": deals})
cache.set(sd.STORE_KEY, None, 0)


async def _empty():
    return [], None


sd.fetch_rows = _empty                                           # type: ignore[assignment]
res = asyncio.run(sd.refresh())
check(not res.get("count") and (sd.reading() or {}).get("deals"),
      "٦ ولا يُمحى المحفوظُ حين لا يُفهَم صفّ", str(res)[:60])

# ── ٧ · لا جلبَ في مسار الطلب ────────────────────────────────────────────
calls: list = []


async def _never():
    calls.append(1)
    return [], "ما كان ينبغي أن يُنادى"


sd.fetch_rows = _never                                           # type: ignore[assignment]
out = _data(asyncio.run(M.get_special_deals()))
check(not calls and out.get("available") and out.get("count") == 2,
      "٧ الشاشةُ تقرأ المحفوظَ ولا تُشغّل جلباً خارجياً", f"{len(calls)} نداء")
one = _data(asyncio.run(M.get_special_deals(symbol="2010.SR")))
check(one.get("count") == 1 and one["deals"][0]["symbol"] == "2010",
      "٧ب والتصفيةُ برمز الشركة تعمل مع لاحقة .SR", str(one.get("count")))

SCH = (ROOT / "backend" / "app" / "scheduler"
       / "scheduler.py").read_text(encoding="utf-8")
check("job_special_deals" in SCH and 'id="special_deals"' in SCH,
      "٧ج والجلبُ مجدوَلٌ فعلاً — لا دالّةٌ لا يستدعيها أحد")
# والأيامُ تُقرأ من الوسائط لا من التعليقات: التعليقُ يذكر «sun-thu»
# ليشرح العطب، وذكرُه شرحاً ليس ارتكاباً له.
import re as _re  # noqa: E402
_days = _re.findall(r'day_of_week\s*=\s*"([^"]+)"', SCH)
check(_days and not any("-" in d and d != "mon-fri" for d in _days),
      "٧د ولا مدًى مقلوبٌ في وسائط الأيام — عطبُ D258 لا يعود", str(_days))

# ── ٨ · الطبقةُ الثانيةُ قارئٌ لا عنوانٌ في تعليق ────────────────────────
# سمّيتُ «أرقام» مصدراً ثانياً وتركتُ القارئ — وهو العطبُ الذي نبّه إليه
# المالك: «تجهّز الحلَّ ثمّ تتركه». فيُقاس القارئُ على الشكلين معاً.
TBL = """<table>
 <tr><th>الشركة</th><th>الرمز</th><th>السعر</th><th>الكمية</th><th>التاريخ</th></tr>
 <tr><td>بنك الرياض</td><td>1010</td><td>28.50</td><td>2,000,000</td><td>2026-09-10</td></tr>
 <tr><td>سابك</td><td>2010</td><td>71.20</td><td>450,000</td><td>2026-09-11</td></tr>
 <tr><td>صفٌّ بلا كمّية</td><td>4030</td><td>19.00</td><td>—</td><td>2026-09-11</td></tr>
</table>"""
got = sd.rows_from_html(TBL)
check([d["symbol"] for d in got] == ["1010", "2010"]
      and got[0]["price"] == 28.5 and got[0]["quantity"] == 2_000_000
      and got[0]["value"] == 57_000_000.0,
      "٨ الجدولُ يُقرأ بأركانه الثلاثة، والقيمةُ تُشتقّ", str(got[0]))
check(got[0].get("at") == "2026-09-10" and got[0].get("name") == "بنك الرياض",
      "٨ب والتاريخُ والاسمُ يُقرآن إن وُجدا", str(got[0])[:90])

# وصفُّ الحاويات يحمل تاريخاً كما يحمله صفُّ صفقةٍ حقيقيّ — والشرطُ
# أُضيف في D293 بعد أن اختُلقت صفقاتٌ من كتلٍ بلا تاريخ.
DIV = """<div class="row"><span>1120</span><span>الراجحي</span>
   <span>96.40</span><span>1,250,000</span><span>2026-09-11</span></div>
 <div class="nav"><span>القطاع</span><span>البنوك</span></div>"""
gd = sd.rows_from_html(DIV)
check(len(gd) == 1 and gd[0]["symbol"] == "1120" and gd[0]["quantity"] == 1_250_000,
      "٨ج وبلا جدولٍ تُقرأ الحاويات — و«أرقام» تنشر بلا جدول", str(gd))
check(sd.rows_from_html("<table><tr><td>لا صفقات</td></tr></table>") == [],
      "٨د وصفحةٌ بلا صفقةٍ تعود فارغةً لا مختلَقة")

# والترتيب: «تداول» أوّلاً، و«أرقام» حين تتعثّر — لا العكس.
SRC = (ROOT / "backend" / "app" / "services"
       / "special_deals.py").read_text(encoding="utf-8")
# ══ الترتيبُ انقلب لهذه الشاشة وحدَها بأمر المالك ══ (D288)
# كان هذا الفحصُ يحرس «تداول أوّلاً» — وهي القاعدةُ العامّةُ الباقية في
# كلّ شاشةٍ أخرى. أمّا مسارُ الصفقات الخاصة فقد قِيس محجوباً عند الحافّة
# (‏403 لمتصفّحٍ حقيقيّ)، وأمر المالكُ أن يكون المصدرُ «أرقام». وحارسٌ
# يحرس ترتيباً نُسخ لا ترتيباً مقصوداً يمنع الصواب — فيُقلَب مع القاعدة،
# ويبقى شرطُ **ذكر الطبقتين** كما هو.
check(SRC.index("await argaam_deals(days)") < SRC.index("await fetch_rows()"),
      "٨ه و«أرقام» أوّلاً في هذه الشاشة — والرسميُّ يُجرَّب بعده لا يُنتظَر")
check("إن فُتح المسارُ يوماً عاد الرسميُّ" in SRC,
      "٨ه٢ وسببُ القلب مكتوبٌ — فلا يُقرأ تخلّياً عن قاعدة الطبقات")
check("أرقام:" in SRC,
      "٨و وسببُ التعذّر يذكر الطبقتين معاً — لا واحدةً منهما")

# ── ٩ · «أرقام» مصدرُ الشاشة، والتبويبُ موصولٌ، والنبضُ يتبع السوق ───────
# بأمر المالك: «أضف تبويباً جديداً للسوق باسم صفقات خاصة واجعل مصدرها من
# أرقام»، و«أسعارٌ لحظيةٌ والسوقُ مباشر» (D288).
SRC2 = (ROOT / "backend" / "app" / "services"
        / "special_deals.py").read_text(encoding="utf-8")
check(SRC2.index("await argaam_deals(days)") < SRC2.index("await fetch_rows()"),
      "٩ «أرقام» أوّلُ الطبقات لهذه الشاشة — والمتعثّرُ لا يُقدَّم")
_blk9 = SRC2.split("async def argaam_deals")[1][:2200]
check(_blk9.index("smart_fetch") < _blk9.index("render("),
      "٩ب والقراءةُ الخفيفةُ تُجرَّب قبل المتصفّح — لا كروميومُ بلا حاجة")
check('"source": src' in SRC2,
      "٩ج ويُحفَظ مصدرُ الرقم معه — فتقوله الشاشة")

MP = (ROOT / "frontend" / "src" / "pages" / "MarketPage.tsx").read_text(encoding="utf-8")
check('name: "صفقات خاصة"' in MP and "<SpecialDeals" in MP,
      "٩د والتبويبُ مسجَّلٌ ومركَّبٌ في شاشة السوق — لا مكوّنٌ يتيم")
SD = (ROOT / "frontend" / "src" / "components" / "market"
      / "SpecialDeals.tsx").read_text(encoding="utf-8")
check("لا صفقات خاصة في هذه المدة" in SD,
      "٩ه ويومٌ بلا صفقاتٍ يُقال — لا يُطوى التبويب ولا يُعرض صفرٌ مختلَق")
API2 = (ROOT / "frontend" / "src" / "services" / "api.ts").read_text(encoding="utf-8")
check("/market/special-deals" in API2 and "marketApi.specialDeals(" in SD,
      "٩و والمسارُ له نداءٌ في الواجهة")

# النبضُ يتبع السوق، وبحاكمٍ واحد.
HK = (ROOT / "frontend" / "src" / "hooks" / "useMarketLive.ts").read_text(encoding="utf-8")
check('queryKey: ["server-time"]' in HK,
      "٩ز والطورُ باستعلامٍ واحدٍ مشترَك — لا نداءان لحقيقةٍ واحدة")
# العلاقةُ تُقاس لا الرقمُ: الأرقامُ تُضبَط (‏15ث ← 3ث في D289) والقاعدةُ
# ثابتة — الجلسةُ أسرعُ من قبل الافتتاح، وهو أسرعُ من الإغلاق.
_ms = dict(_re.findall(r"(open|preclose|pre|closed):\s*([\d_*\s]+),", HK))


def _val(k: str) -> float:
    return eval(_ms[k].replace("_", ""))       # noqa: S307 — تعبيرٌ من ملفّنا


check(_val("open") < _val("pre") < _val("closed"),
      "٩ح والنبضُ أسرعُ في الجلسة وأبطأُ في الإغلاق",
      f"جلسة {_val('open'):.0f} · قبل {_val('pre'):.0f} · مغلق {_val('closed'):.0f}")
TK = (ROOT / "frontend" / "src" / "components" / "common"
      / "MarketTicker.tsx").read_text(encoding="utf-8")
check("refetchInterval: liveMs" in TK and "refetchInterval: liveMs" in MP,
      "٩ط والشريطُ وشاشةُ السوق يقرآن النبضَ منه لا رقماً ثابتاً")
check("refetchInterval: 5 * 60 * 1000" not in MP,
      "٩ي ولا مهلةَ خمسِ دقائقَ باقيةٌ لسعرٍ يُسمّى لحظياً")

# ── ١٠ · لا حاشيةَ ولا وسمَ مصدرٍ على الشاشة ────────────────────────────
# بأمر المالك — وقد قالها قبلاً: «لا فوت نوت ولا هيد نوت لكلّ ميزة».
# والميثاقُ نفسُه: «لا حواشي تفسيرية أسفل الشاشات». والشرحُ مكانُه التعليق
# في الشيفرة لا وجهُ التطبيق (D292).
_DEPTH = (ROOT / "frontend" / "src" / "components" / "market"
          / "MarketDepth.tsx").read_text(encoding="utf-8")
_body = _DEPTH.split("*/", 1)[1]            # ما بعد تعليق الرأس
for bad in ("مستوى ${data.levels}", "آخر إغلاق", "data.note", "{data.source}"):
    check(bad not in _body, f"١٠ ولا حاشيةَ في عمق السوق — «{bad}»")
_SD = (ROOT / "frontend" / "src" / "components" / "market"
       / "SpecialDeals.tsx").read_text(encoding="utf-8").split("*/", 1)[1]
for bad in ("{data.source}", "tag-v"):
    check(bad not in _SD, f"١٠ب ولا وسمَ مصدرٍ في الصفقات الخاصة — «{bad}»")
check("لا صفقات خاصة في هذه المدة" in _SD,
      "١٠ج ويبقى إعلانُ الغياب — وهو حالةٌ لا حاشية")

# ── ١١ · الطريقةُ الذكيةُ تُستعمَل لأرقام ───────────────────────────────
_SRC = (ROOT / "backend" / "app" / "services"
        / "special_deals.py").read_text(encoding="utf-8")
check("smart_fetch" in _SRC and "warm=" in _SRC,
      "١١ وجلبُ «أرقام» بالطريقة الذكية مع تسخين موقعه — لا httpx عادية")
_HTTP = (ROOT / "backend" / "app" / "services"
         / "tadawul_http.py").read_text(encoding="utf-8")
check("async def smart_fetch" in _HTTP and _HTTP.count("_IMPERSONATE") >= 2,
      "١١ب والانتحالُ منتِجٌ واحدٌ عامٌّ — لا نسخةٌ لكلّ مصدر")

# ── ١٢ · لا اختلاقَ صفقةٍ من قائمة تنقّل ────────────────────────────────
# قِيس على الخادم: عاد القارئُ بثلاث «صفقات» — «الدخول» (زرُّ الدخول)
# و«الإعلام والترفيه» و«الطاقة» (قطاعات)، برموزٍ 7759 و9615 لا وجودَ لها
# في تاسي. واختلاقٌ يُقرأ قراراً أسوأُ من فراغٍ يُقال (D293).
JUNK = """<div class="menu"><span>الدخول</span><span>7759</span>
   <span>966.00</span><span>92,000</span></div>
 <div class="sec"><span>الإعلام والترفيه</span><span>9615</span>
   <span>9642</span><span>9521</span></div>
 <div class="sec"><span>الطاقة</span><span>2222</span><span>2030</span>
   <span>2380</span></div>"""
check(sd.rows_from_html(JUNK) == [],
      "١٢ كتلُ التنقّل لا تُقرأ صفقاتٍ — الاختلاقُ أسوأُ من الفراغ",
      str(sd.rows_from_html(JUNK))[:80])
check(sd.rows_from_html(TBL) and sd.rows_from_html(TBL)[0]["symbol"] == "1010",
      "١٢ب والجدولُ الحقيقيُّ ما زال يُقرأ — لم يُقتل القارئُ بالحراسة")
# والحرّاسُ يُقاسون بسلوكهم لا بنصِّ شيفرتهم: صياغةٌ تتغيّر والقاعدةُ تبقى.
_GHOST = ("<table><tr><td>شركةٌ غيرُ مدرجة</td><td>7759</td><td>966.00</td>"
          "<td>92,000</td><td>2026-09-10</td></tr></table>")
check(sd.rows_from_html(_GHOST) == [],
      "١٢ج والرمزُ يُطابَق برموز السوق — لا أيُّ أربعةِ أرقام",
      str(sd.rows_from_html(_GHOST))[:80])
_NODATE = ("<table><tr><td>بنك الرياض</td><td>1010</td><td>28.50</td>"
           "<td>2,000,000</td></tr></table>")
check(sd.rows_from_html(_NODATE) == [],
      "١٢د وصفقةٌ بلا تاريخٍ ليست صفقة", str(sd.rows_from_html(_NODATE))[:80])
check(len(sd.rows_from_html(_NODATE, at="2026-09-10")) == 1,
      "١٢ذ وتاريخُ المقالة يكفي حين أفصح عنه المصدر — لا ساعتُنا")
_NAVROW = ("<table><tr><td>تسجيل الدخول</td><td>1010</td><td>28.50</td>"
           "<td>2,000,000</td><td>2026-09-10</td></tr></table>")
check(sd.rows_from_html(_NAVROW) == [],
      "١٢ه وكلماتُ الواجهة تُستبعَد بأسمائها", str(sd.rows_from_html(_NAVROW))[:80])
_no_date = TBL.replace("<td>2026-09-10</td>", "<td></td>")
check(all(d["symbol"] != "1010" for d in sd.rows_from_html(_no_date)),
      "١٢و وصفٌّ فقد تاريخَه يسقط — الشرطُ يعمل لا يُكتَب")

# ── ١٣ · سجلٌّ بمدًى، وصيغةٌ يجدها التطبيقُ بنفسه ───────────────────────
# قال المالك: «توجد صفقاتٌ في أرقام، وليس شرطاً أن تكون لحظية — سجلُّ
# عملياتٍ بالتاريخ أسبوعيٌّ وشهريٌّ مثل المفكرة». وكلمةُ **history** في
# اسم المسار كانت تقولها، وكنتُ أطلب الصفحةَ **بلا مدى تاريخٍ** (D295).
_vs = sd._variants(30)
check(len(_vs) >= 5 and any("fromdate" in str(v.get("data") or v.get("params"))
                            for v in _vs),
      "١٣ الصيغُ تحمل مدى تاريخٍ حقيقياً — لا طلبٌ بلا تاريخ", f"{len(_vs)} صيغة")
check(any(v["method"] == "POST" and v.get("headers") for v in _vs),
      "١٣ب ومنها نداءُ جافاسكربت — القشرةُ لا تُعطي صفوفَها لطلبٍ عاديّ")
_names = [v["name"] for v in _vs]
check(len(_names) == len(set(_names)), "١٣ج ولكلّ صيغةٍ اسمٌ يُسجَّل في المحاولة")

# والمدى يُصفّي السجلَّ: ما خرج عنه لا يُعرض، وما لا تاريخَ له لا يُحذف بالظنّ.
_rows = [{"symbol": "1010", "price": 28.5, "quantity": 1000, "value": 28500,
          "at": _dt2.date.today().isoformat()},
         {"symbol": "2010", "price": 70.0, "quantity": 500, "value": 35000,
          "at": (_dt2.date.today() - _dt2.timedelta(days=20)).isoformat()},
         {"symbol": "1120", "price": 96.0, "quantity": 800, "value": 76800,
          "at": (_dt2.date.today() - _dt2.timedelta(days=200)).isoformat()},
         {"symbol": "4030", "price": 19.0, "quantity": 100, "value": 1900}]
check([d["symbol"] for d in sd.within(_rows, 7)] == ["1010", "4030"],
      "١٣د والأسبوعيُّ أسبوعيّ", str([d["symbol"] for d in sd.within(_rows, 7)]))
check([d["symbol"] for d in sd.within(_rows, 30)] == ["1010", "2010", "4030"],
      "١٣ه والشهريُّ شهريّ", str([d["symbol"] for d in sd.within(_rows, 30)]))
check("4030" in [d["symbol"] for d in sd.within(_rows, 7)],
      "١٣و وصفقةٌ بلا تاريخٍ مقروءٍ تبقى — لا تُحذف بالظنّ")

_SDS = (ROOT / "frontend" / "src" / "components" / "market"
        / "SpecialDeals.tsx").read_text(encoding="utf-8")
check('{ days: 7, label: "أسبوعي" }' in _SDS and '{ days: 30, label: "شهري" }' in _SDS,
      "١٣ز والخيارانِ في الشاشة: أسبوعيٌّ وشهريّ")
_API3 = (ROOT / "frontend" / "src" / "services" / "api.ts").read_text(encoding="utf-8")
check("special-deals?days=" in _API3, "١٣ح والمدى يُمرَّر في النداء")
_SD2 = (ROOT / "backend" / "app" / "services"
        / "special_deals.py").read_text(encoding="utf-8")
check("lastgood.save(SHAPE_KEY" in _SD2,
      "١٣ط والصيغةُ الناجحةُ تُحفَظ فتُجرَّب أوّلاً — القياسُ في الخدمة لا في طرفيّة المالك")
check(_SD2.count("async def argaam_deals") == 1,
      "١٣ي ودالّةٌ واحدةٌ لا نسختان — الأخيرةُ تغلب الأولى بصمت")

# ── ١٤ · اقرأ كيف ينشر المصدرُ، واجلبها مثله ────────────────────────────
# قال المالك: «انظر أوّلاً لأرقام كيف يجلبها واجلبها مثله» (D296). وكنتُ
# أطرق مسارَ صفقاتِ كبار الملّاك بصيغِ نداءٍ مخترَعة، و«أرقام» تنشر
# الصفقاتَ الخاصة **مقالةً مؤرَّخةً لكلّ جلسة** تحت وسمِ موضوع.
_TAG_ART = ('<meta property="article:published_time" '
            'content="{d}T12:00:00+03:00"/>'
            '<table><tr><th>الشركة</th><th>الكمية</th><th>السعر</th>'
            '<th>القيمة</th></tr>'
            '<tr><td>{n}</td><td>{q}</td><td>{p}</td><td>{v}</td></tr></table>')

# ١٤ · جلسةٌ واحدةٌ للخطّة — وهذا ما يفصل «قراءةَ صفحة» عن «قراءةِ موقع»:
# الكوكيزُ التي تُعطيها الصفحةُ يحملها النداءُ التالي، كما يفعل المتصفّح.
def _one_session() -> tuple:
    import http.server
    import socketserver
    import threading

    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):                                # noqa: D102
            pass

        def do_GET(self):                                         # noqa: N802
            if self.path == "/page":
                self.send_response(200)
                self.send_header("Set-Cookie", "sp_guard=abc; Path=/")
                self.end_headers()
                self.wfile.write(b"<html>ok</html>")
                return
            ok = "sp_guard=abc" in (self.headers.get("Cookie") or "")
            self.send_response(200 if ok else 403)
            self.end_headers()
            self.wfile.write(b"ROWS" if ok else b"NOCOOKIE")

    srv = socketserver.TCPServer(("127.0.0.1", 0), H)
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        from app.services.tadawul_http import smart_fetch, smart_flow

        def plan():
            yield {"url": base + "/page"}
            s2, b2 = yield {"url": base + "/data", "referer": base + "/page"}
            return s2, b2

        flow = asyncio.run(smart_flow(plan))

        async def apart():
            await smart_fetch(base + "/page")
            return await smart_fetch(base + "/data")
        return flow, asyncio.run(apart())
    finally:
        srv.shutdown()


_flow, _apart = _one_session()
check(_flow[0] == 200 and _flow[1] == "ROWS",
      "١٤ خطّةُ الجلب في جلسةٍ واحدة: كوكيزُ الصفحة تحملها نداءاتُها",
      f"{_flow[0]}/{_flow[1]}")
check(_apart[0] == 403,
      "١٤ب والنداءُ المنفصلُ يُردّ — فالعطبُ كان بنيوياً لا في المعاملات",
      f"{_apart[0]}")

# ١٤ج · الفهرسُ يُكتشف من قائمة «أرقام» نفسِها — لا مسارٌ مثبَّتٌ وحدَه
check(sd._index_from_nav(
    '<li id="mnu_x"><a href="/ar/tags/id/24779/1/t">الصفقات الخاصة</a></li>')
    == "https://www.argaam.com/ar/tags/id/24779/1/t",
    "١٤ج والفهرسُ من قائمة المصدر نفسِه")
check(len(sd._index_pages("https://www.argaam.com/ar/tags/id/24779/1/t")) > 1,
      "١٤د وترقيمُ الفهرس بترقيم المصدر")

# ١٤ه · مقالاتُ الصفقات وحدَها تُتبَع — لا كلُّ ما في الفهرس
_lnk = sd._index_links(
    '<a href="/ar/article/articledetail/id/1">تاسي: 7 صفقات خاصة بقيمة 157 مليوناً</a>'
    '<a href="/ar/article/articledetail/id/2">تاسي: الأسهم الأنشط من حيث القيمة</a>')
check(len(_lnk) == 1 and _lnk[0][0].endswith("/id/1"),
      "١٤ه ومقالاتُ الصفقات وحدَها تُتبَع", f"{len(_lnk)} رابطاً")

# ١٤و · صفوفُ المقالة تحمل **تاريخَ نشرها** — لا تاريخَ ساعتنا
_today = _dt2.date.today().isoformat()
_art = _TAG_ART.format(d=_today, n="الراجحي", q="1,000,000", p="92.50",
                       v="92,500,000")
check(sd._article_date(_art) == _dt2.date.today(),
      "١٤و وتاريخُ المقالة من إفصاحها")
_got = sd.rows_from_html(_art, at=_today)
check(len(_got) == 1 and _got[0]["symbol"] == "1120"
      and _got[0]["at"] == _today and _got[0]["quantity"] == 1_000_000,
      "١٤ز والاسمُ القصيرُ يُحلّ رمزاً — «أرقام» لا تكتب رمزَ تاسي",
      str(_got))

# ١٤ح · وترتيبُ الأعمدة ليس عهداً: الكمّيةُ يُصدّقها عمودُ القيمة
_rev = ('<table><tr><td>الراجحي</td><td>92,500,000</td><td>92.50</td>'
        '<td>1,000,000</td></tr></table>')
_r2 = sd.rows_from_html(_rev, at=_today)
check(len(_r2) == 1 and _r2[0]["quantity"] == 1_000_000,
      "١٤ح والكمّيةُ يُصدّقها حاصلُ الضرب لا ترتيبُ العمود", str(_r2))

# ١٤ط · ونصُّ المقالة لا يُحصَد: بلا جدولٍ لا صفقةَ — حارسُ D293 باقٍ
check(sd.rows_from_html(
    '<div>الراجحي 92.50 ريال بكمية 1,000,000 سهم</div>'
    '<div>قطاع الطاقة 2222 الإعلام 9615</div>', at=_today) == [],
    "١٤ط ونصٌّ بلا جدولٍ لا يُقرأ صفقات — لا اختلاقَ من فقرة")
check(sd._by_name(["شركةٌ لا وجودَ لها في السوق"]) is None,
      "١٤ي واسمٌ لا يُطابق شركةً يُترك — لا أقربُ شبيه")

# ١٤ك٢ · ورابطٌ يُقرأ من صفحةٍ يُفَكُّ ترميزُه قبل طلبه ─────────────────
# قِيس على خادم المالك: قائمةُ «أرقام» تكتب `?marketid=3&amp;pageno=1`،
# فطُلب الرابطُ بحرفيّته فردّ المصدرُ **403** — وقرأتُ الردَّ حجباً وبنيتُ
# عليه أن المسارَ خطأ (D303).
_NAV_AMP = ('<li id="mnu_x"><a href="/ar/shareholder/shareholders-history-deals'
            '?marketid=3&amp;pageno=1">الصفقات الخاصة</a></li>')
_u = sd._index_from_nav(_NAV_AMP)
check(_u is not None and "&amp;" not in _u and _u.endswith("&pageno=1"),
      "١٤ك٢ ورابطُ القائمة يُفَكُّ ترميزُه — `&amp;` ليست `&`", str(_u))
_lnk2 = sd._index_links(
    '<a href="/ar/article/articledetail/id/9?a=1&amp;b=2">تاسي: صفقات خاصة</a>')
check(_lnk2 and "&amp;" not in _lnk2[0][0],
      "١٤ك٣ وكذلك روابطُ المقالات", str(_lnk2[:1]))

# ١٤ك · والقارئُ يستعمل الخطّة فعلاً — لا نداءين منفصلين كما كان
check("smart_flow" in _SD2 and "_argaam_plan" in _SD2,
      "١٤ك والصفقاتُ تُقرأ بخطّةٍ في جلسةٍ واحدة")
check(_SD2.count("def _argaam_plan") == 1 and _SD2.count("def rows_from_html") == 1,
      "١٤ل ودالّةٌ واحدةٌ لكلّ معنى — لا نسختان تتنازعان")

# ── ١٥ · اكتشافُ النقطة من حركة الشبكة ─────────────────────────────────
# قِيس على الخادم أن صفحةَ الصفقات الخاصة في بوّابة «تداول» **لا تذكر اسمَ
# خدمتها في شيفرتها** (صفرُ أسماء `=NJ…=/`)، وأن صفحةَ «أرقام» مغلقةٌ على
# غير المشترك. فالاسمُ يُقرأ من **ما تطلبه الصفحةُ فعلاً** (D306).
def _sniff_probe() -> tuple[int, str]:
    import http.server
    import socketserver
    import threading

    for c in ("/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
              "/usr/bin/chromium", "/usr/bin/chromium-browser"):
        if _os.path.exists(c):
            _os.environ.setdefault("CHROME_BIN", c)
            break

    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):                                # noqa: D102
            pass

        def do_GET(self):                                         # noqa: N802
            if self.path == "/page":
                # اسمٌ **لا يطابق** مرشِّح الأسماء — كما وقع على الخادم
                # (‏RefreshTradeDetailsServlet · TickerServlet · D307).
                b = (b"<html><body><script>"
                     b"fetch('/RefreshTradeDetailsServlet');"
                     b"</script></body></html>")
                ct = "text/html; charset=utf-8"
            elif self.path.startswith("/RefreshTradeDetails"):
                b = b'{"deals":[{"symbol":"1120","price":92.5}]}'
                ct = "application/json"
            else:
                self.send_response(404)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", ct)
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

    srv = socketserver.TCPServer(("127.0.0.1", 0), H)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        from app.services.browser_fetch import BrowserUnavailable, sniff
        try:
            res = asyncio.run(sniff(f"http://127.0.0.1:{port}/page",
                                    settle_ms=2000, hosts=("127.0.0.1",),
                                    max_bodies=12))
        except BrowserUnavailable as e:
            return -1, str(e)[:60]
        xhr = [c for c in res["calls"] if c["type"] in ("xhr", "fetch")]
        body = next(iter(res["bodies"].values()), "")
        return len(xhr), body[:60]
    finally:
        srv.shutdown()


_n, _b = _sniff_probe()
if _n < 0:
    print(f"…  اكتشافُ النقطة بالشبكة لا يُقاس هنا (المتصفّح: {_b}) — لا حكم.")
else:
    check(_n >= 1, "١٥ المتصفّحُ يسجّل نداءَ البيانات الذي تطلبه الصفحة",
          f"{_n} نداءً")
    check('"symbol"' in _b or "1120" in _b,
          "١٥ب ويُحفَظ جسمُ الردّ **بمضيف المصدر** لا بمرشِّح اسمٍ يُسقطه",
          _b[:40])
check("sniff" in (ROOT / "scripts" / "audit" / "deals_probe.py")
      .read_text(encoding="utf-8"),
      "١٥ج والمسبارُ يستعمله فيطبع ما طلبته الصفحةُ فعلاً")

# ── ١٦ · بابُ «تداول» العامّ يُنادى كما تناديه صفحتُه ──────────────────
# ظهر البابُ بتسجيل الشبكة على خادم المالك: صفحةُ الصفقات الخاصة تنادي
# `RefreshTradeDetailsServlet` وتعود بـ٢٩ ألفَ حرف (D310). وشكلُ الجسم لم
# يُقَس، فيُقبَل الشكلان — ويُقاس الاثنان هنا بخادمٍ محليّ.
# والمسارُ يُكتشف من القائمة: قِيس أن المحفوظَ يُصرَف إلى صفحةٍ أخرى (D311).
check(sd.td_page_from_nav(
    '<a href="/wps/portal/x/!ut/p/z1/ABC/deals?a=1&amp;b=2">الصفقات الخاصة</a>')
    == "https://www.saudiexchange.sa/wps/portal/x/!ut/p/z1/ABC/deals?a=1&b=2",
    "١٦ه ورابطُ «تداول» من قائمتها، مفكوكَ الترميز")
check(sd.td_page_from_nav("<a href='/x'>شيءٌ آخر</a>") is None,
      "١٦و ولا يُلتقط رابطٌ لا يحمل اسمَ الميزة")
check(sd.td_base("<base href='https://x/wps/portal/a/!ut/p/z1/Q/'>")
      == "https://x/wps/portal/a/!ut/p/z1/Q",
      "١٦ز وأساسُ الصفحة يُقرأ منها")


def _td_layer(mode: str) -> tuple[int, str]:
    """الطبقةُ كما تعمل حقّاً: قائمةٌ ← صفحةٌ ← (جدولُها أو خدمتُها).

    والحالتان مقيستان بشكلهما الحقيقيّ: صفحةٌ يرسم خادمُها الجدول، أو
    قشرةٌ فيها اسمُ خدمةٍ تُنادى فتعود JSON. (أوّلُ صياغةٍ جعلت الصفحةَ
    نفسَها JSON — وهذا لا يقع في بوّابةٍ تُخدَم HTML.)
    """
    import http.server
    import json as _j
    import socketserver
    import threading

    pay = {"data": [{"symbol": "1120", "companyName": "الراجحي", "price": 92.5,
                     "quantity": 1000000, "value": 92500000,
                     "tradeDate": "2026-09-14"}]}
    htm = ("<table><tr><td>بنك الرياض</td><td>1010</td><td>28.50</td>"
           "<td>2,000,000</td><td>2026-09-14</td></tr></table>")

    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):                                # noqa: D102
            pass

        def do_GET(self):                                         # noqa: N802
            port = self.server.server_address[1]
            if self.path.endswith("/home"):
                b = '<a href="/page">الصفقات الخاصة</a>'.encode()
            elif "=NJ" in self.path:
                b = _j.dumps(pay).encode()
            elif mode == "service":
                b = (f"<html><base href='http://127.0.0.1:{port}/b/'>"
                     "<a href='/b/p0/z1=NJgetNegotiatedDeals=/'>x</a>"
                     "</html>").encode()
            else:
                b = (f"<html><base href='http://127.0.0.1:{port}/b/'>"
                     + htm + "</html>").encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

    srv = socketserver.TCPServer(("127.0.0.1", 0), H)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    page, home = sd.PAGE, sd.TD_HOME
    sd.TD_HOME = f"http://127.0.0.1:{port}/home"
    sd.PAGE = f"http://127.0.0.1:{port}/page"
    try:
        deals, why = asyncio.run(sd.tadawul_trade_details())
        return len(deals), (deals[0]["symbol"] if deals else (why or "")[:70])
    finally:
        sd.PAGE, sd.TD_HOME = page, home
        srv.shutdown()


_nj, _sj = _td_layer("service")
check(_nj == 1 and _sj == "1120",
      "١٦ قشرةٌ ⇒ تُنادى خدمتُها المسمّاةُ في الصفحة فتُقرأ صفوفُها",
      f"{_nj}/{_sj}")
_nh, _sh = _td_layer("table")
check(_nh == 1 and _sh == "1010",
      "١٦ب وجدولٌ يرسمه الخادمُ يُقرأ بلا نداءٍ ثانٍ", f"{_nh}/{_sh}")
check("RefreshTradeDetailsServlet" in _SD2 or "TD_HELPER" in _SD2,
      "١٦ج والبابُ مكتوبٌ كما قِيس لا كما خُمِّن")
check("await smart_flow" in _SD2,
      "١٦د ويُنادى بجلسةٍ واحدةٍ تُسخَّن بصفحته — كما تناديه الصفحة")

# ── ١٧ · «الصفقات المتفاوض عليها»: البابُ المقيسُ يُقرأ ────────────────
# وُجد بالتصفّح على خادم المالك (D314…D317): اسمُ الميزة في «تداول»
# «الصفقات المتفاوض عليها»، وصفحتُها لكلّ سوقٍ بالنمط
# `ourmarkets/<السوق>-market-watch/issuers-trading-information`، وخدمتُها
# `getNegotiatedDetails` تردّ بمدى تاريخٍ (D318). ويُقاس هنا على **الجسم
# كما وصل بالحرف** — لا على شكلٍ صنعتُه.
def _neg(payload: dict, market: str = "main") -> tuple[int, dict, str]:
    import http.server
    import json as _j
    import socketserver
    import threading

    got_qs: dict = {}
    page = ('<html><head><base href="http://127.0.0.1:{p}/wps/portal/x/!ut/p/z1/A/">'
            '</head><body><a href="/wps/portal/x/p0/IZ7=CZ6=NJgetNegotiatedDetails=/">'
            'x</a></body></html>')

    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):                                # noqa: D102
            pass

        def do_GET(self):                                         # noqa: N802
            port = self.server.server_address[1]
            if "=NJ" in self.path:
                from urllib.parse import parse_qs, urlsplit
                got_qs.update({k: v[0] for k, v in
                               parse_qs(urlsplit(self.path).query).items()})
                b = _j.dumps(payload, ensure_ascii=False).encode()
                ct = "application/json"
            else:
                b, ct = page.format(p=port).encode(), "text/html; charset=utf-8"
            self.send_response(200)
            self.send_header("Content-Type", ct)
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

    srv = socketserver.TCPServer(("127.0.0.1", 0), H)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    keep = sd.NEG_PAGE
    sd.NEG_PAGE = f"http://127.0.0.1:{port}/{{market}}-page"
    try:
        deals, why = asyncio.run(sd.tadawul_negotiated(30, markets=(market,)))
        return len(deals), (deals[0] if deals else {"why": why}), str(got_qs)
    finally:
        sd.NEG_PAGE = keep
        srv.shutdown()


_REAL = {"data": [
    {"company": "المجموعة السعودية", "tradePrice": 11.62,
     "tradeVolume": 395000, "tradeVolumeLong": 0, "turnOver": 4589900,
     "strTime": "14:13:11", "strDate": "15-09-2026", "symbol": "2250",
     "companyURL": "/wps/portal/x"}]}
_n, _d, _qs = _neg(_REAL)
check(_n == 1 and _d.get("symbol") == "2250" and _d.get("price") == 11.62
      and _d.get("quantity") == 395000 and _d.get("value") == 4589900,
      "١٧ جسمُ «getNegotiatedDetails» يُقرأ بحقوله كما وصلت",
      json.dumps(_d, ensure_ascii=False)[:120])
check(_d.get("at") == "15-09-2026" and _d.get("time") == "14:13:11",
      "١٧ب والتاريخُ والوقتُ من المصدر لا من ساعتنا",
      f"{_d.get('at')} · {_d.get('time')}")
check("fromDate" in _qs and "toDate" in _qs and "sector" in _qs
      and "requestLocale" in _qs,
      "١٧ج ويُنادى بمعاملات الصفحة نفسِها (مدًى وقطاعٌ ولغة)", _qs[:110])
_n0, _d0, _ = _neg({"data": []})
check(_n0 == 0 and "why" in _d0,
      "١٧د ويومٌ بلا صفقاتٍ يُقال سببَه ولا يُخترع صفّ", str(_d0)[:90])
_bad, _db, _ = _neg({"data": [{"company": "شركةٌ", "strDate": "15-09-2026"}]})
check(_bad == 0,
      "١٧ه وصفٌّ بلا سعرٍ ولا كمّيةٍ يُترك — لا نصفُ صفقة")

print(("FAIL" if fail else "PASS") + " D272 · D273 — العمقُ يُعرَض، والصفقاتُ الخاصة تُبنى")
raise SystemExit(fail)
