# AI Quant Research Lab

A public showcase for a private AI-driven quant research workbench.

This repository is intentionally presentation-only. It describes the system architecture, agent tracks, dashboard surfaces, and safety boundaries without publishing core strategy code, datasets, model artifacts, credentials, or training logs.

## Project Tracks

- **RD-Agent Quant Lab**: Remote quant research execution, safe-run resource controls, Qlib evaluation, and result dashboards.
- **Market News Agent**: Market intelligence workflow for monitoring, structuring, and summarizing research context.
- **Trading Recommendation Agent**: Private pre-market opportunity scan and post-market validation workflow with only sanitized public surfaces.
- **VWAP Learning Agent**: Execution-strategy learning track focused on VWAP-style enhancement and experiment comparison.

## Public Scope

Published here:

- Showcase website
- High-level architecture narrative
- Sanitized project descriptions
- Dashboard and workflow concepts

Not published here:

- Core implementation code
- Trading logic or strategy details
- Training scripts and prompts
- Raw logs, datasets, model artifacts, and credentials
- Private infrastructure addresses

## GitHub Pages

The site is deployed from static files in this repository through GitHub Pages.

Local preview:

```powershell
python -m http.server 8080
```

Then open `http://127.0.0.1:8080/`.

## Daily Agent Briefs

The homepage reads `data/agent-briefs.json` and renders sanitized public cards for the news agent and trading recommendation agent.

Refresh the public data after private emails are delivered:

```powershell
.\scripts\refresh_agent_briefs.ps1
```

Optionally point the refresher at private HTML email previews without committing those previews:

```powershell
$env:NEWS_AGENT_PUBLIC_SOURCE = "path-to-private-news-email-preview.html"
$env:TRADING_AGENT_PUBLIC_SOURCE = "path-to-private-trading-email-preview.html"
.\scripts\refresh_agent_briefs.ps1
```

The refresher redacts paths, email addresses, IP addresses, links, credential-like text, model identifiers, and lines that look like live trading signals. Only `data/agent-briefs.json` should be committed.

To publish the refreshed cards to GitHub Pages after email delivery:

```powershell
.\scripts\publish_pages_update.ps1 -Commit -Push
```

Use `-Push` only on the machine where GitHub credentials are already configured. The script commits only the sanitized JSON surface.

## Maintenance

This showcase is designed to be maintained with Codex-assisted edits. Future updates can add project cards, sanitized screenshots, and result summaries without exposing private research internals.
