import React from "react";
import { useQuery } from "@tanstack/react-query";
import { Mic, ExternalLink, Presentation, FileText } from "lucide-react";
import { marketApi } from "../../services/api";

/* ══ مؤتمراتُ المحلّلين والمستثمرين ══ (D559) — من إعلانات «تداول» نفسِها:
   الموعدُ وحالتُه، والفترةُ المناقشة، ورابطُ الحضور قبله والعرضُ التقديميُّ بعده. */

type Call = { id: string; date?: string; time?: string; status: "upcoming" | "held"; period?: string;
              join?: string; deck?: string; url?: string; summary?: string };

function Link({ href, icon: Icon, label }: { href?: string; icon: any; label: string }) {
  if (!href) return null;
  return (
    <a href={href} target="_blank" rel="noopener noreferrer"
      className="btn-ghost !py-1.5 !px-2.5 text-xs min-h-[32px] inline-flex items-center gap-1.5">
      <Icon size={13} /> {label}
    </a>
  );
}

export default function InvestorCalls({ symbol }: { symbol: string }) {
  const { data: calls = [] } = useQuery<Call[]>({
    queryKey: ["investor-calls", symbol],
    queryFn: () => marketApi.investorCalls(symbol).then(r => (Array.isArray(r.data.data) ? r.data.data : [])),
    staleTime: 30 * 60 * 1000,
  });
  if (!calls.length) return null;
  return (
    <div className="card p-0">
      <div className="flex items-center gap-2 p-4 border-b border-[var(--hairline)]">
        <Mic size={16} className="text-[var(--brand-ink)]" />
        <h2 className="card-title">مؤتمرات المحللين</h2>
        <span className="ms-auto text-[11px] text-[var(--ink-muted)]">{calls.length} مؤتمر</span>
      </div>
      <div className="divide-y divide-[var(--hairline)]">
        {calls.map(c => {
          const up = c.status === "upcoming";
          return (
            <div key={c.id} className="p-3.5 space-y-2">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-[13px] font-semibold text-[var(--ink)] tabular-nums">{c.date}</span>
                {c.time && <span className="text-[11px] text-[var(--ink-muted)] tabular-nums">{c.time}</span>}
                <span className="tag-b" style={up ? { color: "var(--brand-ink)" } : undefined}>{up ? "قادم" : "عُقد"}</span>
                {c.period && <span className="text-[11px] text-[var(--ink-muted)]">{c.period}</span>}
              </div>
              <div className="flex items-center gap-2 flex-wrap">
                <Link href={up ? c.join : undefined} icon={ExternalLink} label="التسجيل للحضور" />
                <Link href={c.deck} icon={Presentation} label="العرض التقديمي" />
                <Link href={c.url} icon={FileText} label="الإعلان" />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
