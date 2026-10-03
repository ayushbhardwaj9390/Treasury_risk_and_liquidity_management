param([string]$NodePath)
$ErrorActionPreference = 'Stop'
$previewRoot = Split-Path -Parent $PSScriptRoot
$previewPython = Join-Path $previewRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $previewPython)) { throw 'Install backend dependencies in .venv first.' }
if (-not $NodePath) {
    $previewNode = Get-Command node -ErrorAction SilentlyContinue
    if ($previewNode) { $NodePath = $previewNode.Source }
    else { throw 'Node.js must be on PATH, or pass -NodePath with its full path.' }
}
if (-not (Test-Path -LiteralPath (Join-Path $previewRoot 'frontend\.next\BUILD_ID'))) {
    throw 'Build the frontend first: run pnpm build in frontend.'
}
foreach ($previewPort in @(3000, 8000)) {
    $portCheck = [System.Net.Sockets.TcpClient]::new()
    try {
        $pendingConnection = $portCheck.ConnectAsync('127.0.0.1', $previewPort)
        if ($pendingConnection.Wait(1000) -and $portCheck.Connected) {
            throw "Port $previewPort is already used. Stop the existing preview before starting another."
        }
    } catch [System.AggregateException] { } finally { $portCheck.Dispose() }
}
$previousDatabase = $env:DATABASE_URL
$previousEnvironment = $env:ENVIRONMENT
$previousAuth = $env:AUTH_MODE
$previousApi = $env:API_BASE_URL
try {
    $env:DATABASE_URL = 'sqlite:///./application-preview.db'
    $env:ENVIRONMENT = 'development'
    $env:AUTH_MODE = 'demo_header'
    $env:API_BASE_URL = 'http://127.0.0.1:8000'
    $previewBackend = Start-Process -FilePath $previewPython -ArgumentList @('-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000') -WorkingDirectory (Join-Path $previewRoot 'backend') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $previewRoot 'backend\preview-output.txt') -RedirectStandardError (Join-Path $previewRoot 'backend\preview-error-output.txt') -PassThru
    try {
        $previewFrontend = Start-Process -FilePath $NodePath -ArgumentList @('node_modules/next/dist/bin/next', 'start', '--hostname', '127.0.0.1', '--port', '3000') -WorkingDirectory (Join-Path $previewRoot 'frontend') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $previewRoot 'frontend\preview-output.txt') -RedirectStandardError (Join-Path $previewRoot 'frontend\preview-error-output.txt') -PassThru
    } catch { Stop-Process -Id $previewBackend.Id; throw }
    Write-Output "Preview: http://127.0.0.1:3000 (frontend PID $($previewFrontend.Id), backend launcher PID $($previewBackend.Id))"
    Write-Output 'Synthetic local demonstration only. Startup errors appear in the preview-error-output.txt files.'
} finally {
    $env:DATABASE_URL = $previousDatabase
    $env:ENVIRONMENT = $previousEnvironment
    $env:AUTH_MODE = $previousAuth
    $env:API_BASE_URL = $previousApi
}
