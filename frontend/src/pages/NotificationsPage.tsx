import React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { notificationsApi } from "../services/api";
import { Bell, Check, Trash2, CheckCheck, Eraser } from "lucide-react";
import { useT } from "../i18n";
import CompanyLogo from "../components/common/CompanyLogo";
import Logo from "../components/common/Logo";
import { useAuthStore } from "../store/authStore";

const PRIORITY_COLORS: any = { CRITICAL: "text-[var(--neg-ink)]", HIGH: "text-[var(--warn-ink)]", MEDIUM: "text-[var(--brand-ink)]", LOW: "text-[var(--ink-muted)]", INFO: "text-[var(--ink-muted)]" };

// Portfolio/market notifications embed the real Tadawul symbol in
// parentheses, e.g. "مركزك في سابك (2010) رابح…" — extract it (never
// guessed) so the bell can show that company's real logo.
function extractSymbol(n: any): string | null {
  const m = /\((\d{4})\)/.exec(`${n.title || ""} ${n.message || ""}`);
  return m ? m[1] : null;
}

const READ_CAP = 20;

export default function NotificationsPage() {
  const t = useT();
  const qc = useQueryClient();
  const { isOwner } = useAuthStore();
  const { data: notifs = [] } = useQuery({
    queryKey: ["notifications"],
    queryFn: () => notificationsApi.list().then(r => (Array.isArray(r.data.data) ? r.data.data : [])),
  });

  const invalidate = () => qc.invalidateQueries({ queryKey: ["notifications"] });
  const readMutation    = useMutation({ mutationFn: notificationsApi.read,       onSuccess: invalidate });
  const deleteMutation  = useMutation({ mutationFn: notificationsApi.delete,     onSuccess: invalidate });
  const readAllMutation = useMutation({ mutationFn: notificationsApi.readAll,    onSuccess: invalidate });
  const delReadMutation = useMutation({ mutationFn: notificationsApi.deleteRead, onSuccess: invalidate });
  const delAllMutation  = useMutation({ mutationFn: notificationsApi.deleteAll,  onSuccess: invalidate });

  const unread  = notifs.filter((n: any) => n.status === "UNREAD");
  const allRead = notifs.filter((n: any) => n.status !== "UNREAD");
  const busy = readAllMutation.isPending || delReadMutation.isPending || delAllMutation.isPending;

  return (
    <div className="space-y-5 fade-in">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-2xl font-medium text-[var(--ink)]">{t("notif.title")}</h1>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <span className={unread.length > 0 ? "tag-a" : "tag-n"}>{unread.length} {t("notif.unread")}</span>
          {isOwner && notifs.length > 0 && (
            <div className="flex items-center gap-1.5">
              {unread.length > 0 && (
                <button onClick={() => readAllMutation.mutate()} disabled={busy}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium text-[var(--pos-ink)] disabled:opacity-40 transition-all">
                  <CheckCheck size={13} /> قراءة الكل
                </button>
              )}
              {allRead.length > 0 && (
                <button onClick={() => delReadMutation.mutate()} disabled={busy}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium text-[var(--ink)] disabled:opacity-40 transition-all">
                  <Eraser size={13} /> حذف المقروءة
                </button>
              )}
              <button
                onClick={() => { if (window.confirm("حذف جميع الإشعارات؟ لا يمكن التراجع.")) delAllMutation.mutate(); }}
                disabled={busy}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium text-[var(--neg-ink)] disabled:opacity-40 transition-all">
                <Trash2 size={13} /> حذف الكل
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="card">
        <h2 className="card-title mb-4">{t("notif.unread")}</h2>
        {unread.length === 0 ? (
          <div className="text-center py-8 text-[var(--ink-muted)]">
            <Bell size={28} className="mx-auto mb-2 opacity-50" />
            <p className="text-sm">{t("notif.empty")}</p>
          </div>
        ) : (
          <div className="space-y-2.5">
            {unread.map((n: any) => (
              <div key={n.id} className="notif" style={{borderColor: ({CRITICAL:"var(--neg-ink)",HIGH:"var(--warn-ink)",MEDIUM:"var(--chart-1)",LOW:"var(--chart-3)",INFO:"var(--ink-muted)"} as any)[n.priority] || "var(--chart-1)"}}>
                {extractSymbol(n) ? <CompanyLogo symbol={extractSymbol(n)!} size={32} /> : <Logo size={32} />}
                <div className="flex-1 min-w-0">
                  {/* وسمُ الأولوية بلغة وسوم الأحداث نفسها (بأمر المالك:
                      الأقسام الأربعة لغةٌ واحدة). وكانت الأولوية تُقال بلون
                      الإطار وحده — إشارةٌ لا تُقرأ إلا لمن يحفظ الاصطلاح،
                      ولا يراها من لا يميّز الألوان أصلاً. فصارت كلمةً. */}
                  <p className="notif-title flex items-center gap-2 flex-wrap">
                    <span className="min-w-0">{n.title}</span>
                    <span className="ev-tag ms-auto shrink-0" style={{
                      color: "var(--tag-ink)",
                      background: ({CRITICAL:"var(--tag-split)", HIGH:"var(--tag-results)",
                               MEDIUM:"var(--tag-rights)", LOW:"var(--tag-dividend)",
                               INFO:"var(--tag-news)"} as any)[n.priority] || "var(--tag-news)" }}>
                      {({CRITICAL:"عاجل", HIGH:"مهم", MEDIUM:"متابعة",
                         LOW:"معلومة", INFO:"إشعار"} as any)[n.priority] || "إشعار"}
                    </span>
                  </p>
                  <p className="notif-msg">{n.message}</p>
                  <p className="notif-time">{n.created_at ? new Date(n.created_at).toLocaleString("en-US") : "—"}</p>
                </div>
                {isOwner && (
                  <div className="flex gap-1 shrink-0">
                    <button onClick={() => readMutation.mutate(n.id)} disabled={readMutation.isPending} title="تعليم كمقروء"
                      className="p-1.5 rounded-lg text-[var(--ink-muted)] hover:text-[var(--pos-ink)] transition-all disabled:opacity-40"><Check size={14} /></button>
                    <button onClick={() => deleteMutation.mutate(n.id)} disabled={deleteMutation.isPending} title="حذف"
                      className="p-1.5 rounded-lg text-[var(--ink-muted)] hover:text-[var(--neg-ink)] transition-all disabled:opacity-40"><Trash2 size={14} /></button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {allRead.length > 0 && (
        <div className="card">
          <h2 className="card-title mb-3">{t("notif.read")}</h2>
          <div className="space-y-1">
            {allRead.slice(0, READ_CAP).map((n: any) => (
              <div key={n.id} className="flex items-center gap-3 py-2 border-b border-[var(--hairline)] last:border-0 opacity-60">
                {extractSymbol(n) ? <CompanyLogo symbol={extractSymbol(n)!} size={22} /> : <Logo size={22} />}
                <p className="text-sm flex-1 text-[var(--ink)]">{n.title}</p>
                <p className="text-xs text-[var(--ink-muted)]">{n.created_at ? new Date(n.created_at).toLocaleDateString("en-GB") : "—"}</p>
                {isOwner && <button onClick={() => deleteMutation.mutate(n.id)} disabled={deleteMutation.isPending} title="حذف"
                  className="p-1 rounded-lg text-[var(--ink-muted)] hover:text-[var(--neg-ink)] transition-all disabled:opacity-40"><Trash2 size={12} /></button>}
              </div>
            ))}
          </div>
          {/* القصّ كان صامتاً: من له خمسون تنبيهاً مقروءاً يرى عشرين ويظنّ أن
              الباقي حُذف. العدد يُذكر صراحةً. */}
          {allRead.length > READ_CAP && (
            <p className="text-[11px] text-[var(--ink-muted)] text-center pt-3 mt-1" style={{ borderTop: "1px solid var(--line)" }}>
              عُرض أحدث {READ_CAP} من {allRead.length.toLocaleString("en-US")} تنبيهاً مقروءاً
            </p>
          )}
        </div>
      )}
    </div>
  );
}
