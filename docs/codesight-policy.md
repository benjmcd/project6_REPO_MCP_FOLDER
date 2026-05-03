# Codesight Policy

`.codesight` is generated navigation, not implementation authority.

Use it only to find candidate files quickly. Before changing behavior, read the actual tracked source, tests, scripts, and CI in the focused worktree.

## Freshness

A local `.codesight` folder should carry a local freshness marker such as `.codesight/freshness.json` with:

- `source_commit`: the commit used to generate the navigation files
- `generated_at`: generation timestamp
- `command`: regeneration command

If the marker is missing, malformed, or points at a different commit, treat `.codesight` counts and maps as stale hints only.

## Validation

`python ./tools/validate_structure.py` warns when a local `.codesight` folder exists without a freshness marker. The warning is intentionally non-fatal because `.codesight` is local generated state and may be absent from clean worktrees.
