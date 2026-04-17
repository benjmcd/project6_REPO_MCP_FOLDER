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

export type ReviewTraceState = {
  has_source_blob: boolean;
  has_diagnostics: boolean;
  has_normalized_text: boolean;
  has_indexed_chunks: boolean;
  has_downstream_usage: boolean;
};

export type ReviewDocumentSelectorRow = {
  target_id: string;
  accession_number: string | null;
  document_title: string | null;
  document_type: string | null;
  media_type: string | null;
  content_id: string | null;
  trace_state: ReviewTraceState;
};

export type ReviewDocumentSelector = {
  run_id: string;
  default_target_id: string | null;
  documents: ReviewDocumentSelectorRow[];
};

export type ReviewTraceIdentity = {
  accession_number: string | null;
  document_title: string | null;
  document_type: string | null;
  media_type: string | null;
  source_file_name: string | null;
  content_id: string | null;
  content_contract_id: string | null;
  chunking_contract_id: string | null;
  normalization_contract_id: string | null;
};

export type ReviewTracePageGeometry = {
  page_number: number;
  width: number;
  height: number;
};

export type ReviewTraceSource = {
  viewer_kind: string;
  blob_ref_present: boolean;
  source_endpoint: string | null;
  content_type: string | null;
  size_bytes: number | null;
  page_geometries: ReviewTracePageGeometry[];
};

export type ReviewTraceSummary = {
  document_class: string | null;
  quality_status: string | null;
  page_count: number;
  ordered_unit_count: number;
  indexed_chunk_count: number;
  visual_page_ref_count: number;
  visual_derivative_unit_count: number;
};

export type ReviewTraceCompleteness = {
  has_linkage_row: boolean;
  has_document_row: boolean;
  has_source_blob: boolean;
  has_diagnostics: boolean;
  has_normalized_text: boolean;
  has_indexed_chunks: boolean;
  has_visual_derivatives: boolean;
  has_downstream_usage: boolean;
  retrieval_available: boolean;
};

export type ReviewTraceSyncCapabilities = {
  source_to_units: string;
  units_to_source: string;
  normalized_text_to_source: string;
  chunk_to_source: string;
};

export type ReviewTraceTab = {
  tab_id: string;
  label: string;
  available: boolean;
  endpoint: string | null;
};

export type ReviewTraceManifest = {
  run_id: string;
  target_id: string;
  identity: ReviewTraceIdentity;
  source: ReviewTraceSource;
  summary: ReviewTraceSummary;
  trace_completeness: ReviewTraceCompleteness;
  sync_capabilities: ReviewTraceSyncCapabilities;
  tabs: ReviewTraceTab[];
  warnings: string[];
  limitations: string[];
};

export type ReviewDiagnostics = {
  run_id: string;
  target_id: string;
  available: boolean;
  quality_status: string | null;
  document_class: string | null;
  page_count: number;
  ordered_unit_count: number;
  visual_page_ref_count: number;
  visual_derivative_unit_count: number;
  unit_kind_counts: Record<string, number>;
  warnings: string[];
  degradation_codes: string[];
  extractor_metadata: Record<string, unknown> | null;
};

export type ReviewNormalizedText = {
  run_id: string;
  target_id: string;
  available: boolean;
  char_count: number;
  mapping_precision: string | null;
  text: string | null;
};

export type ReviewIndexedChunkItem = {
  chunk_id: string;
  chunk_ordinal: number;
  page_start: number | null;
  page_end: number | null;
  start_char: number | null;
  end_char: number | null;
  unit_kind: string | null;
  quality_status: string | null;
  chunk_text: string;
  mapping_precision: string | null;
};

export type ReviewIndexedChunks = {
  run_id: string;
  target_id: string;
  available: boolean;
  chunk_count: number;
  chunks: ReviewIndexedChunkItem[];
};

export type ReviewExtractedUnitItem = {
  unit_id: string;
  page_number: number | null;
  unit_kind: string | null;
  text: string | null;
  bbox: number[] | null;
  start_char: number | null;
  end_char: number | null;
  row_index: number | null;
  provenance: Record<string, unknown> | null;
};

export type ReviewVisualArtifactItem = {
  artifact_id: string;
  page_number: number | null;
  status: string | null;
  visual_page_class: string | null;
  artifact_semantics: string | null;
  format: string | null;
  media_type: string | null;
  width: number | null;
  height: number | null;
  dpi: number | null;
  sha256: string | null;
  endpoint: string | null;
};

export type ReviewExtractedUnits = {
  run_id: string;
  target_id: string;
  available: boolean;
  reason_code: string | null;
  source_precision: string;
  source_layer: string;
  page_number: number | null;
  total_unit_count: number;
  visual_artifacts: ReviewVisualArtifactItem[];
  units: ReviewExtractedUnitItem[];
};

export type WorkbenchCompareRunSourceItem = {
  run_id: string;
  display_label: string;
  completed_at: string | null;
  variant_kind: string;
};

export type WorkbenchCompareBundleSourceItem = {
  bundle_id: string;
  display_label: string;
  generated_at_utc: string | null;
  decision_recommendation: string | null;
  local_only: boolean;
};

export type WorkbenchCompareSources = {
  default_baseline_run_id: string | null;
  default_candidate_a_run_id: string | null;
  default_candidate_b_bundle_id: string | null;
  baseline_runs: WorkbenchCompareRunSourceItem[];
  candidate_a_runs: WorkbenchCompareRunSourceItem[];
  candidate_b_bundles: WorkbenchCompareBundleSourceItem[];
};

export type WorkbenchCompareTargetItem = {
  fixture_id: string;
  display_label: string;
  source_file_name: string | null;
  baseline_target_id: string;
  candidate_a_target_id: string;
  candidate_b_available: boolean;
  comparability_state: string;
};

export type WorkbenchCompareTargets = {
  baseline_run_id: string;
  candidate_a_run_id: string;
  candidate_b_bundle_id: string;
  default_fixture_id: string | null;
  targets: WorkbenchCompareTargetItem[];
};

export type WorkbenchCompareSourceIdentity = {
  fixture_id: string;
  document_title: string | null;
  document_type: string | null;
  source_file_name: string | null;
  accession_number: string | null;
  document_ref: string | null;
  document_sha256: string | null;
};

export type WorkbenchCompareRunBinding = {
  run_id: string;
  target_id: string;
  content_id: string | null;
};

export type WorkbenchCompareBundleBinding = {
  bundle_id: string;
  candidate_b_run_id: string | null;
};

export type WorkbenchCompareVariantBindings = {
  baseline: WorkbenchCompareRunBinding;
  candidate_a: WorkbenchCompareRunBinding;
  candidate_b: WorkbenchCompareBundleBinding;
};

export type WorkbenchCompareBadge = {
  key: string;
  label: string;
  value: string;
  severity: string;
};

export type WorkbenchCompareTabDef = {
  tab_id: string;
  label: string;
  available: boolean;
};

export type WorkbenchCompareDeepLinks = {
  baseline_trace: string | null;
  candidate_a_trace: string | null;
  candidate_b_trace: string | null;
};

export type WorkbenchCompareManifest = {
  fixture_id: string;
  source_identity: WorkbenchCompareSourceIdentity;
  variant_bindings: WorkbenchCompareVariantBindings;
  summary_badges: WorkbenchCompareBadge[];
  tabs: WorkbenchCompareTabDef[];
  warnings: string[];
  limitations: string[];
  deep_links: WorkbenchCompareDeepLinks;
};

export type WorkbenchCompareColumn = {
  variant_id: string;
  available: boolean;
  comparability_class: string;
  label: string;
  data: Record<string, unknown>;
  warnings: string[];
  limitations: string[];
  deep_link: string | null;
};

export type WorkbenchCompareTab = {
  fixture_id: string;
  tab_id: string;
  columns: Record<string, WorkbenchCompareColumn>;
  comparability_legend: Record<string, string>;
  warnings: string[];
  limitations: string[];
};

export type CandidateBTraceTabDef = {
  tab_id: string;
  label: string;
  available: boolean;
};

export type CandidateBTraceIdentity = {
  fixture_id: string;
  bundle_id: string;
  candidate_b_run_id: string | null;
  document_title: string | null;
  source_file_name: string | null;
  document_ref: string | null;
  document_sha256: string | null;
};

export type CandidateBTraceSummary = {
  processing_status: string | null;
  decision_recommendation: string | null;
  page_count: number | null;
  normalized_char_count: number | null;
  struct_tree_state: string | null;
  heading_count: number | null;
  list_count: number | null;
  image_count: number | null;
  table_count: number | null;
  hidden_text_present: boolean | null;
  footer_page_numbers: number[];
  image_sources: string[];
  annotated_pdf_status: string | null;
  expected_gain_claims: string[];
  expected_non_equivalences: string[];
  regime_labels: string[];
  review_notes: string | null;
};

export type CandidateBTraceArtifacts = {
  annotated_pdf: string | null;
  raw_json: string | null;
  raw_markdown: string | null;
};

export type CandidateBTraceManifest = {
  candidate_b_bundle_id: string;
  fixture_id: string;
  identity: CandidateBTraceIdentity;
  summary: CandidateBTraceSummary;
  tabs: CandidateBTraceTabDef[];
  default_tab: string;
  warnings: string[];
  limitations: string[];
  artifacts: CandidateBTraceArtifacts;
};

export type AnalystIntegrationRequest = {
  sources: Record<string, Array<Record<string, unknown>>>;
  link_keys: string[];
};

export type AnalystValidationRequest = {
  rows: Array<Record<string, unknown>>;
  options: Record<string, unknown>;
};

export type AnalystInsightRequest = {
  validation_summary: Record<string, unknown>;
  integrated: Record<string, unknown>;
};
