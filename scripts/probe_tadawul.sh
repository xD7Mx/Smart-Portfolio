#!/bin/sh
# ══════════════════════════════════════════════════════════════════════
#  فاحصُ مصدر الإفصاحات الرسمية — تداول
#
#  الغرض: معرفة هل يستطيع خادمك قراءة إعلانات الشركات من **المصدر الرسمي**
#  مباشرةً، فتستغني عن الخروج إلى موقعٍ خارجي لاستعمال ميزةٍ داخل تطبيقك.
#
#  هذا السكربت **يقرأ ولا يكتب**: لا يمسّ قاعدة البيانات ولا التطبيق ولا
#  ملفاً واحداً. كل ما يفعله أنه يسأل ويطبع ما يعود.
#
#  يُشغَّل على الخادم (حيث الإنترنت):
#      sh scripts/probe_tadawul.sh
#  ثم أرسل لي المخرَج كما هو.
# ══════════════════════════════════════════════════════════════════════
set -u
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
OUT=/tmp/tadawul_probe
mkdir -p "$OUT"

try() {
  name="$1"; url="$2"; extra="${3:-}"
  echo "──────────────────────────────────────────────"
  echo "  $name"
  code=$(curl -s -o "$OUT/$name.body" -w '%{http_code}' --max-time 25 \
         -H "User-Agent: $UA" \
         -H "Accept: application/json, text/plain, */*" \
         -H "Accept-Language: ar,en;q=0.8" \
         $extra "$url" 2>/dev/null)
  size=$(wc -c < "$OUT/$name.body" 2>/dev/null || echo 0)
  echo "  الحالة: $code   الحجم: $size بايت"
  if [ "$code" = "200" ] && [ "$size" -gt 200 ]; then
    head -c 400 "$OUT/$name.body" | tr -d '\r' | sed 's/^/    /'
    echo
    echo "    …"
    # هل يبدو JSON؟
    if head -c 1 "$OUT/$name.body" | grep -q '[{[]'; then
      echo "    ← يبدو JSON ✓ (صالحٌ للقراءة الآلية)"
    else
      echo "    ← يبدو HTML (يحتاج استخراجاً، وهو أهشّ)"
    fi
  fi
  echo
}

echo "فاحص مصدر الإفصاحات — $(date '+%F %T')"
echo

# ١) الصفحة الرسمية للإعلانات (لمعرفة هل تُفتح أصلاً من خادمك)
try "01_page" "https://www.saudiexchange.sa/wps/portal/saudiexchange/newsandreports/issuer-news"

# ٢) واجهة الإفصاحات الداخلية التي تُغذّي تلك الصفحة (JSON)
try "02_api" "https://www.saudiexchange.sa/wps/portal/saudiexchange/newsandreports/issuer-news/!ut/p/z1/jc0xD4IwEIbh3-LQlV6hAjo2DAgaExMV22UhgpaEtqTWGP-9GAcXo7d97yV3iKMKcVvfla6dMrbup_3AZ0dCijSlOSyzOAOSCVFAmO9pCOjwCoS4dsr9nEoQVvJfIC5bA7-BFtvHb-YtTolMLKuIpZeCzGuQ-BiapmnQxjR9y5r68z2R4Z-eTsRlbHYs4RPCw8HgB1BLBg0=/"

# ٣) بديلٌ رسميّ ثانٍ: تدفّق الإعلانات من هيئة السوق المالية
try "03_cma" "https://cma.org.sa/Market/NEWS/pages/default.aspx"

echo "══════════════════════════════════════════════"
echo "الردود الكاملة محفوظة في: $OUT/"
echo "أرسل لي هذا المخرَج كما هو — منه أعرف أيّ طريقٍ سالك."
echo
echo "ملاحظة: إن ردّت الثلاثة بـ403 أو 000، فالخادم محجوبٌ عنها ولا"
echo "مجال للمكابرة — عندها نبحث في بدائل أخرى وأقول لك ذلك صراحةً."
