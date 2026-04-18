import {
  summaryRows,
  type SummaryRow,
} from "@/lib/review-adapter";
import type {
  ReviewOverview,
  ReviewProjectionNode,
} from "@/lib/review-types";

type PipelinePaneProps = {
  overview: ReviewOverview | null;
  selectedProjectionId: string | null;
  onSelectProjection: (projectionId: string) => void;
};

function nodeTone(node: ReviewProjectionNode): string {
  if (node.state === "complete") {
    return "border-emerald-200 bg-emerald-50";
  }
  if (node.state === "missing") {
    return "border-rose-200 bg-rose-50";
  }
  if (node.state === "mismatch") {
    return "border-amber-200 bg-amber-50";
  }
  return "border-slate-200 bg-white";
}

function renderSummaryRows(rows: SummaryRow[]) {
  if (rows.length === 0) {
    return (
      <div className="text-xs text-slate-500">
        No structured summary fields for this projection.
      </div>
    );
  }

  return (
    <dl className="space-y-2 text-sm">
      {rows.slice(0, 3).map((row) => (
        <div key={row.label}>
          <dt className="font-medium text-slate-800">{row.label}</dt>
          <dd className="text-slate-600">{row.value}</dd>
        </div>
      ))}
    </dl>
  );
}

export function PipelinePane({
  overview,
  selectedProjectionId,
  onSelectProjection,
}: PipelinePaneProps) {
  return (
    <section className="flex min-h-[24rem] flex-col rounded-3xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-200 px-5 py-4">
        <h2 className="text-lg font-semibold text-slate-950">Pipeline pane</h2>
        <p className="mt-1 text-sm text-slate-600">
          This lane renders the current run projection and pipeline layout from
          the committed review snapshot without recreating Mermaid parity yet.
        </p>
      </div>

      {!overview ? (
        <div className="flex flex-1 items-center justify-center px-5 py-12 text-sm text-slate-500">
          Select a run to load the pipeline projection and layout.
        </div>
      ) : (
        <div className="grid flex-1 gap-5 p-5 xl:grid-cols-[minmax(0,1.4fr)_minmax(18rem,0.8fr)]">
          <div className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              {overview.pipeline_layout.sections.map((section) => (
                <article
                  key={section.title}
                  className="rounded-2xl border border-slate-200 bg-slate-50 p-4"
                >
                  <h3 className="text-sm font-semibold uppercase tracking-[0.16em] text-slate-500">
                    {section.title}
                  </h3>
                  <dl className="mt-3 space-y-3">
                    {section.entries.map((entry) => (
                      <div key={`${section.title}-${entry.label}`}>
                        <dt className="text-xs font-medium text-slate-500">
                          {entry.label}
                        </dt>
                        <dd className="text-sm text-slate-800">{entry.value}</dd>
                      </div>
                    ))}
                  </dl>
                </article>
              ))}
            </div>

            <div className="grid gap-3 lg:grid-cols-2">
              {overview.run_projection.nodes.map((node) => {
                const selected = selectedProjectionId === node.projection_id;
                return (
                  <button
                    key={node.projection_id}
                    type="button"
                    className={`rounded-2xl border p-4 text-left transition hover:border-sky-300 hover:shadow-sm ${nodeTone(node)} ${selected ? "ring-2 ring-sky-300" : ""}`}
                    onClick={() => onSelectProjection(node.projection_id)}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="text-sm font-semibold text-slate-950">
                          {node.title}
                        </div>
                        <div className="mt-1 text-xs uppercase tracking-[0.14em] text-slate-500">
                          {node.stage_family}
                        </div>
                      </div>
                      <span className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-600">
                        {node.state}
                      </span>
                    </div>
                    {node.detail_lines.length > 0 ? (
                      <ul className="mt-3 space-y-1 text-sm text-slate-600">
                        {node.detail_lines.slice(0, 2).map((line) => (
                          <li key={`${node.projection_id}-${line}`}>{line}</li>
                        ))}
                      </ul>
                    ) : null}
                  </button>
                );
              })}
            </div>
          </div>

          <aside className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <h3 className="text-sm font-semibold uppercase tracking-[0.16em] text-slate-500">
              Selected projection
            </h3>
            {selectedProjectionId ? (
              (() => {
                const node =
                  overview.run_projection.nodes.find(
                    (item) => item.projection_id === selectedProjectionId,
                  ) ?? null;
                if (!node) {
                  return (
                    <p className="mt-3 text-sm text-slate-500">
                      The selected projection is no longer present in this run.
                    </p>
                  );
                }
                return (
                  <div className="mt-3 space-y-4">
                    <div>
                      <div className="text-base font-semibold text-slate-950">
                        {node.title}
                      </div>
                      <div className="mt-1 text-sm text-slate-600">
                        {node.canonical_node_ids.join(", ") || "No canonical mapping"}
                      </div>
                    </div>
                    {renderSummaryRows(summaryRows(node.structured_summary))}
                  </div>
                );
              })()
            ) : (
              <p className="mt-3 text-sm text-slate-500">
                Select a projection card to inspect its mapped summary without
                leaving the sandbox shell.
              </p>
            )}
          </aside>
        </div>
      )}
    </section>
  );
}
