$ErrorActionPreference = "Stop"

$composeScript = Join-Path $PSScriptRoot "docker-compose.ps1"
$dockerBin = "C:\Program Files\Docker\Docker\resources\bin"
$dockerExe = Join-Path $dockerBin "docker.exe"
$repoRoot = Split-Path -Parent $PSScriptRoot
$backendTestsPath = Join-Path $repoRoot "backend\tests"

& $composeScript up -d --build backend
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if (-not (Test-Path $backendTestsPath)) {
    throw "Backend tests directory not found at '$backendTestsPath'."
}

& $dockerExe cp $backendTestsPath meta-ads-audit-backend-1:/app/tests
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

& $composeScript exec backend sh -lc "cd /app && PYTHONPATH=/app pytest tests/test_ai_summary.py"
exit $LASTEXITCODE
