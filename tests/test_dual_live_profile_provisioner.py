import os
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
PROVISIONER = ROOT / "scripts" / "provision-dual-live-profile.ps1"
WINDOWS_POWERSHELL = Path(
    r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
)


def test_profile_provisioner_is_exact_current_identity_zero_capability_builder() -> None:
    source = PROVISIONER.read_text(encoding="utf-8")

    for parameter in ("ProfileMoniker", "OutputBinding"):
        assert f"${parameter}" in source
    for field in (
        "appcontainer_profile_root",
        "broker_profile_root",
        "broker_sid",
        "package_sid",
        "profile_moniker",
        "user_data_root",
    ):
        assert field in source

    assert "CreateAppContainerProfile" in source
    assert "DeriveAppContainerSidFromAppContainerName" in source
    assert "[IntPtr]::Zero, 0, [ref]$createdSid" in source
    assert "$derivedPackageSid -ne $createdPackageSid" in source
    assert "$brokerIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()" in source
    assert "$brokerSid = $brokerIdentity.User.Value" in source
    assert "GetAppContainerFolderPath" in source
    assert "FreeSid" in source
    assert "CoTaskMemFree" in source
    assert "LocalFree" in source
    assert "WindowsBuiltInRole]::Administrator" in source
    assert "[IO.FileMode]::CreateNew" in source
    assert ".Flush($true)" in source
    assert "ConvertTo-Json -Compress" in source
    assert "ConvertTo-CanonicalUtf8 $binding" in source
    assert "Assert-BindingObservation" in source

    for forbidden in (
        "Start-Process",
        "Invoke-WebRequest",
        "New-LocalUser",
        "net.exe user",
        "DeleteAppContainerProfile",
        "Remove-Item",
        "Get-Credential",
        "PRIVATE KEY",
        "$env:",
    ):
        assert forbidden not in source


@pytest.mark.skipif(os.name != "nt", reason="requires Windows PowerShell 5.1")
def test_profile_provisioner_parses_on_windows_powershell_51() -> None:
    command = (
        "$tokens=$null;$errors=$null;"
        f"[Management.Automation.Language.Parser]::ParseFile('{PROVISIONER}',"
        "[ref]$tokens,[ref]$errors)|Out-Null;"
        "if($errors.Count){$errors|ForEach-Object{$_.Message};exit 1}"
    )
    result = subprocess.run(
        [str(WINDOWS_POWERSHELL), "-NoProfile", "-NonInteractive", "-Command", command],
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.skipif(os.name != "nt", reason="requires Windows PowerShell 5.1")
def test_profile_binding_helper_round_trips_non_ascii_paths_on_powershell_51() -> None:
    command = (
        f"$source=Get-Content -Raw -LiteralPath '{PROVISIONER}';"
        "$tokens=$null;$errors=$null;"
        "$ast=[Management.Automation.Language.Parser]::ParseInput($source,[ref]$tokens,[ref]$errors);"
        "$function=$ast.FindAll({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'ConvertTo-CanonicalUtf8'},$true);"
        "if($errors.Count -or $function.Count -ne 1){exit 1};"
        "Invoke-Expression $function[0].Extent.Text;"
        "$expected=[ordered]@{appcontainer_profile_root='C:\\Profiles\\Bündle';broker_profile_root='C:\\Users\\Renée';broker_sid='S-1-5-21-1';package_sid='S-1-15-2-1';profile_moniker='Project6.Live';user_data_root='C:\\Users\\Renée\\AppData\\Local'};"
        "$bytes=ConvertTo-CanonicalUtf8 $expected;"
        "if($bytes.Length -ge 3 -and $bytes[0] -eq 0xef -and $bytes[1] -eq 0xbb -and $bytes[2] -eq 0xbf){exit 2};"
        "$observed=([Text.UTF8Encoding]::new($false,$true)).GetString($bytes)|ConvertFrom-Json;"
        "if($observed.appcontainer_profile_root -cne $expected.appcontainer_profile_root -or $observed.broker_profile_root -cne $expected.broker_profile_root -or $observed.user_data_root -cne $expected.user_data_root){exit 3}"
    )
    result = subprocess.run(
        [str(WINDOWS_POWERSHELL), "-NoProfile", "-NonInteractive", "-Command", command],
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stdout + result.stderr
