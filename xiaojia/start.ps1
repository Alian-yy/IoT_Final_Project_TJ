# Xiaojia IoT Publisher - Unified Startup Script
# Encoding: UTF-8

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Xiaojia IoT - Publisher System      " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Get script directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

# ========== 1. Check Frontend Dependencies ==========
Write-Host "[1/4] Checking frontend dependencies..." -ForegroundColor Yellow
if (-Not (Test-Path "node_modules")) {
    Write-Host "      Installing frontend dependencies..." -ForegroundColor Yellow
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "X Frontend dependency installation failed!" -ForegroundColor Red
        exit 1
    }
    Write-Host "OK Frontend dependencies installed" -ForegroundColor Green
} else {
    Write-Host "OK Frontend dependencies ready" -ForegroundColor Green
}

# ========== 2. Check Backend Dependencies ==========
Write-Host ""
Write-Host "[2/4] Checking backend dependencies..." -ForegroundColor Yellow

# Activate conda environment
$condaEnv = "xiaojia-iot"
Write-Host "      Activating conda env: $condaEnv" -ForegroundColor Gray

# Check Python packages
$checkPython = conda run -n $condaEnv python -c "import fastapi, uvicorn, paho.mqtt.client" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "      Installing backend dependencies..." -ForegroundColor Yellow
    conda run -n $condaEnv pip install -r backend/requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "X Backend dependency installation failed!" -ForegroundColor Red
        exit 1
    }
    Write-Host "OK Backend dependencies installed" -ForegroundColor Green
} else {
    Write-Host "OK Backend dependencies ready" -ForegroundColor Green
}

# ========== 3. Start Backend Service ==========
Write-Host ""
Write-Host "[3/4] Starting backend service..." -ForegroundColor Yellow
Write-Host ""

# Start FastAPI in separate window
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptPath\backend'; conda activate $condaEnv; python main.py" -WindowStyle Normal

Write-Host "OK Backend service starting (http://localhost:8001)" -ForegroundColor Green
Write-Host "   Waiting for backend to be ready..." -ForegroundColor Gray

# Wait for backend to start
$maxRetries = 15
$retryCount = 0
$backendReady = $false

while ($retryCount -lt $maxRetries) {
    Start-Sleep -Seconds 1
    try {
        # Use .NET WebClient for better compatibility
        $webClient = New-Object System.Net.WebClient
        $response = $webClient.DownloadString("http://localhost:8001/")
        if ($response -like "*status*") {
            $backendReady = $true
            break
        }
    } catch {
        $retryCount++
        Write-Host "   ." -NoNewline -ForegroundColor Gray
    }
}

Write-Host ""
if ($backendReady) {
    Write-Host "OK Backend service ready" -ForegroundColor Green
} else {
    Write-Host "! Backend startup timeout, but continuing with frontend" -ForegroundColor Yellow
}

# ========== 4. Start Frontend Service ==========
Write-Host ""
Write-Host "[4/4] Starting frontend service..." -ForegroundColor Yellow
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Service URLs:" -ForegroundColor Cyan
Write-Host "  Frontend: http://localhost:5173" -ForegroundColor Green
Write-Host "  Backend:  http://localhost:8001" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop frontend service" -ForegroundColor Gray
Write-Host "Backend runs in separate window - close manually" -ForegroundColor Gray
Write-Host ""

npm run dev
