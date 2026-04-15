import type { ReviewRunSelectorItem } from "@/lib/review-types";
import { formatRunLabel } from "@/lib/review-adapter";

type RunSelectProps = {
  runs: ReviewRunSelectorItem[];
  selectedRunId: string | null;
  disabled?: boolean;
  onChange: (runId: string) => void;
};

export function RunSelect({
  runs,
  selectedRunId,
  disabled = false,
  onChange,
}: RunSelectProps) {
  return (
    <label className="flex min-w-[20rem] flex-col gap-2 text-sm font-medium text-slate-700">
      <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
        Review run
      </span>
      <select
        className="rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 shadow-sm outline-none transition focus:border-sky-500 focus:ring-2 focus:ring-sky-200 disabled:cursor-not-allowed disabled:bg-slate-100"
        disabled={disabled || runs.length === 0}
        value={selectedRunId ?? ""}
        onChange={(event) => onChange(event.target.value)}
      >
        {runs.length === 0 ? (
          <option value="">No reviewable runs found</option>
        ) : null}
        {runs.map((run) => (
          <option key={run.run_id} value={run.run_id}>
            {formatRunLabel(run)}
          </option>
        ))}
      </select>
    </label>
  );
}
