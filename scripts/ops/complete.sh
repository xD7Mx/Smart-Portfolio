#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────
# أمرٌ واحدٌ يُكمل الدورةَ ويطبع حكماً — للمالك حين يعود إلى الخادم.
#
#   bash scripts/ops/complete.sh            كلُّ شيءٍ بالترتيب
#   bash scripts/ops/complete.sh --no-sweep بلا مسحةِ التقييم (أسرع)
#
# ولا يبني حزمةً ولا يسلّم شيئاً: البناءُ بإذنٍ صريحٍ وحدَه (بند الميثاق
# الثالث)، وهذا يهيّئ ويقيس ويقول ما بقي.
#
# الترتيبُ معلَنٌ ولكلّ خطوةٍ سببُها:
#   ١· تسويةُ الشجرة كاملةً — لا سحبٌ جزئيٌّ يجعل اللجنةَ تحكم على
#      ملفٍّ قديم (‏D376).
#   ٢· إعادةُ الخادم ليقرأ الشفرةَ الجديدة.
#   ٣· لقطةُ «تداول» تُجلَب صريحةً — عمليةٌ جديدةٌ لا ترث مخزَنَ الخادم
#      (‏D397).
#   ٤· حصادُ القوائم لمن شاخ إيداعُه أو غاب.
#   ٥· مسحةُ التقييم: درجةٌ وسعرٌ عادلٌ لكلّ شركةٍ في الرئيسيّ (273).
#   ٦· سلسلةُ المعلومة حلقةً حلقةً (‏chain_integrity).
#   ٧· لجنةُ كشف الأعطال — البوّابةُ التي لا يُسلَّم دونها.
# ─────────────────────────────────────────────────────────────────────────
set -u
cd "$(dirname "$0")/../.." || exit 2
BR="claude/sharp-tesla-dwc2xg"
C="${SP_CONTAINER:-sp_backend}"
SWEEP=1
[ "${1:-}" = "--no-sweep" ] && SWEEP=0

say() { printf '\n══ %s ══\n' "$1"; }

say "١ · تسويةُ الشجرة على $BR"
git fetch origin "$BR" && git checkout FETCH_HEAD -- . && \
  echo "الشجرةُ عند $(git rev-parse --short FETCH_HEAD)" || \
  { echo "✘ تعذّرت التسوية — تُراجَع الشبكةُ أو الصلاحيات"; exit 1; }
# ‏D715: والتسويةُ تامّة — `checkout -- .` يكتب الملفّاتِ ولا يحذف ما حُذف من الفرع، فبقيت على الخادم ملفّاتٌ محذوفة
# (قِيس: ‏investor_calls.py · InvestorCalls.tsx). فيُثبَّت المستودعُ على إيداع الفرع، ويُزال من القرص ما يقول تاريخُ الفرع
# إنه حُذف — وحده: لا يُمسّ ملفٌّ لا تاريخَ له (‏.env · البيانات).
git -c advice.detachedHead=false checkout -q -f --detach FETCH_HEAD 2>/dev/null || true
STALE="$(git ls-files --others --exclude-standard -- frontend/src backend/app scripts 2>/dev/null | while read -r f; do
  git log FETCH_HEAD -1 --format=%h --diff-filter=D -- "$f" 2>/dev/null | grep -q . && echo "$f"; done)"
if [ -n "$STALE" ]; then
  echo "ملفّاتٌ حُذفت من الفرع وبقيت على القرص — تُزال:"; echo "$STALE" | sed 's/^/  /'
  echo "$STALE" | while read -r f; do rm -f -- "$f"; done
fi

say "١ب · أسماءُ «تداول» الرسمية (D520) — قبل الإعادة لتُقرأ عند الإقلاع"
docker exec "$C" python -c "
import asyncio, sys; sys.path.insert(0,'/app')
from app.services.tadawul_sync import sync_official
r = asyncio.run(sync_official())
print({k: (v if k != 'changed' else len(v)) for k, v in r.items()})
for c in (r.get('changed') or [])[:40]: print(' ', c['symbol'], c['from'], '←', c['to'])
" 2>&1 | grep -vE "INFO|DEBUG" | tail -45

say "٢ · إعادةُ الخادم"
# ‏D434: `up -d` يُطبّق إعداد الحاوية إن تغيّر (أمرُ التشغيل بلا --reload)،
# ثمّ الإعادةُ تقرأ الشفرةَ الجديدة — فالخادمُ لا يُعاد إلا هنا.
docker compose up -d --no-deps backend >/dev/null 2>&1 || true
docker restart "$C" >/dev/null 2>&1 && sleep 12 && echo "أُعيد $C" || \
  echo "⚠ تعذّرت إعادةُ $C — يُراجَع اسمُ الحاوية (SP_CONTAINER=…)"

say "٢ب · الواجهة — تُبنى إن تغيّرت منذ آخر بناء (D715)"
# ‏D715: كانت الدورةُ تُعيد الخادمَ وحدَه، والواجهةُ مهمّةٌ منفصلة (‏web) — فنُشرت تعديلاتُ الواجهة على الفرع ولم يرها المالك
# («لم أجد التحديثات على التطبيق»). فبصمةُ شجرة الواجهة تُحفظ بعد كلّ بناء، ومتى اختلفت بُنيت الواجهةُ هنا.
WEB_NOW="$(git rev-parse FETCH_HEAD:frontend 2>/dev/null || true)"
WEB_MARK=".web_built_tree"
if [ -n "$WEB_NOW" ] && [ "$(cat "$WEB_MARK" 2>/dev/null)" != "$WEB_NOW" ]; then
  if docker compose build frontend >/dev/null 2>&1 && docker compose up -d frontend >/dev/null 2>&1; then
    docker restart sp_nginx >/dev/null 2>&1 || true
    echo "$WEB_NOW" > "$WEB_MARK"
    echo "الواجهةُ بُنيت ونُشرت ($(printf %.8s "$WEB_NOW"))"
  else
    echo "✘ تعذّر بناءُ الواجهة — يُراجَع: docker compose build frontend"
  fi
else
  echo "الواجهةُ كما بُنيت آخرَ مرّة — لا تغيير"
fi

say "٣ · لقطةُ «تداول»"
docker exec "$C" python -c "
import asyncio, sys; sys.path.insert(0,'/app')
from app.services import tadawul_market as tm
print(asyncio.run(tm.refresh()))
r,l,a = tm.usable_rows(); print('رموزٌ:', len(r), '· حيّة:', l, '·', a)
" 2>&1 | grep -vE "INFO|DEBUG" | tail -3

say "٤ · حصادُ القوائم (السوقُ الرئيسيّ)"
docker exec "$C" python -c "
import asyncio, sys; sys.path.insert(0,'/app')
from app.data.market_universe import MARKET_UNIVERSE
from app.data.universe import main_market
from app.services import tadawul_xbrl as X
syms = [s for s in sorted(main_market(MARKET_UNIVERSE)) if not s.startswith('9')]
print('يُحصد:', len(syms))
print(asyncio.run(X.refresh(syms, conc=8)))
" 2>&1 | grep -vE "DEBUG" | tail -4

say "٤ب · مستشارُ الريت — صافي الأصول والتوزيعات من إعلانات «تداول» (D554)"
docker exec "$C" python -c "
import asyncio, sys; sys.path.insert(0,'/app')
from app.services.market_screener import get_cached_screener
from app.services.statement_merge import archetype_of
from app.services.reit_advisor import build
from app.services.tadawul_market import row_for
async def m():
    n = 0
    for r in get_cached_screener() or []:
        s = str(r.get('symbol'))
        if archetype_of(s) == 'reit':
            a = await build(s, (row_for(s) or {}).get('price'), force=True)
            n += 1 if a and a.get('nav') else 0
    print('ريتاتٌ بصافي أصولٍ منشور:', n)
asyncio.run(m())
" 2>&1 | grep -vE "DEBUG|INFO" | tail -2

if [ "$SWEEP" = "1" ]; then
  say "٥ · مسحةُ التقييم — درجةٌ وسعرٌ عادلٌ لكلّ شركة"
  docker exec "$C" python -c "
import asyncio, sys; sys.path.insert(0,'/app')
from app.services.market_valuation_sweep import sweep
print(asyncio.run(sweep()))
" 2>&1 | grep -vE "DEBUG" | tail -4
else
  say "٥ · مسحةُ التقييم — مُتخطّاةٌ بطلبك"
fi

say "٦ · سلسلةُ المعلومة حلقةً حلقةً"
# ══ والحلقةُ العاشرةُ تُقاس على الخادم لا «لم تُقَس» ══ (D427)
# حلقةُ الشاشة قراءةٌ ساكنةٌ لملفّات الواجهة، والحاويةُ لا تحملها —
# فخرجت «لم يُقَس» في كلّ دورة، وسلسلةٌ «متّصلةٌ» فيها حلقةٌ لم تُرَ.
# فتُنسخ ملفّاتُ الواجهة من شجرة الخادم — وهي التي تُبنى منها الواجهةُ
# المنشورة — إلى مجلّدٍ مؤقّتٍ في الحاوية، وتُدلّ السلسلةُ عليه.
docker exec "$C" rm -rf /tmp/sp_front >/dev/null 2>&1 || true
tar cf - frontend/src 2>/dev/null \
  | docker exec -i "$C" sh -c 'mkdir -p /tmp/sp_front && tar xf - -C /tmp/sp_front' \
  || echo "⚠ تعذّر نسخُ الواجهة إلى الحاوية — الحلقةُ العاشرةُ لن تُقاس"
docker exec -e SP_FRONT_ROOT=/tmp/sp_front "$C" \
  python /app/scripts/audit/chain_integrity.py 2>&1 | grep -vE "INFO|DEBUG"

say "٧ · لجنةُ كشف الأعطال (في صورة الخادم نفسِها · D714)"
bash scripts/ops/committee_image.sh 2>&1 | tail -14

say "الخلاصة"
echo "إن خرجت السلسلةُ متّصلةً واللجنةُ نظيفةً فالمنتَجُ جاهزٌ للمراجعة."
echo "ولا تُبنى حزمةٌ إلا بأمرك الصريح — واسمُها spupdatechanged.tar.gz"
echo "وتُبنى بـ bash scripts/package.sh وحدَه، وتُسلَّم بأمر تركيبها معها."
