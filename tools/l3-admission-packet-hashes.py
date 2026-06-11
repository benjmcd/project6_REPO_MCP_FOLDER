from __future__ import annotations

"""Admission packet hash helper for Layer 3 SEC/XBRL nonlocal production admission.

Hash basis: SHA-256 of the exact evidence file bytes (no encoding coercion).
Modes:
  compute  -- print sha256 hex for one or more evidence files
  fill     -- given a packet template JSON and field->file mapping, write a filled copy
  verify   -- given a filled packet JSON and field->file mapping, check hashes match

Usage examples:
  python tools/l3-admission-packet-hashes.py compute path/to/approval_record.pdf
  python tools/l3-admission-packet-hashes.py fill \\
      --packet template.json --out filled.json \\
      --field approval_record_hash:path/to/approval_record.pdf \\
      --field in_app_auth_evidence_hash:path/to/auth_evidence.json
  python tools/l3-admission-packet-hashes.py verify \\
      --packet filled.json \\
      --field approval_record_hash:path/to/approval_record.pdf \\
      --field in_app_auth_evidence_hash:path/to/auth_evidence.json
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Hash computation
# ---------------------------------------------------------------------------

def _sha256_file(path: Path) -> str:
    """Return lowercase 64-char SHA-256 hex of the exact file bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Field mapping parser
# ---------------------------------------------------------------------------

def _parse_field_mapping(pairs: list[str]) -> dict[str, Path]:
    """Parse ``field:path`` pairs into a dict.  Aborts on malformed input."""
    mapping: dict[str, Path] = {}
    for pair in pairs:
        if ":" not in pair:
            _die(f"invalid --field value {pair!r}: expected 'field_name:file_path'")
        field, _, file_path = pair.partition(":")
        field = field.strip()
        if not field:
            _die(f"empty field name in --field value {pair!r}")
        mapping[field] = Path(file_path)
    return mapping


def _die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_compute(args: argparse.Namespace) -> int:
    """Print sha256 hex for each file, one per line, formatted for packet paste."""
    files: list[Path] = [Path(p) for p in args.files]
    errors = 0
    for path in files:
        if not path.is_file():
            print(f"ERROR: not a file: {path}", file=sys.stderr)
            errors += 1
            continue
        digest = _sha256_file(path)
        print(f"{digest}  {path}")
    return 1 if errors else 0


def cmd_fill(args: argparse.Namespace) -> int:
    """Fill hash fields in a packet template and write the result."""
    packet_path = Path(args.packet)
    out_path = Path(args.out)

    if not packet_path.is_file():
        _die(f"packet file not found: {packet_path}")
    if out_path.exists():
        _die(
            f"output file already exists: {out_path}\n"
            "  fill refuses to overwrite an existing file; remove it first."
        )

    try:
        packet = json.loads(packet_path.read_bytes())
    except (OSError, json.JSONDecodeError) as exc:
        _die(f"could not read packet JSON: {exc}")

    if not isinstance(packet, dict):
        _die("packet JSON must be a JSON object (dict)")

    # Remove _template_note if present -- diagnostic script flags it as
    # unexpected_packet_field.
    packet.pop("_template_note", None)

    mapping = _parse_field_mapping(args.field)

    errors: list[str] = []
    for field, file_path in mapping.items():
        if not file_path.is_file():
            errors.append(f"  {field}: evidence file not found: {file_path}")
            continue
        packet[field] = _sha256_file(file_path)

    if errors:
        print("ERROR: one or more evidence files missing:", file=sys.stderr)
        for e in errors:
            print(e, file=sys.stderr)
        return 1

    out_path.write_text(
        json.dumps(packet, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )
    print(f"Wrote filled packet: {out_path}")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    """Recompute hashes from evidence files and report match/mismatch per field."""
    packet_path = Path(args.packet)
    if not packet_path.is_file():
        _die(f"packet file not found: {packet_path}")

    try:
        packet = json.loads(packet_path.read_bytes())
    except (OSError, json.JSONDecodeError) as exc:
        _die(f"could not read packet JSON: {exc}")

    if not isinstance(packet, dict):
        _die("packet JSON must be a JSON object (dict)")

    mapping = _parse_field_mapping(args.field)

    mismatches: list[str] = []
    for field, file_path in mapping.items():
        if not file_path.is_file():
            mismatches.append(
                f"  MISSING_FILE  {field}: evidence file not found: {file_path}"
            )
            continue
        expected = packet.get(field)
        actual = _sha256_file(file_path)
        if expected is None:
            mismatches.append(
                f"  FIELD_ABSENT  {field}: not present in packet"
            )
        elif expected == actual:
            print(f"  MATCH         {field}")
        else:
            mismatches.append(
                f"  MISMATCH      {field}\n"
                f"                packet:   {expected}\n"
                f"                computed: {actual}"
            )

    if mismatches:
        print("VERIFY FAILED:", file=sys.stderr)
        for m in mismatches:
            print(m, file=sys.stderr)
        return 1

    print("All fields verified OK.")
    return 0


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="l3-admission-packet-hashes.py",
        description=(
            "Layer 3 SEC/XBRL admission packet hash helper.\n\n"
            "Hash basis: SHA-256 of the exact evidence file bytes.\n"
            "Output hash format: 64 lowercase hexadecimal characters.\n\n"
            "The diagnostic script that consumes filled packets is:\n"
            "  diagnostics/assessment/sec-xbrl-nonlocal-admission-disposition.py\n"
            "Expected filenames in --packet-dir mode:\n"
            "  sec-xbrl-final-admission-packet.json\n"
            "  sec-xbrl-backfill-disposition-packet.json\n"
            "Templates:\n"
            "  next_milestone_plans/Layer3_planning_docs/"
            "sec-xbrl-final-admission-packet-template.json\n"
            "  next_milestone_plans/Layer3_planning_docs/"
            "sec-xbrl-backfill-disposition-packet-template.json"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="mode", metavar="MODE")
    sub.required = True

    # compute
    p_compute = sub.add_parser(
        "compute",
        help="Print sha256 hex for one or more evidence files.",
        description=(
            "Compute SHA-256 (64 lowercase hex chars) of each file's exact bytes.\n"
            "Output format: '<hash>  <path>' — suitable for direct paste into packet hash fields."
        ),
    )
    p_compute.add_argument(
        "files",
        nargs="+",
        metavar="FILE",
        help="One or more evidence files to hash.",
    )

    # fill
    p_fill = sub.add_parser(
        "fill",
        help="Fill hash fields in a packet template and write a completed copy.",
        description=(
            "Read a packet template JSON, compute SHA-256 hashes for named evidence\n"
            "files, write the result to --out.  The _template_note field is removed\n"
            "automatically (the diagnostic script flags it as unexpected_packet_field).\n"
            "Refuses to overwrite an existing output file.  Non-hash fields are left\n"
            "untouched -- only the fields named in --field are modified."
        ),
    )
    p_fill.add_argument(
        "--packet",
        required=True,
        metavar="TEMPLATE.json",
        help="Path to the packet template JSON.",
    )
    p_fill.add_argument(
        "--out",
        required=True,
        metavar="FILLED.json",
        help="Destination path for the filled packet (must not already exist).",
    )
    p_fill.add_argument(
        "--field",
        action="append",
        default=[],
        metavar="FIELD:FILE",
        help=(
            "Map a packet hash field to its evidence file: 'field_name:path/to/file'.\n"
            "Repeat for each hash field.  Example:\n"
            "  --field approval_record_hash:path/to/approval_record.pdf\n"
            "  --field in_app_auth_evidence_hash:path/to/auth_evidence.json"
        ),
    )

    # verify
    p_verify = sub.add_parser(
        "verify",
        help="Recompute hashes from evidence files and report match/mismatch.",
        description=(
            "Recompute SHA-256 hashes from the named evidence files and compare\n"
            "them against the values stored in the filled packet JSON.\n"
            "Exits nonzero if any field is missing, mismatched, or its evidence\n"
            "file is absent."
        ),
    )
    p_verify.add_argument(
        "--packet",
        required=True,
        metavar="FILLED.json",
        help="Path to the filled packet JSON.",
    )
    p_verify.add_argument(
        "--field",
        action="append",
        default=[],
        metavar="FIELD:FILE",
        help="Map a packet hash field to its evidence file (same format as fill mode).",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.mode == "compute":
        return cmd_compute(args)
    if args.mode == "fill":
        return cmd_fill(args)
    if args.mode == "verify":
        return cmd_verify(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
