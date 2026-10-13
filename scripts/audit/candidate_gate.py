#!/usr/bin/env python3
"""قياسُ الإصدار المرشَّح قبل نشره (‏D642) — طريقُ الإصدار الثاني عبر حارس التجميد.

البوابةُ تقرأ المخزنَ الذي تكتبه مسحةُ الإنتاج، فقياسُها كما هي يعني نشرَ المرشَّح قبل اعتماده. فهذا الكاشف:
  ١ يحسب كلَّ شركةٍ بشيفرة المرشَّح داخل عمليّته (`_one` من المسحة — بلا كتابةٍ في أيّ مخزن)،
  ٢ يبني مخزناً ومخزنَ أحكامٍ في الذاكرة فوق الحاليَّين،
  ٣ يُشغّل البوابتين عليهما — فتخرج مقاييسُ المرشَّح وأرقامُ الإنتاج على الإصدار المجمَّد لم تُمسّ.

    docker exec sp_backend python /app/scripts/audit/candidate_gate.py

ثمّ: `engine_report_save.py <مخرَج السعر العادل> <مخرَج المحرّكات ٢–٥>` لبصمة المرشَّح، ويحكم حارسُ التجميد."""
import asyncio, hashlib, os, runpy, sys
# ‏D696: شاهدُ الأساس في الجولة نفسِها — `SP_CODE_ROOT` جذرُ شيفرةٍ أخرى (الأساسُ المجمَّد من `git archive` · مهمّةُ
# `candidate_ab` في ops.yml) يُحمَّل منه `app` أوّلاً، فتُحلّ كلُّ وحداته من مسار تلك الحزمة لا من `/app` (حزمةٌ نظاميّة:
# مسارُها ثابتٌ وإن أُضيف `/app` إلى sys.path بعدها). والبياناتُ واحدة: المخازنُ نفسُها والساعةُ نفسُها.
_ROOT = os.environ.get("SP_CODE_ROOT") or "/app"
sys.path.insert(0, _ROOT)
import app as _app   # noqa: E402,F401  — يُثبّت الحزمةَ من الجذر المختار
sys.path.insert(1, "/app/scripts/audit")
from engine_freeze_d635 import FILES as _FILES, ROOT as _FROOT   # noqa: E402


def _fp(root: str) -> str:
    """بصمةُ المحرّكات بخوارزمية حارس التجميد نفسِها — على الملفّات التي تُشغَّل فعلاً تحت `root` (‏/app = backend)."""
    h = hashlib.sha1()
    for f in _FILES:
        rel = f.relative_to(_FROOT).as_posix()
        h.update(rel.encode())
        q = os.path.join(root, rel[len("backend/"):]) if rel.startswith("backend/") else os.path.join(root, rel)
        h.update(open(q, "rb").read() if os.path.exists(q) else b"<missing>")
    return h.hexdigest()[:12]


_FP = _fp(_ROOT)
assert os.path.dirname(os.path.dirname(_app.__file__)) == os.path.normpath(_ROOT), f"app من {_app.__file__} لا من {_ROOT}"
# ‏D650: لا يمسّ الإنتاجَ شيءٌ من قياس المرشَّح. الكاشُ الطويل يُكتب إلى قرصٍ يشاركه الخادم ويمتصّ منه ما انتهاؤه أبعد
# (D582) — فقيمةُ مرشَّحٍ تحت مفتاحٍ لم يتغيّر كانت تصل الإنتاجَ ساعات. فالكاشُ هنا في الذاكرة وحدها (عمرٌ دون عتبة
# الحفظ)، ولقطاتُ «آخر سليم» لا تُكتب.
from app.services import cache as _cache, lastgood as _lg   # noqa: E402
_set0 = _cache.set
_cache.set = lambda key, value, ttl: _set0(key, value, min(ttl, _cache._PERSIST_MIN_TTL - 60))
_lg.save = lambda *a, **k: None
# ‏D696: والجانبان يحسبان نماذجَ السعر العادل من البيانات نفسِها الآن — مفتاحُ كاشها (‏fvm:vNN:{sym}) بلا إصدار محرّك، فكان
# الشاهدُ يقرأ ما حسبه الإنتاجُ صباحاً بسعره والمرشَّحُ (بمفتاحٍ مُرقّى) يحسب الآن (قِيس: run 38422895101 · الرياض ريت عند
# حدّ 60٪ في جانبٍ دون الآخر). فتُنزع من ذاكرة هذه العمليّة وحدها، ولا يُكتب القرصُ منها أبداً فلا يُمسّ كاشُ الإنتاج.
_cache._flush = lambda *a, **k: None
with _cache._lock:
    for _k in [k for k in _cache._store if k.startswith("fvm:")]:
        _cache._store.pop(_k, None)
from app.data.market_universe import MARKET_UNIVERSE
from app.data.universe import main_market
from app.data.universe import is_nomu
from app.services import content_engine, lastgood
from app.services.market_valuation_sweep import _one


async def compute():
    syms = sorted(s for s in main_market(MARKET_UNIVERSE) if not is_nomu(s))
    sem = asyncio.Semaphore(8)
    res = await asyncio.gather(*(_one(s, sem) for s in syms), return_exceptions=True)
    return {r[0]: r[1] for r in res if isinstance(r, tuple)}


done = asyncio.run(compute())
store0 = content_engine.fund_store_load()
store = {k: dict(v) for k, v in store0.items()}
deep = {k: (dict(v) if isinstance(v, dict) else v) for k, v in (lastgood.load("governance:deep") or {}).items()}
for s, v in done.items():
    vd = v.pop("_verdict", None) or {}
    v.pop("_failed", None)
    store[s] = {**(store.get(s) or {}), **v}
    if vd.get("decision") is not None or "red_lines" in vd:
        deep[s] = {**(deep.get(s) or {}), **({"decision": vd["decision"]} if vd.get("decision") is not None else {}),
                   **({"ceiling": vd["ceiling"]} if vd.get("ceiling") else {}),      # ‏D690: مُدخَلاتُ سقف القيمة العادلة
                   **({"red_lines": vd["red_lines"]} if "red_lines" in vd else {})}

_orig_load = lastgood.load
content_engine.fund_store_load = lambda: store
lastgood.load = lambda key, *a, **k: deep if key == "governance:deep" else _orig_load(key, *a, **k)
print(f"@@CANDIDATE@@ حُسبت {len(done)} شركةً بشيفرة {_ROOT} (بصمة {_FP}) — بلا كتابةٍ في المخزن\n")
print("════ بوابةُ السعر العادل ════")
print(f"@@ENGINE_FP@@ {_FP} · {_ROOT}")
runpy.run_path("/app/scripts/audit/engine_gate.py", run_name="__main__")
print("\n════ بوابةُ المحرّكات ٢–٥ ════")
print(f"@@ENGINE_FP@@ {_FP} · {_ROOT}")
runpy.run_path("/app/scripts/audit/engines_gate_v1.py", run_name="__main__")
print("\n════ بوابةُ رقم اليوم ════")                         # ‏D649: صفحاتُ المرشَّح مقابل فرزه
print(f"@@ENGINE_FP@@ {_FP} · {_ROOT}")
runpy.run_path("/app/scripts/audit/parity_gate.py", run_name="__main__")
print("\n════ بوابةُ ثبات رقم اليوم (السعرُ +2٪ بعد المسحة) ════")
print(f"@@ENGINE_FP@@ {_FP} · {_ROOT}")
runpy.run_path("/app/scripts/audit/parity_shift_gate.py", run_name="__main__")
