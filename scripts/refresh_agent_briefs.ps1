param(
  [string]$NewsHtml = $env:NEWS_AGENT_PUBLIC_SOURCE,
  [string]$NewsHtmls = $env:NEWS_AGENT_PUBLIC_SOURCES,
  [string]$TradingHtml = $env:TRADING_AGENT_PUBLIC_SOURCE,
  [string]$TradingSignalJson = $env:TRADING_AGENT_SIGNAL_JSON,
  [string]$TradingCloseHtml = $env:TRADING_AGENT_CLOSE_SOURCE,
  [string]$Output = "data/agent-briefs.json"
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $RepoRoot

$ArgsList = @("scripts/publish_agent_briefs.py", "--output", $Output)

if ($NewsHtml) {
  $ArgsList += @("--news-html", $NewsHtml)
}

if ($NewsHtmls) {
  $ArgsList += @("--news-htmls", $NewsHtmls)
}

if ($TradingHtml) {
  $ArgsList += @("--trading-html", $TradingHtml)
}

if ($TradingSignalJson) {
  $ArgsList += @("--trading-signal-json", $TradingSignalJson)
}

if ($TradingCloseHtml) {
  $ArgsList += @("--trading-close-html", $TradingCloseHtml)
}

python @ArgsList
