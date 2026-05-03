function Get-ReviewRuntimeBindings {
    param(
        [string]$RuntimeRoot
    )

    $bindings = @()
    if (-not $RuntimeRoot -or -not (Test-Path $RuntimeRoot)) {
        return $bindings
    }

    $lcE2eRoot = Join-Path $RuntimeRoot 'lc_e2e'
    if (-not (Test-Path $lcE2eRoot)) {
        return $bindings
    }

    function Get-FirstCompletedAtValue {
        param([object]$Summary)

        foreach ($propertyName in @('completed_at_utc', 'completed_at', 'generated_at_utc')) {
            $property = $Summary.PSObject.Properties[$propertyName]
            if ($null -eq $property) {
                continue
            }
            $value = [string]$property.Value
            if (-not [string]::IsNullOrWhiteSpace($value)) {
                return $value
            }
        }

        return ''
    }

    foreach ($candidateDir in Get-ChildItem $lcE2eRoot -Directory -ErrorAction SilentlyContinue) {
        $summaryPath = Join-Path $candidateDir.FullName 'local_corpus_e2e_summary.json'
        $runtimeDb = Join-Path $candidateDir.FullName 'lc.db'
        if (-not (Test-Path $summaryPath) -or -not (Test-Path $runtimeDb)) {
            continue
        }

        try {
            $summary = Get-Content $summaryPath -Raw | ConvertFrom-Json
        } catch {
            continue
        }

        $bindings += [pscustomobject]@{
            RuntimeRoot = $RuntimeRoot
            ReviewRoot = $candidateDir.FullName
            RuntimeDb = $runtimeDb
            SummaryPath = $summaryPath
            Name = $candidateDir.Name
            RunId = [string]$summary.run_id
            Passed = ($summary.passed -eq $true)
            CompletedAt = Get-FirstCompletedAtValue -Summary $summary
        }
    }

    return $bindings
}

function Get-SharedReviewRuntimeRoot {
    param(
        [string]$LaneRoot
    )

    if ([string]::IsNullOrWhiteSpace($LaneRoot) -or -not (Test-Path $LaneRoot)) {
        return $null
    }

    $current = Get-Item (Resolve-Path $LaneRoot).Path
    while ($null -ne $current) {
        if ($current.Name -eq 'worktrees' -and $null -ne $current.Parent) {
            return (Join-Path $current.Parent.FullName 'backend\app\storage_test_runtime')
        }
        $current = $current.Parent
    }

    return $null
}

function Get-ReviewRuntimeCandidateStates {
    param(
        [string]$LaneRoot,
        [string]$RuntimeRoot = ''
    )

    $candidateStates = @()

    if (-not [string]::IsNullOrWhiteSpace($RuntimeRoot)) {
        $candidateStates += [pscustomobject]@{
            Source = 'explicit'
            RuntimeRoot = $RuntimeRoot
        }
        return $candidateStates
    }

    $sharedRuntimeRoot = Get-SharedReviewRuntimeRoot -LaneRoot $LaneRoot
    if (-not [string]::IsNullOrWhiteSpace($sharedRuntimeRoot)) {
        $candidateStates += [pscustomobject]@{
            Source = 'shared-repo-root'
            RuntimeRoot = $sharedRuntimeRoot
        }
    }

    $candidateStates += [pscustomobject]@{
        Source = 'repo-native-app'
        RuntimeRoot = (Join-Path $LaneRoot 'backend\app\storage_test_runtime')
    }
    $candidateStates += [pscustomobject]@{
        Source = 'repo-native-backend'
        RuntimeRoot = (Join-Path $LaneRoot 'backend\storage_test_runtime')
    }

    return $candidateStates
}

function Resolve-ReviewRuntimeState {
    param(
        [string]$LaneRoot,
        [string]$RuntimeRoot = ''
    )

    $candidateStates = @(Get-ReviewRuntimeCandidateStates -LaneRoot $LaneRoot -RuntimeRoot $RuntimeRoot)

    foreach ($candidateState in $candidateStates) {
        if (-not (Test-Path $candidateState.RuntimeRoot)) {
            continue
        }

        $resolvedRuntimeRoot = (Resolve-Path $candidateState.RuntimeRoot).Path
        $bindings = @(Get-ReviewRuntimeBindings -RuntimeRoot $resolvedRuntimeRoot)
        if ($bindings.Count -eq 0) {
            continue
        }

        $preferredBinding = @(
            $bindings |
                Sort-Object @{ Expression = { if ($_.Passed) { 0 } else { 1 } } }, `
                             @{ Expression = { $_.CompletedAt } ; Descending = $true }, `
                             @{ Expression = { $_.Name } ; Descending = $true }
        )[0]

        return [pscustomobject]@{
            Source = $candidateState.Source
            RuntimeRoot = $resolvedRuntimeRoot
            RuntimeDb = (Resolve-Path $preferredBinding.RuntimeDb).Path
            ReviewRoot = (Resolve-Path $preferredBinding.ReviewRoot).Path
            SummaryPath = (Resolve-Path $preferredBinding.SummaryPath).Path
            RunId = $preferredBinding.RunId
            Passed = $preferredBinding.Passed
            CompletedAt = $preferredBinding.CompletedAt
            AvailableBindings = $bindings
        }
    }

    $searchedRoots = @($candidateStates | ForEach-Object { $_.RuntimeRoot }) -join "`n"
    throw "Unable to resolve a review runtime root. Searched:`n$searchedRoots"
}
