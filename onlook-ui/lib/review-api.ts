import type { ReviewOverview, ReviewRunSelector } from "@/lib/review-types";

function normalizeApiBase(rawBase: string | undefined): string | null {
  if (!rawBase) {
    return null;
  }

  return rawBase.replace(/\/+$/, "");
}

export function readReviewApiBase(): string | null {
  return normalizeApiBase(process.env.NEXT_PUBLIC_REVIEW_API_BASE);
}

export function isReviewApiConfigured(): boolean {
  return readReviewApiBase() !== null;
}

async function requestJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const apiBase = readReviewApiBase();
  if (!apiBase) {
    throw new Error("NEXT_PUBLIC_REVIEW_API_BASE is not set.");
  }

  const response = await fetch(`${apiBase}${path}`, {
    method: "GET",
    cache: "no-store",
    credentials: "omit",
    headers: {
      Accept: "application/json",
    },
    signal,
  });

  if (!response.ok) {
    throw new Error(`Review API request failed (${response.status}) for ${path}.`);
  }

  return (await response.json()) as T;
}

export function fetchRuns(signal?: AbortSignal): Promise<ReviewRunSelector> {
  return requestJson<ReviewRunSelector>("/runs", signal);
}

export function fetchOverview(
  runId: string,
  signal?: AbortSignal,
): Promise<ReviewOverview> {
  return requestJson<ReviewOverview>(
    `/runs/${encodeURIComponent(runId)}/overview`,
    signal,
  );
}
