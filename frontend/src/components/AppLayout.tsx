import type { ReactNode } from "react";
import { Link, useOutletContext } from "react-router-dom";

import type { AuthUser } from "../hooks/useAuth";

export type BreadcrumbItem = {
  label: string;
  to?: string;
};

type AppLayoutProps = {
  actions?: ReactNode;
  breadcrumbs?: BreadcrumbItem[];
  children: ReactNode;
  maxWidthClassName?: string;
  subtitle?: ReactNode;
  title: ReactNode;
};

export function AppLayout({
  actions,
  breadcrumbs = [],
  children,
  maxWidthClassName = "max-w-6xl",
  subtitle,
  title,
}: AppLayoutProps) {
  const user = useOutletContext<AuthUser>();

  return (
    <main className="min-h-screen bg-white px-4 py-6 text-zinc-950 sm:px-6 lg:px-8">
      <div className={`mx-auto flex ${maxWidthClassName} flex-col gap-6`}>
        <div className="flex flex-col gap-3 border-b border-zinc-200 pb-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
              {breadcrumbs.length > 0 ? (
                <Breadcrumbs items={breadcrumbs} />
              ) : null}
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <span className="text-sm font-medium text-teal-700">
                {user.email}
              </span>
              <Link
                className="inline-flex h-10 items-center justify-center rounded-lg border border-zinc-300 px-4 text-sm font-medium hover:bg-zinc-50"
                to="/logout"
              >
                Logout
              </Link>
            </div>
          </div>

          <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <h1 className="text-3xl font-semibold tracking-normal text-zinc-950">
                {title}
              </h1>
              {subtitle ? (
                <div className="mt-2 max-w-3xl text-sm text-zinc-600">
                  {subtitle}
                </div>
              ) : null}
            </div>
            {actions ? (
              <div className="flex flex-wrap gap-2">{actions}</div>
            ) : null}
          </header>
        </div>

        {children}
      </div>
    </main>
  );
}

function Breadcrumbs({ items }: { items: BreadcrumbItem[] }) {
  return (
    <nav aria-label="Breadcrumbs" className="text-sm font-medium text-zinc-600">
      <ol className="flex flex-wrap items-center gap-2">
        {items.map((item, index) => {
          const isLast = index === items.length - 1;

          return (
            <li
              className="flex items-center gap-2"
              key={`${item.label}-${index}`}
            >
              {item.to && !isLast ? (
                <Link className="hover:text-teal-700" to={item.to}>
                  {item.label}
                </Link>
              ) : (
                <span className={isLast ? "text-zinc-950" : undefined}>
                  {item.label}
                </span>
              )}
              {!isLast ? <span className="text-zinc-400">/</span> : null}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
