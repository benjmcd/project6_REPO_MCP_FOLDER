# Defect-#2 transport fix landing record (2026-08-07)

> Landing record for `b580cddc05c90219db8b3c070a4a05fb9f5f9110..818cc37e2f626bf8bb46056674d302df2765c7f0`
> on `codex/dual-live-plan`. This record does not authorize P8, credentials, egress arming, a live
> run, a merge to main, or any later lane.

## 1. Custody and landed identity

The landing executor verified both canonical carrier files before use:

| Carrier | Bytes | SHA-256 |
|---|---:|---|
| `C:\p6-scratch\dl-fix2.patch` | 6,164 | `f453d6e917b818b69e99dba5bf4b9b753a68f5bc1367670f41c1bfe931a26940` |
| `C:\p6-scratch\dl-fix2-test_connector_transport_loopback.py` | 22,858 | `60303d0723aa0c7a960d9d190c8fd4a0f07d734928be965d74e0cbd6e64a29f6` |

The patch was applied without alteration and the test carrier was copied byte-identically. The
single landed commit is:

`818cc37e2f626bf8bb46056674d302df2765c7f0`

Its parent is `b580cddc05c90219db8b3c070a4a05fb9f5f9110`. The exact landed shape is three files,
672 insertions and 11 deletions:

```text
45  10  backend/app/services/connector_egress_transport.py
623 0   backend/tests/test_connector_transport_loopback.py
4   1   tools/dual_live_run.py
```

Post-image SHA-256s:

```text
39c54ab902affaf067dfa40db1474ffb1395027c5fc96663bcfca2791ba68a01  backend/app/services/connector_egress_transport.py
60303d0723aa0c7a960d9d190c8fd4a0f07d734928be965d74e0cbd6e64a29f6  backend/tests/test_connector_transport_loopback.py
9f3c6a2487c0f5c4ac7a46a94539f8da8dad158c40b1aedda6e45570222ca611  tools/dual_live_run.py
```

The carrier's mechanically derived stat, rather than stale approximate prose in the handoff, is the
recorded authority. No gate allowlist, frozen document, production test, or certified manifest was
edited.

## 2. Commit and landing mechanism

The neutral, trailer-free commit message was:

```text
fix(dual-live): classify released-connection completion correctly in bounded transport

Distinguish completed responses from unarmed post-release reads in the bounded connector transport.

Add loopback coverage for the non-injected socket path and expose quiescence refusal at the runner boundary.
```

Immediately before the explicit-refspec push, remote
`refs/heads/codex/dual-live-plan` still resolved to `b580cddc05c90219db8b3c070a4a05fb9f5f9110`.
The accepted push was:

```text
b580cddc..818cc37e  818cc37e2f626bf8bb46056674d302df2765c7f0 -> codex/dual-live-plan
```

No PR and no push through the locally misconfigured `origin` remote or a bare branch name occurred.

## 3. Serialized counters at the landed revision

All final runs used `C:\p6-run\py312\python.exe`, one suite at a time:

```text
tests/test_dual_gate.py
356 passed, 1 warning in 148.38s (0:02:28)

backend/tests/test_dual_eval.py
404 passed, 1 warning in 413.03s (0:06:53)

backend/tests/test_connector_transport_loopback.py
10 passed, 1 warning in 1.05s

backend/tests/test_egress_transport.py
92 passed, 1 warning in 3.77s
```

The warnings were `PytestCacheWarning` instances: `.pytest_cache` creation was denied in the isolated
worktree. They did not change the pass counters. The known evaluator sequence-binder flake did not
fire. The 356 gate includes the frozen plan blob `68f740af86dc7d1ac2227f81a6ea28e7e2c7458f`
and B1a seal `b8a89df28ed1ed5adfd8ded7ee12d28863cf0ed2` unchanged assertions.

### Restricted-sandbox first attempt

The first gate invocation ran under the restricted sandbox identity rather than the intended host
identity. It could not validate reviewed Git source identity and its PowerShell child could not see
the installed Python 3.11. Its exact terminal count was:

```text
2 failed, 354 passed in 181.08s (0:03:01)
```

No source or test changed. The same complete gate was then rerun once under the normal host context
and produced the authoritative `356 passed` result above.

## 4. RED-count scoping correction

The review packet's statement that the unpatched revision produced **RED 1** referred to a scoped
single-node invocation; it was not a full-module count. The L2 adjudicator confirmed that the full
loopback module at the unpatched revision yields **3 failed / 5 skipped**: the NRC multi-chunk, NRC
single-chunk, and ScienceBase multi-chunk cases fail their `completed` assertion, while tri-state-only
tests skip because the helper is absent. This is strictly stronger demonstrated defect coverage, not
a regression or a reduction in the reviewed proof.

## 5. Review and non-claims

The independent delta review verdict is `L2-SOUND-WITH-FINDINGS`; its exact record is
`2026-08-07-l2-delta-review-818cc37e.md`. That review unblocked L3 regeneration on this axis but did
not grant P8, credential, egress, live-run, merge-to-main, or acceptance authority. The live HTTPS
path, TLS candidate shape, endpoint framing, and real-timing quiescence remain live-frontier residuals.
