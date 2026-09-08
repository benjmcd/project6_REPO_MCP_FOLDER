# Reading an analysis product

In the Layer 3 workbench, load a session, open **Products**, select a product and
choose **Read product**. The reader shows the exact stored title and body,
session/product identities, lifecycle, authoring mode, basis/spec hashes and
bounded evidence identities. Loading a roster does not fetch product bodies.

The existing **Save Draft** form remains the authoring path. A saved draft is not
an approved finding. The server's `human` executor label names the technical
authoring mode; it does not establish who wrote the text or who approved it.
The content itself should identify material assistance and relevant limitations.

The selected read uses:

```text
GET /api/v1/layer3/analysis-product/{analysis_product_id}/content?session_id=...
```

It follows the existing Layer 3 read authorization. That audience includes
auditors when role enforcement is configured. Authored prose can contain values;
this reader is not author-private. Local `AUTH_OWNER=none` is owner-equivalent,
and the default identity-presence mode is not role-enforcing authentication.
The read does not enable public artifact-value flags.

The `layer3.analysis_product_content.v1` response contains the exact admitted
text, bounded metadata and evidence kind/ID/role. It omits free-form authoring
provenance, locators and artifact contents. It counts same-session evidence links
and returns at most 200 in stable link-ID order, with an explicit total and
truncation indicator. Each returned target must exist in that session; targets
beyond the cap are not inspected. Missing product returns 404, wrong session 409,
and an unavailable returned evidence target fails the whole read with 409.
Stored text exceeding the existing authoring limits (title 256/body 16,384
characters) is refused rather than silently truncated.

Changing product or session, refreshing the session, or removing the selected
product from the loaded inventory clears its content. Obsolete success/error
responses cannot populate a newer selection or release its busy control. Title
and body render as literal wrapped text, preserving stored line endings.

Session inventory, lineage and package inventory retain their metadata-only
contracts. The reader does not rerun analysis, rewrite a review, promote lifecycle,
follow evidence recursively or deliver an external package. Rollback is a code
revert of the reader/UI; no schema migration, backfill or draft deletion is needed.

Focused verification lives in `backend/tests/test_layer3_analysis_product_content.py`
and `e2e/product-content.spec.js`, alongside the existing authoring, lineage and
authorization compatibility suites. A retained local save/reopen exercise is
separate evidence from those isolated tests.
