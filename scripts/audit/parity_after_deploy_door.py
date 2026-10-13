"""كاشف (قراءةٌ فقط): لماذا تخالف الصفحةُ الفرزَ بعد نشرٍ في منتصف اليوم؟ — 1321 · 2270 · 4190 (السعر العادل) و4013 (القرار).

بعد نشر 2.4 (‏run 38390787359: إعادةُ الخادم 11:31 ثمّ حصادُ قوائم ثمّ مسحةٌ 11:40–11:47) قالت بوابةُ رقم اليوم مرّتين:
السعرُ العادل ≠ الفرز 3 · القرار 1. فلكلّ واحدةٍ: تحليلُ الصفحة المخزَّن (مفتاحُه · رقمُه · تاريخُ مسحته · قرارُه وسقفُه وسعرُه)،
وصفُّ المسحة الرسميّ (رقمُه وتاريخُه)، والمخزنُ العميق (القرارُ وسقفُه ومصدرُه ويومُه ومحرّكُه).

    docker exec sp_backend python /app/scripts/audit/parity_after_deploy_door.py
"""
import json
import sys

sys.path.insert(0, "/app")

from app.services import cache, lastgood   # noqa: E402
from app.services.analysis import _ENGINE_V, official_row   # noqa: E402
from app.services.governance_rules import rules_version   # noqa: E402
from app.services.content_engine import fund_store_load   # noqa: E402
from app.services.market_screener import served_decision   # noqa: E402

store = fund_store_load() or {}
deep = lastgood.load("governance:deep") or {}
cut = lambda d, ks: {k: d.get(k) for k in ks} if isinstance(d, dict) else d   # noqa: E731
for s in ("1321", "2270", "4190", "4013"):
    off = official_row(s) or {}
    ck = f"analysis:{s}.SR:{rules_version()}:{_ENGINE_V}:official:{off.get('score_asof') or 'live'}"
    a = cache.get(ck)
    st = store.get(s) or {}
    d = deep.get(s) or {}
    print(f"══ {s}")
    print("   مفتاحُ الصفحة:", ck, "· مخزَّن" if a is not None else "· غيرُ مخزَّن")
    if isinstance(a, dict):
        print("   الصفحة:", json.dumps({"fv": a.get("fair_value"), "official_asof": a.get("fair_value_official_asof"),
                                       "price": a.get("price"), "decision": cut(a.get("decision"), ("raw", "rule_id")),
                                       "ceiling": cut(a.get("decision_ceiling"), ("fair_value", "entry_price", "base"))},
                                      ensure_ascii=False, default=str))
    print("   المسحة:", json.dumps(cut(st, ("fair_value", "fair_value_conf", "score_asof", "stmt_asof")), ensure_ascii=False))
    print("   العميق:", json.dumps({"decision": cut(d.get("decision"), ("raw", "rule_id")), "source": d.get("source"),
                                   "at": d.get("at"), "v": d.get("v"), "engine_now": _ENGINE_V,
                                   "ceiling": cut(d.get("ceiling"), ("fair_value", "entry_price", "base")),
                                   "served_at_page_price": served_decision(d, (a or {}).get("price") if isinstance(a, dict) else None)},
                                  ensure_ascii=False, default=str))
    # وهل في الذاكرة نسخٌ أخرى لتحليل الصفحة لهذه الشركة؟
    try:
        ks = [k for k in (getattr(cache, "keys", lambda *_: [])(f"analysis:{s}.SR") or [])]
        print("   مفاتيحُ التحليل:", ks[:6])
    except Exception as e:                                         # noqa: BLE001
        print("   مفاتيحُ التحليل: تعذّر", type(e).__name__)
