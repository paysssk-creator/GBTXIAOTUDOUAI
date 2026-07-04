param(
    [string]$Version = "v1.1.18"
)

$ErrorActionPreference = "Stop"

$projectRoot = $PSScriptRoot
$releaseRoot = Join-Path $projectRoot "release"
$stageRoot = Join-Path $releaseRoot "user_download"
$packageDir = Join-Path $stageRoot ("GBT_Pro_" + $Version)
$zipPath = Join-Path $releaseRoot ("GBT_Pro_" + $Version + "_user_download.zip")
$exeName = "GBT_Pro_" + $Version + ".exe"

if (-not (Test-Path (Join-Path $releaseRoot $exeName))) {
    throw "缺少正式 onefile 包: $exeName"
}

if (Test-Path $packageDir) {
    Remove-Item -Recurse -Force $packageDir
}
if (Test-Path $zipPath) {
    Remove-Item -Force $zipPath
}

New-Item -ItemType Directory -Force -Path $packageDir | Out-Null

Copy-Item -Force (Join-Path $releaseRoot $exeName) (Join-Path $packageDir $exeName)
Copy-Item -Force (Join-Path $releaseRoot "GBT_Pro_User_Setup.bat") (Join-Path $packageDir "GBT_Pro_User_Setup.bat")
Copy-Item -Force (Join-Path $releaseRoot "README_USER_INSTALL.txt") (Join-Path $packageDir "README_USER_INSTALL.txt")
Copy-Item -Force (Join-Path $releaseRoot "manifest.json") (Join-Path $packageDir "manifest.json")

Compress-Archive -Path (Join-Path $packageDir "*") -DestinationPath $zipPath -CompressionLevel Optimal

$hash = (Get-FileHash -Algorithm SHA256 $zipPath).Hash.ToLowerInvariant()
$shaPath = $zipPath + ".sha256.txt"
Set-Content -Path $shaPath -Value $hash -Encoding ASCII

Write-Host "OK: user package dir -> $packageDir"
Write-Host "OK: user zip -> $zipPath"
Write-Host "OK: sha256 -> $shaPath"
