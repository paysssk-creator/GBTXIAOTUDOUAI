$ErrorActionPreference = "Continue"
Add-Type -AssemblyName System.Net.Http
$cli = New-Object System.Net.Http.HttpClient
$cli.Timeout = [TimeSpan]::FromSeconds(90)
$BASE = "http://127.0.0.1:8765"
$ts = Get-Date -Format "yyyyMMddHHmmss"
$USER = "audit_$ts"
$PASS = "Audit!2026"
$PASS_COUNT = 0
$FAIL_COUNT = 0
$FAILS = @()

function Test-Endpoint($label, $method, $path, $body) {
    try {
        if ($method -eq "GET") {
            $resp = $cli.GetAsync("$BASE$path").Result
        } else {
            $content = New-Object System.Net.Http.StringContent($body, [System.Text.Encoding]::UTF8, "application/json")
            $resp = $cli.PostAsync("$BASE$path", $content).Result
        }
        $txt = $resp.Content.ReadAsStringAsync().Result
        $code = [int]$resp.StatusCode
        $removedExpected = $label -like "*Removed*"
        if (($code -ge 200 -and $code -lt 300) -or ($removedExpected -and $code -eq 410)) {
            Write-Host "[PASS] $label ($code)" -ForegroundColor Green
            $script:PASS_COUNT++
            return @{label=$label; code=$code; body=$txt; pass=$true}
        } else {
            $short = if ($txt.Length -gt 300) { $txt.Substring(0,300) + "..." } else { $txt }
            Write-Host "[FAIL] $label ($code): $short" -ForegroundColor Red
            $script:FAIL_COUNT++
            $script:FAILS += "$label (HTTP $code)"
            return @{label=$label; code=$code; body=$txt; pass=$false}
        }
    } catch {
        Write-Host "[CRASH] $label : $_" -ForegroundColor Red
        $script:FAIL_COUNT++
        $script:FAILS += "$label (CRASH)"
        return @{label=$label; code=0; body=""; pass=$false}
    }
}

function Assert-JsonOk($result, $label) {
    try {
        $j = $result.body | ConvertFrom-Json
        if ($null -ne $j.ok -and -not $j.ok) {
            Write-Host "[FAIL] $label (ok=false): $($j.error)" -ForegroundColor Red
            $script:FAIL_COUNT++
            $script:FAILS += "$label (ok=false)"
            return $false
        }
    } catch {}
    return $true
}

Write-Host "========== A2: LOGIN & TOKEN =========="
$r = Test-Endpoint "A2.1 Status" "GET" "/api/status" $null
$regBody = '{"username":"' + $USER + '","password":"' + $PASS + '","email":"' + $USER + '@test.com"}'
$r = Test-Endpoint "A2.2 Register" "POST" "/api/auth/register" $regBody
$loginBody = '{"username":"' + $USER + '","password":"' + $PASS + '"}'
$r = Test-Endpoint "A2.3 Login" "POST" "/api/auth/login" $loginBody
$TOKEN = ""
$AUTH_TOKEN = ""
try { $j = $r.body | ConvertFrom-Json; $TOKEN = $j.token; $AUTH_TOKEN = $j.token } catch {}
if ($TOKEN) {
    Write-Host "Token obtained"
    $cli.DefaultRequestHeaders.Authorization = New-Object System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", $TOKEN)
    $cli.DefaultRequestHeaders.Remove("X-Auth-Token")
    $cli.DefaultRequestHeaders.Add("X-Auth-Token", $AUTH_TOKEN)
} else { Write-Host "NO TOKEN" -ForegroundColor Red }

# PAYMENT / RECHARGE REMOVED
Write-Host "========== PRE: PAYMENT REMOVED =========="
Start-Sleep -Seconds 1
Test-Endpoint "PRE.1 Recharge Removed" "POST" "/api/token/recharge" '{}'

Write-Host "========== A3: DASHBOARD =========="
Test-Endpoint "A3.1 System Metrics" "GET" "/api/system" $null
Test-Endpoint "A3.2 Dashboard" "GET" "/api/dashboard" $null
Test-Endpoint "A3.3 LLM Config" "GET" "/api/config/llm" $null
Test-Endpoint "A3.4 Account" "GET" "/api/account" $null
Test-Endpoint "A3.5 Token Balance" "GET" "/api/token/balance" $null
Test-Endpoint "A3.6 Token Plans" "GET" "/api/token/plans" $null

Write-Host "========== A4: AI CHAT =========="
Start-Sleep -Seconds 2
$chatBody1 = '{"text":"Hello, introduce yourself in one sentence","deep_reasoning":false}'
Test-Endpoint "A4.1 Chat V3" "POST" "/api/chat" $chatBody1
Start-Sleep -Seconds 3
$chatBody2 = '{"text":"What is 1+1? Answer in one sentence","deep_reasoning":true}'
Test-Endpoint "A4.2 Chat R1" "POST" "/api/chat" $chatBody2

Write-Host "========== A5: PILOT =========="
Test-Endpoint "A5.1 Pilot Stop" "POST" "/api/pilot/stop" "{}"
Start-Sleep -Seconds 1
Test-Endpoint "A5.2 Pilot Status" "GET" "/api/pilot/status" $null
Test-Endpoint "A5.3 Pilot Signals" "GET" "/api/pilot/signals" $null
Test-Endpoint "A5.4 Pilot Start" "GET" "/api/pilot/start" $null
Test-Endpoint "A5.5 Pilot Config" "POST" "/api/pilot/config" '{"mode":"auto"}'

Write-Host "========== A6: MARKET =========="
Test-Endpoint "A6.1 Market Indices" "GET" "/api/market" $null
Test-Endpoint "A6.2 Stock Quote" "GET" "/api/market/stock/000001" $null
Test-Endpoint "A6.3 Stock History" "GET" "/api/market/stock/000001/history" $null
Test-Endpoint "A6.4 Stock Alt" "GET" "/api/stock/000001" $null
Test-Endpoint "A6.5 Market Recap" "GET" "/api/market/recap" $null

Write-Host "========== A7: ACCOUNT =========="
Test-Endpoint "A7.1 Account Info" "GET" "/api/account" $null
Test-Endpoint "A7.2 Trades" "GET" "/api/account/trades" $null
Test-Endpoint "A7.3 Positions" "GET" "/api/account/positions" $null
Test-Endpoint "A7.4 Token Balance" "GET" "/api/token/balance" $null

Write-Host "========== A8: HACKER =========="
Test-Endpoint "A8.1 Removed Capabilities" "GET" "/api/hacker/capabilities" $null
$hBody1 = '{"id":"system_status","action":"运行"}'
Test-Endpoint "A8.2 Removed Exec system_status" "POST" "/api/hacker/exec" $hBody1

Write-Host "========== A9: DESKTOP =========="
Test-Endpoint "A9.1 Snapshot" "GET" "/api/desktop/snapshot" $null
Test-Endpoint "A9.2 URL Scheme" "GET" "/api/url_scheme" $null
Test-Endpoint "A9.3 Capabilities" "GET" "/api/desktop/capabilities" $null
$deskBody = '{"id":"system_status","action":"运行"}'
$r = Test-Endpoint "A9.4 Exec system_status" "POST" "/api/desktop/exec" $deskBody
Assert-JsonOk $r "A9.4 Exec system_status" | Out-Null

Write-Host "========== A10: MCP =========="
Test-Endpoint "A10.1 MCP Servers" "GET" "/api/mcp/servers" $null

Write-Host "========== A11: PAYMENT =========="
Test-Endpoint "A11.1 Payment Removed Status" "GET" "/api/payment/status" $null
$linkBody = '{"amount":1,"currency":"USD","first_name":"Audit","email":"audit@test.com"}'
Test-Endpoint "A11.2 Payment Removed Link" "POST" "/api/payment/link" $linkBody
Test-Endpoint "A11.3 Payment Removed Orders" "GET" "/api/payment/orders" $null

Write-Host "========== A12: MIRROR SPACE =========="
Test-Endpoint "A12.1 Mirror Status" "GET" "/api/mirror/status" $null
Test-Endpoint "A12.2 Mirror Skills" "GET" "/api/mirror/skills" $null
$invokeBody = '{"skill":"validate","params":{}}'
Test-Endpoint "A12.3 Mirror Invoke" "POST" "/api/mirror/invoke" $invokeBody

Write-Host "========== A13: PANEL =========="
Test-Endpoint "A13.1 Panel Status" "GET" "/api/panel/status" $null
Test-Endpoint "A13.2 Rollback" "POST" "/api/panel/rollback" '{}'

Write-Host "========== A14: OAUTH =========="
Test-Endpoint "A14.1 OAuth Providers" "GET" "/api/auth/oauth/providers" $null
# Auth profile uses X-Auth-Token header, already set above
Test-Endpoint "A14.2 Auth Profile" "GET" "/api/auth/profile?token=$AUTH_TOKEN" $null

Write-Host "========== EXTRA: CONNECTORS =========="
Test-Endpoint "EX.1 Providers" "GET" "/api/providers" $null
Test-Endpoint "EX.2 Connectors" "GET" "/api/connectors" $null
Test-Endpoint "EX.3 Strategies" "GET" "/api/strategies" $null
Test-Endpoint "EX.4 Audit" "GET" "/api/audit" $null
Test-Endpoint "EX.5 Access Log" "GET" "/api/access_log" $null
Test-Endpoint "EX.6 Devices" "GET" "/api/devices" $null
Test-Endpoint "EX.7 Watcher Status" "GET" "/api/watcher/status" $null

Write-Host "========== FINAL: Token =========="
Test-Endpoint "Final Balance" "GET" "/api/token/balance" $null

Write-Host ""
Write-Host "========================================"
Write-Host "RESULTS: $PASS_COUNT PASS, $FAIL_COUNT FAIL"
if ($FAIL_COUNT -gt 0) {
    Write-Host "FAILURES:" -ForegroundColor Red
    $FAILS | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
    exit 1
} else {
    Write-Host "ALL TESTS PASSED" -ForegroundColor Green
    exit 0
}
