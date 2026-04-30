import { Button, Card } from "@heroui/react";
import { startTransition } from "react";
import { useNavigate, useOutletContext } from "react-router-dom";

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
  const navigate = useNavigate();

  return (
    <main className="min-h-screen px-4 py-6 sm:px-6 lg:px-8">
      <div className="mx-auto flex max-w-6xl flex-col gap-6">
        <section className="grid gap-6">
          <div className="rounded-[2rem] border sm:p-10">
            <div className="mt-6 flex flex-wrap gap-3 text-sm">
              <span className="rounded-full  px-4 py-2">{user.email}</span>
              <span className="rounded-full px-4 py-2">
                {user.is_superuser ? "Superuser access" : "Standard access"}
              </span>
              <span className="rounded-full px-4 py-2 text-emerald-800">
                {user.is_active ? "Active account" : "Inactive account"}
              </span>
            </div>
          </div>

          <Card className="rounded-[2rem] border backdrop-blur-xl">
            <Card.Header className="space-y-2 px-8 pt-8 pb-0">
              <span className="text-xs font-semibold uppercase tracking-[0.32em]">
                Current User
              </span>
              <h2 className="text-3xl font-semibold text-stone-900">
                Session snapshot
              </h2>
            </Card.Header>
            <Card.Content className="space-y-4 px-8 py-8">
              <div className="rounded-[1.5rem]  p-4">
                <span className="block text-xs uppercase tracking-[0.26em] ">
                  User ID
                </span>
                <p className="mt-2 break-all text-sm text-stone-700">
                  {user.id}
                </p>
              </div>
              <div className="rounded-[1.5rem] p-4">
                <span className="block text-xs uppercase tracking-[0.26em] ">
                  Created
                </span>
                <p className="mt-2 text-sm ">
                  {formatDateLabel(user.created_at)}
                </p>
              </div>
              <Button
                fullWidth
                onPress={() => {
                  startTransition(() => {
                    navigate("/logout");
                  });
                }}
              >
                Open logout page
              </Button>
            </Card.Content>
          </Card>
        </section>
      </div>
    </main>
  );
}
