import { Button, Form } from "@heroui/react";
import { startTransition, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import useSWR, { mutate } from "swr";

import { AppLayout } from "../components/AppLayout";
import { FormFields, type FormFieldConfig } from "../components/FormFields";
import { isApiError } from "../utils/api";
import type { ModelConfig } from "../utils/modelsApi";
import { deleteModel as deleteModelApi } from "../utils/modelsApi";
import { createProject, type Project } from "../utils/projectsApi";
import { formatDate } from "../utils/view";

export function ProjectsPage() {
  const navigate = useNavigate();
  const { data, error, isLoading, mutate: mutateProjects } = useSWR<Project[]>(
    "/api/v1/projects",
  );
  const { data: models } = useSWR<ModelConfig[]>("/api/v1/models", {
    refreshInterval: (latest) =>
      latest?.some((m) => m.status === "pulling") ? 2000 : 0,
  });
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const projects = data ?? [];
  const projectFields: FormFieldConfig[] = [
    {
      description: "Name the research workspace or experiment bundle.",
      kind: "input",
      label: "Project name",
      maxLength: 255,
      name: "name",
      onChange: setName,
      placeholder: "Placenta-heart matching MVP",
      required: true,
      type: "text",
      value: name,
    },
    {
      description: "Optional context for target tissue, dataset scope, or demo objective.",
      kind: "textarea",
      label: "Project description",
      name: "description",
      onChange: setDescription,
      placeholder: "Compare placental regions against left ventricle mechanics using Heart Map literature.",
      rows: 4,
      value: description,
    },
  ];

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      const project = await createProject({
        name,
        description: description.trim() ? description : null,
      });
      await mutateProjects();
      setName("");
      setDescription("");

      startTransition(() => {
        navigate(`/projects/${project.id}`);
      });
    } catch (submitError) {
      setErrorMessage(
        isApiError(submitError)
          ? submitError.message
          : "Unable to create project.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <AppLayout
      breadcrumbs={[{ label: "Projects" }]}
      title="Research Projects"
    >
      <section className="grid gap-5 lg:grid-cols-[360px_1fr]">
          <Form
            className="flex flex-col gap-4 rounded-lg border border-zinc-200 bg-white p-5"
            onSubmit={handleSubmit}
          >
            <h2 className="text-lg font-semibold tracking-normal">
              New Project
            </h2>
            <FormFields fields={projectFields} />
            {errorMessage ? (
              <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">
                {errorMessage}
              </p>
            ) : null}
            <Button
              className="h-10 rounded-lg bg-teal-700 px-4 text-sm font-semibold text-white hover:bg-teal-800"
              isDisabled={isSubmitting}
              type="submit"
            >
              {isSubmitting ? "Creating..." : "Create Project"}
            </Button>
          </Form>

          <section className="rounded-lg border border-zinc-200 bg-white">
            <div className="border-b border-zinc-200 px-5 py-4">
              <h2 className="text-lg font-semibold tracking-normal">
                Project List
              </h2>
            </div>

            {isLoading ? (
              <p className="px-5 py-6 text-sm text-zinc-600">Loading...</p>
            ) : error ? (
              <p className="px-5 py-6 text-sm text-rose-700">
                Unable to load projects.
              </p>
            ) : projects.length === 0 ? (
              <p className="px-5 py-6 text-sm text-zinc-600">
                No projects yet.
              </p>
            ) : (
              <div className="divide-y divide-zinc-200">
                {projects.map((project) => (
                  <Link
                    className="grid gap-2 px-5 py-4 hover:bg-zinc-50"
                    key={project.id}
                    to={`/projects/${project.id}`}
                  >
                    <span className="text-base font-semibold">
                      {project.name}
                    </span>
                    {project.description ? (
                      <span className="text-sm text-zinc-600">
                        {project.description}
                      </span>
                    ) : null}
                    <span className="text-xs font-medium text-zinc-500">
                      Updated {formatDate(project.updated_at)}
                    </span>
                  </Link>
                ))}
              </div>
            )}
          </section>
      </section>

      <section className="mt-5 rounded-lg border border-zinc-200 bg-white">
        <div className="flex items-center justify-between border-b border-zinc-200 px-5 py-4">
          <h2 className="text-lg font-semibold tracking-normal">Available Models</h2>
          <Link
            className="inline-flex h-9 items-center rounded-lg bg-teal-700 px-4 text-sm font-semibold text-white hover:bg-teal-800"
            to="/models/new"
          >
            Add Model
          </Link>
        </div>
        {(models ?? []).length === 0 ? (
          <p className="px-5 py-6 text-sm text-zinc-600">No models configured.</p>
        ) : (
          <div className="divide-y divide-zinc-200">
            {(models ?? []).map((m) => (
              <div className="flex items-center justify-between gap-3 px-5 py-3" key={m.id}>
                <div className="grid gap-0.5 min-w-0 flex-1">
                  <span className="font-medium truncate">{m.name}</span>
                  <span className="text-xs text-zinc-500">
                    {m.provider === "ollama" ? "Ollama" : "LiteLLM"} · {m.model_id}
                  </span>
                  {m.status === "pulling" ? (
                    <div className="mt-1 h-1.5 w-full rounded-full bg-zinc-200">
                      <div className="h-1.5 animate-pulse rounded-full bg-teal-600/50 w-full" />
                    </div>
                  ) : m.status === "error" ? (
                    <span className="text-xs text-rose-600">Pull failed</span>
                  ) : null}
                </div>
                <button
                  className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded text-zinc-400 hover:bg-rose-50 hover:text-rose-600"
                  onClick={async () => {
                    await deleteModelApi(m.id);
                    mutate("/api/v1/models");
                  }}
                  title="Remove model"
                  type="button"
                >
                  <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                    <path d="M3 6h18M8 6V4a1 1 0 011-1h6a1 1 0 011 1v2m3 0v14a1 1 0 01-1 1H6a1 1 0 01-1-1V6h14" />
                    <path d="M10 11v6M14 11v6" />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        )}
      </section>
    </AppLayout>
  );
}
