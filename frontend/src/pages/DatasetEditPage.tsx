import { Button, Form } from "@heroui/react";
import { startTransition, useEffect, useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate, useParams } from "react-router-dom";
import useSWR from "swr";

import { AppLayout } from "../components/AppLayout";
import { FormFields, type FormFieldConfig } from "../components/FormFields";
import { isApiError } from "../utils/api";
import type { Dataset } from "../utils/datasetsApi";
import { updateDataset } from "../utils/datasetsApi";
import { parseOptionalJson } from "../utils/view";

export function DatasetEditPage() {
  const { projectId, datasetId } = useParams();
  const navigate = useNavigate();
  const { data: datasets, error: loadError } = useSWR<Dataset[]>(
    projectId ? `/api/v1/projects/${projectId}/datasets` : null,
  );

  const found = (datasets ?? []).find((d) => d.id === datasetId);

  const [name, setName] = useState("");
  const [type, setType] = useState("placenta");
  const [originalFilename, setOriginalFilename] = useState("");
  const [storagePath, setStoragePath] = useState("");
  const [metadata, setMetadata] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (found) {
      setName(found.name);
      setType(found.type);
      setOriginalFilename(found.original_filename);
      setStoragePath(found.storage_path);
      setMetadata(found.metadata ? JSON.stringify(found.metadata, null, 2) : "");
    }
  }, [found]);
  /* eslint-enable react-hooks/set-state-in-effect */

  if (!projectId || !datasetId) {
    return <Navigate to="/" replace />;
  }
  const currentProjectId = projectId;

  const datasetFields: FormFieldConfig[] = [
    {
      description:
        "Use a concise dataset title researchers can recognize in run traces.",
      kind: "input",
      label: "Dataset name",
      maxLength: 255,
      name: "name",
      onChange: setName,
      placeholder: "Placenta proteomics",
      required: true,
      type: "text",
      value: name,
    },
    {
      description:
        "Classify the source so later preprocessing can choose the right normalization path.",
      kind: "select",
      label: "Dataset type",
      name: "type",
      onChange: setType,
      options: [
        { label: "Placenta", value: "placenta" },
        { label: "Cardiac", value: "cardiac" },
        { label: "Placenta-heart merged", value: "placenta_heart_merged" },
      ],
      placeholder: "Select dataset type",
      required: true,
      value: type,
    },
    {
      description:
        "Store the filename exactly as it arrived before preprocessing.",
      kind: "input",
      label: "Original filename",
      maxLength: 255,
      name: "original_filename",
      onChange: setOriginalFilename,
      placeholder: "placenta.tsv",
      required: true,
      type: "text",
      value: originalFilename,
    },
    {
      description:
        "Point to the mounted artifact path available to the backend and worker.",
      kind: "input",
      label: "Storage path",
      name: "storage_path",
      onChange: setStoragePath,
      placeholder: "/data/raw/placenta.tsv",
      required: true,
      type: "text",
      value: storagePath,
    },
    {
      description:
        "Optional JSON for delimiter, source, organism, assay, or column hints.",
      kind: "textarea",
      label: "Metadata JSON",
      name: "metadata",
      onChange: setMetadata,
      placeholder: '{ "delimiter": "tab", "source": "demo" }',
      rows: 5,
      value: metadata,
    },
  ];

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      await updateDataset(currentProjectId, datasetId!, {
        name,
        type,
        original_filename: originalFilename,
        storage_path: storagePath,
        metadata: parseOptionalJson(metadata),
      });

      startTransition(() => {
        navigate(`/projects/${currentProjectId}`);
      });
    } catch (error) {
      if (error instanceof SyntaxError) {
        setErrorMessage("Metadata must be valid JSON.");
      } else {
        setErrorMessage(
          isApiError(error) ? error.message : "Unable to update dataset.",
        );
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  if (loadError) {
    return (
      <AppLayout
        breadcrumbs={[
          { label: "Projects", to: "/" },
          { label: "Project", to: `/projects/${currentProjectId}` },
          { label: "Edit Dataset" },
        ]}
        title="Edit Dataset"
      >
        <section className="rounded-lg border border-rose-200 bg-rose-50 p-5 text-sm text-rose-800">
          Dataset not found.
        </section>
      </AppLayout>
    );
  }

  return (
    <AppLayout
      breadcrumbs={[
        { label: "Projects", to: "/" },
        { label: "Project", to: `/projects/${currentProjectId}` },
        { label: "Edit Dataset" },
      ]}
      maxWidthClassName="max-w-3xl"
      title="Edit Dataset"
    >
      {name ? (
        <Form
          className="flex flex-col gap-4 rounded-lg border border-zinc-200 bg-white p-5"
          onSubmit={handleSubmit}
        >
          <FormFields fields={datasetFields} />

          {errorMessage ? (
            <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">
              {errorMessage}
            </p>
          ) : null}

          <div className="flex flex-wrap gap-2">
            <Button
              className="h-10 rounded-lg bg-teal-700 px-4 text-sm font-semibold text-white hover:bg-teal-800"
              isDisabled={isSubmitting}
              type="submit"
            >
              {isSubmitting ? "Saving..." : "Save Dataset"}
            </Button>
            <Link
              className="inline-flex h-10 items-center justify-center rounded-lg border border-zinc-300 px-4 text-sm font-medium hover:bg-zinc-50"
              to={`/projects/${currentProjectId}`}
            >
              Cancel
            </Link>
          </div>
        </Form>
      ) : (
        <p className="text-sm text-zinc-600">Loading...</p>
      )}
    </AppLayout>
  );
}
