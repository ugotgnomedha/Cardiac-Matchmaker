import { apiRequest } from "./api";

export interface ModelConfig {
  id: string;
  name: string;
  provider: "ollama" | "litellm";
  model_id: string;
  is_active: boolean;
  status: string;
  metadata_: Record<string, unknown> | null;
  created_at: string;
}

export interface OllamaModel {
  name: string;
  modified_at: string;
  size: number;
}

export interface ModelCreatePayload {
  name: string;
  provider: "ollama" | "litellm";
  model_id: string;
  api_key?: string;
}

export function listModels() {
  return apiRequest<ModelConfig[]>("/api/v1/models");
}

export function addModel(payload: ModelCreatePayload) {
  return apiRequest<ModelConfig>("/api/v1/models", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function deleteModel(modelId: string) {
  return apiRequest<void>(`/api/v1/models/${modelId}`, { method: "DELETE" });
}

export function listOllamaModels() {
  return apiRequest<{ models: OllamaModel[] }>("/api/v1/models/ollama/list");
}

export function pullOllamaModel(name: string) {
  return apiRequest<unknown>("/api/v1/models/ollama/pull", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export interface PullProgress {
  status: string;
  digest?: string;
  total?: number;
  completed?: number;
  error?: string;
}

export function pullOllamaModelStream(
  name: string,
  onProgress: (data: PullProgress) => void,
  onError: (error: string) => void,
  onComplete: () => void,
): AbortController {
  const controller = new AbortController();
  const url = `${import.meta.env.VITE_API_URL || "http://localhost:8000"}/api/v1/models/ollama/pull/stream`;

  fetch(url, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        onError(`HTTP ${response.status}`);
        return;
      }
      const reader = response.body?.getReader();
      if (!reader) {
        onError("No response body");
        return;
      }
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.error) {
                onError(data.error);
                return;
              }
              if (data.status === "success") {
                onComplete();
                return;
              }
              onProgress(data);
            } catch {
              // skip malformed lines
            }
          }
        }
      }
      onComplete();
    })
    .catch((err) => {
      if (err.name !== "AbortError") {
        onError(String(err));
      }
    });

  return controller;
}

export function testApiKey(provider: string, modelId: string, apiKey: string) {
  return apiRequest<{ ok: boolean; model: string }>("/api/v1/models/test-key", {
    method: "POST",
    body: JSON.stringify({ provider, model_id: modelId, api_key: apiKey }),
  });
}
