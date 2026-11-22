#!/usr/bin/env python3
"""حارسُ D783 — ترسُ القوائم يتحكّم في كلّ شيء، والترندُ بلونيه في قسمه، والفيبو أربعَ عشرة، والأرقامُ عمودٌ واحد (2026-11-21).

قال المالك: «زرُّ الترس للقائمة الجانبية يتحكّم في كلّ شيء: إعادةُ تسمية، حذف، إخفاء… ولازم أتحكّم بالترتيب: أرفع وأنزل وأرتّب — تاسي تحت
والسباكس فوق، أرامكو تحت والراجحي فوق»، و«الترندُ لم أجده في إعدادات الدحم في الألوان — ضاع»، و«الفيبو في واحدٍ ناقص… أربعَ عشرةَ مستوىً
عددتُها في تريدنق فيو»، و«الأرقامُ واحدٌ يمينٌ والثاني يسار — خلِّها في صفٍّ واحد بدون أن تتداخل».
وهذا يحرس الأوصال؛ والسلوكُ في المتصفّح ‏chart_d783.mjs، ووضعُ الأرقام ‏chart_colors_d772.mjs (١).

    python3 scripts/audit/chart_d783.py
"""
import os
import pathlib
import re
import sys
import tempfile

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


mk = (ROOT / "backend/app/api/v1/endpoints/market.py").read_text(encoding="utf-8")
tr = (ROOT / "frontend/src/components/market/TradeRoom.tsx").read_text(encoding="utf-8")
pc = (ROOT / "frontend/src/components/chart/ProChart.tsx").read_text(encoding="utf-8")
pn = (ROOT / "frontend/src/components/analysis/D7MPanel.tsx").read_text(encoding="utf-8")
d7 = (ROOT / "frontend/src/components/analysis/d7m.ts").read_text(encoding="utf-8")
ov = (ROOT / "frontend/src/lib/chartOverlay.ts").read_text(encoding="utf-8")
api = (ROOT / "frontend/src/services/api.ts").read_text(encoding="utf-8")

# ١ ترتيبُ القوائم على الخادم بصلاحية المالك — ومسارُه قبل مسار القائمة الواحدة (لا يُقرأ «order» رقمَ قائمة)
i_ord, i_patch = mk.find('@router.put("/watchlist/groups/order", dependencies=[Depends(require_owner)])'), mk.find('@router.patch("/watchlist/groups/{group_id}"')
check(0 < i_ord < i_patch and "watchGroupsOrder" in api and "g.sort_order = pos[g.id]" in mk,
      "١ ترتيبُ القوائم نفسِها على الخادم بصلاحية المالك (ما لم يُسمَّ يبقى بعدها بترتيبه — لا تضيع قائمة)")

# ٢ الترسُ: إظهارٌ ورفعٌ وإنزالٌ وتسميةٌ وحذفٌ لكلّ قائمة، وترتيبُ العناصر — و«محفظتي» في المتصفّح والقوائمُ على الخادم، وانزلاقٌ لا قفز
check(all(f'data-role="{k}"' in tr for k in ("troom-gup", "troom-gdown", "troom-grename", "troom-gdel", "troom-gorder", "troom-up", "troom-down"))
      and "marketApi.watchOrder(nx, g)" in tr and 'lsSet("sp_room_mine_order"' in tr and "marketApi.watchGroupsOrder(ids)" in tr
      and "marketApi.watchGroupUpdate(a.id, { name: a.name })" in tr and "function useFlip(" in tr and "prefers-reduced-motion: reduce" in tr,
      "٢ ترسُ القوائم يتحكّم في كلّ شيء (إظهار · رفع · إنزال · تسمية · حذف · ترتيبُ العناصر)، والعنصرُ ينزلق إلى مكانه ويحترم تقليلَ الحركة")

# ٣ الترندُ بلونيه داخل قسمه، ولكلّ عنصرٍ لونُه في قسمه، والمنتقي يعرض اللونَ المرسوم
check('data-role="d7m-trend"' in pn and '<Color k="trendUp"' in pn and '<Color k="trendDown"' in pn and "<legend>الألوان</legend>" not in pn
      and "colorDefaults={colorDefaults()}" in pc and 'hexTok(k === "channel" || k === "draw" ? "--brand-ink" : PC[k] || t)' in pc,
      "٣ الترندُ بلونيه (الصاعد والهابط) في قسم «الترند»، ولكلّ عنصرٍ لونُه في قسمه، والمنتقي يعرض اللونَ المرسومَ فعلاً")

# ٤ الفيبو: «الكل» أربعَ عشرة، و«مختصر» ستّة — كلُّ خطّين منطقة (‏D784 نقض «الثلاثة» بأمر المالك 2026-11-22)، وترحيلُ الإعدادات المحفوظة مرّةً
lv = re.search(r"export const FIB_LEVELS: \[number, string\]\[\] = \[([\s\S]*?)\];", d7)
n_levels = len(re.findall(r"\[-?\d+(?:\.\d+)?, ", lv.group(1))) if lv else 0
check(n_levels == 14 and "[String(lv), true])) as Record<string, boolean>" in d7 and "(!compact || SIX.has(lv))" in pc and "FIB_HIDDEN" not in d7 + pc
      and "export const FIB_SIX = [0, -0.1, 0.5, 0.618, 1, 1.1];" in d7
      and "if ((Number(sv.fibV) || 1) < 4)" in pc and "if ((Number(sv.fibV) || 1) < 5)" in pc and "fibV: 5" in pc,
      "٤ مستوياتُ الفيبو أربعَ عشرة: «الكل» كلُّها كتريدنق فيو، و«مختصر» ستّةٌ — كلُّ خطّين منطقة (‏D784)، والإعداداتُ المحفوظةُ تُرحَّل مرّةً", f"{n_levels} مستوى")

# ٥ الأرقامُ عمودٌ واحد: لا إزاحةَ أفقية، والرقمُ يلامس خطَّه أو ينزل صفّاً خالياً بمِهماز
seg = ov[ov.index("// ٤ب أرقامُ المستويات"):ov.index("const placedN")]
check("const col = " in seg and "hit.x1 + 6" not in seg and 'ctx.fillText(o.l.label as string, col + 2' in seg and "ctx.setLineDash([2, 2])" in seg,
      "٥ أرقامُ المستويات عمودٌ واحدٌ أمام آخر شمعة (لا يمينٌ ويسار)، يلامس كلٌّ خطَّه، والعنقودُ الضيّقُ صفٌّ خالٍ بمِهمازٍ إلى خطّه")

# ٦ ‏D783 قِيس على الخادم: «Fed Chairman Warsh Speaks» بلا اسمٍ عربيّ — فالقاموسُ يعرف الصيغتين
from app.services.econ_calendar import ar_title   # noqa: E402
check(ar_title("Fed Chairman Warsh Speaks") == ar_title("Fed Chair Powell Speaks") == "كلمةُ رئيس الفيدرالي",
      "٦ «Fed Chairman Warsh Speaks» (صيغةُ المصدر المقيسة على الخادم) اسمُها العربيّ «كلمةُ رئيس الفيدرالي» كـ«Fed Chair…»")
print("\nالنتيجة:", "نظيف ✔" if not fail else "فشل ✘")
sys.exit(fail)
