import type {
  AnalystInsightRequest,
  AnalystIntegrationRequest,
  AnalystValidationRequest,
  CandidateBTraceManifest,
  ReviewDiagnostics,
  ReviewDocumentSelector,
  ReviewExtractedUnits,
  ReviewIndexedChunks,
  ReviewNormalizedText,
  ReviewOverview,
  ReviewRunSelector,
  ReviewTraceManifest,
  WorkbenchCompareManifest,
  WorkbenchCompareSources,
  WorkbenchCompareTab,
  WorkbenchCompareTargets,
} from "@/lib/review-types";

function normalizeApiBase(rawBase: string | undefined): string | null {
  if (!rawBase) {
    return null;
  }

  return rawBase.replace(/\/+$/, "");
}

export function readReviewApiBase(): string | null {
  return normalizeApiBase(process.env.NEXT_PUBLIC_REVIEW_API_BASE);
}

export function readApiV1Base(): string | null {
  const reviewBase = readReviewApiBase();
  if (!reviewBase) {
    return null;
  }

  return reviewBase.replace(/\/review\/nrc-aps$/, "");
}

export function readApiOrigin(): string | null {
  const apiBase = readApiV1Base();
  if (!apiBase) {
    return null;
  }

  try {
    return new URL(apiBase).origin;
  } catch {
    return null;
  }
}

export function isReviewApiConfigured(): boolean {
  return readReviewApiBase() !== null;
}

type RequestOptions = {
  signal?: AbortSignal;
  method?: "GET" | "POST";
  body?: string;
  headers?: HeadersInit;
};

async function requestJson<T>(
  basePath: string,
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  if (!basePath) {
    throw new Error("Required API base is not configured.");
  }

  const response = await fetch(`${basePath}${path}`, {
    method: options.method ?? "GET",
    cache: "no-store",
    credentials: "omit",
    headers: {
      Accept: "application/json",
      ...options.headers,
    },
    body: options.body,
    signal: options.signal,
  });

  if (!response.ok) {
    throw new Error(`Review API request failed (${response.status}) for ${path}.`);
  }

  return (await response.json()) as T;
}

async function requestReviewJson<T>(
  path: string,
  signal?: AbortSignal,
): Promise<T> {
  const apiBase = readReviewApiBase();
  if (!apiBase) {
    throw new Error("NEXT_PUBLIC_REVIEW_API_BASE is not set.");
  }

  return requestJson<T>(apiBase, path, { signal });
}

async function requestApiV1Json<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const apiBase = readApiV1Base();
  if (!apiBase) {
    throw new Error("NEXT_PUBLIC_REVIEW_API_BASE is not set.");
  }

  return requestJson<T>(apiBase, path, options);
}

async function requestAbsoluteJson<T>(
  url: string,
  signal?: AbortSignal,
): Promise<T> {
  const response = await fetch(resolveApiUrl(url), {
    method: "GET",
    cache: "no-store",
    credentials: "omit",
    headers: {
      Accept: "application/json",
    },
    signal,
  });

  if (!response.ok) {
    throw new Error(`Artifact request failed (${response.status}) for ${url}.`);
  }

  return (await response.json()) as T;
}

async function requestAbsoluteText(
  url: string,
  signal?: AbortSignal,
): Promise<string> {
  const response = await fetch(resolveApiUrl(url), {
    method: "GET",
    cache: "no-store",
    credentials: "omit",
    headers: {
      Accept: "text/plain, text/markdown;q=0.9, */*;q=0.1",
    },
    signal,
  });

  if (!response.ok) {
    throw new Error(`Artifact request failed (${response.status}) for ${url}.`);
  }

  return response.text();
}

export function resolveApiUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) {
    return path;
  }

  const apiOrigin = readApiOrigin();
  if (apiOrigin) {
    return new URL(path, apiOrigin).toString();
  }

  if (typeof window !== "undefined") {
    return new URL(path, window.location.origin).toString();
  }

  return path;
}

export function fetchRuns(signal?: AbortSignal): Promise<ReviewRunSelector> {
  return requestReviewJson<ReviewRunSelector>("/runs", signal);
}

export function fetchOverview(
  runId: string,
  signal?: AbortSignal,
): Promise<ReviewOverview> {
  return requestReviewJson<ReviewOverview>(
    `/runs/${encodeURIComponent(runId)}/overview`,
    signal,
  );
}

export function fetchDocuments(
  runId: string,
  signal?: AbortSignal,
): Promise<ReviewDocumentSelector> {
  return requestReviewJson<ReviewDocumentSelector>(
    `/runs/${encodeURIComponent(runId)}/documents`,
    signal,
  );
}

export function fetchTraceManifest(
  runId: string,
  targetId: string,
  signal?: AbortSignal,
): Promise<ReviewTraceManifest> {
  return requestReviewJson<ReviewTraceManifest>(
    `/runs/${encodeURIComponent(runId)}/documents/${encodeURIComponent(targetId)}/trace`,
    signal,
  );
}

export function fetchDiagnostics(
  runId: string,
  targetId: string,
  signal?: AbortSignal,
): Promise<ReviewDiagnostics> {
  return requestReviewJson<ReviewDiagnostics>(
    `/runs/${encodeURIComponent(runId)}/documents/${encodeURIComponent(targetId)}/diagnostics`,
    signal,
  );
}

export function fetchNormalizedText(
  runId: string,
  targetId: string,
  signal?: AbortSignal,
): Promise<ReviewNormalizedText> {
  return requestReviewJson<ReviewNormalizedText>(
    `/runs/${encodeURIComponent(runId)}/documents/${encodeURIComponent(targetId)}/normalized-text`,
    signal,
  );
}

export function fetchIndexedChunks(
  runId: string,
  targetId: string,
  signal?: AbortSignal,
): Promise<ReviewIndexedChunks> {
  return requestReviewJson<ReviewIndexedChunks>(
    `/runs/${encodeURIComponent(runId)}/documents/${encodeURIComponent(targetId)}/indexed-chunks`,
    signal,
  );
}

export function fetchExtractedUnits(
  runId: string,
  targetId: string,
  pageNumber?: number,
  signal?: AbortSignal,
): Promise<ReviewExtractedUnits> {
  const params = new URLSearchParams();
  if (typeof pageNumber === "number") {
    params.set("page_number", String(pageNumber));
  }
  const suffix = params.size > 0 ? `?${params.toString()}` : "";
  return requestReviewJson<ReviewExtractedUnits>(
    `/runs/${encodeURIComponent(runId)}/documents/${encodeURIComponent(targetId)}/extracted-units${suffix}`,
    signal,
  );
}

export function fetchWorkbenchSources(
  signal?: AbortSignal,
): Promise<WorkbenchCompareSources> {
  return requestReviewJson<WorkbenchCompareSources>(
    "/workbench-compare/sources",
    signal,
  );
}

export type WorkbenchSelection = {
  baselineRunId: string;
  candidateARunId: string;
  candidateBBundleId: string;
};

function buildWorkbenchParams(selection: WorkbenchSelection): string {
  const params = new URLSearchParams({
    baseline_run_id: selection.baselineRunId,
    candidate_a_run_id: selection.candidateARunId,
    candidate_b_bundle_id: selection.candidateBBundleId,
  });
  return params.toString();
}

export function fetchWorkbenchTargets(
  selection: WorkbenchSelection,
  signal?: AbortSignal,
): Promise<WorkbenchCompareTargets> {
  return requestReviewJson<WorkbenchCompareTargets>(
    `/workbench-compare/targets?${buildWorkbenchParams(selection)}`,
    signal,
  );
}

export function fetchWorkbenchManifest(
  selection: WorkbenchSelection,
  fixtureId: string,
  signal?: AbortSignal,
): Promise<WorkbenchCompareManifest> {
  return requestReviewJson<WorkbenchCompareManifest>(
    `/workbench-compare/targets/${encodeURIComponent(fixtureId)}/manifest?${buildWorkbenchParams(selection)}`,
    signal,
  );
}

export function fetchWorkbenchTab(
  selection: WorkbenchSelection,
  fixtureId: string,
  tabId: string,
  signal?: AbortSignal,
): Promise<WorkbenchCompareTab> {
  return requestReviewJson<WorkbenchCompareTab>(
    `/workbench-compare/targets/${encodeURIComponent(fixtureId)}/tabs/${encodeURIComponent(tabId)}?${buildWorkbenchParams(selection)}`,
    signal,
  );
}

export function fetchCandidateBManifest(
  bundleId: string,
  fixtureId: string,
  signal?: AbortSignal,
): Promise<CandidateBTraceManifest> {
  const params = new URLSearchParams({
    candidate_b_bundle_id: bundleId,
    fixture_id: fixtureId,
  });
  return requestReviewJson<CandidateBTraceManifest>(
    `/candidate-b-trace/manifest?${params.toString()}`,
    signal,
  );
}

export function fetchArtifactJson<T>(
  url: string,
  signal?: AbortSignal,
): Promise<T> {
  return requestAbsoluteJson<T>(url, signal);
}

export function fetchArtifactText(
  url: string,
  signal?: AbortSignal,
): Promise<string> {
  return requestAbsoluteText(url, signal);
}

export function postAnalystIntegration(
  body: AnalystIntegrationRequest,
  signal?: AbortSignal,
): Promise<Record<string, unknown>> {
  return requestApiV1Json<Record<string, unknown>>(
    "/analyst-insight/integration/cross-reference",
    {
      method: "POST",
      signal,
      body: JSON.stringify(body),
      headers: {
        "Content-Type": "application/json",
      },
    },
  );
}

export function postAnalystValidation(
  body: AnalystValidationRequest,
  signal?: AbortSignal,
): Promise<Record<string, unknown>> {
  return requestApiV1Json<Record<string, unknown>>(
    "/analyst-insight/validation/run",
    {
      method: "POST",
      signal,
      body: JSON.stringify(body),
      headers: {
        "Content-Type": "application/json",
      },
    },
  );
}

export function postAnalystInsight(
  body: AnalystInsightRequest,
  signal?: AbortSignal,
): Promise<Record<string, unknown>> {
  return requestApiV1Json<Record<string, unknown>>(
    "/analyst-insight/insights/process",
    {
      method: "POST",
      signal,
      body: JSON.stringify(body),
      headers: {
        "Content-Type": "application/json",
      },
    },
  );
}
