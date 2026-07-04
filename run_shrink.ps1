$env:PYTHONIOENCODING='utf-8'
Set-Location -LiteralPath $PSScriptRoot
& '.\.venv\Scripts\python.exe' '.\data\shrink_desktop_app.py' 2>&1