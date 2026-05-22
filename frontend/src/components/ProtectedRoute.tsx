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
        <Card className="w-full max-w-lg rounded-lg border border-zinc-200 bg-white">
          <Card.Content className="space-y-3 p-8 text-center">
            <h1 className="text-2xl font-semibold text-zinc-950">
              Checking access
            </h1>
            <p className="text-sm text-zinc-600">Loading...</p>
          </Card.Content>
        </Card>
      </section>
    );
  }

  if (error) {
    return (
      <section className="flex min-h-screen items-center justify-center px-4 py-8 sm:px-6 lg:px-8">
        <Card className="w-full max-w-lg rounded-lg border border-rose-200 bg-white">
          <Card.Content className="space-y-4 p-8 text-center">
            <h1 className="text-2xl font-semibold text-zinc-950">
              Authentication unavailable
            </h1>
            <p className="text-sm text-rose-700">{error.message}</p>
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
