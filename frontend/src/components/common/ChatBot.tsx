import React, { useEffect, useLayoutEffect, useRef, useState } from "react";
import { MessageCircle, X, Send, Loader2, Sparkles, RotateCcw, Copy, Check } from "lucide-react";
import { aiApi } from "../../services/api";

/**
 * مساعد المحفظة — لوحة دردشة كاملة السلوك.
 *
 * معالجات جوهرية:
 *  • **الكيبورد**: نستخدم visualViewport لقياس الارتفاع المرئي فعلياً، فترتفع
 *    اللوحة مع الكيبورد وتنزل معه بلا قفزات. وحجم خط الإدخال 16px لأن iOS
 *    يُكبّر الصفحة قسراً لأي حقل أصغر من ذلك (سبب «الزوم القوي»).
 *  • **أدوات**: نسخ الإجابة · محادثة جديدة · حذف المحادثة.
 *  • **المظهرين**: ألوان عبر متغيّرات التطبيق + أصناف مخصّصة تُقلب في الفاتح.
 */

type Msg = { role: "user" | "assistant"; content: string };

const STORE_KEY = "sp:chat";
const SUGGESTIONS = [
  "ما أداء محفظتي؟",
  "كم صافي ربحي وعائد محفظتي؟",
  "أفضل وأضعف مراكزي؟",
  "ما وضع السوق اليوم؟",
  "أقرب الأحداث المهمة لشركاتي؟",
];

/** تنظيف نصّ الإجابة: يُزيل النجوم المكرّرة وكتل الأكواد — لا نعرض شيفرة. */
function cleanReply(t: string): string {
  let s = t || "";
  s = s.replace(/```[\s\S]*?```/g, "");          // كتل شيفرة
  s = s.replace(/`([^`]*)`/g, "$1");             // شيفرة سطرية
  s = s.replace(/\*\*(.*?)\*\*/g, "$1");         // **عريض**
  s = s.replace(/(^|\s)\*(?!\s)(.*?)\*(?=\s|$)/g, "$1$2"); // *مائل*
  s = s.replace(/^[ \t]*[*+][ \t]+/gm, "• ");    // نقاط بالنجمة → •
  s = s.replace(/^#{1,6}[ \t]*/gm, "");          // عناوين ماركداون
  s = s.replace(/\n{3,}/g, "\n\n");
  return s.trim();
}

export default function ChatBot() {
  const [open, setOpen] = useState(false);
  const [msgs, setMsgs] = useState<Msg[]>(() => {
    try { return JSON.parse(sessionStorage.getItem(STORE_KEY) || "[]"); } catch { return []; }
  });
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState<number | null>(null);
  const [spin, setSpin] = useState(false);
  const [vh, setVh] = useState<number | null>(null);   // ارتفاع المنطقة المرئية
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  /* ── الكيبورد: نتتبّع visualViewport فترتفع اللوحة معه بدقّة ── */
  useLayoutEffect(() => {
    if (!open) return;
    const vv = (window as any).visualViewport;
    if (!vv) return;
    const onResize = () => setVh(vv.height);
    onResize();
    vv.addEventListener("resize", onResize);
    vv.addEventListener("scroll", onResize);
    return () => { vv.removeEventListener("resize", onResize); vv.removeEventListener("scroll", onResize); };
  }, [open]);

  useEffect(() => {
    try { sessionStorage.setItem(STORE_KEY, JSON.stringify(msgs.slice(-40))); } catch { /* ممتلئ */ }
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [msgs, open, vh]);

  // قفل تمرير الصفحة خلف اللوحة (يمنع «سحب الصفحة» أثناء الدردشة)
  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = prev; };
  }, [open]);

  const send = async (q?: string) => {
    const question = (q ?? text).trim();
    if (!question || busy) return;
    setText("");
    const next: Msg[] = [...msgs, { role: "user", content: question }];
    setMsgs(next);
    setBusy(true);
    try {
      const r = await aiApi.chat(question, next.slice(-8));
      const reply = cleanReply(r.data?.data?.reply || "") || "تعذّر توليد الإجابة.";
      setMsgs([...next, { role: "assistant", content: reply }]);
    } catch {
      setMsgs([...next, { role: "assistant", content: "تعذّر الاتصال بالخادم." }]);
    } finally {
      setBusy(false);
      inputRef.current?.focus();
    }
  };

  const clearChat = () => {
    setMsgs([]);
    try { sessionStorage.removeItem(STORE_KEY); } catch { /* لا شيء */ }
  };

  const copyMsg = async (i: number, content: string) => {
    try { await navigator.clipboard.writeText(content); setCopied(i); setTimeout(() => setCopied(null), 1500); }
    catch { /* غير مدعوم */ }
  };

  // ارتفاع اللوحة: يتبع المنطقة المرئية على الجوال (مع الكيبورد)، وثابت على الكمبيوتر.
  const panelStyle: React.CSSProperties = vh
    ? { height: Math.min(vh - 8, 620), maxHeight: "100%" }
    : { height: "min(78vh, 600px)" };

  return (
    <>
      {!open && (
        <button onClick={() => setOpen(true)} aria-label="صقر — مساعدك الاستثماري"
          className="chat-fab fixed z-40 bottom-5 end-5 rounded-full flex items-center justify-center shadow-xl active:scale-95 transition-transform"
          style={{ width: 52, height: 52 }}>
          <MessageCircle size={22} />
        </button>
      )}

      {open && (
        <div className="fixed z-50 inset-x-0 bottom-0 sm:inset-x-auto sm:end-5 sm:bottom-5 sm:w-[400px]"
          style={vh ? { top: 0, display: "flex", alignItems: "flex-end" } : undefined}>
          <div className="chat-panel w-full rounded-t-3xl sm:rounded-3xl overflow-hidden shadow-2xl flex flex-col"
            style={panelStyle}>
            {/* الرأس + الأدوات */}
            <div className="flex items-center gap-2 px-3.5 py-3 shrink-0" style={{ borderBottom: "1px solid var(--hairline)" }}>
              <Sparkles size={16} className="shrink-0 ai-star" />
              <span className="text-sm font-bold chat-title">صقر</span>
              <span className="text-[10px]" style={{ color: "var(--ink-muted)" }}>مساعدك الاستثماري</span>
              <div className="ms-auto flex items-center gap-0.5">
                {/* زرّان لا ثلاثة: «محادثة جديدة» و«إغلاق». زرّ السلة كان
                    يستدعي نفس الدالة تماماً — تكرارٌ بلا معنى. */}
                {/* يبقى الزرّ مركَّباً أثناء الدوران: مسح المحادثة يُخفيه
                    (شرطه msgs.length) فتختفي الدورة قبل أن تُرى. */}
                {(msgs.length > 0 || spin) && (
                  /* الزرّ كان جامداً: المحادثة تُمسح فوراً بلا أثرٍ مرئي،
                     فيبدو كأن الضغطة لم تصل. دورةٌ قصيرة تؤكّد الفعل. */
                  <button onClick={() => { setSpin(true); setTimeout(() => { clearChat(); setSpin(false); }, 480); }}
                    title="محادثة جديدة" className="chat-tool p-1.5 rounded-lg">
                    <RotateCcw size={15} className={spin ? "animate-spin" : undefined} />
                  </button>
                )}
                <button onClick={() => setOpen(false)} title="إغلاق"
                  className="chat-tool p-1.5 rounded-lg"><X size={17} /></button>
              </div>
            </div>

            {/* الرسائل */}
            <div className="flex-1 overflow-y-auto overscroll-contain px-3 py-3 space-y-2.5">
              {msgs.length === 0 && (
                <div className="py-4">
                  {/* هويّةٌ باسم، وتحيّةٌ في سطرٍ واحد. الاسم يُقال مرّةً عند
                      بداية المحادثة لا في كل إجابة، فلا يصير تكراراً مملّاً. */}
                  <p className="text-[15px] font-bold mb-1" style={{ color: "var(--ink)" }}>أهلاً، أنا صقر</p>
                  <p className="text-[12.5px] mb-4" style={{ color: "var(--ink-muted)" }}>كيف أخدمك؟</p>
                  {/* الاقتراحات تُحاذي النصّ وتأخذ عرضه فقط. كانت أزراراً
                      ممتدّة بعرض اللوح، فيظهر أمام كل سؤال خطٌّ باهت طويل لا
                      معنى له — لغة التطبيق هنا وسمٌ يحتضن نصّه لا شريط. */}
                  <div className="flex flex-col items-start gap-2">
                    {SUGGESTIONS.map(s => (
                      <button key={s} onClick={() => send(s)} className="chat-sugg text-[12.5px] rounded-full px-3.5 py-2 text-start active:scale-[.99] transition-transform">
                        {s}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {msgs.map((m, i) => (
                <div key={i} className={"flex group " + (m.role === "user" ? "justify-start" : "justify-end")}>
                  <div className={"max-w-[88%] rounded-2xl px-3 py-2 text-[13.5px] leading-relaxed whitespace-pre-wrap "
                      + (m.role === "user" ? "chat-bubble-user" : "chat-bubble-ai")}>
                    {m.content}
                    {m.role === "assistant" && (
                      <button onClick={() => copyMsg(i, m.content)} title="نسخ"
                        className="chat-tool mt-1.5 flex items-center gap-1 text-[11px]">
                        {copied === i ? <><Check size={11} /> نُسخ</> : <><Copy size={11} /> نسخ</>}
                      </button>
                    )}
                  </div>
                </div>
              ))}
              {busy && (
                <div className="flex justify-end">
                  <div className="chat-bubble-ai rounded-2xl px-3 py-2 flex items-center gap-2 text-[12px]">
                    <Loader2 size={13} className="animate-spin" /> يقرأ بياناتك…
                  </div>
                </div>
              )}
              <div ref={endRef} />
            </div>

            {/* الإدخال — 16px يمنع تكبير iOS القسري */}
            <div className="p-2.5 shrink-0 flex items-center gap-2" style={{ borderTop: "1px solid var(--hairline)" }}>
              <input ref={inputRef} value={text} onChange={e => setText(e.target.value)}
                onKeyDown={e => e.key === "Enter" && send()}
                placeholder="اكتب سؤالك…" enterKeyHint="send" maxLength={1000}
                className="chat-input flex-1 rounded-xl px-3 py-2.5 focus:outline-none"
                style={{ fontSize: 16 }} />
              <button onClick={() => send()} disabled={busy || !text.trim()}
                className="chat-send rounded-xl p-2.5 disabled:opacity-40 active:scale-95 transition-transform">
                <Send size={16} />
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
