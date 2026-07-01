from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable


class VisibleTextParser(HTMLParser):
    """Small stdlib-only HTML text extractor for private email previews."""

    BLOCK_TAGS = {
        "article",
        "br",
        "div",
        "h1",
        "h2",
        "h3",
        "h4",
        "li",
        "p",
        "section",
        "table",
        "td",
        "th",
        "tr",
        "ul",
        "ol",
    }

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self.parts.append(data)

    def text(self) -> str:
        return "".join(self.parts)


REDACTIONS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b[A-Za-z]:\\[^\n\r<>\"']+"), "[redacted-path]"),
    (re.compile(r"(?<!:)//?(?:home|Users|var|etc|root)/[^\s<>\"']+"), "[redacted-path]"),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "[redacted-ip]"),
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[redacted-email]"),
    (re.compile(r"https?://[^\s<>\"']+"), "[redacted-link]"),
    (
        re.compile(
            r"(?i)\b(api[_-]?key|access[_-]?key|token|secret|password|smtp|auth|credential)\b[^\n]{0,120}"
        ),
        "[redacted-secret]",
    ),
    (re.compile(r"(?i)\b(gpt|lgbm|xgboost|ranker|hsa|candidate|baseline)[\w\-./:]*"), "[redacted-model]"),
]


ACTIONABLE_HINTS = re.compile(
    r"(?i)(ticker|symbol|buy|sell|long|short|entry|target|stop|holding|recommend|signal|"
    r"股票代码|推荐|买入|卖出|做多|做空|持有期|止损|目标价|收益率|胜率)"
)


def read_visible_text(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    if path.suffix.lower() in {".html", ".htm"}:
        parser = VisibleTextParser()
        parser.feed(raw)
        return parser.text()
    return raw


def redact(text: str) -> str:
    cleaned = text
    for pattern, replacement in REDACTIONS:
        cleaned = pattern.sub(replacement, cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def safe_lines(text: str, limit: int = 4) -> list[str]:
    candidates: list[str] = []
    for raw_line in text.splitlines():
        line = redact(raw_line)
        if len(line) < 24 or len(line) > 180:
            continue
        if ACTIONABLE_HINTS.search(line):
            continue
        if line.count("|") >= 2:
            continue
        candidates.append(line)
    return candidates[:limit]


def source_status(path_value: str | None) -> tuple[str, list[str]]:
    if not path_value:
        return "ready for daily refresh", []
    path = Path(path_value).expanduser()
    if not path.exists() or not path.is_file():
        return "private snapshot unavailable; using safe fallback", []
    text = read_visible_text(path)
    lines = safe_lines(text)
    mtime = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M local")
    return f"refreshed from private email snapshot at {mtime}", lines


def merge_bullets(defaults: Iterable[str], extracted: Iterable[str]) -> list[str]:
    merged = list(defaults)
    for line in extracted:
        if line not in merged and len(merged) < 5:
            merged.append(line)
    return merged


def build_payload(news_source: str | None, trading_source: str | None) -> dict:
    news_status, news_lines = source_status(news_source)
    trading_status, trading_lines = source_status(trading_source)

    return {
        "ok": True,
        "published_at": datetime.now().strftime("%Y-%m-%d %H:%M local"),
        "scope": "sanitized_public_showcase",
        "briefs": [
            {
                "id": "market-news-agent",
                "market": "News Agent",
                "title": "Market News Agent",
                "updated_at": news_status,
                "summary": (
                    "Transforms market, macro, and company news into concise research context while "
                    "keeping private ingestion, prompting, scoring, and data-source details withheld."
                ),
                "tags": ["macro context", "company catalysts", "market sentiment"],
                "bullets": merge_bullets(
                    [
                        "Produces pre-market and post-market intelligence surfaces for private review.",
                        "Separates broad index recaps from higher-information company and macro events.",
                        "Publishes only redacted public snapshots; raw feeds and private prompts are excluded.",
                    ],
                    news_lines,
                ),
            },
            {
                "id": "trading-recommendation-agent",
                "market": "Trading Agent",
                "title": "Trading Recommendation Agent",
                "updated_at": trading_status,
                "summary": (
                    "Combines technical scans, ranking overlays, and close validation into private email "
                    "briefs; the public layer is intentionally non-actionable."
                ),
                "tags": ["technical scan", "ranking overlay", "validation loop"],
                "bullets": merge_bullets(
                    [
                        "Generates pre-market opportunity scans and post-market validation summaries.",
                        "Keeps ticker-level signals, model internals, and strategy rules private.",
                        "Public showcase displays capabilities and workflow only, not live recommendations.",
                    ],
                    trading_lines,
                ),
            },
            {
                "id": "portfolio-safe-disclosure",
                "market": "Disclosure",
                "title": "Public Boundary",
                "updated_at": "always on",
                "summary": (
                    "This GitHub Pages site is a portfolio layer for demonstrating engineering systems, "
                    "not a trading signal distribution channel."
                ),
                "tags": ["showcase only", "redacted", "no advice"],
                "bullets": [
                    "No credentials, infrastructure addresses, true local paths, raw logs, or private recipients are published.",
                    "No core training code, strategy implementation, or data-source details are exposed.",
                    "Content is for system-demonstration purposes and is not financial advice.",
                ],
            },
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish sanitized public agent brief cards.")
    parser.add_argument("--news-html", default=os.getenv("NEWS_AGENT_PUBLIC_SOURCE"))
    parser.add_argument("--trading-html", default=os.getenv("TRADING_AGENT_PUBLIC_SOURCE"))
    parser.add_argument("--output", default="data/agent-briefs.json")
    args = parser.parse_args()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = build_payload(args.news_html, args.trading_html)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote sanitized public brief data to {output}")


if __name__ == "__main__":
    main()
