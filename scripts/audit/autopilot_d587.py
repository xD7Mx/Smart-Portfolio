#!/usr/bin/env python3
"""حارسُ D585–D588: الطيارُ الآليّ للمحفظة.
  D585 أداةُ D7M على الخادم تطابق نسخةَ الرسم البيانيّ حرفاً (يوميّ · أسبوعيّ · شهريّ).
  D586 المكتبةُ موادُّ دراسية: مبادئُ بأرقام صفحاتٍ موجودة، والمصوَّرُ والطلاسمُ تُقرأ بصرياً بحارس الذاكرة.
  D587 قواعدُ الحماية حتمية: لا شراءَ فوق القيمة ولا عند مقاومة، ولا تعديلَ متوسّطٍ والشهريُّ مكسور، وتخفيفُ التركّز،
       وأفضلُ دخولٍ عند الدعم يخفض المتوسّط، وتصفيةٌ جزئيةٌ عند مقاومةٍ شهرية؛ والنموذجُ لا يملك تغييرَ الإجراء.
  D588 مفتاحُ مستثمر / مضارب يغيّر الحكم بما يقتضيه.

    python3 scripts/audit/autopilot_d587.py
"""
import os, sys, json, tempfile, pathlib, subprocess, random, shutil
from datetime import date, timedelta
_SB = tempfile.mkdtemp(prefix="sp-audit-")
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json"); os.environ["SP_STATE_DIR"] = _SB
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
fail = 0
def check(ok, label, det=""):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

# ── D585: التطابقُ مع d7m.ts ──
from app.services import d7m as D
random.seed(7); v = 50.0; bars = []; d = date(2016, 1, 3)
for i in range(2400):
    o = v; v *= 1 + random.gauss(0.0003, 0.018)
    h = max(o, v) * (1 + abs(random.gauss(0, 0.006))); l = min(o, v) * (1 - abs(random.gauss(0, 0.006)))
    if d.weekday() in (4, 5):
        d += timedelta(days=1); continue
    bars.append({"date": d.isoformat(), "open": round(o, 3), "high": round(h, 3), "low": round(l, 3), "close": round(v, 3),
                 "volume": random.randint(100000, 900000)})
    d += timedelta(days=1)
esb = ROOT / "frontend/node_modules/.bin/esbuild"
if esb.exists() and shutil.which("node"):
    json.dump(bars, open(os.path.join(_SB, "bars.json"), "w"))
    subprocess.run([str(esb), str(ROOT / "frontend/src/components/analysis/d7m.ts"), "--format=esm",
                    f"--outfile={_SB}/d7m.mjs", "--log-level=error"], check=True)
    js = (f'import fs from "node:fs"; const D = await import("{_SB}/d7m.mjs"); const bars = JSON.parse(fs.readFileSync("{_SB}/bars.json"));'
          'const o = {}; for (const [k, b] of [["D", bars], ["W", D.resample(bars, "W")], ["M", D.resample(bars, "M")]]) {'
          ' const f = D.autoFib(b, 3, 7); const z = D.zigzag(b, 3, 7);'
          ' o[k] = { n: b.length, piv: z.length, levels: f ? f.lines.map(l => +l.price.toFixed(6)) : null, adx: D.dmi(b, 14, 14).adx[b.length - 1] }; }'
          ' o.liq = D.liquidity(bars, 20, false).state; console.log(JSON.stringify(o));')
    ts = json.loads(subprocess.run(["node", "--input-type=module", "-e", js], capture_output=True, text=True, check=True).stdout)
    same = True
    for k, b in (("D", bars), ("W", D.resample(bars, "W")), ("M", D.resample(bars, "M"))):
        f = D.auto_fib(b, 3, 7); adx = D.dmi(b)[2][-1]
        same = same and len(b) == ts[k]["n"] and len(D.zigzag(b, 3, 7)) == ts[k]["piv"] \
            and [round(f["levels"][x], 6) for x in D.FIB_LEVELS] == ts[k]["levels"] and abs(adx - ts[k]["adx"]) < 1e-9
    check(same and D.liquidity(bars)["state"] == ts["liq"], "١ D7M على الخادم = نسخةُ الرسم البيانيّ (يوميّ · أسبوعيّ · شهريّ)")
else:
    print("… تعذّر فحصُ التطابق: node/esbuild غيرُ متاح")

# ── D587/D588: القواعد ──
from app.services.autopilot import rules, goal_eta
W_sup = {"where": "داخل منطقة الدعم", "support": [23.0, 24.0], "resistance": [30, 31], "state": "صاعد", "target_1_618": 34}
W_res = {"where": "داخل منطقة المقاومة", "support": [20, 21], "resistance": [29.5, 30.5], "state": "صاعد"}
M_ok = {"where": "بين الدعم والمقاومة", "support": [18, 19], "resistance": [33, 34], "state": "صاعد"}
M_res = {"where": "داخل منطقة المقاومة", "support": [18, 19], "resistance": [29, 31], "state": "صاعد"}
M_down = {"where": "تحت الدعم", "support": [18, 19], "resistance": [33, 34], "state": "هابط"}
base = {"quantity": 1000, "current_weight": 8, "target_weight": 10, "need": 5000}
r = rules({**base, "price": 23.5, "avg_cost": 26, "fair_value": 30, "decision": "شراء", "weekly": W_sup, "monthly": M_ok})
check(r["action"] == "اشترِ الآن" and not r["blocks"] and any("متوسطك" in w for w in r["why"]),
      "٢ مستثمر: شراءٌ في دعمٍ أسبوعيٍّ يخفض المتوسّط ويُحسب أثرُه", str(r))
r = rules({**base, "price": 31, "avg_cost": 26, "fair_value": 28, "decision": "شراء", "weekly": W_res, "monthly": M_res})
check(r["action"] == "صفِّ جزئياً" and any("فوق قيمته العادلة" in b for b in r["blocks"]),
      "٣ مستثمر: فوق القيمة وعند مقاومةٍ شهرية ⇒ تصفيةٌ جزئية وحجبُ الشراء", str(r))
r = rules({**base, "price": 20, "avg_cost": 26, "fair_value": 22, "decision": "انتظار", "weekly": W_sup, "monthly": M_down})
check(any("لا تعديل متوسط" in b for b in r["blocks"]) and not r["action"].startswith("اشترِ"),
      "٤ مستثمر: الشهريُّ مكسورٌ والقرارُ ليس شراء ⇒ لا تعديلَ متوسّط", str(r))
r = rules({**base, "price": 25, "avg_cost": 20, "fair_value": 30, "decision": "انتظار", "current_weight": 18, "target_weight": 10,
           "weekly": W_sup, "monthly": M_ok})
check(r["action"] == "خفّف", "٥ التركّز فوق الهدف بخمس نقاط ⇒ خفّف", str(r))
r = rules({**base, "price": 30, "avg_cost": 26, "fair_value": 40, "decision": "شراء", "weekly": W_res, "monthly": M_ok,
           "daily_liquidity": "محايد"}, "trader")
check(r["action"] == "خذ الربح" and any("مقاومة أسبوعية" in b for b in r["blocks"]),
      "٦ مضارب: مقاومةٌ أسبوعيةٌ فوق المتوسّط ⇒ خذ الربح ولو تحت القيمة العادلة", str(r))
r = rules({**base, "price": 23.5, "avg_cost": 26, "fair_value": 30, "decision": "شراء", "weekly": W_sup, "monthly": M_ok,
           "daily_liquidity": "تصريف بيعي"}, "trader")
check(not r["action"].startswith("ادخل") and any("تصريف" in b for b in r["blocks"]), "٧ مضارب: لا دخولَ وسيولةُ اليوم تصريف", str(r))
r2 = rules({**base, "price": 23.5, "avg_cost": 26, "fair_value": 30, "decision": "شراء", "weekly": W_sup, "monthly": M_ok,
            "daily_liquidity": "تجميع خفي"}, "trader")
check(r2["action"] == "ادخل الآن", "٨ مضارب: دعمٌ أسبوعيٌّ وسيولةُ تجميع ⇒ ادخل الآن", str(r2))
g = goal_eta(500_000, 1_000_000, 15.0)
check(g["status"] == "على المسار" and abs(g["years"] - 4.96) < 0.05, "٩ زمنُ الوصول للهدف بالعائد المركّب الفعليّ", str(g))
check(goal_eta(500_000, 1_000_000, None)["status"] == "غير متوفّر", "١٠ بلا عائدٍ مركّب ⇒ «غير متوفّر» لا تخمين")

src = (ROOT / "backend/app/services/autopilot.py").read_text()
check('"action": allowed[s]' in src, "١١ الإجراءُ من القواعد لا من النموذج")
lw = (ROOT / "backend/app/services/library_wisdom.py").read_text()
check("digest_visual" in lw and "MIN_FREE_MB" in lw and "_upload(path" in lw and "_forget(fname)" in lw and "pg in valid_pages" in lw,
      "١٢ المكتبة: مبادئُ بصفحاتٍ موجودة، والمصوَّرُ يُقرأ بصرياً قطعاً بحارس الذاكرة ويُحذف بعده")
fe = (ROOT / "frontend/src/components/governance/AutopilotCard.tsx").read_text()
gp = (ROOT / "frontend/src/pages/GovernancePage.tsx").read_text()
check("<AutopilotCard />" in gp and '"seg-btn"' in fe and "مستثمر" in fe and "مضارب" in fe, "١٣ بطاقةُ الحوكمة ومفتاحُ مستثمر / مضارب بلغة التطبيق")
sch = (ROOT / "backend/app/scheduler/scheduler.py").read_text()
check('id="autopilot_close"' in sch and 'id="library_wisdom_dawn"' in sch, "١٤ يُحسب بعد الإغلاق، والمكتبةُ تُدرَس فجراً")
sys.exit(fail)
