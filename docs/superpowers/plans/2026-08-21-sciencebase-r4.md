# ScienceBase Python Binding Correction R4 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every SQLite DELETE-mode rollback journal owner/SYSTEM-only at birth while preserving D-AROOT's protected non-inheritable DACL and restoring the durable `reservation.db` to the unchanged strict custody oracle before publication.

**Architecture:** Keep the existing create-once, handle-pinned staging/publish path. Add one Windows reservation-security component that (1) installs a duplicated thread impersonation token whose default DACL is exactly owner/SYSTEM, (2) verifies the transient journal with its own unprotected-explicit oracle while the dirty transaction is paused, and (3) verifies cleanup after commit/rollback. Extend the existing Windows custody backend with an idempotent handle-based full-DACL replacement for the durable database; runtime code verifies but never repairs the durable file.

**Tech Stack:** Python 3.12.10, stdlib `ctypes`, Windows Advapi32/Kernel32 APIs, SQLite rollback journal mode `DELETE`, pytest.

## Global Constraints

- D-AROOT remains protected and non-inheritable: owner and SYSTEM `FILE_ALL_ACCESS` only.
- `reservation.db` must satisfy the unchanged durable oracle `(owner=True, protected=True, exact owner/SYSTEM DACL=True)`.
- A transient `*-journal` must be unprotected but contain exactly two explicit, non-inherited, non-inheritable allow ACEs: owner and SYSTEM `FILE_ALL_ACCESS`.
- The process primary token and its default DACL must never be changed; impersonation is thread-local and must be restored fail-closed.
- SQLite remains in `DELETE` mode; WAL, PERSIST, TRUNCATE, MEMORY, OFF, a custom VFS, and post-birth journal ACL repair are forbidden.
- No live execution, actual elevation, signing, key access, custody writes, commit, push, or attempt spend.
- Use only focused tests needed for this correction.

---

### Task 1: Durable database full-DACL replacement

**Files:**
- Modify: `backend/app/services/sciencebase_spent_marker.py`
- Modify: `backend/tests/test_sciencebase_spent_marker.py`
- Modify: `backend/app/services/sciencebase_live_readiness.py`
- Modify: `backend/tests/test_sciencebase_live_readiness.py`

**Interfaces:**
- Consumes: the already pinned staging handle in `publish_new_initialized_file`.
- Produces: `AtomicCustodyBackend.resecure(handle)`, `WindowsMarkerBackend.resecure(handle)`, and `publish_new_initialized_file(..., resecure_after_initialize=True)`.

- [x] **Step 1: Write the failing unit tests**

Add tests proving that requested re-securing occurs after initialization and before publish, and that a re-securing failure leaves the canonical path absent with code `custody_resecure_failed`. The fake backend records `resecure` and changes its file security posture to `(True, True, True)`.

- [x] **Step 2: Run the RED tests**

Run:

```powershell
python -m pytest backend/tests/test_sciencebase_spent_marker.py -q -k resecure
```

Expected: failure because the protocol, keyword, and `resecure` operation do not exist.

- [x] **Step 3: Implement the smallest handle-based replacement**

Use the existing protected owner/SYSTEM security descriptor and call:

```python
SetSecurityInfo(
    handle,
    SE_FILE_OBJECT,
    OWNER_SECURITY_INFORMATION
    | DACL_SECURITY_INFORMATION
    | PROTECTED_DACL_SECURITY_INFORMATION,
    owner_sid,
    None,
    exact_dacl,
    None,
)
```

When `resecure_after_initialize=True`, call it after `initialize(staging)` returns and before publish; re-check the same pinned staging identity with `secure() == (True, True, True)`. Translate any replacement or recheck failure to `CustodyHold("custody_resecure_failed")`.

- [x] **Step 4: Wire initialization and verify GREEN**

Call `publish_new_initialized_file(database, initialize, resecure_after_initialize=True)`. Map `custody_resecure_failed` to `LiveReadinessHold("reservation_database_resecure_failed")` and keep all existing mappings unchanged.

Run:

```powershell
python -m pytest backend/tests/test_sciencebase_spent_marker.py backend/tests/test_sciencebase_live_readiness.py -q -k "resecure or initialize_reservation_database"
```

Expected: selected tests pass.

### Task 2: Birth-token scope and dedicated transient-journal oracle

**Files:**
- Create: `backend/app/services/sciencebase_reservation_security.py`
- Create: `backend/tests/test_sciencebase_reservation_security.py`
- Modify: `backend/app/services/sciencebase_live_readiness.py`
- Modify: `backend/tests/test_sciencebase_live_readiness.py`

**Interfaces:**
- Produces: `ReservationSecurityHold(code)`, `WindowsReservationSecurity(root)`, `birth_scope()`, `verify_database(path)`, `verify_transient_journal(database, journal)`, and `verify_journal_absent(journal)`.
- Consumes: `WindowsMarkerBackend` handle, identity, strict durable security, final-path, and token helpers.

- [x] **Step 1: Correct the existing native RED expectation**

Change the initializer journal proof to require an unprotected journal with exactly two explicit ACEs and no inheritance flags. Add unit tests for these stable failures:

```python
"reservation_birth_token_invalid"
"reservation_birth_token_restore_failed"
"reservation_journal_missing"
"reservation_journal_binding_invalid"
"reservation_journal_security_invalid"
"reservation_journal_cleanup_indeterminate"
```

- [x] **Step 2: Run the native RED proof**

Run:

```powershell
python -m pytest backend/tests/test_sciencebase_live_readiness.py -q -k observes_delete_journal
```

Expected: failure showing the current journal includes an extra logon/default-DACL ACE or otherwise fails the exact transient posture.

- [x] **Step 3: Implement the duplicated thread-token scope**

Duplicate the effective process token as an impersonation token. Before use, verify its `TokenUser` and `TokenOwner` equal the expected root owner; replace only the duplicate token's `TokenDefaultDacl` with an ACL containing owner and SYSTEM `FILE_ALL_ACCESS` ACEs with flags `0`; read it back and verify it exactly. Assign it only to the calling thread. On exit, restore the prior thread token or remove impersonation, verify restoration, and close all duplicated handles.

- [x] **Step 4: Implement the journal oracle**

Open root, database, and exact `database.name + "-journal"` by no-follow handles without delete sharing. Require ordinary non-reparse, link-count-one files on the same volume, exact final path and direct parent, root/database identity stability before and after, journal owner equal to the frozen owner, unprotected DACL, and exactly two explicit allow ACEs with flags `0` and `FILE_ALL_ACCESS`. `verify_journal_absent` must distinguish not-found from residue/indeterminate access.

- [x] **Step 5: Wire initialization and verify GREEN**

Enclose connect, `BEGIN IMMEDIATE`, schema/write, journal oracle, commit/rollback, and close in `birth_scope()`. Run the journal oracle after the first dirty write and before commit, then require absence after commit or rollback.

Run:

```powershell
python -m pytest backend/tests/test_sciencebase_reservation_security.py backend/tests/test_sciencebase_live_readiness.py -q -k "reservation_security or observes_delete_journal or initialize_reservation_database"
```

Expected: selected tests pass and the native journal posture is unprotected with only owner/SYSTEM explicit full-control ACEs.

### Task 3: Runtime dirty-transaction lifecycle and negative ACL coverage

**Files:**
- Modify: `backend/app/services/connector_egress_transport.py`
- Modify: `backend/tests/test_egress_effect_boundary.py`
- Modify: `backend/tests/test_sciencebase_live_readiness.py`
- Modify: `tests/test_sciencebase_no_signature_rehearsal.py`
- Modify: `docs/superpowers/specs/2026-08-19-sb-python-design.md`

**Interfaces:**
- `ReservationStore(..., reservation_security=None)` defaults to `WindowsReservationSecurity` and accepts a focused fake in unit tests.
- Every actual write in `reserve()` and `write_sciencebase_live_event()` uses `birth_scope()`, observes the journal after the dirty insert, verifies absence after commit/rollback, and closes SQLite before leaving the scope.
- `_revalidate_identity()` additionally calls `verify_database()` and maps failure to `reservation_database_security_invalid`; it never repairs security.

- [x] **Step 1: Write failing lifecycle tests**

Use a recording fake security component to prove the order `birth-enter -> dirty insert -> journal verify -> commit/rollback -> journal absent -> connection close -> birth-exit` for reservation and live-event writes. Prove existing-row/no-write branches do not demand a journal. Add negative fake-oracle cases for durable extra/inherited ACLs, journal extra/inherited/deny/logon ACLs, cleanup residue, and restore failure.

- [x] **Step 2: Run RED**

Run:

```powershell
python -m pytest backend/tests/test_egress_effect_boundary.py backend/tests/test_sciencebase_live_readiness.py -q -k "journal or security or reservation_is_committed or closeout"
```

Expected: failures because runtime writes do not yet invoke the security component.

- [x] **Step 3: Implement the two write-path integrations**

Add the injected/default security component, call durable verification during identity revalidation, and wrap only the two shared dirty-write methods. Because GO-consumption, terminal, and closeout all call `write_sciencebase_live_event`, this covers all live-event writes without duplicating policy in the callers. Translate security failures to their stable reason codes and preserve existing business dispositions.

- [x] **Step 4: Run focused ordinary lifecycle GREEN**

Run:

```powershell
python -m pytest backend/tests/test_sciencebase_spent_marker.py backend/tests/test_sciencebase_reservation_security.py backend/tests/test_egress_effect_boundary.py backend/tests/test_sciencebase_live_readiness.py tests/test_sciencebase_no_signature_rehearsal.py -q
```

Expected: all selected tests pass; Windows-only tests have zero skips on the owner host.

- [x] **Step 5: Update the approved design and run final static checks**

Replace the rejected ObjectInherit-only R3 passage with the approved R4 rules and stable failure codes. Run:

```powershell
python -m ruff check backend/app/services/sciencebase_spent_marker.py backend/app/services/sciencebase_reservation_security.py backend/app/services/connector_egress_transport.py backend/app/services/sciencebase_live_readiness.py backend/tests/test_sciencebase_spent_marker.py backend/tests/test_sciencebase_reservation_security.py backend/tests/test_egress_effect_boundary.py backend/tests/test_sciencebase_live_readiness.py tests/test_sciencebase_no_signature_rehearsal.py
git diff --check
```

Expected: Ruff passes and `git diff --check` reports no whitespace errors. Do not commit or push.
