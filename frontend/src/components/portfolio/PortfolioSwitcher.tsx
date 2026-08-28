import React, { useEffect, useRef, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Check, ChevronDown, Plus, X, Pencil, Trash2 } from "lucide-react";
import { portfoliosApi } from "../../services/api";
import { usePortfolioStore } from "../../store/portfolioStore";
import { useAuthStore } from "../../store/authStore";

interface Portfolio {
  id: number;
  name: string;
  color: string;
  is_default: boolean;
  include_in_aggregate: boolean;
}

// لوحة ألوان هادئة ومرتّبة لاختيار لون المحفظة عند الإنشاء.
/* لوحةُ الاختيار من عائلة الرسوم وحدها: الرموز الدلالية (ربح/خسارة/تحذير)
   ليست هويّاتٍ تُختار، واستعمالها هنا كان يُدخل الأحمر والأصفر الصارخين في
   موضعٍ لا معنى لهما فيه. */
const SWATCHES = [
  "var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)",
  "var(--chart-5)", "var(--chart-6)", "var(--chart-7)", "var(--ink-muted)",
];

export default function PortfolioSwitcher() {
  const qc = useQueryClient();
  const { isOwner } = useAuthStore();
  const activeId = usePortfolioStore((s) => s.activeId);
  const setActive = usePortfolioStore((s) => s.setActive);
  const unified = usePortfolioStore((s) => s.unified);
  const setUnified = usePortfolioStore((s) => s.setUnified);
  const [open, setOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [color, setColor] = useState(SWATCHES[0]);
  const [editId, setEditId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  const { data: portfolios = [] } = useQuery<Portfolio[]>({
    queryKey: ["portfolios"],
    queryFn: () => portfoliosApi.list().then((r) => r.data.data),
  });

  // إن لم تُختَر محفظة نشطة بعد، نتبنّى الافتراضية ضمنيًا للعرض.
  const active =
    portfolios.find((p) => String(p.id) === String(activeId)) ||
    portfolios.find((p) => p.is_default) ||
    portfolios[0];

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
        setCreating(false);
      }
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const switchTo = (id: number) => {
    setActive(id);
    setOpen(false);
    // كل البيانات مرتبطة بالمحفظة — نُبطل الكاش كي تُعاد بالترويسة الجديدة.
    qc.invalidateQueries();
  };

  const [editColor, setEditColor] = useState(SWATCHES[0]);
  const renameMut = useMutation({
    mutationFn: ({ id, name, color }: { id: number; name: string; color: string }) => portfoliosApi.update(id, { name, color }),
    onSuccess: () => { setEditId(null); qc.invalidateQueries({ queryKey: ["portfolios"] }); },
  });

  const removeMut = useMutation({
    mutationFn: (id: number) => portfoliosApi.remove(id),
    onSuccess: (_r, id) => {
      // إن حُذفت المحفظة النشطة، ننتقل للافتراضية/الأولى المتبقية.
      if (String(id) === String(active?.id)) setActive(null);
      qc.invalidateQueries();
    },
  });

  const createMut = useMutation({
    mutationFn: () => portfoliosApi.create({ name: name.trim(), color }),
    onSuccess: (r) => {
      const created = r.data.data as Portfolio;
      setName("");
      setColor(SWATCHES[0]);
      setCreating(false);
      qc.invalidateQueries({ queryKey: ["portfolios"] });
      switchTo(created.id);
    },
  });

  if (portfolios.length === 0) return null;

  return (
    <div className="relative" ref={ref}>
      {/* البوّابة المطوية: رمز المحفظة اللوني + السهم فقط — الاسم يظهر عند الفتح */}
      <button
        onClick={() => setOpen((v) => !v)}
        title={active?.name}
        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl transition-colors"
        style={{ background: "var(--surface)" }}
      >
        <span className="w-3 h-3 rounded-full shrink-0" style={{ background: active?.color || "var(--chart-1)" }} />
        <ChevronDown size={15} className={`text-[var(--ink-muted)] transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div
          className="sp-menu absolute top-full mt-2 end-0 z-40 w-64 rounded-2xl overflow-hidden shadow-2xl"
        >
          <div className="px-3 pt-2.5 pb-1.5 text-[11px] text-[var(--ink-muted)]">المحافظ</div>

          <div className="max-h-72 overflow-auto">
            {portfolios.map((p) => {
              const isActive = active?.id === p.id;
              const editing = editId === p.id;
              if (editing) {
                const save = () => editName.trim() && renameMut.mutate({ id: p.id, name: editName.trim(), color: editColor });
                return (
                  <div key={p.id} className="px-3 py-2.5 space-y-2">
                    <div className="flex items-center gap-2">
                      <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: editColor }} />
                      <input autoFocus value={editName} onChange={(e) => setEditName(e.target.value)}
                        onKeyDown={(e) => { if (e.key === "Enter") save(); if (e.key === "Escape") setEditId(null); }}
                        className="input !py-1 text-[13px] flex-1" />
                      <button onClick={save} title="حفظ" aria-label="حفظ" className="text-[var(--pos-ink)] hover:text-[var(--pos-ink)] shrink-0"><Check size={15} /></button>
                      <button onClick={() => setEditId(null)} className="text-[var(--ink-muted)] hover:text-[var(--ink)] shrink-0"><X size={14} /></button>
                    </div>
                    <div className="flex items-center gap-1.5 flex-wrap ps-4">
                      {SWATCHES.map((c) => (
                        <button key={c} onClick={() => setEditColor(c)} className="w-5 h-5 rounded-full transition-transform"
                          style={{ background: c, outline: editColor === c ? "2px solid #fff" : "none", outlineOffset: 1, transform: editColor === c ? "scale(1.12)" : "none" }} />
                      ))}
                    </div>
                  </div>
                );
              }
              return (
                <div key={p.id} className="group relative flex items-center px-3 py-2 hover:panel">
                  <button onClick={() => switchTo(p.id)} className="flex items-center gap-2.5 flex-1 min-w-0 text-start">
                    <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: p.color }} />
                    <span className="text-[13px] text-[var(--ink)] truncate flex-1">{p.name}</span>
                    {p.is_default && <span className="text-[9.5px] text-[var(--ink-muted)] shrink-0">افتراضية</span>}
                    {isActive && <Check size={15} className="text-[var(--brand-ink)] shrink-0" />}
                  </button>
                  {/* أزرار منبثقة فوق نهاية الصف عند التمرير — لا تأخذ حيّز الاسم */}
                  {isOwner && (
                    <div className="absolute top-1/2 -translate-y-1/2 flex items-center gap-1 px-1.5 py-1 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity"
                      style={{ insetInlineEnd: 6, background: "var(--pop)", boxShadow: "-8px 0 8px var(--pop)" }}>
                      <button onClick={() => { setEditId(p.id); setEditName(p.name); setEditColor(p.color || SWATCHES[0]); }}
                        className="icon-live p-1 rounded-md text-[var(--ink-muted)]" title="تعديل (الاسم واللون)">
                        <Pencil size={13} />
                      </button>
                      {!p.is_default && portfolios.length > 1 && (
                        <button onClick={() => { if (confirm(`حذف محفظة «${p.name}»؟ (تُؤرشَف وبياناتها محفوظة)`)) removeMut.mutate(p.id); }}
                          className="icon-live p-1 rounded-md text-[var(--ink-muted)] hover:!text-[var(--neg-ink)]" title="حذف المحفظة">
                          <Trash2 size={13} />
                        </button>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* سويتش توحيد الثروة — أسفل قوائم المحافظ. تشغيل = تُجمَع الثروة
              والرسوم عبر كل المحافظ؛ إطفاء = كل محفظة منفصلة. */}
          <div className="flex items-center gap-2 px-3 py-2.5" style={{ borderTop: "1px solid var(--line)" }}>
            <div className="flex-1 min-w-0">
              <div className="text-[12px] font-bold text-[var(--ink)]">توحيد الثروة</div>
              <div className="text-[10px] text-[var(--ink-muted)]">{unified ? "مجموع كل المحافظ" : "كل محفظة على حدة"}</div>
            </div>
            <button
              onClick={() => { setUnified(!unified); qc.invalidateQueries(); }}
              role="switch" aria-checked={unified}
              title="توحيد الثروة"
              className={"switch" + (unified ? " on" : "")} />
          </div>

          {isOwner && (
            <div style={{ borderTop: "1px solid var(--line)" }}>
              {!creating ? (
                <button
                  onClick={() => setCreating(true)}
                  className="w-full flex items-center gap-2 px-3 py-2.5 text-[13px] text-[var(--brand-ink)] hover:bg-[var(--field)]"
                >
                  <Plus size={15} /> إنشاء محفظة
                </button>
              ) : (
                <div className="p-3 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <span className="text-[12px] text-[var(--ink)]">محفظة جديدة</span>
                    <button onClick={() => setCreating(false)} className="text-[var(--ink-muted)] hover:text-[var(--ink)]">
                      <X size={14} />
                    </button>
                  </div>
                  <input
                    autoFocus
                    className="input !py-1.5 text-[13px]"
                    placeholder="اسم المحفظة"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && name.trim()) createMut.mutate();
                    }}
                  />
                  <div className="flex items-center gap-1.5 flex-wrap">
                    {SWATCHES.map((c) => (
                      <button
                        key={c}
                        onClick={() => setColor(c)}
                        className="w-6 h-6 rounded-full transition-transform"
                        style={{
                          background: c,
                          outline: color === c ? "2px solid #fff" : "none",
                          outlineOffset: 1,
                          transform: color === c ? "scale(1.1)" : "none",
                        }}
                      />
                    ))}
                  </div>
                  <button
                    disabled={!name.trim() || createMut.isPending}
                    onClick={() => createMut.mutate()}
                    className="btn-primary w-full !py-1.5 text-[13px] disabled:opacity-50"
                  >
                    {createMut.isPending ? "..." : "إنشاء"}
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
