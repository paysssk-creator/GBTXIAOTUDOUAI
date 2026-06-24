# GBT AI Workstation installer (Windows)
# Usage:
#   irm https://raw.githubusercontent.com/paysssk-creator/GBTXIAOTUDOUAI/main/scripts/install.ps1 | iex

$ErrorActionPreference = "Stop"

$Repo = "paysssk-creator/GBTXIAOTUDOUAI"
$LatestApi = "https://api.github.com/repos/$Repo/releases/latest"

function Write-Info { param([string]$m) Write-Host "→ $m" -ForegroundColor Cyan }
function Write-Ok { param([string]$m) Write-Host "✓ $m" -ForegroundColor Green }
function Write-Err { param([string]$m) Write-Host "✗ $m" -ForegroundColor Red }

$Arch = if ([Environment]::Is64BitOperatingSystem) { "x86_64" } else { "x86" }
$Target = "$Arch-pc-windows-msvc"

Write-Info "Detecting latest release..."
$Release = Invoke-RestMethod -Uri $LatestApi -UseBasicParsing
$Version = $Release.tag_name
$AssetName = "gbt-app_$($Version -replace '^v','')_$Target.msi"
$AssetUrl = $Release.assets | Where-Object { $_.name -eq $AssetName } | Select-Object -ExpandProperty browser_download_url

if (-not $AssetUrl) {
    Write-Err "Could not find installer asset: $AssetName"
    exit 1
}

Write-Info "Latest version: $Version"
Write-Info "Downloading $AssetName..."

$TmpDir = Join-Path $env:TEMP "gbt-install-$(Get-Random)"
New-Item -ItemType Directory -Path $TmpDir -Force | Out-Null
$Installer = Join-Path $TmpDir $AssetName

Invoke-WebRequest -Uri $AssetUrl -OutFile $Installer -UseBasicParsing
Write-Ok "Downloaded $AssetName"

Write-Info "Installing..."
$Proc = Start-Process -FilePath "msiexec.exe" -ArgumentList "/i", "`"$Installer`"", "/qn", "/norestart" -Wait -PassThru
if ($Proc.ExitCode -ne 0) {
    Write-Err "Installation failed with exit code $($Proc.ExitCode)"
    exit $Proc.ExitCode
}

Write-Ok "GBT AI Workstation installed successfully"
Remove-Item -Recurse -Force $TmpDir -ErrorAction SilentlyContinue
