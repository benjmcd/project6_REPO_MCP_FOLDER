# Stale / Duplicate Surface Register

This register identifies documentation surfaces that were encountered during the Phase 7A closeout and classified as stale or duplicate. These surfaces were intentionally left untouched to avoid spreading non-authoritative prose.

| Surface Path | Classification | Reason for Preservation / Non-Update |
| :--- | :--- | :--- |
| `BREAK_REFINEMENT_SUMMARY.md` | Stale | Historical patch summary. Not the current operational status. |
| `DECOMP_BREAK_PATCH_SUMMARY.md` | Stale | Historical patch summary. Superseded by method-aware framework docs. |
| `POST_REVIEW_PATCH_SUMMARY.md` | Stale | Historical patch summary. |
| `handoff/document_ingestion_report.md` | Duplicate/Stale | Generic ingestion report. Superseded by the focused Phase 7A validation package and `nrc_aps_status_handoff.md`. |
| `brain/83f74131-2449-4c6a-8524-59668044960f/walkthrough.md` | Stale | Non-authoritative narrrative proof-of-work. |
| `handoff/START_HERE.txt` | Secondary | Broad handoff guide. Not updated as it points to the general handoff structure which remains valid, while slice-specific truth is now in `nrc_aps_status_handoff.md`. |
| `handoff/backend/*` | Stale Mirror | Drifted snapshot. Do NOT use as live implementation truth; exclusively trust root `backend/app/services/*`. |
| Unverified `tests/...` and `tools/...` paths | Broken Authority Routing | Referenced in `README.md` / `REPO_INDEX.md` but not established from allowed active workspace evidence. |

**Authoritative replacement for all NRC APS ingestion status**: `docs/nrc_adams/nrc_aps_status_handoff.md`
