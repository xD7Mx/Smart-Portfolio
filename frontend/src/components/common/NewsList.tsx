import React, { useState } from "react";
import { Clock, ShieldCheck, X, Share2, ExternalLink, Loader2 } from "lucide-react";
import { marketApi } from "../../services/api";
import CompanyLogo from "./CompanyLogo";
import SourceLogo, { hasSourceLogo } from "./SourceLogo";
import { lookupCompany } from "../../data/saudiCompanies";

/**
 * اللغة التصميمية الموحّدة للأخبار — مكوّن واحد يخدم «أخبار السوق» و«أخبار
 * المحفظة» معاً، فلا يختلف شكل الخبر بين قسمٍ وآخر (كان قسم المحفظة يفتح
 * الرابط مباشرةً بلا نافذة تفاصيل).
 *
 * ثلاثة مبادئ:
 *  1) الهوية البصرية: شعار الشركة الحقيقي، أو شعار المصدر المعتمد.
 *  2) لا حشو: الملخّص يُعرض فقط إن وفّره المصدر فعلاً — لا مربّع وصفي مُقحَم.
 *  3) لا إحراج: زرّ «المصدر» لا يظهر إلا بعد التحقّق من أن الرابط يفتح فعلاً.
 */

const fmtTime = (d: string) =>
  d ? new Date(d).toLocaleString("en-GB", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }) : "";

/* وسمُ تصنيف الخبر — بلغة وسوم الأحداث نفسها (أرضيةٌ صلبة وحبرٌ أسود)،
   بأمر المالك: الأقسام الأربعة (مفكرة · إفصاحات · أخبار · تنبيهات) تقرأ
   لغةً واحدة. والدرجات من رموز `--tag-*` لا قيماً مكتوبة هنا. */
export const CATEGORY_STYLE: Record<string, { bg: string; fg: string }> = {
  "أسواق":  { bg: "var(--tag-rights)", fg: "var(--tag-ink)" },
  "اقتصاد": { bg: "var(--tag-results)", fg: "var(--tag-ink)" },
  "شركات":  { bg: "var(--tag-dividend)", fg: "var(--tag-ink)" },
};

/** قاعدة قبول العرض: للخبر هوية بصرية حقيقية (شعار شركة أو مصدر معتمد). */
export function hasNewsIdentity(n: any): boolean {
  return !!n.company || hasSourceLogo(n.source);
}

/** نافذة تفاصيل الخبر — موحّدة لكل الأقسام. */
export function NewsDetailModal({ n, onClose }: { n: any; onClose: () => void }) {
  const cat = CATEGORY_STYLE[n.category] || CATEGORY_STYLE["أسواق"];
  const companyName = n.company ? (lookupCompany(n.company)?.name_ar || n.company) : null;
  // حالة الرابط: نتحقّق أنه يفتح فعلاً قبل عرض زرّ «المصدر» — روابط جوجل
  // نيوز تمرّ عبر مُحوِّل، وبعض الناشرين يحجب أو يحذف المقال فتظهر صفحة
  // خطأ. لا نعرض زراً يقود لخطأ.
  const [link, setLink] = useState<{ state: "checking" | "ok" | "bad"; url?: string }>(
    n.url ? { state: "checking" } : { state: "bad" }
  );
  React.useEffect(() => {
    if (!n.url) return;
    let alive = true;
    marketApi.resolveNewsUrl(n.url)
      .then(r => { const u = r.data?.data?.url; if (alive) setLink(u ? { state: "ok", url: u } : { state: "bad" }); })
      .catch(() => { if (alive) setLink({ state: "bad" }); });
    return () => { alive = false; };
  }, [n.url]);

  const summary = n.summary;   // بلا حشو: إن لم يوفّر المصدر ملخّصاً لا نعرض مربعاً
  const share = async () => {
    const url = link.url || n.url || window.location.href;
    const shareData = { title: n.headline, text: n.headline, url };
    if ((navigator as any).share) {
      try { await (navigator as any).share(shareData); } catch { /* أُلغيت */ }
    } else {
      try { await navigator.clipboard.writeText(url); } catch { /* لا شيء */ }
    }
  };

  return (
    <div className="modal-overlay" onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="modal-box fade-in" style={{ maxWidth: 480 }}>
        <div className="flex items-center justify-between mb-4">
          {n.company ? <CompanyLogo symbol={n.company} size={40} /> : <SourceLogo source={n.source} size={40} />}
          <button onClick={onClose} title="إغلاق" aria-label="إغلاق" className="text-[var(--ink-muted)] hover:text-[var(--ink)] p-1"><X size={18} /></button>
        </div>
        <div className="flex items-center gap-2 flex-wrap mb-2.5">
          <span className="ev-tag" style={{ background: cat.bg, color: cat.fg }}>{n.category || "أسواق"}</span>
          {companyName && <span className="tag-b" style={{ fontSize: 10 }}>{companyName}{n.company ? ` (${n.company})` : ""}</span>}
          {n.trusted && <span className="text-[10px] font-bold text-[var(--pos-ink)] flex items-center gap-1"><ShieldCheck size={11} /> مصدر موثّق</span>}
        </div>
        <h2 className="text-lg font-bold text-[var(--ink)] leading-snug mb-2">{n.headline}</h2>
        <p className="text-xs text-[var(--ink-muted)] flex items-center gap-1.5 mb-4">
          <Clock size={12} />
          {[n.source, n.published ? fmtTime(n.published) : null].filter(Boolean).join(" · ")}
        </p>
        {summary && (
          <div className="news-summary rounded-xl p-3.5 mb-4">
            <p className="text-sm leading-relaxed">{summary}</p>
          </div>
        )}
        <div className="flex gap-2">
          <button onClick={share} className="btn-primary flex-1 justify-center"><Share2 size={14} /> مشاركة الخبر</button>
          {link.state === "checking" && (
            <span className="btn-ghost flex items-center gap-1.5 opacity-60"><Loader2 size={14} className="animate-spin" /> المصدر</span>
          )}
          {link.state === "ok" && (
            <a href={link.url} target="_blank" rel="noopener noreferrer" className="btn-ghost flex items-center gap-1.5">
              <ExternalLink size={14} /> المصدر
            </a>
          )}
          {/* الرابط معطوب/محجوب → لا زرّ إطلاقاً (لا نُحرج المستخدم بصفحة خطأ) */}
        </div>
      </div>
    </div>
  );
}

/** بطاقة خبر واحدة — نفس الشكل في كل الأقسام. */
function NewsRow({ n, onOpen }: { n: any; onOpen: () => void }) {
  const cat = CATEGORY_STYLE[n.category] || CATEGORY_STYLE["أسواق"];
  const companyName = n.company ? (lookupCompany(n.company)?.name_ar || n.company) : null;
  return (
    <button onClick={onOpen} className="news-item w-full text-start block active:scale-[.995] transition-transform" style={{ padding: 12 }}>
      <div className="flex items-start gap-3">
        {n.company ? <CompanyLogo symbol={n.company} size={38} /> : <SourceLogo source={n.source} size={38} />}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className="ev-tag" style={{ background: cat.bg, color: cat.fg }}>{n.category || "أسواق"}</span>
            {companyName && <span className="tag-b" style={{ fontSize: 10 }}>{companyName}{n.company ? ` (${n.company})` : ""}</span>}
            {n.trusted && <span className="text-[10px] font-bold text-[var(--pos-ink)] flex items-center gap-1"><ShieldCheck size={11} /> مصدر موثّق</span>}
          </div>
          <p className="text-sm font-semibold text-[var(--ink)] leading-snug">{n.headline}</p>
          <p className="text-xs text-[var(--ink-muted)] mt-1 flex items-center gap-1">
            <Clock size={11} />
            {[n.source, n.published ? fmtTime(n.published) : null].filter(Boolean).join(" · ")}
          </p>
        </div>
      </div>
    </button>
  );
}

/**
 * قائمة أخبار موحّدة — تُستخدم في «أخبار السوق» و«أخبار المحفظة» معاً.
 * `pageSize` يفعّل زرّ «عرض المزيد» حين تكون القائمة طويلة.
 */
export default function NewsList({ news, isLoading, emptyText, pageSize = 0 }: {
  news: any[]; isLoading?: boolean; emptyText?: string; pageSize?: number;
}) {
  const [shown, setShown] = useState(pageSize || Infinity);
  const [open, setOpen] = useState<any | null>(null);
  const visible = (news || []).filter(hasNewsIdentity);

  if (isLoading) {
    return <div className="space-y-2">{Array.from({ length: 5 }).map((_, i) => <div key={i} className="h-14 skeleton rounded-xl" />)}</div>;
  }
  if (!visible.length) {
    return <div className="py-16 text-center text-[var(--ink-muted)] text-sm">{emptyText || "لا توجد أخبار حالياً"}</div>;
  }
  return (
    <>
      <div className="space-y-2.5">
        {visible.slice(0, shown).map((n: any, i: number) => (
          <NewsRow key={n.id ?? `${n.headline}-${i}`} n={n} onOpen={() => setOpen(n)} />
        ))}
      </div>
      {visible.length > shown && (
        <button onClick={() => setShown(s => s + (pageSize || 20))}
          className="btn-ghost w-full justify-center mt-3 text-xs">
          عرض المزيد ({visible.length - shown} خبراً إضافياً)
        </button>
      )}
      {open && <NewsDetailModal n={open} onClose={() => setOpen(null)} />}
    </>
  );
}
