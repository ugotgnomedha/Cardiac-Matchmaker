const DEFAULT_API_URL = "http://localhost:8000";
const configuredApiUrl = import.meta.env.VITE_API_URL?.trim();

const API_BASE_URL = (
  configuredApiUrl && configuredApiUrl.length > 0
    ? configuredApiUrl
    : DEFAULT_API_URL
).replace(/\/$/, "");

export class ApiError extends Error {
  status: number;
  payload: unknown;

  constructor(status: number, message: string, payload: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

function buildUrl(path: string) {
  if (/^https?:\/\//.test(path)) {
    return path;
  }

  return `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

async function parseResponse(response: Response) {
  if (response.status === 204) {
    return undefined;
  }

  const contentType = response.headers.get("content-type") ?? "";

  if (contentType.includes("application/json")) {
    return response.json();
  }

  const text = await response.text();
  return text.length > 0 ? text : undefined;
}

function getErrorMessage(payload: unknown, fallbackMessage: string) {
  if (typeof payload === "string" && payload.length > 0) {
    return payload;
  }

  if (payload && typeof payload === "object") {
    const detail =
      "detail" in payload
        ? payload.detail
        : "message" in payload
          ? payload.message
          : null;

    if (typeof detail === "string" && detail.length > 0) {
      return detail;
    }
  }

  return fallbackMessage || "Request failed";
}

export async function apiRequest<ResponseData = unknown>(
  path: string,
  init?: RequestInit,
) {
  const headers = new Headers(init?.headers);

  if (typeof init?.body === "string" && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(buildUrl(path), {
    credentials: "include",
    ...init,
    headers,
  });

  const payload = await parseResponse(response);

  if (!response.ok) {
    throw new ApiError(
      response.status,
      getErrorMessage(payload, response.statusText),
      payload,
    );
  }

  return payload as ResponseData;
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}
