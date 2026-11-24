import { D7M_COLORS, D7M_DEFAULTS, FIB_LEVELS, type D7MSettings } from "./d7m";
import Select from "../common/Select";
import Toggle from "../common/Toggle";
import CheckBox from "../common/CheckBox";
import ColorPick, { tokenHex, useBackdropClose } from "../common/ColorPick";

type K = keyof D7MSettings;
type Props = { cfg: D7MSettings; onChange: (c: D7MSettings) => void; onClose: () => void; colorDefaults?: Record<string, string> };
type Ctx = { cfg: D7MSettings; set: (k: K, v: unknown) => void; colorDefaults?: Record<string, string> };

/* ‏D798 (المالك 2026-11-24): «لمّا أغيّر لونَ الترند الصاعد والهابط — الألوانُ إذا ضغطتُ على الشاشة بسرعة تُغلق». قِيس السبب: كانت عناصرُ
   الصفّ (‏Check · Num · Color) معرَّفةً **داخل** دالّة النافذة، فكلُّ تغييرٍ يعيد رسمَها نوعاً جديداً — فيهدم React حقلَ اللون ويبنيه، فيُغلق
   منتقي الألوان الأصيلُ على الجوال عند أوّل حركةٍ فيه، ويفقد حقلُ الرقم مؤشّرَه بعد كلّ حرف. فصارت عناصرَ ثابتةً خارجها، واللونُ من لوحة
   ألوانٍ كتريدنق فيو (‏ColorPick)، ونقرُ الخلفية لا يُغلق النافذةَ إلا إن بدأ عليها وانتهى عليها. */
function Check({ c, k, label }: { c: Ctx; k: K; label: string }) {
  return <div className="d7m-row"><Toggle checked={!!c.cfg[k]} onChange={v => c.set(k, v)} label={label} /></div>;
}
function Num({ c, k, label, step = 1 }: { c: Ctx; k: K; label: string; step?: number }) {
  return (
    <label className="d7m-row">
      <span>{label}</span>
      <input type="number" step={step} value={Number(c.cfg[k])} dir="ltr"
        onChange={e => { const n = Number(e.target.value); if (Number.isFinite(n)) c.set(k, n); }} />
    </label>
  );
}
function Color({ c, k, name }: { c: Ctx; k: string; name: string }) {
  const fb = c.colorDefaults?.[k] || tokenHex((D7M_COLORS.find(x => x[0] === k) || ["", "", "--ink-muted"])[2]);
  return (
    <div className="d7m-row" data-color={k}>
      <span>{name}</span>
      <ColorPick label={name} value={c.cfg.colors[k] || ""} fallback={fb}
        onChange={v => { const cs = { ...c.cfg.colors }; if (v) cs[k] = v; else delete cs[k]; c.set("colors", cs); }} />
    </div>
  );
}

/** إعداداتُ مؤشّر D7M — كلُّ مدخلٍ في السكربت له مفتاحٌ هنا.
 *  ‏D783 (المالك 2026-11-21): «الترندُ لم أجده في إعدادات الدحم في الألوان — ضاع»: كانت الألوانُ قسماً عامّاً في الأعلى، ولونُ الترند فيه باسم
 *  «اتجاه صاعد/هابط»، والمنتقي يعرض لونَ رمزٍ غيرِ المرسوم فعلاً. فصار لكلّ عنصرٍ لونُه داخل قسمه كتريدنق فيو (الترندُ بلونيه في قسم الترند)،
 *  والمنتقي يعرض اللونَ المرسومَ نفسَه (‏colorDefaults من الرسم). */
export default function D7MPanel({ cfg, onChange, onClose, colorDefaults }: Props) {
  const set = (k: K, v: unknown) => onChange({ ...cfg, [k]: v } as D7MSettings);
  const c: Ctx = { cfg, set, colorDefaults };
  const bd = useBackdropClose(onClose);
  return (
    <div className="d7m-modal" role="dialog" aria-label="إعدادات D7M" {...bd} data-role="d7m-settings">
      <div className="d7m-sheet" onClick={e => e.stopPropagation()}>
        <div className="d7m-head">
          <strong>إعدادات D7M</strong>
          <button type="button" className="d7m-btn" onClick={() => onChange({ ...D7M_DEFAULTS })}>الافتراضي</button>
          <button type="button" className="d7m-btn" onClick={onClose} aria-label="إغلاق">✕</button>
        </div>

        <fieldset><legend>فيبوناتشي تلقائي</legend>
          <Check c={c} k="fib" label="إظهار" />
          <Num c={c} k="fibDev" label="مضاعف الانحراف" step={0.5} />
          <Num c={c} k="fibDepth" label="العمق" />
          <Check c={c} k="fibReverse" label="عكس الاتجاه" />
          <Check c={c} k="fibZones" label="تظليلُ المناطق الثلاث" />
          <Color c={c} k="fib" name="لونُ المستويات" />
          <Color c={c} k="fibGold" name="لونُ المستويات الذهبية" />
          <div className="d7m-row d7m-col" data-role="fib-mode">
            <span>المستويات</span>
            <span className="seg inline-flex">
              {([["compact", "مختصر"], ["all", "الكل"]] as const).map(([v, t]) => (
                <button key={v} type="button" className={"seg-btn chip" + ((cfg.fibMode || "compact") === v ? " on" : "")} aria-pressed={(cfg.fibMode || "compact") === v}
                  onClick={() => set("fibMode", v)}>{t}</button>
              ))}
            </span>
          </div>
          {/* ‏D799 (المالك 2026-11-24): «مستوياتُ الفيبوناتشي ليست ثابتةً أمام الشموع — تلحقني إذا لففتُ الشارت إلى اليسار… خلّها ثابتة، أو خيار:
              ثابتة أو متحرّكة» — «ثابتة» تبدأ من قاع الموجة أو قمّتها وتقف عندها، و«متحرّكة» على عرض الشاشة كما كانت */}
          <div className="d7m-row d7m-col" data-role="fib-anchor">
            <span>المستوياتُ عند تحريك الرسم</span>
            <span className="seg inline-flex">
              {([["fixed", "ثابتةٌ على الشموع"], ["moving", "تتبع الشاشة"]] as const).map(([v, t]) => (
                <button key={v} type="button" className={"seg-btn chip" + ((cfg.fibAnchor || "fixed") === v ? " on" : "")} aria-pressed={(cfg.fibAnchor || "fixed") === v}
                  onClick={() => set("fibAnchor", v)} data-anchor={v}>{t}</button>
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
                  label={<span className="tabular-nums" dir="ltr">{lv}</span>} />
              </div>
            ))}
          </div>
        </fieldset>

        <fieldset data-role="d7m-trend"><legend>الترند — خطوطُ الاتجاه التلقائية</legend>
          <Check c={c} k="trend" label="إظهار" />
          <Check c={c} k="trendMajor" label="الترندُ الرئيسي" />
          <Check c={c} k="trendMinor" label="الترندُ الفرعي" />
          <Num c={c} k="trendPP" label="فترة المحور" />
          <Check c={c} k="trendShapes" label="علامات الاختراق" />
          <Color c={c} k="trendUp" name="لونُ الترند الصاعد" />
          <Color c={c} k="trendDown" name="لونُ الترند الهابط" />
        </fieldset>

        <fieldset><legend>القناة التلقائية</legend>
          <Check c={c} k="channel" label="إظهار" />
          <Check c={c} k="chMid" label="خطُّ المنتصف" />
          <Num c={c} k="chDev" label="مضاعف الانحراف" step={0.5} />
          <Num c={c} k="chDepth" label="العمق" />
          <Color c={c} k="channel" name="لونُ القناة" />
        </fieldset>

        <fieldset><legend>VWAP</legend>
          <Check c={c} k="vwap" label="إظهار" />
          <label className="d7m-row"><span>المرساة</span>
            <Select value={cfg.vwapAnchor} onChange={e => set("vwapAnchor", e.target.value)}>
              <option value="Session">جلسة</option><option value="Week">أسبوع</option>
              <option value="Month">شهر</option><option value="Year">سنة</option>
            </Select>
          </label>
          <Check c={c} k="vwapBand" label="النطاقات" />
          <Num c={c} k="vwapMult" label="مضاعف النطاق" step={0.5} />
          <Color c={c} k="vwap" name="لونُ VWAP" />
          <Color c={c} k="band" name="لونُ النطاقات" />
        </fieldset>

        <fieldset><legend>المتوسطات الأُسّية</legend>
          {(["ema20", "ema50", "ema100", "ema200", "ema400"] as const).map(k => (
            <div key={k} className="d7m-ema">
              <Check c={c} k={k} label={`EMA ${k.slice(3)}`} />
              <Color c={c} k={k} name={`لونُ EMA ${k.slice(3)}`} />
            </div>
          ))}
        </fieldset>

        <fieldset><legend>الرسمُ اليدويّ</legend>
          <Color c={c} k="draw" name="لونُ الرسم اليدويّ" />
        </fieldset>

        <fieldset><legend>مستويات اليوم السابق</legend>
          <Check c={c} k="pdh" label="أعلى أمس" /><Check c={c} k="pdl" label="أدنى أمس" />
          <Check c={c} k="pdc" label="إغلاق أمس" /><Check c={c} k="dOpen" label="افتتاح اليوم" />
        </fieldset>

        {/* ‏D782 (المالك): «لوحتان: قوّةُ الاتجاه وقوّةُ السيولة — ولوحةُ الأطر نستغني عنها» — فلا مكانَ ولا حدودَ ولا محلّلَ ولا تنبيهاتٍ ولا أداةَ صفقة */}
        <fieldset><legend>اللوحات</legend>
          <div data-role="d7m-panels-toggle"><Check c={c} k="dashboard" label="لوحتا قوّة الاتجاه والسيولة" /></div>
        </fieldset>

      </div>
    </div>
  );
}
