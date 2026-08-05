param(
  [string]$Output = "data/index-performance.json"
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $RepoRoot

python scripts/refresh_market_indices.py --output $Output
if ($LASTEXITCODE -ne 0) {
  throw "refresh_market_indices.py failed with exit code $LASTEXITCODE"
}
