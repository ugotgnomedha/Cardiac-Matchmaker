import { apiRequest } from "./api";

export interface LiteratureDocument {
  id: string;
  project_id: string;
  title: string;
  original_filename: string;
  storage_path: string;
  status: string;
  metadata: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentCreatePayload {
  title: string;
  original_filename: string;
  storage_path: string;
  status?: string;
  metadata?: Record<string, unknown> | null;
}

export function listDocuments(projectId: string) {
  return apiRequest<LiteratureDocument[]>(
    `/api/v1/projects/${projectId}/documents`,
  );
}

export function createDocument(
  projectId: string,
  payload: DocumentCreatePayload,
) {
  return apiRequest<LiteratureDocument>(
    `/api/v1/projects/${projectId}/documents`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}
