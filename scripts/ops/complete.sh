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

say "٢ · إعادةُ الخادم"
# ‏D434: `up -d` يُطبّق إعداد الحاوية إن تغيّر (أمرُ التشغيل بلا --reload)،
# ثمّ الإعادةُ تقرأ الشفرةَ الجديدة — فالخادمُ لا يُعاد إلا هنا.
docker compose up -d --no-deps backend >/dev/null 2>&1 || true
docker restart "$C" >/dev/null 2>&1 && sleep 12 && echo "أُعيد $C" || \
  echo "⚠ تعذّرت إعادةُ $C — يُراجَع اسمُ الحاوية (SP_CONTAINER=…)"

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

say "٧ · لجنةُ كشف الأعطال (من جذر المستودع)"
bash scripts/audit/run.sh 2>&1 | tail -14

say "الخلاصة"
echo "إن خرجت السلسلةُ متّصلةً واللجنةُ نظيفةً فالمنتَجُ جاهزٌ للمراجعة."
echo "ولا تُبنى حزمةٌ إلا بأمرك الصريح — واسمُها spupdatechanged.tar.gz"
echo "وتُبنى بـ bash scripts/package.sh وحدَه، وتُسلَّم بأمر تركيبها معها."
