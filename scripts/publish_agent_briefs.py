from __future__ import annotations

import argparse
import html
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


class TableParser(HTMLParser):
    """Extract simple HTML tables without external dependencies."""

    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._table: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag == "table":
            self._table = []
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = []
        elif tag in {"br", "div", "p", "li"} and self._cell is not None:
            self._cell.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if tag in {"td", "th"} and self._cell is not None and self._row is not None:
            value = re.sub(r"\s+", " ", "".join(self._cell)).strip()
            self._row.append(value)
            self._cell = None
        elif tag == "tr" and self._row is not None and self._table is not None:
            if any(cell for cell in self._row):
                self._table.append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            if self._table:
                self.tables.append(self._table)
            self._table = None

    def handle_data(self, data: str) -> None:
        if not self._skip_depth and self._cell is not None:
            self._cell.append(data)


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
    (re.compile(r"(?i)\b(gpt|lgbm|xgboost|ranker|hsa|baseline|candidate|shadow)[\w\-./:]*"), "[redacted-model]"),
]


ACTIONABLE_HINTS = re.compile(
    r"(?i)(ticker|symbol|buy|sell|long|short|entry|target|stop|holding|recommend|signal|"
    r"股票代码|推荐|买入|卖出|做多|做空|持有期|止损|目标价|收益率|胜率)"
)


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


def split_paths(path_value: str | None) -> list[Path]:
    if not path_value:
        return []
    paths: list[Path] = []
    for raw in re.split(r"[;|]", path_value):
        raw = raw.strip()
        if raw:
            paths.append(Path(raw).expanduser())
    return paths


def existing_paths(path_value: str | None) -> list[Path]:
    return [path for path in split_paths(path_value) if path.exists() and path.is_file()]


def source_status(path_value: str | None) -> tuple[str, list[str]]:
    if not path_value:
        return "ready for daily refresh", []
    paths = existing_paths(path_value)
    if not paths:
        return "private snapshot unavailable; using safe fallback", []
    text = "\n".join(read_visible_text(path) for path in paths)
    lines = safe_lines(text)
    mtime = max(path.stat().st_mtime for path in paths)
    stamp = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M local")
    return f"refreshed from private snapshots at {stamp}", lines


def parse_tables(path: Path) -> list[list[list[str]]]:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    parser = TableParser()
    parser.feed(raw)
    return parser.tables


def compact(value: object, limit: int = 220) -> str:
    text = redact(html.unescape(str(value or "")))
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        return text[: limit - 1].rstrip() + "..."
    return text


def score_bucket(value: object) -> str:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return "withheld"
    if score >= 0.12:
        return "high"
    if score >= 0.04:
        return "medium"
    if score > 0:
        return "low-positive"
    return "below-threshold"


def extract_generated_at(paths: list[Path]) -> str | None:
    for path in paths:
        text = read_visible_text(path)
        match = re.search(r"(?:生成时间|generated_at)[:：]\s*([^\n\r]+)", text)
        if match:
            return compact(match.group(1), 80)
    return None


def extract_mood(paths: list[Path]) -> str | None:
    moods: list[str] = []
    for path in paths:
        text = read_visible_text(path)
        match = re.search(r"市场情绪[:：]\s*([^\n\r]+)", text)
        if match:
            moods.append(compact(match.group(1), 80))
    return " / ".join(moods[:2]) if moods else None


def extract_news_items(path_value: str | None, limit: int = 8) -> list[dict]:
    items: list[dict] = []
    for path in existing_paths(path_value):
        market = "A-share" if "preview_a" in path.name.lower() else "US"
        for table in parse_tables(path):
            for row in table:
                if len(row) < 4:
                    continue
                if row[0] in {"新闻", "News"} or "新闻" in row[0] and len(row[0]) < 12:
                    continue
                title, related, tone_value, reason = row[:4]
                if len(title.strip()) < 8:
                    continue
                items.append(
                    {
                        "kind": "news",
                        "market": market,
                        "title": compact(title, 120),
                        "tone": compact(tone_value, 28),
                        "related": compact(related, 80),
                        "summary": compact(reason, 180),
                    }
                )
                if len(items) >= limit:
                    return items
    return items


def public_email_lines(path: Path, limit: int = 90) -> list[str]:
    """Return public-safe email text lines while preserving report substance."""

    text = read_visible_text(path)
    lines: list[str] = []
    seen: set[str] = set()
    for raw_line in text.splitlines():
        line = compact(raw_line, 260)
        if not line or line in seen:
            continue
        if line in {"|", "-", "--"}:
            continue
        if len(line) < 2:
            continue
        seen.add(line)
        lines.append(line)
        if len(lines) >= limit:
            break
    return lines


def public_email_tables(path: Path, limit: int = 6) -> list[dict]:
    tables: list[dict] = []
    for table in parse_tables(path):
        if not table:
            continue
        header = [compact(cell, 80) for cell in table[0]][:8]
        body = [[compact(cell, 120) for cell in row[:8]] for row in table[1:9]]
        if header or body:
            tables.append({"headers": header, "rows": body})
        if len(tables) >= limit:
            break
    return tables


def email_kind_from_path(path: Path, fallback: str) -> str:
    name = path.name.lower()
    if "close" in name or "validation" in name or "post" in name:
        return f"{fallback} close review"
    if "premarket" in name or "open" in name or "preview" in name:
        return f"{fallback} pre-market"
    return fallback


def build_email_mirrors(
    news_source: str | None,
    trading_source: str | None,
    trading_close_source: str | None,
) -> list[dict]:
    mirrors: list[dict] = []
    sources: list[tuple[str, list[Path]]] = [
        ("News Agent", existing_paths(news_source)),
        ("Trading Agent", existing_paths(trading_source)),
        ("Trading Agent", existing_paths(trading_close_source)),
    ]
    for label, paths in sources:
        for path in paths:
            stamp = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M local")
            mirrors.append(
                {
                    "id": re.sub(r"[^a-z0-9]+", "-", f"{label}-{path.stem}".lower()).strip("-"),
                    "title": email_kind_from_path(path, label),
                    "updated_at": stamp,
                    "source": "post-delivery public mirror",
                    "lines": public_email_lines(path),
                    "tables": public_email_tables(path),
                }
            )
    return mirrors


def load_json(path_value: str | None) -> dict | None:
    paths = existing_paths(path_value)
    if not paths:
        return None
    try:
        return json.loads(paths[0].read_text(encoding="utf-8", errors="ignore"))
    except json.JSONDecodeError:
        return None


def extract_markdown_watchlist(path_value: str | None, limit: int = 3) -> list[dict]:
    rows: list[dict] = []
    paths = existing_paths(path_value)
    if not paths:
        return rows
    text = read_visible_text(paths[0])
    for raw in text.splitlines():
        line = html.unescape(raw.strip())
        if not re.match(r"^\|\s*\d+\s*\|", line):
            continue
        parts = [part.strip() for part in line.strip("|").split("|")]
        if len(parts) < 10:
            continue
        rows.append(
            {
                "kind": "watchlist",
                "title": f"Observation {len(rows) + 1}",
                "symbol": compact(parts[1], 32),
                "name": compact(parts[2], 32),
                "status": "not triggered",
                "industry": compact(parts[3], 44),
                "horizon": "pre-market watch",
                "summary": "Near-threshold watch item from the paper-tracking report; it did not reach the formal trigger.",
                "reason": compact(parts[9], 120),
                "metrics": [
                    {"label": "close", "value": compact(parts[4], 24)},
                    {"label": "win prob", "value": compact(parts[6], 24)},
                    {"label": "expected", "value": compact(parts[7], 24)},
                    {"label": "loss risk", "value": compact(parts[8], 24)},
                ],
            }
        )
        if len(rows) >= limit:
            break
    return rows


def extract_trading_recommendations(
    signal_json_path: str | None,
    trading_html_path: str | None,
    close_html_path: str | None,
    limit: int = 4,
) -> list[dict]:
    recommendations: list[dict] = []
    signal_payload = load_json(signal_json_path)
    if signal_payload:
        signals = signal_payload.get("signals") or []
        selected_count = signal_payload.get("selected_count", len(signals))
        for signal in signals[:limit]:
            rank = signal.get("rank") or len(recommendations) + 1
            recommendations.append(
                {
                    "kind": "research_signal",
                    "title": f"Research candidate {rank}",
                    "symbol": compact(signal.get("symbol") or "", 32),
                    "name": compact(signal.get("name") or "", 32),
                    "status": "paper signal" if selected_count else "not triggered",
                    "industry": compact(signal.get("industry") or "withheld", 44),
                    "horizon": f"{signal.get('horizon', '--')} trading days",
                    "summary": (
                        "Private ranking workflow selected this paper-tracked candidate; "
                        "implementation rules and model internals are withheld."
                    ),
                    "reason": f"score bucket: {score_bucket(signal.get('ranker_score'))}; channel and policy withheld.",
                    "metrics": [
                        {"label": "trade date", "value": compact(signal_payload.get("trade_date"), 24)},
                        {"label": "universe", "value": compact(signal_payload.get("universe"), 24)},
                        {"label": "research only", "value": "yes" if signal.get("research_only", True) else "no"},
                    ],
                }
            )

    if not recommendations:
        recommendations.extend(extract_markdown_watchlist(trading_html_path, limit=3))

    close_paths = existing_paths(close_html_path)
    if close_paths:
        text = read_visible_text(close_paths[0])
        if "未触发正式机会" in text or "没有已到推荐持有期" in text:
            recommendations.append(
                {
                    "kind": "validation",
                    "title": "Close validation",
                    "status": "no matured validation",
                    "industry": "portfolio state",
                    "horizon": "post-close",
                    "summary": "Latest close report found no formal pre-market trade to validate and no matured holding-period signal.",
                    "reason": "The validation loop still published a state check, but no public trade result is shown.",
                    "metrics": [],
                }
            )
    return recommendations[:limit]


def brief_stats(news_paths: list[Path], trading_signal: dict | None) -> dict:
    stats: dict[str, list[dict[str, str]]] = {"news": [], "trading": []}
    generated = extract_generated_at(news_paths)
    mood = extract_mood(news_paths)
    if generated:
        stats["news"].append({"label": "generated", "value": generated})
    if mood:
        stats["news"].append({"label": "mood", "value": mood})
    if trading_signal:
        stats["trading"].extend(
            [
                {"label": "trade date", "value": compact(trading_signal.get("trade_date"), 24)},
                {"label": "selected", "value": compact(trading_signal.get("selected_count"), 16)},
                {"label": "universe", "value": compact(trading_signal.get("universe"), 24)},
            ]
        )
    return stats


def merge_bullets(defaults: Iterable[str], extracted: Iterable[str]) -> list[str]:
    merged = list(defaults)
    for line in extracted:
        if line not in merged and len(merged) < 5:
            merged.append(line)
    return merged


def build_payload(
    news_source: str | None,
    trading_source: str | None,
    trading_signal_json: str | None,
    trading_close_source: str | None,
) -> dict:
    news_status, news_lines = source_status(news_source)
    trading_status, trading_lines = source_status(trading_source)
    news_items = extract_news_items(news_source)
    trading_signal = load_json(trading_signal_json)
    trading_items = extract_trading_recommendations(
        trading_signal_json,
        trading_source,
        trading_close_source,
    )
    stats = brief_stats(existing_paths(news_source), trading_signal)
    email_mirrors = build_email_mirrors(news_source, trading_source, trading_close_source)

    return {
        "ok": True,
        "published_at": datetime.now().strftime("%Y-%m-%d %H:%M local"),
        "scope": "public_email_mirror_with_private_internals_withheld",
        "email_mirrors": email_mirrors,
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
                "stats": stats["news"],
                "bullets": merge_bullets(
                    [
                        "Produces pre-market and post-market intelligence surfaces for private review.",
                        "Separates broad index recaps from higher-information company and macro events.",
                        "Publishes only redacted public snapshots; raw feeds and private prompts are excluded.",
                    ],
                    news_lines,
                ),
                "items": news_items,
            },
            {
                "id": "trading-recommendation-agent",
                "market": "Trading Agent",
                "title": "Trading Recommendation Agent",
                "updated_at": trading_status,
                "summary": (
                    "Combines technical scans, ranking overlays, and close validation into private email "
                    "briefs; the public layer mirrors report content while withholding private internals."
                ),
                "tags": ["technical scan", "ranking overlay", "validation loop"],
                "stats": stats["trading"],
                "bullets": merge_bullets(
                    [
                        "Generates pre-market opportunity scans and post-market validation summaries.",
                        "Keeps ticker-level signals, model internals, and strategy rules private.",
                        "Public showcase displays redacted paper-tracking state, not executable live recommendations.",
                    ],
                    trading_lines,
                ),
                "recommendations": trading_items,
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
    parser.add_argument("--news-htmls", default=os.getenv("NEWS_AGENT_PUBLIC_SOURCES"))
    parser.add_argument("--trading-html", default=os.getenv("TRADING_AGENT_PUBLIC_SOURCE"))
    parser.add_argument("--trading-signal-json", default=os.getenv("TRADING_AGENT_SIGNAL_JSON"))
    parser.add_argument("--trading-close-html", default=os.getenv("TRADING_AGENT_CLOSE_SOURCE"))
    parser.add_argument("--output", default="data/agent-briefs.json")
    args = parser.parse_args()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    news_source = args.news_htmls or args.news_html
    payload = build_payload(
        news_source,
        args.trading_html,
        args.trading_signal_json,
        args.trading_close_html,
    )
    has_email_sources = any([news_source, args.trading_html, args.trading_close_html])
    if not has_email_sources and output.exists():
        try:
            previous = json.loads(output.read_text(encoding="utf-8", errors="ignore"))
            previous_mirrors = previous.get("email_mirrors")
            if isinstance(previous_mirrors, list) and previous_mirrors:
                payload["email_mirrors"] = previous_mirrors
                payload["scope"] = "public_email_mirror_preserved_from_previous_refresh"
        except json.JSONDecodeError:
            pass
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote sanitized public brief data to {output}")


if __name__ == "__main__":
    main()
