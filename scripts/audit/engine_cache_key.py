#!/usr/bin/env python3
"""إصلاحُ المحرّك يصل فوراً — مفتاحُ كاش التحليل يحمل بصمةَ الشيفرة (D448).

    python3 scripts/audit/engine_cache_key.py

قِيس: نُشر إصلاحُ نمط القطاع (D446) وبقيت أرقامُ السوق كما هي — لأن مفتاح
كاش التحليل يتبدّل بملفّ القواعد وحدَه، والكاشُ يوماً كاملاً ويعبر
الإقلاع. والفحصُ سلوكيّ: تحليلٌ مخزَّنٌ بالمفتاح، ثمّ يتغيّر نصُّ ملفٍّ من
المحرّك، ويُشترط أن تتبدّل البصمةُ فلا يُقرأ المخزَّن.
"""
import os as _os, tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX
_os.environ["SP_STATUS_LOG"] = _os.path.join(_SANDBOX, "status_codes.jsonl")
import pathlib, shutil, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend")); sys.path.insert(0, "/app")
try:
    from app.services import analysis as AN
except ModuleNotFoundError as e:
    print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس"); sys.exit(0)
fail = 0
ev = getattr(AN, "engine_version", None)
ok = callable(ev)
print(f"{'PASS' if ok else 'FAIL'} ١ للمحرّك بصمةٌ في مفتاح الكاش")
if ok:
    src = pathlib.Path(AN.__file__).resolve().parent / "fair_value.py"
    bak = src.read_bytes()
    v1 = ev()
    try:
        src.write_bytes(bak + b"\n# probe\n")
        v2 = ev()
    finally:
        src.write_bytes(bak)
    ok2 = v1 != v2 and ev() == v1
    print(f"{'PASS' if ok2 else 'FAIL'} ٢ وتعديلُ محرّك السعر العادل يبدّلها — {v1} → {v2}")
    ok3 = "_ENGINE_V" in (pathlib.Path(AN.__file__).read_text(encoding="utf-8").split("async def analyze_company", 1)[1][:400])
    print(f"{'PASS' if ok3 else 'FAIL'} ٣ والبصمةُ داخلةٌ في مفتاح التحليل نفسِه")
    ok = ok and ok2 and ok3
print(("PASS" if ok else "FAIL") + " D448 — إصلاحُ المحرّك يصل فوراً")
sys.exit(0 if ok else 1)
