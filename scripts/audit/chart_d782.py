#!/usr/bin/env python3
"""حارسُ D782 — لوحتا الاتجاه والسيولة، و«تحليلُ الرسم»، والأحداثُ بالعربية وللسوق السعودي، والسعرُ الأسرع، والقوائمُ القابلةُ للتعديل (2026-11-21).

قال المالك: «نحن في الأسهم نحتاج نعرف حاجتين: الاتجاه والسيولة… لوحتان… وداخل الرسم زرُّ تحليل الرسم: الذكاءُ يقرأ الرسمَ ومؤشّراتِه ومستوياتِه
ويعرف متى البيعُ ومتى الشراء… والأحداثُ بالعربية وتدعم السوقين… والإطاراتُ أكثرُ ثلاثةٍ استخداماً… ومختصرُ والكلّ داخل D7M… وملتي سكرين…
والسعرُ تفاعليٌّ مباشر… والمؤشّراتُ بأسعارها وقابلةٌ للتعديل… وترسٌ يُظهر القوائمَ ويُخفيها ويقسمها قسمين».
وهذا يحرس الخادمَ والأوصال؛ والسلوكُ في المتصفّح يقيسه ‏chart_d782.mjs، والحسابُ ‏pulse_d782.mjs.

    python3 scripts/audit/chart_d782.py
"""
import asyncio, os, pathlib, sys, tempfile   # noqa: E401
_SB = tempfile.mkdtemp()
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
fail = 0


def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))


from app.services import chart_read as CR   # noqa: E402
from app.services import econ_calendar as EC   # noqa: E402
from app.services import live_quote as LQ   # noqa: E402

# ١ حراسةُ القراءة: المستوى برقم اللقطة وإلّا سقط، والجملةُ برقمٍ لا أصلَ له تسقط، ولا مؤشّرَ إلّا ما ظهر
bars = [[f"2026-11-{d:02d}", 100 + d, 101 + d, 99 + d, 100.5 + d, 1e6] for d in range(1, 31)]
snap = {"symbol": "NVDA", "frames": [{"tf": "1d", "tf_ar": "يوم", "price": 130.5, "bars": bars, "shown": ["d7m", "stochrsi", "volume"],
        "ind": {"Stoch RSI": {"k": 91.3, "d": 84.2, "overbought": 80, "oversold": 20}},
        "levels": [{"kind": "fib", "label": "فيبوناتشي 0", "price": 131.0}, {"kind": "ema", "label": "EMA 50", "price": 118.25}],
        "img": "data:image/jpeg;base64,/9j/AAAA"}]}
obj = {"bias": "صاعد", "headline": "السعرُ عند مقاومة 131.0 وStoch RSI في تشبّعٍ شرائيٍّ (91.3)",
       "frames": [{"tf": "يوم", "reading": "صاعدٌ فوق EMA 50 عند 118.25"}],
       "levels": [{"kind": "مقاومة", "price": 131.02, "from": "فيبوناتشي 0", "note": "قمّةُ الموجة"}, {"kind": "دعم", "price": 125.0, "from": "مختلَق"},
                  {"kind": "دعم", "price": 118.25, "from": "EMA 50", "note": "دعمٌ عند 117"}],
       "indicators": [{"name": "Stoch RSI", "reading": "في تشبّعٍ شرائيٍّ فوق 80"}, {"name": "MACD", "reading": "تقاطعٌ صاعد"}],
       "buy": "إن ارتدّ من 118.25 مع تشبّعٍ بيعيّ", "sell": "إن أغلق تحت 112.4 فالخروج", "invalid": "إغلاقٌ فوق 131.0 بحجمٍ عالٍ", "risk": "تشبّعٌ شرائيّ"}
v = CR.validate(obj, snap)
check(v["bias"] == "صاعد" and v["headline"] and [(x["kind"], x["price"]) for x in v["levels"]] == [("مقاومة", 131.0), ("دعم", 118.25)]
      and v["levels"][1]["note"] == "" and [x["name"] for x in v["indicators"]] == ["Stoch RSI"] and v["sell"] is None and v["buy"] and v["invalid"]
      and v["dropped"] >= 3,
      "١ القراءةُ محروسة: المستوى يُكتب برقم اللقطة (131.02 ⇐ 131.0) وما لا أصلَ له يسقط (125)، والجملةُ برقمٍ مختلَق تسقط كلُّها (112.4 · 117)، "
      "ولا يُقرأ مؤشّرٌ لم يظهر على الرسم (MACD)", f"{[(x['kind'], x['price']) for x in v['levels']]} · أُسقط {v['dropped']}")
check(81 not in CR.known_numbers({"frames": [{"img": "data:81", "bars": []}]}) and CR.fingerprint(snap) == CR.fingerprint(dict(snap))
      and CR.clean_text("على إطار 4 ساعات", []) == "على إطار 4 ساعات",
      "٢ الصورةُ لا تُعدّ مصدرَ أرقام، والبصمةُ ثابتةٌ للّقطة نفسِها (تُخبَّأ القراءةُ ثلاثَ دقائق)، والأعدادُ الصغيرة (إطارُ «4 ساعات») ليست أسعاراً")

# ٣ النموذجُ لا يُنادى بلا مفتاح، فلا قراءةَ مختلَقة: ‏ok=False
RD_calls = []


async def fake_gemini(parts, max_tokens, temperature=0.1):
    RD_calls.append(parts)
    return None
from app.services import research_desk as RD   # noqa: E402
RD._gemini = fake_gemini
r = asyncio.run(CR.read(snap))
img_sent = any("inline_data" in p for p in (RD_calls[0] if RD_calls else []))
check(r["ok"] is False and "reading" not in r and img_sent and "لا تذكر رقماً ليس في اللقطة" in CR.PROMPT,
      "٣ الصورةُ تُرسل مع الأرقام، وإن تعذّر النموذجُ قيل «تعذّر» — لا قراءةَ بديلةٌ مختلَقة")

# ٤ الأحداث: عربيةٌ من القاموس، وللسوق السعودي ما يحرّكه (الفيدراليّ العالي · النفط · الصين العالية) لا كلُّ حدثٍ أمريكيّ
from datetime import datetime, timezone   # noqa: E402
items = [{"title": "FOMC Meeting Minutes", "country": "USD", "date": "2026-11-25T14:00:00-05:00", "impact": "High", "forecast": "", "previous": ""},
         {"title": "Crude Oil Inventories", "country": "USD", "date": "2026-11-25T10:30:00-05:00", "impact": "Medium", "forecast": "-1.2M", "previous": "2.1M"},
         {"title": "Retail Sales m/m", "country": "USD", "date": "2026-11-25T08:30:00-05:00", "impact": "Medium", "forecast": "0.3%", "previous": "0.2%"},
         {"title": "Caixin Manufacturing PMI", "country": "CNY", "date": "2026-11-25T20:45:00-05:00", "impact": "High", "forecast": "", "previous": ""},
         {"title": "FOMC Member Waller Speaks", "country": "USD", "date": "2026-11-25T12:00:00-05:00", "impact": "Medium", "forecast": "", "previous": ""},
         {"title": "German ifo Business Climate", "country": "EUR", "date": "2026-11-25T04:00:00-05:00", "impact": "High", "forecast": "", "previous": ""}]
now = datetime(2026, 11, 25, 6, 0, tzinfo=timezone.utc)
us, sa = EC.shape(items, now=now), EC.shape(items, now=now, market="sa")
check([e["title"] for e in us] == ["Retail Sales m/m", "Crude Oil Inventories", "FOMC Member Waller Speaks", "FOMC Meeting Minutes"]
      and [e["title"] for e in sa] == ["Crude Oil Inventories", "FOMC Meeting Minutes", "Caixin Manufacturing PMI"]
      and all(e["ar"] for e in us + sa) and sa[2]["ar"].startswith("الصين — ") and us[2]["ar"] == "كلمةُ عضوٍ في الفيدرالي",
      "٤ لكلّ حدثٍ اسمُه العربيُّ من قاموسٍ ثابت (لا ينتظر النموذج)، وللسوق السعودي ما يحرّكه: الفيدراليُّ العالي والنفطُ والصينُ العالية — "
      "لا مبيعاتُ التجزئة المتوسّطة ولا ألمانيا", f"{[e['ar'] for e in sa]}")


async def fake_raw():
    return items


async def fake_an(ev, market="us"):
    return {e["id"]: {"ar": "اسمُ النموذج", "what": "x", "above": "a", "below": "b", "above_lean": "pos" if market == "sa" else "put", "below_lean": "neg"} for e in ev}


async def fake_co(sym, name="", now=None):
    return [{"date": "2026-11-30", "title": "أحقّيةُ توزيعٍ نقديّ", "kind": "توزيع"}] if sym == "2222.SR" else []
EC.raw_week, EC.analysis, EC.company_events = fake_raw, fake_an, fake_co
w_sa = asyncio.run(EC.week(market="sa", symbol="2222.SR", name="أرامكو"))
w_us = asyncio.run(EC.week())
check(w_sa["market"] == "sa" and w_sa["company"] and w_sa["events"][1]["ar"] == "محضرُ اجتماع الفيدرالي" and w_sa["events"][1]["above_lean"] == "pos"
      and w_us["company"] == [] and w_us["market"] == "us" and "READ_SA" in dir(EC) and "الريالُ مربوطٌ بالدولار" in EC.READ_SA,
      "٥ القراءةُ السعوديّةُ بقراءة السوق السعودي (إيجابيّ · سلبيّ) ومعها أحداثُ الشركة المفتوحة — والاسمُ من القاموس يتقدّم على تسمية النموذج",
      f"{w_sa['events'][1]['ar']} · {w_sa['company']}")

# ٦ السعرُ الأسرع: ثانيتان للسهم الأمريكيّ المباشر في الجلسة الرسمية ما دامت الحصّةُ فوق ثلثها — وإلّا أربع
from app.services import usage_tracker as UT   # noqa: E402
UT.remaining_fraction = lambda p: 0.9
fast = (LQ.ttl_for("NVDA", "open", "ياهو"), LQ.ttl_for("2222.SR", "open", "ياهو"), LQ.ttl_for("NVDA", "post", "ياهو"), LQ.ttl_for("NVDA", "open", "TradingView"))
UT.remaining_fraction = lambda p: 0.2
low = LQ.ttl_for("NVDA", "open", "ياهو")
check(fast == (2, 4, 4, 4) and low == 4,
      "٦ السعرُ الأمريكيُّ المباشرُ يتجدّد كلَّ ثانيتين في الجلسة الرسمية (والواجهةُ تسأل كذلك)، ويعود أربعاً إن نقصت الحصّةُ عن ثلثها — لا يسقط إلى المؤجّل",
      f"{fast} · {low}")

# ٧ الأوصال: النقطتان، والمؤشّراتُ قائمةٌ على الخادم تُزرع مرّةً، والواجهة
mk = (ROOT / "backend/app/api/v1/endpoints/market.py").read_text(encoding="utf-8")
tr = (ROOT / "frontend/src/components/market/TradeRoom.tsx").read_text(encoding="utf-8")
pc = (ROOT / "frontend/src/components/chart/ProChart.tsx").read_text(encoding="utf-8")
lq = (ROOT / "frontend/src/components/chart/LiveQuote.tsx").read_text(encoding="utf-8")
pn = (ROOT / "frontend/src/components/analysis/D7MPanel.tsx").read_text(encoding="utf-8")
check('@router.post("/chart-read")' in mk and "len(img) <= 900_000" in mk and "(p.get(\"frames\") or [])[:4]" in mk
      and "async def econ_events(market: str = \"us\", symbol: str = \"\", name: str = \"\")" in mk,
      "٧ نقطةُ «تحليل الرسم» بحدودها (أربعُ شاشات · صورةٌ ≤ 900 ك.ب · شموعٌ ≤ 160)، ونقطةُ الأحداث للسوقين")
seed = mk[mk.index("INDICES_SEED = "):mk.index("_SEED_LOCK = ")]
check("await _ensure_indices_group(db)" in mk and seed.count('", "') == 7 and 'seen[key] = True' in mk and "if seen.get(key):" in mk
      and "const INDICES: [string, string][]" not in tr and 'list === "idx" ? r.name' not in tr,
      "٨ «المؤشرات» قائمةٌ على الخادم تُزرع مرّةً بالسبعة وتُعرض بأسعارها كغيرها، ويُضاف إليها ويُحذف — وإن حذفها المالكُ لم تَعُد")
check('data-role="troom-gear"' in tr and 'lsSet("sp_room_hidden"' in tr and 'data-role="troom-sec2"' in tr and 'lsSet("sp_room_layout"' in tr
      and "slot={k} mini" in tr and 'data-role="troom-sdot"' in tr and "<ChartRead" in tr,
      "٩ ترسُ القوائم (إظهارٌ وإخفاءٌ وقسمٌ ثانٍ)، والشاشاتُ المتعدّدة، وأيقونةُ حالة السوق بجانب الاسم، و«تحليلُ الرسم» فوق الشاشات")
check("D7MStrip" not in pc and 'data-role="pc-fibmode"' not in pc and "<ForcePanels" in pc and "topTfs(tfUse)" in pc and 'lsSet("sp_chart_tf_use"' in pc
      and 'data-role="fib-mode"' in pn and 'data-role="d7m-panels-toggle"' in pn and "badge={!identity}" in pc and 'window.dispatchEvent(new CustomEvent("sp-draws"' in pc
      and "2_000" in lq and not (ROOT / "frontend/src/components/chart/D7MStrip.tsx").exists(),
      "١٠ الرسم: لوحتا القوّة بدل الشريط، والإطاراتُ أكثرُ ثلاثةٍ استخداماً، و«مختصر · الكل» داخل إعدادات D7M وحدها، والرسمُ اليدويُّ واحدٌ في الشاشات، "
      "والسعرُ كلَّ ثانيتين")
print("\nالنتيجة:", "نظيف ✔" if not fail else "فشل ✘")
sys.exit(fail)
