$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$scriptPath = Join-Path $PSScriptRoot "validate_env.py"

if (-not (Test-Path $scriptPath)) {
  Write-Error "validate_env.py not found: $scriptPath"
  exit 2
}

Write-Host "Running environment validation..."
python "$scriptPath"
exit $LASTEXITCODE
