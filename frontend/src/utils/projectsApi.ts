import { apiRequest } from "./api";

export interface Project {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreatePayload {
  name: string;
  description?: string | null;
}

export interface ProjectUpdatePayload {
  name?: string;
  description?: string | null;
}

export function listProjects() {
  return apiRequest<Project[]>("/api/v1/projects");
}

export function createProject(payload: ProjectCreatePayload) {
  return apiRequest<Project>("/api/v1/projects", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getProject(projectId: string) {
  return apiRequest<Project>(`/api/v1/projects/${projectId}`);
}

export function updateProject(projectId: string, payload: ProjectUpdatePayload) {
  return apiRequest<Project>(`/api/v1/projects/${projectId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}
