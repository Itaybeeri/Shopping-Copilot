# Shopping Copilot - Setup Script
# Run once before first use: .\setup.ps1

$errors = @()

Write-Host "`n🔍 Checking prerequisites..." -ForegroundColor Cyan

# --- Node.js ---
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    $errors += "Node.js is not installed. Download from https://nodejs.org (v18+)"
} else {
    $nodeVersion = (node --version) -replace 'v', ''
    $nodeMajor = [int]($nodeVersion.Split('.')[0])
    if ($nodeMajor -lt 18) {
        $errors += "Node.js v$nodeVersion is too old. Version 18+ required. Download from https://nodejs.org"
    } else {
        Write-Host "  ✅ Node.js v$nodeVersion" -ForegroundColor Green
    }
}

# --- npm ---
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    $errors += "npm is not installed. It comes with Node.js — reinstall from https://nodejs.org"
} else {
    Write-Host "  ✅ npm $(npm --version)" -ForegroundColor Green
}

# --- Python ---
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    $errors += "Python is not installed. Download from https://python.org (v3.9+)"
} else {
    $pythonVersion = (python --version) -replace 'Python ', ''
    $parts = $pythonVersion.Split('.')
    $major = [int]$parts[0]
    $minor = [int]$parts[1]
    if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 9)) {
        $errors += "Python v$pythonVersion is too old. Version 3.9+ required. Download from https://python.org"
    } else {
        Write-Host "  ✅ Python v$pythonVersion" -ForegroundColor Green
    }
}

# --- pip ---
if (-not (Get-Command pip -ErrorAction SilentlyContinue)) {
    $errors += "pip is not installed. Run: python -m ensurepip"
} else {
    Write-Host "  ✅ pip $(pip --version | Select-String -Pattern '[\d.]+' | ForEach-Object { $_.Matches[0].Value })" -ForegroundColor Green
}

# --- .env file ---
if (-not (Test-Path "$PSScriptRoot\backend\.env")) {
    $errors += ".env file missing in backend/. Copy backend\.env.example to backend\.env and set your OPENAI_API_KEY"
} else {
    $envContent = Get-Content "$PSScriptRoot\backend\.env" -Raw
    if ($envContent -notmatch 'OPENAI_API_KEY=.+' -or $envContent -match 'OPENAI_API_KEY=your_openai_api_key_here') {
        $errors += "OPENAI_API_KEY is not set in backend\.env"
    } else {
        Write-Host "  ✅ .env file found" -ForegroundColor Green
    }
}

# --- Abort if errors ---
if ($errors.Count -gt 0) {
    Write-Host "`n❌ Setup failed. Fix the following issues before continuing:`n" -ForegroundColor Red
    $errors | ForEach-Object { Write-Host "  • $_" -ForegroundColor Yellow }
    Write-Host ""
    exit 1
}

Write-Host "`n📦 Installing Python dependencies..." -ForegroundColor Cyan
pip install -r "$PSScriptRoot\backend\requirements.txt"
if ($LASTEXITCODE -ne 0) { Write-Host "❌ pip install failed" -ForegroundColor Red; exit 1 }

Write-Host "`n📦 Installing frontend dependencies..." -ForegroundColor Cyan
Set-Location "$PSScriptRoot\frontend"
npm install
if ($LASTEXITCODE -ne 0) { Write-Host "❌ npm install failed" -ForegroundColor Red; exit 1 }

Write-Host "`n🏗️  Building frontend..." -ForegroundColor Cyan
npm run build
if ($LASTEXITCODE -ne 0) { Write-Host "❌ npm build failed" -ForegroundColor Red; exit 1 }

Set-Location $PSScriptRoot

Write-Host "`n✅ Setup complete! Run the app with: .\run.ps1`n" -ForegroundColor Green
