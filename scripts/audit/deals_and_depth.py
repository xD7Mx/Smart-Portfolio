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
    cache.set(tm.STORE_KEY, {"at": "2026-09-12T12:00:00+00:00", "rows": rows},
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
lastgood.save(sd.STORE_KEY, {"at": "2026-09-12T10:00:00+00:00", "deals": deals})
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

DIV = """<div class="row"><span>1120</span><span>الراجحي</span>
   <span>96.40</span><span>1,250,000</span></div>
 <div class="nav"><span>القطاع</span><span>البنوك</span></div>"""
gd = sd.rows_from_html(DIV)
check(len(gd) == 1 and gd[0]["symbol"] == "1120" and gd[0]["quantity"] == 1_250_000,
      "٨ج وبلا جدولٍ تُقرأ الحاويات — و«أرقام» تنشر بلا جدول", str(gd))
check(sd.rows_from_html("<table><tr><td>لا صفقات</td></tr></table>") == [],
      "٨د وصفحةٌ بلا صفقةٍ تعود فارغةً لا مختلَقة")

# والترتيب: «تداول» أوّلاً، و«أرقام» حين تتعثّر — لا العكس.
SRC = (ROOT / "backend" / "app" / "services"
       / "special_deals.py").read_text(encoding="utf-8")
check(SRC.index("await fetch_rows()") < SRC.index("await argaam_deals()"),
      "٨ه والرسميُّ أوّلاً، و«أرقام» حين يتعثّر — لا العكس")
check("أرقام:" in SRC,
      "٨و وسببُ التعذّر يذكر الطبقتين معاً — لا واحدةً منهما")

print(("FAIL" if fail else "PASS") + " D272 · D273 — العمقُ يُعرَض، والصفقاتُ الخاصة تُبنى")
raise SystemExit(fail)
