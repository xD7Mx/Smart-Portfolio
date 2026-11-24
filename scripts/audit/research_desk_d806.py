#!/usr/bin/env python3
"""حارسُ D806 — «التقريرُ اليوميّ 24/11 كاتبٌ: لا توجد أخبارٌ محليةٌ ولا عالمية» (المالك: «عيبٌ لا أقبله ولا أسمح به»).

قِيس على الخادم (‏research_desk_door_d806.py): تقريرا اليوم من الجزيرة كابيتال والراجحي المالية فشلت قراءتُهما الساعة 15:08 (النموذجُ
«503 high demand» يومَها) فعُلِّما «مقروءَين» ولم يُعادا؛ ثمّ كتابةُ التقرير الساعة 15:40 — وأمامها أربعةُ مصادر فيها 24 خبراً محلياً
و23 عالمياً — فشلت هي أيضاً، فحُفظ التقريرُ وأُرسل بلا عنوانٍ ولا خبرٍ واحد. فالحارس:

  ١ ما فشلت قراءتُه يُعاد حتى أربعَ مرّات — والناجحُ لا يُعاد.
  ٢ النموذجُ المزدحمُ ثلاثاً ⇒ الاحتياطيّ؛ و«غيرُ الموجود» ⇒ التالي فوراً؛ والكلُّ مزدحمٌ ⇒ ‏busy بلا جوابٍ مختلَق؛ والانتظارُ ثوانٍ لا 15 ثمّ 30.
  ٣ يومُ 24/11 نفسُه (المصادرُ الأربعةُ بأخبارها، والنموذجُ معطّلٌ كلَّه): التقريرُ بأخباره المحلية والعالمية من مصادرها كما وردت،
    بلا اسمِ جهةٍ ناشرةٍ ولا خبرٍ مكرّر، وعنوانُه من أرقام الجلسة — ومصدرُ نصّه «notes».
  ٤ والنموذجُ يجيب ⇒ نصُّه هو («ai»)؛ وجوابٌ بلا خبرٍ واحد ⇒ محاولةٌ ثانية ثمّ أخبارُ المصادر.
  ٥ المصدرُ المستقلّ (بأمر المالك: «لو أقفلت البنوك يستغني عنها»): عناوينُ اليوم من الوسائل المعتمدة وحدها — لا القديمةُ ولا غيرُ المعتمدة.
  ٦ التوقيتُ والإرسال: قراءةُ ما فشل قبل الكتابة (15:28)، ولا يُرسَل تقريرٌ لم يكتبه قسمُ الأبحاث إلا في المحاولة الأخيرة (16:30 · 17:30)،
    وقراءتان لا تتزامنان؛ ومهمّةُ إعادة كتابة جلسةٍ بتاريخها وحده.

    python3 scripts/audit/research_desk_d806.py
"""
from __future__ import annotations

import os as _os
import tempfile as _tf

_SANDBOX = _tf.mkdtemp(prefix="sp_d806_")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

import asyncio  # noqa: E402
import pathlib  # noqa: E402
import re  # noqa: E402
import sys  # noqa: E402
from datetime import date, datetime, timedelta, timezone  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

fail = 0


def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))


import httpx  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.services import research_desk as RD  # noqa: E402

# ── ١ إعادةُ ما فشل ──
it = lambda u, d="2026-11-24", kind="تقرير يوميّ": {"url": u, "date": d, "kind": kind, "source": "الجزيرة كابيتال", "title": "x"}   # noqa: E731
items = [it("a"), it("b"), it("c"), it("d")]
read = {"a": {"ok": False, "tries": 1}, "b": {"ok": False, "tries": 4}, "c": {"ok": True}}
q = [x["url"] for x in RD.queue(items, read, date(2026, 11, 24), 10)]
check(sorted(q) == ["a", "d"], "١ ما فشلت قراءتُه يُعاد (حتى أربعَ مرّات) والجديدُ يُقرأ — والناجحُ لا يُعاد", str(q))

# ── ٢ النموذجُ وأحتياطيّاه ──
settings.AI_API_KEY = "test-key"
settings.AI_MODEL = "primary-model"
settings.AI_MODEL_FALLBACKS = "backup-one,backup-two"
GOOD = {"candidates": [{"content": {"parts": [{"text": '{"headline": "x", "local": [], "global": []}'}]}}]}
slept: list[float] = []
calls: list[str] = []


async def fake_sleep(s, *a, **k):
    slept.append(float(s))


def run_ask(script):
    slept.clear()
    calls.clear()
    seq = list(script)

    async def fake_post(url, key, body, timeout):
        calls.append(url.split("/models/")[1].split(":")[0])
        r = seq.pop(0) if seq else 503
        if r == "timeout":
            raise httpx.ReadTimeout("slow")
        return (r, GOOD if r == 200 else {})
    RD._post = fake_post
    s0 = asyncio.sleep
    asyncio.sleep = fake_sleep
    try:
        return asyncio.run(RD._ask([{"text": "x"}], 100, 0.1, 200.0))
    finally:
        asyncio.sleep = s0


o1, w1 = run_ask([503, 503, 503, 200])
c1, s1 = list(calls), sum(slept)
o2, w2 = run_ask([404, 200])
c2 = list(calls)
o3, w3 = run_ask([503] * 9)
check(isinstance(o1, dict) and c1 == ["primary-model"] * 3 + ["backup-one"] and s1 <= 12 and isinstance(o2, dict) and c2 == ["primary-model", "backup-one"]
      and o3 is None and w3 == "busy" and len(calls) == 9,
      "٢ المزدحمُ ثلاثاً ⇒ الاحتياطيّ، و«غيرُ الموجود» ⇒ التالي فوراً، والكلُّ مزدحمٌ ⇒ ‏busy بلا جواب — والانتظارُ ثوانٍ لا 15 ثمّ 30",
      f"{c1} · {s1} · {c2} · {w3}")

# ── ٣ يومُ 24/11: المصادرُ الأربعةُ والنموذجُ معطّل ──
note = lambda src, d, loc, glo, risks=(): {"key": f"{src}{d}", "date": d, "source": src, "title": "التقرير اليومي", "kind": "تقرير يوميّ",   # noqa: E731
                                           "headline": "خلاصة", "local_news": list(loc), "global_news": list(glo), "risks": list(risks)}
J23 = note("الجزيرة كابيتال", "2026-11-23", [f"أعلنت شركة {i} عن أرباحٍ بـ{i} مليون" for i in range(8)],
           [f"ارتفع مؤشّر {i} بنسبة {i}%" for i in range(7)], ["تذبذبُ النفط"])
R23 = note("الراجحي المالية", "2026-11-23", ["أعلنت شركة 1 عن أرباحٍ بـ1 مليون", "وقّعت أرامكو اتفاقية — بحسب الجزيرة كابيتال"],
           ["ارتفع مؤشّر 1 بنسبة 1%", "صعد الذهب 0.5%"])
MKT = {"tasi": {"close": 11234.56, "pct": -0.42}, "breadth": {"value": 5.2e9, "up": 80, "down": 170}, "tech": {"view": "محايد"},
       "sectors": [{"name": "البنوك", "pct": 0.3}, {"name": "المواد الأساسية", "pct": -1.1}]}
K = {"notes": [J23, R23], "read": {}}


async def no_ai(*a, **k):
    RD.LAST["why"] = "busy"
    return None


async def run_text(fake, srcs):
    RD._gemini = fake
    s0 = asyncio.sleep
    asyncio.sleep = fake_sleep
    try:
        return await RD.compose_text(srcs, MKT, [], date(2026, 11, 24), "المحفظة الرئيسية", K)
    finally:
        asyncio.sleep = s0

slept.clear()
txt, src = asyncio.run(run_text(no_ai, [J23, R23]))
loc, glo = [x["text"] for x in txt["local"]], [x["text"] for x in txt["global"]]
check(src == "notes" and len(loc) == 7 and len(glo) == 5 and len(set(loc)) == len(loc) and not any("الجزيرة كابيتال" in t for t in loc)
      and all(x["src"] and x["src"][0] >= 1 for x in txt["local"] + txt["global"]) and "11,234.56" in txt["headline"] and slept,
      "٣ يومُ 24/11 والنموذجُ معطّلٌ كلَّه: الأخبارُ المحليةُ والعالميةُ من مصادرها كما وردت (سبعٌ وخمس، بلا تكرارٍ ولا اسمِ جهة) والعنوانُ من أرقام الجلسة",
      f"{src} · {len(loc)}/{len(glo)} · {txt['headline'][:60]}")

# ── ٤ النموذجُ يجيب ⇒ نصُّه؛ وجوابٌ فارغ ⇒ محاولةٌ ثانيةٌ ثمّ المصادر ──
n_calls = {"n": 0}


async def ai_ok(*a, **k):
    n_calls["n"] += 1
    return {"headline": "تاسي يتراجع", "local": [{"text": "أرامكو توقّع اتفاقية", "src": [1]}], "global": [{"text": "الذهب يصعد", "src": [2]}],
            "portfolio": [], "watch": []}


async def ai_empty(*a, **k):
    n_calls["n"] += 1
    return {"headline": "", "local": [], "global": []}

t4, s4 = asyncio.run(run_text(ai_ok, [J23, R23]))
n_calls["n"] = 0
t5, s5 = asyncio.run(run_text(ai_empty, [J23, R23]))
check(s4 == "ai" and t4["headline"] == "تاسي يتراجع" and len(t4["local"]) == 1 and s5 == "notes" and n_calls["n"] == 2 and len(t5["local"]) >= 1,
      "٤ النموذجُ يجيب ⇒ نصُّه هو؛ وجوابٌ بلا خبرٍ واحد ⇒ محاولةٌ ثانيةٌ ثمّ أخبارُ المصادر — لا «لا أخبار»", f"{s4} · {s5} · {n_calls['n']}")

# ── ٥ المصدرُ المستقلّ ──
from app.services import news_fetcher as NF  # noqa: E402
now = datetime.now(timezone.utc)
mk = lambda h, src, hrs, tr=True: {"headline": h, "source": src, "published": now - timedelta(hours=hrs), "trusted": tr}   # noqa: E731


async def f_market():
    return [mk("أرامكو تعلن نتائجها", "أرقام", 2), mk("خبرٌ قديم", "أرقام", 80), mk("مدوّنةٌ مجهولة", "مدوّنة", 1, False),
            mk("أرامكو تعلن نتائجها", "مباشر", 3)]


async def f_global():
    return [mk("الفيدرالي يثبّت الفائدة", "رويترز", 5)]


async def f_econ():
    return [mk("النفط يرتفع 2%", "الشرق بلومبيرغ", 6)]

NF.fetch_market_news, NF.fetch_global_news, NF.fetch_economic_news = f_market, f_global, f_econ
W = asyncio.run(RD.wire_sources(date(2026, 11, 24)))
wl = (W[0].get("local_news") if W else []) or []
wg = (W[1].get("global_news") if len(W) > 1 else []) or []
t6, s6 = asyncio.run(run_text(no_ai, W))
check(len(W) == 2 and wl == ["أرامكو تعلن نتائجها — أرقام"] and len(wg) == 2 and [x["text"] for x in t6["local"]] == ["أرامكو تعلن نتائجها"]
      and len(t6["global"]) == 2 and s6 == "notes",
      "٥ المصدرُ المستقلّ عن البنوك: عناوينُ اليوم من الوسائل المعتمدة وحدها (لا القديمُ ولا المجهولُ ولا المكرّر) — ويكفي وحده لأخبار التقرير",
      f"{wl} · {wg} · {[x['text'] for x in t6['local']]}")

# ── ٦ التوقيتُ والإرسال والمهمّة ──
src_rd = (ROOT / "backend/app/services/research_desk.py").read_text(encoding="utf-8")
sch = (ROOT / "backend/app/scheduler/scheduler.py").read_text(encoding="utf-8")
ops = (ROOT / ".github/workflows/ops.yml").read_text(encoding="utf-8")
check('elif r.get("text_source") != "ai" and not final:' in src_rd and "srcs = recent_sources(k[\"notes\"], today) + await wire_sources(today)" in src_rd
      and "ولا تكتب «لا جديد»" in src_rd and "await compose_all(send=True, final=False)" in sch and 'id="research_ingest_retry"' in sch
      and 'hour=15, minute=28' in sch and 'id="research_report_retry"' in sch and 'id="research_report_last"' in sch and 'if _RD_INGEST["on"]:' in sch
      and "research_rewrite)" in ops and "[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]) ;;" in ops and "send=False" in ops.split("research_rewrite)")[1][:1200]
      and not re.search(r"RD\._gemini|await asyncio\.sleep\(15 \* \(i \+ 1\)\)", src_rd),
      "٦ قراءةُ ما فشل 15:28 قبل الكتابة، ولا يُرسَل تقريرٌ لم يكتبه القسمُ إلا في الأخيرة (16:30 · 17:30)، وقراءتان لا تتزامنان، ومهمّةُ إعادة جلسةٍ بتاريخها وحده بلا إرسال")

print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
