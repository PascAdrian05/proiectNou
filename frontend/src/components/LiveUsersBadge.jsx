import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { presenceService } from "../services/api/presenceService";

export function LiveUsersBadge() {
  const { isAuthenticated } = useAuth();
  const [onlineUsers, setOnlineUsers] = useState(0);

  useEffect(() => {
    if (!isAuthenticated) {
      setOnlineUsers(0);
      return undefined;
    }

    let isMounted = true;

    async function loadOnlineUsers() {
      try {
        const data = await presenceService.online();
        if (isMounted) {
          setOnlineUsers(Number(data?.online_users || 0));
        }
      } catch {
        if (isMounted) {
          setOnlineUsers(0);
        }
      }
    }

    loadOnlineUsers();
    const intervalId = window.setInterval(loadOnlineUsers, 10000);

    return () => {
      isMounted = false;
      window.clearInterval(intervalId);
    };
  }, [isAuthenticated]);

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="live-badge" title="Users currently active in this tenant">
      <span className="live-badge-dot" />
      <span>{onlineUsers} online</span>
    </div>
  );
}