[CmdletBinding()]
param(
    [ValidateSet("setup", "migrate", "start-api", "status", "validate-live", "validate-nrc-aps", "collect-nrc-aps-live-batch", "build-nrc-aps-replay-corpus", "validate-nrc-aps-replay", "check-nrc-aps-replay-corpus", "validate-nrc-aps-sync-drift", "validate-nrc-aps-safeguards", "validate-nrc-aps-artifact-ingestion", "validate-nrc-aps-content-index", "validate-nrc-aps-evidence-bundle", "validate-nrc-aps-evidence-citation-pack", "validate-nrc-aps-evidence-report", "validate-nrc-aps-evidence-report-export", "validate-nrc-aps-evidence-report-export-package", "validate-nrc-aps-context-packet", "validate-nrc-aps-context-dossier", "validate-nrc-aps-deterministic-insight-artifact", "validate-nrc-aps-deterministic-challenge-artifact", "validate-nrc-aps-promotion", "compare-nrc-aps-promotion-policy", "prove-nrc-aps-document-processing", "gate-nrc-aps", "eval-attached", "all")]
    [string]$Action = "status",
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [int]$ConsecutiveRuns = 3,
    [int]$TimeoutSeconds = 600,
    [int]$BatchSpacingSeconds = 5,
    [string]$NrcApsBatchManifest = "",
    [string]$NrcApsPromotionPolicy = "",
    [string]$NrcApsTunedPromotionPolicy = "",
    [string]$NrcApsPromotionRationale = "",
    [string]$PythonVersion = "3.12",
    [switch]$AbortBatchOnCycleFailure,
    [switch]$RequireOcr,
    [switch]$RequireTunedPromotionPass,
    [switch]$Reload
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $RepoRoot "backend"
$RequirementsPath = Join-Path $BackendDir "requirements.txt"
$LiveValidatorPath = Join-Path $RepoRoot "tools\run_sciencebase_live_pilot_validation.py"
$NrcApsValidatorPath = Join-Path $RepoRoot "tools\run_nrc_aps_live_validation.py"
$NrcApsLiveBatchPath = Join-Path $RepoRoot "tools\nrc_aps_live_validation_batch.py"
$NrcApsReplayGatePath = Join-Path $RepoRoot "tools\nrc_aps_replay_gate.py"
$NrcApsSyncDriftGatePath = Join-Path $RepoRoot "tools\nrc_aps_sync_drift_gate.py"
$NrcApsSafeguardGatePath = Join-Path $RepoRoot "tools\nrc_aps_safeguard_gate.py"
$NrcApsArtifactIngestionGatePath = Join-Path $RepoRoot "tools\nrc_aps_artifact_ingestion_gate.py"
$NrcApsContentIndexGatePath = Join-Path $RepoRoot "tools\nrc_aps_content_index_gate.py"
$NrcApsEvidenceBundleGatePath = Join-Path $RepoRoot "tools\nrc_aps_evidence_bundle_gate.py"
$NrcApsEvidenceCitationPackGatePath = Join-Path $RepoRoot "tools\nrc_aps_evidence_citation_pack_gate.py"
$NrcApsEvidenceReportGatePath = Join-Path $RepoRoot "tools\nrc_aps_evidence_report_gate.py"
$NrcApsEvidenceReportExportGatePath = Join-Path $RepoRoot "tools\nrc_aps_evidence_report_export_gate.py"
$NrcApsEvidenceReportExportPackageGatePath = Join-Path $RepoRoot "tools\nrc_aps_evidence_report_export_package_gate.py"
$NrcApsContextPacketGatePath = Join-Path $RepoRoot "tools\nrc_aps_context_packet_gate.py"
$NrcApsContextDossierGatePath = Join-Path $RepoRoot "tools\nrc_aps_context_dossier_gate.py"
$NrcApsDeterministicInsightArtifactGatePath = Join-Path $RepoRoot "tools\nrc_aps_deterministic_insight_artifact_gate.py"
$NrcApsDeterministicChallengeArtifactGatePath = Join-Path $RepoRoot "tools\nrc_aps_deterministic_challenge_artifact_gate.py"
$NrcApsPromotionGatePath = Join-Path $RepoRoot "tools\nrc_aps_promotion_gate.py"
$NrcApsPromotionTuningPath = Join-Path $RepoRoot "tools\nrc_aps_promotion_tuning.py"
$NrcApsReplaySourceRoot = Join-Path $BackendDir "app\storage_test\connectors"
$NrcApsTestStorageDir = Join-Path $BackendDir "app\storage_test_runtime"
$NrcApsTestDatabaseUrl = "sqlite:///./test_method_aware.db"
$NrcApsLiveReportsDir = Join-Path $BackendDir "app\storage\connectors\reports"
$NrcApsLiveBatchRoot = Join-Path $NrcApsLiveReportsDir "nrc_aps_live_batches"
$NrcApsPromotionPolicyPath = Join-Path $BackendDir "app\services\nrc_adams_resources\aps_promotion_policy_v1.json"
$NrcApsReplayCorpusPath = Join-Path $RepoRoot "tests\fixtures\nrc_aps_replay\v1"
$NrcApsReplayValidationReportPath = Join-Path $RepoRoot "tests\reports\nrc_aps_replay_validation_report.json"
$NrcApsReplayDiffReportPath = Join-Path $RepoRoot "tests\reports\nrc_aps_replay_corpus_diff.json"
$NrcApsSyncDriftValidationReportPath = Join-Path $RepoRoot "tests\reports\nrc_aps_sync_drift_validation_report.json"
$NrcApsSafeguardValidationReportPath = Join-Path $RepoRoot "tests\reports\nrc_aps_safeguard_validation_report.json"
$NrcApsArtifactIngestionValidationReportPath = Join-Path $RepoRoot "tests\reports\nrc_aps_artifact_ingestion_validation_report.json"
$NrcApsContentIndexValidationReportPath = Join-Path $RepoRoot "tests\reports\nrc_aps_content_index_validation_report.json"
$NrcApsEvidenceBundleValidationReportPath = Join-Path $RepoRoot "tests\reports\nrc_aps_evidence_bundle_validation_report.json"
$NrcApsEvidenceCitationPackValidationReportPath = Join-Path $RepoRoot "tests\reports\nrc_aps_evidence_citation_pack_validation_report.json"
$NrcApsEvidenceReportValidationReportPath = Join-Path $RepoRoot "tests\reports\nrc_aps_evidence_report_validation_report.json"
$NrcApsEvidenceReportExportValidationReportPath = Join-Path $RepoRoot "tests\reports\nrc_aps_evidence_report_export_validation_report.json"
$NrcApsEvidenceReportExportPackageValidationReportPath = Join-Path $RepoRoot "tests\reports\nrc_aps_evidence_report_export_package_validation_report.json"
$NrcApsContextPacketValidationReportPath = Join-Path $RepoRoot "tests\reports\nrc_aps_context_packet_validation_report.json"
$NrcApsContextDossierValidationReportPath = Join-Path $RepoRoot "tests\reports\nrc_aps_context_dossier_validation_report.json"
$NrcApsDeterministicInsightArtifactValidationReportPath = Join-Path $RepoRoot "tests\reports\nrc_aps_deterministic_insight_artifact_validation_report.json"
$NrcApsDeterministicChallengeArtifactValidationReportPath = Join-Path $RepoRoot "tests\reports\nrc_aps_deterministic_challenge_artifact_validation_report.json"
$NrcApsPromotionValidationReportPath = Join-Path $RepoRoot "tests\reports\nrc_aps_promotion_validation_report.json"
$NrcApsPromotionComparisonReportPath = Join-Path $RepoRoot "tests\reports\nrc_aps_promotion_policy_compare_v1.json"
$NrcApsDocumentProcessingProofPath = Join-Path $RepoRoot "tools\run_nrc_aps_document_processing_proof.py"
$NrcApsDocumentProcessingProofReportPath = Join-Path $RepoRoot "tests\reports\nrc_aps_document_processing_proof_report.json"
$AttachedEvalPath = Join-Path $RepoRoot "tools\run_attached_dataset_eval.py"

function Invoke-Py {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,
        [string]$WorkingDirectory = $RepoRoot
    )
    Push-Location $WorkingDirectory
    try {
        & py "-$PythonVersion" @Arguments
        if ($LASTEXITCODE -ne 0) {
            $argString = ($Arguments -join ' ')
            throw "Python command failed with exit code ${LASTEXITCODE}: py -$PythonVersion $argString"
        }
    }
    finally {
        Pop-Location
    }
}

function Wait-ApiReady {
    param(
        [Parameter(Mandatory = $true)]
        [string]$HealthUrl,
        [int]$MaxWaitSeconds = 60
    )
    $deadline = (Get-Date).AddSeconds($MaxWaitSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-RestMethod -Uri $HealthUrl -Method Get -TimeoutSec 3
            if ($response.status -eq "ok") {
                return
            }
        }
        catch {
            Start-Sleep -Milliseconds 500
        }
    }
    throw "API did not become healthy at $HealthUrl within $MaxWaitSeconds seconds."
}

function Start-ApiForeground {
    $hostUri = [Uri]$BaseUrl
    $port = $hostUri.Port
    $apiHost = $hostUri.Host
    $args = @("-m", "uvicorn", "main:app", "--host", $apiHost, "--port", "$port")
    if ($Reload) {
        $args += "--reload"
    }
    Invoke-Py -Arguments $args -WorkingDirectory $BackendDir
}

function Start-ApiBackground {
    $hostUri = [Uri]$BaseUrl
    $port = $hostUri.Port
    $apiHost = $hostUri.Host
    $args = @("-$PythonVersion", "-m", "uvicorn", "main:app", "--host", $apiHost, "--port", "$port")
    $stdoutPath = Join-Path $RepoRoot ".project6_api_stdout.log"
    $stderrPath = Join-Path $RepoRoot ".project6_api_stderr.log"
    return Start-Process -FilePath "py" -ArgumentList $args -WorkingDirectory $BackendDir -PassThru -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath
}

function Resolve-NrcApsPromotionPolicyPath {
    if ([string]::IsNullOrWhiteSpace($NrcApsPromotionPolicy)) {
        return $NrcApsPromotionPolicyPath
    }
    return $NrcApsPromotionPolicy
}

function Resolve-NrcApsBatchManifestPath {
    if (-not [string]::IsNullOrWhiteSpace($NrcApsBatchManifest)) {
        if (-not (Test-Path $NrcApsBatchManifest)) {
            throw "NRC APS batch manifest not found: $NrcApsBatchManifest"
        }
        return (Resolve-Path $NrcApsBatchManifest).Path
    }
    if (-not (Test-Path $NrcApsLiveBatchRoot)) {
        throw "NRC APS live batch root not found: $NrcApsLiveBatchRoot"
    }
    $latest = Get-ChildItem -Path $NrcApsLiveBatchRoot -Recurse -File -Filter "*_manifest_v1.json" `
        | Sort-Object LastWriteTime -Descending `
        | Select-Object -First 1
    if ($null -eq $latest) {
        throw "No NRC APS live batch manifest found under $NrcApsLiveBatchRoot"
    }
    return $latest.FullName
}

switch ($Action) {
    "setup" {
        Invoke-Py -Arguments @("-m", "pip", "install", "-r", $RequirementsPath)
        Write-Host "Setup complete."
    }
    "migrate" {
        Invoke-Py -Arguments @("-m", "alembic", "-c", "alembic.ini", "upgrade", "head") -WorkingDirectory $BackendDir
        Write-Host "Migrations applied."
    }
    "start-api" {
        Start-ApiForeground
    }
    "status" {
        try {
            $health = Invoke-RestMethod -Uri ($BaseUrl.TrimEnd("/") + "/health") -Method Get -TimeoutSec 3
            Write-Host ("API healthy: {0}" -f ($health.status))
        }
        catch {
            Write-Host "API not reachable at $BaseUrl"
            exit 1
        }
    }
    "validate-live" {
        Invoke-Py -Arguments @($LiveValidatorPath, "--base-url", $BaseUrl, "--consecutive-runs", "$ConsecutiveRuns", "--timeout-seconds", "$TimeoutSeconds")
    }
    "validate-nrc-aps" {
        if (-not (Test-Path $NrcApsValidatorPath)) {
            throw "NRC APS validator script not found: $NrcApsValidatorPath"
        }
        Invoke-Py -Arguments @($NrcApsValidatorPath, "--timeout-seconds", "$TimeoutSeconds")
    }
    "collect-nrc-aps-live-batch" {
        if (-not (Test-Path $NrcApsLiveBatchPath)) {
            throw "NRC APS live batch script not found: $NrcApsLiveBatchPath"
        }
        $args = @(
            $NrcApsLiveBatchPath,
            "--cycle-count", "$ConsecutiveRuns",
            "--spacing-seconds", "$BatchSpacingSeconds",
            "--timeout-seconds", "$TimeoutSeconds",
            "--batch-root", $NrcApsLiveBatchRoot
        )
        if ($AbortBatchOnCycleFailure) {
            $args += "--abort-on-failure"
        }
        Invoke-Py -Arguments $args
    }
    "build-nrc-aps-replay-corpus" {
        if (-not (Test-Path $NrcApsReplayGatePath)) {
            throw "NRC APS replay gate script not found: $NrcApsReplayGatePath"
        }
        Invoke-Py -Arguments @(
            $NrcApsReplayGatePath,
            "build",
            "--source-root", $NrcApsReplaySourceRoot,
            "--out", $NrcApsReplayCorpusPath,
            "--diff-report", $NrcApsReplayDiffReportPath
        )
    }
    "validate-nrc-aps-replay" {
        if (-not (Test-Path $NrcApsReplayGatePath)) {
            throw "NRC APS replay gate script not found: $NrcApsReplayGatePath"
        }
        Invoke-Py -Arguments @(
            $NrcApsReplayGatePath,
            "validate",
            "--corpus", $NrcApsReplayCorpusPath,
            "--report", $NrcApsReplayValidationReportPath
        )
    }
    "check-nrc-aps-replay-corpus" {
        if (-not (Test-Path $NrcApsReplayGatePath)) {
            throw "NRC APS replay gate script not found: $NrcApsReplayGatePath"
        }
        Invoke-Py -Arguments @(
            $NrcApsReplayGatePath,
            "check",
            "--source-root", $NrcApsReplaySourceRoot,
            "--corpus", $NrcApsReplayCorpusPath,
            "--diff-report", $NrcApsReplayDiffReportPath
        )
    }
    "validate-nrc-aps-sync-drift" {
        if (-not (Test-Path $NrcApsSyncDriftGatePath)) {
            throw "NRC APS sync drift gate script not found: $NrcApsSyncDriftGatePath"
        }
        Invoke-Py -Arguments @(
            $NrcApsSyncDriftGatePath,
            "--report", $NrcApsSyncDriftValidationReportPath
        )
    }
    "validate-nrc-aps-safeguards" {
        if (-not (Test-Path $NrcApsSafeguardGatePath)) {
            throw "NRC APS safeguard gate script not found: $NrcApsSafeguardGatePath"
        }
        Invoke-Py -Arguments @(
            $NrcApsSafeguardGatePath,
            "--report", $NrcApsSafeguardValidationReportPath
        )
    }
    "validate-nrc-aps-artifact-ingestion" {
        if (-not (Test-Path $NrcApsArtifactIngestionGatePath)) {
            throw "NRC APS artifact ingestion gate script not found: $NrcApsArtifactIngestionGatePath"
        }
        Invoke-Py -Arguments @(
            $NrcApsArtifactIngestionGatePath,
            "--report", $NrcApsArtifactIngestionValidationReportPath
        )
    }
    "validate-nrc-aps-content-index" {
        if (-not (Test-Path $NrcApsContentIndexGatePath)) {
            throw "NRC APS content index gate script not found: $NrcApsContentIndexGatePath"
        }
        Invoke-Py -Arguments @(
            $NrcApsContentIndexGatePath,
            "--report", $NrcApsContentIndexValidationReportPath
        )
    }
    "validate-nrc-aps-evidence-bundle" {
        if (-not (Test-Path $NrcApsEvidenceBundleGatePath)) {
            throw "NRC APS evidence bundle gate script not found: $NrcApsEvidenceBundleGatePath"
        }
        Invoke-Py -Arguments @(
            $NrcApsEvidenceBundleGatePath,
            "--report", $NrcApsEvidenceBundleValidationReportPath
        )
    }
    "validate-nrc-aps-evidence-citation-pack" {
        if (-not (Test-Path $NrcApsEvidenceCitationPackGatePath)) {
            throw "NRC APS evidence citation pack gate script not found: $NrcApsEvidenceCitationPackGatePath"
        }
        Invoke-Py -Arguments @(
            $NrcApsEvidenceCitationPackGatePath,
            "--report", $NrcApsEvidenceCitationPackValidationReportPath
        )
    }
    "validate-nrc-aps-evidence-report" {
        if (-not (Test-Path $NrcApsEvidenceReportGatePath)) {
            throw "NRC APS evidence report gate script not found: $NrcApsEvidenceReportGatePath"
        }
        Invoke-Py -Arguments @(
            $NrcApsEvidenceReportGatePath,
            "--report", $NrcApsEvidenceReportValidationReportPath
        )
    }
    "validate-nrc-aps-evidence-report-export" {
        if (-not (Test-Path $NrcApsEvidenceReportExportGatePath)) {
            throw "NRC APS evidence report export gate script not found: $NrcApsEvidenceReportExportGatePath"
        }
        $previousStorageDir = $env:STORAGE_DIR
        $previousDatabaseUrl = $env:DATABASE_URL
        try {
            $env:STORAGE_DIR = $NrcApsTestStorageDir
            $env:DATABASE_URL = $NrcApsTestDatabaseUrl
            Invoke-Py -Arguments @(
                $NrcApsEvidenceReportExportGatePath,
                "--report", $NrcApsEvidenceReportExportValidationReportPath
            )
        }
        finally {
            if ($null -eq $previousStorageDir) {
                Remove-Item Env:STORAGE_DIR -ErrorAction SilentlyContinue
            }
            else {
                $env:STORAGE_DIR = $previousStorageDir
            }
            if ($null -eq $previousDatabaseUrl) {
                Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
            }
            else {
                $env:DATABASE_URL = $previousDatabaseUrl
            }
        }
    }
    "validate-nrc-aps-evidence-report-export-package" {
        if (-not (Test-Path $NrcApsEvidenceReportExportPackageGatePath)) {
            throw "NRC APS evidence report export package gate script not found: $NrcApsEvidenceReportExportPackageGatePath"
        }
        $previousStorageDir = $env:STORAGE_DIR
        $previousDatabaseUrl = $env:DATABASE_URL
        try {
            $env:STORAGE_DIR = $NrcApsTestStorageDir
            $env:DATABASE_URL = $NrcApsTestDatabaseUrl
            Invoke-Py -Arguments @(
                $NrcApsEvidenceReportExportPackageGatePath,
                "--report", $NrcApsEvidenceReportExportPackageValidationReportPath
            )
        }
        finally {
            if ($null -eq $previousStorageDir) {
                Remove-Item Env:STORAGE_DIR -ErrorAction SilentlyContinue
            }
            else {
                $env:STORAGE_DIR = $previousStorageDir
            }
            if ($null -eq $previousDatabaseUrl) {
                Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
            }
            else {
                $env:DATABASE_URL = $previousDatabaseUrl
            }
        }
    }
    "validate-nrc-aps-context-packet" {
        if (-not (Test-Path $NrcApsContextPacketGatePath)) {
            throw "NRC APS context packet gate script not found: $NrcApsContextPacketGatePath"
        }
        $previousStorageDir = $env:STORAGE_DIR
        $previousDatabaseUrl = $env:DATABASE_URL
        try {
            $env:STORAGE_DIR = $NrcApsTestStorageDir
            $env:DATABASE_URL = $NrcApsTestDatabaseUrl
            Invoke-Py -Arguments @(
                $NrcApsContextPacketGatePath,
                "--report", $NrcApsContextPacketValidationReportPath
            )
        Invoke-Py -Arguments @(
            $NrcApsContextDossierGatePath,
            "--report", $NrcApsContextDossierValidationReportPath
        )
        }
        finally {
            if ($null -eq $previousStorageDir) {
                Remove-Item Env:STORAGE_DIR -ErrorAction SilentlyContinue
            }
            else {
                $env:STORAGE_DIR = $previousStorageDir
            }
            if ($null -eq $previousDatabaseUrl) {
                Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
            }
            else {
                $env:DATABASE_URL = $previousDatabaseUrl
            }
        }
    }
    "validate-nrc-aps-context-dossier" {
        if (-not (Test-Path $NrcApsContextDossierGatePath)) {
            throw "NRC APS context dossier gate script not found: $NrcApsContextDossierGatePath"
        }
        $previousStorageDir = $env:STORAGE_DIR
        $previousDatabaseUrl = $env:DATABASE_URL
        try {
            $env:STORAGE_DIR = $NrcApsTestStorageDir
            $env:DATABASE_URL = $NrcApsTestDatabaseUrl
        Invoke-Py -Arguments @(
            $NrcApsContextDossierGatePath,
            "--report", $NrcApsContextDossierValidationReportPath
        )
        }
        finally {
            if ($null -eq $previousStorageDir) {
                Remove-Item Env:STORAGE_DIR -ErrorAction SilentlyContinue
            }
            else {
                $env:STORAGE_DIR = $previousStorageDir
            }
            if ($null -eq $previousDatabaseUrl) {
                Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
            }
            else {
                $env:DATABASE_URL = $previousDatabaseUrl
            }
        }
    }
    "validate-nrc-aps-deterministic-insight-artifact" {
        if (-not (Test-Path $NrcApsDeterministicInsightArtifactGatePath)) {
            throw "NRC APS deterministic insight artifact gate script not found: $NrcApsDeterministicInsightArtifactGatePath"
        }
        $previousStorageDir = $env:STORAGE_DIR
        $previousDatabaseUrl = $env:DATABASE_URL
        try {
            $env:STORAGE_DIR = $NrcApsTestStorageDir
            $env:DATABASE_URL = $NrcApsTestDatabaseUrl
            Invoke-Py -Arguments @(
                $NrcApsDeterministicInsightArtifactGatePath,
                "--report", $NrcApsDeterministicInsightArtifactValidationReportPath
            )
        }
        finally {
            if ($null -eq $previousStorageDir) {
                Remove-Item Env:STORAGE_DIR -ErrorAction SilentlyContinue
            }
            else {
                $env:STORAGE_DIR = $previousStorageDir
            }
            if ($null -eq $previousDatabaseUrl) {
                Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
            }
            else {
                $env:DATABASE_URL = $previousDatabaseUrl
            }
        }
    }
    "validate-nrc-aps-deterministic-challenge-artifact" {
        if (-not (Test-Path $NrcApsDeterministicChallengeArtifactGatePath)) {
            throw "NRC APS deterministic challenge artifact gate script not found: $NrcApsDeterministicChallengeArtifactGatePath"
        }
        $previousStorageDir = $env:STORAGE_DIR
        $previousDatabaseUrl = $env:DATABASE_URL
        try {
            $env:STORAGE_DIR = $NrcApsTestStorageDir
            $env:DATABASE_URL = $NrcApsTestDatabaseUrl
            Invoke-Py -Arguments @(
                $NrcApsDeterministicChallengeArtifactGatePath,
                "--report", $NrcApsDeterministicChallengeArtifactValidationReportPath
            )
        }
        finally {
            if ($null -eq $previousStorageDir) {
                Remove-Item Env:STORAGE_DIR -ErrorAction SilentlyContinue
            }
            else {
                $env:STORAGE_DIR = $previousStorageDir
            }
            if ($null -eq $previousDatabaseUrl) {
                Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
            }
            else {
                $env:DATABASE_URL = $previousDatabaseUrl
            }
        }
    }
    "validate-nrc-aps-promotion" {
        if (-not (Test-Path $NrcApsPromotionGatePath)) {
            throw "NRC APS promotion gate script not found: $NrcApsPromotionGatePath"
        }
        $batchManifestPath = Resolve-NrcApsBatchManifestPath
        $policyPath = Resolve-NrcApsPromotionPolicyPath
        Invoke-Py -Arguments @(
            $NrcApsPromotionGatePath,
            "--batch-manifest", $batchManifestPath,
            "--policy", $policyPath,
            "--report", $NrcApsPromotionValidationReportPath
        )
    }
    "compare-nrc-aps-promotion-policy" {
        if (-not (Test-Path $NrcApsPromotionTuningPath)) {
            throw "NRC APS promotion tuning script not found: $NrcApsPromotionTuningPath"
        }
        if ([string]::IsNullOrWhiteSpace($NrcApsTunedPromotionPolicy)) {
            throw "NrcApsTunedPromotionPolicy is required for compare-nrc-aps-promotion-policy."
        }
        if ([string]::IsNullOrWhiteSpace($NrcApsPromotionRationale)) {
            throw "NrcApsPromotionRationale is required for compare-nrc-aps-promotion-policy."
        }
        $batchManifestPath = Resolve-NrcApsBatchManifestPath
        $policyPath = Resolve-NrcApsPromotionPolicyPath
        $args = @(
            $NrcApsPromotionTuningPath,
            "--batch-manifest", $batchManifestPath,
            "--baseline-policy", $policyPath,
            "--tuned-policy", $NrcApsTunedPromotionPolicy,
            "--rationale", $NrcApsPromotionRationale,
            "--out-dir", (Split-Path -Parent $NrcApsPromotionComparisonReportPath)
        )
        if ($RequireTunedPromotionPass) {
            $args += "--require-tuned-pass"
        }
        Invoke-Py -Arguments $args
    }
    "prove-nrc-aps-document-processing" {
        if (-not (Test-Path $NrcApsDocumentProcessingProofPath)) {
            throw "NRC APS document-processing proof script not found: $NrcApsDocumentProcessingProofPath"
        }
        $args = @(
            $NrcApsDocumentProcessingProofPath,
            "--report", $NrcApsDocumentProcessingProofReportPath,
            "--artifact-report", $NrcApsArtifactIngestionValidationReportPath,
            "--content-index-report", $NrcApsContentIndexValidationReportPath
        )
        if ($RequireOcr) {
            $args += "--require-ocr"
        }
        Invoke-Py -Arguments $args
    }
    "gate-nrc-aps" {
        if (-not (Test-Path $NrcApsReplayGatePath)) {
            throw "NRC APS replay gate script not found: $NrcApsReplayGatePath"
        }
        if (-not (Test-Path $NrcApsSyncDriftGatePath)) {
            throw "NRC APS sync drift gate script not found: $NrcApsSyncDriftGatePath"
        }
        if (-not (Test-Path $NrcApsSafeguardGatePath)) {
            throw "NRC APS safeguard gate script not found: $NrcApsSafeguardGatePath"
        }
        if (-not (Test-Path $NrcApsArtifactIngestionGatePath)) {
            throw "NRC APS artifact ingestion gate script not found: $NrcApsArtifactIngestionGatePath"
        }
        if (-not (Test-Path $NrcApsContentIndexGatePath)) {
            throw "NRC APS content index gate script not found: $NrcApsContentIndexGatePath"
        }
        if (-not (Test-Path $NrcApsEvidenceBundleGatePath)) {
            throw "NRC APS evidence bundle gate script not found: $NrcApsEvidenceBundleGatePath"
        }
        if (-not (Test-Path $NrcApsEvidenceCitationPackGatePath)) {
            throw "NRC APS evidence citation pack gate script not found: $NrcApsEvidenceCitationPackGatePath"
        }
        if (-not (Test-Path $NrcApsEvidenceReportGatePath)) {
            throw "NRC APS evidence report gate script not found: $NrcApsEvidenceReportGatePath"
        }
        if (-not (Test-Path $NrcApsEvidenceReportExportGatePath)) {
            throw "NRC APS evidence report export gate script not found: $NrcApsEvidenceReportExportGatePath"
        }
        if (-not (Test-Path $NrcApsEvidenceReportExportPackageGatePath)) {
            throw "NRC APS evidence report export package gate script not found: $NrcApsEvidenceReportExportPackageGatePath"
        }
        if (-not (Test-Path $NrcApsContextPacketGatePath)) {
            throw "NRC APS context packet gate script not found: $NrcApsContextPacketGatePath"
        }
        if (-not (Test-Path $NrcApsContextDossierGatePath)) {
            throw "NRC APS context dossier gate script not found: $NrcApsContextDossierGatePath"
        }
        if (-not (Test-Path $NrcApsDeterministicInsightArtifactGatePath)) {
            throw "NRC APS deterministic insight artifact gate script not found: $NrcApsDeterministicInsightArtifactGatePath"
        }
        if (-not (Test-Path $NrcApsDeterministicChallengeArtifactGatePath)) {
            throw "NRC APS deterministic challenge artifact gate script not found: $NrcApsDeterministicChallengeArtifactGatePath"
        }
        Invoke-Py -Arguments @(
            "-m", "pytest",
            "tests/test_api.py", "-k", "test_nrc_ and not test_nrc_context_dossier_get_fails_closed_on_ambiguous_id",
            "tests/test_nrc_aps_replay_gate.py",
            "tests/test_nrc_aps_sync_drift.py",
            "tests/test_nrc_aps_safeguards.py",
            "tests/test_nrc_aps_safeguard_gate.py",
            "tests/test_nrc_aps_artifact_ingestion.py",
            "tests/test_nrc_aps_artifact_ingestion_gate.py",
            "tests/test_nrc_aps_content_index.py",
            "tests/test_nrc_aps_content_index_gate.py",
            "tests/test_nrc_aps_evidence_bundle_contract.py",
            "tests/test_nrc_aps_evidence_bundle.py",
            "tests/test_nrc_aps_evidence_bundle_gate.py",
            "tests/test_nrc_aps_evidence_citation_pack_contract.py",
            "tests/test_nrc_aps_evidence_citation_pack.py",
            "tests/test_nrc_aps_evidence_citation_pack_gate.py",
            "tests/test_nrc_aps_evidence_report_contract.py",
            "tests/test_nrc_aps_evidence_report.py",
            "tests/test_nrc_aps_evidence_report_gate.py",
            "tests/test_nrc_aps_evidence_report_export_contract.py",
            "tests/test_nrc_aps_evidence_report_export.py",
            "tests/test_nrc_aps_evidence_report_export_gate.py",
            "tests/test_nrc_aps_evidence_report_export_package_contract.py",
            "tests/test_nrc_aps_evidence_report_export_package.py",
            "tests/test_nrc_aps_evidence_report_export_package_gate.py",
            "tests/test_nrc_aps_context_packet_contract.py",
            "tests/test_nrc_aps_context_packet.py",
            "tests/test_nrc_aps_context_packet_gate.py",
            "tests/test_nrc_aps_context_dossier_contract.py",
            "tests/test_nrc_aps_context_dossier.py",
            "tests/test_nrc_aps_context_dossier_gate.py",
            "tests/test_nrc_aps_deterministic_insight_artifact_contract.py",
            "tests/test_nrc_aps_deterministic_insight_artifact.py",
            "tests/test_nrc_aps_deterministic_insight_artifact_gate.py",
            "tests/test_nrc_aps_deterministic_challenge_artifact_contract.py",
            "tests/test_nrc_aps_deterministic_challenge_artifact.py",
            "tests/test_nrc_aps_deterministic_challenge_artifact_gate.py",
            "tests/test_nrc_aps_live_validation.py",
            "tests/test_nrc_aps_promotion_gate.py",
            "tests/test_nrc_aps_live_batch.py",
            "tests/test_nrc_aps_promotion_tuning.py"
        )
        Invoke-Py -Arguments @(
            $NrcApsReplayGatePath,
            "validate",
            "--corpus", $NrcApsReplayCorpusPath,
            "--report", $NrcApsReplayValidationReportPath
        )
        $previousStorageDir = $env:STORAGE_DIR
        $previousDatabaseUrl = $env:DATABASE_URL
        try {
            $env:STORAGE_DIR = $NrcApsTestStorageDir
            $env:DATABASE_URL = $NrcApsTestDatabaseUrl
            Invoke-Py -Arguments @(
                $NrcApsSyncDriftGatePath,
                "--report", $NrcApsSyncDriftValidationReportPath
            )
            Invoke-Py -Arguments @(
                $NrcApsSafeguardGatePath,
                "--report", $NrcApsSafeguardValidationReportPath
            )
            Invoke-Py -Arguments @(
                $NrcApsArtifactIngestionGatePath,
                "--report", $NrcApsArtifactIngestionValidationReportPath
            )
            Invoke-Py -Arguments @(
                $NrcApsContentIndexGatePath,
                "--report", $NrcApsContentIndexValidationReportPath
            )
            Invoke-Py -Arguments @(
                $NrcApsEvidenceBundleGatePath,
                "--report", $NrcApsEvidenceBundleValidationReportPath
            )
            Invoke-Py -Arguments @(
                $NrcApsEvidenceCitationPackGatePath,
                "--report", $NrcApsEvidenceCitationPackValidationReportPath
            )
            Invoke-Py -Arguments @(
                $NrcApsEvidenceReportGatePath,
                "--report", $NrcApsEvidenceReportValidationReportPath
            )
            Invoke-Py -Arguments @(
                $NrcApsEvidenceReportExportGatePath,
                "--report", $NrcApsEvidenceReportExportValidationReportPath
            )
            Invoke-Py -Arguments @(
                $NrcApsEvidenceReportExportPackageGatePath,
                "--report", $NrcApsEvidenceReportExportPackageValidationReportPath
            )
            Invoke-Py -Arguments @(
                $NrcApsContextPacketGatePath,
                "--report", $NrcApsContextPacketValidationReportPath
            )
            Invoke-Py -Arguments @(
                $NrcApsContextDossierGatePath,
                "--report", $NrcApsContextDossierValidationReportPath
            )
            Invoke-Py -Arguments @(
                $NrcApsDeterministicInsightArtifactGatePath,
                "--report", $NrcApsDeterministicInsightArtifactValidationReportPath
            )
            Invoke-Py -Arguments @(
                $NrcApsDeterministicChallengeArtifactGatePath,
                "--report", $NrcApsDeterministicChallengeArtifactValidationReportPath
            )
        }
        finally {
            if ($null -eq $previousStorageDir) {
                Remove-Item Env:STORAGE_DIR -ErrorAction SilentlyContinue
            }
            else {
                $env:STORAGE_DIR = $previousStorageDir
            }
            if ($null -eq $previousDatabaseUrl) {
                Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
            }
            else {
                $env:DATABASE_URL = $previousDatabaseUrl
            }
        }
        # This negative test persists synthetic same-id dossier artifacts that intentionally fail the dossier gate.
        Invoke-Py -Arguments @(
            "-m", "pytest",
            "tests/test_api.py", "-k", "test_nrc_context_dossier_get_fails_closed_on_ambiguous_id"
        )
    }
    "eval-attached" {
        if (-not (Test-Path $AttachedEvalPath)) {
            throw "Attached eval script not found: $AttachedEvalPath"
        }
        Invoke-Py -Arguments @($AttachedEvalPath)
    }
    "all" {
        Invoke-Py -Arguments @("-m", "pip", "install", "-r", $RequirementsPath)
        Invoke-Py -Arguments @("-m", "alembic", "-c", "alembic.ini", "upgrade", "head") -WorkingDirectory $BackendDir
        $proc = Start-ApiBackground
        try {
            Wait-ApiReady -HealthUrl ($BaseUrl.TrimEnd("/") + "/health") -MaxWaitSeconds 90
            Invoke-Py -Arguments @($LiveValidatorPath, "--base-url", $BaseUrl, "--consecutive-runs", "$ConsecutiveRuns", "--timeout-seconds", "$TimeoutSeconds")
        }
        finally {
            if ($null -ne $proc -and -not $proc.HasExited) {
                Stop-Process -Id $proc.Id -Force
            }
        }
    }
}
