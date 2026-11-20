/* ══ مختبرُ الأبحاث ══ (‏D745 · ‏D759 · ‏D763 · ‏D769 · ‏D777 بأمر المالك)
   ‏D777 (المالك 2026-11-20): «ما نلخبط أنفسنا بين عقود الخيارات وبين صقر — كلاهما مهمّتُه وهدفُه واحد: أفضلُ العقود ونسبةُ نجاحٍ عالية…
   ألغِ التبويبين فوق، وخلِّ عقود الخيارات داخل صقر، فيكون التبويبُ السوقَ الأمريكيّ والسوقَ السعوديّ فقط، ويأخذ التصميمُ حيّزاً أكبر».
   فالمختبرُ صقرٌ وحده (ومبدّلُ سوقيه في رأسه)، و«عقود الخيارات» تبويبٌ داخله للسوق الأمريكيّ. ومن حفظ «عقود الخيارات» أو «المحفظة» قديماً
   يفتح صقرَ على التبويب نفسِه. */
import SaqrDesk from "../components/saqr/SaqrDesk";

/** يُرحَّل اختيارُ المختبر القديم إلى تبويب صقر مرّةً — ثمّ يُمحى (‏D777). */
function migrate(): void {
  try {
    const v = localStorage.getItem("sp_lab_view");
    if (v === null) return;
    if (v === "portfolio") localStorage.setItem("sp_saqr_tab", "portfolio");
    else if (v !== "saqr") { localStorage.setItem("sp_saqr_tab", "options"); localStorage.setItem("sp_saqr_market", "us"); }
    localStorage.removeItem("sp_lab_view");
  } catch { /* */ }
}

export default function ResearchLab() {
  migrate();
  return (
    <div className="space-y-3" data-role="research-lab">
      <div className="rl-pane"><SaqrDesk /></div>
    </div>
  );
}
