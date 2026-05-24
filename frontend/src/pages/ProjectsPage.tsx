import { Button, Form } from "@heroui/react";
import { startTransition, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import useSWR from "swr";

import { AppLayout } from "../components/AppLayout";
import { FormFields, type FormFieldConfig } from "../components/FormFields";
import { isApiError } from "../utils/api";
import { createProject, type Project } from "../utils/projectsApi";
import { formatDate } from "../utils/view";

export function ProjectsPage() {
  const navigate = useNavigate();
  const { data, error, isLoading, mutate } = useSWR<Project[]>(
    "/api/v1/projects",
  );
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
      await mutate();
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
    </AppLayout>
  );
}
