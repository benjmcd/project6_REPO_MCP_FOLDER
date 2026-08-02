# G2-P3 supply-chain advisory sweep — attestation (2026-08-02)

Status: **ATTESTATION PRODUCED; G2-P3 DISPOSITION NOT TAKEN.** This record supplies
the CVE/freshness result the P3 clause asks for. It accepts nothing, waives nothing,
and closes nothing — producing the attestation does not by itself close G2-P3 as a
prerequisite. Disposition of every finding below remains an explicit owner item at
G2-P6 and G2-P8. There is no implicit waiver.

## Scope of the egress used to produce this record

The advisory lookups were performed as **read-only external research by the assistant
harness**. They touched zero project surfaces, zero project code paths, zero
credentials, and zero project configuration. Nothing was installed, nothing was
fetched into the repository, nothing was executed against project code, and no
connector, transport, or acquisition path was armed, enabled, or rehearsed. This is
**not project runtime egress**.

It is therefore inside condition C3's PREP-ONLY authorization, which names "CVE
attestation" as in-scope preparation while separately forbidding "egress arming
outside the offline harness"
(`docs/campaign-records/2026-08-02-g1-grouped-gate-verdict.md:33-35`).

This distinction is load-bearing because the previously attempted in-project route
failed for exactly this reason: "`pip-audit` was unavailable offline"
(`docs/campaign-records/2026-07-30-g1-implementation-report.md:290`). Running
`pip-audit` from inside the project environment would require enabling project egress,
which C3 forbids before P8.

## Authority and scope

- Branch `codex/dual-live-plan` in `worktrees/dual-live-plan`; starting authority
  `d1b2be2794e670488ae0617240540a26b0dadcbd`.
- Binding gate: `docs/campaign-records/2026-08-02-g1-grouped-gate-verdict.md`.
- Frozen plan blob `68f740af86dc7d1ac2227f81a6ea28e7e2c7458f`: not edited.
- B1a seal constant `b8a89df28ed1ed5adfd8ded7ee12d28863cf0ed2`: not edited.
- G2-P1 and G2-P2 remain OPEN and BLOCKING. Nothing here is a host provisioning, a
  host reproduction, or a live-run authorization.

## The governing clause, verbatim

`docs/campaign-records/2026-08-02-g1-grouped-gate-verdict.md:47-48`:

> - G2-P3 Supply chain: one-time CVE/freshness attestation of the egress stack + the in-process PDF parser
>   (PyMuPDF/MuPDF locked ver); confirm no unpinned optional requests extras in the child env.

## Audit target set — 7 distributions (REPO-CONFIRMED)

| # | Distribution | Exact version audited | Pin source |
|---|---|---|---|
| 1 | certifi | 2026.6.17 | `backend/app/services/dual_live_dependencies.py:27`; `backend/requirements.lock.txt:175` |
| 2 | chardet | 7.4.3 | `backend/app/services/dual_live_dependencies.py:28`; `backend/requirements.lock.txt:182` |
| 3 | charset-normalizer | 3.4.7 | `backend/app/services/dual_live_dependencies.py:29`; `backend/requirements.lock.txt:220` |
| 4 | idna | 3.18 | `backend/app/services/dual_live_dependencies.py:30`; `backend/requirements.lock.txt:868` |
| 5 | requests | 2.34.2 | `backend/app/services/dual_live_dependencies.py:31`; `backend/requirements.lock.txt:2414` |
| 6 | urllib3 | 2.7.0 | `backend/app/services/dual_live_dependencies.py:32`; `backend/requirements.lock.txt:2891` |
| 7 | pymupdf (PyMuPDF / MuPDF) | 1.27.2.3 | `backend/requirements.lock.txt:2160` |

Note on PyMuPDF. `backend/requirements.txt:19` declares only the floor `PyMuPDF>=1.24`,
which is not a concrete version an advisory database can be queried against. The
audited version is the resolved lock pin `1.27.2.3`. PyMuPDF is **not** one of the six
RECORD-hash-verified distributions in `dual_live_dependencies.py`; it is an ordinary
pinned dependency, audited here because the P3 clause names it. Advisories against the
bundled MuPDF native library are in scope for row 7.

## Requests extras check — SATISFIED AT SOURCE; child-env half still owed

`backend/requirements.lock.txt` contains exactly one `requests` entry,
`requests==2.34.2` at line 2414, in plain form. No `requests[...]` extras form appears
anywhere in the lock file, so no unpinned optional extra can be introduced *from the
declared dependency source*.

This is the source-level half of the third P3 sub-clause. The clause's literal wording
is "in the child env", which is a property of the running acquisition child. No such
child exists: G2-P1 is OPEN and no eligible host has been provisioned. **The child-env
confirmation is therefore still owed**, and is carried on the G2-P1 record's open
checklist (`docs/campaign-records/2026-08-02-g2-p1-host-provisioning.md`, section 5).
This record does not claim the sub-clause is fully discharged.

## Orthogonal note — the RequestsDependencyWarning is not a vulnerability finding

Every G2-prep suite run reports "1 dependency warning". It is identified as a
`RequestsDependencyWarning` naming `urllib3 2.6.3` or `chardet 7.1.0` /
`charset_normalizer 3.4.4`
(`docs/campaign-records/2026-08-02-g2-prep-report.md:119`;
`docs/campaign-records/2026-08-02-g2-prep.md:344`). Those are the versions installed on
the **ineligible prep host**, not the pinned versions audited above; the same fact is
recorded at `docs/campaign-records/2026-08-02-task8-toctou-condition1.md:23`, which
states that it "does not make the host dependency-eligible for a real/live run". The
warning is a version-mismatch signal that the prep host sits outside the eligibility
gate. It is orthogonal to this attestation: it neither satisfies nor fails G2-P3, and
it is not waived here.

## Method

For each of the 7 distributions, the sources below were queried for the exact pinned
version. A finding is recorded whenever any source returns an advisory whose published
affected-version range includes the pinned version.

- OSV.dev, ecosystem PyPI — **primary**
- GitHub Advisory Database (GHSA), ecosystem pip — **primary**
- NVD (CVE) — **corroborating**
- PyPI JSON — freshness only

OSV and GHSA are primary because they are ecosystem-scoped and version-ranged. NVD
keyword search is not ecosystem-scoped and returns substantial unrelated matter for
generic tokens; it is used to corroborate an OSV/GHSA hit or to surface an ID the
ecosystem sources missed, never as the sole basis for an AFFECTED verdict. Where the
sources disagree, the verdict is INDETERMINATE, not a judgement call.

Applicability verdicts: **AFFECTED** (pinned version falls inside a published affected
range), **NOT AFFECTED** (pinned version falls outside every published affected range),
**INDETERMINATE** (range unpublished, ambiguous, sources disagree, or the exact pinned
version is not indexed by the source).

Disposition values: **NONE-REQUIRED** (no advisory applies) or
**OWNER-DECISION-REQUIRED-AT-P6**. "Waived", "accepted", and "cleared" are not
available values in this record.

Recording rule: only what a fetched source actually returned is recorded, together with
the form in which it was queried (structured API response vs. rendered list page).
Where a source could not be reached or does not index the pinned version, that is
stated as such. No result is supplied from model recall.

## Findings

Query date (UTC): 2026-08-02

### Summary

| # | Distribution | Version | Advisories applying | Highest severity applying | Freshness | Disposition |
|---|---|---|---|---|---|---|
| 1 | certifi | 2026.6.17 | 0 applying (3 found, all NOT AFFECTED) | n/a (none apply) | >=1 release behind (latest 2026.7.22) | NONE-REQUIRED |
| 2 | chardet | 7.4.3 | none found | n/a (none apply) | current (== latest) | NONE-REQUIRED |
| 3 | charset-normalizer | 3.4.7 | none found | n/a (none apply) | 2 releases behind (latest 3.4.9) | NONE-REQUIRED |
| 4 | idna | 3.18 | 0 applying (2 found, both NOT AFFECTED) | n/a (none apply) | current (== latest) | NONE-REQUIRED |
| 5 | requests | 2.34.2 | 0 applying (3 found, all NOT AFFECTED) | n/a (none apply) | current (== latest) | NONE-REQUIRED |
| 6 | urllib3 | 2.7.0 | 0 applying (19 found, all NOT AFFECTED) | n/a (none apply) | current (== latest) | NONE-REQUIRED |
| 7 | pymupdf | 1.27.2.3 | 0 confirmed applying (1 pymupdf adv NOT AFFECTED); MuPDF-core set INDETERMINATE | INDETERMINATE (MuPDF-core mapping unresolved) | >=1 minor behind (latest 1.28.0) | OWNER-DECISION-REQUIRED-AT-P6 |

### Per-distribution detail

One block per distribution, in the table order above. Every field is mandatory.
"none found", "not published", and "not indexed" are valid values; blank is not.

#### 1. certifi == 2026.6.17

- Sources queried: OSV.dev (PyPI/certifi); GitHub Advisory Database (pip/certifi);
  NVD (keyword `certifi`); PyPI JSON. Source form and reachability: OSV.dev reachable —
  `GET https://osv.dev/list?ecosystem=PyPI&q=certifi` returned a **rendered list page**
  (OSV's structured query API is POST-only, so a GET receives the rendered UI, not an API
  query); it showed 6 rows = 3 distinct vulnerabilities each listed twice (GHSA id + PYSEC
  alias), and individual OSV detail pages (also rendered) were fetched for verbatim
  affected-range confirmation. GitHub Advisories reachable —
  `GET https://github.com/advisories?query=ecosystem%3Apip+certifi` returned a **rendered
  list page** of 3 advisories; individual GHSA detail pages (rendered) gave CVSS vectors and
  ranges. NVD reachable via **structured JSON API**, but the generic `keywordSearch=certifi`
  returned ~4,434 unrelated results and was not usable; targeted `cveId=` JSON queries for the
  3 CVE ids all succeeded and were used as corroboration, spaced apart. PyPI JSON reachable —
  **structured API**; `info.version` = 2026.7.22, and version-specific endpoints for 2026.6.17
  and 2026.7.22 returned exact upload timestamps.
- Query date (UTC): 2026-08-02
- Advisory IDs returned for this package, any version: GHSA-248v-346w-9cwc / CVE-2024-39689 /
  PYSEC-2024-230; GHSA-xqr8-7jwr-rhp7 / CVE-2023-37920 / PYSEC-2023-135; GHSA-43fp-rhv2-5gv8 /
  CVE-2022-23491 / PYSEC-2022-42986
- Per advisory returned:
  - ID: GHSA-248v-346w-9cwc / CVE-2024-39689 / PYSEC-2024-230
    - Severity: source disagreement on label only — the GitHub Advisory UI labels it LOW with no
      CVSS on the list page; the underlying CVSS v3.1 (on the GHSA detail page and NVD) is 7.5
      HIGH, vector CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:H/A:N.
    - Published affected range: >= 2021.5.30, < 2024.7.4 (agreeing across OSV, GHSA, NVD).
    - Applicability to 2026.6.17: NOT AFFECTED — pinned 2026.6.17 is far greater than the fixed
      version 2024.7.4, so it lies outside the affected range >=2021.5.30,<2024.7.4.
    - First fixed version: 2024.7.4
  - ID: GHSA-xqr8-7jwr-rhp7 / CVE-2023-37920 / PYSEC-2023-135
    - Severity: sources disagree on score (range/fix agree) — GHSA CVSS v3.1 7.5 HIGH
      (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:H/A:N); NVD primary CVSS v3.1 9.8 CRITICAL
      (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H), with GHSA's 7.5 listed as secondary.
    - Published affected range: >= 2015.4.28, < 2023.7.22 (agreeing across OSV, GHSA, NVD).
    - Applicability to 2026.6.17: NOT AFFECTED — pinned 2026.6.17 is far greater than the fixed
      version 2023.7.22, outside the affected range >=2015.4.28,<2023.7.22.
    - First fixed version: 2023.7.22
  - ID: GHSA-43fp-rhv2-5gv8 / CVE-2022-23491 / PYSEC-2022-42986
    - Severity: sources disagree on score (range/fix agree) — GHSA CVSS v3.1 6.8 MEDIUM
      (CVSS:3.1/AV:N/AC:L/PR:H/UI:N/S:C/C:N/I:H/A:N) [OSV detail also cites CVSS v4.0 5.9]; NVD
      primary CVSS v3.1 7.5 HIGH (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:H/A:N), with GHSA's 6.8
      as secondary.
    - Published affected range: >= 2017.11.05, < 2022.12.07 (agreeing across OSV, GHSA, NVD).
    - Applicability to 2026.6.17: NOT AFFECTED — pinned 2026.6.17 is far greater than the fixed
      version 2022.12.07, outside the affected range >=2017.11.05,<2022.12.07.
    - First fixed version: 2022.12.07
- Freshness: latest upstream release reported by PyPI JSON is 2026.7.22, released
  2026-07-22T03:35:11.276376Z; the pinned 2026.6.17 was released 2026-06-17T10:31:06.348672Z
  and is at least 1 release behind (~5 weeks stale). The exact count of intermediate releases
  is not determinable — the full PyPI "releases" object could not be reliably enumerated
  end-to-end through the fetch tool.
- Disposition: NONE-REQUIRED

#### 2. chardet == 7.4.3

- Sources queried: OSV.dev (PyPI/chardet); GitHub Advisory Database (pip/chardet); NVD
  (keyword `chardet`); PyPI JSON. Source form and reachability: OSV.dev reachable —
  `GET https://osv.dev/list?ecosystem=PyPI&q=chardet` returned a **rendered list page** (OSV's
  structured query API is POST-only) whose body states "No results (check our FAQ if this is
  unexpected)". GitHub Advisories reachable —
  `GET https://github.com/advisories?query=ecosystem%3Apip+chardet` returned a **rendered list
  page** stating "No results matched your search". NVD reachable — **structured JSON API**,
  `keywordSearch=chardet&resultsPerPage=50` returned `totalResults: 0`, empty vulnerabilities
  array. PyPI JSON reachable — **structured API**; `info.version` = 7.4.3, confirming 7.4.3 is
  the current latest published release (a follow-up fetch to isolate the 7.4.3 `upload_time`
  was truncated by the fetch tool on the large payload, so the exact release date could not be
  extracted).
- Query date (UTC): 2026-08-02
- Advisory IDs returned for this package, any version: none found
- Per advisory returned: none found — no advisory targets chardet in any queried source.
- Freshness: latest upstream release reported by PyPI JSON is 7.4.3 (== the pinned version,
  the current/latest published release); the pinned version is current (0 releases behind). The
  exact upload timestamp for 7.4.3 could not be extracted (the large PyPI releases payload was
  truncated by the fetch tool), so "current" is established by `info.version` equality rather
  than a fetched date.
- Disposition: NONE-REQUIRED

#### 3. charset-normalizer == 3.4.7

- Sources queried: OSV.dev (PyPI/charset-normalizer); GitHub Advisory Database
  (pip/charset-normalizer); NVD (keyword `charset-normalizer`); PyPI JSON. Source form and
  reachability: OSV.dev reachable —
  `GET https://osv.dev/list?ecosystem=PyPI&q=charset-normalizer` returned a **rendered list
  page** (OSV's structured query API is POST-only) stating "No results (check our FAQ if this
  is unexpected)". GitHub Advisories reachable —
  `GET https://github.com/advisories?query=ecosystem%3Apip+charset-normalizer` returned a
  **rendered list page** whose header reports "1 advisory", but the sole advisory shown is
  GHSA-m8gf-v64p-gfmg ("BabelDOC: Arbitrary Code Execution via CMap Pickle Deserialization",
  CVE-2026-54071, High), which targets the unrelated BabelDOC package, not charset-normalizer
  (an apparent fuzzy/text-search match, not a package-scoped hit); no advisory naming
  charset-normalizer itself was shown. NVD reachable — **structured JSON API**,
  `keywordSearch=charset-normalizer&resultsPerPage=50` returned `totalResults: 0`. PyPI JSON
  reachable — **structured API**; `info.version` = 3.4.9, and the releases confirm 3.4.7 is
  present, uploaded 2026-04-02.
- Query date (UTC): 2026-08-02
- Advisory IDs returned for this package, any version: none found (the single GHSA the GitHub
  list surfaced, GHSA-m8gf-v64p-gfmg, is against the unrelated BabelDOC package and is
  excluded).
- Per advisory returned: none found — no advisory targets charset-normalizer in any queried
  source.
- Freshness: latest upstream release reported by PyPI JSON is 3.4.9, released 2026-07-07; the
  pinned 3.4.7 was released 2026-04-02 and is 2 releases behind (3.4.8 released 2026-07-06;
  3.4.9 released 2026-07-07).
- Disposition: NONE-REQUIRED

#### 4. idna == 3.18

- Sources queried: OSV.dev (PyPI/idna); GitHub Advisory Database (pip/idna); NVD (keyword
  `idna`); PyPI JSON. Source form and reachability: OSV.dev reachable —
  `GET https://osv.dev/list?ecosystem=PyPI&q=idna` returned a **rendered list page** (OSV's
  structured query API is POST-only) of 4 entries = 2 distinct vulnerabilities via PYSEC/GHSA
  alias pairs; OSV per-vulnerability detail pages (also rendered) for all four ids gave
  affected-range and fixed-version detail plus CVE cross-references. GitHub Advisories
  reachable — `GET https://github.com/advisories?query=ecosystem%3Apip+idna` returned a
  **rendered list page** with the same 2 GHSA ids (GHSA-65pc-fj4g-8rjx, GHSA-jjg7-2v4v-x38h),
  corroborating completeness. NVD reachable — **structured JSON API**, but the generic
  `keywordSearch=idna` surfaced mostly off-target hits (libidn, curl, Ruby OpenSSL, the
  CPython stdlib idna-codec CVE-2022-45061 which is a different codebase, golang.org/x/net/idna,
  etc.) and did not surface the two relevant CVEs; corroboration was obtained via two targeted
  `cveId=` JSON GETs (CVE-2026-45409 and CVE-2024-3651), reachable both times and spaced apart,
  which agreed on range and fix (with a severity-score disagreement on CVE-2024-3651). PyPI JSON
  reachable — **structured API**; confirms 3.18 is the current latest (uploaded
  2026-06-02T14:34:07Z).
- Query date (UTC): 2026-08-02
- Advisory IDs returned for this package, any version: CVE-2026-45409 / GHSA-65pc-fj4g-8rjx /
  PYSEC-2026-215; CVE-2024-3651 / GHSA-jjg7-2v4v-x38h / PYSEC-2024-60
- Per advisory returned:
  - ID: CVE-2026-45409 / GHSA-65pc-fj4g-8rjx / PYSEC-2026-215
    - Severity: CVSS v3.1 5.3 MEDIUM — CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:L (consistent
      across OSV, GHSA, NVD); GHSA additionally reports CVSS v4.0 6.9 MEDIUM.
    - Published affected range: idna 0.1 through 3.14 inclusive (all releases before 3.15),
      consistent across OSV, GHSA, NVD. DoS in valid_contexto(); an incomplete fix for
      CVE-2024-3651.
    - Applicability to 3.18: NOT AFFECTED — pinned 3.18 > first-fixed 3.15, outside the affected
      range < 3.15; all three sources agree on the 3.15 boundary.
    - First fixed version: 3.15
  - ID: CVE-2024-3651 / GHSA-jjg7-2v4v-x38h / PYSEC-2024-60
    - Severity: source disagreement on score only — NVD and PYSEC report CVSS v3.1 7.5 HIGH
      (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H); GHSA reports CVSS v3.1 6.2 MEDIUM plus
      CVSS v4.0 6.9 MEDIUM. Range/fix agree.
    - Published affected range: idna 0.1 through 3.6 inclusive (all releases before 3.7),
      consistent across OSV, GHSA, NVD. Quadratic-complexity DoS in idna.encode().
    - Applicability to 3.18: NOT AFFECTED — pinned 3.18 >> first-fixed 3.7, outside the affected
      range < 3.7; all three sources agree on the 3.7 boundary despite disagreeing on severity.
    - First fixed version: 3.7
- Freshness: latest upstream release reported by PyPI JSON is 3.18 (== the pinned version;
  uploaded 2026-06-02T14:34:07Z; no version published after 3.18 as of the query date); the
  pinned version is current (0 releases behind).
- Disposition: NONE-REQUIRED

#### 5. requests == 2.34.2

- Sources queried: OSV.dev (PyPI/requests); GitHub Advisory Database (pip/requests); NVD
  (keyword `requests`); PyPI JSON. Source form and reachability: OSV.dev reachable —
  `GET https://osv.dev/list?ecosystem=PyPI&q=requests` returned a **rendered list page** (OSV's
  structured query API is POST-only) initially showing 3 items with "Load more"; re-fetching
  surfaced 13 further ids, all MAL-2026-* (malicious/typosquat package advisories, e.g. the
  spot-checked MAL-2026-2245 = "requests-testik111") or PYSEC-2026-3050/GHSA-vh75-fwv3-pqrh
  (which affects the different "requests-hardened" project) — none apply to the genuine
  "requests" package. GitHub Advisories reachable but NOT package-scoped —
  `GET https://github.com/advisories?query=ecosystem%3Apip+requests` matched 618 advisories on
  the keyword "requests" across unrelated packages, so this listing route was unusable;
  corroboration was obtained by fetching the 3 GHSA detail pages directly (rendered), which
  matched OSV. NVD reachable — **structured JSON API**; the broad `keywordSearch=requests`
  returned `totalResults: 9630` but the pipeline surfaced only very old (1992-2001) entries and
  did not expose the relevant CVEs, so it was reachable-but-not-usable at that query; a narrower
  same-host `cveId=` GET for each of the 3 CVE ids returned valid single-result JSON
  corroborating range and severity. PyPI JSON reachable — **structured API**; `info.version` =
  2.34.2 (current/latest), cross-verified via the rendered pypi.org/project/requests/2.34.2/
  and #history pages (2.34.2 released 2026-05-14, latest).
- Query date (UTC): 2026-08-02
- Advisory IDs returned for this package, any version: GHSA-9hjg-9r4m-mvj7 / CVE-2024-47081 /
  PYSEC-2026-1872; GHSA-9wx4-h78v-vm56 / CVE-2024-35195 / PYSEC-2026-1873; GHSA-gc5v-m9x4-r6x2 /
  CVE-2026-25645 / PYSEC-2026-2275
- Per advisory returned:
  - ID: GHSA-9hjg-9r4m-mvj7 / CVE-2024-47081 / PYSEC-2026-1872
    - Severity: CVSS v3.1 5.3 MEDIUM — CVSS:3.1/AV:N/AC:H/PR:N/UI:R/S:U/C:H/I:N/A:N (OSV, GHSA,
      NVD agree). .netrc credential leak via maliciously-crafted URLs.
    - Published affected range: < 2.32.4 (introduced all previous versions; fixed 2.32.4),
      agreeing across OSV, GHSA, NVD.
    - Applicability to 2.34.2: NOT AFFECTED — pinned 2.34.2 > fixed 2.32.4, outside the '<2.32.4'
      range with no re-introduction after the fix.
    - First fixed version: 2.32.4
  - ID: GHSA-9wx4-h78v-vm56 / CVE-2024-35195 / PYSEC-2026-1873
    - Severity: CVSS v3.1 5.6 MEDIUM — CVSS:3.1/AV:L/AC:H/PR:H/UI:R/S:U/C:H/I:H/A:N (OSV, GHSA,
      NVD agree). Session object does not re-verify TLS after an initial verify=False request.
    - Published affected range: < 2.32.0 (introduced all previous versions; fixed 2.32.0),
      agreeing across OSV, GHSA, NVD.
    - Applicability to 2.34.2: NOT AFFECTED — pinned 2.34.2 > fixed 2.32.0, outside '<2.32.0'.
    - First fixed version: 2.32.0
  - ID: GHSA-gc5v-m9x4-r6x2 / CVE-2026-25645 / PYSEC-2026-2275
    - Severity: sources disagree on score/vector while agreeing on Medium — OSV and NVD-primary
      CVSS v3.1 5.5 (CVSS:3.1/AV:L/AC:L/PR:L/UI:N/S:U/C:N/I:H/A:N); GHSA and NVD-secondary CVSS
      v3.1 4.4 (CVSS:3.1/AV:L/AC:H/PR:L/UI:R/S:U/C:N/I:H/A:N). Predictable temp filename in
      requests.utils.extract_zipped_paths(); ordinary library usage unaffected.
    - Published affected range: < 2.33.0 (fixed 2.33.0), agreeing across OSV, GHSA, NVD.
    - Applicability to 2.34.2: NOT AFFECTED — pinned 2.34.2 > fixed 2.33.0, outside '<2.33.0';
      the severity-score disagreement does not affect this since all sources agree on the range.
    - First fixed version: 2.33.0
- Freshness: latest upstream release reported by PyPI JSON is 2.34.2 (== the pinned version;
  released 2026-05-14; no newer version published), confirmed by both `info.version` and the
  rendered project/#history pages; the pinned version is current (0 releases behind).
- Disposition: NONE-REQUIRED

#### 6. urllib3 == 2.7.0

- Sources queried: OSV.dev (PyPI/urllib3); GitHub Advisory Database (pip/urllib3); NVD (keyword
  `urllib3`); PyPI JSON. Source form and reachability: OSV.dev reachable —
  `GET https://osv.dev/list?ecosystem=PyPI&q=urllib3` returned a **rendered list page** (OSV's
  structured query API is POST-only) of 16 rows (8 PYSEC + 8 GHSA, no ranges on the list view);
  to obtain ranges, OSV's GET-by-id **structured JSON API** `https://api.osv.dev/v1/vulns/<id>`
  was fetched for every distinct advisory (all 19 distinct advisories returned as structured
  JSON). GitHub Advisories reachable —
  `GET https://github.com/advisories?query=ecosystem%3Apip+urllib3` returned a **rendered list
  page** of 19 advisories; ids/aliases cross-checked against OSV and matched. NVD reachable —
  **structured JSON API**, `keywordSearch=urllib3&resultsPerPage=50` returned `totalResults: 21`
  and the summary extracted 17 rows matching the OSV/GHSA set (some CVSS deltas vs GHSA); the 2
  newest advisories (CVE-2026-44431, CVE-2026-44432, published 2026-05-11) were not confirmed in
  the extracted NVD rows, consistent with normal NVD lag (NVD is corroborating-only and this gap
  changes no verdict). PyPI JSON reachable — **structured API**; project-level `info.version` =
  2.7.0 (latest) and version-level 2.7.0/json both reachable.
- Query date (UTC): 2026-08-02
- Advisory IDs returned for this package, any version: GHSA-mf9v-mfxr-j63j / CVE-2026-44432 /
  PYSEC-2026-142; GHSA-qccp-gfcp-xxvc / CVE-2026-44431 / PYSEC-2026-141; GHSA-38jv-5279-wg99 /
  CVE-2026-21441 / PYSEC-2026-1996; GHSA-2xpw-w6gg-jr37 / CVE-2025-66471 / PYSEC-2026-1994;
  GHSA-gm62-xv2j-4w53 / CVE-2025-66418 / PYSEC-2026-1998; GHSA-48p4-8xcf-vxj5 / CVE-2025-50182 /
  PYSEC-2026-1997; GHSA-pq67-6m6q-mj2v / CVE-2025-50181 / PYSEC-2026-1999; GHSA-34jh-p97f-mpxf /
  CVE-2024-37891 / PYSEC-2026-1995; GHSA-g4mx-q9vg-27p4 / CVE-2023-45803 / PYSEC-2023-212;
  GHSA-v845-jxx5-vc9f / CVE-2023-43804 / PYSEC-2023-192; GHSA-gwvm-45gx-3cf8 / CVE-2018-25091 /
  PYSEC-2023-207; GHSA-q2q7-5pp4-w6pg / CVE-2021-33503 / PYSEC-2021-108; GHSA-hmv2-79q8-fv6g /
  CVE-2020-7212 / PYSEC-2020-149; GHSA-5phf-pp7p-vc2r / CVE-2021-28363 / PYSEC-2021-59;
  GHSA-mh33-7rrq-662w / CVE-2019-11324 / PYSEC-2019-133; GHSA-r64q-w8jr-g9qp / CVE-2019-11236 /
  PYSEC-2019-132; GHSA-wqvq-5m8c-6g24 / CVE-2020-26137 / PYSEC-2020-148; GHSA-v4w5-p2hg-8fh6 /
  CVE-2016-9015 / PYSEC-2017-98; GHSA-www2-v7xj-xrc6 / CVE-2018-20060 / PYSEC-2018-32
- Per advisory returned:
  - ID: GHSA-mf9v-mfxr-j63j / CVE-2026-44432 / PYSEC-2026-142
    - Severity: CVSS v3.1 7.5 HIGH (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H); CVSS v4.0
      CVSS:4.0/AV:N/AC:L/AT:P/PR:N/UI:N/VC:N/VI:N/VA:H/SC:N/SI:N/SA:H.
    - Published affected range: introduced 2.6.0, fixed 2.7.0 (2.6.0-2.6.3 affected).
    - Applicability to 2.7.0: NOT AFFECTED — pinned 2.7.0 equals the fixed version and is outside
      the published affected interval [2.6.0, 2.7.0).
    - First fixed version: 2.7.0
  - ID: GHSA-qccp-gfcp-xxvc / CVE-2026-44431 / PYSEC-2026-141
    - Severity: CVSS v3.1 5.3 MEDIUM; CVSS v4.0 5.4.
    - Published affected range: introduced 1.23, fixed 2.7.0 (1.23 through 2.6.3 affected).
    - Applicability to 2.7.0: NOT AFFECTED — pinned 2.7.0 equals the fixed version and is outside
      [1.23, 2.7.0).
    - First fixed version: 2.7.0
  - ID: GHSA-38jv-5279-wg99 / CVE-2026-21441 / PYSEC-2026-1996
    - Severity: CVSS v3.1 CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H (HIGH); CVSS v4.0
      CVSS:4.0/AV:N/AC:L/AT:P/PR:N/UI:N/VC:N/VI:N/VA:H/SC:N/SI:N/SA:H.
    - Published affected range: 1.22 to 2.6.2, fixed in 2.6.3.
    - Applicability to 2.7.0: NOT AFFECTED — pinned 2.7.0 is well above the fixed boundary 2.6.3,
      outside [1.22, 2.6.3).
    - First fixed version: 2.6.3
  - ID: GHSA-2xpw-w6gg-jr37 / CVE-2025-66471 / PYSEC-2026-1994
    - Severity: CVSS v4.0 CVSS:4.0/AV:N/AC:L/AT:P/PR:N/UI:N/VC:N/VI:N/VA:H/SC:N/SI:N/SA:H (HIGH);
      NVD-corroborated 7.5 HIGH.
    - Published affected range: 1.0 through 2.5.0, fixed in 2.6.0.
    - Applicability to 2.7.0: NOT AFFECTED — pinned 2.7.0 exceeds the fixed boundary 2.6.0,
      outside [1.0, 2.6.0).
    - First fixed version: 2.6.0
  - ID: GHSA-gm62-xv2j-4w53 / CVE-2025-66418 / PYSEC-2026-1998
    - Severity: CVSS v4.0 AV:N/AC:L/AT:P/PR:N/UI:N/VC:N/VI:N/VA:H/SC:N/SI:N/SA:H (HIGH);
      NVD-corroborated 7.5 HIGH.
    - Published affected range: introduced 1.24, fixed 2.6.0 (1.24 through 2.5.0 affected).
    - Applicability to 2.7.0: NOT AFFECTED — pinned 2.7.0 exceeds the fixed boundary 2.6.0,
      outside [1.24, 2.6.0).
    - First fixed version: 2.6.0
  - ID: GHSA-48p4-8xcf-vxj5 / CVE-2025-50182 / PYSEC-2026-1997
    - Severity: GHSA CVSS v3.1 5.7 MODERATE; NVD-corroborated 6.1 MEDIUM (score differs between
      sources, same tier).
    - Published affected range: 2.2.0 through 2.4.0, fixed in 2.5.0.
    - Applicability to 2.7.0: NOT AFFECTED — pinned 2.7.0 exceeds the fixed boundary 2.5.0,
      outside [2.2.0, 2.5.0).
    - First fixed version: 2.5.0
  - ID: GHSA-pq67-6m6q-mj2v / CVE-2025-50181 / PYSEC-2026-1999
    - Severity: CVSS v3.1 CVSS:3.1/AV:N/AC:H/PR:L/UI:N/S:U/C:H/I:N/A:N (MODERATE);
      NVD-corroborated 6.1 MEDIUM.
    - Published affected range: introduced 0.2, fixed 2.5.0 (0.2 through 2.4.0 affected).
    - Applicability to 2.7.0: NOT AFFECTED — pinned 2.7.0 exceeds the fixed boundary 2.5.0,
      outside [0.2, 2.5.0).
    - First fixed version: 2.5.0
  - ID: GHSA-34jh-p97f-mpxf / CVE-2024-37891 / PYSEC-2026-1995
    - Severity: CVSS v3.1 CVSS:3.1/AV:N/AC:H/PR:H/UI:N/S:U/C:H/I:N/A:N (MODERATE);
      NVD-corroborated 6.5 MEDIUM.
    - Published affected range: two branches — introduced 0 fixed 1.26.19; introduced 2.0.0 fixed
      2.2.2.
    - Applicability to 2.7.0: NOT AFFECTED — pinned 2.7.0 exceeds both branch fixed boundaries
      (1.26.19 and 2.2.2).
    - First fixed version: 1.26.19 (1.x line) / 2.2.2 (2.x line)
  - ID: GHSA-g4mx-q9vg-27p4 / CVE-2023-45803 / PYSEC-2023-212
    - Severity: CVSS v3.1 CVSS:3.1/AV:A/AC:H/PR:H/UI:N/S:U/C:H/I:N/A:N; NVD-corroborated 4.2
      MEDIUM.
    - Published affected range: two branches — introduced 2.0.0 fixed 2.0.7; introduced 0 fixed
      1.26.18.
    - Applicability to 2.7.0: NOT AFFECTED — pinned 2.7.0 exceeds both branch fixed boundaries
      (2.0.7 and 1.26.18).
    - First fixed version: 2.0.7 (2.x line) / 1.26.18 (1.x line)
  - ID: GHSA-v845-jxx5-vc9f / CVE-2023-43804 / PYSEC-2023-192
    - Severity: CVSS v3.1 7.2 HIGH; NVD-corroborated 8.1 HIGH.
    - Published affected range: two branches — 2.0.0 through 2.0.5 fixed 2.0.6; 0.2 through
      1.26.16 fixed 1.26.17.
    - Applicability to 2.7.0: NOT AFFECTED — pinned 2.7.0 exceeds both branch fixed boundaries
      (2.0.6 and 1.26.17).
    - First fixed version: 2.0.6 (2.x line) / 1.26.17 (1.x line)
  - ID: GHSA-gwvm-45gx-3cf8 / CVE-2018-25091 / PYSEC-2023-207
    - Severity: CVSS v3.1 5.4 MODERATE; NVD-corroborated 6.1 MEDIUM.
    - Published affected range: 0.2 through 1.24.1, fixed in 1.24.2.
    - Applicability to 2.7.0: NOT AFFECTED — pinned 2.7.0 far exceeds the fixed boundary 1.24.2.
    - First fixed version: 1.24.2
  - ID: GHSA-q2q7-5pp4-w6pg / CVE-2021-33503 / PYSEC-2021-108
    - Severity: HIGH vector; NVD-corroborated 7.5 HIGH.
    - Published affected range: 1.25.4 through 1.26.4, fixed in 1.26.5.
    - Applicability to 2.7.0: NOT AFFECTED — pinned 2.7.0 far exceeds the fixed boundary 1.26.5.
    - First fixed version: 1.26.5
  - ID: GHSA-hmv2-79q8-fv6g / CVE-2020-7212 / PYSEC-2020-149
    - Severity: CVSS v3.1 7.5 HIGH; NVD-corroborated 7.5 HIGH.
    - Published affected range: introduced 1.25.2, fixed 1.25.8.
    - Applicability to 2.7.0: NOT AFFECTED — pinned 2.7.0 far exceeds the fixed boundary 1.25.8.
    - First fixed version: 1.25.8
  - ID: GHSA-5phf-pp7p-vc2r / CVE-2021-28363 / PYSEC-2021-59
    - Severity: CVSS v3.1 5.4 MODERATE; NVD-corroborated 6.5 MEDIUM.
    - Published affected range: introduced 1.26.0, fixed 1.26.4 (1.26.0-1.26.3 affected).
    - Applicability to 2.7.0: NOT AFFECTED — pinned 2.7.0 far exceeds the fixed boundary 1.26.4.
    - First fixed version: 1.26.4
  - ID: GHSA-mh33-7rrq-662w / CVE-2019-11324 / PYSEC-2019-133
    - Severity: CVSS v3.0 7.5 HIGH; NVD-corroborated 7.5 HIGH.
    - Published affected range: 0 through 1.24.1, fixed in 1.24.2.
    - Applicability to 2.7.0: NOT AFFECTED — pinned 2.7.0 far exceeds the fixed boundary 1.24.2.
    - First fixed version: 1.24.2
  - ID: GHSA-r64q-w8jr-g9qp / CVE-2019-11236 / PYSEC-2019-132
    - Severity: CVSS v3.0 MODERATE; NVD-corroborated 6.1 MEDIUM.
    - Published affected range: 0 through 1.24.2, fixed in 1.24.3.
    - Applicability to 2.7.0: NOT AFFECTED — pinned 2.7.0 far exceeds the fixed boundary 1.24.3.
    - First fixed version: 1.24.3
  - ID: GHSA-wqvq-5m8c-6g24 / CVE-2020-26137 / PYSEC-2020-148
    - Severity: CVSS v3.1 6.2 MODERATE; NVD-corroborated 6.5 MEDIUM.
    - Published affected range: 0 through 1.25.8, fixed in 1.25.9.
    - Applicability to 2.7.0: NOT AFFECTED — pinned 2.7.0 far exceeds the fixed boundary 1.25.9.
    - First fixed version: 1.25.9
  - ID: GHSA-v4w5-p2hg-8fh6 / CVE-2016-9015 / PYSEC-2017-98
    - Severity: CVSS v3.0 5.3 MODERATE; NVD-corroborated 3.7 LOW (score differs by source, same
      low-moderate tier).
    - Published affected range: 1.17 through 1.18, fixed in 1.18.1.
    - Applicability to 2.7.0: NOT AFFECTED — pinned 2.7.0 far exceeds the fixed boundary 1.18.1.
    - First fixed version: 1.18.1
  - ID: GHSA-www2-v7xj-xrc6 / CVE-2018-20060 / PYSEC-2018-32
    - Severity: CVSS v3.0 CVSS:3.0/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H (CRITICAL);
      NVD-corroborated 9.8 CRITICAL.
    - Published affected range: 0 through 1.22, fixed in 1.23.
    - Applicability to 2.7.0: NOT AFFECTED — pinned 2.7.0 far exceeds the fixed boundary 1.23.
    - First fixed version: 1.23
- Freshness: latest upstream release reported by PyPI JSON is 2.7.0 (== the pinned version;
  uploaded 2026-05-07T16:13:17Z wheel / 16:13:18Z sdist; `info.version` = 2.7.0); the pinned
  version is current (0 releases behind) and is itself the release that fixed the two newest
  advisories (CVE-2026-44431, CVE-2026-44432).
- Disposition: NONE-REQUIRED

#### 7. pymupdf == 1.27.2.3

- Sources queried: OSV.dev (PyPI/pymupdf); GitHub Advisory Database (pip/pymupdf); NVD (keyword
  `pymupdf`); PyPI JSON; plus supplementary informational `mupdf` queries. Source form and
  reachability: OSV.dev reachable — `GET https://osv.dev/list?ecosystem=PyPI&q=pymupdf` returned
  a **rendered list page** (OSV's structured query API is POST-only) of 2 entries
  (PYSEC-2026-3001 and GHSA-cxqh-p2w9-fmr7, the same underlying path-traversal issue). GitHub
  Advisories reachable — `GET https://github.com/advisories?query=ecosystem%3Apip+pymupdf`
  returned a **rendered list page** of 2 entries: GHSA-cxqh-p2w9-fmr7/CVE-2026-3029 (genuine
  PyMuPDF) and GHSA-m8gf-v64p-gfmg (package "BabelDOC", surfaced only by fuzzy full-text match on
  the word "pymupdf"; excluded). NVD reachable — **structured JSON API**,
  `keywordSearch=pymupdf&resultsPerPage=50` returned `totalResults: 1` (CVE-2026-3029),
  corroborating OSV/GHSA but with a differing self-computed CVSS. PyPI JSON reachable —
  **structured API** for freshness and to positively confirm 1.27.2.3 is a genuine published
  release; the bulk /json "releases" object was too large for the harness to enumerate
  exhaustively, so the version-scoped endpoints pymupdf/1.27.2.3/json and pymupdf/1.28.0/json
  were used and both resolved. Supplementary (non-primary, informational — the plan flags
  bundled-MuPDF advisories as in scope): `GET https://osv.dev/list?ecosystem=PyPI&q=mupdf`
  reachable, 0 results in the PyPI ecosystem; `GET https://github.com/advisories?query=mupdf`
  reachable, a **rendered list page** of 25 GHSA entries against a distinct "MuPDF" package
  entity (the C library), none tagged to the "pymupdf" PyPI package.
- Query date (UTC): 2026-08-02
- Advisory IDs returned for this package, any version: GHSA-cxqh-p2w9-fmr7 / CVE-2026-3029 /
  PYSEC-2026-3001 (genuine pymupdf). Additionally, a MuPDF-core-library CVE set exists under the
  GHSA "MuPDF" package entity (25 entries, e.g. GHSA-6jrq-hjxp-2x5r/CVE-2026-3308,
  GHSA-39p9-g2pq-q8r7/CVE-2026-25556, GHSA-82r2-3cm6-cxw2/CVE-2026-7233, and 22 further), which
  is NOT returned by the primary "ecosystem:pip pymupdf" / OSV PyPI queries.
- Per advisory returned:
  - ID: GHSA-cxqh-p2w9-fmr7 / CVE-2026-3029 / PYSEC-2026-3001 (one vulnerability, three ID
    namespaces)
    - Severity: GHSA/OSV CVSS v4.0 6.9 Medium —
      CVSS:4.0/AV:L/AC:L/AT:N/PR:N/UI:N/VC:N/VI:H/VA:N/SC:N/SI:N/SA:N. NVD (corroborating,
      disagrees) CVSS v3.1 7.5 HIGH primary (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H) and
      8.2 HIGH secondary (CVSS:3.1/AV:L/AC:L/PR:L/UI:R/S:C/C:H/I:H/A:H).
    - Published affected range: >=1.26.5, <1.26.7 (OSV/GHSA: introduced 1.26.5, fixed 1.26.7;
      affected versions enumerated 1.26.5 and 1.26.6). NVD phrases it "1.26.5 through 1.26.7"
      (ambiguous on 1.26.7 inclusion) but this does not change the verdict.
    - Applicability to 1.27.2.3: NOT AFFECTED — pinned 1.27.2.3 has minor version 27, strictly
      greater than the affected range's upper bound (minor 26; <1.26.7 per GHSA/OSV, or at most
      <=1.26.7 under NVD's looser phrasing); released 2026-04-24, after the 1.26.7 fix. Outside
      the range under every source regardless of the boundary ambiguity.
    - First fixed version: 1.26.7
  - ID: MuPDF-core-library CVE set (GHSA "MuPDF" package entity — 25 entries; NOT surfaced by
    the primary pip/pymupdf or OSV PyPI queries)
    - Severity: not resolved — the 25 entries span Low to Critical; not individually scored here
      because applicability to this pinned build could not be established (see reason).
    - Published affected range: not resolved to the pinned build — several stated ranges (e.g.
      "through 1.27.0", "1.23.0 through 1.27.0", "up to 1.28.0") numerically overlap the pymupdf
      1.27.x/1.28.x version space, but MuPDF-the-C-library and PyMuPDF-the-Python-binding are
      versioned independently by separate projects, and no queried source states which MuPDF
      core build pymupdf==1.27.2.3 embeds.
    - Applicability to 1.27.2.3: INDETERMINATE — pymupdf bundles the MuPDF C library, but neither
      PyPI's metadata for 1.27.2.3 nor the pymupdf-scoped OSV/GHSA results state the embedded
      MuPDF core version/commit, and no GET-only source available here maps pymupdf==1.27.2.3 to
      a specific MuPDF core version to compare against those ranges. Per the applicability rubric,
      an unresolvable/ambiguous mapping is INDETERMINATE, not NOT AFFECTED.
    - First fixed version: n/a — not resolved (varies per advisory; moot until the embedded core
      version is identified)
- Additionally: no queried source reports the bundled MuPDF core version for pymupdf==1.27.2.3;
  the 25-entry MuPDF advisory set targets the MuPDF C library, not the Python binding.
- Freshness: latest upstream release reported by PyPI JSON is 1.28.0, released
  2026-06-29T09:03:30Z; the pinned 1.27.2.3 is confirmed a genuine published release via its
  version-scoped endpoint, released 2026-04-24T14:09:17Z. The pin is NOT current — at least one
  minor release behind (1.27.2.3 -> 1.28.0), roughly two months older than the latest; the exact
  "N releases behind" is not determinable (the intervening 1.27.x/1.28.x list could not be
  exhaustively enumerated through this GET-only harness).
- Disposition: OWNER-DECISION-REQUIRED-AT-P6

## Verdict boundary

All six pinned egress-stack distributions — certifi, chardet, charset-normalizer, idna,
requests, and urllib3 — returned zero advisories applicable to the audited pin: every advisory
found (3 for certifi, none for chardet, none for charset-normalizer, 2 for idna, 3 for requests,
19 for urllib3) is NOT AFFECTED or none was found, so all six are disposed NONE-REQUIRED. The
seventh distribution, pymupdf 1.27.2.3, splits: the one advisory scoped to the PyMuPDF Python
binding — GHSA-cxqh-p2w9-fmr7 / CVE-2026-3029 / PYSEC-2026-3001 (GHSA/OSV CVSS v4.0 6.9 Medium;
NVD CVSS v3.1 7.5 HIGH primary / 8.2 HIGH secondary; affected >=1.26.5,<1.26.7) — is NOT AFFECTED
at the pin; but the separately-tracked MuPDF C-library advisory set (25 GHSA entries under the
distinct "MuPDF" entity, whose stated ranges numerically overlap the 1.27.x/1.28.x space) is
INDETERMINATE, because no GET-only source maps pymupdf==1.27.2.3 to a specific bundled MuPDF core
version — its disposition is OWNER-DECISION-REQUIRED-AT-P6. Aggregate freshness: four pins are
current (chardet, idna, requests, urllib3) and three are behind upstream (certifi at least 1
release / ~5 weeks; charset-normalizer 2 releases; pymupdf at least 1 minor, 1.27.2.3 -> 1.28.0).
No acceptance claim is made here.

G2-P3 supplies a result, not a decision. Owner acceptance of any residual named above
is required at G2-P6, which couples P3's CVE result to the hostile-native-PDF residual
(`docs/campaign-records/2026-08-02-g1-grouped-gate-verdict.md:57-58`). G2-P8 remains a
separate explicit live-run authorization. G2-P1 and G2-P2 remain OPEN and BLOCKING, and
the child-env half of the extras sub-clause is still owed. This record is not a security
clearance for the live run.
