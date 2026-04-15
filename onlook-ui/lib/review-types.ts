export type ReviewRunSummaryCounters = {
  selected_count: number;
  downloaded_count: number;
  failed_count: number;
};

export type ReviewRunSelectorItem = {
  run_id: string;
  display_label: string | null;
  connector_key: string;
  status: string;
  submitted_at: string;
  completed_at: string | null;
  reviewable: boolean;
  disabled_reason_code: string | null;
  summary_counters: ReviewRunSummaryCounters;
};

export type ReviewRunSelector = {
  default_run_id: string | null;
  runs: ReviewRunSelectorItem[];
};

export type ReviewProjectionNode = {
  projection_id: string;
  title: string;
  detail_lines: string[];
  stage_family: string;
  canonical_node_ids: string[];
  state: string;
  warnings: string[];
  mapped_file_refs: string[];
  mapped_tree_ids: string[];
  artifact_refs: string[];
  structured_summary: Record<string, unknown>;
  is_composite: boolean;
};

export type ReviewProjectionEdge = {
  source_id: string;
  target_id: string;
};

export type ReviewProjectionGraph = {
  projection_id: string;
  version: string;
  nodes: ReviewProjectionNode[];
  edges: ReviewProjectionEdge[];
};

export type ReviewPipelineLayoutEntry = {
  label: string;
  value: string;
  path: string | null;
};

export type ReviewPipelineLayoutSection = {
  title: string;
  entries: ReviewPipelineLayoutEntry[];
};

export type ReviewPipelineLayout = {
  run_id: string;
  sections: ReviewPipelineLayoutSection[];
};

export type ReviewTreeNode = {
  tree_id: string;
  name: string;
  path: string;
  is_dir: boolean;
  children: ReviewTreeNode[] | null;
  mapped_node_ids: string[];
};

export type ReviewTree = {
  run_id: string;
  root: ReviewTreeNode;
};

export type ReviewOverview = {
  run_id: string;
  run_summary: Record<string, unknown>;
  run_projection: ReviewProjectionGraph;
  pipeline_layout: ReviewPipelineLayout;
  tree: ReviewTree;
};
