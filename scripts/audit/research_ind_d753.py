#!/usr/bin/env python3
"""حارسُ D753 — «مؤشّرُ الأبحاث» واحدٌ في التقرير اليوميّ وفي الرسم البيانيّ (بأمر المالك 2026-11-16).

«الرسمُ داخل التقرير خلِّه مثل رسم الجزيرة كابيتال — خمسةُ مؤشّرات، ثلاثةٌ بالأعلى واثنان بالأسفل… وضعه في الرسم عندي مؤشّراً مستقلّاً
باسم مؤشّر الأبحاث، مطابقاً لمؤشّرهم». فالمؤشّرُ شيفرتان — الخادمُ يرسم الورقة (‏research_paper.research_ind) والواجهةُ ترسم الغرفة
(‏lib/researchIndicator.ts) — ولا يجوز أن تختلفا: يُطابَق بينهما على شموعٍ مولَّدةٍ بأشكالٍ مختلفة (صاعد · هابط · متذبذب · منفجر)،
في فيبوناتشي ومرساته وامتداداته، والدعوم والمقاومات بأسمائها، وخطَّي الاتجاه، وأسهم الإشارة، والمتوسّطين وRSI. ثمّ ساكنٌ على الربط:
خمسةُ مؤشّرات الرسم المرجعيّ في الورقة، والمؤشّرُ في قائمة الرسم باسمه، وألوانُه رموزٌ بمظهرَي التطبيق لا قيمٌ ثابتة.

    python3 scripts/audit/research_ind_d753.py
"""
import json, os, pathlib, random, re, shutil, subprocess, sys, tempfile   # noqa: E401
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


from app.services import research_paper as RP   # noqa: E402


def walk(seed: int, n: int, drift: float, vol: float, px: float = 100.0) -> list[dict]:
    r, out = random.Random(seed), []
    for i in range(n):
        o = px
        c = max(1.0, o * (1 + drift + r.gauss(0, vol)))
        h, lo = max(o, c) * (1 + abs(r.gauss(0, vol / 2))), min(o, c) * (1 - abs(r.gauss(0, vol / 2)))
        out.append({"o": round(o, 4), "h": round(h, 4), "l": round(lo, 4), "c": round(c, 4), "v": 1000 + r.randint(0, 9000)})
        px = c
    return out


CASES = {"صاعد": walk(7, 260, 0.0012, 0.012), "هابط": walk(11, 260, -0.001, 0.013), "متذبذب": walk(23, 260, 0.0, 0.018),
         "منفجر": walk(5, 260, 0.004, 0.01), "قصير": walk(3, 60, 0.0005, 0.015)}
py = {k: RP.research_ind(b) for k, b in CASES.items()}
check(all(v and v.get("levels") and (v.get("fib") or k == "قصير") for k, v in py.items()),
      "١ مؤشّرُ الخادم يُخرج لكلّ شكلٍ من أشكال السوق مستوياتٍ، ولسنة الشموع فيبوناتشي", " · ".join(k for k, v in py.items() if not (v and v.get("levels"))))
lv = py["صاعد"]["levels"]
c = CASES["صاعد"][-1]["c"]
sup = [lv[f"s{i}"] for i in (1, 2, 3) if f"s{i}" in lv]
res = [lv[f"r{i}"] for i in (1, 2, 3) if f"r{i}" in lv]
check(len(sup) == 3 and len(res) == 3 and sup == sorted(sup, reverse=True) and res == sorted(res) and max(sup) < c < min(res) + 1e-9
      and all(lv.get(f"{k}_name") for k in ("p", "s1", "s2", "s3", "r1", "r2", "r3")),
      "٢ ثلاثةُ دعومٍ تحت السعر تنازلياً وثلاثُ مقاوماتٍ فوقه تصاعدياً، ولكلٍّ اسمُه (فيبوناتشي · متوسّط · قمّة · قاع · نفسيّ · كلاسيكيّ)",
      " / ".join(f"{lv[k]:.2f} {lv[k + '_name']}" for k in ("s1", "p", "r1")))
fb = py["صاعد"]["fib"]
check([round(x["k"], 3) for x in fb["levels"]] == [0, 1, 1.272, 1.618, 2] and fb["levels"][0]["p"] < fb["levels"][1]["p"],
      "٣ فيبوناتشي الرسم المرجعيّ: 0 · 1 · 1.272 · 1.618 · 2 من القاع إلى قمّة الارتداد", " · ".join(f"{x['k']}={x['p']:.2f}" for x in fb["levels"]))

# ── ٤ التطابقُ بين الشيفرتين ──
node, esb = shutil.which("node"), FRONT / "node_modules/esbuild/lib/main.js"
if not node or not esb.exists():
    print("… لم يُقَس التطابقُ (لا node أو esbuild في هذه البيئة)")
else:
    tmp = pathlib.Path(tempfile.mkdtemp())
    (tmp / "cases.json").write_text(json.dumps(CASES), encoding="utf-8")
    run = tmp / "run.mjs"
    run.write_text(f"""
import {{ readFileSync, writeFileSync }} from "node:fs";
import {{ pathToFileURL }} from "node:url";
const {{ build }} = await import(pathToFileURL({json.dumps(str(esb))}).href);
await build({{ entryPoints: [{json.dumps(str(FRONT / "src/lib/researchIndicator.ts"))}], outfile: {json.dumps(str(tmp / "ri.mjs"))}, format: "esm", bundle: false, logLevel: "silent" }});
const {{ researchInd }} = await import(pathToFileURL({json.dumps(str(tmp / "ri.mjs"))}).href);
const C = JSON.parse(readFileSync({json.dumps(str(tmp / "cases.json"))}, "utf8"));
const out = {{}};
for (const [k, b] of Object.entries(C)) out[k] = researchInd(b);
writeFileSync({json.dumps(str(tmp / "ts.json"))}, JSON.stringify(out));
""", encoding="utf-8")
    pr = subprocess.run([node, str(run)], capture_output=True, text=True, timeout=120)
    ts = json.loads((tmp / "ts.json").read_text(encoding="utf-8")) if (tmp / "ts.json").exists() else {}

    def close(a, b):
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return abs(a - b) <= 1e-6 * max(1.0, abs(a))
        return a == b

    for k, p in py.items():
        t = ts.get(k)
        bad = []
        if not t:
            bad.append("لا ناتج " + (pr.stderr or "")[-200:])
        else:
            pf, tf = p.get("fib") or {}, t.get("fib") or {}
            if (pf.get("i0"), pf.get("i1")) != (tf.get("i0"), tf.get("i1")) or not all(close(a["p"], b["p"]) for a, b in zip(pf.get("levels", []), tf.get("levels", []))):
                bad.append("فيبوناتشي")
            if set(p["levels"]) != set(t["levels"]) or not all(close(p["levels"][q], t["levels"][q]) for q in p["levels"]):
                bad.append("المستويات")
            if [(p["trend"][q] or {}).get("x1") for q in ("res", "sup")] != [(t["trend"][q] or {}).get("x1") for q in ("res", "sup")]:
                bad.append("خطّا الاتجاه")
            if [(s["i"], s["side"]) for s in p["signals"]] != [(s["i"], s["side"]) for s in t["signals"]]:
                bad.append("الإشارات")
            if not all(close(p[q][-1], t[q][-1]) for q in ("sma20", "sma50", "rsi") if p[q][-1] is not None):
                bad.append("المتوسّطان وRSI")
        check(not bad, f"٤ مؤشّرُ الرسم يطابق مؤشّر التقرير على الشموع نفسِها — {k}",
              "، ".join(bad) or f"{len(p['signals'])} إشارة · محور {p['levels']['p']:.2f} {p['levels']['p_name']}")

# ── ٥–٧ الربطُ في الورقة والرسم والمظهرَين ──
src = (ROOT / "backend/app/services/research_paper.py").read_text(encoding="utf-8")
sv = RP.svg_research(CASES["صاعد"], title="TASI", ri=py["صاعد"]) if "def svg_research" in src else ""
check(bool(sv) and "SMA 20" in sv.replace("20 SMA", "SMA 20") and "RSI" in sv and "1.618" in sv and sv.count("<svg") == 1,
      "٥ رسمُ الورقة بهيئة الرسم المرجعيّ: متوسّطا 20 و50 وفيبوناتشي وخطّا الاتجاه فوق، والكمّيةُ وRSI 14 تحت", f"{len(sv)} حرفاً")
pc = (FRONT / "src/components/chart/ProChart.tsx").read_text(encoding="utf-8")
check('"research", "مؤشر الأبحاث"' in pc and "researchInd(" in pc and 'k === "research"' in pc and '"researchRsi"' in pc and "--ri-fib" in pc,
      "٦ «مؤشر الأبحاث» في قائمة مؤشّرات الرسم باسمه، بشيفرة التقرير نفسِها ولوحتَيه (الكمّية · RSI) وفيبوناتشي وأسهمه")
css = (FRONT / "src/styles/globals.css").read_text(encoding="utf-8")
toks = ["--ri-sma20", "--ri-sma50", "--ri-fib", "--ri-rsi", "--ri-band", "--ri-trend", "--ri-buy", "--ri-sell"]
blocks = re.findall(r"(:root|html\.light)\s*\{([^}]*--ri-fib[^}]*)\}", css)
lib = (FRONT / "src/lib/researchIndicator.ts").read_text(encoding="utf-8")
check({b[0] for b in blocks} == {":root", "html.light"} and all(all(t + ":" in b[1] for t in toks) for b in blocks) and not re.search(r"#[0-9a-fA-F]{6}", lib),
      "٧ ألوانُ المؤشّر رموزٌ معرَّفةٌ للمظهرَين الداكن والفاتح — لا قيمةَ ثابتةً في شيفرته")

print("\nالنتيجة:", "عطب ✖" if fail else "نظيف ✔")
sys.exit(fail)
