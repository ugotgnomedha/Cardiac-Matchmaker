import { Button, Form } from "@heroui/react";
import { startTransition, useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate, useParams } from "react-router-dom";

import { AppLayout } from "../components/AppLayout";
import { FormFields, type FormFieldConfig } from "../components/FormFields";
import { isApiError } from "../utils/api";
import { createDocument } from "../utils/documentsApi";
import { parseOptionalJson } from "../utils/view";

export function DocumentUploadPage() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [originalFilename, setOriginalFilename] = useState("");
  const [storagePath, setStoragePath] = useState("");
  const [metadata, setMetadata] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!projectId) {
    return <Navigate to="/" replace />;
  }
  const currentProjectId = projectId;
  const documentFields: FormFieldConfig[] = [
    {
      description:
        "Use the paper title or a clear short name for retrieval citations.",
      kind: "input",
      label: "Document title",
      maxLength: 255,
      name: "title",
      onChange: setTitle,
      placeholder: "Heart Map",
      required: true,
      type: "text",
      value: title,
    },
    {
      description:
        "Record the original PDF filename before parsing and chunking.",
      kind: "input",
      label: "Original filename",
      maxLength: 255,
      name: "original_filename",
      onChange: setOriginalFilename,
      placeholder: "heart-map.pdf",
      required: true,
      type: "text",
      value: originalFilename,
    },
    {
      description:
        "Point to the mounted PDF path available to the backend and worker.",
      kind: "input",
      label: "Storage path",
      name: "storage_path",
      onChange: setStoragePath,
      placeholder: "/data/pdfs/heart-map.pdf",
      required: true,
      type: "text",
      value: storagePath,
    },
    {
      description:
        "Optional JSON for authors, DOI, paper nickname, year, or extraction notes.",
      kind: "textarea",
      label: "Metadata JSON",
      name: "metadata",
      onChange: setMetadata,
      placeholder: '{ "paper": "Doll et al.", "year": 2024 }',
      rows: 5,
      value: metadata,
    },
  ];

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      await createDocument(currentProjectId, {
        title,
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
          isApiError(error) ? error.message : "Unable to register document.",
        );
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <AppLayout
      breadcrumbs={[
        { label: "Projects", to: "/" },
        { label: "Project", to: `/projects/${currentProjectId}` },
        { label: "Register Document" },
      ]}
      maxWidthClassName="max-w-3xl"
      title="Register Document"
    >
      <Form
        className="flex flex-col gap-4 rounded-lg border border-zinc-200 bg-white p-5"
        onSubmit={handleSubmit}
      >
        <FormFields fields={documentFields} />

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
            {isSubmitting ? "Registering..." : "Register Document"}
          </Button>
          <Link
            className="inline-flex h-10 items-center justify-center rounded-lg border border-zinc-300 px-4 text-sm font-medium hover:bg-zinc-50"
            to={`/projects/${currentProjectId}`}
          >
            Cancel
          </Link>
        </div>
      </Form>
    </AppLayout>
  );
}
