import { formatTimestamp, statusTone } from "@/lib/review-adapter";
import type { ReviewRunSelectorItem } from "@/lib/review-types";
import { RunSelect } from "@/components/run-select";

type HeaderBarProps = {
  runs: ReviewRunSelectorItem[];
  selectedRun: ReviewRunSelectorItem | null;
  selectedRunId: string | null;
  isLoading: boolean;
  onRunChange: (runId: string) => void;
};

function toneClasses(tone: string): string {
  if (tone === "success") {
    return "border-emerald-200 bg-emerald-50 text-emerald-700";
  }
  if (tone === "danger") {
    return "border-rose-200 bg-rose-50 text-rose-700";
  }
  if (tone === "accent") {
    return "border-sky-200 bg-sky-50 text-sky-700";
  }
  return "border-slate-200 bg-slate-100 text-slate-700";
}

export function HeaderBar({
  runs,
  selectedRun,
  selectedRunId,
  isLoading,
  onRunChange,
}: HeaderBarProps) {
  const statusToneValue = selectedRun ? statusTone(selectedRun.status) : "muted";

  return (
    <header className="border-b border-slate-200 bg-white/90 px-6 py-5 backdrop-blur">
      <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
        <div className="max-w-3xl space-y-3">
          <div className="flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-sky-700">
            <span className="rounded-full border border-sky-200 bg-sky-50 px-3 py-1">
              Onlook sandbox
            </span>
            <span className="rounded-full border border-violet-200 bg-violet-50 px-3 py-1 text-violet-700">
              Slice 1
            </span>
          </div>
          <div className="space-y-2">
            <h1 className="text-3xl font-semibold tracking-tight text-slate-950">
              NRC APS review sandbox
            </h1>
            <p className="max-w-2xl text-sm leading-6 text-slate-600">
              This React and Tailwind shell reads the existing review API only.
              The live static review UI and document trace surface remain the
              authority while this sandbox proves the Onlook lane.
            </p>
          </div>
          <div className="flex flex-wrap gap-2 text-xs font-medium">
            <span className="rounded-full border border-slate-200 bg-slate-100 px-3 py-1 text-slate-700">
              Client fetch only
            </span>
            <span className="rounded-full border border-slate-200 bg-slate-100 px-3 py-1 text-slate-700">
              Credentials omitted
            </span>
            <span className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-amber-700">
              Document Trace stays on the live surface in slice 1
            </span>
          </div>
        </div>

        <div className="flex w-full max-w-xl flex-col gap-4 rounded-2xl border border-slate-200 bg-slate-50 p-4 shadow-sm">
          <RunSelect
            runs={runs}
            selectedRunId={selectedRunId}
            disabled={isLoading}
            onChange={onRunChange}
          />
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-xl border border-slate-200 bg-white p-3">
              <div className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                Status
              </div>
              <div className="mt-2 flex items-center gap-2">
                <span
                  className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${toneClasses(statusToneValue)}`}
                >
                  {selectedRun?.status ?? "unselected"}
                </span>
                <span className="text-sm text-slate-600">
                  {selectedRun?.reviewable ? "Reviewable" : "Not reviewable"}
                </span>
              </div>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-3">
              <div className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                Completed
              </div>
              <div className="mt-2 text-sm text-slate-700">
                {formatTimestamp(selectedRun?.completed_at)}
              </div>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
