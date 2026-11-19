/* ══ مختبرُ الأبحاث ══ (‏D745 · ‏D759 · ‏D763 بأمر المالك 2026-11-18)
   «التقريرُ اليوميّ خلّه في تبويب مفكرة السوق… وفي مختبر الأبحاث يصبح لدينا عقودُ الخيارات، وأضف تبويباً اسمه المحفظة… وتبويباً ثالثاً
   باسم صقر — وكيلُ تداولٍ آليّ… يبدأ من 100 دولار ويحاول أن يوصلها إلى 10,000». فثلاثةُ تبويبات: توصياتُ العقود طويلة الأجل، ومحفظةُ صقر
   المستقلّة (لا تمسّ محفظةَ المالك)، ولوحةُ صقر نفسُه. والتبويبُ المختار يُحفظ؛ ومن كان على «التقرير» القديم يفتح على عقود الخيارات.
   ‏D769 (المالك 2026-11-19): «خلّنا نوحّد كلَّ تفاصيل صقر — المحفظةُ داخل صقر بجانب لوحة المعلومات والسجل»: فتبويبان، والمحفظةُ تبويبٌ في صقر،
   ومن كان على «المحفظة» يفتح صقرَ على محفظته. */
import { useState } from "react";
import OptionPicks from "../components/market/OptionPicks";
import SaqrDesk from "../components/saqr/SaqrDesk";

type View = "options" | "saqr";
const VIEWS: readonly (readonly [View, string])[] = [["options", "عقود الخيارات"], ["saqr", "صقر"]] as const;
const readView = (): View => {
  try {
    const v = localStorage.getItem("sp_lab_view");
    if (v === "portfolio") { localStorage.setItem("sp_saqr_tab", "portfolio"); localStorage.setItem("sp_lab_view", "saqr"); return "saqr"; }
    return v === "saqr" ? v : "options";
  } catch { return "options"; }
};

export default function ResearchLab() {
  const [view, setView] = useState<View>(readView);
  const pick = (v: View) => { setView(v); try { localStorage.setItem("sp_lab_view", v); } catch { /* */ } };
  return (
    <div className="space-y-3" data-role="research-lab">
      <div className="seg inline-flex rl-views" role="tablist" aria-label="مختبر الأبحاث" data-role="rl-views">
        {VIEWS.map(([k, t]) => (
          <button key={k} type="button" role="tab" aria-selected={view === k} className={"seg-btn chip" + (view === k ? " on" : "")}
            onClick={() => pick(k)} data-view={k}>{t}</button>
        ))}
      </div>
      <div key={view} className="rl-pane">
        {view === "options" ? <OptionPicks /> : <SaqrDesk />}
      </div>
    </div>
  );
}
