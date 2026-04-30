import { startTransition, useEffect } from "react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";

export function LogoutPage() {
  const navigate = useNavigate();
  const { logout } = useAuth();

  useEffect(() => {
    logout();

    startTransition(() => {
      navigate("/login", { replace: true });
    });
  }, []);
  return null;
}
