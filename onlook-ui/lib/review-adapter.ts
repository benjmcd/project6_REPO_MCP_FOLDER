import type {
  ReviewOverview,
  ReviewProjectionNode,
  ReviewRunSelectorItem,
  ReviewTreeNode,
} from "@/lib/review-types";

export type TreeStats = {
  directories: number;
  files: number;
};

export type SummaryRow = {
  label: string;
  value: string;
};

function labelizeKey(key: string): string {
  const normalized = key.replace(/_/g, " ").trim();
  if (!normalized) {
    return "Value";
  }

  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}

function stringifyValue(value: unknown): string {
  if (value === null || value === undefined) {
    return "Unavailable";
  }
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }

  const serialized = JSON.stringify(value);
  if (!serialized) {
    return "Unavailable";
  }

  return serialized.length > 180
    ? `${serialized.slice(0, 177)}...`
    : serialized;
}

export function formatTimestamp(value: string | null | undefined): string {
  if (!value) {
    return "Unavailable";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(parsed);
}

export function formatRunLabel(run: ReviewRunSelectorItem): string {
  return run.display_label ?? `${run.run_id} | ${run.status}`;
}

export function statusTone(status: string): string {
  if (status === "completed") {
    return "success";
  }
  if (status === "failed") {
    return "danger";
  }
  if (status === "running") {
    return "accent";
  }
  return "muted";
}

export function summaryRows(record: Record<string, unknown>): SummaryRow[] {
  return Object.entries(record).map(([key, value]) => ({
    label: labelizeKey(key),
    value: stringifyValue(value),
  }));
}

export function findProjectionNode(
  overview: ReviewOverview | null,
  projectionId: string | null,
): ReviewProjectionNode | null {
  if (!overview || !projectionId) {
    return null;
  }

  return (
    overview.run_projection.nodes.find(
      (node) => node.projection_id === projectionId,
    ) ?? null
  );
}

export function findTreeNode(
  node: ReviewTreeNode,
  treeId: string | null,
): ReviewTreeNode | null {
  if (!treeId) {
    return null;
  }
  if (node.tree_id === treeId) {
    return node;
  }

  for (const child of node.children ?? []) {
    const match = findTreeNode(child, treeId);
    if (match) {
      return match;
    }
  }

  return null;
}

export function collectTreeStats(node: ReviewTreeNode): TreeStats {
  let directories = node.is_dir ? 1 : 0;
  let files = node.is_dir ? 0 : 1;

  for (const child of node.children ?? []) {
    const childStats = collectTreeStats(child);
    directories += childStats.directories;
    files += childStats.files;
  }

  return { directories, files };
}
