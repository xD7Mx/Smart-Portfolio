import React, { useState } from "react";
import { Share2, Check } from "lucide-react";

/**
 * المشاركة — زرٌّ يعمل فعلاً (و«افتح في أرقام» حُذف بأمر المالك · D620).
 *
 * ## لماذا كانت المشاركة لا تفعل شيئاً
 *
 * `navigator.share` و`navigator.clipboard` **لا يعملان إلا في سياقٍ آمن**
 * (HTTPS أو localhost). وخادم المالك على HTTP، فالنداء يُرفض بصمت: لا
 * نافذة مشاركة ولا نسخ ولا رسالة خطأ. الزرّ يُضغط ولا يقع شيء.
 *
 * فالمعالجة ثلاث طبقات: نافذة المشاركة إن توفّرت، فالحافظة إن سُمح بها،
 * فالطريقة القديمة (حقلٌ مخفيّ و`execCommand`) وهي تعمل على HTTP. وفي
 * كل حالٍ **يُقال للمالك ما وقع** — «نُسخ الرابط» — فلا يبقى يضغط ظانّاً
 * أن الزرّ معطوب.
 */
export function ShareButton({ title, text, url, className = "btn-primary flex-1 justify-center" }:
  { title: string; text?: string | null; url?: string | null; className?: string }) {
  const [done, setDone] = useState(false);
  /* ‏D620: يُشارَك الخبرُ نفسُه لا رابطُ التطبيق — رابطُ الخادم الخاصّ لا يفتحه غيرُ المالك، وكان يُلصَق
     في المتصفّح فيصير بحثاً في «قوقل». والرابطُ يُضاف حين يكون للمصدر الرسميّ وحده. */
  const body = [title, text, url].filter(Boolean).join("\n");

  const copyFallback = (text: string) => {
    // طريقةٌ قديمة لكنّها الوحيدة التي تعمل خارج السياق الآمن.
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    let ok = false;
    try { ok = document.execCommand("copy"); } catch { ok = false; }
    document.body.removeChild(ta);
    return ok;
  };

  const share = async () => {
    const payload: any = { title, text: [title, text].filter(Boolean).join("\n") };
    if (url) payload.url = url;
    if ((navigator as any).share && window.isSecureContext) {
      try { await (navigator as any).share(payload); return; } catch { /* أُلغيت */ }
    }
    let ok = false;
    if (navigator.clipboard && window.isSecureContext) {
      try { await navigator.clipboard.writeText(body); ok = true; } catch { ok = false; }
    }
    if (!ok) ok = copyFallback(body);
    if (ok) { setDone(true); setTimeout(() => setDone(false), 2200); }
  };

  return (
    <button onClick={share} className={className} type="button"
      title={done ? "نُسخ" : "مشاركة"}>
      {done ? <Check size={14} /> : <Share2 size={14} />}
      {done ? "نُسخ الخبر" : "مشاركة"}
    </button>
  );
}
