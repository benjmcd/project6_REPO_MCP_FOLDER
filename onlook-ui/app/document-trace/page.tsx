import { Suspense } from "react";

import { DocumentTraceShell } from "@/components/document-trace-shell";

export default function DocumentTracePage() {
  return (
    <Suspense fallback={<div className="p-6 text-sm text-slate-600">Loading document trace...</div>}>
      <DocumentTraceShell />
    </Suspense>
  );
}
