#!/bin/sh
# ══════════════════════════════════════════════════════════════════════
#  فاحصُ التدفّقات المنشورة للآلة (RSS/JSON)
#
#  الفرق الجوهري عن الكشط: هذه قنواتٌ **يَنشرها الموقع نفسه ليقرأها البرنامج**
#  لا صفحاتٌ للبشر نتسلّل إليها. من ينشر RSS فقد دعا الآلة إلى القراءة.
#  لذلك هي مجّانية ومشروعة ولا تُحجب.
#
#  يُشغَّل على الخادم:  sh scripts/probe_feeds.sh
#  ثم أرسل المخرَج — منه نعرف أيّ قناةٍ تحمل الإفصاحات فعلاً.
# ══════════════════════════════════════════════════════════════════════
set -u
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
OUT=/tmp/feeds; mkdir -p "$OUT"

try() {
  n="$1"; u="$2"
  echo "──────────────────────────────────────"
  echo "  $n"
  echo "  $u"
  c=$(curl -sL -o "$OUT/$n" -w '%{http_code}' --max-time 20 \
      -H "User-Agent: $UA" -H "Accept: application/rss+xml, application/xml, application/json, */*" "$u")
  z=$(wc -c < "$OUT/$n" 2>/dev/null || echo 0)
  echo "  الحالة: $c   الحجم: $z بايت"
  if [ "$c" = "200" ] && [ "$z" -gt 200 ]; then
    if grep -qi "<rss\|<feed\|<item" "$OUT/$n" 2>/dev/null; then
      cnt=$(grep -ci "<item\|<entry" "$OUT/$n" 2>/dev/null || echo 0)
      echo "  ← تدفّق RSS ✓  عناصر: $cnt"
      # أوّل عنوانٍ وتاريخ — منهما نعرف أهو إفصاحٌ أم خبرٌ عام
      grep -oi "<title>[^<]*</title>" "$OUT/$n" | sed -n 2,4p | sed 's/^/      /'
      grep -oi "<pubDate>[^<]*</pubDate>" "$OUT/$n" | sed -n 1,2p | sed 's/^/      /'
    elif head -c 1 "$OUT/$n" | grep -q '[{[]'; then
      echo "  ← JSON ✓"
      head -c 260 "$OUT/$n" | sed 's/^/      /'; echo
    else
      echo "  ← HTML (صفحة بشر — لا تصلح)"
    fi
  fi
  echo
}

echo "فاحص التدفّقات — $(date '+%F %T')"; echo

# «أرقام» — الموقع الذي يستعمله المالك اليوم. تدفّقاته منشورةٌ للآلة.
try "argaam_rss"        "https://www.argaam.com/ar/rss"
try "argaam_disclosure" "https://www.argaam.com/ar/rss/articles/3"
try "argaam_company"    "https://www.argaam.com/ar/rss/company/1120"

# تداول — إن كان ينشر تدفّقاً
try "tadawul_rss"       "https://www.saudiexchange.sa/wps/portal/saudiexchange/rss"

# هيئة السوق المالية — سالكة (٢٠٠) كما أثبت الفحص السابق
try "cma_rss"           "https://cma.org.sa/_layouts/15/listfeed.aspx?List=News"

echo "══════════════════════════════════════"
echo "الردود في $OUT/ — أرسل المخرَج كما هو."
echo "ما يظهر «تدفّق RSS ✓» يصلح مصدراً للإفصاحات، وما عداه لا."
