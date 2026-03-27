param(
    [string]$DestinationRoot = "C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\jules_repo"
)

$ErrorActionPreference = "Stop"

$sourceRoot = "C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER"

function Convert-ToLongPath {
    param([string]$Path)

    $fullPath = [System.IO.Path]::GetFullPath($Path)
    if ($fullPath.StartsWith("\\?\")) {
        return $fullPath
    }
    return "\\?\$fullPath"
}

function New-MirrorDirectory {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        [System.IO.Directory]::CreateDirectory((Convert-ToLongPath -Path $Path)) | Out-Null
    }
}

function Copy-MirrorFile {
    param(
        [string]$SourcePath,
        [string]$DestinationPath
    )

    $destinationParent = Split-Path -Parent $DestinationPath
    New-MirrorDirectory -Path $destinationParent
    [System.IO.File]::Copy(
        (Convert-ToLongPath -Path $SourcePath),
        (Convert-ToLongPath -Path $DestinationPath),
        $true
    )
}

function Copy-MirrorTree {
    param(
        [string]$SourcePath,
        [string]$DestinationPath,
        [string[]]$ExcludeDirectories = @("__pycache__", ".pytest_cache"),
        [string[]]$ExcludeFilePatterns = @("*.pyc", "*.pyo")
    )

    New-MirrorDirectory -Path $DestinationPath

    $sourcePrefix = [System.IO.Path]::GetFullPath($SourcePath)

    Get-ChildItem -LiteralPath $SourcePath -Recurse -Force | ForEach-Object {
        $fullName = [System.IO.Path]::GetFullPath($_.FullName)
        $relativePath = $fullName.Substring($sourcePrefix.Length).TrimStart("\", "/")

        if ([string]::IsNullOrWhiteSpace($relativePath)) {
            return
        }

        $pathParts = $relativePath -split "[\\/]"
        foreach ($excludedDirectory in $ExcludeDirectories) {
            if ($pathParts -contains $excludedDirectory) {
                return
            }
        }

        if (-not $_.PSIsContainer) {
            foreach ($pattern in $ExcludeFilePatterns) {
                if ($_.Name -like $pattern) {
                    return
                }
            }
        }

        $destinationItem = Join-Path $DestinationPath $relativePath
        if ($_.PSIsContainer) {
            New-MirrorDirectory -Path $destinationItem
        }
        else {
            $parent = Split-Path -Parent $destinationItem
            New-MirrorDirectory -Path $parent
            [System.IO.File]::Copy(
                (Convert-ToLongPath -Path $_.FullName),
                (Convert-ToLongPath -Path $destinationItem),
                $true
            )
        }
    }
}

if (Test-Path -LiteralPath $DestinationRoot) {
    $existingChildren = Get-ChildItem -LiteralPath $DestinationRoot -Force
    if ($existingChildren.Count -gt 0) {
        throw "Destination already exists and is not empty: $DestinationRoot"
    }
}
else {
    New-MirrorDirectory -Path $DestinationRoot
}

$backendRoot = Join-Path $DestinationRoot "backend"
$plansRoot = Join-Path $DestinationRoot "frontend_UI_plans"
$docsRoot = Join-Path $DestinationRoot "docs\nrc_adams"
$docsPostgresRoot = Join-Path $DestinationRoot "docs\postgres"
$nextMilestoneRoot = Join-Path $DestinationRoot "next_milestone_plans"
$julesWorkspaceRoot = Join-Path $plansRoot "agent_workspaces\jules"

New-MirrorDirectory -Path $backendRoot
New-MirrorDirectory -Path $plansRoot
New-MirrorDirectory -Path $docsRoot
New-MirrorDirectory -Path $docsPostgresRoot
New-MirrorDirectory -Path $nextMilestoneRoot
New-MirrorDirectory -Path $julesWorkspaceRoot

# Core repo context
Copy-MirrorFile -SourcePath (Join-Path $sourceRoot "README.md") -DestinationPath (Join-Path $DestinationRoot "README.md")
Copy-MirrorFile -SourcePath (Join-Path $sourceRoot "project6.ps1") -DestinationPath (Join-Path $DestinationRoot "project6.ps1")

# Backend code surface needed for Slice 01
Copy-MirrorFile -SourcePath (Join-Path $sourceRoot "backend\main.py") -DestinationPath (Join-Path $DestinationRoot "backend\main.py")
Copy-MirrorFile -SourcePath (Join-Path $sourceRoot "backend\requirements.txt") -DestinationPath (Join-Path $DestinationRoot "backend\requirements.txt")
Copy-MirrorFile -SourcePath (Join-Path $sourceRoot "backend\alembic.ini") -DestinationPath (Join-Path $DestinationRoot "backend\alembic.ini")
Copy-MirrorFile -SourcePath (Join-Path $sourceRoot "backend\.env.example") -DestinationPath (Join-Path $DestinationRoot "backend\.env.example")
Copy-MirrorTree -SourcePath (Join-Path $sourceRoot "backend\alembic") -DestinationPath (Join-Path $DestinationRoot "backend\alembic")
Copy-MirrorFile -SourcePath (Join-Path $sourceRoot "backend\app\__init__.py") -DestinationPath (Join-Path $DestinationRoot "backend\app\__init__.py")
Copy-MirrorTree -SourcePath (Join-Path $sourceRoot "backend\app\api") -DestinationPath (Join-Path $DestinationRoot "backend\app\api")
Copy-MirrorTree -SourcePath (Join-Path $sourceRoot "backend\app\core") -DestinationPath (Join-Path $DestinationRoot "backend\app\core")
Copy-MirrorTree -SourcePath (Join-Path $sourceRoot "backend\app\db") -DestinationPath (Join-Path $DestinationRoot "backend\app\db")
Copy-MirrorTree -SourcePath (Join-Path $sourceRoot "backend\app\models") -DestinationPath (Join-Path $DestinationRoot "backend\app\models")
Copy-MirrorTree -SourcePath (Join-Path $sourceRoot "backend\app\schemas") -DestinationPath (Join-Path $DestinationRoot "backend\app\schemas")
Copy-MirrorTree -SourcePath (Join-Path $sourceRoot "backend\app\services") -DestinationPath (Join-Path $DestinationRoot "backend\app\services")
Copy-MirrorTree -SourcePath (Join-Path $sourceRoot "backend\tests") -DestinationPath (Join-Path $DestinationRoot "backend\tests")

# Golden runtime fixture committed into the mirror repo.
Copy-MirrorTree `
    -SourcePath (Join-Path $sourceRoot "backend\app\storage_test_runtime\lc_e2e\20260327_062011") `
    -DestinationPath (Join-Path $DestinationRoot "backend\app\storage_test_runtime\lc_e2e\20260327_062011") `
    -ExcludeDirectories @("__pycache__", ".pytest_cache") `
    -ExcludeFilePatterns @("*.pyc", "*.pyo")

# Planning docs copied as authority references for the cloud agent.
$planningDocs = @(
    "README.md",
    "agent_bakeoff_brief.md",
    "agent_bakeoff_execution_protocol.md",
    "agent_bakeoff_local_setup_phase1.md",
    "agent_bakeoff_phase1_brief.md",
    "agent_bakeoff_phase1_scope.md",
    "agent_bakeoff_phase1_implementation_blueprint.md",
    "agent_bakeoff_phase1_validation_plan.md",
    "agent_bakeoff_phase1_submission_checklist.md",
    "agent_bakeoff_phase1_rubric.md",
    "agent_bakeoff_prompt_antigravity_phase1.md",
    "agent_bakeoff_prompt_jules_phase1.md",
    "agent_bakeoff_rubric.md",
    "agent_bakeoff_scope_slice_01.md",
    "agent_bakeoff_submission_checklist.md",
    "nrc_aps_review_ui_canonical_graph_registry.md",
    "nrc_aps_review_ui_data_contract.md",
    "nrc_aps_review_ui_dependency_and_asset_strategy.md",
    "nrc_aps_review_ui_example_payloads.md",
    "nrc_aps_review_ui_implementation_blueprint.md",
    "nrc_aps_review_ui_mapping_and_reviewability_rules.md",
    "nrc_aps_review_ui_open_decisions.md",
    "nrc_aps_review_ui_spec.md",
    "nrc_aps_review_ui_validation_plan.md"
)

foreach ($doc in $planningDocs) {
    Copy-MirrorFile `
        -SourcePath (Join-Path $sourceRoot "frontend_UI_plans\$doc") `
        -DestinationPath (Join-Path $DestinationRoot "frontend_UI_plans\$doc")
}

Copy-MirrorTree -SourcePath (Join-Path $sourceRoot "docs\nrc_adams") -DestinationPath $docsRoot
if (Test-Path -LiteralPath (Join-Path $sourceRoot "docs\postgres")) {
    Copy-MirrorTree -SourcePath (Join-Path $sourceRoot "docs\postgres") -DestinationPath $docsPostgresRoot
}

if (Test-Path -LiteralPath (Join-Path $sourceRoot "next_milestone_plans")) {
    Copy-MirrorTree `
        -SourcePath (Join-Path $sourceRoot "next_milestone_plans") `
        -DestinationPath $nextMilestoneRoot
}

foreach ($subdir in @("deliverables", "logs", "patches", "screenshots")) {
    $workspaceDir = Join-Path $julesWorkspaceRoot $subdir
    New-MirrorDirectory -Path $workspaceDir
    Set-Content -LiteralPath (Join-Path $workspaceDir ".gitkeep") -Value "" -NoNewline
}

Set-Content -LiteralPath (Join-Path $julesWorkspaceRoot "README.md") -Value @'
# Jules Workspace

This folder is the owned output surface for the Jules bake-off lane inside the GitHub-safe mirror.

Use it for:

- `deliverables/`
- `logs/`
- `patches/`
- `screenshots/`
'@

Set-Content -LiteralPath (Join-Path $DestinationRoot ".gitignore") -Value @'
__pycache__/
.pytest_cache/
*.pyc
*.pyo
.venv/
.env
node_modules/
frontend_UI_plans/agent_workspaces/jules/deliverables/*
!frontend_UI_plans/agent_workspaces/jules/deliverables/.gitkeep
frontend_UI_plans/agent_workspaces/jules/logs/*
!frontend_UI_plans/agent_workspaces/jules/logs/.gitkeep
frontend_UI_plans/agent_workspaces/jules/patches/*
!frontend_UI_plans/agent_workspaces/jules/patches/.gitkeep
frontend_UI_plans/agent_workspaces/jules/screenshots/*
!frontend_UI_plans/agent_workspaces/jules/screenshots/.gitkeep
'@

Set-Content -LiteralPath (Join-Path $DestinationRoot "JULES_MIRROR_README.md") -Value @'
# Jules GitHub Mirror

This repository is a GitHub-safe mirror of the main local repo for the Jules bake-off lane.

It intentionally includes:

- the backend code surface needed for the NRC APS review UI slice
- the frozen planning/spec documents
- selected root/docs authority files needed by the active milestone packet
- the current `next_milestone_plans/` context when present in the source repo
- the committed golden runtime fixture under `backend/app/storage_test_runtime/lc_e2e/20260327_062011`

It intentionally excludes local-only heavyweight artifacts that block GitHub pushes, such as:

- `.venvs/`
- the large local demo corpus input tree
- unrelated local databases and scratch outputs

The source of truth for the feature remains the main local repo. This mirror exists only to let Jules operate on a GitHub-backed branch with the correct planning and fixture context.
'@

Set-Content -LiteralPath (Join-Path $DestinationRoot "frontend_UI_plans\JULES_GITHUB_START_HERE.md") -Value @'
# Jules GitHub Start Here

Use this repo, not the main local-only workspace, when running the Jules bake-off.

Important path rule:

- when older planning docs mention `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\...`, interpret that as the matching repo-relative path inside this mirror
- ignore any references to local `.claude\worktrees\...` lanes; your editable lane is this GitHub branch itself

Golden runtime fixture in this mirror:

- `./backend/app/storage_test_runtime/lc_e2e/20260327_062011`
- `run_id = d6be0fff-bbd7-468a-9b00-7103d5995494`

Owned output directory in this mirror:

- `./frontend_UI_plans/agent_workspaces/jules/`

Use:

- `deliverables/`
- `logs/`
- `patches/`
- `screenshots/`

Start with `agent_bakeoff_prompt_jules_github.md`.

If you are executing a later milestone beyond the original Slice 01 bake-off, also review the current files under:

- `./next_milestone_plans/`
- `./frontend_UI_plans/agent_bakeoff_phase1_brief.md`
- `./frontend_UI_plans/agent_bakeoff_phase1_scope.md`
- `./frontend_UI_plans/agent_bakeoff_prompt_jules_phase1.md`
'@

Set-Content -LiteralPath (Join-Path $DestinationRoot "frontend_UI_plans\agent_bakeoff_prompt_jules_github.md") -Value @'
# Agent Bake-Off Prompt: Jules GitHub Mirror

## Round 0 Dry-Run Prompt

```text
You are participating in a controlled implementation bake-off inside this GitHub repo.

Your editable workspace is this repo and the currently selected branch.

Your owned bake-off output directory is:

./frontend_UI_plans/agent_workspaces/jules/

Use:

- deliverables/
- logs/
- patches/
- screenshots/

Your task right now is a DRY RUN ONLY. Do not implement code yet.

Treat the following docs as the authority for scope and implementation shape:

- ./frontend_UI_plans/agent_bakeoff_brief.md
- ./frontend_UI_plans/agent_bakeoff_scope_slice_01.md
- ./frontend_UI_plans/agent_bakeoff_submission_checklist.md
- ./frontend_UI_plans/agent_bakeoff_rubric.md
- ./frontend_UI_plans/nrc_aps_review_ui_spec.md
- ./frontend_UI_plans/nrc_aps_review_ui_data_contract.md
- ./frontend_UI_plans/nrc_aps_review_ui_implementation_blueprint.md
- ./frontend_UI_plans/nrc_aps_review_ui_canonical_graph_registry.md
- ./frontend_UI_plans/nrc_aps_review_ui_mapping_and_reviewability_rules.md
- ./frontend_UI_plans/nrc_aps_review_ui_dependency_and_asset_strategy.md
- ./frontend_UI_plans/nrc_aps_review_ui_validation_plan.md
- ./frontend_UI_plans/nrc_aps_review_ui_example_payloads.md
- ./frontend_UI_plans/JULES_GITHUB_START_HERE.md

Hard constraints:

- NRC APS only
- strictly read-only review surface
- backend-served additive UI
- no new build toolchain
- no new frontend framework
- no CDN dependencies
- strict filesystem tree as the default tree mode
- right-side details drawer

Not in scope:

- run execution controls
- live polling
- file preview
- JSON/text preview
- image preview
- curated review-tree mode
- non-NRC APS generalization
- cross-run comparison

Golden runtime for validation:

- ./backend/app/storage_test_runtime/lc_e2e/20260327_062011
- run_id = d6be0fff-bbd7-468a-9b00-7103d5995494

For this round, do not modify files. Produce:

1. a concise implementation plan for Slice 01
2. the exact files you expect to modify
3. the exact new files you expect to add
4. any assumptions you would make
5. any blockers or likely risk areas
6. a short statement confirming whether you can stay inside the frozen scope

Write your dry-run notes into:

- ./frontend_UI_plans/agent_workspaces/jules/logs/
- ./frontend_UI_plans/agent_workspaces/jules/deliverables/

If a repo-confirmed blocker forces a scope change, state it explicitly and stop there instead of broadening scope on your own.
```

## Round 1 Implementation Prompt

```text
Proceed with Slice 01 implementation in this GitHub repo and the currently selected branch.

Your owned bake-off output directory is:

./frontend_UI_plans/agent_workspaces/jules/

Use:

- deliverables/
- logs/
- patches/
- screenshots/

You must implement the bounded first slice exactly as defined by:

- ./frontend_UI_plans/agent_bakeoff_brief.md
- ./frontend_UI_plans/agent_bakeoff_scope_slice_01.md
- ./frontend_UI_plans/agent_bakeoff_submission_checklist.md
- ./frontend_UI_plans/agent_bakeoff_rubric.md
- ./frontend_UI_plans/nrc_aps_review_ui_spec.md
- ./frontend_UI_plans/nrc_aps_review_ui_data_contract.md
- ./frontend_UI_plans/nrc_aps_review_ui_implementation_blueprint.md
- ./frontend_UI_plans/nrc_aps_review_ui_canonical_graph_registry.md
- ./frontend_UI_plans/nrc_aps_review_ui_mapping_and_reviewability_rules.md
- ./frontend_UI_plans/nrc_aps_review_ui_dependency_and_asset_strategy.md
- ./frontend_UI_plans/nrc_aps_review_ui_validation_plan.md
- ./frontend_UI_plans/nrc_aps_review_ui_example_payloads.md
- ./frontend_UI_plans/JULES_GITHUB_START_HERE.md

Implement only:

- additive GET review endpoints
- review model plumbing
- minimal backend-served UI shell
- strict filesystem tree
- right-side details drawer shell
- node/file cross-selection wiring
- focused tests for the slice

Preserve these constraints:

- read-only only
- NRC APS only
- no new frontend framework
- no npm / Vite / Webpack / TypeScript build system
- no CDN assets
- no preview
- no polling
- no execution controls

Important implementation requirements:

- keep the code modular and non-fragile
- follow the implementation blueprint for file/module boundaries
- use the canonical graph registry rather than deriving the graph from Mermaid text
- do not hardcode the single golden runtime as the only supported root
- surface known mismatch cases visibly instead of hiding them

Validate against the golden runtime:

- ./backend/app/storage_test_runtime/lc_e2e/20260327_062011
- run_id = d6be0fff-bbd7-468a-9b00-7103d5995494

At the end, provide:

1. concise implementation summary
2. changed file list with reasons
3. architecture notes
4. assumptions made
5. risks and tradeoffs
6. tests added and tests run
7. commands used for validation
8. scope-conformance statement
9. screenshot(s) or UI evidence if available

Write your submission artifacts into:

- ./frontend_UI_plans/agent_workspaces/jules/deliverables/
- ./frontend_UI_plans/agent_workspaces/jules/logs/
- ./frontend_UI_plans/agent_workspaces/jules/patches/
- ./frontend_UI_plans/agent_workspaces/jules/screenshots/

If you hit a real blocker, stop and explain it clearly instead of broadening scope.
```
'@

Write-Host "Jules GitHub mirror created at $DestinationRoot"
