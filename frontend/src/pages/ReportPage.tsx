import { Navigate, useParams } from "react-router-dom";
import useSWR from "swr";

import { AppLayout } from "../components/AppLayout";
import { isApiError } from "../utils/api";
import type { AnalysisRun, Report } from "../utils/runsApi";
import { formatDate, statusClassName } from "../utils/view";

export function ReportPage() {
  const { runId } = useParams();
  const { data: run } = useSWR<AnalysisRun>(
    runId ? `/api/v1/runs/${runId}` : null,
  );
  const { data: report, error } = useSWR<Report>(
    runId ? `/api/v1/runs/${runId}/report` : null,
  );
  const hasNoReport = isApiError(error) && error.status === 404;

  if (!runId) {
    return <Navigate to="/" replace />;
  }

  return (
    <AppLayout
      actions={
        report ? (
          <span
            className={`inline-flex h-10 items-center rounded-full border px-4 text-sm font-medium ${statusClassName(
              report.status,
            )}`}
          >
            {report.status}
          </span>
        ) : null
      }
      breadcrumbs={[
        { label: "Projects", to: "/" },
        ...(run
          ? [{ label: "Project", to: `/projects/${run.project_id}` }]
          : []),
        { label: "Run", to: `/runs/${runId}` },
        { label: "Report" },
      ]}
      maxWidthClassName="max-w-5xl"
      subtitle={run?.target_application ?? "Loading run..."}
      title="Report"
    >
      {hasNoReport ? (
        <section className="rounded-lg border border-zinc-200 bg-white p-5 text-sm text-zinc-600">
          No report yet.
        </section>
      ) : error ? (
        <section className="rounded-lg border border-rose-200 bg-rose-50 p-5 text-sm text-rose-800">
          Unable to load report.
        </section>
      ) : !report ? (
        <section className="rounded-lg border border-zinc-200 bg-white p-5 text-sm text-zinc-600">
          Loading...
        </section>
      ) : (
        <section className="grid gap-5">
          <div className="rounded-lg border border-zinc-200 bg-white p-5">
            <dl className="grid gap-3 text-sm sm:grid-cols-3">
              <div>
                <dt className="font-medium text-zinc-500">Created</dt>
                <dd>{formatDate(report.created_at)}</dd>
              </div>
              <div>
                <dt className="font-medium text-zinc-500">Updated</dt>
                <dd>{formatDate(report.updated_at)}</dd>
              </div>
              <div>
                <dt className="font-medium text-zinc-500">Storage Path</dt>
                <dd className="break-all">
                  {report.storage_path ?? "Not set"}
                </dd>
              </div>
            </dl>
          </div>

          {report.markdown_body ? (
            <article className="rounded-lg border border-zinc-200 bg-white p-5">
              <pre className="whitespace-pre-wrap font-sans text-sm leading-6 text-zinc-800">
                {report.markdown_body}
              </pre>
            </article>
          ) : null}

          {report.json_body ? (
            <pre className="overflow-auto rounded-lg border border-zinc-200 bg-zinc-50 p-5 text-sm text-zinc-800">
              {JSON.stringify(report.json_body, null, 2)}
            </pre>
          ) : null}
        </section>
      )}
    </AppLayout>
  );
}
