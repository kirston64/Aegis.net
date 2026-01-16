# Aegis.net Demo Launcher

$CurrentDir = $PSScriptRoot
Write-Host "Wrapper running in: $CurrentDir"

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "🛡️  STARTING AEGIS LIVE DEMO" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan

# 1. Start Origin Website (Port 9000)
Write-Host "[1/3] Starting Origin Website..."
Start-Process powershell -WorkingDirectory $CurrentDir -ArgumentList "-NoExit", "-Command", "python run_origin.py"
Start-Sleep -Seconds 2

# 2. Start Mock Edge Node (Port 8080)
Write-Host "[2/3] Starting Edge Simulator..."
Start-Process powershell -WorkingDirectory $CurrentDir -ArgumentList "-NoExit", "-Command", "python mock_edge_node.py"
Start-Sleep -Seconds 2

# 3. Start Dashboard (npm run dev -> Port 5173)
Write-Host "[3/4] Starting Dashboard..."
if (Test-Path "$CurrentDir\dashboard\node_modules") {
    Start-Process powershell -WorkingDirectory "$CurrentDir\dashboard" -ArgumentList "-NoExit", "-Command", "npm run dev"
    Start-Sleep -Seconds 4
} else {
    Write-Warning "Dashboard dependencies not installed. Skipping Dashboard launch."
    Write-Warning "Run 'cd dashboard; npm install' to fix."
}

# 4. Open Browser Windows
Write-Host "[4/4] Opening Browsers..."
Start-Process "http://localhost:8080"      # The Protected Site (Edge)
Start-Process "http://localhost:5173"      # The Admin Dashboard

Write-Host "`n✅ SYSTEM ONLINE!" -ForegroundColor Green
Write-Host "1. Website:   http://localhost:8080 (Target)"
Write-Host "2. Dashboard: http://localhost:5173 (Control)"
Write-Host "3. Attack:    Run 'python control-plane/stress_test.py' here" -ForegroundColor Yellow
