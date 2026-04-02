$ErrorActionPreference = "Stop"

$dockerBin = "C:\Program Files\Docker\Docker\resources\bin"
$dockerExe = Join-Path $dockerBin "docker.exe"
$credentialHelper = Join-Path $dockerBin "docker-credential-desktop.exe"

if (-not (Test-Path $dockerExe)) {
    throw "Docker executable not found at '$dockerExe'."
}

if (-not (Test-Path $credentialHelper)) {
    throw "Docker credential helper not found at '$credentialHelper'."
}

if (-not (($env:PATH -split ';') -contains $dockerBin)) {
    $env:PATH = "$dockerBin;$env:PATH"
}

& $dockerExe compose @args
exit $LASTEXITCODE
