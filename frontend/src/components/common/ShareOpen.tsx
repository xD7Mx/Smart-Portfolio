import React, { useEffect, useState } from "react";
import { Share2, ExternalLink, Check } from "lucide-react";
import { marketApi } from "../../services/api";

/**
 * المشاركة و«افتح في أرقام» — زرّان يعملان فعلاً.
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
export function ShareButton({ title, url, className = "btn-primary flex-1 justify-center" }:
  { title: string; url?: string | null; className?: string }) {
  const [done, setDone] = useState(false);
  const link = url || window.location.href;

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
    const payload = { title, text: title, url: link };
    if ((navigator as any).share && window.isSecureContext) {
      try { await (navigator as any).share(payload); return; } catch { /* أُلغيت */ }
    }
    let ok = false;
    if (navigator.clipboard && window.isSecureContext) {
      try { await navigator.clipboard.writeText(`${title}\n${link}`); ok = true; } catch { ok = false; }
    }
    if (!ok) ok = copyFallback(`${title}\n${link}`);
    if (ok) { setDone(true); setTimeout(() => setDone(false), 2200); }
  };

  return (
    <button onClick={share} className={className} type="button"
      title={done ? "نُسخ" : "مشاركة"}>
      {done ? <Check size={14} /> : <Share2 size={14} />}
      {done ? "نُسخ الرابط" : "مشاركة"}
    </button>
  );
}

/* خريطة معرّفات أرقام — تُجلب مرّةً وتبقى في الذاكرة طوال الجلسة.
   الطلب واحدٌ لكل الصفحات، فزرٌّ في مئة بطاقة لا يعني مئة نداء. */
let _map: Record<string, string> | null = null;
let _pending: Promise<Record<string, string>> | null = null;
function loadIds(): Promise<Record<string, string>> {
  if (_map) return Promise.resolve(_map);
  if (!_pending) {
    _pending = marketApi.argaamIds()
      .then(r => { _map = (r.data?.data?.ids as any) || {}; return _map!; })
      .catch(() => { _map = {}; return _map!; });
  }
  return _pending;
}

/**
 * «افتح في أرقام» — صفحة الشركة بعينها.
 *
 * لا يظهر إلا حين يُعرف معرّف الشركة. وزرٌّ يفتح صفحة بحثٍ ليس «افتح في
 * أرقام»، والوعد الذي لا يُوفى أسوأ من زرٍّ غائب.
 */
export function ArgaamButton({ symbol, className = "btn-ghost flex items-center gap-1.5" }:
  { symbol?: string | null; className?: string }) {
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    const s = String(symbol || "").replace(".SR", "").trim();
    if (!s) return;
    let alive = true;
    loadIds().then(m => {
      const cid = m[s];
      if (alive && cid) setUrl(`https://www.argaam.com/ar/company/companyoverview/marketid/3/companyid/${cid}`);
    });
    return () => { alive = false; };
  }, [symbol]);
  if (!url) return null;
  return (
    <a href={url} target="_blank" rel="noopener noreferrer" className={className}>
      <ExternalLink size={14} /> افتح في أرقام
    </a>
  );
}
