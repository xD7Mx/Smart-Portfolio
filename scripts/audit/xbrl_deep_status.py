"""تقدّمُ الحصاد العميق (D547): آخرُ أسطر /tmp/xbrl_deep.log داخلَ الحاوية.

    docker exec sp_backend python /app/scripts/audit/xbrl_deep_status.py
"""
try:
    lines = open("/tmp/xbrl_deep.log", encoding="utf-8").read().splitlines()
except FileNotFoundError:
    lines = ["لم يبدأ الحصادُ العميق"]
for l in [x for x in lines if "XBRL" in x or "DONE" in x or "Error" in x][-12:]:
    print(l[-400:])
