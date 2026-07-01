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

& "$PSScriptRoot\refresh_agent_briefs.ps1" `
  -NewsHtml $NewsHtml `
  -NewsHtmls $NewsHtmls `
  -TradingHtml $TradingHtml `
  -TradingCloseHtml $TradingCloseHtml `
  -AShareTradingHtml $AShareTradingHtml `
  -AShareTradingCloseHtml $AShareTradingCloseHtml

if ($Commit) {
  git add data/agent-briefs.json

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
}
