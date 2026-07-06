$ErrorActionPreference = "Continue"
Add-Type -AssemblyName System.Net.Http
$cli = New-Object System.Net.Http.HttpClient
$cli.Timeout = [TimeSpan]::FromSeconds(60)
$BASE = "http://127.0.0.1:8765"
$ISSUES = New-Object System.Collections.ArrayList

function DeepCheck($label, $method, $path, $body, $checks) {
    try {
        if ($method -eq "GET") {
            $resp = $cli.GetAsync("$BASE$path").Result
        } else {
            $content = New-Object System.Net.Http.StringContent($body, [System.Text.Encoding]::UTF8, "application/json")
            $resp = $cli.PostAsync("$BASE$path", $content).Result
        }
        $txt = $resp.Content.ReadAsStringAsync().Result
        $code = [int]$resp.StatusCode
        if ($code -lt 200 -or $code -ge 300) {
            Write-Host "[DEEP-FAIL] ${label} HTTP ${code}" -ForegroundColor Red
            [void]$ISSUES.Add("${label}: HTTP ${code}")
            return
        }
        try { $j = $txt | ConvertFrom-Json } catch { Write-Host "[DEEP-FAIL] ${label} not JSON" -ForegroundColor Red; [void]$ISSUES.Add("${label}: not JSON"); return }
        foreach ($ck in $checks) {
            try {
                $val = Invoke-Expression "`$j.$ck"
                if ($null -eq $val -or "" -eq $val) {
                    Write-Host "[DEEP-WARN] ${label} .${ck} is null/empty" -ForegroundColor Yellow
                    [void]$ISSUES.Add("${label}: .${ck} is null")
                } else {
                    $sval = if ($val -is [string] -and $val.Length -gt 80) { $val.Substring(0,80) + "..." } else { "$val" }
                    Write-Host "[DEEP-OK] ${label} .${ck} = ${sval}" -ForegroundColor Cyan
                }
            } catch {
                Write-Host "[DEEP-WARN] ${label} .${ck} missing" -ForegroundColor Yellow
                [void]$ISSUES.Add("${label}: .${ck} missing")
            }
        }
    } catch {
        Write-Host "[DEEP-CRASH] ${label} : $_" -ForegroundColor Red
        [void]$ISSUES.Add("${label}: CRASH")
    }
}

Write-Host "===== DEEP CONTENT VERIFICATION ====="

# Login first
$ts = Get-Date -Format "yyyyMMddHHmmss"
$USER = "deep_$ts"
$PASS = "Audit!2026"
$regBody = '{"username":"' + $USER + '","password":"' + $PASS + '","email":"' + $USER + '@test.com"}'
try {
    $c = New-Object System.Net.Http.StringContent($regBody, [System.Text.Encoding]::UTF8, "application/json")
    $cli.PostAsync("$BASE/api/auth/register", $c).Result | Out-Null
} catch {}
$loginBody = '{"username":"' + $USER + '","password":"' + $PASS + '"}'
$c2 = New-Object System.Net.Http.StringContent($loginBody, [System.Text.Encoding]::UTF8, "application/json")
$resp = $cli.PostAsync("$BASE/api/auth/login", $c2).Result
$txt = $resp.Content.ReadAsStringAsync().Result
$TOKEN = ""
try { $j = $txt | ConvertFrom-Json; $TOKEN = $j.token } catch {}
if ($TOKEN) {
    $cli.DefaultRequestHeaders.Authorization = New-Object System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", $TOKEN)
    $cli.DefaultRequestHeaders.Add("X-Auth-Token", $TOKEN)
    Write-Host "Logged in as $USER"
} else { Write-Host "Login failed" -ForegroundColor Red }

# Recharge
$rBody = '{"code":"GBT-DEMO-5K"}'
$c3 = New-Object System.Net.Http.StringContent($rBody, [System.Text.Encoding]::UTF8, "application/json")
$cli.PostAsync("$BASE/api/token/recharge", $c3).Result | Out-Null

# 1. Status
DeepCheck "Status" "GET" "/api/status" $null @("ok", "version", "app")

# 2. System
DeepCheck "System" "GET" "/api/system" $null @("ok", "cpu_percent", "memory_percent", "disk_percent")

# 3. Dashboard
DeepCheck "Dashboard" "GET" "/api/dashboard" $null @("ok", "llm_status")

# 4. Market indices
DeepCheck "Market" "GET" "/api/market" $null @("ok", "indices")

# 5. Stock quote
DeepCheck "Stock_000001" "GET" "/api/market/stock/000001" $null @("ok", "code", "name")

# 6. Stock history
DeepCheck "History" "GET" "/api/market/stock/000001/history" $null @("ok", "code")

# 7. Recap
DeepCheck "Recap" "GET" "/api/market/recap" $null @("ok")

# 8. Account
DeepCheck "Account" "GET" "/api/account" $null @("ok")

# 9. Mirror status
DeepCheck "Mirror" "GET" "/api/mirror/status" $null @("ok")

# 10. Mirror skills
DeepCheck "Skills" "GET" "/api/mirror/skills" $null @("ok", "list")

# 11. Payment status
DeepCheck "PayStatus" "GET" "/api/payment/status" $null @("ok", "configured")

# 12. OAuth providers
DeepCheck "OAuth" "GET" "/api/auth/oauth/providers" $null @("ok", "providers")

# 13. Chat V3 with Chinese text - ENCODING TEST
Write-Host "--- ENCODING TEST: Chinese Chat ---"
$cnBody = '{"text":"你好","deep_reasoning":false}'
try {
    $content = New-Object System.Net.Http.StringContent($cnBody, [System.Text.Encoding]::UTF8, "application/json")
    $resp2 = $cli.PostAsync("$BASE/api/chat", $content).Result
    $code2 = [int]$resp2.StatusCode
    $txt2 = $resp2.Content.ReadAsStringAsync().Result
    if ($code2 -eq 200) {
        Write-Host "[ENCODING-OK] Chinese chat returned 200" -ForegroundColor Green
    } elseif ($code2 -eq 402) {
        Write-Host "[ENCODING-OK] Chinese chat returned 402 (parser works)" -ForegroundColor Green
    } else {
        Write-Host "[ENCODING-FAIL] Chinese chat returned ${code2}: $txt2" -ForegroundColor Red
        [void]$ISSUES.Add("Chinese encoding: HTTP ${code2}")
    }
} catch {
    Write-Host "[ENCODING-CRASH] $_" -ForegroundColor Red
}

# 14. Mirror invoke with validate
DeepCheck "MirrorInvoke" "POST" "/api/mirror/invoke" '{"skill":"validate","params":{}}' @("ok")

Write-Host ""
Write-Host "===== ISSUES FOUND: $($ISSUES.Count) ====="
if ($ISSUES.Count -gt 0) {
    $ISSUES | ForEach-Object { Write-Host "  $_" -ForegroundColor Yellow }
    exit 1
} else {
    Write-Host "ALL DEEP CHECKS CLEAN" -ForegroundColor Green
    exit 0
}
