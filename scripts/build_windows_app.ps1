$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

python -m pip install -r requirements.txt
python -m pip install -r requirements-build.txt

if (Test-Path build) { Remove-Item build -Recurse -Force }
if (Test-Path dist) { Remove-Item dist -Recurse -Force }

python -m PyInstaller --clean packaging/BeeHQ-windows.spec

Write-Host ""
Write-Host "Built Windows app folder:"
Write-Host "  $Root\dist\BeeHQ"
