#!/usr/bin/env python3
"""كاشفُ سنةٍ من تقارير الجزيرة كابيتال اليومية (‏D755) — المالك 2026-11-16: «لا تجتهد من رأسك؛ امسك آخر تقاريرهم لسنةٍ كاملة
وشوف المؤشّر كيف يشتغل… هم يُظهرون نتائج بتواريخ يومية فتستطيع أن تستنبط كيف يعمل».
يُنزّل كلَّ تقريرٍ يوميٍّ منشور، ويحفظ صورةَ رسم المؤشّر العامّ منه في مخبأٍ على الخادم (‏storage/ajc_charts — ليس من بيانات المالك)،
ويجمع ما يقوله نصُّهم الفنّيّ عن المتوسّطات والتباعد والمؤشّرات بأرقامها، ثمّ يقرأ القارئُ البصريّ أحدثَ رسمين حرفياً."""
import asyncio, base64, collections, json, os, re, sys, time   # noqa: E401
os.environ["TZ"] = "Asia/Riyadh"; time.tzset()
sys.path.insert(0, "/app")
sys.stdout.reconfigure(line_buffering=True)
OUT = os.path.join(os.environ.get("SP_STATE_DIR", "/app/storage"), "ajc_charts")

LEGEND = """This is a TradingView chart from a Saudi broker's daily report. Transcribe EVERY legend/label text exactly as printed, character by character
(numbers included), for EVERY pane top to bottom. Then describe drawings. JSON only:
{"panes": [{"index": 0, "legend_lines": ["exact text", "..."], "series": [{"legend": "exact", "color": "#hex", "kind": "line|histogram|area|band"}]}],
 "arrows": [{"color": "red|green|other", "position": "above bar|below bar", "approx_date": "from x-axis", "pane": 0}],
 "divergence_lines": [{"pane": 0, "color": "red|green", "from_date": "", "to_date": "", "connects": "highs|lows", "label": "text near it if any"}],
 "other_lines": [{"pane": 0, "type": "trendline|channel|horizontal|fib", "color": "", "note": ""}],
 "x_axis_range": "first and last visible dates", "notes": ""}"""

KEYS = re.compile(r"(تباعد|الانحراف|انحراف|ديفرجنس|divergence|المتوسط|متوسط|EMA|SMA|RSI|القوة النسبية|ماكد|MACD|بولنجر|فيبوناتشي|"
                  r"قناة|خط الاتجاه|اتجاه صاعد|اتجاه هابط|سهم|إشارة)", re.I)


CHILD = r"""
import asyncio, json, os, re, sys
sys.path.insert(0, "/app")
import fitz
from app.services import research_desk as RD
it, out_png, out_txt = json.loads(sys.argv[1]), sys.argv[2], sys.argv[3]
path = asyncio.run(RD._download(it))
if not path:
    sys.exit(3)
doc = fitz.open(path)
txt = "\n".join(doc[p].get_text() for p in range(min(doc.page_count, 4)))
best = None
for pno in range(min(doc.page_count, 4)):
    for img in doc[pno].get_images(full=True):
        try:
            info = doc.extract_image(img[0])
        except Exception:
            continue
        w, h = info.get("width", 0), info.get("height", 0)
        if w < 500 or h < 250:
            continue
        if not best or w * h > best[0]:
            best = (w * h, pno + 1, info)
meta = {}
if best:
    info = best[2]
    pix = fitz.Pixmap(info["image"])
    if pix.alpha or pix.n - pix.alpha >= 4:
        pix = fitz.Pixmap(fitz.csRGB, pix, 0) if pix.n - pix.alpha >= 4 else fitz.Pixmap(pix, 0)
    pix.save(out_png)
    meta = {"page": best[1], "w": pix.width, "h": pix.height}
json.dump({"text": txt, "meta": meta}, open(out_txt, "w"), ensure_ascii=False)
os.remove(path)
"""


async def main():
    from app.services import research_desk as RD
    from app.services.research_reports import _ajc
    os.makedirs(OUT, exist_ok=True)
    allit = await _ajc()
    kinds = collections.Counter(i.get("kind") for i in allit)
    print("كلُّ البنود:", len(allit), dict(kinds))
    items = sorted([i for i in allit if i.get("kind") == "تقرير يوميّ"], key=lambda i: i.get("date") or "", reverse=True)
    print("اليومية:", len(items), "من", items[-1]["date"] if items else "-", "إلى", items[0]["date"] if items else "-")
    for i in items[:3] + items[-2:]:
        print("  ", i["date"], i.get("title"), re.sub(r"^https?://[^/]+", "", str(i.get("url")))[:110])
    phrases = collections.Counter()
    meta = {}

    async def one(it):
        """قِيس: التنزيلُ أو مكتبةُ ‏PDF أسقطا العمليةَ كلَّها (‏malloc · free) مرّتين — فكلُّ تقريرٍ في عمليته، ويُخبَّأ ناتجُه فيُستأنف."""
        import subprocess
        d = it["date"]
        png, js = os.path.join(OUT, f"{d}.png"), os.path.join(OUT, f"{d}.json")
        if not os.path.exists(js):
            # التنزيلُ والاستخراجُ معاً في عمليةٍ منفصلة: إن سقطت سقطت وحدَها
            r = subprocess.run([sys.executable, "-c", CHILD, json.dumps({k: it[k] for k in ("url", "source", "title") if k in it}), png, js],
                               capture_output=True, text=True, timeout=180)
            if r.returncode:
                print(f"  {d}: تعذّر ({r.returncode}) {(r.stderr or '').strip()[-120:]}")
        if not os.path.exists(js):
            return
        o = json.load(open(js))
        for line in re.split(r"[\n.،]", o.get("text") or ""):
            if KEYS.search(line) and re.search(r"\d", line):
                phrases[re.sub(r"[\d,.]+", "#", line.strip())[:90]] += 1
        if o.get("meta"):
            meta[d] = o["meta"]
    from datetime import date, timedelta
    floor = (date.today() - timedelta(days=372)).isoformat()
    items = [i for i in items if (i.get("date") or "") >= floor]
    print("سنةٌ كاملة:", len(items), "تقريراً منذ", floor)
    t0 = time.time()
    for i in items:
        if time.time() - t0 > 2600:
            print("… توقّف التنزيلُ عند حدّ الزمن — يُكمل التشغيلُ التالي من حيث وقف")
            break
        await one(i)
    json.dump(meta, open(os.path.join(OUT, "meta.json"), "w"))
    print(f"\nحُفظت رسومٌ: {len(meta)} في {time.time() - t0:.0f}ث · الأبعاد: {collections.Counter((m['w'], m['h'], m['page']) for m in meta.values()).most_common(5)}")
    print("\nأكثرُ العبارات الفنية تكراراً (الأرقام #):")
    for p, n in phrases.most_common(45):
        print(f"  {n:4d} · {p}")
    for d in sorted(meta, reverse=True)[:2]:
        png = open(os.path.join(OUT, f"{d}.png"), "rb").read()
        obj = await RD._gemini([{"inline_data": {"mime_type": "image/png", "data": base64.b64encode(png).decode()}}, {"text": LEGEND}],
                               max_tokens=3500, temperature=0.0)
        print(f"\n══ القراءة الحرفية · {d} ══")
        print(json.dumps(obj, ensure_ascii=False)[:3500] if obj else "تعذّرت القراءة")


asyncio.run(main())
