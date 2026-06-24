import { createContext, useCallback, useContext, useMemo, useState } from "react";

const ToastContext = createContext(null);

let toastId = 0;

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const dismiss = useCallback((id) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const push = useCallback((message, type = "info", durationMs = 4000) => {
    const id = ++toastId;
    setToasts((prev) => [...prev, { id, message, type }]);

    if (durationMs > 0) {
      window.setTimeout(() => dismiss(id), durationMs);
    }

    return id;
  }, [dismiss]);

  const value = useMemo(
    () => ({
      toasts,
      push,
      dismiss,
      success: (message, durationMs) => push(message, "success", durationMs),
      error: (message, durationMs) => push(message, "error", durationMs),
      info: (message, durationMs) => push(message, "info", durationMs),
    }),
    [toasts, push, dismiss],
  );

  return <ToastContext.Provider value={value}>{children}</ToastContext.Provider>;
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used inside ToastProvider");
  }
  return context;
}
