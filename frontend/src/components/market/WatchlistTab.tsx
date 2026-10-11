import React, { useEffect, useRef, useState } from "react";
import { invalidateWatchlist } from "../../services/watchlistCache";
import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import { Star, Search, Plus, X, ChevronDown, Check, Pencil, Trash2 } from "lucide-react";
import LivePrice from "../common/LivePrice";
import { marketApi } from "../../services/api";
import { useAuthStore } from "../../store/authStore";
import { searchCompanies } from "../../data/saudiCompanies";
import CompanyLogo from "../common/CompanyLogo";
import { useAppStore } from "../../store/appStore";
import { useLongPressSort } from "../../hooks/useLongPressSort";

/* لوحةُ الاختيار من عائلة الرسوم وحدها: الرموز الدلالية (ربح/خسارة/تحذير)
   ليست هويّاتٍ تُختار، واستعمالها هنا كان يُدخل الأحمر والأصفر الصارخين في
   موضعٍ لا معنى لهما فيه. */
const SWATCHES = [
  "var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)",
  "var(--chart-5)", "var(--chart-6)", "var(--chart-7)", "var(--ink-muted)",
];
const KEY = "sp_active_watchlist";

interface Group { id: number; name: string; color: string; is_default: boolean; }

/** قسمُ «الشاشة» (‏D683 بأمر المالك: كان «المراقبة» · D677: قسمٌ في القائمة مكانَ مختبر الأبحاث): قوائمُ متعدّدة —
 *  مبدّلٌ وبطاقةٌ لكلّ شركة، تُرتَّب بالضغط المطوّل والسحب. */
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

  /* ‏D558: أُلغيت «غرفة التداول» بأمر المالك — شركاتُها تُنقل مرّةً إلى هذه القائمة في المحفظة الحالية */
  const roomSymbols = useAppStore((s: any) => s.roomSymbols) as string[] | undefined;
  const setRoomSymbols = useAppStore((s: any) => s.setRoomSymbols);
  const moved = useRef(false);
  useEffect(() => {
    if (moved.current || !owner || gid == null || isLoading || !roomSymbols?.length) return;
    moved.current = true;
    const have = new Set(rows.map((r: any) => String(r.symbol)));
    const todo = roomSymbols.filter(x => /^\d{4}$/.test(x) && !have.has(x));
    Promise.allSettled(todo.map(x => marketApi.watchAdd(x, undefined, gid)))
      .then(res => { if (res.every(r => r.status === "fulfilled")) setRoomSymbols([]); invalidateWatchlist(qc); });
  }, [owner, gid, isLoading, roomSymbols, rows]);

  const [editing, setEditing] = useState(false);
  const setActive = (id: number) => { setActiveId(id); localStorage.setItem(KEY, String(id)); };

  /* ‏D677: تفاصيلُ كلّ شركةٍ من الفرز المخزَّن نفسِه (مفتاحُه مشتركٌ مع المختبر فلا يُطلب مرّتين): السعرُ العادل وثقتُه
     والقرار — رقمُ اليوم الذي تعرضه صفحةُ السهم، لا حسابٌ ثانٍ */
  const { data: scr = [] } = useQuery({
    queryKey: ["screener-lite"], staleTime: 30 * 60_000,
    queryFn: () => marketApi.screener().then(r => {
      const d = r.data?.data;
      return (Array.isArray(d) ? d : Array.isArray(d?.rows) ? d.rows : []) as any[];
    }),
  });
  const info: Record<string, any> = Object.fromEntries(scr.map((x: any) => [String(x.symbol).replace(".SR", ""), x]));
  const desk = useDesk();

  /* ‏D683: الترتيبُ بالضغط المطوّل ثمّ السحب — يُحفظ على الخادم، ويُعرض فوراً قبل ردّه */
  const order = useMutation({
    mutationFn: (symbols: string[]) => marketApi.watchOrder(symbols, gid),
    onError: () => invalidateWatchlist(qc),
  });
  const sort = useLongPressSort(rows as any[], (r: any) => String(r.symbol), (next) => {
    qc.setQueryData(["watchlist", gid], next);
    order.mutate(next.map((r: any) => String(r.symbol)));
  }, { enabled: !!owner });

  return (
    <div className="space-y-3">
      <div className="card">
        <div className="flex items-center gap-2">
          <Star size={18} className="text-[var(--warn-ink)]" />
          <h1 className="text-xl font-medium text-[var(--ink)]">الشاشة</h1>
          <div className="ms-auto flex items-center gap-2">
            <span className="text-[11px] text-[var(--ink-muted)] tabular-nums">{rows.length} شركة</span>
            {owner && rows.length > 0 && (
              <button onClick={() => setEditing(e => !e)} aria-label={editing ? "إنهاء التعديل" : "تعديل القائمة"}
                className="w-8 h-8 grid place-items-center rounded-lg transition-colors"
                style={{ color: editing ? "var(--brand-ink)" : "var(--ink-muted)", background: editing ? "var(--field)" : undefined }}>
                {editing ? <Check size={15} /> : <Pencil size={14} />}
              </button>
            )}
            <GroupSwitcher groups={groups} active={active} owner={owner} onSwitch={setActive} />
          </div>
        </div>
        {owner && gid != null && <div className="mt-3"><WatchlistAdd onPick={(c: any) => add.mutate(c)} existing={rows.map((r: any) => r.symbol)} /></div>}
      </div>
      {isLoading ? (
        <div className={GRID}>{[...Array(6)].map((_, i) => <div key={i} className="h-36 skeleton rounded-2xl" />)}</div>
      ) : rows.length === 0 ? (
        <div className="card py-12 text-center text-[var(--ink-muted)] text-sm">لا شركات في هذه القائمة</div>
      ) : (
        /* ‏D677 · D683 (بأمر المالك): بطاقةٌ لكلّ شركة — ثلاثٌ في الصفّ على الجوال وعلى الحاسوب. والبطاقةُ خاناتٌ ثابتة
           تصطفّ بين البطاقات: الهويّة (سطران محجوزان)، ثمّ شبكةٌ من عمودين — السعرُ وتغيّرُه، ثمّ العادلُ والقرار —
           والقرارُ في عمود التغيّر وفي منتصفه تحته */
        <div ref={sort.boxRef} className={GRID}>
          {sort.list.map((r: any) => (
            <div key={r.symbol} {...sort.itemProps(String(r.symbol))} className="min-w-0">
              <ScreenCard r={r} x={info[String(r.symbol)] || {}} desk={desk} onOpen={onOpen}
                lifted={sort.dragKey === String(r.symbol)}
                onRemove={owner && editing ? () => remove.mutate(r.symbol) : undefined} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* الشبكة (‏D685 بأمر المالك: «أضف سطراً أفقياً حتى يظهر أكبرُ قدرٍ ممكن»): أربعٌ في الصفّ على الحاسوب، وثلاثٌ على
   الجوال — جُرّبت الأربعُ فيه بخليّةٍ مدمجة فقال المالك: «أربعُ أعمدةٍ غيرُ جميل على الجوال، خلّه ثلاثة» */
const GRID = "grid grid-cols-3 lg:grid-cols-4 gap-2 md:gap-3";

function useDesk() {
  const q = "(min-width: 768px)";
  const [desk, setDesk] = useState(() => typeof window !== "undefined" && !!window.matchMedia?.(q).matches);
  useEffect(() => {
    const m = window.matchMedia?.(q);
    if (!m) return;
    const on = () => setDesk(m.matches);
    m.addEventListener("change", on); on();
    return () => m.removeEventListener("change", on);
  }, []);
  return desk;
}

function ScreenCard({ r, x, desk, onOpen, lifted, onRemove }: {
  r: any; x: any; desk: boolean; onOpen: (s: string) => void; lifted: boolean; onRemove?: () => void;
}) {
  const up = (r.change_pct ?? 0) >= 0;
  const ink = r.change_pct == null ? "var(--ink-muted)" : up ? "var(--pos-ink)" : "var(--neg-ink)";
  const fv = typeof x.fair_value === "number" && x.fair_value > 0 ? x.fair_value : null;
  const ups = typeof x.upside_pct === "number" ? x.upside_pct : null;
  const dec = typeof x.decision === "string" ? x.decision : null;
  const decInk = dec ? (DECISION_INK[dec] || "var(--ink-muted)") : "var(--ink-muted)";
  const chgBadge = (
    <span data-role="chg" className="text-[9.5px] md:text-[12px] font-bold tabular-nums px-1 md:px-1.5 py-0.5 rounded-md whitespace-nowrap"
      style={{ color: ink, background: `color-mix(in srgb, ${ink} 10%, transparent)` }}>
      {r.change_pct == null ? "—" : <>
        {desk && <span className="chg-arrow">{up ? "▲" : "▼"} </span>}
        <span dir="ltr">{up ? "+" : ""}{r.change_pct.toFixed(2)}%</span></>}
    </span>
  );
  return (
    <div className="relative h-full rounded-2xl border bg-[var(--surface)] transition-colors"
      style={{ borderColor: lifted ? "transparent" : "var(--hairline)" }}>
      {/* عمودٌ مرنٌ يبدأ من أعلى: الزرُّ يوسِّط محتواه رأسياً افتراضاً، فالبطاقةُ الأقصرُ في صفٍّ أطول (سابك بلا عادل)
          كان رأسُها ينزل 8px عن جاراتها — قِيس */}
      <button onClick={() => onOpen(r.symbol)} className="w-full h-full text-start min-w-0 flex flex-col justify-start p-2 md:p-4">
        <span className={"flex items-start gap-1.5 md:gap-2.5 min-w-0" + (onRemove ? " pe-7" : "")}>
          <CompanyLogo symbol={r.symbol} size={desk ? 34 : 24} />
          <span className="min-w-0 flex-1">
            <span data-role="name" className="text-[var(--ink)] text-[11px] md:text-[14px] font-semibold leading-[1.35] line-clamp-2 min-h-[2.7em] md:min-h-0 md:line-clamp-1">{r.name}</span>
            <span className="block text-[9.5px] md:text-[10.5px] text-[var(--brand-ink)] tabular-nums mt-0.5">{r.symbol}</span>
          </span>
        </span>
        <span className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-1.5 md:gap-x-3 gap-y-1.5 md:gap-y-2.5 mt-2 md:mt-3">
          {/* هامشُ الوميض صفرٌ هنا: السالبُ (‎-4px) يُخرج الرقمَ عن خانته فتقصّه الخانة («24.1(») */}
          <span data-role="price" className={"text-[var(--ink)] tabular-nums font-semibold truncate md:text-[19px] "
            + (Math.abs(r.price ?? 0) >= 1000 ? "text-[12px]" : "text-[13.5px]")}>
            <LivePrice symbol={r.symbol} fallback={r.price} style={{ margin: 0 }} />
          </span>
          <span className="justify-self-center">{chgBadge}</span>
          <span className="col-span-2 border-t border-[var(--hairline)]" aria-hidden />
          <span className="min-w-0 text-[9.5px] md:text-[11px] text-[var(--ink-muted)] leading-[1.4]">
            <span className="block md:inline">العادل</span>{" "}
            <span className="block md:inline text-[var(--ink)] font-semibold tabular-nums text-[10.5px] md:text-[11px]">{fv ? fv.toFixed(2) : "—"}</span>{" "}
            {ups != null && fv != null && (
              <span className="block md:inline"><span className="tabular-nums" dir="ltr" style={{ color: ups >= 0 ? "var(--pos-ink)" : "var(--neg-ink)" }}>
                {ups >= 0 ? "+" : ""}{ups.toFixed(1)}%</span></span>
            )}
          </span>
          <span data-role="dec" className="justify-self-center text-[11.5px] font-bold whitespace-nowrap" style={{ color: decInk }}>{dec || "—"}</span>
        </span>
      </button>
      {onRemove && (
        <button onClick={onRemove} aria-label="إزالة" title="إزالة"
          className="icon-live absolute top-1 end-1 md:top-2 md:end-2 w-8 h-8 grid place-items-center rounded-lg text-[var(--ink-muted)] hover:text-[var(--neg-ink)] transition-all"><X size={14} /></button>
      )}
    </div>
  );
}

/* لونُ القرار من رموز التطبيق — كما في صفحة السهم */
const DECISION_INK: Record<string, string> = {
  "شراء قوي": "var(--pos-ink)", "شراء": "var(--pos-ink)", "احتفاظ": "var(--ink)",
  "انتظار": "var(--warn-ink)", "تجنب": "var(--neg-ink)",
};

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
        <div className="menu-pop absolute top-full mt-2 end-0 z-40 w-60 rounded-2xl overflow-hidden shadow-2xl"
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
        <input value={q} onChange={e => setQ(e.target.value)} placeholder="أضف شركة إلى الشاشة — بالاسم أو الرمز"
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
