import { apiRequest } from "./api";

export interface ModelConfig {
  id: string;
  name: string;
  provider: "ollama" | "litellm";
  model_id: string;
  is_active: boolean;
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

export function testApiKey(provider: string, modelId: string, apiKey: string) {
  return apiRequest<{ ok: boolean; model: string }>("/api/v1/models/test-key", {
    method: "POST",
    body: JSON.stringify({ provider, model_id: modelId, api_key: apiKey }),
  });
}
