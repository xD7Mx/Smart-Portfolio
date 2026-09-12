#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D242 — الكونُ ينمو مع السوق، ولا يفقد أحداً.
#
# سأل المالك: شركةٌ أوقفتها «تداول» أتختفي؟ وإن عادت أترجع؟ واكتتابٌ
# جديدٌ أيظهر؟ فكان الجوابُ: لا تختفي وتشيخ صامتةً، وتعود وحدَها،
# **والاكتتابُ لا يظهر أبداً**. فبُنيت مزامنةٌ أسبوعيةٌ مع «تداول».
#
# وخطرُ المزامنة أعظمُ من خطر السكون: جلبٌ فاشلٌ يُقرأ «سوقاً تقلّص»
# فيُمحى نصفُ الكون. فيُقاس السلوكُ بمزوّدٍ مموَّه:
#   ١· الجديدُ يُضاف باسمه وقطاعه
#   ٢· والغائبُ **لا يُحذف** بل يُوسَم موقوفاً بتاريخه
#   ٣· والعائدُ يُرفع وسمُه
#   ٤· وقائمةٌ قصيرةٌ تُرفَض كلُّها — لا تُوسَم على أساسها
#   ٥· والطبقةُ تصل الشاشاتَ من المصدر الواحد لا من مصدرٍ ثانٍ
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os as _os
import tempfile as _tf

_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

import asyncio  # noqa: E402
import pathlib  # noqa: E402
import sys  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

fail = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))


from app.services import tadawul_sync as ts  # noqa: E402

# ── ١ · الفهمُ من الشكلين ────────────────────────────────────────────────
html = ("<table><tr><th>الرمز</th><th>الشركة</th></tr>"
        "<tr><td>2222</td><td>أرامكو السعودية</td></tr>"
        "<tr><td>9500</td><td>شركةُ اكتتابٍ جديدة</td></tr></table>")
js = '{"data":[{"symbol":"2222","companyNameAr":"أرامكو السعودية","sectorNameAr":"الطاقة"}]}'
h, j = ts.parse_listed(html), ts.parse_listed(js)
check(h.get("9500", {}).get("name") == "شركةُ اكتتابٍ جديدة" and len(h) == 2,
      "١ يُفهم جدولُ HTML — رمزٌ رباعيٌّ واسمٌ عربيّ", f"{len(h)} رمزاً")
check(j.get("2222", {}).get("sector") == "الطاقة",
      "٢ ويُفهم JSON بحقوله العربية", str(j.get("2222")))

# ── ٣ · قائمةٌ قصيرةٌ تُرفَض — جلبٌ فشل لا سوقٌ تقلّص ────────────────────
async def _tiny(url):
    return 200, html


# ══ يُموَّه المَعبرُ لا العميلُ القديم ══ (بعد D250)
# كانت المزامنةُ تجلب بعميل «الإعلانات»، فكان التمويهُ هناك. وقد صارت
# تجلب من `tadawul_http.fetch` — فبقي التمويهُ على المهجور، وخرج الفحصُ
# إلى الإنترنت فقاس حالةَ البروكسي لا قاعدةَ الرفض. فيُموَّه المَعبر.
import app.services.tadawul_announcements as _ann  # noqa: E402
import app.services.tadawul_http as _th  # noqa: E402


async def _tiny_gw(url, **kw):
    return 200, html


_ann._raw_fetch = _tiny                                          # type: ignore[assignment]
_th.fetch = _tiny_gw                                             # type: ignore[assignment]


async def _no_argaam():
    return {}


# ولا شبكةَ في اللجنة: مصدرُ «أرقام» يُموَّه أيضاً، وإلا خرج الفحصُ إلى
# الإنترنت فصار يقيس حالةَ البروكسي لا قاعدةَ الرفض.
ts._argaam_listed = _no_argaam                                   # type: ignore[assignment]
listed, why = asyncio.run(ts.fetch_listed())
check(not listed and "الحدّ" in (why or ""),
      "٣ قائمةٌ دون الحدّ تُرفَض ويُقال سببُها", str(why))

# ── ٤ · الخطّةُ: جديدٌ · موقوفٌ · عائد ───────────────────────────────────
from app.data.saudi_directory import SAUDI_DIRECTORY as DIR  # noqa: E402

real = sorted(DIR)[:250]
full = {s: {"name": (DIR[s].get("name") or s)} for s in real}
full["9500"] = {"name": "شركةُ اكتتابٍ جديدة", "sector": "الطاقة"}
p = ts.plan(full)
gone_sym = sorted(set(DIR) - set(full))[0]
check(any(r["symbol"] == "9500" for r in p["added"]),
      "٤ الاكتتابُ الجديد يُضاف", f"جديد {len(p['added'])}")
check(any(r["symbol"] == gone_sym for r in (p.get("absent_once") or []) + p["suspended"]),
      "٥ والغائبُ عن قائمة «تداول» يُرشَّح للإيقاف",
      f"مرشَّح {len((p.get('absent_once') or []) + p['suspended'])} · منها {gone_sym}")

# ══ غيابٌ مرّةً لا يكفي ══ (D245 · بعد أوّل تشغيلٍ حقيقيّ)
# رشّح التشغيلُ الأوّلُ عشرةَ رموزٍ للإيقاف، وفيها ثلاثةٌ مدرَجةٌ فعلاً —
# فغيابُها عن قائمةٍ واحدةٍ ثقبُ جلبٍ لا حقيقةُ سوق. فالوسمُ بعد غيابين.
check(not p["suspended"] and any(r["symbol"] == gone_sym
                                 for r in p.get("absent_once") or []),
      "٥ب وأوّلُ غيابٍ يُعَدّ ولا يُوسَم",
      f"موقوف {len(p['suspended'])} · غائبٌ مرّةً {len(p.get('absent_once') or [])}")
ts.apply_plan(p)
p = ts.plan(full)                      # التشغيلةُ الثانية: غيابٌ ثانٍ
check(any(r["symbol"] == gone_sym for r in p["suspended"]),
      "٥ج والغيابُ الثاني يُوسَم موقوفاً", f"موقوف {len(p['suspended'])}")

applied = ts.apply_plan(p)
ov = ts.overlay()
check(ov.get("9500", {}).get("name") == "شركةُ اكتتابٍ جديدة"
      and ov.get(gone_sym, {}).get("suspended") is True
      and ov[gone_sym].get("since"),
      "٦ والطبقةُ تحفظ الاثنين — إضافةً ووسمَ إيقافٍ بتاريخه",
      f"{applied}")

# ── والتسميةُ المختصرةُ لا تُطبَّق ──
sym0 = sorted(set(DIR))[0]
short = dict(full)
short[sym0] = {"name": "مختصر"}
p3 = ts.plan(short)
ts.apply_plan(p3)
check((ts.overlay().get(sym0) or {}).get("name") != "مختصر",
      "٦ب واسمُ المتابعة المختصر يُسجَّل ولا يُكتب — أسماؤنا منسَّقة",
      f"في الطبقة: {(ts.overlay().get(sym0) or {}).get('name')}")

# ══ والتقريرُ يعُدّ ما كُتب ══ (D246)
# قال التقريرُ في التشغيل الحقيقيّ «‏renamed: 138» وهو لم يكتب واحدةً —
# فعدَّ الخطّةَ وسمّاها تطبيقاً. وتقريرٌ يقول ما لم يفعل أخطرُ من سكوت.
rep = ts.apply_plan(ts.plan(short))
check(rep.get("renamed") == 0 and rep.get("renamed_reported_only", 0) >= 1,
      "٦ج والتقريرُ يعُدّ المكتوبَ ويفصل المسجَّلَ عنه",
      f"مكتوب {rep.get('renamed')} · مسجَّلٌ فقط {rep.get('renamed_reported_only')}")

# ── ٧ · ولا حذفَ أبداً: الموقوفةُ تبقى معروفةً بالاسم ───────────────────
check(gone_sym in DIR and (DIR[gone_sym].get("name")),
      "٧ ولا يُمحى صفُّ الموقوفة — تاريخُ المالك لا يُفقد",
      f"{gone_sym} · {DIR[gone_sym].get('name')}")

# ── ٨ · والعودةُ ترفع الوسمَ ────────────────────────────────────────────
back = dict(full)
back[gone_sym] = {"name": DIR[gone_sym].get("name") or gone_sym}
p2 = ts.plan(back)
check(any(r["symbol"] == gone_sym for r in p2["resumed"]),
      "٨ والعائدةُ إلى التداول يُرفع وسمُها", f"عائد {len(p2['resumed'])}")
ts.apply_plan(p2)
check(not (ts.overlay().get(gone_sym, {}) or {}).get("suspended"),
      "٩ ويُكتب الرفعُ فعلاً لا في التقرير وحدَه")

# ── ١٠ · والوسمُ يصل الشاشاتَ من المصدر الواحد ──────────────────────────
src = (ROOT / "backend/app/data/saudi_directory.py").read_text(encoding="utf-8")
check("market:directory_overlay" in src and "def is_suspended" in src,
      "١٠ الطبقةُ تُقرأ في دليل السوق نفسِه — لا مصدرَ هويةٍ ثانٍ")

# ── ١١ · والمزامنةُ مجدولةٌ فعلاً ───────────────────────────────────────
sch = (ROOT / "backend/app/scheduler/scheduler.py").read_text(encoding="utf-8")
check("job_directory_sync" in sch and "directory_sync_weekly" in sch,
      "١١ ومجدولةٌ أسبوعياً — لا دالّةٌ لا ينادِيها أحد")

print()
print("النتيجة:", "فيه ملاحظات ✘" if fail else "نظيف ✔")
raise SystemExit(fail)
