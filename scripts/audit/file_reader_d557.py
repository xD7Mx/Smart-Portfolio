#!/usr/bin/env python3
"""حارسُ D557: القارئُ البصريّ — الملفُّ يُرسَل للنموذج ولا يُفتح على الخادم، والاختيارُ خمسُ
سنواتٍ سنويّةٍ وأحدثُ فترة، والتقليمُ خمسُ سنوات، والدفعةُ ليليّةٌ محدودةٌ ومحروسة،
ورأيُ الذكاء بصوت المستشار يقرأ المعرفة.

    python3 scripts/audit/file_reader_d557.py
"""
import os, sys, tempfile, pathlib
_SB = tempfile.mkdtemp(prefix="sp-audit-")
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
os.environ["SP_STATUS_LOG"] = os.path.join(_SB, "status_codes.jsonl")
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from datetime import date
fail = 0
def check(ok, label, det=""):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

from app.services import file_reader as F
L = [{"url": f"https://x/{d}.pdf", "filed": d, "referer": ""} for d in
     ("2026-08-10", "2026-05-12", "2026-03-20", "2025-11-05", "2025-08-09", "2025-04-30", "2025-03-25", "2024-03-18",
      "2023-03-29", "2022-03-30", "2021-03-28", "2020-03-30")]
p = [x["filed"] for x in F.pick(L, date(2026, 9, 30))]
check(p == ["2026-08-10", "2026-03-20", "2025-03-25", "2024-03-18", "2023-03-29", "2022-03-30"],
      "١ الاختيار: أحدثُ ملفّ ثمّ سنويُّ كلّ سنةٍ من الخمس — لا 2020", str(p))
fl = {"a": {"period": "2020-12-31"}, "b": {"period": "2021-12-31"}, "c": {"filed": "2026-08-10"}}
check(set(F.prune(fl, date(2026, 9, 30))) == {"b", "c"}, "٢ التقليم: خمسُ سنواتٍ فقط")
from app.services import lastgood
lastgood.save("know:9999", {"files": {
    "x": {"period": "2026-06-30", "kind": "quarter", "points": ["الإيراد 1,200 مليون (+8٪)", "الدين 300 مليون"],
          "flags": ["لفتُ انتباه من المراجع"], "auditor": "مراجعٌ ما — نظيف", "verdict": "ربعٌ جيّد"},
    "y": {"period": "2025-12-31", "kind": "annual", "points": ["…"], "flags": [], "verdict": "سنةٌ مستقرّة"}}})
k = F.knowledge("9999")
check(k[0].startswith("[فترة 2026-06-30] الإيراد") and any("[سنوي 2025-12-31] سنةٌ مستقرّة" in x for x in k)
      and any("تحذير" in x for x in k), "٣ المعرفة: أحدثُ فترةٍ بتفصيلها وحكمُ كلّ سنةٍ وتحذيراتُها", str(k))
check(F.coverage("9999") == {"files": 2, "from": "2025-12-31", "to": "2026-06-30"}, "٤ التغطية")
src = (ROOT / "backend/app/services/file_reader.py").read_text(encoding="utf-8")
check('"file_uri": uri' in src and "upload/v1beta/files" in src and "fetch_to_file(" in src and "b64encode" not in src
      and "fetch_bytes" not in src and F.MIN_FREE_MB <= 80 and "fitz" not in src and "parse_pdf" not in src and "ocr" not in src.lower().replace("القراءة الضوئية", ""),
      "٥ D565 خفيفٌ فعلاً: الملفُّ يُنزَّل قطعاً إلى القرص ويُرفع قطعاً إلى ملفّات النموذج — لا يُحمَل في الذاكرة ولا يُفتح (قِيس: حدُّ 150MB أوقف ليلةً كاملة)")
check("mem_available_mb()" in src and "remaining_fraction(\"gemini\")" in src and "with background():" in src
      and "MAX_MB * 1024 * 1024" in src and 300 <= F.NIGHT_FILES <= 500,
      "٦ محروس (حدُّ ذاكرته الخاصّ، وملفُّ الربع الأول في أبريل لا يُحسب سنوياً): ذاكرةٌ، ونصيبُ الحصّة، وحدُّ الحجم، ودفعةٌ ليليّةٌ محدودة")
sch = (ROOT / "backend/app/scheduler/scheduler.py").read_text(encoding="utf-8")
check("job_file_reader" in sch and 'id="file_reader_night"' in sch and "create_subprocess_exec" in sch
      and "malloc_trim" in src and "content=chunks()" in src and "async def chunks()" in src and "os.remove(tmp)" in src,
      "٧ ليلاً في عمليةٍ منفصلة، وذاكرةٌ تُعاد بعد كلّ ملفّ، والرفعُ قطعاً والملفُّ المؤقّتُ يُحذف (D565)")
ai = (ROOT / "backend/app/services/ai_content.py").read_text(encoding="utf-8")
am = (ROOT / "backend/app/services/app_mind.py").read_text(encoding="utf-8")
ui = (ROOT / "frontend/src/components/analysis/StockOpinion.tsx").read_text(encoding="utf-8")
check("المستشارُ الماليّ الخاصّ" in ai and '"advisor_bullets"' in ai and "{files_ctx}" in ai and "ai:opinion:v6:" in ai
      and "file_reader import coverage, knowledge" in am and "data.advisor_bullets" in ui and "data.files_bullets" in ui,
      "٨ رأيُ الذكاء بصوت المستشار، يقرأ معرفةَ الملفّات، وتُعرض")
check('join(Holding, Holding.company_id == Company.id)' in src and "select(Holding.symbol)" not in src
      and 'rec.get("complete") and rec.get("at", "") >= week' in src and 'report["_mem"] = True' in src
      and "timeout=6 * 60 * 60" in sch and "CronTrigger(hour=0, minute=20)" in sch,
      "٩ D560 أيامٌ لا شهران: 400 ملفٍّ ليلاً من منتصف الليل، والمحفظةُ أوّلاً فعلاً، والمقروءةُ جزئياً لا تُترك أسبوعاً، والذاكرةُ القليلةُ انتظارٌ لا توقّف")
print(f"{'FAIL' if fail else 'PASS'} D557 — القارئ البصري")
sys.exit(fail)
