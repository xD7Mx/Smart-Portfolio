#!/usr/bin/env python3
"""حارسُ D807 · D808 · D809 — صقرٌ واحد، والفرصُ موجودةٌ في السوق الهابط، وقرصُ صقر بأسمائه (بأمر المالك 2026-11-24).

قال المالك: «لا أريد الإشارةَ إلى صقر بأنّه مجلس — "استبعدها مجلسُ صقر ورفضها عضو": إيش الكلامُ الفاضي هذا؟ صقرٌ واحد، للأمريكيّ والسعوديّ
واحد؛ الفرقُ بيئةُ العمل: الأمريكيُّ فيه عقودُ خيارات ويُربح فيه هبوطاً، والسعوديُّ لا شراءَ فيه إلا والسهمُ صاعد — ولو عرضيّاً لكنّه صاعد»؛
و«السوقُ السعوديُّ هابطٌ فيقول استبعد ستّاً اليوم — ما أحبّ هذه الشكلية؛ الفرصُ دائماً موجودة»؛ و«التصميمُ كالساعة جميل، لكنّ النقاطَ لازم
تدلّ على شيء — كتابةٌ عندها ثابتة، وكلماتٌ افتتاحيةٌ تبيّن معناها».

  ١ لا «مجلس» ولا «عضو» ولا «الفريق» في نصٍّ يراه المالك (الواجهةُ وأسبابُ صقر وسطورُ بطاقاته) — والنموذجُ يُقال له «أنت صقر» وجوابُه يُصفّى.
  ٢ السعوديّ: تاسي الهابطُ والخطرُ المرتفعُ تحفّظٌ لا رفض؛ والسهمُ العرضيُّ المائلُ إلى الصعود تحفّظ، والهابطُ والعرضيُّ المائلُ إلى الهبوط رفض.
  ٣ الأمريكيّ: الفرصةُ في الجهتين (شراءٌ وبيع) كما كانت — البيئةُ وحدها تختلف.
  ٤ الواجهة: «تحت المراقبة» بدل «استبعدها المجلس»، وقرصُ صقر بأسماءٍ ثابتةٍ عند نقاطه وكلماتٍ افتتاحيةٍ بمعنى ألوانها.

    python3 scripts/audit/saqr_d807.py
"""
from __future__ import annotations

import os as _os
import tempfile as _tf

_SANDBOX = _tf.mkdtemp(prefix="sp_d807_")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

import pathlib  # noqa: E402
import re  # noqa: E402
import sys  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")
fail = 0


def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))


def code_only(path: str) -> str:
    """النصُّ بلا تعليقاتٍ ولا وثائق — ما يُنفَّذ ويُعرض وحده."""
    t = (ROOT / path).read_text(encoding="utf-8")
    if path.endswith(".py"):
        t = re.sub(r'"""[\s\S]*?"""', "", t)
        t = "\n".join(re.sub(r"\s#.*$", "", ln) for ln in t.splitlines() if not ln.lstrip().startswith("#") and "logger." not in ln)   # سجلُّ الخادم لا يراه المالك
    else:
        t = re.sub(r"\{/\*[\s\S]*?\*/\}", "", t)
        t = re.sub(r"/\*[\s\S]*?\*/", "", t)
        t = re.sub(r"(^|[^:])//[^\n]*", r"\1", t)
    return t


BAD = re.compile(r"مجلس|عضو|أعضاء|الفريق")
SHOWN = ["frontend/src/components/saqr/SaqrOpps.tsx", "frontend/src/components/saqr/SaqrDesk.tsx", "frontend/src/components/market/OptionPicks.tsx",
         "backend/app/services/saqr_sa.py", "backend/app/services/option_picks.py", "backend/app/services/chart_scan.py", "backend/app/services/saqr_list.py"]
hits = []
for f in SHOWN:
    for ln in code_only(f).splitlines():
        for q in re.findall(r'"([^"\n]*)"|`([^`\n]*)`|>([^<>{}\n]+)<', ln):
            txt = next((x for x in q if x), "")
            if BAD.search(txt) and "مجلس الإدارة" not in txt:
                hits.append(f"{f.split('/')[-1]}: {txt[:60]}")
from app.services import saqr_council as CN  # noqa: E402
fixed = CN.one_voice("استبعدها مجلسُ صقر ورفضها عضوٌ — والأعضاءُ متّفقون والمجلس يوافق")
check(not hits and "أنت صقر" in CN.LINK_PROMPT and "مجلس" not in CN.LINK_PROMPT.replace("لا «مجلس»", "") and not BAD.search(fixed),
      "١ صقرٌ واحد: لا «مجلس» ولا «عضو» ولا «الفريق» في نصٍّ يراه المالك، والنموذجُ يُقال له «أنت صقر» وجوابُه يُصفّى", "; ".join(hits[:4]) or fixed)

# ٢ السعوديّ
TR_UP = {"state": "صاعد", "close": 50.0, "sma50": 45.0, "ret3m": 12.0, "strength": 20}
TR_SIDE_UP = {"state": "عرضي", "close": 50.0, "sma50": 48.0, "ret3m": 3.0, "strength": 5}
TR_SIDE_DN = {"state": "عرضي", "close": 47.0, "sma50": 48.0, "ret3m": -2.0, "strength": 5}
TR_DOWN = {"state": "هابط", "close": 40.0, "sma50": 48.0, "ret3m": -12.0, "strength": 15}
v = lambda tr: CN.m_trend(tr, "long", "sa", rs3=4.0)["v"]   # noqa: E731
ev_down = CN.m_events("sa", "long", {"verdict": "هابط", "close": 10500}, None, [], None)
ev_geo = CN.m_events("sa", "long", {"verdict": "صاعد", "close": 11500}, {"level": "مرتفع", "why": "توتّرٌ إقليميّ"}, [], None)
check(v(TR_UP) == "ok" and v(TR_SIDE_UP) == "warn" and v(TR_SIDE_DN) == "veto" and v(TR_DOWN) == "veto"
      and ev_down["v"] == "warn" and "الصاعد وحده" in ev_down["say"] and ev_geo["v"] == "warn",
      "٢ السعوديّ: السهمُ الصاعدُ يُشترى وإن هبط تاسي (تحفّظٌ يُنقص الدرجة)، والعرضيُّ المائلُ إلى الصعود تحفّظ، والهابطُ والعرضيُّ المائلُ إلى الهبوط لا",
      f"{v(TR_UP)}/{v(TR_SIDE_UP)}/{v(TR_SIDE_DN)}/{v(TR_DOWN)} · {ev_down['v']} · {ev_geo['v']}")

# ٣ الأمريكيّ في الجهتين
us_long = CN.m_trend({**TR_UP, "state": "صاعد"}, "long", "us")["v"]
us_short = CN.m_trend({**TR_DOWN, "state": "هابط"}, "short", "us")["v"]
check(us_long == "ok" and us_short == "ok" and CN.m_events("us", "short", None, None, [], None)["v"] == "ok",
      "٣ الأمريكيّ: الفرصةُ في الجهتين — المسارُ الصاعدُ للشراء والهابطُ للبيع (العقود) — والبيئةُ وحدها تختلف", f"{us_long} · {us_short}")

# ٤ الواجهة
opps = code_only("frontend/src/components/saqr/SaqrOpps.tsx")
desk = code_only("frontend/src/components/saqr/SaqrDesk.tsx")
css = (ROOT / "frontend/src/styles/globals.css").read_text(encoding="utf-8")
check("تحت المراقبة" in opps and "استبعد" not in opps and 'data-role="sq-label"' in desk and 'data-role="sq-legend"' in desk
      and ("كلُّ نقطةٍ نظامٌ باسمه" in desk or "كلُّ أيقونةٍ نظامٌ باسمه" in desk)   # ‏D836: أيقوناتٌ بدل النقاط بأمر المالك
      and all(w in desk for w in (">يعمل<", ">يتحفّظ<", ">ساكن<")) and ".sq-lbl { font-size: 10.5px" in css
      and "<HubWrap s={s} sesOpen={sesOpen} />" in desk,
      "٤ الواجهة: «تحت المراقبة» بدل «استبعدها المجلس»، وقرصُ صقر باسمٍ ثابتٍ عند كلّ نقطة وكلماتٍ افتتاحيةٍ بمعنى ألوانها (يعمل · يتحفّظ · ساكن)")

print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
