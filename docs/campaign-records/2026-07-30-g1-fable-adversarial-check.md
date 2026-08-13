# G1 adversarial check — Fable verdict (session 91b270df, 2026-07-30)

VERDICT: DISPOSITION-HONEST-AND-CORRECT on facts, stop-discipline, scope. Every falsifiable G1 claim
reproduced (V1=184 passed, V2=138 passed/1 skipped, frozen docs byte-untouched 2b1cb178/fed23fed, no
push, default-off, six aggregate fixtures present + real). Zero fabrication, zero silent spec drift.

BUT the S1-S4 "four frozen-spec contradictions" framing is MISCALIBRATED — do NOT send as-is to owner:
- S3 REAL (the sole true load-bearing frozen-contract defect): evaluate_nrc_acquisition_success runs at
  ScienceBase arming creation -> needs the canonical origin receipt -> receipt needs ApsContentLinkage
  -> linkage is Phase-B-only -> Phase B runs after ScienceBase arming = fail-closed dead end. Reinforced
  by intra-Task-6 circularity (derive loads linkage 2026-2028 vs linkage surfaces carry receipt hash
  2064-2066). Codex STOP correct; its split-receipt proposal is the right shape.
- S2 SPLIT: NRC half REAL-but-narrow (acceptance 1741-1742 vs deferral 1925-1927; plan supplies its own
  resolution "therefore downstream"). ScienceBase half SPURIOUS as contradiction — 1578-1591 affirmatively
  REQUIRES strict-lane provenance/DatasetVersion; this is unbuilt work, not a spec conflict.
- S1 OVERSTATED: genuine ambiguity, not mutual exclusion. 1284-1289 grammar ("exact active lease token"
  PLUS "unexpired lease" = two separate reqs) favors token-exactness-only for finalize (1089-1091 omits
  "unexpired"); under that reading no mutual exclusion. Codex implemented the opposite reading and thereby
  created the stranded-running state it reports as a defect.
- S4 OVERSTATED/self-inflicted: "skip" appears once (plan 2639); command-level reading is plainer, and the
  frozen baseline c7b47543 already contains skip-bearing files in the plan's own broad command surface, so
  the test-level reading was unsatisfiable before any G1 work. The 1-skip is Codex's single-file test
  design; a launcher + non-collected guarded module yields zero skips with no spec change.

Minor: V4/V5 exit code is 4 not 1 (missing-file arg); "independently approved" = same-session Codex
subagents (unaudited-but-plausible, produced a real STOP not a rubber-stamp); one new flag
CONNECTOR_LIVE_EGRESS_EXCLUSIVE_PROOF_MODE defaults True (protective tightening).
Gap: Task-4 ScienceBase persistence completion missing from the proposed forward sequence — the receipt
dead-ends without it even after an S3 delta.

RECOMMENDATION: reframe before owner adjudication — S3 as sole true frozen defect (split-receipt), S1 as
reading-confirmation, S2 as NRC-timing-confirmation + ScienceBase implementation obligation, S4 as
test-restructure + optional 2639 clarification; insert Task-4 persistence before Task-6 receipt minting.
