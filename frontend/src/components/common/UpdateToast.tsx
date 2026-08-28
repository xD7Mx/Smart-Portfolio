import { useEffect, useState } from "react";
import { RefreshCw, X } from "lucide-react";
import { UPDATE_EVENT } from "../../registerSW";

/**
 * إشعار «نسخة جديدة متاحة» — لا يُطبَّق التحديث إلا بموافقتك، فلا تُعاد
 * الصفحة وأنت في منتصف إدخال صفقة. يظهر أسفل الشاشة ويحترم المظهرين.
 */
export default function UpdateToast() {
  const [reg, setReg] = useState<ServiceWorkerRegistration | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const on = (e: Event) => setReg((e as CustomEvent).detail as ServiceWorkerRegistration);
    window.addEventListener(UPDATE_EVENT, on);
    return () => window.removeEventListener(UPDATE_EVENT, on);
  }, []);

  if (!reg) return null;

  const apply = () => {
    setBusy(true);
    // الـSW يستمع لهذه الرسالة ويُفعّل نفسه، ثم controllerchange يُعيد التحميل.
    (reg.waiting || reg.installing)?.postMessage("SKIP_WAITING");
    setTimeout(() => window.location.reload(), 1500);   // شبكة أمان
  };

  return (
    <div className="fixed z-[60] bottom-20 sm:bottom-5 start-5 end-5 sm:end-auto sm:w-[340px]">
      <div className="update-toast rounded-2xl shadow-2xl p-3.5 flex items-center gap-3 fade-in">
        <RefreshCw size={18} className={"text-[var(--brand-ink)] shrink-0 " + (busy ? "animate-spin" : "")} />
        <div className="flex-1 min-w-0">
          <p className="text-[13px] font-bold update-toast-title">نسخة جديدة جاهزة</p>
          <p className="text-[11px] text-[var(--ink-muted)]">اضغط للتحديث — لن تفقد أي بيانات.</p>
        </div>
        <button onClick={apply} disabled={busy} className="btn-primary !py-1.5 !px-3 !text-xs shrink-0">
          {busy ? "…" : "تحديث"}
        </button>
        <button onClick={() => setReg(null)} className="chat-tool p-1 rounded-lg shrink-0" title="لاحقاً">
          <X size={15} />
        </button>
      </div>
    </div>
  );
}
