import { Suspense } from "react";

import { CandidateBTraceShell } from "@/components/candidate-b-trace-shell";

export default function CandidateBTracePage() {
  return (
    <Suspense fallback={<div className="p-6 text-sm text-slate-600">Loading candidate B trace...</div>}>
      <CandidateBTraceShell />
    </Suspense>
  );
}
