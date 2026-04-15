import {
  findProjectionNode,
  findTreeNode,
  formatTimestamp,
  summaryRows,
} from "@/lib/review-adapter";
import type { ReviewOverview, ReviewRunSelectorItem } from "@/lib/review-types";

type DetailsPaneProps = {
  selectedRun: ReviewRunSelectorItem | null;
  overview: ReviewOverview | null;
  selectedProjectionId: string | null;
  selectedTreeId: string | null;
};

export function DetailsPane({
  selectedRun,
  overview,
  selectedProjectionId,
  selectedTreeId,
}: DetailsPaneProps) {
  const selectedProjection = findProjectionNode(overview, selectedProjectionId);
  const selectedTreeNode =
    overview && selectedTreeId
      ? findTreeNode(overview.tree.root, selectedTreeId)
      : null;

  return (
    <aside className="flex min-h-[24rem] flex-col rounded-3xl border border-slate-200 bg-slate-950 text-slate-100 shadow-sm">
      <div className="border-b border-slate-800 px-5 py-4">
        <h2 className="text-lg font-semibold">Details pane</h2>
        <p className="mt-1 text-sm text-slate-400">
          Node, tree, and run context stays read-only in the first sandbox slice.
        </p>
      </div>

      <div className="flex-1 space-y-6 overflow-auto px-5 py-5">
        {selectedProjection ? (
          <section className="space-y-3">
            <div>
              <div className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
                Selected projection
              </div>
              <h3 className="mt-2 text-xl font-semibold text-white">
                {selectedProjection.title}
              </h3>
              <p className="mt-1 text-sm text-slate-400">
                {selectedProjection.stage_family} - {selectedProjection.state}
              </p>
            </div>
            {selectedProjection.detail_lines.length > 0 ? (
              <ul className="space-y-1 text-sm text-slate-300">
                {selectedProjection.detail_lines.map((line) => (
                  <li key={`${selectedProjection.projection_id}-${line}`}>{line}</li>
                ))}
              </ul>
            ) : null}
            {selectedProjection.warnings.length > 0 ? (
              <div className="rounded-2xl border border-amber-400/30 bg-amber-300/10 p-4 text-sm text-amber-100">
                <div className="font-semibold">Warnings</div>
                <ul className="mt-2 space-y-1">
                  {selectedProjection.warnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              </div>
            ) : null}
            <div className="space-y-3">
              {summaryRows(selectedProjection.structured_summary).map((row) => (
                <div key={`projection-${row.label}`}>
                  <div className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                    {row.label}
                  </div>
                  <div className="mt-1 text-sm text-slate-200">{row.value}</div>
                </div>
              ))}
            </div>
          </section>
        ) : null}

        {selectedTreeNode ? (
          <section className="space-y-3">
            <div>
              <div className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
                Selected tree node
              </div>
              <h3 className="mt-2 text-xl font-semibold text-white">
                {selectedTreeNode.name}
              </h3>
              <p className="mt-1 text-sm text-slate-400">{selectedTreeNode.path}</p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
                <div className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                  Kind
                </div>
                <div className="mt-1 text-sm text-slate-200">
                  {selectedTreeNode.is_dir ? "Directory" : "File"}
                </div>
              </div>
              <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
                <div className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                  Mapped nodes
                </div>
                <div className="mt-1 text-sm text-slate-200">
                  {selectedTreeNode.mapped_node_ids.length}
                </div>
              </div>
            </div>
          </section>
        ) : null}

        {!selectedProjection && !selectedTreeNode ? (
          <section className="space-y-4">
            <div>
              <div className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
                Selected run
              </div>
              <h3 className="mt-2 text-xl font-semibold text-white">
                {selectedRun?.run_id ?? "No run selected"}
              </h3>
              <p className="mt-1 text-sm text-slate-400">
                {selectedRun
                  ? `${selectedRun.status} - completed ${formatTimestamp(selectedRun.completed_at)}`
                  : "Choose a run to populate the sandbox shell."}
              </p>
            </div>

            {selectedRun ? (
              <div className="grid gap-3 sm:grid-cols-3">
                <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
                  <div className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                    Selected
                  </div>
                  <div className="mt-1 text-lg font-semibold text-white">
                    {selectedRun.summary_counters.selected_count}
                  </div>
                </div>
                <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
                  <div className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                    Downloaded
                  </div>
                  <div className="mt-1 text-lg font-semibold text-white">
                    {selectedRun.summary_counters.downloaded_count}
                  </div>
                </div>
                <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
                  <div className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                    Failed
                  </div>
                  <div className="mt-1 text-lg font-semibold text-white">
                    {selectedRun.summary_counters.failed_count}
                  </div>
                </div>
              </div>
            ) : null}

            {overview ? (
              <div className="space-y-3">
                {summaryRows(overview.run_summary).slice(0, 8).map((row) => (
                  <div key={`summary-${row.label}`}>
                    <div className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                      {row.label}
                    </div>
                    <div className="mt-1 text-sm text-slate-200">{row.value}</div>
                  </div>
                ))}
              </div>
            ) : null}
          </section>
        ) : null}

        <section className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
            Boundary note
          </div>
          <p className="mt-2 text-sm leading-6 text-slate-300">
            Document Trace, Mermaid parity, and live-surface promotion remain out
            of scope for slice 1. This pane is intentionally a shell over the
            existing overview payload only.
          </p>
        </section>
      </div>
    </aside>
  );
}
