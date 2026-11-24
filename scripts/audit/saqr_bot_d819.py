#!/usr/bin/env python3
"""حارسُ D819 — صقرٌ على تلغرام من جديد (بأمر المالك 2026-11-24): «يجب إعادةُ تشكيله وتضمينُ التقرير اليوميّ كأحد الخيارات — شكلُه الحاليّ
لا يعجبني — وسؤالُ صقر لا يعطيني نتيجةً ملموسة».

قِيس على الخادم (‏saqr_ask_door_d819.py) بأسئلة المالك: «أفضلُ فرصةٍ في الأمريكيّ» و«رأيك في NVDA» و«عقدٌ بـ500 دولار» ⇐ «خارج نطاقي — السوقُ
السعوديُّ فقط»، و«نظرتُك لتاسي» ⇐ «بياناتُ تاسي غير متوفّرة»: السياقُ بلا كتلةٍ واحدةٍ من عمل صقر، والتعليماتُ تحصره في السعوديّ، و«نبضُ السوق»
يُقصّ أوّلاً.

  ١ أسئلةُ المالك نفسُها تُجاب من عمل صقر بأرقامها: فرصُ المسح (دخولٌ وهدفٌ ووقفٌ وحكم)، وعقودُ دفتر الميزانية (تنفيذٌ وانتهاءٌ وكلفة)، ونظرتُه
    لتاسي، وسهمٌ أمريكيٌّ قرأه — فوراً وبلا نموذج؛ ولا «خارج نطاقي».
  ٢ والنموذجُ لما سوى ذلك: تعليماتُه للسوقين وعقود الخيارات، وعملُ صقر ونبضُ السوق في رأس سياقه لا يُقصّان.
  ٣ القائمة: ستّةُ أبوابٍ بترتيب الطلب — فرصُ اليوم · التقريرُ اليوميّ · محفظتي · السوق · الأحداثُ والأخبار · اسأل صقر — والبابُ يُفتح في
    الرسالة نفسِها (تعديلٌ لا رسالةٌ جديدة)، والرئيسيةُ بطاقةُ حالٍ في لمحة.
  ٤ التقريرُ اليوميّ ملفٌّ من القائمة — آخرُه، وأيامُه السابقةُ أزرار؛ والمالكُ وحده يُجاب.

    python3 scripts/audit/saqr_bot_d819.py
"""
from __future__ import annotations

import os as _os
import tempfile as _tf

_SANDBOX = _tf.mkdtemp(prefix="sp_d819_")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

import asyncio  # noqa: E402
import pathlib  # noqa: E402
import sys  # noqa: E402
from datetime import datetime, timezone  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")
fail = 0


def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))


from app.services import chart_scan as CS  # noqa: E402
from app.services import option_picks as OP  # noqa: E402
from app.services import research_desk as RD  # noqa: E402
from app.services import saqr_brief as B  # noqa: E402

NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")
it = lambda s, n, side="long": {"symbol": s, "name": n, "side": side, "setup": "ارتدادٌ من الدعم", "quality": 78, "horizon": "شهر", "horizon_n": 1,   # noqa: E731
                                "entry": [180.5, 184.0], "target": 205.0, "stop": 172.0, "close": 183.2,
                                "council": {"verdict": "يوافق", "score": 82}, "link": {"decision": "شراء", "link": "المسارُ صاعدٌ والنتائجُ قوية."}}
SCANS = {"us": {"at": NOW, "found": 2, "read": 150, "items": [it("NVDA", "NVIDIA"), it("AAPL", "Apple")], "reads": {"TSLA": {"setup": None}}},
         "sa": {"at": NOW, "found": 1, "read": 260, "items": [it("1120", "مصرف الراجحي")], "reads": {}}}
CS.load = lambda m: SCANS.get(m)
OP.book_budgets = lambda: [300, 600, 1500]
OP.book_load = lambda b: {"open": [{"contract": "NVDA261218C00190000", "symbol": "NVDA", "name": "NVIDIA", "type": "call", "strike": 190.0, "expiry": "2026-12-18",
                                    "target": 205.0, "card": {"cost": 540.0, "breakeven": 195.4, "pop": 41.0, "dte": 24}, "last": {"dte": 24, "pl_pct": 3.5}}]}
REP = {"date": "2026-11-24", "portfolio_id": 1, "headline": "تاسي يرتدّ فوق 9,970", "local": [{"text": "خبرٌ محلّي"}], "global": [{"text": "خبرٌ عالميّ"}],
       "market": {"tasi": {"close": 9977.06, "pct": 0.4}, "tech": {"view": "اتجاه هابط"}, "saqr": {"why": ["الإشاراتُ الفنيةُ سلبية", "اتّساعُ السوق ضعيف"]}}}
RD.load_report = lambda pid, day=None: dict(REP, date=day or REP["date"]) if str(pid) == "1" else None
RD.report_dates = lambda pid: ["2026-11-24", "2026-11-23", "2026-11-22"]

# ── ١ أسئلةُ المالك ──
a1 = B.answer("ما أفضل فرصة اليوم في السوق الأمريكي؟") or ""
a2 = B.answer("أعطني صفقة عقد خيارات بميزانية 500 دولار") or ""
a3 = B.answer("ما نظرتك لتاسي هذا الأسبوع؟") or ""
a4 = B.answer("وش رأيك في NVDA؟") or ""
a5 = B.answer("كيف حال الطقس")
check("NVDA" in a1 and "180.50–184.00" in a1 and "205.00" in a1 and "172.00" in a1 and "صقر يوافق (82/100)" in a1 and "1120" not in a1
      and "NVDA261218C00190000" in a2 and "190.00" in a2 and "2026-12-18" in a2 and "540" in a2 and "600" in a2
      and "اتجاه هابط" in a3 and "9,977.06" in a3 and "الإشاراتُ الفنيةُ سلبية" in a3
      and "فرصةٌ في آخر مسح" in a4 and "NVDA" in a4 and a5 is None and not any("خارج نطاق" in x for x in (a1, a2, a3, a4)),
      "١ أسئلةُ المالك تُجاب من عمل صقر بأرقامها: فرصُ الأمريكيّ (دخولٌ وهدفٌ ووقفٌ وحكم)، وعقدُ أقرب دفترٍ لـ500$ (تنفيذٌ وانتهاءٌ وكلفة)، "
      "ونظرتُه لتاسي، وNVDA كما قرأه — ولا «خارج نطاقي»", f"{len(a1)}/{len(a2)}/{len(a3)}/{len(a4)}")

# ── ٢ النموذجُ وسياقُه ──
src_chat = (ROOT / "backend/app/services/ai_chat.py").read_text(encoding="utf-8")
from app.services import ai_chat as C  # noqa: E402
res = asyncio.run(C.answer(None, "ما أفضل فرصة اليوم في السوق الأمريكي؟", prefer_llm=True, saqr=True))
k = B.knowledge()
check(res.get("source") == "saqr" and "NVDA" in res.get("reply", "") and "والأمريكيّ وعقودِ خياراته" in C.SYSTEM_RULES and "لسوق الأسهم\nالسعودي (تداول). تُخاطب" not in C.SYSTEM_RULES
      and 'PRIORITY = ["صقر — عمله", "المحفظة", "نبض السوق"' in src_chat and 'ctx = {"صقر — عمله": saqr_brief.knowledge(), **ctx}' in src_chat
      and "rules += saqr_brief.RULES" in src_chat and set(k) >= {"فرص صقر — السوق السعودي", "فرص صقر — السوق الأمريكي", "عقود الخيارات في دفتر صقر", "نظرة صقر لتاسي", "التقرير اليومي"},
      "٢ قناةُ صقر تمرّ من عمله أوّلاً (بلا نموذج لما يعرفه)، والنموذجُ لما سواه: تعليماتُه للسوقين وعقود الخيارات، وعملُ صقر ونبضُ السوق أوّلُ ما في سياقه",
      f"{res.get('source')} · {sorted(k)}")

# ── ٣ و٤ القائمةُ والأبوابُ والتقريرُ اليوميّ ──
from app.services import saqr_bot as SB  # noqa: E402
from app.services import research_paper as RP  # noqa: E402
import app.core.database as DBM  # noqa: E402


class _S:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

DBM.AsyncSessionLocal = lambda: _S()
calls: list = []


async def fake_call(method, **payload):
    calls.append((method, payload))
    return {"message_id": 7}


async def fake_file(data, name, caption="", chat=None):
    calls.append(("sendDocument", {"name": name, "caption": caption}))
    return {"ok": True}


async def fake_pdf(r, part="all"):
    return b"%PDF-1.4"


async def no_sum(db):
    raise RuntimeError("بلا قاعدة")

bot = SB.SaqrBot()
bot.token, bot.owner, bot.enabled = "t", "42", True
bot._call, bot.send_file, bot._summary = fake_call, fake_file, no_sum
RP.pdf = fake_pdf


def press(data=None, text=None, chat="42"):
    calls.clear()
    upd = {"callback_query": {"id": "q", "data": data, "message": {"message_id": 99, "chat": {"id": chat}}}} if data else \
          {"message": {"text": text, "chat": {"id": chat}}}
    asyncio.run(bot._handle(upd))
    return [(m, p) for m, p in calls if m not in ("answerCallbackQuery", "sendChatAction")]

menu_doors = [d for row in SB.MENU for _, d in row]
home = press("menu")
door = press("opps")
us = press("opps:us")
opt = press("opps:opt")
daily = press("daily")
older = press("daily:2026-11-22")
stranger = press("menu", chat="13")
check(menu_doors == ["opps", "daily", "pf", "mkt", "evt", "ask"] and home and home[0][0] == "editMessageText" and "فرص اليوم" in home[0][1]["text"]
      and "التقرير اليومي" in home[0][1]["text"] and door[0][0] == "editMessageText" and door[0][1]["message_id"] == 99
      and us[0][0] == "sendMessage" and "NVDA" in us[0][1]["text"] and "205.00" in us[0][1]["text"] and "NVDA261218C00190000" in opt[0][1]["text"]
      and stranger == [],
      "٣ القائمة: ستّةُ أبوابٍ بترتيب الطلب، والبابُ يُفتح في الرسالة نفسِها، والرئيسيةُ بطاقةُ حالٍ (الفرصُ وآخرُ تقرير) — والغريبُ لا يُجاب",
      f"{menu_doors} · {[m for m, _ in home + door + us]}")
check(daily and daily[0][0] == "sendDocument" and daily[0][1]["name"] == "daily-report-2026-11-24.pdf" and "التقرير اليومي" in daily[0][1]["caption"]
      and any("daily:2026-11-23" in str(p.get("reply_markup")) for _, p in daily[1:]) and older and older[0][1]["name"] == "daily-report-2026-11-22.pdf",
      "٤ التقريرُ اليوميّ ملفٌّ من القائمة — آخرُه بتعليقه المؤرَّخ، وأيامُه السابقةُ أزرارٌ تحته تفتح كلَّ يومٍ بملفّه",
      f"{[(m, p.get('name')) for m, p in daily + older]}")

print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
