import { Button, Form } from "@heroui/react";
import { startTransition, useEffect, useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate, useParams } from "react-router-dom";
import useSWR from "swr";

import { AppLayout } from "../components/AppLayout";
import { FormFields, type FormFieldConfig } from "../components/FormFields";
import { isApiError } from "../utils/api";
import type { ModelConfig } from "../utils/modelsApi";
import { createRun } from "../utils/runsApi";
import { parseOptionalJson } from "../utils/view";

export function NewRunPage() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [targetApplication, setTargetApplication] = useState("");
  const [targetTissue, setTargetTissue] = useState("");
  const [query, setQuery] = useState("");
  const [constraints, setConstraints] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { data: models } = useSWR<ModelConfig[]>("/api/v1/models");
  const [selectedModelId, setSelectedModelId] = useState("");

  useEffect(() => {
    if (models && models.length === 1) {
      setSelectedModelId(models[0].model_id);
    }
  }, [models]);

  if (!projectId) {
    return <Navigate to="/" replace />;
  }
  const currentProjectId = projectId;
  const runFields: FormFieldConfig[] = [
    {
      description:
        "Describe the intended surgical or repair scenario for ranking.",
      kind: "input",
      label: "Target application",
      maxLength: 255,
      name: "target_application",
      onChange: setTargetApplication,
      placeholder: "myocardial patch",
      required: true,
      type: "text",
      value: targetApplication,
    },
    {
      description: "Name the cardiac tissue, structure, or function target.",
      kind: "input",
      label: "Target tissue",
      maxLength: 255,
      name: "target_tissue",
      onChange: setTargetTissue,
      placeholder: "left ventricle",
      required: true,
      type: "text",
      value: targetTissue,
    },
    {
      description:
        "State the recommendation question the analysis run should answer.",
      kind: "textarea",
      label: "Research query",
      name: "query",
      onChange: setQuery,
      placeholder:
        "Find the best placental material for myocardial patch support.",
      required: true,
      rows: 5,
      value: query,
    },
    {
      description:
        "Optional JSON for candidate count, mechanical priorities, or exclusion rules.",
      kind: "textarea",
      label: "Constraints JSON",
      name: "constraints",
      onChange: setConstraints,
      placeholder: '{ "prefer_mechanical_support": true, "max_candidates": 5 }',
      rows: 5,
      value: constraints,
    },
  ];

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      const run = await createRun(currentProjectId, {
        target_application: targetApplication,
        target_tissue: targetTissue,
        query,
        constraints: parseOptionalJson(constraints),
        selected_config: selectedModelId ? { model: selectedModelId } : undefined,
      });

      startTransition(() => {
        navigate(`/runs/${run.id}`);
      });
    } catch (error) {
      if (error instanceof SyntaxError) {
        setErrorMessage("Constraints must be valid JSON.");
      } else {
        setErrorMessage(
          isApiError(error) ? error.message : "Unable to create run.",
        );
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  const modelSelector = models === undefined ? (
    <p className="text-sm text-zinc-500">Loading models...</p>
  ) : models.length === 0 ? (
    <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
      No models configured.{" "}
      <Link to="/models/new" className="underline">
        Add one
      </Link>{" "}
      first.
    </p>
  ) : models.length === 1 ? (
    <div className="grid gap-1.5">
      <span className="text-sm font-medium text-zinc-700">Model</span>
      <input
        className="h-10 rounded-lg border border-zinc-300 px-3 text-zinc-500 bg-zinc-50"
        readOnly
        value={models[0].name}
      />
      <span className="text-xs text-zinc-500">
        Only one model available. This model will be used.
      </span>
    </div>
  ) : (
    <div className="grid gap-1.5">
      <label className="text-sm font-medium text-zinc-700" htmlFor="model-select">
        Model
      </label>
      <select
        className="h-10 rounded-lg border border-zinc-300 px-3 text-zinc-950"
        id="model-select"
        onChange={(e) => setSelectedModelId(e.target.value)}
        required
        value={selectedModelId}
      >
        <option value="">Select model...</option>
        {models.map((m) => (
          <option key={m.id} value={m.model_id}>
            {m.name} ({m.provider})
          </option>
        ))}
      </select>
      <span className="text-xs text-zinc-500">
        Select the LLM to power the reasoning agent for this run.
      </span>
    </div>
  );

  return (
    <AppLayout
      breadcrumbs={[
        { label: "Projects", to: "/" },
        { label: "Project", to: `/projects/${currentProjectId}` },
        { label: "New Run" },
      ]}
      maxWidthClassName="max-w-3xl"
      title="New Run"
    >
      <Form
        className="flex flex-col gap-4 rounded-lg border border-zinc-200 bg-white p-5"
        onSubmit={handleSubmit}
      >
        <FormFields fields={runFields} />

        {modelSelector}

        {errorMessage ? (
          <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">
            {errorMessage}
          </p>
        ) : null}

        <div className="flex flex-wrap gap-2">
          <Button
            className="h-10 rounded-lg bg-teal-700 px-4 text-sm font-semibold text-white hover:bg-teal-800"
            isDisabled={isSubmitting || (models?.length ?? 0) === 0}
            type="submit"
          >
            {isSubmitting ? "Creating..." : "Create Run"}
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
