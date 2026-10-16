function Test-PublishPython {
  param([string]$Candidate)

  if (-not $Candidate -or -not (Test-Path -LiteralPath $Candidate -PathType Leaf)) { return $null }
  # Windows execution aliases can open the Store or return 9009 in scheduled tasks.
  if ($Candidate -match '[\\/]Microsoft[\\/]WindowsApps[\\/]') { return $null }

  $process = New-Object System.Diagnostics.Process
  $process.StartInfo.FileName = $Candidate
  $process.StartInfo.Arguments = '-c "import sys; print(sys.executable); print(sys.version_info.major); print(sys.version_info.minor)"'
  $process.StartInfo.UseShellExecute = $false
  $process.StartInfo.CreateNoWindow = $true
  $process.StartInfo.RedirectStandardOutput = $true
  $process.StartInfo.RedirectStandardError = $true
  try {
    [void]$process.Start()
    if (-not $process.WaitForExit(5000)) {
      $process.Kill()
      return $null
    }
    $lines = @($process.StandardOutput.ReadToEnd().Trim() -split '\r?\n')
    if ($process.ExitCode -ne 0 -or $lines.Count -ne 3) { return $null }
    if ([int]$lines[1] -ne 3 -or [int]$lines[2] -lt 10) { return $null }
    if (-not (Test-Path -LiteralPath $lines[0] -PathType Leaf)) { return $null }
    return $lines[0]
  } catch {
    return $null
  } finally {
    $process.Dispose()
  }
}

function Resolve-PublishPython {
  param(
    [string]$RepoRoot,
    [string]$Preferred = $env:QUANT_LAB_PYTHON
  )

  if ($Preferred) {
    $resolved = Test-PublishPython -Candidate $Preferred
    if (-not $resolved) { throw 'QUANT_LAB_PYTHON must point to a working Python 3.10+ executable.' }
    return $resolved
  }

  $candidates = @()
  foreach ($prefix in @($env:VIRTUAL_ENV, $env:CONDA_PREFIX)) {
    if ($prefix) {
      $candidates += Join-Path $prefix 'Scripts\python.exe'
      $candidates += Join-Path $prefix 'python.exe'
    }
  }
  if ($RepoRoot) { $candidates += Join-Path $RepoRoot '.venv\Scripts\python.exe' }
  if ($env:USERPROFILE) {
    $candidates += Join-Path $env:USERPROFILE 'anaconda3\python.exe'
    $candidates += Join-Path $env:USERPROFILE 'miniconda3\python.exe'
  }
  foreach ($name in @('python.exe', 'python3.exe', 'py.exe')) {
    foreach ($command in @(Get-Command $name -CommandType Application -All -ErrorAction SilentlyContinue)) {
      $candidates += $command.Source
    }
  }

  $seen = New-Object 'System.Collections.Generic.HashSet[string]'
  foreach ($candidate in $candidates) {
    if (-not $seen.Add($candidate)) { continue }
    $resolved = Test-PublishPython -Candidate $candidate
    if ($resolved) { return $resolved }
  }
  throw 'No working Python 3.10+ found for publishing. Set QUANT_LAB_PYTHON to an installed interpreter.'
}
