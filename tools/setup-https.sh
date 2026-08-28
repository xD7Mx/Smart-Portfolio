#!/usr/bin/env bash
# إصدار شهادة Let's Encrypt وتفعيل HTTPS.
#
# شرطٌ واحد لا بديل عنه: **اسم نطاق يشير إلى عنوان الخادم**. لا تُصدَر شهادة
# موثوقة لعنوان IP، والشهادة الموقّعة ذاتياً لا تُسجّل Service Worker ولا
# تُثبِّت التطبيق — فتبقى الـPWA معطّلة.
set -euo pipefail
DOMAIN="${1:-}"
EMAIL="${2:-}"
[ -z "$DOMAIN" ] && { echo "الاستعمال: bash tools/setup-https.sh example.com you@mail.com"; exit 1; }

cd "$(dirname "$0")/.."
mkdir -p docker/ssl /var/www/certbot 2>/dev/null || true

echo "١) تحقّق أنّ $DOMAIN يشير إلى هذا الخادم:"
dig +short "$DOMAIN" || true
echo "٢) افتح المنفذ 443 في مجموعة الأمان قبل المتابعة."
read -rp "هل تمّ الأمران؟ (yes) " ok
[ "$ok" = "yes" ] || exit 1

docker run --rm \
  -v "$PWD/docker/ssl:/etc/letsencrypt" \
  -v /var/www/certbot:/var/www/certbot \
  -p 80:80 \
  certbot/certbot certonly --standalone \
  -d "$DOMAIN" --agree-tos -m "${EMAIL:-admin@$DOMAIN}" --non-interactive

echo
echo "صدرت الشهادة. الخطوة الأخيرة يدوية عمداً:"
echo "  cp docker/nginx-tls.conf.example docker/nginx.conf.new"
echo "  # بدّل YOUR_DOMAIN بـ $DOMAIN، وانسخ كتل location من nginx.conf الحالي"
echo "  # ثم: mv docker/nginx.conf.new docker/nginx.conf && docker compose restart nginx"
echo
echo "التجديد (ضعه في cron شهرياً):"
echo "  docker run --rm -v \$PWD/docker/ssl:/etc/letsencrypt certbot/certbot renew"
