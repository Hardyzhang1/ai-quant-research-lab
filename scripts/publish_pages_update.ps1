param(
  [string]$NewsHtml = $env:NEWS_AGENT_PUBLIC_SOURCE,
  [string]$NewsHtmls = $env:NEWS_AGENT_PUBLIC_SOURCES,
  [string]$TradingHtml = $env:TRADING_AGENT_PUBLIC_SOURCE,
  [string]$TradingCloseHtml = $env:TRADING_AGENT_CLOSE_SOURCE,
  [string]$AShareTradingHtml = $env:ASHARE_TRADING_AGENT_PUBLIC_SOURCE,
  [string]$AShareTradingCloseHtml = $env:ASHARE_TRADING_AGENT_CLOSE_SOURCE,
  [switch]$Commit,
  [switch]$Push
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $RepoRoot

$PublishVersion = Get-Date -Format "yyyyMMddHHmmss"
$PublishedAt = Get-Date -Format "yyyy-MM-ddTHH:mm:ssK"

function Latest-File {
  param(
    [string]$Dir,
    [string]$Pattern
  )
  if (-not (Test-Path -LiteralPath $Dir)) {
    return $null
  }
  return Get-ChildItem -LiteralPath $Dir -Filter $Pattern -File -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
}

function Newest-Existing {
  param([object[]]$Paths)
  $existing = @()
  foreach ($path in $Paths) {
    if ($null -eq $path) {
      continue
    }
    $literal = if ($path -is [System.IO.FileInfo]) { $path.FullName } else { [string]$path }
    if ($literal -and (Test-Path -LiteralPath $literal)) {
      $existing += Get-Item -LiteralPath $literal
    }
  }
  if (-not $existing.Count) {
    return $null
  }
  return ($existing | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
}

function Sync-RemotePreview {
  param(
    [string]$Remote,
    [string]$RemotePath,
    [string]$LocalPath
  )
  $localSource = $RemotePath -replace "/", "\"
  if (Test-Path -LiteralPath $localSource) {
    Copy-Item -LiteralPath $localSource -Destination $LocalPath -Force
    return
  }
  try {
    scp "${Remote}:$RemotePath" $LocalPath *> $null
  } catch {
    # Best effort: publishing should still use the newest cached local preview.
  }
}

function First-ExistingDir {
  param([string[]]$Dirs)
  foreach ($dir in $Dirs) {
    if ($dir -and (Test-Path -LiteralPath $dir)) {
      return $dir
    }
  }
  return $Dirs[0]
}

$PrivatePreviewDir = Join-Path $RepoRoot "tmp\private-previews"
New-Item -ItemType Directory -Force -Path $PrivatePreviewDir | Out-Null

$Remote = "74594@100.83.100.43"
$RemotePreviews = @{
  "preview_a_premarket_latest.html" = "D:/Codex/work/market-news-agent/preview_a_premarket.html"
  "preview_us_premarket_latest.html" = "D:/Codex/work/market-news-agent/preview_us_premarket.html"
  "preview_a_close_latest.html" = "D:/Codex/work/market-news-agent/preview_a_close.html"
  "preview_us_close_latest.html" = "D:/Codex/work/market-news-agent/preview_us_close.html"
  "preview_ashare_close_latest.html" = "D:/Codex/work/ashare-rq-agent/preview_ashare_close.html"
  "preview_technical_us_validation_latest.html" = "D:/Codex/work/technical-analysis-agent/preview_technical_us_validation.html"
}
foreach ($entry in $RemotePreviews.GetEnumerator()) {
  Sync-RemotePreview -Remote $Remote -RemotePath $entry.Value -LocalPath (Join-Path $PrivatePreviewDir $entry.Key)
}

$NewsAgentOutput = First-ExistingDir @(
  "D:\Codex\work\market-news-agent",
  "C:\Users\HONOR\Documents\Codex\2026-06-21\qin\outputs\market-news-agent"
)
$AShareTradingAgentOutput = First-ExistingDir @(
  "D:\Codex\work\ashare-rq-agent",
  "C:\Users\HONOR\Documents\Codex\2026-06-21\qin\outputs\ashare-rq-agent"
)
$USTradingAgentOutput = First-ExistingDir @(
  "D:\Codex\work\technical-analysis-agent",
  "C:\Users\HONOR\Documents\Codex\2026-06-21\qin\outputs\technical-analysis-agent"
)

if (-not $NewsHtmls -and -not $NewsHtml) {
  $newsSources = @(
    Newest-Existing @((Join-Path $PrivatePreviewDir "preview_us_premarket_latest.html"), (Join-Path $NewsAgentOutput "preview_us_premarket.html"))
    Newest-Existing @((Join-Path $PrivatePreviewDir "preview_a_premarket_latest.html"), (Join-Path $NewsAgentOutput "preview_a_premarket.html"))
    Newest-Existing @((Join-Path $PrivatePreviewDir "preview_us_close_latest.html"), (Join-Path $NewsAgentOutput "preview_us_close_filtered.html"))
    Newest-Existing @((Join-Path $PrivatePreviewDir "preview_a_close_latest.html"), (Join-Path $NewsAgentOutput "preview_a_close_filtered.html"))
  ) | Where-Object { $_ }
  if ($newsSources.Count) {
    $NewsHtmls = $newsSources -join ";"
  }
}

if (-not $TradingHtml) {
  $candidate = Join-Path $USTradingAgentOutput "preview_technical_us.html"
  if (Test-Path -LiteralPath $candidate) {
    $TradingHtml = $candidate
  }
}

if (-not $TradingCloseHtml) {
  $TradingCloseHtml = Newest-Existing @(
    (Latest-File $USTradingAgentOutput "preview_technical_us_validation*.html"),
    (Latest-File $PrivatePreviewDir "preview_technical_us_validation*.html")
  )
}

if (-not $AShareTradingHtml) {
  $candidate = Join-Path $AShareTradingAgentOutput "preview_ashare_premarket.html"
  if (Test-Path -LiteralPath $candidate) {
    $AShareTradingHtml = $candidate
  }
}

if (-not $AShareTradingCloseHtml) {
  $AShareTradingCloseHtml = Newest-Existing @(
    (Latest-File $AShareTradingAgentOutput "preview_ashare_close*.html"),
    (Latest-File $PrivatePreviewDir "preview_ashare_close*.html")
  )
}

& "$PSScriptRoot\refresh_agent_briefs.ps1" `
  -NewsHtml $NewsHtml `
  -NewsHtmls $NewsHtmls `
  -TradingHtml $TradingHtml `
  -TradingCloseHtml $TradingCloseHtml `
  -AShareTradingHtml $AShareTradingHtml `
  -AShareTradingCloseHtml $AShareTradingCloseHtml

& "$PSScriptRoot\refresh_market_indices.ps1"

$SiteVersionPath = Join-Path $RepoRoot "data\site-version.json"
[ordered]@{
  version = $PublishVersion
  published_at = $PublishedAt
} | ConvertTo-Json | Set-Content -LiteralPath $SiteVersionPath -Encoding UTF8

$IndexPath = Join-Path $RepoRoot "index.html"
$IndexHtml = Get-Content -LiteralPath $IndexPath -Raw -Encoding UTF8
$IndexHtml = $IndexHtml -replace 'styles\.css\?v=[0-9A-Za-z_.:-]+', "styles.css?v=$PublishVersion"
$IndexHtml = $IndexHtml -replace 'app\.js\?v=[0-9A-Za-z_.:-]+', "app.js?v=$PublishVersion"
Set-Content -LiteralPath $IndexPath -Value $IndexHtml -Encoding UTF8

if ($Commit) {
  git add index.html data/agent-briefs.json data/index-performance.json data/site-version.json

  $hasStagedChanges = git diff --cached --quiet
  if ($LASTEXITCODE -ne 0) {
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm"
    git commit -m "Update sanitized agent briefs ($stamp)"
  } else {
    Write-Host "No public brief changes to commit."
  }
}

if ($Push) {
  git push
  if ($LASTEXITCODE -ne 0) {
    throw "git push failed with exit code $LASTEXITCODE"
  }
}
