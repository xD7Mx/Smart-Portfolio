/* ══ غرفة التداول — رسمٌ وقوائمُ مراقبة في شاشةٍ واحدة ══ (بأمر المالك 2026-11-14 · D732)
   «أضيف شركات في القائمة المفضّلة، وأضع قوائم — للسوق الأمريكي وللسوق السعودي… وإذا ضغطتُ على الشركة يظهر الشارت
   بخصائصه: ستوكاستيك، RSI، الماكد، CVD… والمؤشّر حقّي». فالرسمُ في الصدر والقوائمُ بجانبه (تحته على الجوال):
   «محفظتي» و«المؤشرات» قائمتان ثابتتان، وقوائمُ المالك تُنشأ وتُحذف ويُضاف إليها من السوقين بحقل بحثٍ واحد،
   والضغطُ على سطرٍ يفتح رسمَه. والقوائمُ من خادم «المراقبة» نفسِه.
   ‏D736 (المالك 2026-11-15): «المستخدم عربيّ — الشركاتُ في اليمين والرسمُ البيانيُّ على اليسار»، والرسمُ هو الاحترافيُّ الجديد
   (‏chart/ProChart) يبقى قائماً حين يتبدّل الرمز — لا يُهدم ويُبنى. */
import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, X, Pencil, Check, Trash2, Layers } from "lucide-react";
import ProChart from "../chart/ProChart";
import CompanyLogo from "../common/CompanyLogo";
import InlineStockSearch from "./InlineStockSearch";
import OptionChain from "./OptionChain";
import { isOption, optionSub, optionTitle, parseOption } from "../../lib/options";
import { holdingsApi, marketApi } from "../../services/api";
import { invalidateWatchlist } from "../../services/watchlistCache";
import { useAppStore } from "../../store/appStore";
import { useAuthStore } from "../../store/authStore";

const INDICES: [string, string][] = [
  ["^TASI.SR", "تاسي"], ["^GSPC", "S&P 500"], ["^IXIC", "ناسداك"], ["^DJI", "داو جونز"],
  ["BZ=F", "برنت"], ["GC=F", "الذهب"], ["BTC-USD", "بتكوين"],
];
const PRESETS = ["السوق السعودي", "السوق الأمريكي"];
type Row = { symbol: string; name: string; price?: number | null; change_pct?: number | null };
const isSaudi = (s: string) => /^\d{4}(\.SR)?$/.test(s);
const pct = (v?: number | null) => v == null || !isFinite(Number(v)) ? null : Number(v);
/* ‏D747: لأيّ سهمٍ أو صندوقٍ أمريكيّ سلسلةُ خيارات — والمؤشّرُ إلى مؤشّر خياراته (‏S&P 500 ⇐ SPX · ناسداك ⇐ NDX) */
const OPT_INDEX: Record<string, string> = { "^GSPC": "^SPX", "^SPX": "^SPX", "^IXIC": "^NDX", "^NDX": "^NDX", "^RUT": "^RUT", "^VIX": "^VIX" };
const chainOf = (s: string): string | null => {
  const o = parseOption(s);
  if (o) return o.root;
  if (OPT_INDEX[s]) return OPT_INDEX[s];
  return /^[A-Z][A-Z.\-]{0,6}$/.test(s) && !isSaudi(s) && !/-USD$/.test(s) ? s : null;
};

export default function TradeRoom() {
  const qc = useQueryClient();
  const { theme } = useAppStore();
  const owner = useAuthStore((s: any) => s.isOwner);
  const [list, setListState] = useState<string>(() => { try { return localStorage.getItem("sp_room_list") || "mine"; } catch { return "mine"; } });
  const setList = (v: string) => { setListState(v); try { localStorage.setItem("sp_room_list", v); } catch { /* خاصّ */ } };
  const [sym, setSymState] = useState<string | null>(() => { try { return localStorage.getItem("sp_room_symbol"); } catch { return null; } });
  const chartRef = useRef<HTMLDivElement>(null);
  const pick = (s: string) => {
    setSymState(s); try { localStorage.setItem("sp_room_symbol", s); } catch { /* خاصّ */ }
    // على الجوال القائمةُ تحت الرسم — يُعاد إليه بانسياب
    if (window.innerWidth < 1024) chartRef.current?.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
  };
  const [editing, setEditing] = useState(false);
  const [chainFor, setChainFor] = useState<string | null>(null);
  const [naming, setNaming] = useState<string | null>(null);

  const { data: holdings = [] } = useQuery({
    queryKey: ["holdings"],
    queryFn: () => holdingsApi.list().then(r => (Array.isArray(r.data?.data) ? r.data.data : [])),
  });
  const { data: groups = [] } = useQuery<any[]>({
    queryKey: ["watchlist-groups"],
    queryFn: () => marketApi.watchGroups().then(r => (Array.isArray(r.data.data) ? r.data.data : [])),
  });
  const gid = list.startsWith("g") ? Number(list.slice(1)) : null;
  const group = groups.find((g: any) => g.id === gid);
  useEffect(() => { if (gid != null && groups.length && !group) setList("mine"); }, [gid, groups.length, group]);
  const { data: wrows = [], isFetching } = useQuery<Row[]>({
    queryKey: ["watchlist", gid],
    queryFn: () => marketApi.watchlist(gid!).then(r => (Array.isArray(r.data.data) ? r.data.data : [])),
    enabled: gid != null && !!group, refetchInterval: 60_000,
  });

  const rows: Row[] = useMemo(() => {
    if (list === "mine") return holdings.filter((h: any) => h.company?.symbol).map((h: any) => ({
      symbol: h.company.symbol, name: h.company.name_ar || h.company.name || h.company.company_name,
      price: Number(h.last_price) || null, change_pct: pct(h.change_pct) }));
    if (list === "idx") return INDICES.map(([s, n]) => ({ symbol: s, name: n }));
    return wrows;
  }, [list, holdings, wrows]);

  const symbol = sym || rows[0]?.symbol || "^TASI.SR";
  const label = INDICES.find(([s]) => s === symbol)?.[1];

  const add = useMutation({
    mutationFn: (a: { s: string; name?: string }) => marketApi.watchAdd(a.s, a.name, gid!),
    onSuccess: () => invalidateWatchlist(qc),
  });
  const remove = useMutation({
    mutationFn: (s: string) => marketApi.watchRemove(s, gid!),
    onSuccess: () => invalidateWatchlist(qc),
  });
  const create = useMutation({
    mutationFn: (name: string) => marketApi.watchGroupCreate({ name }),
    onSuccess: (r: any) => {
      setNaming(null);
      qc.invalidateQueries({ queryKey: ["watchlist-groups"] }).then(() => {
        const id = r?.data?.data?.id; if (id) setList(`g${id}`);
      });
    },
  });
  const dropGroup = useMutation({
    mutationFn: (id: number) => marketApi.watchGroupRemove(id),
    onSuccess: () => { setList("mine"); setEditing(false); qc.invalidateQueries({ queryKey: ["watchlist-groups"] }); invalidateWatchlist(qc); },
  });
  const missingPresets = PRESETS.filter(p => !groups.some((g: any) => g.name === p));

  const tabs: [string, string][] = [["mine", "محفظتي"], ["idx", "المؤشرات"], ...groups.map((g: any) => [`g${g.id}`, g.name] as [string, string])];

  return (
    <div className="troom" data-role="troom">
      <aside className="troom-list card" data-role="troom-list">
        <div className="troom-tabs" role="tablist" aria-label="القوائم">
          {tabs.map(([id, name]) => (
            <button key={id} type="button" role="tab" aria-selected={list === id} data-role="troom-tab"
              className={"seg-btn chip" + (list === id ? " on" : "")} onClick={() => { setList(id); setEditing(false); }}>{name}</button>
          ))}
          {owner && (
            <button type="button" className="seg-btn chip troom-new" title="قائمة جديدة" aria-label="قائمة جديدة" data-role="troom-new"
              onClick={() => setNaming(n => n == null ? "" : null)}><Plus size={14} /></button>
          )}
        </div>

        {naming != null && (
          <div className="troom-naming" data-role="troom-naming">
            <input className="input" autoFocus placeholder="اسمُ القائمة" value={naming} aria-label="اسم القائمة"
              onChange={e => setNaming(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter" && naming.trim()) create.mutate(naming.trim()); if (e.key === "Escape") setNaming(null); }} />
            <button type="button" className="btn-primary troom-icon" disabled={!naming.trim() || create.isPending}
              onClick={() => create.mutate(naming.trim())} title="إنشاء" aria-label="إنشاء"><Check size={15} /></button>
            {missingPresets.map(p => (
              <button key={p} type="button" className="seg-btn chip" onClick={() => create.mutate(p)} data-role="troom-preset">{p}</button>
            ))}
          </div>
        )}

        {gid != null && group && (
          <div className="troom-bar">
            {owner && <InlineStockSearch onPick={s => add.mutate({ s })} global />}
            <span className="text-[11px] text-[var(--ink-muted)] tabular-nums ms-auto">{wrows.length}</span>
            {owner && (
              <button type="button" className={"btn-ghost troom-icon" + (editing ? " on" : "")} title={editing ? "تمّ" : "تحرير القائمة"}
                aria-label="تحرير القائمة" onClick={() => setEditing(e => !e)} data-role="troom-edit">
                {editing ? <Check size={15} /> : <Pencil size={14} />}
              </button>
            )}
            {owner && editing && !group.is_default && (
              <button type="button" className="btn-ghost troom-icon troom-danger" title={`حذف قائمة «${group.name}»`} aria-label="حذف القائمة"
                onClick={() => { if (window.confirm(`حذفُ قائمة «${group.name}» وما فيها؟`)) dropGroup.mutate(group.id); }}>
                <Trash2 size={14} />
              </button>
            )}
          </div>
        )}

        <div className="troom-rows" data-role="troom-rows">
          {rows.map((r, i) => {
            const ch = pct(r.change_pct);
            const on = r.symbol === symbol;
            return (
              <div key={r.symbol} className={"troom-row card-rise" + (on ? " on" : "")} style={{ animationDelay: `${Math.min(i, 14) * 18}ms` }}>
                <button type="button" className="troom-pick" onClick={() => pick(r.symbol)} aria-pressed={on} data-role="troom-row"
                  title={r.name}>
                  <CompanyLogo symbol={r.symbol} size={24} />
                  <span className="min-w-0 flex-1 text-start">
                    {(() => {
                      const o = parseOption(r.symbol);
                      if (o) return (<>
                        <span className="block text-[12.5px] font-bold text-[var(--ink)] truncate">{optionTitle(o)}</span>
                        <span className="block text-[10px] text-[var(--ink-muted)] truncate tabular-nums">{optionSub(o)}</span>
                      </>);
                      return (<>
                        <span className="block text-[12.5px] font-bold text-[var(--ink)] truncate">{list === "idx" ? r.name : (isSaudi(r.symbol) ? r.name : r.symbol)}</span>
                        <span className="block text-[10px] text-[var(--ink-muted)] truncate tabular-nums" dir={isSaudi(r.symbol) ? undefined : "ltr"}
                          style={{ textAlign: "right" }}>
                          {list === "idx" ? r.symbol : isSaudi(r.symbol) ? r.symbol.replace(".SR", "") : (r.name !== r.symbol ? r.name : "")}
                        </span>
                      </>);
                    })()}
                  </span>
                  {r.price != null && (
                    <span className="text-end shrink-0">
                      <span className="block text-[12.5px] font-bold tabular-nums text-[var(--ink)]" dir="ltr">{Number(r.price).toFixed(2)}</span>
                      {ch != null && <span className={"block text-[10.5px] font-bold tabular-nums " + (ch >= 0 ? "text-[var(--pos-ink)]" : "text-[var(--neg-ink)]")} dir="ltr">
                        {(ch >= 0 ? "+" : "") + ch.toFixed(2)}%</span>}
                    </span>
                  )}
                </button>
                {editing && gid != null && (
                  <button type="button" className="btn-ghost troom-icon troom-danger" aria-label={`إزالة ${r.symbol}`} title="إزالة"
                    onClick={() => remove.mutate(r.symbol)} data-role="troom-remove"><X size={14} /></button>
                )}
              </div>
            );
          })}
          {!rows.length && (
            <div className="text-[12px] text-[var(--ink-muted)] text-center py-6">
              {gid != null ? (isFetching ? "…" : "القائمةُ فارغة.") : "لا شركات."}
            </div>
          )}
        </div>
      </aside>

      <section ref={chartRef} className="troom-chart card" data-role="troom-chart">
        <ProChart symbol={symbol} theme={theme === "light" ? "light" : "dark"}
          identity={<span className="flex items-center gap-1.5 min-w-0">
            <CompanyLogo symbol={symbol} size={26} />
            {isOption(symbol) ? (() => { const o = parseOption(symbol)!; return (<>
              <span className="text-[14px] font-bold text-[var(--ink)] tabular-nums whitespace-nowrap">{optionTitle(o)}</span>
              <span className="troom-osub tabular-nums">{optionSub(o)}</span>
            </>); })() : (<>
              <span className="text-[14px] font-bold text-[var(--ink)] tabular-nums" dir="ltr">{label || symbol.replace(".SR", "")}</span>
              {!label && <span className="text-[12px] text-[var(--ink-muted)] truncate max-w-[40vw] lg:max-w-[180px]">
                {rows.find(r => r.symbol === symbol)?.name || ""}</span>}
            </>)}
            {chainOf(symbol) && (
              <button type="button" className="btn-ghost troom-oc" onClick={() => setChainFor(chainOf(symbol))} data-role="troom-options"
                title="عقود الخيارات" aria-label={`عقود خيارات ${chainOf(symbol)}`}>
                <Layers size={13} className="inline-block align-[-2px] me-1" />الخيارات
              </button>
            )}
          </span>} />
        {chainFor && (
          <OptionChain underlying={chainFor} onClose={() => setChainFor(null)}
            onPick={c => { setChainFor(null); pick(c); }}
            onAdd={owner && gid != null && group ? (c, name) => add.mutate({ s: c, name }) : undefined} />
        )}
      </section>
    </div>
  );
}
