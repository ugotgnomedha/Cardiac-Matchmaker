import { Link, Navigate, useParams } from "react-router-dom";
import type { ReactNode } from "react";
import useSWR from "swr";

import { AppLayout } from "../components/AppLayout";
import type { Dataset } from "../utils/datasetsApi";
import type { LiteratureDocument } from "../utils/documentsApi";
import type { Project } from "../utils/projectsApi";
import type { AnalysisRun } from "../utils/runsApi";
import { formatDate, statusClassName } from "../utils/view";

export function ProjectDetailPage() {
  const { projectId } = useParams();
  const { data: project, error: projectError } = useSWR<Project>(
    projectId ? `/api/v1/projects/${projectId}` : null,
  );
  const { data: datasets } = useSWR<Dataset[]>(
    projectId ? `/api/v1/projects/${projectId}/datasets` : null,
  );
  const { data: documents } = useSWR<LiteratureDocument[]>(
    projectId ? `/api/v1/projects/${projectId}/documents` : null,
  );
  const { data: runs } = useSWR<AnalysisRun[]>(
    projectId ? `/api/v1/projects/${projectId}/runs` : null,
  );

  if (!projectId) {
    return <Navigate to="/" replace />;
  }

  return (
    <AppLayout
      actions={
        projectError ? null : (
          <>
            <Link
              className="inline-flex h-10 items-center justify-center rounded-lg border border-zinc-300 px-4 text-sm font-medium hover:bg-zinc-50"
              to={`/projects/${projectId}/datasets/new`}
            >
              Register Dataset
            </Link>
            <Link
              className="inline-flex h-10 items-center justify-center rounded-lg border border-zinc-300 px-4 text-sm font-medium hover:bg-zinc-50"
              to={`/projects/${projectId}/documents/new`}
            >
              Register Document
            </Link>
            <Link
              className="inline-flex h-10 items-center justify-center rounded-lg bg-teal-700 px-4 text-sm font-semibold text-white hover:bg-teal-800"
              to={`/projects/${projectId}/runs/new`}
            >
              New Run
            </Link>
          </>
        )
      }
      backTo="/"
      breadcrumbs={[
        { label: "Projects", to: "/" },
        { label: project?.name ?? "Project" },
      ]}
      subtitle={project?.description}
      title={project?.name ?? "Loading..."}
    >
      {projectError ? (
        <section className="rounded-lg border border-rose-200 bg-rose-50 p-5 text-sm text-rose-800">
          Project not found.
        </section>
      ) : (
        <section className="grid gap-5 lg:grid-cols-3">
          <WorkflowPanel title="Datasets">
            {(datasets ?? []).length === 0 ? (
              <p className="text-sm text-zinc-600">No datasets.</p>
            ) : (
              <div className="divide-y divide-zinc-200">
                {(datasets ?? []).map((dataset) => (
                  <div className="grid gap-1 py-3" key={dataset.id}>
                    <span className="font-medium">{dataset.name}</span>
                    <span className="text-sm text-zinc-600">
                      {dataset.type} · {dataset.original_filename}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </WorkflowPanel>

          <WorkflowPanel title="Documents">
            {(documents ?? []).length === 0 ? (
              <p className="text-sm text-zinc-600">No documents.</p>
            ) : (
              <div className="divide-y divide-zinc-200">
                {(documents ?? []).map((document) => (
                  <div className="grid gap-2 py-3" key={document.id}>
                    <span className="font-medium">{document.title}</span>
                    <span
                      className={`w-fit rounded-full border px-2 py-1 text-xs font-medium ${statusClassName(
                        document.status,
                      )}`}
                    >
                      {document.status}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </WorkflowPanel>

          <WorkflowPanel title="Runs">
            {(runs ?? []).length === 0 ? (
              <p className="text-sm text-zinc-600">No runs.</p>
            ) : (
              <div className="divide-y divide-zinc-200">
                {(runs ?? []).map((run) => (
                  <Link
                    className="grid gap-2 py-3 hover:text-teal-700"
                    key={run.id}
                    to={`/runs/${run.id}`}
                  >
                    <span className="font-medium">
                      {run.target_application}
                    </span>
                    <span className="text-sm text-zinc-600">
                      {run.target_tissue} · {formatDate(run.created_at)}
                    </span>
                    <span
                      className={`w-fit rounded-full border px-2 py-1 text-xs font-medium ${statusClassName(
                        run.status,
                      )}`}
                    >
                      {run.status}
                    </span>
                  </Link>
                ))}
              </div>
            )}
          </WorkflowPanel>
        </section>
      )}
    </AppLayout>
  );
}

function WorkflowPanel({
  children,
  title,
}: {
  children: ReactNode;
  title: string;
}) {
  return (
    <section className="rounded-lg border border-zinc-200 bg-white p-5">
      <h2 className="text-lg font-semibold tracking-normal">{title}</h2>
      <div className="mt-3">{children}</div>
    </section>
  );
}
