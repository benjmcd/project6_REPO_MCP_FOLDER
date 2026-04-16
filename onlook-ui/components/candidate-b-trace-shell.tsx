"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import {
  fetchArtifactJson,
  fetchArtifactText,
  fetchCandidateBManifest,
  fetchWorkbenchSources,
  fetchWorkbenchTargets,
  readReviewApiBase,
  resolveApiUrl,
  type WorkbenchSelection,
} from "@/lib/review-api";
import { formatScalarValue } from "@/lib/display";
import type {
  CandidateBTraceManifest,
  WorkbenchCompareSources,
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

export function CandidateBTraceShell() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const [sources, setSources] = useState<WorkbenchCompareSources | null>(null);
  const [targets, setTargets] = useState<{
    default_fixture_id: string | null;
    targets: Array<{ fixture_id: string; display_label: string }>;
  } | null>(null);
  const [manifest, setManifest] = useState<CandidateBTraceManifest | null>(null);
  const [selectedBaselineRunId, setSelectedBaselineRunId] = useState<string | null>(
    () => searchParams.get("baseline_run_id"),
  );
  const [selectedCandidateARunId, setSelectedCandidateARunId] = useState<
    string | null
  >(() => searchParams.get("candidate_a_run_id"));
  const [selectedCandidateBBundleId, setSelectedCandidateBBundleId] = useState<
    string | null
  >(() => searchParams.get("candidate_b_bundle_id"));
  const [selectedFixtureId, setSelectedFixtureId] = useState<string | null>(() =>
    searchParams.get("fixture_id"),
  );
  const [activeTabId, setActiveTabId] = useState<string>(() =>
    searchParams.get("tab") ?? "summary",
  );
  const [rawJson, setRawJson] = useState<unknown | null>(null);
  const [rawMarkdown, setRawMarkdown] = useState<string | null>(null);
  const [isLoadingSources, setIsLoadingSources] = useState(true);
  const [isLoadingTargets, setIsLoadingTargets] = useState(false);
  const [isLoadingManifest, setIsLoadingManifest] = useState(false);
  const [isLoadingArtifact, setIsLoadingArtifact] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const selection = useMemo<WorkbenchSelection | null>(() => {
    if (
      !selectedBaselineRunId ||
      !selectedCandidateARunId ||
      !selectedCandidateBBundleId
    ) {
      return null;
    }

    return {
      baselineRunId: selectedBaselineRunId,
      candidateARunId: selectedCandidateARunId,
      candidateBBundleId: selectedCandidateBBundleId,
    };
  }, [selectedBaselineRunId, selectedCandidateARunId, selectedCandidateBBundleId]);

  const badges = useMemo<SurfaceBadge[]>(
    () => [
      {
        label: "API base",
        value: readReviewApiBase() ?? "Unconfigured",
        tone: readReviewApiBase() ? "accent" : "warning",
      },
      {
        label: "Bundle",
        value: selectedCandidateBBundleId ?? "Unselected",
        tone: "neutral",
      },
      {
        label: "Artifacts",
        value: manifest
          ? String(
              [
                manifest.artifacts.annotated_pdf,
                manifest.artifacts.raw_json,
                manifest.artifacts.raw_markdown,
              ].filter(Boolean).length,
            )
          : "0",
        tone: "neutral",
      },
    ],
    [manifest, selectedCandidateBBundleId],
  );

  useEffect(() => {
    const controller = new AbortController();
    let mounted = true;

    async function loadSources() {
      setIsLoadingSources(true);
      setErrorMessage(null);
      try {
        const data = await fetchWorkbenchSources(controller.signal);
        if (!mounted) {
          return;
        }
        setSources(data);
        setSelectedBaselineRunId(
          searchParams.get("baseline_run_id") ?? data.default_baseline_run_id,
        );
        setSelectedCandidateARunId(
          searchParams.get("candidate_a_run_id") ?? data.default_candidate_a_run_id,
        );
        setSelectedCandidateBBundleId(
          searchParams.get("candidate_b_bundle_id") ??
            data.default_candidate_b_bundle_id,
        );
      } catch (error) {
        if (!mounted || controller.signal.aborted) {
          return;
        }
        setErrorMessage(normalizeError(error));
      } finally {
        if (mounted) {
          setIsLoadingSources(false);
        }
      }
    }

    void loadSources();
    return () => {
      mounted = false;
      controller.abort();
    };
  }, [searchParams]);

  useEffect(() => {
    if (!selection) {
      setTargets(null);
      setManifest(null);
      return;
    }
    const currentSelection: WorkbenchSelection = selection;

    const controller = new AbortController();
    let mounted = true;

    async function loadTargets() {
      setIsLoadingTargets(true);
      setErrorMessage(null);
      setManifest(null);
      try {
        const data = await fetchWorkbenchTargets(
          currentSelection,
          controller.signal,
        );
        if (!mounted) {
          return;
        }
        setTargets({
          default_fixture_id: data.default_fixture_id,
          targets: data.targets.map((target) => ({
            fixture_id: target.fixture_id,
            display_label: target.display_label,
          })),
        });
        setSelectedFixtureId(
          searchParams.get("fixture_id") ?? data.default_fixture_id,
        );
      } catch (error) {
        if (!mounted || controller.signal.aborted) {
          return;
        }
        setErrorMessage(normalizeError(error));
      } finally {
        if (mounted) {
          setIsLoadingTargets(false);
        }
      }
    }

    void loadTargets();
    return () => {
      mounted = false;
      controller.abort();
    };
  }, [searchParams, selection]);

  useEffect(() => {
    if (!selectedCandidateBBundleId || !selectedFixtureId) {
      setManifest(null);
      return;
    }
    const currentBundleId = selectedCandidateBBundleId;
    const currentFixtureId = selectedFixtureId;

    const controller = new AbortController();
    let mounted = true;

    async function loadManifest() {
      setIsLoadingManifest(true);
      setErrorMessage(null);
      setRawJson(null);
      setRawMarkdown(null);
      try {
        const data = await fetchCandidateBManifest(
          currentBundleId,
          currentFixtureId,
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
            : data.default_tab;
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
  }, [searchParams, selectedCandidateBBundleId, selectedFixtureId]);

  useEffect(() => {
    if (!manifest) {
      return;
    }
    const currentManifest = manifest;

    const controller = new AbortController();
    let mounted = true;

    async function loadArtifact() {
      if (
        activeTabId === "raw_json" &&
        currentManifest.artifacts.raw_json &&
        rawJson === null
      ) {
        setIsLoadingArtifact(true);
        try {
          const payload = await fetchArtifactJson<unknown>(
            currentManifest.artifacts.raw_json,
            controller.signal,
          );
          if (mounted) {
            setRawJson(payload);
          }
        } catch (error) {
          if (mounted && !controller.signal.aborted) {
            setErrorMessage(normalizeError(error));
          }
        } finally {
          if (mounted) {
            setIsLoadingArtifact(false);
          }
        }
      }

      if (
        activeTabId === "raw_markdown" &&
        currentManifest.artifacts.raw_markdown &&
        rawMarkdown === null
      ) {
        setIsLoadingArtifact(true);
        try {
          const payload = await fetchArtifactText(
            currentManifest.artifacts.raw_markdown,
            controller.signal,
          );
          if (mounted) {
            setRawMarkdown(payload);
          }
        } catch (error) {
          if (mounted && !controller.signal.aborted) {
            setErrorMessage(normalizeError(error));
          }
        } finally {
          if (mounted) {
            setIsLoadingArtifact(false);
          }
        }
      }
    }

    void loadArtifact();
    return () => {
      mounted = false;
      controller.abort();
    };
  }, [activeTabId, manifest, rawJson, rawMarkdown]);

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

  const compareHref =
    selection && selectedFixtureId
      ? `/workbench-compare?baseline_run_id=${encodeURIComponent(
          selection.baselineRunId,
        )}&candidate_a_run_id=${encodeURIComponent(
          selection.candidateARunId,
        )}&candidate_b_bundle_id=${encodeURIComponent(
          selection.candidateBBundleId,
        )}&fixture_id=${encodeURIComponent(selectedFixtureId)}`
      : "/workbench-compare";

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(14,165,233,0.14),_transparent_26%),linear-gradient(180deg,_#f7fafc_0%,_#eef4f8_100%)] text-slate-950">
      <div className="mx-auto flex w-full max-w-[1600px] flex-col gap-5 px-6 py-6">
        <SurfaceIntro
          title="Candidate B Trace"
          detail="This sandbox route ports the live candidate-B trace page while keeping artifact access, summary payloads, and compare-family selector state inside the Next-based Onlook lane."
          badges={badges}
        >
          <div className="grid gap-3 md:grid-cols-2">
            <SelectorField
              label="Baseline"
              value={selectedBaselineRunId ?? ""}
              disabled={isLoadingSources || !sources}
              options={(sources?.baseline_runs ?? []).map((run) => ({
                value: run.run_id,
                label: run.display_label,
              }))}
              onChange={(value) => {
                setSelectedBaselineRunId(value);
                setSelectedFixtureId(null);
                updateRouteParams({
                  baseline_run_id: value,
                  fixture_id: null,
                });
              }}
            />
            <SelectorField
              label="Candidate A"
              value={selectedCandidateARunId ?? ""}
              disabled={isLoadingSources || !sources}
              options={(sources?.candidate_a_runs ?? []).map((run) => ({
                value: run.run_id,
                label: run.display_label,
              }))}
              onChange={(value) => {
                setSelectedCandidateARunId(value);
                setSelectedFixtureId(null);
                updateRouteParams({
                  candidate_a_run_id: value,
                  fixture_id: null,
                });
              }}
            />
            <SelectorField
              label="Candidate B"
              value={selectedCandidateBBundleId ?? ""}
              disabled={isLoadingSources || !sources}
              options={(sources?.candidate_b_bundles ?? []).map((bundle) => ({
                value: bundle.bundle_id,
                label: bundle.display_label,
              }))}
              onChange={(value) => {
                setSelectedCandidateBBundleId(value);
                setSelectedFixtureId(null);
                updateRouteParams({
                  candidate_b_bundle_id: value,
                  fixture_id: null,
                });
              }}
            />
            <SelectorField
              label="Fixture"
              value={selectedFixtureId ?? ""}
              disabled={isLoadingTargets || !targets}
              options={(targets?.targets ?? []).map((target) => ({
                value: target.fixture_id,
                label: target.display_label,
              }))}
              onChange={(value) => {
                setSelectedFixtureId(value);
                updateRouteParams({ fixture_id: value });
              }}
            />
          </div>
        </SurfaceIntro>

        {errorMessage ? <StatusBanner message={errorMessage} tone="error" /> : null}
        {isLoadingSources ? (
          <StatusBanner message="Loading candidate-B bundle sources..." tone="info" />
        ) : null}
        {isLoadingTargets ? (
          <StatusBanner message="Loading aligned fixtures..." tone="info" />
        ) : null}
        {isLoadingManifest ? (
          <StatusBanner message="Loading candidate-B manifest..." tone="info" />
        ) : null}

        {manifest ? (
          <>
            <div className="grid gap-5 xl:grid-cols-[minmax(0,1.2fr)_minmax(24rem,0.8fr)]">
              <Panel
                title="Selection Context"
                subtitle="Candidate-B identity, summary roll-up, and a direct path back to compare."
                actions={
                  <Link
                    href={compareHref}
                    className="rounded-full border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-slate-300 hover:bg-slate-100"
                  >
                    Back to compare
                  </Link>
                }
              >
                <div className="flex flex-col gap-4">
                  <DetailGrid
                    items={[
                      { label: "Fixture", value: manifest.identity.fixture_id },
                      { label: "Bundle", value: manifest.identity.bundle_id },
                      {
                        label: "Candidate B run",
                        value:
                          manifest.identity.candidate_b_run_id ?? "Unavailable",
                      },
                      {
                        label: "Document",
                        value: manifest.identity.document_title ?? "Unavailable",
                      },
                      {
                        label: "Source file",
                        value: manifest.identity.source_file_name ?? "Unavailable",
                      },
                      {
                        label: "Document ref",
                        value: manifest.identity.document_ref ?? "Unavailable",
                      },
                    ]}
                    columns={3}
                  />

                  <DetailGrid
                    items={[
                      {
                        label: "Processing",
                        value:
                          manifest.summary.processing_status ?? "Unavailable",
                      },
                      {
                        label: "Decision",
                        value:
                          manifest.summary.decision_recommendation ?? "Unavailable",
                      },
                      {
                        label: "Annotated PDF",
                        value:
                          manifest.summary.annotated_pdf_status ?? "Unavailable",
                      },
                      {
                        label: "Page count",
                        value: formatScalarValue(manifest.summary.page_count),
                      },
                      {
                        label: "Normalized chars",
                        value: formatScalarValue(
                          manifest.summary.normalized_char_count,
                        ),
                      },
                      {
                        label: "Structure",
                        value: manifest.summary.struct_tree_state ?? "Unavailable",
                      },
                    ]}
                    columns={3}
                  />
                </div>
              </Panel>

              <div className="grid gap-5">
                <NoticeList
                  title="Warnings"
                  items={manifest.warnings}
                  emptyMessage="No candidate-B warnings were returned."
                />
                <NoticeList
                  title="Limitations"
                  items={manifest.limitations}
                  emptyMessage="No candidate-B limitations were returned."
                />
              </div>
            </div>

            <Panel
              title="Trace Tabs"
              subtitle="The manifest chooses the default tab, but all artifact-backed tabs remain accessible within the sandbox lane."
              actions={
                <TabStrip
                  tabs={manifest.tabs.map((tab) => ({
                    tabId: tab.tab_id,
                    label: tab.label,
                    disabled: !tab.available,
                  }))}
                  activeTab={activeTabId}
                  onChange={(tabId) => {
                    setActiveTabId(tabId);
                    updateRouteParams({ tab: tabId });
                  }}
                />
              }
            >
              {isLoadingArtifact ? (
                <StatusBanner message="Loading candidate-B artifact..." tone="info" />
              ) : null}
              <CandidateBTabContent
                manifest={manifest}
                activeTabId={activeTabId}
                rawJson={rawJson}
                rawMarkdown={rawMarkdown}
              />
            </Panel>
          </>
        ) : (
          <EmptyState
            title="Choose a candidate-B selection"
            detail="The candidate-B route needs a baseline, candidate A, candidate B bundle, and fixture selection before the manifest can load."
          />
        )}
      </div>
    </main>
  );
}

function CandidateBTabContent({
  manifest,
  activeTabId,
  rawJson,
  rawMarkdown,
}: {
  manifest: CandidateBTraceManifest;
  activeTabId: string;
  rawJson: unknown | null;
  rawMarkdown: string | null;
}) {
  if (activeTabId === "annotated_pdf") {
    if (!manifest.artifacts.annotated_pdf) {
      return (
        <EmptyState
          title="Annotated PDF unavailable"
          detail="This fixture did not return an annotated PDF artifact endpoint."
        />
      );
    }

    const href = resolveApiUrl(manifest.artifacts.annotated_pdf);
    return (
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap gap-3">
          <a
            href={href}
            target="_blank"
            rel="noreferrer"
            className="rounded-full border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-slate-300 hover:bg-slate-100"
          >
            Open annotated PDF
          </a>
        </div>
        <iframe
          src={href}
          title="Candidate B Annotated PDF"
          className="h-[70vh] w-full rounded-[1.5rem] border border-slate-200 bg-white"
        />
      </div>
    );
  }

  if (activeTabId === "raw_json") {
    if (!manifest.artifacts.raw_json) {
      return (
        <EmptyState
          title="Raw JSON unavailable"
          detail="This fixture did not return a raw JSON artifact endpoint."
        />
      );
    }

    return rawJson ? (
      <div className="flex flex-col gap-3">
        <a
          href={resolveApiUrl(manifest.artifacts.raw_json)}
          target="_blank"
          rel="noreferrer"
          className="rounded-full border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-slate-300 hover:bg-slate-100"
        >
          Open raw JSON
        </a>
        <JsonBlock value={rawJson} />
      </div>
    ) : (
      <EmptyState
        title="Raw JSON loading"
        detail="The artifact endpoint has not returned yet."
      />
    );
  }

  if (activeTabId === "raw_markdown") {
    if (!manifest.artifacts.raw_markdown) {
      return (
        <EmptyState
          title="Raw Markdown unavailable"
          detail="This fixture did not return a raw Markdown artifact endpoint."
        />
      );
    }

    return rawMarkdown ? (
      <div className="flex flex-col gap-3">
        <a
          href={resolveApiUrl(manifest.artifacts.raw_markdown)}
          target="_blank"
          rel="noreferrer"
          className="rounded-full border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-slate-300 hover:bg-slate-100"
        >
          Open raw Markdown
        </a>
        <pre className="overflow-x-auto rounded-2xl border border-slate-200 bg-slate-950 px-4 py-4 text-xs leading-6 text-slate-100">
          {rawMarkdown}
        </pre>
      </div>
    ) : (
      <EmptyState
        title="Raw Markdown loading"
        detail="The artifact endpoint has not returned yet."
      />
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <DetailGrid
        items={[
          {
            label: "Processing status",
            value: manifest.summary.processing_status ?? "Unavailable",
          },
          {
            label: "Decision recommendation",
            value:
              manifest.summary.decision_recommendation ?? "Unavailable",
          },
          {
            label: "Page count",
            value: formatScalarValue(manifest.summary.page_count),
          },
          {
            label: "Heading count",
            value: formatScalarValue(manifest.summary.heading_count),
          },
          {
            label: "List count",
            value: formatScalarValue(manifest.summary.list_count),
          },
          {
            label: "Image count",
            value: formatScalarValue(manifest.summary.image_count),
          },
          {
            label: "Table count",
            value: formatScalarValue(manifest.summary.table_count),
          },
          {
            label: "Hidden text",
            value: formatScalarValue(manifest.summary.hidden_text_present),
          },
          {
            label: "Footer page numbers",
            value: formatScalarValue(manifest.summary.footer_page_numbers),
          },
          {
            label: "Image sources",
            value: formatScalarValue(manifest.summary.image_sources),
          },
          {
            label: "Expected gain claims",
            value: formatScalarValue(manifest.summary.expected_gain_claims),
          },
          {
            label: "Expected non-equivalences",
            value: formatScalarValue(
              manifest.summary.expected_non_equivalences,
            ),
          },
        ]}
        columns={3}
      />
      {manifest.summary.review_notes ? (
        <Panel title="Review Notes">
          <div className="text-sm leading-7 text-slate-700">
            {manifest.summary.review_notes}
          </div>
        </Panel>
      ) : null}
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
