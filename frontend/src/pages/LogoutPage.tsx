import { startTransition, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";

export function LogoutPage() {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const hasLoggedOut = useRef(false);

  useEffect(() => {
    if (hasLoggedOut.current) {
      return;
    }

    hasLoggedOut.current = true;
    void logout();

    startTransition(() => {
      navigate("/login", { replace: true });
    });
  }, [logout, navigate]);
  return null;
}
