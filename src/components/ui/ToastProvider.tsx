import { useEffect, useMemo, useState } from "react";

import { ToastContext, type ToastContextValue, type ToastItem, type ToastVariant } from "./toastContext";

const toastStyles: Record<ToastVariant, string> = {
  info: "border-slate-700/80 bg-slate-900/95 text-slate-100",
  success: "border-emerald-500/50 bg-emerald-950/90 text-emerald-50",
  error: "border-rose-500/50 bg-rose-950/90 text-rose-50",
};


export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const push = (toast: Omit<ToastItem, "id">) => {
    const id = Date.now() + Math.floor(Math.random() * 1000);
    setToasts((current) => [...current, { ...toast, id }]);
    window.setTimeout(() => {
      setToasts((current) => current.filter((item) => item.id !== id));
    }, 4200);
  };

  useEffect(() => {
    const originalAlert = window.alert;
    window.alert = (message?: unknown) => {
      push({
        title: "Notification",
        description: String(message ?? ""),
        variant: "info",
      });
    };

    return () => {
      window.alert = originalAlert;
    };
  }, []);

  const value = useMemo<ToastContextValue>(() => ({
    push,
    success: (title, description) => push({ title, description, variant: "success" }),
    error: (title, description) => push({ title, description, variant: "error" }),
    info: (title, description) => push({ title, description, variant: "info" }),
  }), []);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed right-4 top-4 z-[120] flex w-full max-w-sm flex-col gap-3">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`pointer-events-auto rounded-2xl border px-4 py-3 shadow-2xl backdrop-blur-xl ${toastStyles[toast.variant]}`}
          >
            <div className="text-sm font-semibold">{toast.title}</div>
            {toast.description ? (
              <div className="mt-1 text-xs leading-5 opacity-90 whitespace-pre-wrap">{toast.description}</div>
            ) : null}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
