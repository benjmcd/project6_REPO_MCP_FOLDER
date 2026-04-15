"use client";

import { startTransition, useEffect, useState } from "react";

import { DetailsPane } from "@/components/details-pane";
import { HeaderBar } from "@/components/header-bar";
import { PipelinePane } from "@/components/pipeline-pane";
import { TreePane } from "@/components/tree-pane";
import {
  fetchOverview,
  fetchRuns,
  isReviewApiConfigured,
  readReviewApiBase,
} from "@/lib/review-api";
import type { ReviewOverview, ReviewRunSelector } from "@/lib/review-types";

function normalizeError(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return "Unknown error.";
}

export function ReviewShell() {
  const [runSelector, setRunSelector] = useState<ReviewRunSelector | null>(null);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [overview, setOverview] = useState<ReviewOverview | null>(null);
  const [selectedProjectionId, setSelectedProjectionId] = useState<string | null>(
    null,
  );
  const [selectedTreeId, setSelectedTreeId] = useState<string | null>(null);
  const [isRunsLoading, setIsRunsLoading] = useState(true);
  const [isOverviewLoading, setIsOverviewLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!isReviewApiConfigured()) {
      setErrorMessage("NEXT_PUBLIC_REVIEW_API_BASE is not set.");
      setIsRunsLoading(false);
      return;
    }

    const controller = new AbortController();
    let mounted = true;

    async function loadRuns() {
      setIsRunsLoading(true);
      setErrorMessage(null);

      try {
        const data = await fetchRuns(controller.signal);
        if (!mounted) {
          return;
        }
        setRunSelector(data);
        const firstReviewableRun =
          data.runs.find((run) => run.reviewable)?.run_id ?? null;
        const nextRunId = data.default_run_id ?? firstReviewableRun;
        setSelectedRunId((current) => {
          if (
            current &&
            data.runs.some((run) => run.run_id === current && run.reviewable)
          ) {
            return current;
          }
          return nextRunId;
        });
      } catch (error) {
        if (!mounted || controller.signal.aborted) {
          return;
        }
        setErrorMessage(normalizeError(error));
      } finally {
        if (mounted) {
          setIsRunsLoading(false);
        }
      }
    }

    void loadRuns();

    return () => {
      mounted = false;
      controller.abort();
    };
  }, []);

  useEffect(() => {
    if (!selectedRunId) {
      setOverview(null);
      return;
    }

    const runId = selectedRunId;
    const controller = new AbortController();
    let mounted = true;

    async function loadOverview() {
      setIsOverviewLoading(true);
      setErrorMessage(null);
      setOverview(null);

      try {
        const data = await fetchOverview(runId, controller.signal);
        if (!mounted) {
          return;
        }
        setOverview(data);
      } catch (error) {
        if (!mounted || controller.signal.aborted) {
          return;
        }
        setOverview(null);
        setErrorMessage(normalizeError(error));
      } finally {
        if (mounted) {
          setIsOverviewLoading(false);
        }
      }
    }

    void loadOverview();

    return () => {
      mounted = false;
      controller.abort();
    };
  }, [selectedRunId]);

  const selectedRun =
    runSelector?.runs.find((run) => run.run_id === selectedRunId) ?? null;

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(14,165,233,0.14),_transparent_26%),linear-gradient(180deg,_#f7fafc_0%,_#eef4f8_100%)] text-slate-950">
      <HeaderBar
        runs={runSelector?.runs ?? []}
        selectedRun={selectedRun}
        selectedRunId={selectedRunId}
        isLoading={isRunsLoading || isOverviewLoading}
        onRunChange={(runId) => {
          startTransition(() => {
            setSelectedRunId(runId);
            setSelectedProjectionId(null);
            setSelectedTreeId(null);
          });
        }}
      />

      <div className="mx-auto flex w-full max-w-[1600px] flex-col gap-5 px-6 py-6">
        <section className="rounded-3xl border border-slate-200 bg-white/80 p-4 shadow-sm backdrop-blur">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <div className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                API base
              </div>
              <div className="mt-1 text-sm text-slate-700">
                {readReviewApiBase() ?? "Unconfigured"}
              </div>
            </div>
            <div className="flex flex-wrap gap-2 text-xs font-medium">
              <span className="rounded-full border border-slate-200 bg-slate-100 px-3 py-1 text-slate-700">
                Runs loaded: {runSelector?.runs.length ?? 0}
              </span>
              <span className="rounded-full border border-slate-200 bg-slate-100 px-3 py-1 text-slate-700">
                Projection nodes: {overview?.run_projection.nodes.length ?? 0}
              </span>
              <span className="rounded-full border border-slate-200 bg-slate-100 px-3 py-1 text-slate-700">
                Layout sections: {overview?.pipeline_layout.sections.length ?? 0}
              </span>
            </div>
          </div>
          {errorMessage ? (
            <div className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              {errorMessage}
            </div>
          ) : null}
          {isRunsLoading || isOverviewLoading ? (
            <div className="mt-4 rounded-2xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-700">
              {isRunsLoading
                ? "Loading review runs from the existing API..."
                : "Loading overview payload for the selected run..."}
            </div>
          ) : null}
        </section>

        <div className="grid gap-5 xl:grid-cols-[minmax(0,1.55fr)_minmax(22rem,0.95fr)]">
          <PipelinePane
            overview={overview}
            selectedProjectionId={selectedProjectionId}
            onSelectProjection={(projectionId) => {
              setSelectedProjectionId(projectionId);
              setSelectedTreeId(null);
            }}
          />
          <DetailsPane
            selectedRun={selectedRun}
            overview={overview}
            selectedProjectionId={selectedProjectionId}
            selectedTreeId={selectedTreeId}
          />
        </div>

        <TreePane
          root={overview?.tree.root ?? null}
          selectedTreeId={selectedTreeId}
          onSelectTree={(treeId) => {
            setSelectedTreeId(treeId);
            setSelectedProjectionId(null);
          }}
        />
      </div>
    </main>
  );
}
