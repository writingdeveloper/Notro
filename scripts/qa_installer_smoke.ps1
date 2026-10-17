<# Disposable GitHub-hosted runner only. No Discord, clipboard or personal data.
   Tests actual Inno installer/exe version and removal, not SmartScreen or GUI. #>
param(
    [Parameter(Mandatory = $true)]
    [string]$ExpectedVersion
)
$ErrorActionPreference = "Stop"
if ($env:GITHUB_ACTIONS -ne "true" -or -not $env:RUNNER_TEMP) {
    throw "QA installer smoke only runs on disposable GitHub runners."
}
$installer = Join-Path $PWD "dist\NotroSetup.exe"
$installDir = Join-Path $env:RUNNER_TEMP "Notro QA Installer Smoke"
$env:NOTRO_QA_SUPPRESS_AUTORUN = "1"
if (-not (Test-Path -LiteralPath $installer)) {
    throw "No installer at $installer"
}
$info = (Get-Item -LiteralPath $installer).VersionInfo
if ($info.ProductVersion.Trim() -ne $ExpectedVersion) {
    throw "Installer version mismatch: $($info.ProductVersion)"
}
$signature = Get-AuthenticodeSignature -LiteralPath $installer
if ($signature.Status.ToString() -ne "NotSigned") {
    throw "Expected unsigned QA package; actual: $($signature.Status)"
}
Write-Host "NOTRO_QA_INSTALLING_UNSIGNED" $ExpectedVersion
$arguments = @("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/NOICONS",
               ('/DIR="' + $installDir + '"'))
$installed = Start-Process -FilePath $installer -ArgumentList $arguments -Wait -PassThru
if ($installed.ExitCode -ne 0) {
    throw "Silent QA install failed: $($installed.ExitCode)"
}
$exe = Join-Path $installDir "Notro.exe"
$uninstall = Join-Path $installDir "unins000.exe"
if (-not (Test-Path -LiteralPath $exe)) { throw "Notro.exe not installed" }
if (-not (Test-Path -LiteralPath $uninstall)) { throw "Uninstaller absent" }
$actualVersion = (Get-Item -LiteralPath $exe).VersionInfo.ProductVersion.Trim()
if ($actualVersion -ne $ExpectedVersion) {
    throw "Installed executable version mismatch: $actualVersion"
}
if (Get-Process -Name "Notro" -ErrorAction SilentlyContinue) {
    throw "Installer unexpectedly launched Notro in unattended QA"
}
Write-Host "NOTRO_QA_INSTALLED_VERSION" $actualVersion
$uninstalled = Start-Process -FilePath $uninstall -ArgumentList @(
    "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"
) -Wait -PassThru
if ($uninstalled.ExitCode -ne 0) {
    throw "Silent QA uninstall failed: $($uninstalled.ExitCode)"
}
Start-Sleep -Seconds 1
if (Test-Path -LiteralPath $exe) {
    throw "Notro.exe remains after QA uninstall"
}
Write-Host "NOTRO_QA_INSTALL_UNINSTALL_PASSED"
