#!/usr/bin/env python3
"""حارسُ D775 — ميزانيةُ العقد بيد المالك كلَّ يوم: 100 أو 150 أو 300 أو ما شاء، والقائمةُ تُعرض بها فوراً (2026-11-20).

«الأفضلُ أن تكون الميزانيةُ كستمايز: أخلّيها 300، أخلّيها 150، أخلّيها 100 — كلَّ يومٍ يجي خيرٌ معه».
فلا تُبنى القائمةُ لميزانيةٍ واحدة: يُحفظ لكلّ سهمٍ «الحدُّ الكفء» من عقوده (كلُّ عقدٍ فيه أعلى درجةً من كلّ أرخصَ منه)، ويُختار عند العرض
أفضلُها ضمن الميزانية الآن — فتبديلُها لا يُعيد البحثَ ولا ينتظر الجلسة، وبجانب كلّ ميزانيةٍ جاهزةٍ عددُ عقودها.

    python3 scripts/audit/saqr_d775.py
"""
import os, pathlib, sys, tempfile   # noqa: E401
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


from app.services import saqr_list as SL   # noqa: E402


def k(c, cost, score, typ="call", margin=3):
    return {"contract": c, "type": typ, "cost": cost, "score": score, "margin": margin, "px_src": "ask"}


# ١ الحدُّ الكفء: يبقى العقدُ إن فاق درجةُ كلِّ أرخصَ منه — فأفضلُ عقدٍ ضمن أيّ ميزانيةٍ آخرُ ما لا يتجاوزها
fr = SL.frontier([k("A", 90, 50), k("B", 140, 45), k("C", 160, 70), k("D", 280, 69), k("E", 420, 82), k("F", 90, 40)])
check([x["contract"] for x in fr] == ["A", "C", "E"],
      "١ لكلّ سهمٍ يُحفظ الحدُّ الكفءُ من عقوده: الأرخصُ الأفضلُ ثمّ كلُّ أغلى يفوق ما قبله درجةً — لا ما هو أغلى وأضعف", f"{[x['contract'] for x in fr]}")

# ٢ العرضُ بالميزانية: عند 100 عقدُ 90، وعند 150 كذلك، وعند 300 عقدُ 160، وعند 500 عقدُ 420 — ومعه العددُ عند كلّ ميزانيةٍ جاهزة
E = lambda s, cards, st="صاعد": {"symbol": s, "name": s, "price": 10, "fund": 80, "trend": {"state": st}, "news": None, "seen": "x", "cards": cards}   # noqa: E731
lst = {"v": SL.V, "at": "2026-11-20T16:00:00+00:00", "for": "2026-11-20", "label": "جلسة اليوم", "scanned": 9, "universe": 600, "more": True,
       "entries": {"X": E("X", fr), "Y": E("Y", [k("Y1", 250, 60)]), "P": E("P", [k("P1", 120, 66, "put")], "هابط"), "H": E("H", [k("H1", 80, 90)])},
       "done": {"Z": {"at": "x", "why": "الفارقُ بين العرض والطلب واسع"}, "X": {"at": "x", "why": None}}}
v100, v150, v300, v500 = (SL.view(lst, b, held={"H"}) for b in (100, 150, 300, 500))
pick = lambda v: {i["symbol"]: i["contract"] for i in v["items"]}   # noqa: E731
check(pick(v100) == {"X": "A"} and pick(v150) == {"X": "A", "P": "P1"} and pick(v300) == {"X": "C", "Y": "Y1", "P": "P1"}
      and pick(v500) == {"X": "E", "Y": "Y1", "P": "P1"} and v100["excluded"] == {"فوق الميزانية": 2, "الفارقُ بين العرض والطلب واسع": 1}
      and v100["cheapest"] == 120 and v150["levels"] == {"100": 1, "150": 2, "200": 2, "300": 3, "500": 3} and v300["budget"] == 300
      and SL.view(lst, 175, held={"H"})["levels"].get("175") == 2 and "H" not in pick(v500),
      "٢ القائمةُ بميزانية المالك الآن: لكلّ سهمٍ أفضلُ عقدٍ لا يتجاوزها (100 ⇐ عقدُ 90 · 300 ⇐ عقدُ 160 · 500 ⇐ عقدُ 420)، وما فوقها يُعدّ بأرخصه، "
      "ومع كلّ ميزانيةٍ جاهزةٍ (ومبلغِ المالك نفسِه) عددُ عقودها، وما في المحفظة لا يُعاد عرضُه", f"{pick(v300)} · {v150['levels']}")

# ٣ الشراءُ وحده: يسقط البيعُ بسببه — والقائمةُ القديمةُ بلا عقودٍ محفوظةٍ لا تُعرض فارغةً بلا سبب
vc = SL.view(lst, 300, calls_only=True)
check(pick(vc) == {"X": "C", "Y": "Y1", "H": "H1"} and vc["excluded"].get("بيعٌ وأنت على الشراء وحده") == 1 and SL.view(None, 150) is None,
      "٣ «الشراءُ وحده» بأمر المالك يُسقط عقودَ البيع من العرض بسببها — بلا بحثٍ جديد", f"{vc['excluded']}")

# ٤ لا بحثَ جديدٌ عند تغيير الميزانية، والنقاطُ والتداولُ الآليُّ يقرؤون العرضَ بالميزانية، والواجهةُ تختارها
mk = (ROOT / "backend/app/api/v1/endpoints/market.py").read_text(encoding="utf-8")
tr = (ROOT / "backend/app/services/saqr_trader.py").read_text(encoding="utf-8")
sett = mk[mk.index("async def saqr_settings("):mk.index("async def _saqr_list_bg(")]
hunt = tr[tr.index("async def _hunt("):tr.index("# ══ أوامرُ المالك (‏D771)")]
# ‏D778: شاشةُ القائمة أُزيلت بأمر المالك («نكتفي بعقود الخيارات») — والميزانيةُ تُختار في «عقود الخيارات» (‏op-budget)؛ والقائمةُ في الخلفية للتداول الآليّ
check("_saqr_list_bg" not in sett and mk.count("_saqr_list_view()") >= 2 and "SL.view(SL.load(), budget" in hunt
      and not (ROOT / "frontend/src/components/saqr/SaqrList.tsx").exists(),
      "٤ تغييرُ الميزانية لا يُطلق بحثاً جديداً، ونقطةُ القائمة والتداولُ الآليُّ يقرآنها بميزانية العقد الآن (وشاشتُها أُزيلت — ‏D778)")

print("\nالنتيجة:", "نظيف ✔" if not fail else "فشل ✘")
sys.exit(fail)
