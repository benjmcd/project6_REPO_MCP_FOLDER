"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import {
  fetchDiagnostics,
  fetchDocuments,
  fetchExtractedUnits,
  fetchIndexedChunks,
  fetchNormalizedText,
  fetchRuns,
  fetchTraceManifest,
  readReviewApiBase,
  resolveApiUrl,
} from "@/lib/review-api";
import {
  formatBytes,
  formatDateTime,
  formatScalarValue,
  formatTitleCase,
} from "@/lib/display";
import type {
  ReviewDiagnostics,
  ReviewDocumentSelector,
  ReviewExtractedUnits,
  ReviewIndexedChunks,
  ReviewNormalizedText,
  ReviewRunSelector,
  ReviewTraceManifest,
} from "@/lib/review-types";
import {
  DetailGrid,
  EmptyState,
  JsonBlock,
  NoticeList,
  Panel,
  StatusBanner,
  SurfaceIntro,
  TabStrip,
  type SurfaceBadge,
} from "@/components/sandbox-primitives";

function normalizeError(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return "Unknown error.";
}

export function DocumentTraceShell() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const [runs, setRuns] = useState<ReviewRunSelector | null>(null);
  const [documents, setDocuments] = useState<ReviewDocumentSelector | null>(null);
  const [manifest, setManifest] = useState<ReviewTraceManifest | null>(null);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(() =>
    searchParams.get("run_id"),
  );
  const [selectedTargetId, setSelectedTargetId] = useState<string | null>(() =>
    searchParams.get("target_id"),
  );
  const [activeTabId, setActiveTabId] = useState<string>(() =>
    searchParams.get("tab") ?? "summary",
  );
  const [selectedPageNumber, setSelectedPageNumber] = useState<number | null>(() => {
    const raw = searchParams.get("page");
    if (!raw) {
      return null;
    }
    const parsed = Number(raw);
    return Number.isFinite(parsed) ? parsed : null;
  });
  const [diagnostics, setDiagnostics] = useState<ReviewDiagnostics | null>(null);
  const [normalizedText, setNormalizedText] = useState<ReviewNormalizedText | null>(
    null,
  );
  const [indexedChunks, setIndexedChunks] = useState<ReviewIndexedChunks | null>(null);
  const [extractedUnits, setExtractedUnits] = useState<ReviewExtractedUnits | null>(
    null,
  );
  const [isLoadingRuns, setIsLoadingRuns] = useState(true);
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(false);
  const [isLoadingManifest, setIsLoadingManifest] = useState(false);
  const [isLoadingTab, setIsLoadingTab] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const badges = useMemo<SurfaceBadge[]>(
    () => [
      {
        label: "API base",
        value: readReviewApiBase() ?? "Unconfigured",
        tone: readReviewApiBase() ? "accent" : "warning",
      },
      { label: "Runs", value: String(runs?.runs.length ?? 0), tone: "neutral" },
      {
        label: "Documents",
        value: String(documents?.documents.length ?? 0),
        tone: "neutral",
      },
      {
        label: "Trace tabs",
        value: String(manifest?.tabs.length ?? 0),
        tone: "neutral",
      },
    ],
    [documents?.documents.length, manifest?.tabs.length, runs?.runs.length],
  );

  useEffect(() => {
    const controller = new AbortController();
    let mounted = true;

    async function loadRuns() {
      setIsLoadingRuns(true);
      setErrorMessage(null);
      try {
        const data = await fetchRuns(controller.signal);
        if (!mounted) {
          return;
        }
        setRuns(data);
        setSelectedRunId((current) =>
          isValidRun(current, data)
            ? current
            : (searchParams.get("run_id") ??
                data.default_run_id ??
                data.runs.find((run) => run.reviewable)?.run_id ??
                null),
        );
      } catch (error) {
        if (!mounted || controller.signal.aborted) {
          return;
        }
        setErrorMessage(normalizeError(error));
      } finally {
        if (mounted) {
          setIsLoadingRuns(false);
        }
      }
    }

    void loadRuns();
    return () => {
      mounted = false;
      controller.abort();
    };
  }, [searchParams]);

  useEffect(() => {
    if (!selectedRunId) {
      setDocuments(null);
      setManifest(null);
      return;
    }
    const currentRunId = selectedRunId;

    const controller = new AbortController();
    let mounted = true;

    async function loadDocuments() {
      setIsLoadingDocuments(true);
      setErrorMessage(null);
      setManifest(null);
      resetTabCaches(setDiagnostics, setNormalizedText, setIndexedChunks, setExtractedUnits);

      try {
        const data = await fetchDocuments(currentRunId, controller.signal);
        if (!mounted) {
          return;
        }
        setDocuments(data);
        setSelectedTargetId((current) =>
          isValidTarget(current, data)
            ? current
            : (searchParams.get("target_id") ?? data.default_target_id),
        );
      } catch (error) {
        if (!mounted || controller.signal.aborted) {
          return;
        }
        setDocuments(null);
        setErrorMessage(normalizeError(error));
      } finally {
        if (mounted) {
          setIsLoadingDocuments(false);
        }
      }
    }

    void loadDocuments();
    return () => {
      mounted = false;
      controller.abort();
    };
  }, [searchParams, selectedRunId]);

  useEffect(() => {
    if (!selectedRunId || !selectedTargetId) {
      setManifest(null);
      return;
    }
    const currentRunId = selectedRunId;
    const currentTargetId = selectedTargetId;

    const controller = new AbortController();
    let mounted = true;

    async function loadManifest() {
      setIsLoadingManifest(true);
      setErrorMessage(null);
      resetTabCaches(setDiagnostics, setNormalizedText, setIndexedChunks, setExtractedUnits);

      try {
        const data = await fetchTraceManifest(
          currentRunId,
          currentTargetId,
          controller.signal,
        );
        if (!mounted) {
          return;
        }
        setManifest(data);
        setActiveTabId((current) => {
          const requested = searchParams.get("tab") ?? current;
          return data.tabs.some((tab) => tab.tab_id === requested && tab.available)
            ? requested
            : "summary";
        });
      } catch (error) {
        if (!mounted || controller.signal.aborted) {
          return;
        }
        setManifest(null);
        setErrorMessage(normalizeError(error));
      } finally {
        if (mounted) {
          setIsLoadingManifest(false);
        }
      }
    }

    void loadManifest();
    return () => {
      mounted = false;
      controller.abort();
    };
  }, [searchParams, selectedRunId, selectedTargetId]);

  useEffect(() => {
    if (!selectedRunId || !selectedTargetId) {
      return;
    }
    const currentRunId = selectedRunId;
    const currentTargetId = selectedTargetId;
    const currentTabId = activeTabId;

    const controller = new AbortController();
    let mounted = true;

    async function loadTabData() {
      if (currentTabId === "summary") {
        return;
      }

      setIsLoadingTab(true);
      setErrorMessage(null);

      try {
        if (currentTabId === "diagnostics" && !diagnostics) {
          const data = await fetchDiagnostics(
            currentRunId,
            currentTargetId,
            controller.signal,
          );
          if (mounted) {
            setDiagnostics(data);
          }
        }
        if (currentTabId === "normalized_text" && !normalizedText) {
          const data = await fetchNormalizedText(
            currentRunId,
            currentTargetId,
            controller.signal,
          );
          if (mounted) {
            setNormalizedText(data);
          }
        }
        if (currentTabId === "indexed_chunks" && !indexedChunks) {
          const data = await fetchIndexedChunks(
            currentRunId,
            currentTargetId,
            controller.signal,
          );
          if (mounted) {
            setIndexedChunks(data);
          }
        }
        if (
          currentTabId === "extracted_units" &&
          (!extractedUnits || extractedUnits.page_number !== selectedPageNumber)
        ) {
          const data = await fetchExtractedUnits(
            currentRunId,
            currentTargetId,
            selectedPageNumber ?? undefined,
            controller.signal,
          );
          if (mounted) {
            setExtractedUnits(data);
          }
        }
      } catch (error) {
        if (!mounted || controller.signal.aborted) {
          return;
        }
        setErrorMessage(normalizeError(error));
      } finally {
        if (mounted) {
          setIsLoadingTab(false);
        }
      }
    }

    void loadTabData();
    return () => {
      mounted = false;
      controller.abort();
    };
  }, [
    activeTabId,
    diagnostics,
    extractedUnits,
    indexedChunks,
    normalizedText,
    selectedPageNumber,
    selectedRunId,
    selectedTargetId,
  ]);

  function updateRouteParams(updates: Record<string, string | null>) {
    const next = new URLSearchParams(searchParams.toString());
    Object.entries(updates).forEach(([key, value]) => {
      if (value) {
        next.set(key, value);
      } else {
        next.delete(key);
      }
    });
    const query = next.toString();
    router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
  }

  const sourceHref = manifest?.source.source_endpoint
    ? resolveApiUrl(manifest.source.source_endpoint)
    : null;
  const availableTabs =
    manifest?.tabs.map((tab) => ({
      tabId: tab.tab_id,
      label: tab.label,
      disabled: !tab.available,
    })) ?? [];

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(14,165,233,0.14),_transparent_26%),linear-gradient(180deg,_#f7fafc_0%,_#eef4f8_100%)] text-slate-950">
      <div className="mx-auto flex w-full max-w-[1600px] flex-col gap-5 px-6 py-6">
        <SurfaceIntro
          title="Document Trace"
          detail="This sandbox route ports the trace surface into the Next-based Onlook lane. It keeps the live run and document selectors, lazily loads each trace tab, and preserves source and document artifact access without touching the shipped static page."
          badges={badges}
        >
          <div className="grid gap-3 md:grid-cols-2">
            <SelectorField
              label="Run"
              value={selectedRunId ?? ""}
              disabled={isLoadingRuns || !runs}
              options={(runs?.runs ?? []).map((run) => ({
                value: run.run_id,
                label: `${run.display_label ?? run.run_id} - ${formatDateTime(run.completed_at ?? run.submitted_at)}`,
              }))}
              onChange={(value) => {
                setSelectedRunId(value);
                setSelectedTargetId(null);
                setSelectedPageNumber(null);
                updateRouteParams({
                  run_id: value,
                  target_id: null,
                  page: null,
                });
              }}
            />
            <SelectorField
              label="Document"
              value={selectedTargetId ?? ""}
              disabled={isLoadingDocuments || !documents}
              options={(documents?.documents ?? []).map((document) => ({
                value: document.target_id,
                label: buildDocumentLabel(document),
              }))}
              onChange={(value) => {
                setSelectedTargetId(value);
                setSelectedPageNumber(null);
                updateRouteParams({
                  target_id: value,
                  page: null,
                });
              }}
            />
          </div>
        </SurfaceIntro>

        {errorMessage ? <StatusBanner message={errorMessage} tone="error" /> : null}
        {isLoadingRuns ? (
          <StatusBanner message="Loading review runs..." tone="info" />
        ) : null}
        {isLoadingDocuments ? (
          <StatusBanner message="Loading traceable documents for the selected run..." tone="info" />
        ) : null}
        {isLoadingManifest ? (
          <StatusBanner message="Loading trace manifest..." tone="info" />
        ) : null}

        {manifest ? (
          <>
            <div className="grid gap-5 xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
              <Panel
                title="Source Document"
                subtitle="Identity and source artifact metadata for the selected trace target."
              >
                <div className="flex flex-col gap-4">
                  <DetailGrid
                    items={[
                      {
                        label: "Document",
                        value: manifest.identity.document_title ?? "Unavailable",
                      },
                      {
                        label: "Type",
                        value: manifest.identity.document_type ?? "Unavailable",
                      },
                      {
                        label: "Media type",
                        value: manifest.identity.media_type ?? "Unavailable",
                      },
                      {
                        label: "Source file",
                        value: manifest.identity.source_file_name ?? "Unavailable",
                      },
                      {
                        label: "Accession",
                        value: manifest.identity.accession_number ?? "Unavailable",
                      },
                      {
                        label: "Content ID",
                        value: manifest.identity.content_id ?? "Unavailable",
                      },
                    ]}
                    columns={3}
                  />

                  <DetailGrid
                    items={[
                      {
                        label: "Viewer kind",
                        value: formatTitleCase(manifest.source.viewer_kind),
                      },
                      {
                        label: "Blob present",
                        value: formatScalarValue(manifest.source.blob_ref_present),
                      },
                      {
                        label: "Content type",
                        value: manifest.source.content_type ?? "Unavailable",
                      },
                      {
                        label: "File size",
                        value: formatBytes(manifest.source.size_bytes),
                      },
                      {
                        label: "Page geometries",
                        value: String(manifest.source.page_geometries.length),
                      },
                      {
                        label: "Source endpoint",
                        value: sourceHref ? "Available" : "Unavailable",
                      },
                    ]}
                    columns={3}
                  />

                  {manifest.source.page_geometries.length > 0 ? (
                    <DetailGrid
                      items={manifest.source.page_geometries.map((page) => ({
                        label: `Page ${page.page_number}`,
                        value: `${page.width} x ${page.height}`,
                      }))}
                      columns={4}
                    />
                  ) : null}

                  {sourceHref ? (
                    <div className="flex flex-col gap-3">
                      <div className="flex flex-wrap gap-3">
                        <a
                          href={sourceHref}
                          target="_blank"
                          rel="noreferrer"
                          className="rounded-full border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-slate-300 hover:bg-slate-100"
                        >
                          Open source artifact
                        </a>
                      </div>
                      <iframe
                        src={sourceHref}
                        title="Trace source artifact"
                        className="h-[52rem] w-full rounded-[1.5rem] border border-slate-200 bg-white"
                      />
                    </div>
                  ) : (
                    <EmptyState
                      title="No source artifact endpoint"
                      detail="The manifest did not expose a viewable source endpoint for this document."
                    />
                  )}
                </div>
              </Panel>

              <div className="grid gap-5">
                <NoticeList
                  title="Warnings"
                  items={manifest.warnings}
                  emptyMessage="No trace warnings were returned."
                />
                <NoticeList
                  title="Limitations"
                  items={manifest.limitations}
                  emptyMessage="No trace limitations were returned."
                />
              </div>
            </div>

            <Panel
              title="Trace Tabs"
              subtitle="The heavier live document-trace interactions are intentionally reduced here to an API-backed React shell so the sandbox lane stays maintainable."
              actions={
                <div className="flex flex-col gap-3">
                  <TabStrip
                    tabs={availableTabs}
                    activeTab={activeTabId}
                    onChange={(tabId) => {
                      setActiveTabId(tabId);
                      updateRouteParams({ tab: tabId });
                    }}
                  />
                  {activeTabId === "extracted_units" &&
                  manifest.source.page_geometries.length > 0 ? (
                    <SelectorField
                      label="Page filter"
                      value={selectedPageNumber ? String(selectedPageNumber) : ""}
                      disabled={false}
                      options={[
                        { value: "", label: "All pages" },
                        ...manifest.source.page_geometries.map((page) => ({
                          value: String(page.page_number),
                          label: `Page ${page.page_number}`,
                        })),
                      ]}
                      onChange={(value) => {
                        const nextValue = value ? Number(value) : null;
                        setSelectedPageNumber(Number.isFinite(nextValue) ? nextValue : null);
                        updateRouteParams({ page: value || null });
                      }}
                    />
                  ) : null}
                </div>
              }
            >
              {isLoadingTab ? (
                <StatusBanner message="Loading trace tab payload..." tone="info" />
              ) : null}
              <TraceTabContent
                activeTabId={activeTabId}
                manifest={manifest}
                diagnostics={diagnostics}
                normalizedText={normalizedText}
                indexedChunks={indexedChunks}
                extractedUnits={extractedUnits}
              />
            </Panel>
          </>
        ) : (
          <EmptyState
            title="Choose a run and document"
            detail="The document trace route needs both a review run and a traceable target document before the manifest can load."
          />
        )}
      </div>
    </main>
  );
}

function TraceTabContent({
  activeTabId,
  manifest,
  diagnostics,
  normalizedText,
  indexedChunks,
  extractedUnits,
}: {
  activeTabId: string;
  manifest: ReviewTraceManifest;
  diagnostics: ReviewDiagnostics | null;
  normalizedText: ReviewNormalizedText | null;
  indexedChunks: ReviewIndexedChunks | null;
  extractedUnits: ReviewExtractedUnits | null;
}) {
  if (activeTabId === "diagnostics") {
    if (!diagnostics) {
      return (
        <EmptyState
          title="Diagnostics not loaded"
          detail="The diagnostics endpoint has not returned yet."
        />
      );
    }

    return (
      <div className="flex flex-col gap-4">
        <DetailGrid
          items={[
            { label: "Available", value: formatScalarValue(diagnostics.available) },
            {
              label: "Quality status",
              value: diagnostics.quality_status ?? "Unavailable",
            },
            {
              label: "Document class",
              value: diagnostics.document_class ?? "Unavailable",
            },
            { label: "Page count", value: String(diagnostics.page_count) },
            {
              label: "Ordered units",
              value: String(diagnostics.ordered_unit_count),
            },
            {
              label: "Visual derivatives",
              value: String(diagnostics.visual_derivative_unit_count),
            },
          ]}
          columns={3}
        />
        <NoticeList
          title="Diagnostics warnings"
          items={diagnostics.warnings}
          emptyMessage="No diagnostics warnings were returned."
        />
        <DetailGrid
          items={Object.entries(diagnostics.unit_kind_counts).map(([key, value]) => ({
            label: key,
            value: String(value),
          }))}
          columns={4}
        />
        {diagnostics.extractor_metadata ? (
          <JsonBlock value={diagnostics.extractor_metadata} />
        ) : null}
      </div>
    );
  }

  if (activeTabId === "normalized_text") {
    if (!normalizedText) {
      return (
        <EmptyState
          title="Normalized text not loaded"
          detail="The normalized-text endpoint has not returned yet."
        />
      );
    }

    if (!normalizedText.available || !normalizedText.text) {
      return (
        <EmptyState
          title="Normalized text unavailable"
          detail="The backend marked normalized text as unavailable for this document."
        />
      );
    }

    return (
      <div className="flex flex-col gap-4">
        <DetailGrid
          items={[
            { label: "Characters", value: String(normalizedText.char_count) },
            {
              label: "Mapping precision",
              value: normalizedText.mapping_precision ?? "Unavailable",
            },
          ]}
          columns={2}
        />
        <pre className="overflow-x-auto rounded-2xl border border-slate-200 bg-slate-950 px-4 py-4 text-xs leading-6 text-slate-100">
          {normalizedText.text}
        </pre>
      </div>
    );
  }

  if (activeTabId === "indexed_chunks") {
    if (!indexedChunks) {
      return (
        <EmptyState
          title="Indexed chunks not loaded"
          detail="The indexed-chunks endpoint has not returned yet."
        />
      );
    }

    if (!indexedChunks.available || indexedChunks.chunks.length === 0) {
      return (
        <EmptyState
          title="Indexed chunks unavailable"
          detail="The backend did not return indexed chunks for this document."
        />
      );
    }

    return (
      <div className="flex flex-col gap-4">
        <DetailGrid
          items={[
            { label: "Chunk count", value: String(indexedChunks.chunk_count) },
            {
              label: "Mapping scope",
              value: formatScalarValue(
                indexedChunks.chunks.map((chunk) => chunk.mapping_precision),
              ),
            },
          ]}
          columns={2}
        />
        <div className="grid gap-4">
          {indexedChunks.chunks.map((chunk) => (
            <div
              key={chunk.chunk_id}
              className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4"
            >
              <div className="flex flex-wrap gap-2">
                <span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-700">
                  Chunk {chunk.chunk_ordinal}
                </span>
                <span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-700">
                  Pages {chunk.page_start ?? "?"}–{chunk.page_end ?? "?"}
                </span>
                <span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-700">
                  {chunk.unit_kind ?? "Unknown kind"}
                </span>
              </div>
              <div className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-700">
                {chunk.chunk_text}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (activeTabId === "extracted_units") {
    if (!extractedUnits) {
      return (
        <EmptyState
          title="Extracted units not loaded"
          detail="The extracted-units endpoint has not returned yet."
        />
      );
    }

    if (!extractedUnits.available) {
      return (
        <EmptyState
          title="Extracted units unavailable"
          detail={`The backend marked extracted units as unavailable${extractedUnits.reason_code ? ` (${extractedUnits.reason_code})` : ""}.`}
        />
      );
    }

    return (
      <div className="flex flex-col gap-4">
        <DetailGrid
          items={[
            {
              label: "Total units",
              value: String(extractedUnits.total_unit_count),
            },
            {
              label: "Source layer",
              value: formatTitleCase(extractedUnits.source_layer),
            },
            {
              label: "Precision",
              value: formatTitleCase(extractedUnits.source_precision),
            },
            {
              label: "Page scope",
              value: extractedUnits.page_number
                ? `Page ${extractedUnits.page_number}`
                : "All pages",
            },
          ]}
          columns={4}
        />

        {extractedUnits.visual_artifacts.length > 0 ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {extractedUnits.visual_artifacts.map((artifact) => (
              <div
                key={artifact.artifact_id}
                className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4"
              >
                <div className="text-sm font-semibold text-slate-900">
                  Artifact {artifact.artifact_id}
                </div>
                <div className="mt-2 space-y-1 text-sm text-slate-600">
                  <div>Page: {artifact.page_number ?? "Unknown"}</div>
                  <div>Status: {artifact.status ?? "Unknown"}</div>
                  <div>Format: {artifact.format ?? "Unknown"}</div>
                  <div>Semantics: {artifact.artifact_semantics ?? "Unknown"}</div>
                </div>
                {artifact.endpoint ? (
                  <a
                    href={resolveApiUrl(artifact.endpoint)}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-3 inline-flex rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-700 transition hover:border-slate-300 hover:bg-slate-100"
                  >
                    Open artifact
                  </a>
                ) : null}
              </div>
            ))}
          </div>
        ) : null}

        <div className="grid gap-4">
          {extractedUnits.units.map((unit) => (
            <div
              key={unit.unit_id}
              className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4"
            >
              <div className="flex flex-wrap gap-2">
                <span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-700">
                  {unit.unit_kind ?? "Unit"}
                </span>
                <span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-700">
                  Page {unit.page_number ?? "?"}
                </span>
                <span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-700">
                  Char {unit.start_char ?? "?"}–{unit.end_char ?? "?"}
                </span>
              </div>
              <div className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-700">
                {unit.text ?? "No extracted text."}
              </div>
              {unit.bbox ? (
                <div className="mt-3 text-xs text-slate-500">
                  Bounding box: {unit.bbox.join(", ")}
                </div>
              ) : null}
              {unit.provenance && Object.keys(unit.provenance).length > 0 ? (
                <div className="mt-3">
                  <JsonBlock value={unit.provenance} />
                </div>
              ) : null}
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <DetailGrid
        items={[
          {
            label: "Document class",
            value: manifest.summary.document_class ?? "Unavailable",
          },
          {
            label: "Quality status",
            value: manifest.summary.quality_status ?? "Unavailable",
          },
          {
            label: "Page count",
            value: String(manifest.summary.page_count),
          },
          {
            label: "Ordered units",
            value: String(manifest.summary.ordered_unit_count),
          },
          {
            label: "Indexed chunks",
            value: String(manifest.summary.indexed_chunk_count),
          },
          {
            label: "Visual refs",
            value: String(manifest.summary.visual_page_ref_count),
          },
        ]}
        columns={3}
      />
      <DetailGrid
        items={[
          {
            label: "Source → units",
            value: formatTitleCase(manifest.sync_capabilities.source_to_units),
          },
          {
            label: "Units → source",
            value: formatTitleCase(manifest.sync_capabilities.units_to_source),
          },
          {
            label: "Text → source",
            value: formatTitleCase(
              manifest.sync_capabilities.normalized_text_to_source,
            ),
          },
          {
            label: "Chunk → source",
            value: formatTitleCase(manifest.sync_capabilities.chunk_to_source),
          },
        ]}
        columns={4}
      />
      <DetailGrid
        items={[
          {
            label: "Has source blob",
            value: formatScalarValue(manifest.trace_completeness.has_source_blob),
          },
          {
            label: "Has diagnostics",
            value: formatScalarValue(manifest.trace_completeness.has_diagnostics),
          },
          {
            label: "Has normalized text",
            value: formatScalarValue(
              manifest.trace_completeness.has_normalized_text,
            ),
          },
          {
            label: "Has indexed chunks",
            value: formatScalarValue(
              manifest.trace_completeness.has_indexed_chunks,
            ),
          },
          {
            label: "Has downstream usage",
            value: formatScalarValue(
              manifest.trace_completeness.has_downstream_usage,
            ),
          },
          {
            label: "Retrieval available",
            value: formatScalarValue(
              manifest.trace_completeness.retrieval_available,
            ),
          },
        ]}
        columns={3}
      />
    </div>
  );
}

function SelectorField({
  label,
  value,
  options,
  disabled,
  onChange,
}: {
  label: string;
  value: string;
  options: Array<{ value: string; label: string }>;
  disabled: boolean;
  onChange: (value: string) => void;
}) {
  return (
    <label className="flex flex-col gap-2 text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
      {label}
      <select
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font-medium normal-case tracking-normal text-slate-800 outline-none transition focus:border-sky-300 disabled:cursor-not-allowed disabled:bg-slate-100"
      >
        {options.length === 0 ? (
          <option value="">Loading...</option>
        ) : null}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function buildDocumentLabel(
  document: ReviewDocumentSelector["documents"][number],
): string {
  const label = [
    document.document_title,
    document.accession_number,
    document.document_type,
  ]
    .filter(Boolean)
    .join(" - ");

  return label || document.target_id;
}

function isValidRun(
  value: string | null,
  runs: ReviewRunSelector,
): boolean {
  return Boolean(value && runs.runs.some((run) => run.run_id === value));
}

function isValidTarget(
  value: string | null,
  documents: ReviewDocumentSelector,
): boolean {
  return Boolean(
    value && documents.documents.some((document) => document.target_id === value),
  );
}

function resetTabCaches(
  setDiagnostics: (value: ReviewDiagnostics | null) => void,
  setNormalizedText: (value: ReviewNormalizedText | null) => void,
  setIndexedChunks: (value: ReviewIndexedChunks | null) => void,
  setExtractedUnits: (value: ReviewExtractedUnits | null) => void,
) {
  setDiagnostics(null);
  setNormalizedText(null);
  setIndexedChunks(null);
  setExtractedUnits(null);
}
