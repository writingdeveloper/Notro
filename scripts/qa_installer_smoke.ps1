<# Disposable GitHub-hosted runner ONLY; never the user's real PC.
   Verifies public 2.10.3 -> new unsigned 2.11.0 upgrade and uninstall.
   No Discord account, clipboard or real user data is involved.
   Does not test SmartScreen warnings or interactive GUI behavior. #>
param(
    [Parameter(Mandatory = $true)]
    [string]$ExpectedVersion
)
$ErrorActionPreference = "Stop"
if ($env:GITHUB_ACTIONS -ne "true" -or -not $env:RUNNER_TEMP) {
    throw "QA installer smoke runs only in a disposable GitHub runner."
}
if (-not $env:GH_TOKEN) { throw "Missing GitHub token for baseline release download." }

$installer = Join-Path $PWD "dist\NotroSetup.exe"
$installDir = Join-Path $env:RUNNER_TEMP "Notro QA Installer Smoke"
$env:NOTRO_QA_SUPPRESS_AUTORUN = "1"
if (-not (Test-Path -LiteralPath $installer)) { throw "Installer not found." }
$info = (Get-Item -LiteralPath $installer).VersionInfo
if ($info.ProductVersion.Trim() -ne $ExpectedVersion) {
    throw "Installer version mismatch: $($info.ProductVersion)"
}
$signature = Get-AuthenticodeSignature -LiteralPath $installer
if ($signature.Status.ToString() -ne "NotSigned") {
    throw "Unsigned QA installer expected, found: $($signature.Status)"
}

$baselineDir = Join-Path $env:RUNNER_TEMP "Notro Public Baseline"
New-Item -ItemType Directory -Path $baselineDir -Force | Out-Null
gh release download v2.10.3 --repo writingdeveloper/Notro --pattern "NotroSetup.exe*" --dir $baselineDir --clobber
if ($LASTEXITCODE -ne 0) { throw "Failed to fetch public v2.10.3 installer." }
$baselineExe = Join-Path $baselineDir "NotroSetup.exe"
$baselineSha = Join-Path $baselineDir "NotroSetup.exe.sha256"
if (-not (Test-Path -LiteralPath $baselineExe) -or -not (Test-Path -LiteralPath $baselineSha)) {
    throw "Missing baseline installer or official checksum."
}
$shaLine = (Get-Content -LiteralPath $baselineSha -Raw).Trim()
if ($shaLine -notmatch '^([0-9a-fA-F]{64})\s+NotroSetup\.exe$') {
    throw "Malformed published baseline checksum."
}
$published = $Matches[1]
$verified = (Get-FileHash -LiteralPath $baselineExe -Algorithm SHA256).Hash
if ($verified.ToLower() -ne $published.ToLower()) {
    throw "Baseline v2.10.3 installer checksum mismatch."
}
$baselineVersion = (Get-Item -LiteralPath $baselineExe).VersionInfo.ProductVersion.Trim()
if ($baselineVersion -ne "2.10.3") {
    throw "Unexpected baseline version: $baselineVersion"
}

$installArgs = @("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/NOICONS",
                 ('/DIR="' + $installDir + '"'))
function Wait-OnlyInstallerProcess {
    param([System.Diagnostics.Process] $Process)
    # Start-Process -Wait waits for child processes too. The published
    # v2.10.3 installer starts a persistent tray process on exit, which
    # would otherwise make our upgrade QA hang forever.
    if (-not $Process.WaitForExit(120000)) {
        try { $Process.Kill() } catch {}
        throw "Installer process did not terminate within 120 seconds."
    }
    return $Process.ExitCode
}
Write-Host "NOTRO_QA_BASELINE_VERIFIED" $baselineVersion
$baseline = Start-Process -FilePath $baselineExe -ArgumentList $installArgs -PassThru
$baselineExit = Wait-OnlyInstallerProcess -Process $baseline
if ($baselineExit -ne 0) {
    throw "Baseline silent installation failed: $baselineExit"
}
$exe = Join-Path $installDir "Notro.exe"
$uninstall = Join-Path $installDir "unins000.exe"
if (-not (Test-Path -LiteralPath $exe)) { throw "Missing public baseline executable." }
if ((Get-Item -LiteralPath $exe).VersionInfo.ProductVersion.Trim() -ne "2.10.3") {
    throw "Installed baseline executable version mismatch."
}

# The public v2.10.3 installer has no CI-only suppression flag, so it may
# briefly auto-launch on the empty hosted runner. Stop only that runner's copy.
Start-Sleep -Seconds 3
Get-Process -Name "Notro" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction Stop
Start-Sleep -Seconds 1
if (Get-Process -Name "Notro" -ErrorAction SilentlyContinue) {
    throw "Baseline process still running before upgrade."
}

# Synthetic user data marker ensures upgrade/uninstall retain app data.
$fixtureDir = Join-Path $env:APPDATA "Notro"
New-Item -ItemType Directory -Path $fixtureDir -Force | Out-Null
$fixture = Join-Path $fixtureDir "qa-upgrade-preserve.txt"
$fixtureText = "qa-public-baseline-to-new-unsigned-release"
Set-Content -LiteralPath $fixture -Value $fixtureText -Encoding UTF8

Write-Host "NOTRO_QA_UPGRADING_UNSIGNED" $ExpectedVersion
$installed = Start-Process -FilePath $installer -ArgumentList $installArgs -PassThru
$installedExit = Wait-OnlyInstallerProcess -Process $installed
if ($installedExit -ne 0) {
    throw "Candidate silent upgrade failed: $installedExit"
}
if (-not (Test-Path -LiteralPath $exe)) { throw "Candidate Notro.exe not installed." }
if (-not (Test-Path -LiteralPath $uninstall)) { throw "Candidate uninstaller missing." }
$actualVersion = (Get-Item -LiteralPath $exe).VersionInfo.ProductVersion.Trim()
if ($actualVersion -ne $ExpectedVersion) {
    throw "Candidate installed executable version mismatch: $actualVersion"
}
if (Get-Process -Name "Notro" -ErrorAction SilentlyContinue) {
    throw "Candidate unexpectedly auto-launched during CI-only upgrade."
}
if ((Get-Content -LiteralPath $fixture -Raw).Trim() -ne $fixtureText) {
    throw "Synthetic settings/data marker altered during candidate upgrade."
}
Write-Host "NOTRO_QA_BASELINE_TO_CANDIDATE_UPGRADE_PRESERVED_DATA"

$uninstalled = Start-Process -FilePath $uninstall -ArgumentList @(
    "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"
) -PassThru
$uninstalledExit = Wait-OnlyInstallerProcess -Process $uninstalled
if ($uninstalledExit -ne 0) {
    throw "Uninstall failed: $uninstalledExit"
}
Start-Sleep -Seconds 1
if (Test-Path -LiteralPath $exe) { throw "Notro.exe remains after uninstall." }
if ((Get-Content -LiteralPath $fixture -Raw).Trim() -ne $fixtureText) {
    throw "Uninstaller unexpectedly deleted retained profile data."
}
Remove-Item -LiteralPath $fixture -Force
Write-Host "NOTRO_QA_UPGRADE_UNINSTALL_PASSED"
Write-Host "NOTRO_QA_INSTALL_UNINSTALL_PASSED"
