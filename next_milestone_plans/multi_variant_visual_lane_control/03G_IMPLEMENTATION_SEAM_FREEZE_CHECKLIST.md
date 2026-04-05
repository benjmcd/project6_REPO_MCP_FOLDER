# 03G Implementation Seam Freeze Checklist

## Purpose

Force exact seam closure before coding.

## Freeze items

### A. `_process_pdf(...)` responsibility map
Classify each responsibility as:
- selector-owned
- shared-evidence-owned
- baseline-locked

Must cover:
- native extraction
- OCR fallback gating
- hybrid OCR logic
- visual significance
- visual decision
- visual ref capture
- artifact writer invocation
- page summaries
- degradation code handling

### B. Shared evidence fields
Freeze which fields are shared inputs for:
- OCR fallback
- visual preservation

### C. Non-swappable surfaces
Freeze which remain baseline-locked in pass 1:
- artifact writer behavior
- ref/path/hash behavior
- diagnostics-ref persistence behavior
- runtime DB binding/discovery behavior
- report/export/review assembly
- replay/promotion/safeguard behavior
- default runtime-root discovery behavior

### D. Config freeze
Freeze:
- selector config key
- default value
- allowed values
- override policy
- invalid-selection behavior

### E. Runtime-root freeze
Freeze:
- baseline runtime root
- whether non-baseline variants get separate roots
- how review/runtime discovery treats non-baseline roots
- whether experiment roots are entirely out-of-band

### F. Activation freeze
Freeze:
- whether selector activation is per-request, per-run, per-process, or global
- propagation behavior across ZIP recursion and nested processing calls
- default lifetime of activation state

### G. Acceptance freeze
Freeze exact commands that must pass for bootstrap acceptance.

### H. Rollback freeze
Freeze:
- revert target
- selector disable path
- immediate fallback conditions

## Exit criterion

No code implementation begins until every item above has an explicit frozen answer.


## Additional reference

Use `03O_PROCESS_PDF_SEAM_CANDIDATE_MAP.md` as the live line-based starting point for seam freeze.
It reduces ambiguity, but it does not by itself freeze the seam.


## Additional reference

Use `03V_SELECTOR_KEY_INSERTION_AND_CONSUMPTION_MAP.md` for the canonical path of `visual_lane_mode`.
The remaining seam question is no longer where the key travels; it is only how the visual-preservation lane behaves once it receives it.


## Closure after this revision

The seam boundary is now closed by:
- `03O_PROCESS_PDF_SEAM_CANDIDATE_MAP.md`
- `03W_EXACT_PROCESS_PDF_SEAM_FREEZE_SPECIFICATION.md`

The remaining seam-related work is no longer boundary discovery.
It is only implementation of behavior **within** the frozen seam.
