# 08D — Candidate B OpenDataLoader Non-Interference Proof Sequence

## Purpose

Prove that Candidate B v1 stayed a workbench-only comparator and did not interfere with the current lower-layer owner path.

---

## A. Required sequence

### Step 1 — baseline before Candidate B
Run the existing lower-layer proof unchanged.
If it does not pass, stop.

### Step 2 — Candidate B workbench run
Run Candidate B only through the approved tests/report-side workbench surfaces.

### Step 3 — allowlist / output-root check
Confirm that:
- no files outside the approved Candidate B allowlist were added or modified
- no outputs escaped the approved Candidate B output roots

### Step 4 — baseline after Candidate B
Run the existing lower-layer proof unchanged again.

### Step 5 — compare before/after posture
Confirm:
- baseline proof still passes
- no service-layer file drift occurred
- no dependency-surface drift occurred
- no owner-path semantic expectations were weakened in the compare report

---

## B. Required evidence

The proof record must capture at least:
- baseline proof status before Candidate B
- baseline proof status after Candidate B
- touched-file inventory
- raw-output root inventory
- interference result (`passed` / `failed`)
- failure details if failed

---

## C. Hard failure conditions

Candidate B fails non-interference if any of the following occurs:
- a forbidden file is modified
- a forbidden output location receives new output
- the baseline lower-layer proof no longer passes after Candidate B work
- the compare report attempts to substitute non-equivalent ODL fields for owner-path truth

---

## D. Why this matters

A touch policy by itself is not enough.
The repo already has an owner path and proof harness.
Candidate B only remains safe if it proves it did not disturb either one.
