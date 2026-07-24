# GBT Pro v2.2 一键部署脚本
# 用法: iwr '短URL' | iex  或直接运行此脚本

$ErrorActionPreference = 'Stop'
Write-Host "GBT Pro v2.2 部署中..." -ForegroundColor Cyan

$base = 'https://raw.githubusercontent.com/paysssk-creator/GBTXIAOTUDOUAI/main'
$dirs = @(
    "$PWD\gbt",
    "$PWD\GBTXIAOTUDOUAI\gbt"
)

# 确保目录
foreach ($d in $dirs) {
    New-Item -ItemType Directory -Force -Path $d | Out-Null
    Set-Location $d
    Write-Host " 下载到: $d"
    
    # 下载文件
    $files = @(
        @{Url="$base/gbt/browser_trader.py"; Name="browser_trader.py"},
        @{Url="$base/gbt/browser_desk.py"; Name="browser_desk.py"}
    )
    
    foreach ($f in $files) {
        Write-Host "   $($f.Name)..."
        Invoke-WebRequest -Uri $f.Url -OutFile $f.Name -UseBasicParsing
        $size = (Get-Item $f.Name).Length
        Write-Host "   $($f.Name) OK ($size bytes)" -ForegroundColor Green
    }
    
    Set-Location $PWD\..
}

# launch_trader.bat 放根目录
Set-Location (Get-Location).Path -ErrorAction SilentlyContinue
Invoke-WebRequest -Uri "$base/launch_trader.bat" -OutFile "launch_trader.bat" -UseBasicParsing

Write-Host "部署完成!" -ForegroundColor Green
dir gbt\ -ErrorAction SilentlyContinue
