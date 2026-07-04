$env:PYTHONIOENCODING='utf-8'
$env:PYTHONUTF8='1'
Set-Location -LiteralPath $PSScriptRoot
& '.\.venv\Scripts\python.exe' '.\data\split_routes.py' 2>&1 | Out-File -FilePath '.\data\preview\T-002\split-output.log' -Encoding utf8
Get-Content '.\data\preview\T-002\split-output.log'