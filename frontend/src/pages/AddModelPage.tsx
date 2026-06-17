import { Button } from "@heroui/react";
import { startTransition, useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { AppLayout } from "../components/AppLayout";
import { isApiError } from "../utils/api";
import {
  addModel,
  listOllamaModels,
  pullOllamaModel,
  testApiKey,
  type OllamaModel,
} from "../utils/modelsApi";

const LITELLM_PROVIDERS: Record<string, { label: string; prefix: string; defaultModel: string }> = {
  openai: { label: "OpenAI", prefix: "openai/", defaultModel: "gpt-4o" },
  anthropic: { label: "Anthropic", prefix: "anthropic/", defaultModel: "claude-3-haiku-20240307" },
  deepseek: { label: "DeepSeek", prefix: "deepseek/", defaultModel: "deepseek-chat" },
  groq: { label: "Groq", prefix: "groq/", defaultModel: "llama-3.3-70b-versatile" },
  mistral: { label: "Mistral", prefix: "mistral/", defaultModel: "mistral-large-latest" },
};

export function AddModelPage() {
  const navigate = useNavigate();
  const [tab, setTab] = useState<"ollama" | "litellm">("ollama");

  const [ollamaModels, setOllamaModels] = useState<OllamaModel[]>([]);
  const [ollamaFetchError, setOllamaFetchError] = useState<string | null>(null);
  const [selectedOllama, setSelectedOllama] = useState("");
  const [customOllama, setCustomOllama] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [pulling, setPulling] = useState(false);

  const [litellmProvider, setLitellmProvider] = useState("openai");
  const [litellmModelId, setLitellmModelId] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [keyTestResult, setKeyTestResult] = useState<{ ok: boolean; message: string } | null>(null);
  const [testing, setTesting] = useState(false);
  const [litellmName, setLitellmName] = useState("");

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (tab === "ollama") {
      setOllamaFetchError(null);
      listOllamaModels()
        .then((r) => setOllamaModels(r.models ?? []))
        .catch((e) => setOllamaFetchError(isApiError(e) ? e.message : String(e)));
    }
  }, [tab]);

  useEffect(() => {
    const p = LITELLM_PROVIDERS[litellmProvider];
    setLitellmModelId(p ? p.prefix + p.defaultModel : "");
    setKeyTestResult(null);
  }, [litellmProvider]);

  async function handleTestKey() {
    setTesting(true);
    setKeyTestResult(null);
    try {
      const r = await testApiKey(litellmProvider, litellmModelId, apiKey);
      setKeyTestResult({ ok: true, message: `OK — model: ${r.model}` });
    } catch (e) {
      setKeyTestResult({ ok: false, message: isApiError(e) ? e.message : String(e) });
    } finally {
      setTesting(false);
    }
  }

  async function handleOllamaSubmit(e: FormEvent) {
    e.preventDefault();
    const modelName = selectedOllama === "__custom__" ? customOllama.trim() : selectedOllama;
    if (!modelName || !displayName.trim()) return;
    setErrorMessage(null);
    setPulling(true);
    try {
      await pullOllamaModel(modelName);
      await addModel({ name: displayName.trim(), provider: "ollama", model_id: modelName });
      startTransition(() => navigate("/"));
    } catch (err) {
      setErrorMessage(isApiError(err) ? err.message : "Failed to add model");
    } finally {
      setPulling(false);
    }
  }

  async function handleLitellmSubmit(e: FormEvent) {
    e.preventDefault();
    if (!litellmName.trim() || !litellmModelId.trim() || !apiKey.trim()) return;
    setErrorMessage(null);
    setIsSubmitting(true);
    try {
      await addModel({ name: litellmName.trim(), provider: "litellm", model_id: litellmModelId.trim(), api_key: apiKey });
      startTransition(() => navigate("/"));
    } catch (err) {
      setErrorMessage(isApiError(err) ? err.message : "Failed to add model");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <AppLayout
      breadcrumbs={[
        { label: "Projects", to: "/" },
        { label: "Add Model" },
      ]}
      maxWidthClassName="max-w-xl"
      title="Add Model"
    >
      <div className="flex border-b border-zinc-200 mb-4">
        {(["ollama", "litellm"] as const).map((t) => (
          <button
            key={t}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 -mb-px ${tab === t ? "border-teal-600 text-teal-700" : "border-transparent text-zinc-500 hover:text-zinc-700"}`}
            onClick={() => setTab(t)}
            type="button"
          >
            {t === "ollama" ? "Local (Ollama)" : "API (LiteLLM)"}
          </button>
        ))}
      </div>

      {tab === "ollama" ? (
        <form className="flex flex-col gap-4 rounded-lg border border-zinc-200 bg-white p-5" onSubmit={handleOllamaSubmit}>
          {ollamaFetchError ? (
            <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
              Could not fetch Ollama models: {ollamaFetchError}
            </p>
          ) : null}
          <label className="grid gap-1.5 text-sm font-medium text-zinc-700">
            Ollama model
            <select
              className="h-10 rounded-lg border border-zinc-300 px-3 text-zinc-950"
              value={selectedOllama}
              onChange={(e) => setSelectedOllama(e.target.value)}
            >
              <option value="">Select downloaded model...</option>
              {ollamaModels.map((m) => (
                <option key={m.name} value={m.name}>
                  {m.name} ({(m.size / 1e9).toFixed(1)} GB)
                </option>
              ))}
              <option value="__custom__">Custom name...</option>
            </select>
          </label>
          {selectedOllama === "__custom__" && (
            <label className="grid gap-1.5 text-sm font-medium text-zinc-700">
              Model tag
              <input
                className="h-10 rounded-lg border border-zinc-300 px-3 text-zinc-950"
                placeholder="mistral:7b"
                value={customOllama}
                onChange={(e) => setCustomOllama(e.target.value)}
              />
            </label>
          )}
          <label className="grid gap-1.5 text-sm font-medium text-zinc-700">
            Display name
            <input
              className="h-10 rounded-lg border border-zinc-300 px-3 text-zinc-950"
              placeholder="Qwen 2.5 7B"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              required
            />
          </label>
          {errorMessage && (
            <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">
              {errorMessage}
            </p>
          )}
          <div className="flex gap-2">
            <Button
              className="h-10 rounded-lg bg-teal-700 px-4 text-sm font-semibold text-white hover:bg-teal-800"
              isDisabled={pulling}
              type="submit"
            >
              {pulling ? "Pulling..." : "Pull & Add"}
            </Button>
            <Link
              className="inline-flex h-10 items-center justify-center rounded-lg border border-zinc-300 px-4 text-sm font-medium hover:bg-zinc-50"
              to="/"
            >
              Cancel
            </Link>
          </div>
        </form>
      ) : (
        <form className="flex flex-col gap-4 rounded-lg border border-zinc-200 bg-white p-5" onSubmit={handleLitellmSubmit}>
          <label className="grid gap-1.5 text-sm font-medium text-zinc-700">
            Provider
            <select
              className="h-10 rounded-lg border border-zinc-300 px-3 text-zinc-950"
              value={litellmProvider}
              onChange={(e) => setLitellmProvider(e.target.value)}
            >
              {Object.entries(LITELLM_PROVIDERS).map(([k, v]) => (
                <option key={k} value={k}>{v.label}</option>
              ))}
            </select>
          </label>
          <label className="grid gap-1.5 text-sm font-medium text-zinc-700">
            Model ID
            <input
              className="h-10 rounded-lg border border-zinc-300 px-3 text-zinc-950 font-mono text-sm"
              value={litellmModelId}
              onChange={(e) => setLitellmModelId(e.target.value)}
              required
            />
          </label>
          <label className="grid gap-1.5 text-sm font-medium text-zinc-700">
            API Key
            <div className="flex gap-2">
              <input
                className="h-10 flex-1 rounded-lg border border-zinc-300 px-3 text-zinc-950 font-mono"
                type={showKey ? "text" : "password"}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                required
              />
              <button
                className="inline-flex h-10 items-center rounded-lg border border-zinc-300 px-3 text-xs font-medium hover:bg-zinc-50"
                onClick={(e) => { e.preventDefault(); setShowKey(!showKey); }}
                type="button"
              >
                {showKey ? "Hide" : "Show"}
              </button>
            </div>
          </label>
          <div className="flex items-center gap-3">
            <button
              className="inline-flex h-9 items-center rounded-lg border border-zinc-300 px-4 text-sm font-medium hover:bg-zinc-50 disabled:opacity-50"
              disabled={testing || !apiKey}
              onClick={(e) => { e.preventDefault(); handleTestKey(); }}
              type="button"
            >
              {testing ? "Testing..." : "Test Key"}
            </button>
            {keyTestResult && (
              <span className={`text-sm font-medium ${keyTestResult.ok ? "text-teal-700" : "text-rose-700"}`}>
                {keyTestResult.ok ? "✓" : "✗"} {keyTestResult.message}
              </span>
            )}
          </div>
          <label className="grid gap-1.5 text-sm font-medium text-zinc-700">
            Display name
            <input
              className="h-10 rounded-lg border border-zinc-300 px-3 text-zinc-950"
              placeholder="GPT-4o"
              value={litellmName}
              onChange={(e) => setLitellmName(e.target.value)}
              required
            />
          </label>
          {errorMessage && (
            <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">
              {errorMessage}
            </p>
          )}
          <div className="flex gap-2">
            <Button
              className="h-10 rounded-lg bg-teal-700 px-4 text-sm font-semibold text-white hover:bg-teal-800"
              isDisabled={isSubmitting}
              type="submit"
            >
              {isSubmitting ? "Adding..." : "Add Model"}
            </Button>
            <Link
              className="inline-flex h-10 items-center justify-center rounded-lg border border-zinc-300 px-4 text-sm font-medium hover:bg-zinc-50"
              to="/"
            >
              Cancel
            </Link>
          </div>
        </form>
      )}
    </AppLayout>
  );
}
