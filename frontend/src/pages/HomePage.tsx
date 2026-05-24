import { Card } from "@heroui/react";
import { useOutletContext } from "react-router-dom";

import { AppLayout } from "../components/AppLayout";
import type { AuthUser } from "../hooks/useAuth";

function formatDateLabel(value: string) {
  return new Date(value).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function HomePage() {
  const user = useOutletContext<AuthUser>();

  return (
    <AppLayout breadcrumbs={[{ label: "Account" }]} title="Session Snapshot">
      <section className="grid gap-6">
        <div className="rounded-lg border border-zinc-200 p-5">
          <div className="flex flex-wrap gap-3 text-sm">
            <span className="rounded-full px-4 py-2">{user.email}</span>
            <span className="rounded-full px-4 py-2">
              {user.is_superuser ? "Superuser access" : "Standard access"}
            </span>
            <span className="rounded-full px-4 py-2 text-emerald-800">
              {user.is_active ? "Active account" : "Inactive account"}
            </span>
          </div>
        </div>

        <Card className="rounded-lg border border-zinc-200 bg-white">
          <Card.Header className="space-y-2 px-6 pt-6 pb-0">
            <h2 className="text-lg font-semibold text-zinc-950">
              Current User
            </h2>
          </Card.Header>
          <Card.Content className="space-y-4 px-6 py-6">
            <div className="rounded-lg border border-zinc-200 p-4">
              <span className="block text-xs font-medium uppercase text-zinc-500">
                User ID
              </span>
              <p className="mt-2 break-all text-sm text-zinc-700">{user.id}</p>
            </div>
            <div className="rounded-lg border border-zinc-200 p-4">
              <span className="block text-xs font-medium uppercase text-zinc-500">
                Created
              </span>
              <p className="mt-2 text-sm text-zinc-700">
                {formatDateLabel(user.created_at)}
              </p>
            </div>
          </Card.Content>
        </Card>
      </section>
    </AppLayout>
  );
}
