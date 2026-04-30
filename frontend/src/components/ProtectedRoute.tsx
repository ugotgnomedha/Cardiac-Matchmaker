import { Button, Card } from "@heroui/react";
import { Navigate, Outlet, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";

export function ProtectedRoute() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, isLoading, error } = useAuth();

  if (isLoading) {
    return (
      <section className="flex min-h-screen items-center justify-center px-4 py-8 sm:px-6 lg:px-8">
        <Card className="w-full max-w-lg rounded-[2rem] border border-white/70 bg-white/85 shadow-[0_24px_90px_-40px_rgba(120,53,15,0.55)] backdrop-blur-xl">
          <Card.Content className="space-y-4 p-8 text-center sm:p-10">
            <span className="text-xs font-semibold uppercase tracking-[0.32em] text-amber-700">
              Session Check
            </span>
            <h1 className="text-3xl font-semibold text-stone-900 sm:text-4xl">
              Checking your access.
            </h1>
            <p className="text-sm text-stone-600 sm:text-base">
              Reading current cookie-backed session before rendering protected
              pages.
            </p>
          </Card.Content>
        </Card>
      </section>
    );
  }

  if (error) {
    return (
      <section className="flex min-h-screen items-center justify-center px-4 py-8 sm:px-6 lg:px-8">
        <Card className="w-full max-w-lg rounded-[2rem] border border-white/70 bg-white/90 shadow-[0_24px_90px_-40px_rgba(120,53,15,0.55)] backdrop-blur-xl">
          <Card.Content className="space-y-5 p-8 text-center sm:p-10">
            <span className="text-xs font-semibold uppercase tracking-[0.32em] text-rose-700">
              Auth Error
            </span>
            <h1 className="text-3xl font-semibold text-stone-900 sm:text-4xl">
              Authentication service unavailable.
            </h1>
            <p className="text-sm text-stone-600 sm:text-base">
              {error.message}
            </p>
            <Button onPress={() => navigate("/login", { replace: true })}>
              Go to login
            </Button>
          </Card.Content>
        </Card>
      </section>
    );
  }

  if (!user) {
    const returnTo = `${location.pathname}${location.search}${location.hash}`;

    return <Navigate to="/login" replace state={{ from: returnTo }} />;
  }

  return <Outlet context={user} />;
}
