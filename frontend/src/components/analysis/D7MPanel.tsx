import { D7M_COLORS, D7M_DEFAULTS, FIB_LEVELS, type D7MSettings } from "./d7m";
import Select from "../common/Select";
import Toggle from "../common/Toggle";
import CheckBox from "../common/CheckBox";

/** لونُ الرمز الحاليّ بصيغة #rrggbb ليظهر في منتقي اللون. */
function tokenHex(name: string): string {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  if (/^#[0-9a-f]{6}$/i.test(v)) return v;
  if (/^#[0-9a-f]{3}$/i.test(v)) return "#" + v.slice(1).split("").map(c => c + c).join("");
  const m = v.match(/\d+(\.\d+)?/g);
  if (m && m.length >= 3) return "#" + m.slice(0, 3).map(n => Math.round(+n).toString(16).padStart(2, "0")).join("");
  return "#000000";
}

type K = keyof D7MSettings;
type Props = { cfg: D7MSettings; onChange: (c: D7MSettings) => void; onClose: () => void };

/** إعداداتُ مؤشّر D7M — كلُّ مدخلٍ في السكربت له مفتاحٌ هنا. */
export default function D7MPanel({ cfg, onChange, onClose }: Props) {
  const set = (k: K, v: unknown) => onChange({ ...cfg, [k]: v } as D7MSettings);
  /* ‏D678: مفتاحُ التطبيق الواحد بدل صندوق اختيار النظام */
  const Check = ({ k, label }: { k: K; label: string }) => (
    <div className="d7m-row"><Toggle checked={!!cfg[k]} onChange={v => set(k, v)} label={label} /></div>
  );
  const Num = ({ k, label, step = 1 }: { k: K; label: string; step?: number }) => (
    <label className="d7m-row">
      <span>{label}</span>
      <input type="number" step={step} value={Number(cfg[k])} dir="ltr"
        onChange={e => { const n = Number(e.target.value); if (Number.isFinite(n)) set(k, n); }} />
    </label>
  );
  return (
    <div className="d7m-modal" role="dialog" aria-label="إعدادات D7M" onClick={onClose}>
      <div className="d7m-sheet" onClick={e => e.stopPropagation()}>
        <div className="d7m-head">
          <strong>إعدادات D7M</strong>
          <button type="button" className="d7m-btn" onClick={() => onChange({ ...D7M_DEFAULTS })}>الافتراضي</button>
          <button type="button" className="d7m-btn" onClick={onClose} aria-label="إغلاق">✕</button>
        </div>

        <fieldset><legend>الألوان</legend>
          <div className="d7m-colors">
            {D7M_COLORS.map(([k, label, token]) => (
              <label key={k} className="d7m-row">
                <span>{label}</span>
                <span className="flex items-center gap-1">
                  <input type="color" aria-label={`لون ${label}`} value={cfg.colors[k] || tokenHex(token)}
                    onChange={e => set("colors", { ...cfg.colors, [k]: e.target.value })} />
                  {cfg.colors[k] && (
                    <button type="button" className="d7m-reset" title="لونُ المظهر" aria-label={`إرجاع لون ${label}`}
                      onClick={() => { const c = { ...cfg.colors }; delete c[k]; set("colors", c); }}>↺</button>
                  )}
                </span>
              </label>
            ))}
          </div>
        </fieldset>

        <fieldset><legend>فيبوناتشي تلقائي</legend>
          <Check k="fib" label="إظهار" />
          <Num k="fibDev" label="مضاعف الانحراف" step={0.5} />
          <Num k="fibDepth" label="العمق" />
          <Check k="fibReverse" label="عكس الاتجاه" />
          <Check k="fibZones" label="تظليلُ المناطق الثلاث" />
          <div className="d7m-row d7m-col" data-role="fib-mode">
            <span>المستويات</span>
            <span className="seg inline-flex">
              {([["compact", "مختصر"], ["all", "الكل"]] as const).map(([v, t]) => (
                <button key={v} type="button" className={"seg-btn chip" + ((cfg.fibMode || "compact") === v ? " on" : "")} aria-pressed={(cfg.fibMode || "compact") === v}
                  onClick={() => set("fibMode", v)}>{t}</button>
              ))}
            </span>
          </div>
          <div className="d7m-row d7m-col" data-role="fib-label-pos">
            <span>موضعُ أرقام المستويات</span>
            <span className="seg inline-flex">
              {([["above", "فوق الخطّ"], ["on", "على الخطّ"], ["below", "تحت الخطّ"]] as const).map(([v, t]) => (
                <button key={v} type="button" className={"seg-btn chip" + ((cfg.fibLabelPos || "on") === v ? " on" : "")} aria-pressed={(cfg.fibLabelPos || "on") === v}
                  onClick={() => set("fibLabelPos", v)} data-pos={v}>{t}</button>
              ))}
            </span>
          </div>
          <div className="d7m-levels">
            {FIB_LEVELS.map(([lv]) => (
              <div key={lv} className="d7m-row">
                <CheckBox checked={cfg.fibLevels[String(lv)] !== false}
                  onChange={v => set("fibLevels", { ...cfg.fibLevels, [String(lv)]: v })}
                  label={<span className="tabular-nums">{lv}</span>} />
              </div>
            ))}
          </div>
        </fieldset>

        <fieldset><legend>الاتجاه التلقائي</legend>
          <Check k="trend" label="إظهار" />
          <Check k="trendMajor" label="الاتجاه الرئيسي" />
          <Check k="trendMinor" label="الاتجاه الفرعي" />
          <Num k="trendPP" label="فترة المحور" />
          <Check k="trendShapes" label="علامات الاختراق" />
        </fieldset>

        <fieldset><legend>القناة التلقائية</legend>
          <Check k="channel" label="إظهار" />
          <Check k="chMid" label="خطُّ المنتصف" />
          <Num k="chDev" label="مضاعف الانحراف" step={0.5} />
          <Num k="chDepth" label="العمق" />
        </fieldset>

        <fieldset><legend>VWAP</legend>
          <Check k="vwap" label="إظهار" />
          <label className="d7m-row"><span>المرساة</span>
            <Select value={cfg.vwapAnchor} onChange={e => set("vwapAnchor", e.target.value)}>
              <option value="Session">جلسة</option><option value="Week">أسبوع</option>
              <option value="Month">شهر</option><option value="Year">سنة</option>
            </Select>
          </label>
          <Check k="vwapBand" label="النطاقات" />
          <Num k="vwapMult" label="مضاعف النطاق" step={0.5} />
        </fieldset>

        <fieldset><legend>المتوسطات الأُسّية</legend>
          <Check k="ema20" label="EMA 20" /><Check k="ema50" label="EMA 50" />
          <Check k="ema100" label="EMA 100" /><Check k="ema200" label="EMA 200" />
          <Check k="ema400" label="EMA 400" />
        </fieldset>

        <fieldset><legend>مستويات اليوم السابق</legend>
          <Check k="pdh" label="أعلى أمس" /><Check k="pdl" label="أدنى أمس" />
          <Check k="pdc" label="إغلاق أمس" /><Check k="dOpen" label="افتتاح اليوم" />
        </fieldset>

        {/* ‏D782 (المالك): «لوحتان: قوّةُ الاتجاه وقوّةُ السيولة — ولوحةُ الأطر نستغني عنها» — فلا مكانَ ولا حدودَ ولا محلّلَ ولا تنبيهاتٍ ولا أداةَ صفقة */}
        <fieldset><legend>اللوحات</legend>
          <div data-role="d7m-panels-toggle"><Check k="dashboard" label="لوحتا قوّة الاتجاه والسيولة" /></div>
        </fieldset>

      </div>
    </div>
  );
}
