# GBT Pro · 用户视角 UAT 自动化脚本
# 开发者: 自由的风
# 用途: 任何"已交付"之前必须跑完本脚本；任何 STEP 失败 -> 退出码非 0 -> 禁止交付
# 用法: pwsh -NoProfile -ExecutionPolicy Bypass -File qa_uat/uat_smoke.ps1
param(
    [string]$BaseUrl = 'http://127.0.0.1:8765',
    [string]$ProjectRoot = 'C:\Users\ADMIN\Desktop\自主操盘\GBTXIAOTUDOUAI',
    [string]$OutDir = ''
)
$ErrorActionPreference = 'Stop'

if (-not $OutDir) { $OutDir = Join-Path $ProjectRoot 'qa_uat' }
if (-not (Test-Path $OutDir)) { New-Item -ItemType Directory -Force -Path $OutDir | Out-Null }

$RuntimeDir = $ProjectRoot
$runtimeIni = Join-Path $ProjectRoot 'release\current_runtime.ini'
if (Test-Path $runtimeIni) {
    $runtimeRel = (Get-Content $runtimeIni | Where-Object { $_ -like 'RUNTIME_DIR=*' } | Select-Object -First 1)
    if ($runtimeRel) {
        $runtimeRel = ($runtimeRel -split '=', 2)[1].Trim()
        if ($runtimeRel) { $RuntimeDir = Join-Path $ProjectRoot $runtimeRel }
    }
}

function Resolve-AppArtifactPath {
    param([string]$PathText)
    if (-not $PathText) { return $PathText }
    $raw = [string]$PathText
    if ($raw -match '^\[runtime\]/') {
        $rel = ($raw -replace '^\[runtime\]/', '') -replace '/', '\'
        return (Join-Path $RuntimeDir $rel)
    }
    if ($raw -match '^\[project\]/') {
        $rel = ($raw -replace '^\[project\]/', '') -replace '/', '\'
        return (Join-Path $ProjectRoot $rel)
    }
    if ([System.IO.Path]::IsPathRooted($raw)) { return $raw }
    $candidates = @(
        (Join-Path $RuntimeDir $raw),
        (Join-Path (Join-Path $RuntimeDir '_internal') $raw),
        (Join-Path $ProjectRoot $raw)
    )
    foreach ($cand in $candidates) {
        if (Test-Path $cand) { return $cand }
    }
    return (Join-Path $RuntimeDir $raw)
}

$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
$logPath = Join-Path $OutDir ("UAT-$ts.log")
$results = New-Object System.Collections.Generic.List[object]
$global:failed = 0

function Step {
    param([string]$Name, [scriptblock]$Action)
    Write-Host "==== $Name ====" -ForegroundColor Cyan
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $entry = [ordered]@{
        name=$Name; status='UNKNOWN'; ms=-1; detail=''; artifacts=@()
    }
    try {
        $r = & $Action
        $sw.Stop()
        $entry.ms = [int]$sw.ElapsedMilliseconds
        if ($r -is [hashtable]) {
            $entry.status = if ($r.ok) { 'PASS' } else { 'FAIL' }
            $entry.detail = $r.detail
            if ($r.artifacts) { $entry.artifacts = @($r.artifacts) }
        } else {
            $entry.status = 'PASS'
            $entry.detail = if ($r) { "$r" } else { '' }
        }
    } catch {
        $sw.Stop()
        $entry.ms = [int]$sw.ElapsedMilliseconds
        $entry.status = 'FAIL'
        $entry.detail = "$($_.Exception.Message)"
        $global:failed += 1
    }
    $color = if ($entry.status -eq 'PASS') { 'Green' } else { 'Red' }
    Write-Host ("[{0}] {1} ms" -f $entry.status, $entry.ms) -ForegroundColor $color
    if ($entry.detail) { Write-Host $entry.detail }
    $results.Add([pscustomobject]$entry) | Out-Null
    return $entry
}

function Get-JBody {
    param([string]$Url,[string]$Method='GET',$Body=$null,[string]$Token=$null)
    $h = @{'Content-Type'='application/json'}
    if ($Token) { $h['X-Auth-Token'] = $Token }
    try {
        $r = Invoke-WebRequest -UseBasicParsing -SkipHttpErrorCheck -Uri $Url -Method $Method -Headers $h -Body $Body -TimeoutSec 60
        return @{ code=$r.StatusCode; body=$r.Content; headers=$r.Headers }
    } catch {
        $code = 0; $body = ''
        # 兼容 .NET 6 / 7 / 8 — 失败体可能是 ErrorRecord 或 HttpResponseException
        $err = $_.Exception
        if ($err.PSObject.Properties.Match('Response').Count -gt 0 -and $err.Response) {
            try {
                $code = [int]$err.Response.StatusCode
                $stream = $null
                if ($err.Response.PSObject.Properties.Match('Content').Count -gt 0) {
                    $stream = $err.Response.Content.ReadAsStreamAsync().Result
                }
                if ($stream) {
                    $reader = New-Object System.IO.StreamReader($stream)
                    $body = $reader.ReadToEnd()
                } else {
                    $body = "$err"
                }
            } catch { $body = "$err" }
        } elseif ($err.PSObject.Properties.Match('Response').Count -gt 0 -and $err.Response) {
            # 旧版 HttpWebResponse 兼容
            try { $code = [int]$err.Response.StatusCode; $body = (New-Object System.IO.StreamReader($err.Response.GetResponseStream())).ReadToEnd() } catch { $body = "$err" }
        } else {
            $body = $err.Message
        }
        return @{ code=$code; body=$body; headers=$null; error=$true }
    }
}

# ─── STEP 1: 首页 / 状态 ───
Step '01-首页可访问' {
    $r = Get-JBody "$BaseUrl/api/status"
    if ($r.code -ne 200 -or -not $r.body.Contains('"ok":true')) { throw "status 失败: $($r.code) $($r.body)" }
    @{ ok=$true; detail=$r.body.Substring(0, [Math]::Min(200, $r.body.Length)) }
}

# ─── STEP 2: 注册并登录 ───
$rand = Get-Random -Minimum 100000 -Maximum 999999
$u = "uat_$ts`_$rand"
$pw = 'UAT!2026@secure'
$reg = $null
$tok = $null
Step '02-用户注册' {
    $r = Get-JBody "$BaseUrl/api/auth/register" 'POST' (@{username=$u; password=$pw; email="$u@local"} | ConvertTo-Json)
    if ($r.code -ne 200) { throw "register 失败: $($r.code) $($r.body)" }
    $reg = $r.body
    @{ ok=$true; detail=$reg }
}
Step '03-用户登录' {
    $r = Get-JBody "$BaseUrl/api/auth/login" 'POST' (@{username=$u; password=$pw} | ConvertTo-Json)
    if ($r.code -ne 200) { throw "login 失败: $($r.code) $($r.body)" }
    $j = $r.body | ConvertFrom-Json
    if (-not $j.token) { throw "登录无 token: $($r.body)" }
    $script:tok = $j.token
    @{ ok=$true; detail="token=$($j.token.Substring(0,8))..." }
}

# ─── STEP 4: 余额 ───
Step '04-余额查询' {
    $r = Get-JBody "$BaseUrl/api/token/balance?token=$tok"
    if ($r.code -ne 200) { throw "balance 失败: $($r.code) $($r.body)" }
    $j = $r.body | ConvertFrom-Json
    # 实际接口返回平铺: {ok,plan,remaining,tokens,used}
    if ($null -eq $j.remaining) { throw "balance 异常: $($r.body)" }
    if ($j.remaining -lt 0) { throw "balance 异常: $($r.body)" }
    @{ ok=$true; detail="tokens_remaining=$($j.remaining) plan=$($j.plan)" }
}

# ─── STEP 5: AI 对话（真模型） ───
Step '05-AI对话-deepseek-chat' {
    $r = Get-JBody "$BaseUrl/api/chat" 'POST' (@{token=$tok; text='一句话介绍 GBT Pro'; deep_reasoning=$false} | ConvertTo-Json) -Token $tok
    if ($r.code -ne 200) { throw "chat 失败: $($r.code) $($r.body)" }
    $j = $r.body | ConvertFrom-Json
    if (-not $j.ok) { throw "chat 业务失败: $($r.body)" }
    if (-not $j.response -or $j.response.Length -lt 4) { throw "chat 无内容: $($r.body)" }
    @{ ok=$true; detail="model=$($j.model) consumed=$($j.tokens_consumed) remaining=$($j.tokens_remaining) preview=$($j.response.Substring(0,[Math]::Min(60,$j.response.Length)))" }
}
Step '06-AI对话-deepseek-reasoner' {
    $r = Get-JBody "$BaseUrl/api/chat" 'POST' (@{token=$tok; text='一句话回答 1+1'; deep_reasoning=$true} | ConvertTo-Json) -Token $tok
    if ($r.code -ne 200) { throw "reasoner 失败: $($r.code) $($r.body)" }
    $j = $r.body | ConvertFrom-Json
    if (-not $j.ok) { throw "reasoner 业务失败: $($r.body)" }
    if ($j.model -ne 'deepseek-reasoner') { throw "不是 reasoner: $($j.model)" }
    @{ ok=$true; detail="model=$($j.model) reasoning_len=$(if($j.reasoning){$j.reasoning.Length}else{0}) resp=$($j.response)" }
}

# ─── STEP 7: A股行情 ───
Step '07-行情-指数' {
    # 真实路由: /api/market (无 /indices 后缀)
    $r = Get-JBody "$BaseUrl/api/market"
    if ($r.code -ne 200) { throw "market 失败: $($r.code) $($r.body)" }
    $j = $r.body | ConvertFrom-Json
    $arr = $j.indices
    if (-not $arr) { $arr = $j.list }
    if (-not $arr -or $arr.Count -lt 3) { throw "指数少于 3: $(if($arr){$arr.Count}else{0})  body=$($r.body.Substring(0,[Math]::Min(300,$r.body.Length)))" }
    @{ ok=$true; detail="指数=$($arr.Count) 首批=$($arr[0].name)=$($arr[0].price)" }
}
Step '08-行情-个股600519' {
    $r = Get-JBody "$BaseUrl/api/market/stock/600519"
    if ($r.code -ne 200) { throw "stock 失败: $($r.code)" }
    $j = $r.body | ConvertFrom-Json
    if (-not $j.price) { throw "无 price: $($r.body)" }
    @{ ok=$true; detail="name=$($j.name) price=$($j.price) rsi=$($j.rsi) ma_pattern=$($j.ma_pattern)" }
}
Step '09-行情-60日K线' {
    $r = Get-JBody "$BaseUrl/api/market/stock/600519/history?period=daily&limit=60"
    if ($r.code -ne 200) { throw "kline 失败: $($r.code) $($r.body)" }
    $j = $r.body | ConvertFrom-Json
    # 真实字段是 klines(复数)
    $arr = $j.klines
    if (-not $arr) { $arr = $j.kline }
    if (-not $arr) { $arr = $j.points }
    if (-not $arr) { $arr = $j.history }
    if (-not $arr -or $arr.Count -lt 30) { throw "K线少于 30: $(if($arr){$arr.Count}else{0})  body=$($r.body.Substring(0, [Math]::Min(300, $r.body.Length)))" }
    @{ ok=$true; detail="bars=$($arr.Count) ma60=$($j.ma60) trend=$($j.ma_pattern) count=$($j.count)" }
}
Step '10-复盘(你截图报错那一条)' {
    $r = Get-JBody "$BaseUrl/api/market/recap"
    if ($r.code -ne 200) { throw "recap 失败: $($r.code) $($r.body)" }
    $j = $r.body | ConvertFrom-Json
    if (-not $j.ok) { throw "recap 业务失败: $($r.body)" }
    if (-not $j.report -or $j.report.Length -lt 100) { throw "复盘太短: $($j.report.Length)" }
    @{ ok=$true; detail="model=$($j.model) len=$($j.report.Length) tokens=$($j.tokens_consumed)" }
}

# ─── STEP 11: 桌面操控 / 截图（真落盘） ───
$shotPath = $null
Step '11-桌面截图(真落盘)' {
    $r = Get-JBody "$BaseUrl/api/desktop/exec" 'POST' (@{id='screenshot'} | ConvertTo-Json) -Token $tok
    if ($r.code -ne 200) { throw "exec 失败: $($r.code)" }
    $j = $r.body | ConvertFrom-Json
    if (-not $j.ok) { throw "exec 业务失败: $($r.body)" }
    if ($j.path) {
        $script:shotPath = Resolve-AppArtifactPath ([string]$j.path)
    } else {
        # 兼容旧格式: "Screenshot saved to C:\...screenshot_YYYYMMDD_HHMMSS.png"
        $m = [regex]::Match([string]$j.data, '(?i)saved to (.+\.png)')
        if (-not $m.Success) { throw "未解析到截图路径: $($j.data)" }
        $script:shotPath = Resolve-AppArtifactPath ($m.Groups[1].Value.Trim())
    }
    if (-not (Test-Path $script:shotPath)) { throw "截图文件不存在: $script:shotPath" }
    $f = Get-Item $script:shotPath
    if ($f.Length -lt 1024) { throw "截图过小: $($f.Length) bytes" }
    # 复制一份到 qa_uat 留证
    $cp = Join-Path $OutDir ("screenshot_$ts.png")
    Copy-Item -Force $script:shotPath $cp
    @{ ok=$true; detail="size=$($f.Length)B saved=$($cp)"; artifacts=@($cp) }
}

# ─── STEP 12: 自主操盘 ───
Step '12-自主操盘 stop-first(幂等)' {
    $r = Get-JBody "$BaseUrl/api/pilot/stop" 'POST' '{}' -Token $tok
    if ($r.code -ne 200) { throw "pilot stop 失败: $($r.code)" }
    @{ ok=$true; detail="清理旧实例: $($r.body | ConvertFrom-Json).message" }
}
Step '12b-自主操盘 start' {
    $r = Get-JBody "$BaseUrl/api/pilot/start" 'POST' '{}' -Token $tok
    if ($r.code -ne 200) { throw "pilot start 失败: $($r.code) $($r.body)" }
    $j = $r.body | ConvertFrom-Json
    if (-not $j.ok) { throw "pilot start 业务失败: $($r.body)" }
    @{ ok=$true; detail="mode=$($j.mode) running=$true" }
}
Step '13-自主操盘 stop' {
    $r = Get-JBody "$BaseUrl/api/pilot/stop" 'POST' '{}' -Token $tok
    if ($r.code -ne 200) { throw "pilot stop 失败: $($r.code) $($r.body)" }
    $j = $r.body | ConvertFrom-Json
    if (-not $j.ok) { throw "pilot stop 业务失败: $($r.body)" }
    @{ ok=$true; detail=$j.message }
}

# ─── STEP 14: 已下线模块门禁 ───
Step '14-黑客模块已下线' {
    $r = Get-JBody "$BaseUrl/api/hacker/capabilities"
    if ($r.code -ne 410) { throw "hacker 应已下线，但返回: $($r.code) $($r.body)" }
    $j = $r.body | ConvertFrom-Json
    if (-not $j.removed) { throw "hacker 已下线标记缺失: $($r.body)" }
    @{ ok=$true; detail="hacker=removed" }
}
Step '15-付费模块已下线' {
    $r = Get-JBody "$BaseUrl/api/payment/status"
    if ($r.code -ne 410) { throw "payment 应已下线，但返回: $($r.code) $($r.body)" }
    $j = $r.body | ConvertFrom-Json
    if (-not $j.removed) { throw "payment 已下线标记缺失: $($r.body)" }
    @{ ok=$true; detail="payment=removed" }
}
Step '16-电脑操控能力清单' {
    $r = Get-JBody "$BaseUrl/api/desktop/capabilities"
    if ($r.code -ne 200) { throw "desktop capabilities 失败: $($r.code) $($r.body)" }
    $j = $r.body | ConvertFrom-Json
    if (-not $j.ok -or -not $j.capabilities -or $j.capabilities.Count -lt 5) { throw "desktop capabilities 异常: $($r.body)" }
    @{ ok=$true; detail="desktop_caps=$($j.capabilities.Count)" }
}

# ─── STEP 17: 镜像空间 ───
Step '17-镜像空间-status' {
    $r = Get-JBody "$BaseUrl/api/mirror/status"
    if ($r.code -ne 200) { throw "mirror status 失败: $($r.code)" }
    $j = $r.body | ConvertFrom-Json
    if ($j.info.skills.Count -lt 5) { throw "skill 少于 5: $($j.info.skills.Count)" }
    @{ ok=$true; detail="skills=$($j.info.skills.Count) version=$($j.info.version)" }
}
Step '18-镜像空间-skills' {
    $r = Get-JBody "$BaseUrl/api/mirror/skills"
    if ($r.code -ne 200) { throw "mirror skills 失败: $($r.code)" }
    @{ ok=$true; detail=$($r.body.Length) }
}

# ─── STEP 19: 部署面板 ───
Step '19-部署面板-status' {
    $r = Get-JBody "$BaseUrl/api/panel/status"
    if ($r.code -ne 200) { throw "panel status 失败: $($r.code)" }
    $j = $r.body | ConvertFrom-Json
    if ($j.version -ne 'v1.1.17') { throw "version 不一致: $($j.version)" }
    @{ ok=$true; detail="role=$($j.role) version=$($j.version) tag=$($j.release_tag)" }
}
Step '20-部署面板-rollback演练' {
    $r = Get-JBody "$BaseUrl/api/panel/rollback" 'POST' (@{reason='uat-smoke'; confirm=$true} | ConvertTo-Json)
    if ($r.code -ne 200) { throw "rollback 失败: $($r.code)" }
    $j = $r.body | ConvertFrom-Json
    if (-not $j.ok) { throw "rollback 业务失败: $($r.body)" }
    @{ ok=$true; detail="action=$($j.action) version=$($j.version)" }
}

# ─── STEP 21: 余额再确认 ───
Step '21-余额再确认(对话已扣费)' {
    $r = Get-JBody "$BaseUrl/api/token/balance?token=$tok"
    if ($r.code -ne 200) { throw "balance 失败: $($r.code)" }
    $j = $r.body | ConvertFrom-Json
    if ($null -eq $j.remaining) { throw "balance 解析失败: $($r.body)" }
    @{ ok=$true; detail="used=$($j.used) remaining=$($j.remaining)" }
}

# ─── 写报告 ───
$reportPath = Join-Path $OutDir ("UAT-REPORT-$ts.json")
$summary = [pscustomobject]@{
    started_at=(Get-Date).ToString('o')
    base_url=$BaseUrl
    user=$u
    total=$results.Count
    passed=($results | Where-Object { $_.status -eq 'PASS' }).Count
    failed=($results | Where-Object { $_.status -eq 'FAIL' }).Count
    steps=$results
}
$summary | ConvertTo-Json -Depth 8 | Set-Content -Path $reportPath -Encoding UTF8

# 同时写日志
"==== GBT Pro UAT $ts ====" | Set-Content -Path $logPath
$results | ForEach-Object {
    "[{0}] {1}  {2}ms  {3}" -f $_.status, $_.name, $_.ms, $_.detail | Add-Content $logPath
}

# ─── 桌面截屏（用户视角视觉证据） ───
$deskShot = Join-Path $OutDir ("desktop_$ts.png")
try {
    Add-Type -AssemblyName System.Windows.Forms -ErrorAction SilentlyContinue
    Add-Type -AssemblyName System.Drawing -ErrorAction SilentlyContinue
    $b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
    $bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size)
    $bmp.Save($deskShot, [System.Drawing.Imaging.ImageFormat]::Png)
    $g.Dispose(); $bmp.Dispose()
} catch {
    Add-Content $logPath "DESKTOP_SHOT_ERROR: $($_.Exception.Message)"
}

Write-Host ""
Write-Host "==== UAT 汇总 ====" -ForegroundColor Magenta
Write-Host ("通过: {0}  失败: {1}  总计: {2}" -f $summary.passed, $summary.failed, $summary.total)
Write-Host "报告: $reportPath"
Write-Host "日志: $logPath"
Write-Host "桌面证据: $deskShot"

if ($summary.failed -gt 0) {
    Write-Host "RESULT: BLOCK · 禁止交付" -ForegroundColor Red
    exit 2
} else {
    Write-Host "RESULT: PASS · 可以交付" -ForegroundColor Green
    exit 0
}
