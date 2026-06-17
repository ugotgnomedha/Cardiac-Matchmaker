import { Link, Navigate, useNavigate, useParams } from "react-router-dom";
import { useState } from "react";
import useSWR from "swr";

import { AppLayout } from "../components/AppLayout";
import type { AnalysisRun, AnalysisStep, EvidenceItem } from "../utils/runsApi";
import { createRun } from "../utils/runsApi";
import { formatDate, statusClassName } from "../utils/view";

export function RunDetailPage() {
  const { runId } = useParams();
  const navigate = useNavigate();
  const [isRerunning, setIsRerunning] = useState(false);
  const { data: run, error: runError } = useSWR<AnalysisRun>(
    runId ? `/api/v1/runs/${runId}` : null,
    {
      refreshInterval: (latestRun) =>
        latestRun?.status === "queued" || latestRun?.status === "running"
          ? 3000
          : 0,
    },
  );
  const { data: steps } = useSWR<AnalysisStep[]>(
    runId ? `/api/v1/runs/${runId}/steps` : null,
    {
      refreshInterval:
        run?.status === "queued" || run?.status === "running" ? 3000 : 0,
    },
  );
  const { data: evidence } = useSWR<EvidenceItem[]>(
    runId ? `/api/v1/runs/${runId}/evidence` : null,
    {
      refreshInterval:
        run?.status === "queued" || run?.status === "running" ? 3000 : 0,
    },
  );

  if (!runId) {
    return <Navigate to="/" replace />;
  }

  async function handleRerun() {
    if (!run) return;
    setIsRerunning(true);
    try {
      const newRun = await createRun(run.project_id, {
        target_application: run.target_application,
        target_tissue: run.target_tissue,
        query: run.query,
        constraints: run.constraints ?? undefined,
        selected_config: run.selected_config ?? undefined,
      });
      navigate(`/runs/${newRun.id}`);
    } catch {
      setIsRerunning(false);
    }
  }

  return (
    <AppLayout
      actions={
        run ? (
          <>
            <span
              className={`inline-flex h-10 items-center rounded-full border px-4 text-sm font-medium ${statusClassName(
                run.status,
              )}`}
            >
              {run.status}
            </span>
            <Link
              className="inline-flex h-10 items-center justify-center rounded-lg border border-zinc-300 px-4 text-sm font-medium hover:bg-zinc-50"
              to={`/runs/${runId}/report`}
            >
              Report
            </Link>
            <button
              className="inline-flex h-10 items-center justify-center rounded-lg border border-zinc-300 px-4 text-sm font-medium hover:bg-teal-50 hover:text-teal-700 disabled:opacity-50"
              disabled={isRerunning}
              onClick={handleRerun}
              type="button"
            >
              {isRerunning ? "Creating..." : "Rerun"}
            </button>
          </>
        ) : null
      }
      breadcrumbs={[
        { label: "Projects", to: "/" },
        ...(run
          ? [{ label: "Project", to: `/projects/${run.project_id}` }]
          : []),
        { label: "Run" },
      ]}
      subtitle={run?.query}
      title={
        run?.target_application ?? (runError ? "Run not found" : "Loading...")
      }
    >
      {runError ? (
        <section className="rounded-lg border border-rose-200 bg-rose-50 p-5 text-sm text-rose-800">
          Run not found.
        </section>
      ) : (
        <>
          {run?.status === "failed" && run.error_message ? (
            <section className="mb-5 rounded-lg border border-rose-200 bg-rose-50 p-5">
              <h3 className="text-sm font-semibold text-rose-800">Error</h3>
              <p className="mt-1 text-sm text-rose-700 whitespace-pre-wrap break-all">
                {run.error_message}
              </p>
            </section>
          ) : null}
          <section className="grid gap-5 lg:grid-cols-[320px_1fr]">
          <section className="rounded-lg border border-zinc-200 bg-white p-5">
            <h2 className="text-lg font-semibold tracking-normal">
              Run Snapshot
            </h2>
            <dl className="mt-4 grid gap-3 text-sm">
              <div>
                <dt className="font-medium text-zinc-500">Target Tissue</dt>
                <dd>{run?.target_tissue ?? "Loading..."}</dd>
              </div>
              {run?.selected_config?.model ? (
                <div>
                  <dt className="font-medium text-zinc-500">Model</dt>
                  <dd className="font-mono text-sm">{String(run.selected_config.model)}</dd>
                </div>
              ) : null}
              <div>
                <dt className="font-medium text-zinc-500">Created</dt>
                <dd>{formatDate(run?.created_at)}</dd>
              </div>
              <div>
                <dt className="font-medium text-zinc-500">Started</dt>
                <dd>{formatDate(run?.started_at)}</dd>
              </div>
              <div>
                <dt className="font-medium text-zinc-500">Finished</dt>
                <dd>{formatDate(run?.finished_at)}</dd>
              </div>
            </dl>
          </section>

          <section className="grid gap-5">
            <section className="rounded-lg border border-zinc-200 bg-white p-5">
              <h2 className="text-lg font-semibold tracking-normal">
                Trace Steps
              </h2>
              {(steps ?? []).length === 0 ? (
                <p className="mt-3 text-sm text-zinc-600">No steps.</p>
              ) : (
                <div className="mt-3 divide-y divide-zinc-200">
                  {(steps ?? []).map((step) => (
                    <div className="grid gap-2 py-3" key={step.id}>
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="font-medium">
                          {step.sequence_number}. {step.step_name}
                        </span>
                        <span
                          className={`rounded-full border px-2 py-1 text-xs font-medium ${statusClassName(
                            step.status,
                          )}`}
                        >
                          {step.status}
                        </span>
                      </div>
                      {step.error_message ? (
                        <p className="text-sm text-rose-700">
                          {step.error_message}
                        </p>
                      ) : null}
                    </div>
                  ))}
                </div>
              )}
            </section>

            <section className="rounded-lg border border-zinc-200 bg-white p-5">
              <h2 className="text-lg font-semibold tracking-normal">
                Evidence
              </h2>
              {(evidence ?? []).length === 0 ? (
                <p className="mt-3 text-sm text-zinc-600">No evidence.</p>
              ) : (
                <div className="mt-3 divide-y divide-zinc-200">
                  {(evidence ?? []).map((item) => (
                    <div className="grid gap-2 py-3" key={item.id}>
                      <span className="font-medium">{item.candidate_name}</span>
                      <p className="text-sm text-zinc-700">{item.claim}</p>
                      <span className="text-xs font-medium text-zinc-500">
                        {item.support_label}
                        {item.score === null ? "" : ` · ${item.score}`}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </section>
        </section>
      </>
      )}
    </AppLayout>
  );
}
