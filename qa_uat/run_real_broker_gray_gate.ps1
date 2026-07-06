param(
    [string]$BaseUrl = "http://127.0.0.1:8765",
    [string]$ProjectRoot = "c:\Users\ADMIN\Desktop\自主操盘\GBTXIAOTUDOUAI",
    [string]$Broker = "同花顺",
    [string]$StockCode = "600519",
    [string]$TradeAction = "buy",
    [double]$Price = 1420.55,
    [int]$Lots = 100,
    [string]$ChatText = "打开浏览器",
    [string]$OutDir = "",
    [switch]$AppOnlyPreview
)

$ErrorActionPreference = "Stop"

if (-not $OutDir) {
    $OutDir = Join-Path $ProjectRoot "qa_uat"
}
if (-not (Test-Path $OutDir)) {
    New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
}

$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$reportJson = Join-Path $OutDir ("REAL_BROKER_GRAY_GATE_" + $ts + ".json")
$reportMd = Join-Path $OutDir ("REAL_BROKER_GRAY_GATE_" + $ts + ".md")
$results = New-Object System.Collections.Generic.List[object]

function Read-KeyValueFile {
    param([string]$Path)
    $map = @{}
    if (-not (Test-Path $Path)) { return $map }
    foreach ($line in Get-Content $Path) {
        if (-not $line) { continue }
        if ($line.Trim().StartsWith("#")) { continue }
        if ($line -notmatch "=") { continue }
        $pair = $line -split "=", 2
        $map[$pair[0].Trim()] = $pair[1].Trim()
    }
    return $map
}

function Invoke-ApiJson {
    param(
        [string]$Method,
        [string]$Url,
        $Body = $null
    )
    $headers = @{ "Content-Type" = "application/json" }
    $bodyText = $null
    if ($null -ne $Body) {
        $bodyText = $Body | ConvertTo-Json -Depth 8
    }
    $resp = Invoke-WebRequest -UseBasicParsing -SkipHttpErrorCheck -Method $Method -Uri $Url -Headers $headers -Body $bodyText -TimeoutSec 60
    $json = $null
    try {
        $json = $resp.Content | ConvertFrom-Json -Depth 100
    } catch {
        throw "接口不是 JSON: $Url -> $($resp.Content)"
    }
    return @{
        code = [int]$resp.StatusCode
        json = $json
        raw = $resp.Content
    }
}

function Add-Step {
    param(
        [string]$Name,
        [scriptblock]$Action
    )
    Write-Host "==== $Name ==== " -ForegroundColor Cyan
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $entry = [ordered]@{
        name = $Name
        status = "UNKNOWN"
        ms = -1
        detail = ""
        payload = $null
        response = $null
    }
    try {
        $result = & $Action
        $sw.Stop()
        $entry.ms = [int]$sw.ElapsedMilliseconds
        $entry.status = if ($result.ok) { "PASS" } else { "FAIL" }
        $entry.detail = $result.detail
        $entry.payload = $result.payload
        $entry.response = $result.response
    } catch {
        $sw.Stop()
        $entry.ms = [int]$sw.ElapsedMilliseconds
        $entry.status = "FAIL"
        $entry.detail = $_.Exception.Message
    }
    $results.Add([pscustomobject]$entry) | Out-Null
    $color = if ($entry.status -eq "PASS") { "Green" } else { "Red" }
    Write-Host ("[{0}] {1} ms" -f $entry.status, $entry.ms) -ForegroundColor $color
    if ($entry.detail) { Write-Host $entry.detail }
}

$runtimeIniPath = Join-Path $ProjectRoot "release\current_runtime.ini"
$manifestPath = Join-Path $ProjectRoot "release\manifest.json"
$zipPath = Join-Path $ProjectRoot "release\GBT_Pro_v1.1.19_portable_download.zip"
$shaPath = $zipPath + ".sha256.txt"
$runtimeInfo = Read-KeyValueFile $runtimeIniPath
$runtimeDir = if ($runtimeInfo["RUNTIME_DIR"]) { Join-Path $ProjectRoot $runtimeInfo["RUNTIME_DIR"] } else { "" }

Add-Step "01-候选包与哈希一致性" {
    if (-not (Test-Path $zipPath)) { throw "候选 ZIP 不存在: $zipPath" }
    if (-not (Test-Path $shaPath)) { throw "SHA256 文件不存在: $shaPath" }
    $expected = (Get-Content $shaPath -Raw).Trim().ToLowerInvariant()
    $actual = (Get-FileHash -Algorithm SHA256 $zipPath).Hash.ToLowerInvariant()
    if ($expected -ne $actual) {
        throw "ZIP 哈希不一致: expected=$expected actual=$actual"
    }
    @{
        ok = $true
        detail = "zip_hash_ok=$actual"
        payload = @{ zip = $zipPath; sha_file = $shaPath }
        response = @{ sha256 = $actual }
    }
}

Add-Step "02-运行时指针检查" {
    if (-not (Test-Path $runtimeIniPath)) { throw "缺少 current_runtime.ini" }
    if (-not $runtimeInfo["RUNTIME_EXE"]) { throw "current_runtime.ini 缺少 RUNTIME_EXE" }
    $runtimeExe = Join-Path $ProjectRoot $runtimeInfo["RUNTIME_EXE"]
    if (-not (Test-Path $runtimeExe)) { throw "运行时 EXE 不存在: $runtimeExe" }
    @{
        ok = $true
        detail = "runtime_exe=" + $runtimeExe
        payload = @{ runtime_ini = $runtimeIniPath }
        response = @{ runtime_dir = $runtimeDir; runtime_exe = $runtimeExe }
    }
}

Add-Step "03-服务状态" {
    $r = Invoke-ApiJson "GET" ($BaseUrl + "/api/status")
    if ($r.code -ne 200) { throw "status HTTP=$($r.code)" }
    if (-not $r.json.ok) { throw "status ok=false" }
    @{
        ok = $true
        detail = "version=$($r.json.version) role=$($r.json.role)"
        payload = $null
        response = $r.json
    }
}

Add-Step "04-真实动作链冒烟" {
    $payload = @{
        text = $ChatText
        deep_reasoning = $false
    }
    $r = Invoke-ApiJson "POST" ($BaseUrl + "/api/chat") $payload
    if ($r.code -ne 200) { throw "chat HTTP=$($r.code) body=$($r.raw)" }
    if (-not $r.json.ok) { throw "chat ok=false body=$($r.raw)" }
    @{
        ok = $true
        detail = "chat_action_ok"
        payload = $payload
        response = $r.json
    }
}

Add-Step "05-接管预检" {
    $payload = @{
        id = "trade_takeover_precheck"
        broker = $Broker
        stock_code = $StockCode
        trade_action = $TradeAction
        price = $Price
        lots = $Lots
        auto_focus = $true
        auto_navigate = $true
    }
    if ($AppOnlyPreview) { $payload["app_only"] = $true }
    $r = Invoke-ApiJson "POST" ($BaseUrl + "/api/desktop/exec") $payload
    if ($r.code -ne 200) { throw "precheck HTTP=$($r.code) body=$($r.raw)" }
    if (-not $r.json.ok) { throw "precheck ok=false body=$($r.raw)" }
    $passText = if ($r.json.precheck_passed) { "passed" } else { "pending" }
    @{
        ok = $true
        detail = "precheck=$passText next=" + ($r.json.next_action_id | Out-String).Trim()
        payload = $payload
        response = $r.json
    }
}

Add-Step "06-唯一下一步预演" {
    $payload = @{
        id = "trade_execute_next"
        broker = $Broker
        stock_code = $StockCode
        trade_action = $TradeAction
        price = $Price
        lots = $Lots
        auto_focus = $true
        auto_navigate = $true
        dry_run = $true
    }
    if ($AppOnlyPreview) { $payload["app_only"] = $true }
    $r = Invoke-ApiJson "POST" ($BaseUrl + "/api/desktop/exec") $payload
    if ($r.code -ne 200) { throw "execute_next HTTP=$($r.code) body=$($r.raw)" }
    if (-not $r.json.ok) { throw "execute_next ok=false body=$($r.raw)" }
    @{
        ok = $true
        detail = "planned=" + (($r.json.planned_action | Out-String).Trim())
        payload = $payload
        response = $r.json
    }
}

Add-Step "07-闭环验证预演" {
    $payload = @{
        id = "trade_live_validate"
        broker = $Broker
        stock_code = $StockCode
        trade_action = $TradeAction
        price = $Price
        lots = $Lots
        auto_focus = $true
        auto_navigate = $true
        capture_evidence = $true
        dry_run = $true
    }
    if ($AppOnlyPreview) { $payload["app_only"] = $true }
    $r = Invoke-ApiJson "POST" ($BaseUrl + "/api/desktop/exec") $payload
    if ($r.code -ne 200) { throw "live_validate HTTP=$($r.code) body=$($r.raw)" }
    if (-not $r.json.ok) { throw "live_validate ok=false body=$($r.raw)" }
    $reportPath = ""
    if ($r.json.report -and $r.json.report.evidence) {
        $reportPath = $r.json.report.evidence.report_path
    }
    @{
        ok = $true
        detail = "evidence_plan=" + $reportPath
        payload = $payload
        response = $r.json
    }
}

Add-Step "08-发布门禁状态检查" {
    if (-not (Test-Path $manifestPath)) { throw "缺少 manifest.json" }
    $manifest = Get-Content $manifestPath -Raw | ConvertFrom-Json -Depth 100
    if (-not $manifest.release_gate) { throw "manifest 缺少 release_gate" }
    if ($manifest.release_gate.production_release_allowed) {
        throw "release_gate 异常: 当前不应允许正式放量"
    }
    @{
        ok = $true
        detail = "gate_status=" + $manifest.release_gate.status
        payload = $null
        response = $manifest.release_gate
    }
}

$failedCount = ($results | Where-Object { $_.status -eq "FAIL" }).Count
$summary = [ordered]@{
    started_at = (Get-Date).ToString("o")
    base_url = $BaseUrl
    broker = $Broker
    stock_code = $StockCode
    trade_action = $TradeAction
    app_only_preview = [bool]$AppOnlyPreview
    total = $results.Count
    passed = ($results | Where-Object { $_.status -eq "PASS" }).Count
    failed = $failedCount
    candidate_zip = $zipPath
    sha256 = if (Test-Path $shaPath) { (Get-Content $shaPath -Raw).Trim() } else { "" }
    runtime_dir = $runtimeDir
    checklist_path = "qa_uat\REAL_BROKER_GRAY_ACCEPTANCE_20260705.md"
    steps = $results
    manual_pending = @(
        "真实券商窗口登录态检查",
        "真实 trade_panel_probe 回读确认",
        "最小风险单量灰度执行",
        "回滚演练留档",
        "签收人复核"
    )
}

$summary | ConvertTo-Json -Depth 10 | Set-Content -Path $reportJson -Encoding UTF8

$md = @()
$md += "# 真实券商灰度门禁报告"
$md += ""
$md += "- 时间：" + (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
$md += "- 模式：" + ($(if ($AppOnlyPreview) { "AppOnlyPreview" } else { "RealBrokerGray" }))
$md += "- 候选包：release/GBT_Pro_v1.1.19_portable_download.zip"
$md += "- SHA256：" + $summary.sha256
$md += "- 运行时：" + $runtimeDir
$md += "- 结果：" + ($(if ($failedCount -gt 0) { "BLOCK" } else { "PRECHECK PASS" }))
$md += ""
$md += "## 自动步骤"
$md += ""
foreach ($item in $results) {
    $md += "- [" + $item.status + "] " + $item.name + " | " + $item.detail
}
$md += ""
$md += "## 人工待办"
$md += ""
foreach ($item in $summary.manual_pending) {
    $md += "- [ ] " + $item
}
$md += ""
$md += "## 归档"
$md += ""
$md += "- JSON 报告：" + $reportJson
$md += "- 清单：qa_uat\REAL_BROKER_GRAY_ACCEPTANCE_20260705.md"
$md -join "`r`n" | Set-Content -Path $reportMd -Encoding UTF8

Write-Host ""
Write-Host "==== Gray Gate 汇总 ====" -ForegroundColor Magenta
Write-Host ("通过: {0}  失败: {1}  总计: {2}" -f $summary.passed, $summary.failed, $summary.total)
Write-Host "JSON: $reportJson"
Write-Host "Markdown: $reportMd"

if ($failedCount -gt 0) {
    Write-Host "RESULT: BLOCK · 禁止进入真实券商灰度" -ForegroundColor Red
    exit 2
}

Write-Host "RESULT: PASS · 允许进入真实券商登录态灰度" -ForegroundColor Green
exit 0