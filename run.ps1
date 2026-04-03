# Shopping Copilot - Run Script
# Usage: .\run.ps1

$backendDir = "$PSScriptRoot\backend"

if (-not (Test-Path "$backendDir\.env")) {
    Write-Host "❌ backend\.env not found. Run .\setup.ps1 first." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path "$PSScriptRoot\frontend\dist")) {
    Write-Host "❌ Frontend not built. Run .\setup.ps1 first." -ForegroundColor Red
    exit 1
}

Write-Host "`n🚀 Starting Shopping Copilot at http://localhost:8000`n" -ForegroundColor Green

Set-Location $backendDir
uvicorn main:app --host 0.0.0.0 --port 8000
