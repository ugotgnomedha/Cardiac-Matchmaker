import { apiRequest } from "./api";

export interface AnalysisRun {
  id: string;
  project_id: string;
  status: string;
  query: string;
  target_application: string;
  target_tissue: string;
  constraints: Record<string, unknown> | null;
  started_at: string | null;
  finished_at: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface AnalysisStep {
  id: string;
  analysis_run_id: string;
  sequence_number: number;
  step_name: string;
  status: string;
  input_snapshot: Record<string, unknown> | null;
  output_snapshot: Record<string, unknown> | null;
  started_at: string | null;
  finished_at: string | null;
  error_message: string | null;
  created_at: string;
}

export interface EvidenceItem {
  id: string;
  analysis_run_id: string;
  candidate_match_id: string | null;
  candidate_name: string;
  claim: string;
  document_id: string | null;
  document_chunk_id: string | null;
  support_label: string;
  score: number | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface Report {
  id: string;
  analysis_run_id: string;
  status: string;
  json_body: Record<string, unknown> | null;
  markdown_body: string | null;
  storage_path: string | null;
  created_at: string;
  updated_at: string;
}

export interface RunCreatePayload {
  target_application: string;
  target_tissue: string;
  query: string;
  constraints?: Record<string, unknown> | null;
}

export function createRun(projectId: string, payload: RunCreatePayload) {
  return apiRequest<AnalysisRun>(`/api/v1/projects/${projectId}/runs`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listProjectRuns(projectId: string) {
  return apiRequest<AnalysisRun[]>(`/api/v1/projects/${projectId}/runs`);
}

export function getRun(runId: string) {
  return apiRequest<AnalysisRun>(`/api/v1/runs/${runId}`);
}

export function listRunSteps(runId: string) {
  return apiRequest<AnalysisStep[]>(`/api/v1/runs/${runId}/steps`);
}

export function listRunEvidence(runId: string) {
  return apiRequest<EvidenceItem[]>(`/api/v1/runs/${runId}/evidence`);
}

export function getRunReport(runId: string) {
  return apiRequest<Report>(`/api/v1/runs/${runId}/report`);
}
