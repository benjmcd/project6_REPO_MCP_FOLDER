export function remapLiveReviewPath(rawPath: string | null | undefined): string | null {
  if (!rawPath) {
    return null;
  }

  const parsed = safeParseUrl(rawPath);
  if (!parsed) {
    return rawPath;
  }

  const path = parsed.pathname;
  if (path === "/review/nrc-aps") {
    return parsed.search ? `/${parsed.search}` : "/";
  }
  if (path === "/review/nrc-aps/document-trace") {
    return `/document-trace${parsed.search}`;
  }
  if (path === "/review/nrc-aps/workbench-compare") {
    return `/workbench-compare${parsed.search}`;
  }
  if (path === "/review/nrc-aps/candidate-b-trace") {
    return `/candidate-b-trace${parsed.search}`;
  }
  if (path === "/review/analyst-insight") {
    return `/analyst-insight${parsed.search}`;
  }

  return rawPath;
}

function safeParseUrl(value: string): URL | null {
  try {
    if (/^https?:\/\//i.test(value)) {
      return new URL(value);
    }

    return new URL(value, "https://sandbox.local");
  } catch {
    return null;
  }
}
