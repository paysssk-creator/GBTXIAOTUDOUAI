$env:PYTHONIOENCODING='utf-8'
Set-Location -LiteralPath $PSScriptRoot
& '.\.venv\Scripts\python.exe' '.\data\finalize_blueprints.py' 2>&1