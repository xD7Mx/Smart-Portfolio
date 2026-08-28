import React, { useState } from "react";
import { ChevronDown } from "lucide-react";

/** قائمة منسدلة موحّدة: رأسٌ بالاسم والعدد وسهم، يفتح/يغلق المحتوى بنقرة. */
export default function CollapsibleList({ label, count, children, className = "", defaultOpen = false, compact = false }: {
  label: string; count?: number; children: React.ReactNode; className?: string; defaultOpen?: boolean; compact?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className={className}>
      <button onClick={() => setOpen(o => !o)}
        /* أرضية التطبيق وإطارٌ أثقل — كبقيّة الحقول والقوائم. كان يأخذ السطح
           المصبوغ (`--panel`) والخيط الشعري، فيقرأ كتلةً ثقيلة على الورق. */
        className={(compact ? "inline-flex w-auto" : "w-full flex") + " items-center gap-2 px-3 py-2 rounded-xl transition-colors"}
        style={{ background: "var(--surface)" }}>
        <span className="text-[12.5px] font-bold" style={{ color: "var(--ink)" }}>{label}</span>
        {/* العدد يظهر عند الانسدال ويختفي عند الطيّ: رأس القائمة المطويّة
            يُقرأ اسماً واحداً، والعدد معلومةٌ عن محتواها فلا معنى لعرضه
            قبل فتحها. */}
        {count != null && open && <span className="tag-b" style={{ fontSize: 10 }}>{count}</span>}
        <ChevronDown size={16} className={"text-[var(--ink-muted)] ms-auto transition-transform duration-200 " + (open ? "rotate-180" : "")} />
      </button>
      {/* انسدال سلس: انتقال ارتفاع عبر grid-rows (0fr↔1fr) + شفافية */}
      <div style={{
        display: "grid",
        gridTemplateRows: open ? "1fr" : "0fr",
        opacity: open ? 1 : 0,
        transition: "grid-template-rows .24s ease, opacity .2s ease",
      }}>
        <div style={{ overflow: "hidden" }}>
          <div className="mt-3 px-1">{children}</div>
        </div>
      </div>
    </div>
  );
}
