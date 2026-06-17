import { apiRequest } from "./api";

export interface Dataset {
  id: string;
  project_id: string;
  name: string;
  type: string;
  original_filename: string;
  storage_path: string;
  metadata: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface DatasetCreatePayload {
  name: string;
  type: string;
  original_filename: string;
  storage_path: string;
  metadata?: Record<string, unknown> | null;
}

export function listDatasets(projectId: string) {
  return apiRequest<Dataset[]>(`/api/v1/projects/${projectId}/datasets`);
}

export function createDataset(projectId: string, payload: DatasetCreatePayload) {
  return apiRequest<Dataset>(`/api/v1/projects/${projectId}/datasets`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function deleteDataset(projectId: string, datasetId: string) {
  return apiRequest<void>(`/api/v1/projects/${projectId}/datasets/${datasetId}`, {
    method: "DELETE",
  });
}

export interface DatasetUpdatePayload {
  name?: string;
  type?: string;
  original_filename?: string;
  storage_path?: string;
  metadata?: Record<string, unknown> | null;
}

export function updateDataset(projectId: string, datasetId: string, payload: DatasetUpdatePayload) {
  return apiRequest<Dataset>(`/api/v1/projects/${projectId}/datasets/${datasetId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}
