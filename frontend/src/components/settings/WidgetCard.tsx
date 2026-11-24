/* ‏D791 — ويدجت الآيفون (المالك 2026-11-24: «أريد على الآيفون ويدجت كبقية التطبيقات»).

   ويدجت الآيفون الأصيلُ لا يصنعه إلا تطبيقٌ أصيلٌ يُبنى بـXcode على ماك؛ فالطريقُ الذي يعمل اليوم بلا ماكٍ ولا اشتراك تطبيقُ «Scriptable»
   المجانيّ: سكربتٌ يُنسخ من هنا (بعنوان هذا التطبيق، بلا رمز) ورمزٌ يُنشأ هنا ويُلصق مرّةً هناك فيُحفظ في سلسلة مفاتيح الآيفون.
   الرمزُ يُعرض مرّةً واحدة ويُخزَّن في الخادم مُجزَّأً، ويُلغى من هنا فيتوقّف الويدجت فوراً. */
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Copy, Check, KeyRound, Trash2 } from "lucide-react";
import { marketApi, widgetApi } from "../../services/api";
import { widgetScript } from "../../lib/widgetScript";
import { copyText } from "../../lib/symbols";
import { useAuthStore } from "../../store/authStore";

const API_BASE = import.meta.env.VITE_API_URL || "/api/v1";

const ago = (iso?: string | null) => {
  if (!iso) return null;
  const m = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (!Number.isFinite(m)) return null;
  if (m < 1) return "الآن";
  if (m < 60) return m === 1 ? "منذ دقيقة" : m === 2 ? "منذ دقيقتين" : `منذ ${m} ${m <= 10 ? "دقائق" : "دقيقة"}`;
  const h = Math.round(m / 60);
  if (h < 24) return h === 1 ? "منذ ساعة" : h === 2 ? "منذ ساعتين" : `منذ ${h} ${h <= 10 ? "ساعات" : "ساعة"}`;
  const d = Math.round(h / 24);
  return d === 1 ? "منذ يوم" : d === 2 ? "منذ يومين" : `منذ ${d} ${d <= 10 ? "أيام" : "يوماً"}`;
};

export default function WidgetCard() {
  const qc = useQueryClient();
  const { isOwner } = useAuthStore();
  const { data: st } = useQuery({ queryKey: ["widget-token"], queryFn: () => widgetApi.status().then(r => r.data?.data) });
  const [fresh, setFresh] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);
  /* ‏D800 (المالك 2026-11-24): «أريد في الويدجت الشركاتِ اللي حاطّها في القائمة — مثل ويدجت تريدنق فيو — تتوزّع يميناً ويساراً»: قوائمُ التطبيق
     وقيمةُ خانة Parameter لكلٍّ تُنسخ بضغطة */
  const { data: groups = [] } = useQuery<any[]>({
    queryKey: ["watchlist-groups"],
    queryFn: () => marketApi.watchGroups().then(r => (Array.isArray(r.data?.data) ? r.data.data : [])),
  });
  const [err, setErr] = useState<string | null>(null);
  const create = useMutation({
    mutationFn: () => widgetApi.create().then(r => r.data?.data),
    onSuccess: (d: any) => { setFresh(d?.token || null); setErr(null); qc.invalidateQueries({ queryKey: ["widget-token"] }); },
    onError: (e: any) => setErr(e?.response?.data?.detail || "تعذّر إنشاءُ الرمز."),
  });
  const revoke = useMutation({
    mutationFn: () => widgetApi.revoke(),
    onSuccess: () => { setFresh(null); qc.invalidateQueries({ queryKey: ["widget-token"] }); },
  });
  const copy = async (what: string, text: string) => {
    if (await copyText(text)) { setCopied(what); window.setTimeout(() => setCopied(null), 1600); }
  };
  const active = !!st?.active;
  const used = ago(st?.used);

  return (
    <div className="card" data-role="widget-card">
      <h2 className="card-title mb-1">ويدجت الآيفون</h2>
      <p className="text-xs text-[var(--ink-muted)] mb-4">
        الثروةُ وتغيّرُ اليوم وصافي الربح وعائدُ المحفظة وتاسي على شاشة الآيفون الرئيسية وشاشةِ القفل — بالأرقام نفسِها التي في التطبيق.
      </p>

      <div className="space-y-2 text-sm mb-4">
        <div className="flex justify-between items-center py-2 border-b border-[var(--hairline)]">
          <span className="text-[var(--ink-muted)]">رمز الويدجت</span>
          <span className={active ? "tag-g widget-on" : "tag-n"} data-role="widget-status">
            {active ? <>نافذ · ينتهي بـ <span dir="ltr" className="tabular-nums">{st?.hint}</span></> : "لا رمز"}
          </span>
        </div>
        {active && (
          <div className="flex justify-between items-center py-2 border-b border-[var(--hairline)]">
            <span className="text-[var(--ink-muted)]">آخرُ تحديثٍ للويدجت</span>
            <span className="text-[var(--ink)]">{used || "لم يُستعمل بعد"}</span>
          </div>
        )}
      </div>

      <ol className="widget-steps text-[13px] text-[var(--ink)] space-y-1.5 mb-4" data-role="widget-steps">
        <li>ثبّت تطبيق <b>Scriptable</b> من متجر التطبيقات (مجاني).</li>
        <li>اضغط «نسخ سكربت الويدجت» هنا، ثمّ في Scriptable اضغط <b>+</b> والصق السكربت وسمّه «المحفظة الذكية».</li>
        <li>اضغط «إنشاء رمز» هنا وانسخه، ثمّ شغّل السكربت مرّةً في Scriptable والصق الرمز حين يُطلب.</li>
        <li>اضغط مطوّلاً على الشاشة الرئيسية ← <b>+</b> ← Scriptable ← اختر الحجم، ثمّ «تعديل الويدجت» واختر السكربت.</li>
        <li>اختياريّ: في خانة <b>Parameter</b> اكتب <span dir="ltr">all</span> لكلّ المحافظ — أو قيمةَ قائمةٍ من «قوائمُ المراقبة» أدناه لتظهر شركاتُها بأسعارها في عمودين.</li>
      </ol>

      <div className="flex items-center gap-2 flex-wrap">
        <button type="button" className="btn-ghost widget-btn" data-role="widget-copy-script"
          onClick={() => copy("script", widgetScript(window.location.origin, API_BASE))}>
          {copied === "script" ? <Check size={15} /> : <Copy size={15} />}
          <span>{copied === "script" ? "نُسخ السكربت" : "نسخ سكربت الويدجت"}</span>
        </button>
        {isOwner && (
          <button type="button" className="btn-primary widget-btn" data-role="widget-create" disabled={create.isPending}
            onClick={() => {
              if (active && !window.confirm("رمزٌ جديد يُبطل الحاليّ، ويتوقّف الويدجت حتى تلصق الجديد في Scriptable. أتابع؟")) return;
              create.mutate();
            }}>
            <KeyRound size={15} /><span>{active ? "رمزٌ جديد" : "إنشاء رمز"}</span>
          </button>
        )}
        {isOwner && active && (
          <button type="button" className="btn-ghost widget-btn widget-revoke" data-role="widget-revoke" disabled={revoke.isPending}
            onClick={() => { if (window.confirm("إلغاءُ الرمز يوقف الويدجت فوراً. أتابع؟")) revoke.mutate(); }}>
            <Trash2 size={15} /><span>إلغاء الرمز</span>
          </button>
        )}
      </div>
      {err && <p className="text-xs text-[var(--neg-ink)] mt-2">{err}</p>}

      <div className="widget-lists mt-4" data-role="widget-lists">
        <span className="widget-lcap">قوائمُ المراقبة في الويدجت — انسخ القيمةَ والصقها في خانة <b>Parameter</b></span>
        {([["list", "محفظتي"], ...groups.map((g: any) => [`list:${g.name}`, g.name])] as [string, string][]).map(([v, name]) => (
          <button key={v} type="button" className="widget-param" onClick={() => copy(v, v)} data-role="widget-param" data-param={v}>
            <span className="widget-pname">{name}</span>
            <code dir="ltr" className="widget-pval">{v}</code>
            {copied === v ? <Check size={14} /> : <Copy size={14} />}
          </button>
        ))}
      </div>

      {fresh && (
        <div className="widget-token fade-in mt-4" data-role="widget-token">
          <p className="text-[12px] text-[var(--ink-muted)] mb-2">انسخ الرمزَ الآن والصقه في Scriptable — لا يُعرض مرّةً ثانية.</p>
          <div className="flex items-center gap-2">
            <code className="widget-token-val flex-1 min-w-0 truncate" dir="ltr" data-role="widget-token-val">{fresh}</code>
            <button type="button" className="btn-ghost widget-btn shrink-0" data-role="widget-copy-token" onClick={() => copy("token", fresh)}>
              {copied === "token" ? <Check size={15} /> : <Copy size={15} />}<span>{copied === "token" ? "نُسخ" : "نسخ الرمز"}</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
