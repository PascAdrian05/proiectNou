import { useToast } from "../context/ToastContext";

export function ToastContainer() {
  const { toasts, dismiss } = useToast();

  if (!toasts.length) {
    return null;
  }

  return (
    <div className="toast-stack" aria-live="polite">
      {toasts.map((toast) => (
        <div key={toast.id} className={`toast toast-${toast.type}`}>
          <span>{toast.message}</span>
          <button type="button" className="toast-close" onClick={() => dismiss(toast.id)} aria-label="Dismiss">
            ×
          </button>
        </div>
      ))}
    </div>
  );
}
