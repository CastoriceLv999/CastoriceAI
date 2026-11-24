$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$backendRoot = Join-Path $projectRoot 'castorice_backend'
$frontendRoot = Join-Path $projectRoot 'castorice_vue'
$logRoot = Join-Path $projectRoot '.dev-logs'
New-Item -ItemType Directory -Path $logRoot -Force | Out-Null

function Test-Backend {
    try {
        $health = Invoke-RestMethod 'http://127.0.0.1:8000/' -TimeoutSec 2
        return $health.status -eq 'running'
    } catch { return $false }
}

function Test-Frontend {
    try {
        $page = Invoke-WebRequest 'http://127.0.0.1:5173/' -TimeoutSec 2 -UseBasicParsing
        return $page.Content -match '@vite/client'
    } catch { return $false }
}

$backendProcess = $null
$frontendProcess = $null
if (-not (Test-Backend)) {
    $pythonPath = $null
    foreach ($environment in @('.venv', '.check-venv')) {
        $candidate = Join-Path $projectRoot "$environment\Scripts\python.exe"
        if (Test-Path -LiteralPath $candidate) { $pythonPath = $candidate; break }
    }
    if (-not $pythonPath) {
        throw 'Create a Python environment and install castorice_backend/requirements.txt first. See README.md.'
    }
    $backendProcess = Start-Process -FilePath $pythonPath `
        -ArgumentList @('-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', '8000') `
        -WorkingDirectory $backendRoot -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $logRoot 'backend.out.log') `
        -RedirectStandardError (Join-Path $logRoot 'backend.err.log')
}

if (-not (Test-Frontend)) {
    $vitePath = Join-Path $frontendRoot 'node_modules\vite\bin\vite.js'
    if (-not (Test-Path -LiteralPath $vitePath)) { throw 'Run npm ci in castorice_vue first.' }
    $nodePath = (Get-Command node.exe -ErrorAction Stop).Source
    $frontendProcess = Start-Process -FilePath $nodePath `
        -ArgumentList @(('"{0}"' -f $vitePath), '--host', '127.0.0.1', '--port', '5173', '--strictPort') `
        -WorkingDirectory $frontendRoot -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $logRoot 'frontend.out.log') `
        -RedirectStandardError (Join-Path $logRoot 'frontend.err.log')
}

for ($attempt = 0; $attempt -lt 30; $attempt++) {
    if ((Test-Backend) -and (Test-Frontend)) {
        Write-Host 'Frontend and backend are ready: http://127.0.0.1:5173/'
        Write-Host "Logs: $logRoot"
        return
    }
    if (($backendProcess -and $backendProcess.HasExited) -or ($frontendProcess -and $frontendProcess.HasExited)) { break }
    Start-Sleep -Milliseconds 500
}
throw "Services did not start successfully. Check $logRoot\backend.err.log and frontend.err.log."
