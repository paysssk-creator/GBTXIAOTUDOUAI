param(
    [string]$Version = "v1.1.22",
    [string]$RuntimeDir = ""
)

$ErrorActionPreference = "Stop"

$projectRoot = $PSScriptRoot
$releaseRoot = Join-Path $projectRoot "release"
$stageRoot = Join-Path $releaseRoot "user_download"
$packageName = "GBT_Pro_${Version}_portable"
$packageDir = Join-Path $stageRoot $packageName
$zipPath = Join-Path $releaseRoot ("GBT_Pro_${Version}_portable_download.zip")
$shaPath = $zipPath + ".sha256.txt"
$runtimeDefault = Join-Path $projectRoot ("dist_runtime_fresh8\GBT_Pro_${Version}_dir_parallel")
$runtimeDir = if ($RuntimeDir) { $RuntimeDir } else { $runtimeDefault }
$runtimeDir = [System.IO.Path]::GetFullPath($runtimeDir)
$runtimeName = Split-Path $runtimeDir -Leaf
$runtimeExe = Join-Path $runtimeDir ($runtimeName + ".exe")
$configSource = Join-Path $projectRoot "config\mcp-config.json"
$bridgeSource = Join-Path $projectRoot "tools\mcp_stdio_ai_bridge.exe"

if (-not (Test-Path $runtimeDir)) {
    throw "缺少 runtime 目录: $runtimeDir"
}
if (-not (Test-Path $runtimeExe)) {
    throw "缺少 runtime exe: $runtimeExe"
}
if (-not (Test-Path $configSource)) {
    throw "缺少 MCP 配置: $configSource"
}
if (-not (Test-Path $bridgeSource)) {
    throw "缺少 MCP 桥接器: $bridgeSource"
}

New-Item -ItemType Directory -Force -Path $stageRoot | Out-Null
if (Test-Path $packageDir) {
    Remove-Item -Recurse -Force $packageDir
}
if (Test-Path $zipPath) {
    Remove-Item -Force $zipPath
}
if (Test-Path $shaPath) {
    Remove-Item -Force $shaPath
}

New-Item -ItemType Directory -Force -Path $packageDir | Out-Null
Copy-Item -Recurse -Force $runtimeDir (Join-Path $packageDir $runtimeName)
New-Item -ItemType Directory -Force -Path (Join-Path $packageDir "config") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $packageDir "tools") | Out-Null
Copy-Item -Force $configSource (Join-Path $packageDir "config\mcp-config.json")
Copy-Item -Force $bridgeSource (Join-Path $packageDir "tools\mcp_stdio_ai_bridge.exe")

$launcher = @"
@echo off
setlocal
cd /d "%~dp0"
set "GBT_MCP_CONFIG=%~dp0config\mcp-config.json"
start "" "%~dp0$runtimeName\$runtimeName.exe"
"@
Set-Content -Path (Join-Path $packageDir "Launch GBT Pro.bat") -Value $launcher -Encoding ASCII

$readme = @"
GBT Pro $Version Portable Package
================================

1. Download and extract this zip to any local folder.
2. Double-click Launch GBT Pro.bat.
3. If Windows prompts, choose allow/run.

Notes:
- No Python installation is required.
- This package runs locally on Windows.
- User data stays on the local device.
- MCP stdio bridge is bundled via config\mcp-config.json and tools\mcp_stdio_ai_bridge.exe.
"@
Set-Content -Path (Join-Path $packageDir "README_PORTABLE.txt") -Value $readme -Encoding ASCII

$manifest = @{
    product = "GBT Pro"
    version = $Version
    release_tag = "${Version}-desktop-runtime"
    package_type = "portable-runtime"
    artifacts = @{
        runtime_exe = @{
            path = "user_download\$packageName\$runtimeName\$runtimeName.exe"
        }
        launcher = @{
            path = "user_download\$packageName\Launch GBT Pro.bat"
        }
        mcp_config = @{
            path = "user_download\$packageName\config\mcp-config.json"
        }
        mcp_bridge = @{
            path = "user_download\$packageName\tools\mcp_stdio_ai_bridge.exe"
        }
    }
}
$manifest | ConvertTo-Json -Depth 6 | Set-Content -Path (Join-Path $packageDir "manifest.json") -Encoding UTF8

Compress-Archive -Path (Join-Path $packageDir "*") -DestinationPath $zipPath -CompressionLevel Optimal
$hash = (Get-FileHash -Algorithm SHA256 $zipPath).Hash.ToLowerInvariant()
Set-Content -Path $shaPath -Value $hash -Encoding ASCII

Write-Host "OK: portable package dir -> $packageDir"
Write-Host "OK: portable zip -> $zipPath"
Write-Host "OK: sha256 -> $shaPath"
Write-Host "OK: runtime -> $runtimeExe"
