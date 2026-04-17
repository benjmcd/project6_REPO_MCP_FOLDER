import fs from "node:fs/promises";
import path from "node:path";

import type { NextRequest } from "next/server";

type BinaryPayload = {
  content_type: string;
  relative_path: string;
};

type FixtureShape = {
  review: {
    runs: unknown;
    overviews: Record<string, unknown>;
    documents: Record<string, unknown>;
    traces: Record<string, unknown>;
    diagnostics: Record<string, unknown>;
    normalized_text: Record<string, unknown>;
    indexed_chunks: Record<string, unknown>;
    extracted_units: Record<string, unknown>;
    source_blobs: Record<string, BinaryPayload | null>;
  };
  workbench: {
    selection_key: string;
    sources: unknown;
    targets: Record<string, unknown>;
    manifests: Record<string, unknown>;
    tabs: Record<string, unknown>;
  };
  candidate_b: {
    manifests: Record<string, unknown>;
    raw_json: Record<string, unknown>;
    raw_markdown: Record<string, string>;
    annotated_pdf: Record<string, BinaryPayload>;
  };
  analyst: {
    integration: unknown;
    validation: unknown;
    insight: unknown;
  };
};

export const runtime = "nodejs";

let fixtureCache: FixtureShape | null = null;

async function getFixtureData(): Promise<FixtureShape> {
  if (fixtureCache) {
    return fixtureCache;
  }

  const fixturePath = path.join(process.cwd(), "data", "fixture.json");
  const raw = await fs.readFile(fixturePath, "utf8");
  fixtureCache = JSON.parse(raw) as FixtureShape;
  return fixtureCache;
}

function jsonResponse(body: unknown, status = 200): Response {
  return Response.json(body, {
    status,
    headers: {
      "Cache-Control": "no-store",
    },
  });
}

function textResponse(body: string, status = 200): Response {
  return new Response(body, {
    status,
    headers: {
      "Cache-Control": "no-store",
      "Content-Type": "text/plain; charset=utf-8",
    },
  });
}

async function binaryResponse(payload: BinaryPayload): Promise<Response> {
  const dataRoot = path.join(process.cwd(), "data");
  const absolutePath = path.resolve(dataRoot, payload.relative_path);
  const relativeToRoot = path.relative(dataRoot, absolutePath);

  if (relativeToRoot.startsWith("..") || path.isAbsolute(relativeToRoot)) {
    return notFound(`Binary fixture escapes the sandbox data root: ${payload.relative_path}.`);
  }

  const fileBytes = await fs.readFile(absolutePath);

  return new Response(fileBytes, {
    status: 200,
    headers: {
      "Cache-Control": "no-store",
      "Content-Type": payload.content_type,
    },
  });
}

function documentKey(runId: string, targetId: string): string {
  return `${runId}::${targetId}`;
}

function unitsKey(
  runId: string,
  targetId: string,
  pageNumber: string | null,
): string {
  return `${runId}::${targetId}::${pageNumber ?? "all"}`;
}

function selectionKey(
  data: FixtureShape,
  baselineRunId: string | null,
  candidateARunId: string | null,
  candidateBBundleId: string | null,
): string {
  if (!baselineRunId || !candidateARunId || !candidateBBundleId) {
    return data.workbench.selection_key;
  }

  return `${baselineRunId}::${candidateARunId}::${candidateBBundleId}`;
}

function workbenchKey(selection: string, fixtureId: string): string {
  return `${selection}::${fixtureId}`;
}

function workbenchTabKey(
  selection: string,
  fixtureId: string,
  tabId: string,
): string {
  return `${selection}::${fixtureId}::${tabId}`;
}

function bundleKey(bundleId: string, fixtureId: string): string {
  return `${bundleId}::${fixtureId}`;
}

function notFound(message: string): Response {
  return jsonResponse({ detail: message }, 404);
}

function badRequest(message: string): Response {
  return jsonResponse({ detail: message }, 400);
}

async function handleReviewGet(
  request: NextRequest,
  rest: string[],
): Promise<Response> {
  const data = await getFixtureData();

  if (rest.length === 1 && rest[0] === "runs") {
    return jsonResponse(data.review.runs);
  }

  if (
    rest.length === 3 &&
    rest[0] === "runs" &&
    rest[2] === "overview"
  ) {
    const overview = data.review.overviews[rest[1]];
    return overview
      ? jsonResponse(overview)
      : notFound(`Missing overview fixture for run ${rest[1]}.`);
  }

  if (
    rest.length === 3 &&
    rest[0] === "runs" &&
    rest[2] === "documents"
  ) {
    const documents = data.review.documents[rest[1]];
    return documents
      ? jsonResponse(documents)
      : notFound(`Missing document fixture for run ${rest[1]}.`);
  }

  if (
    rest.length === 5 &&
    rest[0] === "runs" &&
    rest[2] === "documents"
  ) {
    const runId = rest[1];
    const targetId = rest[3];
    const action = rest[4];
    const docId = documentKey(runId, targetId);

    switch (action) {
      case "trace": {
        const trace = data.review.traces[docId];
        return trace
          ? jsonResponse(trace)
          : notFound(`Missing trace fixture for ${docId}.`);
      }
      case "diagnostics": {
        const diagnostics = data.review.diagnostics[docId];
        return diagnostics
          ? jsonResponse(diagnostics)
          : notFound(`Missing diagnostics fixture for ${docId}.`);
      }
      case "normalized-text": {
        const normalized = data.review.normalized_text[docId];
        return normalized
          ? jsonResponse(normalized)
          : notFound(`Missing normalized-text fixture for ${docId}.`);
      }
      case "indexed-chunks": {
        const indexed = data.review.indexed_chunks[docId];
        return indexed
          ? jsonResponse(indexed)
          : notFound(`Missing indexed-chunks fixture for ${docId}.`);
      }
      case "source": {
        const source = data.review.source_blobs[docId];
        return source
          ? await binaryResponse(source)
          : notFound(`Missing source fixture for ${docId}.`);
      }
      case "extracted-units": {
        const pageNumber = request.nextUrl.searchParams.get("page_number");
        const payload = data.review.extracted_units[unitsKey(runId, targetId, pageNumber)];
        return payload
          ? jsonResponse(payload)
          : notFound(
              `Missing extracted-units fixture for ${runId}/${targetId}/${pageNumber ?? "all"}.`,
            );
      }
      default:
        return notFound("Unsupported document fixture route.");
    }
  }

  if (rest.length === 2 && rest[0] === "workbench-compare" && rest[1] === "sources") {
    return jsonResponse(data.workbench.sources);
  }

  if (rest.length === 2 && rest[0] === "workbench-compare" && rest[1] === "targets") {
    const key = selectionKey(
      data,
      request.nextUrl.searchParams.get("baseline_run_id"),
      request.nextUrl.searchParams.get("candidate_a_run_id"),
      request.nextUrl.searchParams.get("candidate_b_bundle_id"),
    );
    const targets = data.workbench.targets[key];
    return targets
      ? jsonResponse(targets)
      : notFound(`Missing workbench targets fixture for ${key}.`);
  }

  if (
    rest.length === 4 &&
    rest[0] === "workbench-compare" &&
    rest[1] === "targets" &&
    rest[3] === "manifest"
  ) {
    const selection = selectionKey(
      data,
      request.nextUrl.searchParams.get("baseline_run_id"),
      request.nextUrl.searchParams.get("candidate_a_run_id"),
      request.nextUrl.searchParams.get("candidate_b_bundle_id"),
    );
    const manifest = data.workbench.manifests[workbenchKey(selection, rest[2])];
    return manifest
      ? jsonResponse(manifest)
      : notFound(`Missing workbench manifest fixture for ${selection}/${rest[2]}.`);
  }

  if (
    rest.length === 5 &&
    rest[0] === "workbench-compare" &&
    rest[1] === "targets" &&
    rest[3] === "tabs"
  ) {
    const selection = selectionKey(
      data,
      request.nextUrl.searchParams.get("baseline_run_id"),
      request.nextUrl.searchParams.get("candidate_a_run_id"),
      request.nextUrl.searchParams.get("candidate_b_bundle_id"),
    );
    const tab = data.workbench.tabs[workbenchTabKey(selection, rest[2], rest[4])];
    return tab
      ? jsonResponse(tab)
      : notFound(`Missing workbench tab fixture for ${selection}/${rest[2]}/${rest[4]}.`);
  }

  if (
    rest.length === 2 &&
    rest[0] === "candidate-b-trace" &&
    rest[1] === "manifest"
  ) {
    const bundleId = request.nextUrl.searchParams.get("candidate_b_bundle_id");
    const fixtureId = request.nextUrl.searchParams.get("fixture_id");
    if (!bundleId || !fixtureId) {
      return badRequest("candidate_b_bundle_id and fixture_id are required.");
    }
    const manifest = data.candidate_b.manifests[bundleKey(bundleId, fixtureId)];
    return manifest
      ? jsonResponse(manifest)
      : notFound(`Missing Candidate-B manifest fixture for ${bundleId}/${fixtureId}.`);
  }

  if (
    rest.length === 2 &&
    rest[0] === "candidate-b-trace" &&
    ["raw-json", "raw-markdown", "annotated-pdf"].includes(rest[1])
  ) {
    const bundleId = request.nextUrl.searchParams.get("candidate_b_bundle_id");
    const fixtureId = request.nextUrl.searchParams.get("fixture_id");
    if (!bundleId || !fixtureId) {
      return badRequest("candidate_b_bundle_id and fixture_id are required.");
    }
    const key = bundleKey(bundleId, fixtureId);

    if (rest[1] === "raw-json") {
      const payload = data.candidate_b.raw_json[key];
      return payload
        ? jsonResponse(payload)
        : notFound(`Missing Candidate-B raw JSON fixture for ${bundleId}/${fixtureId}.`);
    }
    if (rest[1] === "raw-markdown") {
      const payload = data.candidate_b.raw_markdown[key];
      return typeof payload === "string"
        ? textResponse(payload)
        : notFound(`Missing Candidate-B raw Markdown fixture for ${bundleId}/${fixtureId}.`);
    }

    const payload = data.candidate_b.annotated_pdf[key];
    return payload
      ? await binaryResponse(payload)
      : notFound(`Missing Candidate-B PDF fixture for ${bundleId}/${fixtureId}.`);
  }

  return notFound("Unsupported fixture GET route.");
}

async function handleAnalystPost(rest: string[]): Promise<Response> {
  const data = await getFixtureData();

  if (rest.length === 2 && rest[0] === "integration" && rest[1] === "cross-reference") {
    return jsonResponse(data.analyst.integration);
  }

  if (rest.length === 2 && rest[0] === "validation" && rest[1] === "run") {
    return jsonResponse(data.analyst.validation);
  }

  if (rest.length === 2 && rest[0] === "insights" && rest[1] === "process") {
    return jsonResponse(data.analyst.insight);
  }

  return notFound("Unsupported analyst fixture POST route.");
}

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ slug: string[] }> },
): Promise<Response> {
  const { slug } = await context.params;
  if (slug.length < 3 || slug[0] !== "v1") {
    return notFound("Unsupported fixture API path.");
  }

  if (slug[1] === "review" && slug[2] === "nrc-aps") {
    return handleReviewGet(request, slug.slice(3));
  }

  return notFound("Unsupported fixture API path.");
}

export async function POST(
  _request: NextRequest,
  context: { params: Promise<{ slug: string[] }> },
): Promise<Response> {
  const { slug } = await context.params;
  if (slug.length < 2 || slug[0] !== "v1") {
    return notFound("Unsupported fixture API path.");
  }

  if (slug[1] === "analyst-insight") {
    return handleAnalystPost(slug.slice(2));
  }

  return notFound("Unsupported fixture API path.");
}
