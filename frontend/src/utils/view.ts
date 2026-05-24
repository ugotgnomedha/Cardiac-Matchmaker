export function formatDate(value: string | null | undefined) {
  if (!value) {
    return "Not set";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Not set";
  }

  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function parseOptionalJson(value: string) {
  const trimmedValue = value.trim();
  if (!trimmedValue) {
    return null;
  }

  return JSON.parse(trimmedValue) as Record<string, unknown>;
}

export function statusClassName(status: string) {
  const normalizedStatus = status.toLowerCase();

  if (normalizedStatus === "done" || normalizedStatus === "indexed") {
    return "border-emerald-200 bg-emerald-50 text-emerald-800";
  }

  if (normalizedStatus === "failed") {
    return "border-rose-200 bg-rose-50 text-rose-800";
  }

  if (normalizedStatus === "running") {
    return "border-sky-200 bg-sky-50 text-sky-800";
  }

  return "border-zinc-200 bg-zinc-50 text-zinc-700";
}
