import { useState, useEffect } from "react";
import { authService } from "../services/api/authService";

export default function SecurityBadge() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;

    async function fetchStatus() {
      try {
        const data = await authService.getSecurityStatus();
        if (mounted) setStatus(data);
      } catch {
        // Silently fail — badge is non-critical
      } finally {
        if (mounted) setLoading(false);
      }
    }

    fetchStatus();
    return () => { mounted = false; };
  }, []);

  if (loading || !status) return null;

  const { security_score } = status;
  let color = "bg-red-500";
  let label = "Needs attention";

  if (security_score >= 80) {
    color = "bg-green-500";
    label = "Secure";
  } else if (security_score >= 50) {
    color = "bg-yellow-500";
    label = "Good";
  } else if (security_score >= 30) {
    color = "bg-orange-500";
    label = "Fair";
  }

  return (
    <div className="flex items-center gap-2 rounded-full bg-gray-100 px-3 py-1 text-xs dark:bg-gray-700">
      <div className={`h-2 w-2 rounded-full ${color}`} />
      <span className="font-medium text-gray-600 dark:text-gray-300">
        Security: {security_score}%
      </span>
      <span className="text-gray-400 dark:text-gray-500">({label})</span>
    </div>
  );
}