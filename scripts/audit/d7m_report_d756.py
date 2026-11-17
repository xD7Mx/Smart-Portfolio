#!/usr/bin/env python3
"""حارسُ D756 — «مؤشّرُ دحم» في التقرير اليوميّ هو نفسُه الذي في الرسم البيانيّ (بأمر المالك 2026-11-16).

«ضع مؤشّر دحم في التقرير: المستوياتُ المختصرة (المناطقُ الثلاث: الدعمُ والمحايدةُ والمقاومة)، والمتوسّطاتُ 20 و50 و200 على اليوميّ،
وتحته ستوكاستيك RSI كالذي عندي، والترندُ التلقائيّ، والقناةُ السعرية الرئيسية — مرتّباً واضحَ المعالم». فالمؤشّرُ شيفرتان: الواجهةُ
(‏components/analysis/d7m.ts · lib/indicators.ts) والخادمُ (‏services/d7m.py) — ويُطابَق بينهما على شموعٍ مولَّدةٍ بأشكالٍ مختلفة:
الفيبوناتشي ومناطقُه، والقناةُ الرئيسية، وخطوطُ الاتجاه الرئيسية والفرعية وإشاراتُها، وستوكاستيك RSI. ثمّ رسمُ الورقة نفسُه.

    python3 scripts/audit/d7m_report_d756.py
"""
import json, os, pathlib, random, shutil, subprocess, sys, tempfile   # noqa: E401
_SB = tempfile.mkdtemp()
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
ROOT = pathlib.Path(__file__).resolve().parents[2]
FRONT = ROOT / "frontend"
sys.path.insert(0, str(ROOT / "backend"))
fail = 0


def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))


from app.services import d7m as P   # noqa: E402


def walk(seed, n, drift, vol, px=100.0):
    r, out = random.Random(seed), []
    for i in range(n):
        o = px
        c = max(1.0, o * (1 + drift + r.gauss(0, vol)))
        out.append({"date": f"d{i}", "open": round(o, 4), "high": round(max(o, c) * (1 + abs(r.gauss(0, vol / 2))), 4),
                    "low": round(min(o, c) * (1 - abs(r.gauss(0, vol / 2))), 4), "close": round(c, 4), "volume": 1000})
        px = c
    return out


CASES = {"صاعد": walk(7, 320, 0.0012, 0.012), "هابط": walk(11, 320, -0.001, 0.013), "متذبذب": walk(23, 320, 0.0, 0.018),
         "منفجر": walk(5, 320, 0.004, 0.01), "قصير": walk(3, 80, 0.0005, 0.015)}
py = {}
for k, b in CASES.items():
    py[k] = {"fib": P.auto_fib(b, 3, 7), "ch": P.auto_channel(b, 3, 20), "tr": P.auto_trend(b, 15), "sr": P.stoch_rsi([x["close"] for x in b])}
node, esb = shutil.which("node"), FRONT / "node_modules/esbuild/lib/main.js"
if not node or not esb.exists():
    print("… لم يُقَس التطابقُ (لا node أو esbuild في هذه البيئة)")
else:
    tmp = pathlib.Path(tempfile.mkdtemp())
    (tmp / "cases.json").write_text(json.dumps(CASES), encoding="utf-8")
    (tmp / "run.mjs").write_text(f"""
import {{ readFileSync, writeFileSync }} from "node:fs";
import {{ pathToFileURL }} from "node:url";
const {{ build }} = await import(pathToFileURL({json.dumps(str(esb))}).href);
await build({{ entryPoints: [{json.dumps(str(FRONT / "src/components/analysis/d7m.ts"))}], outfile: {json.dumps(str(tmp / "d7m.mjs"))}, format: "esm", bundle: true, logLevel: "silent" }});
await build({{ entryPoints: [{json.dumps(str(FRONT / "src/lib/indicators.ts"))}], outfile: {json.dumps(str(tmp / "ind.mjs"))}, format: "esm", bundle: true, logLevel: "silent" }});
const D = await import(pathToFileURL({json.dumps(str(tmp / "d7m.mjs"))}).href);
const I = await import(pathToFileURL({json.dumps(str(tmp / "ind.mjs"))}).href);
const C = JSON.parse(readFileSync({json.dumps(str(tmp / "cases.json"))}, "utf8"));
const out = {{}};
for (const [k, b] of Object.entries(C)) out[k] = {{ fib: D.autoFib(b, 3, 7), ch: D.autoChannel(b, 3, 20), tr: D.autoTrend(b, 15),
  sr: I.stochRsi(b.map(x => x.close), I.STOCHRSI_DEFAULTS) }};
writeFileSync({json.dumps(str(tmp / "ts.json"))}, JSON.stringify(out));
""", encoding="utf-8")
    pr = subprocess.run([node, str(tmp / "run.mjs")], capture_output=True, text=True, timeout=180)
    ts = json.loads((tmp / "ts.json").read_text(encoding="utf-8")) if (tmp / "ts.json").exists() else {}

    def close(a, b):
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return abs(a - b) <= 1e-6 * max(1.0, abs(a))
        return a == b

    def seq(a, b):
        return len(a) == len(b) and all(close(x, y) for x, y in zip(a, b))

    for k, p in py.items():
        t, bad = ts.get(k), []
        if not t:
            bad.append("لا ناتج " + (pr.stderr or "")[-160:])
        else:
            pf, tf = p["fib"] or {}, t["fib"] or {}
            if bool(pf) != bool(tf) or (pf and not all(close(pf["levels"][lv], next(x["price"] for x in tf["lines"] if x["level"] == lv))
                                                     for lv in pf["levels"])):
                bad.append("الفيبوناتشي")
            pc, tc = p["ch"], t["ch"]
            if bool(pc) != bool(tc) or (pc and not all(seq(a, b) for a, b in zip(pc["base"] + pc["parallel"], tc["base"] + tc["parallel"]))):
                bad.append("القناة")
            pl = [(x["x1"], x["x2"], x["major"], x["up"]) for x in p["tr"]["lines"]]
            tl = [(x["x1"], x["x2"], x["major"], x["up"]) for x in t["tr"]["lines"]]
            if pl != tl or [(s["index"], s["kind"]) for s in p["tr"]["signals"]] != [(s["index"], s["kind"]) for s in t["tr"]["signals"]]:
                bad.append(f"الاتجاه {len(pl)}/{len(tl)}")
            if not (seq(p["sr"]["k"], t["sr"]["k"]) and seq(p["sr"]["d"], t["sr"]["d"])):
                bad.append("ستوكاستيك RSI")
        check(not bad, f"١ مؤشّرُ دحم في التقرير يطابق مؤشّر الرسم على الشموع نفسِها — {k}",
              "، ".join(bad) or f"اتجاه {len(p['tr']['lines'])} خطّاً · قناة {'نعم' if p['ch'] else 'لا'} · فيبوناتشي {'نعم' if p['fib'] else 'لا'}")

from app.services import research_paper as RP   # noqa: E402
day = [{"d": f"2026-{1 + i // 28:02d}-{1 + i % 28:02d}", "o": b["open"], "h": b["high"], "l": b["low"], "c": b["close"], "v": 2e8} for i, b in enumerate(CASES["صاعد"][:300])]
sv = RP.svg_d7m(day, title="TASI") if hasattr(RP, "svg_d7m") else ""
import re   # noqa: E402
chg = re.search(r'<g data-k="channel">(.*?)</g>', sv or "")

txt = re.sub(r"<text[^>]*>.*?</text>", "", sv or "", flags=re.S)
lines = re.findall(r'<line data-lv="[^"]+"[^>]*stroke="([^"]+)"', sv or "")
check(bool(sv) and "SMA 50" in sv and "SMA 200" in sv and "SMA 20 " not in sv and "Stoch RSI 3 3 14 14" in sv and sv.count("<svg") == 1
      and not re.search(r"[\u0600-\u06FF]", re.sub(r'aria-label="[^"]*"', "", sv)) and len(lines) >= 3
      and set(lines) <= {RP.RED, RP.GREEN, RP.GOLD} and (chg is None or chg.group(1).count("<line") <= 2),
      "٢ ‏D757 رسمُ الورقة: كلُّ المستويات ألواناً بلا حرف (المقاومةُ حمراء · الدعمُ أخضر · المحايدةُ صفراء)، و50 و200 وحدهما، والاتجاهُ والقناةُ "
      "بلا خطّ منتصف، وستوكاستيك RSI تحت", f"{len(lines)} مستوى · ألوانُها {sorted(set(lines))}")
src = (ROOT / "backend/app/services/research_paper.py").read_text(encoding="utf-8")
check("def svg_research" not in src and "research_ind(" not in src and not (FRONT / "src/lib/researchIndicator.ts").exists()
      and "research" not in (FRONT / "src/components/chart/ProChart.tsx").read_text(encoding="utf-8"),
      "٣ «مؤشّرُ الأبحاث» أُلغي بأمر المالك — لا في الورقة ولا في الرسم")
# ── ٤–٧ بلاغاتُ المالك الأخرى في الأمر نفسِه ──
desk = (ROOT / "backend/app/services/research_desk.py").read_text(encoding="utf-8")
ca = desk[desk.index("async def compose_all"):]
check("pid == main" in ca and 'sent.get(today.isoformat())' in ca and "is_default" in ca,
      "٤ «يصلني تقريران لا واحد»: يُكتب لكلّ محفظةٍ تقريرُها، ويُرسَل تقريرُ المحفظة الافتراضية وحده، مرّةً واحدةً في اليوم")
html = RP.render({"date": "2026-11-16", "market": {"tasi": {"close": 1}, "breadth": {}, "tech": {}}, "local": [], "global": []}, "all")
check(".page{width:210mm;height:297mm;overflow:hidden" in html and "window.__fit=fit" in html,
      "٥ «المحتوى لا يُقصّ ولا يدخل صفحةً على صفحة»: كلُّ صفحةٍ ورقةُ A4 بقياسها، وما زاد يُصغَّر بنسبته")
from app.services import tasi_history as TH   # noqa: E402
rd = TH.real_daily([{"date": "2026-11-15", "close": 100.0}], [{"date": "2026-11-15 10:00", "open": 99, "high": 101, "low": 98, "close": 100, "volume": 5e6},
                                                             {"date": "2026-11-15 11:00", "open": 100, "high": 102, "low": 99, "close": 101, "volume": 7e6}])
check(rd and rd[0]["volume"] == 12e6, "٦ «CVD لا يعمل — لا أحجام»: كمّيةُ يوم تاسي مجموعُ كمّيات ساعاته", str(rd and rd[0].get("volume")))
pc = (FRONT / "src/components/chart/ProChart.tsx").read_text(encoding="utf-8")
d7 = (FRONT / "src/components/analysis/d7m.ts").read_text(encoding="utf-8")
panel = (FRONT / "src/components/analysis/D7MPanel.tsx").read_text(encoding="utf-8")
check('["macd", "MACD"' in pc and 'data-role="pc-eye"' in pc and 'data-role="pc-eye-all"' in pc and "label: `${l.level} (" in pc
      and 'data-role="pc-candle-colors"' in pc and "st.cfg.chMid" in pc and "trendMajor" in pc and "slice(-300)" in pc
      and "FIB_HIDDEN = new Set([1.1, 0.618, 0.5])" in d7 and "chMid: false" in d7 and 'fibLabelPos: "on"' in d7
      and all(k in panel for k in ('k="trendMajor"', 'k="trendMinor"', 'k="chMid"', 'data-role="fib-label-pos"')),
      "٧ الرسم: ‏MACD، وعينُ الإخفاء لكلّ مؤشّرٍ ولها كلِّها، وأرقامُ فيبوناتشي أمام آخر شمعة (فوق/على/تحت)، وألوانُ الشموع، "
      "و1.1 و0.618 و0.5 مخفيّةٌ افتراضاً، والاتجاهان الرئيسيّ والفرعيّ وخطُّ منتصف القناة خياراتٌ في الإعدادات")
# ٨ ‏D757: تقريرٌ محفوظٌ يُقرأ ويُرسم — كان مخبّأُ الرسم يُحفظ معه فتصير مفاتيحُ مستوياته نصوصاً ويتعطّل الرسمُ في الخادم
import json as _json   # noqa: E402
mk = {"daily": day, "tech": {"close": day[-1]["c"], "piv": {}}, "tasi": {"close": day[-1]["c"]}, "breadth": {}}
RP.levels_of(mk)
stored = _json.loads(_json.dumps({**mk}))                    # كما يعود من الملفّ: ‏_d7m بمفاتيحَ نصّية
ok8 = True
try:
    RP.levels_of(stored)
    RP.svg_d7m(stored["daily"], title="TASI", d=RP.d7m_of(stored))
except Exception as e:   # noqa: BLE001
    ok8 = False
    err8 = repr(e)
src_desk = (ROOT / "backend/app/services/research_desk.py").read_text(encoding="utf-8")
check(ok8 and '"_d7m", "_ri"' in src_desk, "٨ ‏D757 التقريرُ المحفوظُ يُقرأ ويُرسم — ومخبّأُ الرسم لا يُحفظ معه", "" if ok8 else err8)
print("\nالنتيجة:", "عطب ✖" if fail else "نظيف ✔")
sys.exit(fail)
