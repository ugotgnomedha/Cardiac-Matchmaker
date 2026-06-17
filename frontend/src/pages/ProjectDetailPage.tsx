import { Link, Navigate, useParams } from "react-router-dom";
import { useState, type ReactNode } from "react";
import useSWR, { mutate } from "swr";

import { AppLayout } from "../components/AppLayout";
import { ConfirmModal } from "../components/ConfirmModal";
import type { Dataset } from "../utils/datasetsApi";
import { deleteDataset as deleteDatasetApi } from "../utils/datasetsApi";
import type { LiteratureDocument } from "../utils/documentsApi";
import { deleteDocument as deleteDocumentApi, indexDocument as indexDocumentApi } from "../utils/documentsApi";
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

  const [deleteTarget, setDeleteTarget] = useState<{
    kind: "dataset" | "document";
    id: string;
    name: string;
  } | null>(null);

  const [indexingDocId, setIndexingDocId] = useState<string | null>(null);

  if (!projectId) {
    return <Navigate to="/" replace />;
  }

  async function handleDelete() {
    if (!deleteTarget || !projectId) return;
    const { kind, id } = deleteTarget;
    try {
      if (kind === "dataset") {
        await deleteDatasetApi(projectId, id);
      } else {
        await deleteDocumentApi(projectId, id);
      }
    } catch {
      // error will be reflected via SWR
    }
    setDeleteTarget(null);
    mutate(`/api/v1/projects/${projectId}/datasets`);
    mutate(`/api/v1/projects/${projectId}/documents`);
  }

  async function handleIndex(docId: string) {
    if (!projectId) return;
    setIndexingDocId(docId);
    try {
      await indexDocumentApi(projectId, docId);
    } catch {
      // error will be reflected via SWR
    }
    setIndexingDocId(null);
    mutate(`/api/v1/projects/${projectId}/documents`);
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
                  <div className="flex items-center justify-between gap-2 py-3" key={dataset.id}>
                    <div className="grid gap-1 min-w-0">
                      <span className="font-medium truncate">{dataset.name}</span>
                      <span className="text-sm text-zinc-600 truncate">
                        {dataset.type} · {dataset.original_filename}
                      </span>
                    </div>
                    <div className="flex shrink-0 items-center gap-1">
                      <Link
                        className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-zinc-400 hover:bg-teal-50 hover:text-teal-600"
                        to={`/projects/${projectId}/datasets/${dataset.id}/edit`}
                        title="Edit dataset"
                      >
                        <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                          <path d="M11 4H4a1 1 0 00-1 1v14a1 1 0 001 1h14a1 1 0 001-1v-7" />
                          <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" />
                        </svg>
                      </Link>
                      <button
                        className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-zinc-400 hover:bg-rose-50 hover:text-rose-600"
                        onClick={() =>
                          setDeleteTarget({ kind: "dataset", id: dataset.id, name: dataset.name })
                        }
                        title="Delete dataset"
                        type="button"
                      >
                        <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                          <path d="M3 6h18M8 6V4a1 1 0 011-1h6a1 1 0 011 1v2m3 0v14a1 1 0 01-1 1H6a1 1 0 01-1-1V6h14" />
                          <path d="M10 11v6M14 11v6" />
                        </svg>
                      </button>
                    </div>
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
                {(documents ?? []).map((doc) => (
                  <div className="flex items-center justify-between gap-2 py-3" key={doc.id}>
                    <div className="grid gap-1 min-w-0">
                      <span className="font-medium truncate">{doc.title}</span>
                      <div className="flex items-center gap-2">
                        <span
                          className={`w-fit rounded-full border px-2 py-1 text-xs font-medium ${statusClassName(
                            doc.status,
                          )}`}
                        >
                          {doc.status}
                        </span>
                      </div>
                    </div>
                    <div className="flex shrink-0 items-center gap-1">
                      {doc.status !== "indexed" ? (
                        <button
                          className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-zinc-400 hover:bg-teal-50 hover:text-teal-600 disabled:opacity-50"
                          disabled={indexingDocId === doc.id}
                          onClick={() => handleIndex(doc.id)}
                          title="Index document"
                          type="button"
                        >
                          <svg
                            className={`h-4 w-4 ${indexingDocId === doc.id ? "animate-spin" : ""}`}
                            fill="none"
                            stroke="currentColor"
                            strokeWidth={2}
                            viewBox="0 0 24 24"
                          >
                            <path d="M21 12a9 9 0 11-2.64-6.36M21 3v6h-6" />
                          </svg>
                        </button>
                      ) : null}
                      <button
                        className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-zinc-400 hover:bg-rose-50 hover:text-rose-600"
                        onClick={() =>
                          setDeleteTarget({ kind: "document", id: doc.id, name: doc.title })
                        }
                        title="Delete document"
                        type="button"
                      >
                        <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                          <path d="M3 6h18M8 6V4a1 1 0 011-1h6a1 1 0 011 1v2m3 0v14a1 1 0 01-1 1H6a1 1 0 01-1-1V6h14" />
                          <path d="M10 11v6M14 11v6" />
                        </svg>
                      </button>
                    </div>
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

      <ConfirmModal
        confirmLabel="Delete"
        isOpen={deleteTarget !== null}
        message={
          deleteTarget ? (
            <>
              Are you sure you want to delete{" "}
              <strong>{deleteTarget.name}</strong>?
            </>
          ) : null
        }
        onCancel={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
        title={deleteTarget ? `Delete ${deleteTarget.kind}` : ""}
      />
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
