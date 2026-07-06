param(
    [string]$AppName = "",
    [string]$DistRoot = "",
    [string]$WorkRoot = "",
    [switch]$SwitchCurrentRuntime
)

$ErrorActionPreference = "Stop"

$projectRoot = $PSScriptRoot
Set-Location $projectRoot

$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "缺少虚拟环境 Python: $python"
}

$defaultAppName = "GBT_Pro_v1.1.22_dir_parallel"
if (-not $AppName) { $AppName = $defaultAppName }
if (-not $DistRoot) { $DistRoot = Join-Path $projectRoot "dist_rebuild_parallel" }
if (-not $WorkRoot) { $WorkRoot = Join-Path $projectRoot "build_runtime_dir_parallel" }
$appName = $AppName
$distRoot = $DistRoot
$workRoot = $WorkRoot
$runtimeDir = Join-Path $distRoot $appName
$runtimeExe = Join-Path $runtimeDir ($appName + ".exe")
$calendarPath = Join-Path $runtimeDir "_internal\akshare\file_fold\calendar.json"

$args = @(
    "-m", "PyInstaller",
    "--onedir",
    "--noconfirm",
    "--noconsole",
    "--noupx",
    "--name", $appName,
    "--icon", "desktop\GBT.ico",
    "--manifest", "release\gbtpro.manifest",
    "--add-data", "desktop\templates;templates",
    "--add-data", "desktop\GBT_logo.png;.",
    "--add-data", "desktop\GBT.ico;.",
    "--add-data", "gbt\connectors;gbt\connectors",
    "--add-data", "gbt\api;gbt\api",
    "--add-data", "gbt\mirror_space;gbt\mirror_space",
    "--add-data", "gbt\migrations;gbt\migrations",
    "--add-data", "gbt\templates;gbt\templates",
    "--add-data", "gbt\knowledge;gbt\knowledge",
    "--add-data", "gbt\gcc;gbt\gcc",
    "--collect-all", "curl_cffi",
    "--collect-all", "akshare",
    "--hidden-import", "bcrypt",
    "--hidden-import", "flask",
    "--hidden-import", "akshare",
    "--hidden-import", "curl_cffi",
    "--hidden-import", "cryptography",
    "--hidden-import", "gbt.api",
    "--hidden-import", "gbt.api.chat",
    "--hidden-import", "gbt.api.hacker",
    "--hidden-import", "gbt.api.market",
    "--hidden-import", "gbt.api.auth",
    "--hidden-import", "gbt.api.account",
    "--hidden-import", "gbt.api.dash",
    "--hidden-import", "gbt.api.dashboard",
    "--hidden-import", "gbt.api.payment",
    "--hidden-import", "gbt.api.pilot",
    "--hidden-import", "gbt.api.mcp",
    "--hidden-import", "gbt.api.audit",
    "--hidden-import", "gbt.api.mirror",
    "--hidden-import", "gbt.api.llm",
    "--hidden-import", "gbt.api.llm_config",
    "--hidden-import", "gbt.api.llm_metrics",
    "--hidden-import", "gbt.api.token",
    "--hidden-import", "gbt.api.token_recharge",
    "--hidden-import", "gbt.api.charge",
    "--hidden-import", "gbt.api.recharge",
    "--hidden-import", "gbt.api.desktop",
    "--hidden-import", "gbt.api.auth_oauth",
    "--hidden-import", "gbt.api.oauth",
    "--hidden-import", "gbt.api.paper",
    "--hidden-import", "gbt.api.trader",
    "--hidden-import", "gbt.pay_futurapay",
    "--hidden-import", "gbt.pay_widget_probe",
    "--hidden-import", "gbt.payment_lock",
    "--hidden-import", "gbt.release_meta",
    "--hidden-import", "gbt.mcp",
    "--hidden-import", "gbt.oauth_catalog",
    "--hidden-import", "gbt.providers",
    "--hidden-import", "gbt.live_market",
    "--hidden-import", "gbt.tech_analysis",
    "--hidden-import", "gbt.broker_bridge",
    "--hidden-import", "gbt.mirror_space",
    "--hidden-import", "gbt.mirror_space.bridge",
    "--hidden-import", "gbt.mirror_space.mirror_skill",
    "--hidden-import", "gbt.mirror_space.sandbox-orchestrator",
    "--hidden-import", "gbt.mirror_space.immutable_deploy",
    "--hidden-import", "qrcode",
    "--hidden-import", "qrcode.image.pure",
    "--exclude-module", "_pytest",
    "--exclude-module", "pytest",
    "--exclude-module", "tests",
    "--exclude-module", "transformers",
    "--exclude-module", "torch",
    "--exclude-module", "torchvision",
    "--exclude-module", "torchaudio",
    "--exclude-module", "tensorflow",
    "--exclude-module", "keras",
    "--exclude-module", "pyarrow",
    "--exclude-module", "numba",
    "--exclude-module", "scipy",
    "--exclude-module", "matplotlib",
    "--exclude-module", "sklearn",
    "--exclude-module", "Xlib",
    "--exclude-module", "mouseinfo",
    "--exclude-module", "Quartz",
    "--exclude-module", "AppKit",
    "--exclude-module", "pyautogui._pyautogui_x11",
    "--exclude-module", "pyautogui._pyautogui_osx",
    "--distpath", $distRoot,
    "--workpath", $workRoot,
    "--log-level", "WARN",
    "desktop_app.py"
)

& $python @args
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller 构建失败，退出码: $LASTEXITCODE"
}

if (-not (Test-Path $calendarPath)) {
    throw "打包失败：缺少 akshare 持久化资源 $calendarPath"
}

if ($SwitchCurrentRuntime) {
    $runtimeDirRel = [System.IO.Path]::GetRelativePath($projectRoot, $runtimeDir)
    $runtimeExeRel = [System.IO.Path]::GetRelativePath($projectRoot, $runtimeExe)
    $currentIni = Join-Path $projectRoot "release\current_runtime.ini"
    $iniLines = @(
        "APP_NAME=GBT Pro",
        "APP_VERSION=v1.1.22",
        "RELEASE_TAG=v1.1.22-desktop-runtime",
        "RUNTIME_DIR=$runtimeDirRel",
        "RUNTIME_EXE=$runtimeExeRel"
    )
    Set-Content -Path $currentIni -Value $iniLines -Encoding ASCII
    Write-Host "OK: current_runtime.ini switched -> $runtimeExeRel"
}

Write-Host "OK: runtime rebuilt with akshare resource -> $calendarPath"
Write-Host "OK: runtime exe -> $runtimeExe"
