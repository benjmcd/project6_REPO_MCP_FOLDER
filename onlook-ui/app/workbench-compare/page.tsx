import { Suspense } from "react";

import { WorkbenchCompareShell } from "@/components/workbench-compare-shell";

export default function WorkbenchComparePage() {
  return (
    <Suspense fallback={<div className="p-6 text-sm text-slate-600">Loading compare workbench...</div>}>
      <WorkbenchCompareShell />
    </Suspense>
  );
}
