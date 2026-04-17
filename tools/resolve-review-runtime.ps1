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

function Resolve-ReviewRuntimeState {
    param(
        [string]$LaneRoot,
        [string]$RuntimeRoot = ''
    )

    $candidateStates = @()

    if ([string]::IsNullOrWhiteSpace($RuntimeRoot)) {
        $candidateStates += [pscustomobject]@{
            Source = 'repo-native'
            RuntimeRoot = (Join-Path $LaneRoot 'backend\app\storage_test_runtime')
        }
        $candidateStates += [pscustomobject]@{
            Source = 'adopted-sibling'
            RuntimeRoot = (Join-Path $LaneRoot '..\pr45-postmerge-audit\backend\app\storage_test_runtime')
        }
    } else {
        $candidateStates += [pscustomobject]@{
            Source = 'explicit'
            RuntimeRoot = $RuntimeRoot
        }
    }

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
