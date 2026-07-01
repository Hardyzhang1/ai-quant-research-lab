param(
  [string]$NewsHtml = $env:NEWS_AGENT_PUBLIC_SOURCE,
  [string]$TradingHtml = $env:TRADING_AGENT_PUBLIC_SOURCE,
  [string]$Output = "data/agent-briefs.json"
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $RepoRoot

$ArgsList = @("scripts/publish_agent_briefs.py", "--output", $Output)

if ($NewsHtml) {
  $ArgsList += @("--news-html", $NewsHtml)
}

if ($TradingHtml) {
  $ArgsList += @("--trading-html", $TradingHtml)
}

python @ArgsList
