param(
  [string]$NewsHtml = $env:NEWS_AGENT_PUBLIC_SOURCE,
  [string]$NewsHtmls = $env:NEWS_AGENT_PUBLIC_SOURCES,
  [string]$TradingHtml = $env:TRADING_AGENT_PUBLIC_SOURCE,
  [string]$TradingCloseHtml = $env:TRADING_AGENT_CLOSE_SOURCE,
  [string]$AShareTradingHtml = $env:ASHARE_TRADING_AGENT_PUBLIC_SOURCE,
  [string]$AShareTradingCloseHtml = $env:ASHARE_TRADING_AGENT_CLOSE_SOURCE,
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

if ($TradingCloseHtml) {
  $ArgsList += @("--trading-close-html", $TradingCloseHtml)
}

if ($AShareTradingHtml) {
  $ArgsList += @("--ashare-trading-html", $AShareTradingHtml)
}

if ($AShareTradingCloseHtml) {
  $ArgsList += @("--ashare-trading-close-html", $AShareTradingCloseHtml)
}

python @ArgsList
