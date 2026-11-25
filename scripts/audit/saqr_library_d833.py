#!/usr/bin/env python3
"""حارسُ D833 — صقرٌ يتعلّم من مكتبة المالك، داخلياً (المالك 2026-11-25).

قال المالك: «خلِّ صقر برضو يتعلّم من المكتبة اللي موجودة كتغذيةٍ أكاديميةٍ علمية — السوقين — خلّها داخليةً لا تخرج عندي، داخليةً عنده،
يتشرّب جميعَ المعلومات من الكتب اللي أنا حاطّها ومنتقيها بعناية».
كانت المكتبةُ تُدرس للطيار الآليّ وحده (مبادئُ المحفظة ‏D586) ولا يقرؤها صقرٌ في أيّ حكمٍ أو جواب.

  ١ صقرٌ يدرس الكتابَ بعين المتداول: مبادئُ من نصّه وحده برقم صفحةٍ موجودة (المختلَقةُ صفحتُها والطويلةُ تسقط)، تُحفظ مرّةً ولا يُعاد طلبُها.
  ٢ دراسةُ الفجر تشمل صقراً، وتعمل أيضاً بعد الإقلاع (لا ينتظر الفجر).
  ٣ علمُه من الكتب كلِّها بالتناوب (الأهمُّ أوّلاً، ومبادئُ المتداول قبل مبادئ الاستثمار في كلّ دورة)، بلا تكرار — والكتلةُ بلا عنوانٍ ولا صفحة، وبصمتُها
    تتغيّر بعلمٍ جديد.
  ٤ حكمُ صقر الأخير على كلّ صفقة (السوقان): العلمُ في توجيهه قبل الشواهد وخارجَها (فلا يُقتبس منه رقمٌ يمرّ على حارس الأرقام)، ويتجدّد الحكمُ بعلمٍ جديد،
    وما ذكر كتاباً أو المكتبةَ أو عنوانَ كتابٍ يُحذف من كلامه — وبلا مكتبةٍ مدروسة يبقى كما كان.
  ٥ جوابُ صقر للمالك: العلمُ منهجٌ في توجيهه لا بيانات، ولا يخرج في الجواب (إلا إن سأل المالكُ عن مكتبته)، والأسطرُ تبقى كما هي.

    python3 scripts/audit/saqr_library_d833.py
"""
import asyncio
import os
import pathlib
import sys
import tempfile

_SB = tempfile.mkdtemp(prefix="sp_d833_")
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


from app.services import ai_content as AC   # noqa: E402
from app.services import lastgood   # noqa: E402
from app.services import library_service as LS   # noqa: E402
from app.services import library_wisdom as LW   # noqa: E402


class Book:
    def __init__(self, i, title, author=None):
        self.id, self.title, self.author, self.page_count = i, title, author, 40


PAGE = "الاتجاهُ صديقُ المتداول، والسعرُ فوق متوسّطه الطويل يُشترى عند الارتداد لا عند المطاردة. " * 12
LS._read_pages = lambda bid: [PAGE] * 30
LS._looks_garbled = lambda p: False
calls: list[str] = []


async def fake_gen(prompt, key, ttl):
    calls.append(key)
    if key.startswith("ai:libsaqr"):
        return {"principles": [{"p": "لا تشترِ سهماً مسارُه هابطٌ مهما بدا رخيصاً", "page": 7, "kind": "مسار"},
                               {"p": "ضع الوقفَ تحت قاعدة الحجم لا عند رقمٍ مستدير", "page": 12, "kind": "حجم"},
                               {"p": "مبدأٌ بصفحةٍ مختلَقة", "page": 999, "kind": "مخاطر"},
                               {"p": " ".join(["كلمة"] * 30), "page": 3, "kind": "سلوك"}]}
    return {"principles": [{"p": "لا تخاطر بأكثر من 2٪ من رأس المال في صفقة", "page": 9, "kind": "مخاطر"}]}
AC._generate_obj = fake_gen

# ── ١ الدراسة ──
b = Book(1, "فنُّ المضاربة", "مؤلّفٌ ما")
r1 = asyncio.run(LW.saqr_digest(b))
n1 = len(calls)
r2 = asyncio.run(LW.saqr_digest(b))
stored = lastgood.load("lib:saqr:1") or {}
check(r1 and [p["page"] for p in r1["principles"]] == [7, 12] and stored.get("principles") == r1["principles"] and n1 == 1 and len(calls) == 1 and r2["principles"] == r1["principles"]
      and calls[0].startswith("ai:libsaqr:v1:1"),
      "١ صقرٌ يدرس الكتابَ بعين المتداول: مبادئُ من نصّه برقم صفحةٍ موجودة (المختلَقةُ صفحتُها والطويلةُ تسقط)، تُحفظ مرّةً ولا يُعاد طلبُها",
      f"{[p['page'] for p in (r1 or {}).get('principles', [])]} · نداءات {len(calls)}")

# ── ٢ الفجرُ وبعد الإقلاع ──
lw_src = (ROOT / "backend/app/services/library_wisdom.py").read_text(encoding="utf-8")
sch = (ROOT / "backend/app/scheduler/scheduler.py").read_text(encoding="utf-8")
da = lw_src[lw_src.index("async def digest_all("):lw_src.index("VISUAL_MAX_MB")]
check("await saqr_digest(b)" in da and 'id="library_wisdom_dawn"' in sch and 'id="library_wisdom_boot"' in sch
      and "job_library_wisdom, DateTrigger(" in sch,
      "٢ دراسةُ الفجر تشمل صقراً (الكتابُ نفسُه بعين المتداول)، وتعمل أيضاً بعد الإقلاع فلا ينتظر الفجر")

# ── ٣ العلم ──
asyncio.run(LW.digest(Book(1, "فنُّ المضاربة")))
lastgood.save("lib:saqr:2", {"book_id": 2, "title": "الخيارات للمحترفين", "principles": [
    {"p": "اشترِ العقدَ الطويلَ الأجل فالتآكلُ يتسارع قرب الانتهاء", "page": 40, "kind": "خيارات"},
    {"p": "لا تشترِ سهماً مسارُه هابطٌ مهما بدا رخيصاً", "page": 2, "kind": "مسار"}]})
ks = LW.saqr_knowledge(10)
txt, v1 = LW.saqr_block()
lastgood.save("lib:saqr:3", {"book_id": 3, "title": "سيكولوجيا السوق", "principles": [{"p": "التزم بخطّتك ولا تلاحق الخسارة", "page": 5, "kind": "سلوك"}]})
_, v2 = LW.saqr_block()
order = [k["p"] for k in ks]
check(len(order) == len(set(order)) == 4 and order[0] == "لا تشترِ سهماً مسارُه هابطٌ مهما بدا رخيصاً" and order[1].startswith("اشترِ العقدَ الطويل")
      and "لا تخاطر بأكثر من 2٪" in order[2] and order[3].startswith("ضع الوقفَ") and all(k.get("book") for k in ks)
      and txt and "فنُّ المضاربة" not in txt and "الخيارات للمحترفين" not in txt and "صفحة" not in txt and "• لا تشترِ سهماً" in txt and v1 and v2 != v1,
      "٣ علمُه من الكتب كلِّها بالتناوب — الأهمُّ من كلّ كتابٍ أوّلاً، وفي كلّ دورةٍ مبادئُ المتداول قبل مبادئ الاستثمار، بلا تكرار — والكتلةُ بلا عنوانٍ ولا صفحة، "
      "وبصمتُها تتغيّر بعلمٍ جديد",
      " | ".join(order) + f" · {v1} {v2} · {txt[:0]}" + str([x for x in ("فنُّ المضاربة", "صفحة") if x in txt]))

# ── ٤ حكمُ صقر الأخير ──
from app.services import cache   # noqa: E402
from app.services import research_desk as RD   # noqa: E402
from app.services import saqr_council as CN   # noqa: E402
seen: list[str] = []


async def gem(parts, max_tokens=0, temperature=0, **k):
    seen.append(parts[-1]["text"])
    return {"decision": "شراء", "confidence": "متوسطة", "link": "المسارُ صاعدٌ فوق متوسّطه والحجمُ يدعم. وكما في كتاب الخيارات للمحترفين: لا تطارد.",
            "conflict": "قال سيكولوجيا السوق إنّ الخطّة أوّلاً.", "watch": "كسرُ 85 يغيّر الحكم."}
RD._gemini = gem
BD = {"members": [{"role": "المسار", "v": "ok", "say": "مسارٌ صاعد فوق 85"}], "verdict": "يوافق", "score": 80, "veto": False}
lk = asyncio.run(CN.link("1120", "الراجحي", "sa", "long", BD, price=90))
p0 = seen[-1]
lastgood.save("lib:saqr:4", {"book_id": 4, "title": "كتابٌ رابع", "principles": [{"p": "اقرأ الحجمَ قبل السعر", "page": 3, "kind": "حجم"}]})
lk2 = asyncio.run(CN.link("1120", "الراجحي", "sa", "long", BD, price=90))
i_lib, i_ev = p0.find("علمُك الأكاديميّ"), p0.find("الشواهد:\n")
o_kn = LW.saqr_knowledge
LW.saqr_knowledge = lambda limit=24: []                          # مكتبةٌ لم يُدرس منها شيءٌ بعد
cache._store.clear()
n_before = len(seen)
lk3 = asyncio.run(CN.link("1120", "الراجحي", "sa", "long", BD, price=90))
p3 = seen[-1]
LW.saqr_knowledge = o_kn
check(lk and 0 < i_lib < i_ev and "• لا تشترِ سهماً مسارُه هابط" in p0 and "فنُّ المضاربة" not in p0 and len(seen) >= 2 and lk2 is not None and n_before == 2
      and "كتاب" not in lk["link"] and "المسارُ صاعدٌ" in lk["link"] and lk["conflict"] == "" and "كسرُ 85" in lk["watch"]
      and "علمُك الأكاديميّ" not in p3 and lk3 and "كتاب الخيارات" in lk3["link"],
      "٤ حكمُ صقر الأخير على كلّ صفقة: العلمُ في توجيهه قبل الشواهد وخارجَها، ويتجدّد الحكمُ بعلمٍ جديد، وما ذكر كتاباً أو عنواناً يُحذف من كلامه — "
      "وبلا مكتبةٍ مدروسة يبقى كما كان",
      f"link={lk and lk['link']!r} · conflict={lk and lk['conflict']!r} · watch={lk and lk['watch']!r} · {0 < i_lib < i_ev} {len(seen)} {n_before} {bool(lk2)} {lk3 and lk3['link']!r} {'علمُك الأكاديميّ' in p3}")

# ── ٥ جوابُ صقر للمالك ──
chat = (ROOT / "backend/app/services/ai_chat.py").read_text(encoding="utf-8")
blk = chat[chat.index("rules = SYSTEM_RULES"):chat.index("prompt = (f\"{rules}")]
fin = chat[chat.index('text = _strip_markup(text)\n        if lib_titles'):chat.index('return {"reply": text, "grounded": True, "source": "ai"}')]
kept = LW.scrub("سطرٌ أوّل.\n- بندٌ ثانٍ", ["فنُّ المضاربة"])
check("LW.saqr_block(18)" in blk and "منهجٌ تحلّل به لا بياناتٌ" in blk and 're.search(r"كتاب|كتب|مكتب", question)' in blk and "LW.scrub(text" in fin
      and kept == "سطرٌ أوّل.\n- بندٌ ثانٍ",
      "٥ جوابُ صقر للمالك: العلمُ منهجٌ في توجيهه لا بيانات، ولا يخرج في الجواب (إلا إن سأل المالكُ عن مكتبته)، والأسطرُ تبقى كما هي")

print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
