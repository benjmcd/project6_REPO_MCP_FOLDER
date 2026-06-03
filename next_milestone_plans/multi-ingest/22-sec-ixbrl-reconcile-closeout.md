# SEC HTML/iXBRL Reconciliation Closeout

Status: implemented on current main as a planning/status reconciliation checkpoint for the governed SEC-specific HTML/iXBRL parser receipt chain.

## Scope

This checkpoint reconciles the multi-ingest planning pack with current-main authority after `sec_edgar_html_inline_xbrl_source_family_parser_v1` became an admitted Layer 3 source family through the governed SEC parser receipt chain.

It is a docs/status alignment pass. It does not add parsers, schema changes, migrations, source-shape changes, UI behavior, package behavior, Candidate B behavior, Onlook work, or mixed-source package semantics.

## Current-Main Authority

- Reconciliation base main: `86b9786df4723135c62a60ed145c5bbff04b3703`.
- The SEC-specific HTML/iXBRL admission path is `sec_edgar_html_inline_xbrl_source_family_parser_v1`.
- The admitted path is governed by the SEC parser receipt chain, not by generic APS XML/HTML parsing.
- Generic XML/HTML/inline-XBRL remains deferred/refused for APS-derived dataset-version source-family selection.
- PR `#2144` added explicit backend and browser verification that the Layer 3 source-family summary admits the SEC-specific HTML/iXBRL parser family while still rendering generic XML/HTML/inline-XBRL as a deferred/refused guardrail.

## Evidence

Live source evidence:

- `backend/app/services/layer3_aps_source_family.py` lists `sec_edgar_html_inline_xbrl_source_family_parser_v1` as admitted/materialized source-family authority.
- `backend/app/services/layer3_sec_edgar_html_inline_xbrl_parser.py` provides the governed SEC-specific HTML/iXBRL parser receipt entrypoint.
- `backend/app/services/nrc_aps_sec_edgar_parser.py` still refuses generic XML/HTML/inline-XBRL inputs for the bounded APS SEC/EDGAR complete-submission text parser.

Validation evidence from the reconciliation landing pass:

- `python -m pytest .\backend\tests\test_layer3_workbench.py -q`
- `python -m pytest .\backend\tests\test_layer3_api.py -q`
- `python .\tools\validate_structure.py`
- `python .\tools\l3-progress-check.py`
- `python .\tools\l3-target-selection-validate.py --expect frozen`
- `git diff --check`
- Headless Playwright for `e2e/layer3-workbench.spec.js` with the source-family guardrail test.
- Headed Chrome Playwright for the same source-family guardrail test.
- GitHub CI for PR `#2144` passed all backend/test shards before merge.

## Reconciled Boundary

Settled:

- Planning/status docs may describe SEC-specific HTML/iXBRL as admitted only when they name the governed SEC parser receipt chain.
- Workbench source-family guardrails may display both the admitted SEC-specific HTML/iXBRL family and the generic XML/HTML/inline-XBRL deferred/refused family in the same panel because they represent different authority boundaries.
- The multi-ingest lane may treat SEC-specific HTML/iXBRL as an admitted current-main source-family authority for future mixed-source governance planning.

Still not settled:

- Broad generic XML/HTML parsing.
- Arbitrary inline-XBRL parser admission outside the governed SEC receipt chain.
- Rich financial-statement semantics beyond the admitted SEC parser/material authority.
- Mixed qualitative-plus-table package semantics.
- Archive-member SEC HTML/iXBRL orchestration.
- Schema/model/migration work.
- Onlook planning or implementation.

## Next

Do not repeat P10A/P10B/P10C/P10D or the SEC HTML/iXBRL source-family verification. The next implementation decision should be one of:

- a refused/mixed-source trace-detail pass only where server authority already exists and operators need more than candidate-panel guardrails;
- a separately frozen mixed-source package-semantics pass connecting admitted SEC parser/material authority to governed package construction; or
- a legacy CSV bridge deprecation decision after proving downstream consumers have adopted the generic table bridge contract.
