"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import {
  fetchWorkbenchManifest,
  fetchWorkbenchSources,
  fetchWorkbenchTab,
  fetchWorkbenchTargets,
  readReviewApiBase,
  type WorkbenchSelection,
} from "@/lib/review-api";
import { formatScalarValue, formatTitleCase } from "@/lib/display";
import { remapLiveReviewPath } from "@/lib/sandbox-links";
import type {
  WorkbenchCompareColumn,
  WorkbenchCompareManifest,
  WorkbenchCompareSources,
  WorkbenchCompareTab,
  WorkbenchCompareTargets,
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

export function WorkbenchCompareShell() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const [sources, setSources] = useState<WorkbenchCompareSources | null>(null);
  const [targets, setTargets] = useState<WorkbenchCompareTargets | null>(null);
  const [manifest, setManifest] = useState<WorkbenchCompareManifest | null>(null);
  const [tabCache, setTabCache] = useState<Record<string, WorkbenchCompareTab>>({});
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
  const [isLoadingSources, setIsLoadingSources] = useState(true);
  const [isLoadingTargets, setIsLoadingTargets] = useState(false);
  const [isLoadingManifest, setIsLoadingManifest] = useState(false);
  const [isLoadingTab, setIsLoadingTab] = useState(false);
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
        label: "Fixtures",
        value: String(targets?.targets.length ?? 0),
        tone: "neutral",
      },
      {
        label: "Tabs",
        value: String(manifest?.tabs.length ?? 0),
        tone: "neutral",
      },
    ],
    [manifest?.tabs.length, targets?.targets.length],
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
        setSelectedBaselineRunId((current) =>
          isValidRun(current, data.baseline_runs)
            ? current
            : (searchParams.get("baseline_run_id") ?? data.default_baseline_run_id),
        );
        setSelectedCandidateARunId((current) =>
          isValidRun(current, data.candidate_a_runs)
            ? current
            : (searchParams.get("candidate_a_run_id") ??
                data.default_candidate_a_run_id),
        );
        setSelectedCandidateBBundleId((current) =>
          isValidBundle(current, data.candidate_b_bundles)
            ? current
            : (searchParams.get("candidate_b_bundle_id") ??
                data.default_candidate_b_bundle_id),
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
      setTabCache({});
      return;
    }
    const currentSelection: WorkbenchSelection = selection;

    const controller = new AbortController();
    let mounted = true;

    async function loadTargets() {
      setIsLoadingTargets(true);
      setErrorMessage(null);
      setManifest(null);
      setTabCache({});

      try {
        const data = await fetchWorkbenchTargets(
          currentSelection,
          controller.signal,
        );
        if (!mounted) {
          return;
        }

        setTargets(data);
        setSelectedFixtureId((current) =>
          isValidFixture(current, data.targets)
            ? current
            : (searchParams.get("fixture_id") ?? data.default_fixture_id),
        );
      } catch (error) {
        if (!mounted || controller.signal.aborted) {
          return;
        }
        setTargets(null);
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
    if (!selection || !selectedFixtureId) {
      setManifest(null);
      setTabCache({});
      return;
    }
    const currentSelection: WorkbenchSelection = selection;
    const currentFixtureId = selectedFixtureId;

    const controller = new AbortController();
    let mounted = true;

    async function loadManifest() {
      setIsLoadingManifest(true);
      setErrorMessage(null);
      setTabCache({});

      try {
        const data = await fetchWorkbenchManifest(
          currentSelection,
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
  }, [searchParams, selectedFixtureId, selection]);

  useEffect(() => {
    if (!selection || !selectedFixtureId || !manifest || !activeTabId) {
      return;
    }
    const currentSelection: WorkbenchSelection = selection;
    const currentFixtureId = selectedFixtureId;
    const currentTabId = activeTabId;

    if (tabCache[currentTabId]) {
      return;
    }

    const controller = new AbortController();
    let mounted = true;

    async function loadTab() {
      setIsLoadingTab(true);
      setErrorMessage(null);

      try {
        const data = await fetchWorkbenchTab(
          currentSelection,
          currentFixtureId,
          currentTabId,
          controller.signal,
        );
        if (!mounted) {
          return;
        }
        setTabCache((current) => ({ ...current, [currentTabId]: data }));
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

    void loadTab();
    return () => {
      mounted = false;
      controller.abort();
    };
  }, [activeTabId, manifest, selectedFixtureId, selection, tabCache]);

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

  const activeTab = tabCache[activeTabId] ?? null;

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(14,165,233,0.14),_transparent_26%),linear-gradient(180deg,_#f7fafc_0%,_#eef4f8_100%)] text-slate-950">
      <div className="mx-auto flex w-full max-w-[1600px] flex-col gap-5 px-6 py-6">
        <SurfaceIntro
          title="Workbench Compare"
          detail="This sandbox route ports the compare workbench into the Next-based Onlook lane. It keeps the same selection model and tabbed compare payloads while remapping deep links back into the sandbox routes."
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
          <StatusBanner message="Loading compare source options..." tone="info" />
        ) : null}
        {isLoadingTargets ? (
          <StatusBanner message="Loading aligned fixture targets..." tone="info" />
        ) : null}
        {isLoadingManifest ? (
          <StatusBanner message="Loading compare manifest..." tone="info" />
        ) : null}

        {manifest ? (
          <>
            <div className="grid gap-5 xl:grid-cols-[minmax(0,1.2fr)_minmax(24rem,0.8fr)]">
              <Panel
                title="Selection Context"
                subtitle="Identity, variant bindings, and deep links for the currently selected compare fixture."
              >
                <div className="flex flex-col gap-4">
                  <DetailGrid
                    items={[
                      {
                        label: "Fixture",
                        value: manifest.source_identity.fixture_id,
                      },
                      {
                        label: "Document",
                        value: manifest.source_identity.document_title ?? "Unavailable",
                      },
                      {
                        label: "Type",
                        value: manifest.source_identity.document_type ?? "Unavailable",
                      },
                      {
                        label: "Source file",
                        value:
                          manifest.source_identity.source_file_name ?? "Unavailable",
                      },
                      {
                        label: "Accession",
                        value:
                          manifest.source_identity.accession_number ?? "Unavailable",
                      },
                      {
                        label: "Document ref",
                        value: manifest.source_identity.document_ref ?? "Unavailable",
                      },
                    ]}
                    columns={3}
                  />

                  <div className="flex flex-wrap gap-2">
                    {manifest.summary_badges.map((badge) => (
                      <span
                        key={badge.key}
                        className={`rounded-full border px-3 py-1 text-xs font-medium ${compareBadgeClass(
                          badge.severity,
                        )}`}
                      >
                        {badge.label}: {badge.value}
                      </span>
                    ))}
                  </div>

                  <DetailGrid
                    items={[
                      {
                        label: "Baseline target",
                        value: manifest.variant_bindings.baseline.target_id,
                      },
                      {
                        label: "Candidate A target",
                        value: manifest.variant_bindings.candidate_a.target_id,
                      },
                      {
                        label: "Candidate B bundle",
                        value: manifest.variant_bindings.candidate_b.bundle_id,
                      },
                      {
                        label: "Baseline run",
                        value: manifest.variant_bindings.baseline.run_id,
                      },
                      {
                        label: "Candidate A run",
                        value: manifest.variant_bindings.candidate_a.run_id,
                      },
                      {
                        label: "Candidate B run",
                        value:
                          manifest.variant_bindings.candidate_b.candidate_b_run_id ??
                          "Unavailable",
                      },
                    ]}
                    columns={3}
                  />

                  <div className="flex flex-wrap gap-3">
                    <DeepLinkChip
                      label="Baseline trace"
                      href={remapLiveReviewPath(manifest.deep_links.baseline_trace)}
                    />
                    <DeepLinkChip
                      label="Candidate A trace"
                      href={remapLiveReviewPath(
                        manifest.deep_links.candidate_a_trace,
                      )}
                    />
                    <DeepLinkChip
                      label="Candidate B trace"
                      href={remapLiveReviewPath(
                        manifest.deep_links.candidate_b_trace,
                      )}
                    />
                  </div>
                </div>
              </Panel>

              <div className="grid gap-5">
                <NoticeList
                  title="Warnings"
                  items={manifest.warnings}
                  emptyMessage="No compare warnings were returned for this fixture."
                />
                <NoticeList
                  title="Limitations"
                  items={manifest.limitations}
                  emptyMessage="No compare limitations were returned for this fixture."
                />
              </div>
            </div>

            <Panel
              title="Compare Tabs"
              subtitle="Each tab is loaded from the same compare endpoints used by the live static workbench."
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
              <div className="flex flex-col gap-4">
                {isLoadingTab && !activeTab ? (
                  <StatusBanner message="Loading compare tab payload..." tone="info" />
                ) : null}
                {activeTab ? <CompareTabContent tab={activeTab} /> : null}
              </div>
            </Panel>
          </>
        ) : (
          <EmptyState
            title="Choose a complete compare selection"
            detail="The workbench compare route needs baseline, candidate A, candidate B, and fixture selections before the compare manifest can load."
          />
        )}
      </div>
    </main>
  );
}

function CompareTabContent({ tab }: { tab: WorkbenchCompareTab }) {
  const legendEntries = Object.entries(tab.comparability_legend);
  const columns = Object.values(tab.columns);

  return (
    <div className="flex flex-col gap-4">
      {legendEntries.length > 0 ? (
        <DetailGrid
          items={legendEntries.map(([key, value]) => ({
            label: key,
            value,
          }))}
          columns={4}
        />
      ) : null}

      {tab.warnings.length > 0 || tab.limitations.length > 0 ? (
        <div className="grid gap-4 xl:grid-cols-2">
          <NoticeList
            title="Tab warnings"
            items={tab.warnings}
            emptyMessage="No tab warnings were returned."
          />
          <NoticeList
            title="Tab limitations"
            items={tab.limitations}
            emptyMessage="No tab limitations were returned."
          />
        </div>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-3">
        {columns.map((column) => (
          <Panel
            key={`${column.variant_id}-${column.label}`}
            title={column.label}
            subtitle={`${formatTitleCase(column.variant_id)} - ${formatTitleCase(column.comparability_class)}`}
          >
            <CompareColumnContent column={column} />
          </Panel>
        ))}
      </div>
    </div>
  );
}

function CompareColumnContent({ column }: { column: WorkbenchCompareColumn }) {
  if (!column.available) {
    return (
      <EmptyState
        title="Column unavailable"
        detail="The compare API marked this variant as unavailable for the active fixture."
      />
    );
  }

  const entries = Object.entries(column.data);
  const scalarEntries = entries.filter(([, value]) => isScalarish(value));
  const complexEntries = entries.filter(([, value]) => !isScalarish(value));

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap gap-2">
        <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-700">
          State: {formatTitleCase(column.comparability_class)}
        </span>
        {column.deep_link ? (
          <Link
            href={remapLiveReviewPath(column.deep_link) ?? column.deep_link}
            className="rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-xs font-medium text-sky-700 transition hover:border-sky-300 hover:bg-sky-100"
          >
            Open deep link
          </Link>
        ) : null}
      </div>

      {scalarEntries.length > 0 ? (
        <DetailGrid
          items={scalarEntries.map(([key, value]) => ({
            label: key,
            value: formatScalarValue(value),
          }))}
          columns={2}
        />
      ) : null}

      {complexEntries.map(([key, value]) => (
        <div key={key} className="flex flex-col gap-2">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
            {key}
          </div>
          <JsonBlock value={value} />
        </div>
      ))}

      {column.warnings.length > 0 ? (
        <NoticeList
          title="Column warnings"
          items={column.warnings}
          emptyMessage="No column warnings."
        />
      ) : null}
      {column.limitations.length > 0 ? (
        <NoticeList
          title="Column limitations"
          items={column.limitations}
          emptyMessage="No column limitations."
        />
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

function DeepLinkChip({ label, href }: { label: string; href: string | null }) {
  if (!href) {
    return (
      <span className="rounded-full border border-slate-200 bg-slate-100 px-3 py-1 text-xs font-medium text-slate-500">
        {label}: unavailable
      </span>
    );
  }

  return (
    <Link
      href={href}
      className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-700 transition hover:border-slate-300 hover:bg-slate-100"
    >
      {label}
    </Link>
  );
}

function compareBadgeClass(severity: string): string {
  if (severity === "success") {
    return "border-emerald-200 bg-emerald-50 text-emerald-800";
  }
  if (severity === "warning") {
    return "border-amber-200 bg-amber-50 text-amber-800";
  }
  return "border-slate-200 bg-slate-100 text-slate-700";
}

function isValidRun(
  value: string | null,
  items: WorkbenchCompareSources["baseline_runs"],
): boolean {
  return Boolean(value && items.some((item) => item.run_id === value));
}

function isValidBundle(
  value: string | null,
  items: WorkbenchCompareSources["candidate_b_bundles"],
): boolean {
  return Boolean(value && items.some((item) => item.bundle_id === value));
}

function isValidFixture(
  value: string | null,
  items: WorkbenchCompareTargets["targets"],
): boolean {
  return Boolean(value && items.some((item) => item.fixture_id === value));
}

function isScalarish(value: unknown): boolean {
  if (
    value === null ||
    value === undefined ||
    typeof value === "string" ||
    typeof value === "number" ||
    typeof value === "boolean"
  ) {
    return true;
  }

  if (Array.isArray(value)) {
    return value.every(
      (item) =>
        item === null ||
        typeof item === "string" ||
        typeof item === "number" ||
        typeof item === "boolean",
    );
  }

  return false;
}
