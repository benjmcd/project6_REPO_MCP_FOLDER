(function () {
    const CANDIDATE_B_ENGINE = 'candidate_b_opendataloader_pdf';
    const CANDIDATE_A_VARIANT = 'candidate_a_page_evidence_v1';

    function normalize(value) {
        return String(value || '').trim().toLowerCase();
    }

    function variantKind(runtimeBinding) {
        const binding = runtimeBinding || {};
        const engine = normalize(binding.document_processing_engine);
        if (engine === CANDIDATE_B_ENGINE) return CANDIDATE_B_ENGINE;
        return normalize(binding.variant_kind) || normalize(binding.visual_lane_mode) || 'baseline';
    }

    function variantLabel(runtimeBinding) {
        const kind = variantKind(runtimeBinding);
        if (kind === CANDIDATE_B_ENGINE) return 'Candidate B / OpenDataLoader PDF';
        if (kind === CANDIDATE_A_VARIANT) return 'Candidate A';
        return 'Baseline';
    }

    function runOptionLabel(runInfo) {
        const baseLabel = String(runInfo?.display_label || runInfo?.run_id || 'unknown run');
        const label = variantLabel(runInfo?.runtime_binding);
        if (variantKind(runInfo?.runtime_binding) !== CANDIDATE_B_ENGINE) return baseLabel;
        return baseLabel.includes(label) ? baseLabel : `${baseLabel} | ${label}`;
    }

    window.NrcApsRuntimeLabels = {
        variantKind,
        variantLabel,
        runOptionLabel,
    };
}());
