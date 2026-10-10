"""كاشف D670: ختمُ دورة «تداول» في المفكرة — هل يعمل المجدوِلُ في الإنتاج، وكم وصل وبأيّ لغة، وما في المخزن منه.
قراءةٌ فقط: لا يجلب ولا يكتب.

    docker exec sp_backend python /app/scripts/audit/d670_stamp_door.py
"""
import json
import re
import sys
from collections import Counter

sys.path.insert(0, "/app")


def main():
    from app.services import lastgood
    from app.services.content_engine import _cal_load_store
    st = lastgood.load("market:calendar:tadawul_run")
    print("═ الختم: " + (json.dumps(st, ensure_ascii=False, default=str)[:900] if st else "غائب — لم تدُر الدورةُ منذ النشر"))
    store = _cal_load_store()
    tw = [e for e in store.values() if e.get("source") == "تداول"]
    ar = [e for e in tw if re.search(r"[؀-ۿ]", e.get("title") or "")]
    print(f"═ المخزن {len(store)} · من تداول {len(tw)} · عربيةٌ {len(ar)} · بلا رمز {sum(1 for e in tw if not e.get('symbol'))}")
    days = Counter(str(e.get("date") or "")[:10] for e in tw)
    print("   أحدثُ الأيام: " + ", ".join(f"{d} ({n})" for d, n in sorted(days.items(), reverse=True)[:6]))
    for e in sorted(tw, key=lambda x: str(x.get("date") or ""), reverse=True)[:3]:
        print(f"   {e.get('date')} · {e.get('symbol')} · {str(e.get('title'))[:90]}")


main()
