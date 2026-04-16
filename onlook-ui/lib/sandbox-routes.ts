export type SandboxRoute = {
  href: string;
  label: string;
  detail: string;
};

export const sandboxRoutes: SandboxRoute[] = [
  {
    href: "/",
    label: "Review",
    detail: "Pipeline overview, projection graph, and file tree.",
  },
  {
    href: "/document-trace",
    label: "Document Trace",
    detail: "Trace source blobs, normalized text, chunks, and extracted units.",
  },
  {
    href: "/workbench-compare",
    label: "Workbench Compare",
    detail: "Compare baseline, candidate A, and candidate B fixtures.",
  },
  {
    href: "/candidate-b-trace",
    label: "Candidate B Trace",
    detail: "Inspect candidate-B artifacts and summary payloads.",
  },
  {
    href: "/analyst-insight",
    label: "Analyst Insight",
    detail: "Exercise the analyst integration, validation, and insight aliases.",
  },
];
