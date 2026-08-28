import React, { useEffect, useRef, useState } from "react";
import { invalidateWatchlist } from "../../services/watchlistCache";
import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import { Star, Search, Plus, X, ChevronDown, Check, Pencil, Trash2 } from "lucide-react";
import { marketApi } from "../../services/api";
import { useAuthStore } from "../../store/authStore";
import { searchCompanies } from "../../data/saudiCompanies";
import CompanyLogo from "../common/CompanyLogo";

/* لوحةُ الاختيار من عائلة الرسوم وحدها: الرموز الدلالية (ربح/خسارة/تحذير)
   ليست هويّاتٍ تُختار، واستعمالها هنا كان يُدخل الأحمر والأصفر الصارخين في
   موضعٍ لا معنى لهما فيه. */
const SWATCHES = [
  "var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)",
  "var(--chart-5)", "var(--chart-6)", "var(--chart-7)", "var(--ink-muted)",
];
const KEY = "sp_active_watchlist";

interface Group { id: number; name: string; color: string; is_default: boolean; }

/** قائمة المراقبة: قوائم متعدّدة (مثل المحافظ) — مبدّل قوائم + شركات كل قائمة. */
export default function WatchlistTab({ onOpen }: { onOpen: (symbol: string) => void }) {
  const qc = useQueryClient();
  const owner = useAuthStore((s: any) => s.isOwner);
  const [activeId, setActiveId] = useState<number | null>(() => {
    const v = Number(localStorage.getItem(KEY)); return Number.isFinite(v) && v > 0 ? v : null;
  });

  const { data: groups = [] } = useQuery<Group[]>({
    queryKey: ["watchlist-groups"],
    queryFn: () => marketApi.watchGroups().then(r => Array.isArray(r.data.data) ? r.data.data : []),
  });
  const active = groups.find(g => g.id === activeId) || groups.find(g => g.is_default) || groups[0];
  const gid = active?.id;

  const { data: rows = [], isLoading } = useQuery({
    queryKey: ["watchlist", gid],
    queryFn: () => marketApi.watchlist(gid).then(r => Array.isArray(r.data.data) ? r.data.data : []),
    enabled: gid != null,
    refetchInterval: 60000,
  });
  const remove = useMutation({
    mutationFn: (symbol: string) => marketApi.watchRemove(symbol, gid),
    onSuccess: () => invalidateWatchlist(qc),
  });
  const add = useMutation({
    mutationFn: (c: any) => marketApi.watchAdd(c.symbol, c.name_ar || c.name, gid),
    onSuccess: () => invalidateWatchlist(qc),
  });

  const setActive = (id: number) => { setActiveId(id); localStorage.setItem(KEY, String(id)); };

  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-4">
        <Star size={16} className="text-[var(--warn-ink)]" />
        <h2 className="card-title">قائمة المراقبة</h2>
        <div className="ms-auto flex items-center gap-2">
          <span className="text-[11px] text-[var(--ink-muted)]">{rows.length} شركة</span>
          <GroupSwitcher groups={groups} active={active} owner={owner} onSwitch={setActive} />
        </div>
      </div>
      {owner && gid != null && <WatchlistAdd onPick={(c: any) => add.mutate(c)} existing={rows.map((r: any) => r.symbol)} />}
      {isLoading ? (
        <div className="space-y-2 mt-3">{[...Array(3)].map((_, i) => <div key={i} className="h-12 skeleton" />)}</div>
      ) : rows.length === 0 ? (
        <div className="py-12 text-center text-[var(--ink-muted)] text-sm">لا شركات في هذه القائمة</div>
      ) : (
        /* الشركات ظاهرة مباشرةً — لا قائمة منسدلة تُخفي ما جئتَ لرؤيته. */
        <div className="space-y-1.5 mt-3">
          {rows.map((r: any) => {
            const up = (r.change_pct ?? 0) >= 0;
            return (
              <div key={r.symbol} className="flex items-center gap-3 p-2.5 rounded-xl panel hover:bg-[var(--field)] transition-colors">
                <button onClick={() => onOpen(r.symbol)} className="flex items-center gap-3 min-w-0 flex-1 text-start">
                  <CompanyLogo symbol={r.symbol} size={32} />
                  <span className="min-w-0">
                    <span className="text-[var(--ink)] text-[13px] font-semibold truncate block">{r.name}</span>
                    <span className="tag-b" style={{ fontSize: 10 }}>{r.symbol}</span>
                  </span>
                </button>
                <div className="text-end shrink-0">
                  <div className="text-[var(--ink)] tabular-nums text-sm">{r.price != null ? r.price.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "—"}</div>
                  {r.change_pct != null && (
                    <div className="text-[11px] font-bold" style={{ color: up ? "var(--pos-ink)" : "var(--neg-ink)" }}>
                      <span className="chg-arrow">{up ? "▲" : "▼"}</span> {up ? "+" : ""}{r.change_pct.toFixed(2)}%
                    </div>
                  )}
                </div>
                {owner && (
                  <button onClick={() => remove.mutate(r.symbol)} className="icon-live p-1.5 rounded-lg text-[var(--ink-muted)] hover:text-[var(--neg-ink)] transition-all shrink-0" title="إزالة"><X size={14} /></button>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/** مبدّل قوائم المراقبة — نفس نمط بوّابة المحافظ: تبديل + إنشاء + تعديل (اسم+لون) + حذف. */
function GroupSwitcher({ groups, active, owner, onSwitch }: {
  groups: Group[]; active?: Group; owner: boolean; onSwitch: (id: number) => void;
}) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState(""); const [color, setColor] = useState(SWATCHES[0]);
  const [editId, setEditId] = useState<number | null>(null);
  const [editName, setEditName] = useState(""); const [editColor, setEditColor] = useState(SWATCHES[0]);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onDoc = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) { setOpen(false); setCreating(false); } };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const refresh = () => qc.invalidateQueries({ queryKey: ["watchlist-groups"] });
  const createMut = useMutation({
    mutationFn: () => marketApi.watchGroupCreate({ name: name.trim(), color }),
    onSuccess: (r) => { setName(""); setColor(SWATCHES[0]); setCreating(false); refresh(); onSwitch((r.data.data as Group).id); },
  });
  const updateMut = useMutation({
    mutationFn: ({ id, name, color }: { id: number; name: string; color: string }) => marketApi.watchGroupUpdate(id, { name, color }),
    onSuccess: () => { setEditId(null); refresh(); },
  });
  const removeMut = useMutation({
    mutationFn: (id: number) => marketApi.watchGroupRemove(id),
    onSuccess: () => { refresh(); },
  });

  if (groups.length === 0) return null;

  return (
    <div className="relative" ref={ref}>
      <button onClick={() => setOpen(v => !v)} title={active?.name}
        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl transition-colors"
        style={{ background: "var(--panel)", border: "1px solid var(--line)" }}>
        <span className="w-3 h-3 rounded-full shrink-0" style={{ background: active?.color || "var(--chart-1)" }} />
        <ChevronDown size={14} className={"text-[var(--ink-muted)] transition-transform " + (open ? "rotate-180" : "")} />
      </button>

      {open && (
        <div className="absolute top-full mt-2 end-0 z-40 w-60 rounded-2xl overflow-hidden shadow-2xl"
          style={{ background: "var(--bg)", border: "1px solid var(--field-line)" }}>
          <div className="px-3 pt-2.5 pb-1.5 text-[11px] text-[var(--ink-muted)]">القوائم</div>
          <div className="max-h-72 overflow-auto">
            {groups.map((g) => {
              const isActive = active?.id === g.id;
              if (editId === g.id) {
                const save = () => editName.trim() && updateMut.mutate({ id: g.id, name: editName.trim(), color: editColor });
                return (
                  <div key={g.id} className="px-3 py-2.5 space-y-2">
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
                <div key={g.id} className="group relative flex items-center px-3 py-2 hover:panel">
                  <button onClick={() => { onSwitch(g.id); setOpen(false); }} className="flex items-center gap-2.5 flex-1 min-w-0 text-start">
                    <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: g.color }} />
                    <span className="text-[13px] text-[var(--ink)] truncate flex-1">{g.name}</span>
                    {g.is_default && <span className="text-[9.5px] text-[var(--ink-muted)] shrink-0">افتراضية</span>}
                    {isActive && <Check size={15} className="text-[var(--brand-ink)] shrink-0" />}
                  </button>
                  {owner && (
                    <div className="absolute top-1/2 -translate-y-1/2 flex items-center gap-1 px-1.5 py-1 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity"
                      style={{ insetInlineEnd: 6, background: "var(--pop)", boxShadow: "-8px 0 8px var(--pop)" }}>
                      <button onClick={() => { setEditId(g.id); setEditName(g.name); setEditColor(g.color || SWATCHES[0]); }}
                        className="icon-live p-1 rounded-md text-[var(--ink-muted)]" title="تعديل (الاسم واللون)"><Pencil size={13} /></button>
                      {!g.is_default && groups.length > 1 && (
                        <button onClick={() => { if (confirm(`حذف قائمة «${g.name}» وشركاتها؟`)) removeMut.mutate(g.id); }}
                          className="icon-live p-1 rounded-md text-[var(--ink-muted)] hover:!text-[var(--neg-ink)]" title="حذف"><Trash2 size={13} /></button>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {owner && (
            <div style={{ borderTop: "1px solid var(--line)" }}>
              {!creating ? (
                <button onClick={() => setCreating(true)} className="w-full flex items-center gap-2 px-3 py-2.5 text-[13px] text-[var(--brand-ink)] hover:bg-[var(--field)]">
                  <Plus size={15} /> إنشاء قائمة
                </button>
              ) : (
                <div className="p-3 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <span className="text-[12px] text-[var(--ink)]">قائمة جديدة</span>
                    <button onClick={() => setCreating(false)} className="text-[var(--ink-muted)] hover:text-[var(--ink)]"><X size={14} /></button>
                  </div>
                  <input autoFocus className="input !py-1.5 text-[13px]" placeholder="اسم القائمة" value={name}
                    onChange={(e) => setName(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter" && name.trim()) createMut.mutate(); }} />
                  <div className="flex items-center gap-1.5 flex-wrap">
                    {SWATCHES.map((c) => (
                      <button key={c} onClick={() => setColor(c)} className="w-6 h-6 rounded-full transition-transform"
                        style={{ background: c, outline: color === c ? "2px solid #fff" : "none", outlineOffset: 1, transform: color === c ? "scale(1.1)" : "none" }} />
                    ))}
                  </div>
                  <button disabled={!name.trim() || createMut.isPending} onClick={() => createMut.mutate()}
                    className="btn-primary w-full !py-1.5 text-[13px] disabled:opacity-50">
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

/** بحثٌ صغير لإضافة شركة إلى القائمة من دليل تداول. */
function WatchlistAdd({ onPick, existing }: { onPick: (c: any) => void; existing: string[] }) {
  const [q, setQ] = useState("");
  const results = q.trim().length >= 1 ? searchCompanies(q.trim()).filter((c: any) => !existing.includes(c.symbol)).slice(0, 6) : [];
  return (
    <div className="relative">
      <div className="flex items-center gap-2 panel border border-[var(--hairline)] rounded-xl px-3">
        <Search size={15} className="text-[var(--ink-muted)] shrink-0" />
        <input value={q} onChange={e => setQ(e.target.value)} placeholder="أضف شركة للمراقبة — بالاسم أو الرمز"
          className="flex-1 bg-transparent py-2.5 text-sm text-[var(--ink)] placeholder:text-[var(--ink-muted)] focus:outline-none" />
      </div>
      {results.length > 0 && (
        <div className="absolute z-20 left-0 right-0 mt-1 bg-[var(--raised)] border border-[var(--hairline)] rounded-xl overflow-hidden shadow-xl">
          {results.map((c: any) => (
            <button key={c.symbol} onClick={() => { onPick(c); setQ(""); }}
              className="w-full flex items-center gap-2.5 px-3 py-2.5 hover:bg-[var(--field)] text-start transition-colors">
              <CompanyLogo symbol={c.symbol} size={26} />
              <span className="text-[var(--ink)] text-[13px] font-semibold flex-1 truncate">{c.name_ar || c.name}</span>
              <span className="tag-b" style={{ fontSize: 10 }}>{c.symbol}</span>
              <Plus size={14} className="text-[var(--pos-ink)] shrink-0" />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
