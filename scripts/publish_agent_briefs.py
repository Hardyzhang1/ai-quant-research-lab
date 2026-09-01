from __future__ import annotations

import argparse
import html
import json
import os
import re
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path


class VisibleTextParser(HTMLParser):
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
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001
        if tag in {"script", "style", "noscript"}:
            self.skip_depth += 1
            return
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self.skip_depth:
            self.skip_depth -= 1
            return
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            self.parts.append(data)

    def text(self) -> str:
        return "".join(self.parts)


class TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self.table: list[list[str]] | None = None
        self.row: list[str] | None = None
        self.cell: list[str] | None = None
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001
        if tag in {"script", "style", "noscript"}:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        if tag == "table":
            self.table = []
        elif tag == "tr" and self.table is not None:
            self.row = []
        elif tag in {"td", "th"} and self.row is not None:
            self.cell = []
        elif tag in {"br", "div", "p", "li"} and self.cell is not None:
            self.cell.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self.skip_depth:
            self.skip_depth -= 1
            return
        if self.skip_depth:
            return
        if tag in {"td", "th"} and self.cell is not None and self.row is not None:
            value = normalize("".join(self.cell))
            self.row.append(value)
            self.cell = None
        elif tag == "tr" and self.row is not None and self.table is not None:
            if any(self.row):
                self.table.append(self.row)
            self.row = None
        elif tag == "table" and self.table is not None:
            if self.table:
                self.tables.append(self.table)
            self.table = None

    def handle_data(self, data: str) -> None:
        if not self.skip_depth and self.cell is not None:
            self.cell.append(data)


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

NOISE_HINTS = (
    "重要免责声明",
    "本邮件内容仅用于",
    "不构成任何形式",
    "其中关于",
    "任何证券交易",
    "独立判断",
    "如需投资建议",
    "not investment advice",
    "private recipients",
    "SMTP",
    "OpenAI",
    "API Key",
)

HEADER_HINTS = {
    "新闻",
    "相关股票",
    "判断",
    "理由",
    "股票",
    "评分",
    "持有期",
    "时间",
    "来源",
    "市场",
    "指数",
    "状态",
}


def normalize(value: object) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text


def read_text(path: Path) -> str:
    data = path.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def visible_text(path: Path) -> str:
    raw = read_text(path)
    if path.suffix.lower() in {".html", ".htm"}:
        parser = VisibleTextParser()
        parser.feed(raw)
        return parser.text()
    return raw


def parse_tables(path: Path) -> list[list[list[str]]]:
    raw = read_text(path)
    parser = TableParser()
    parser.feed(raw)
    return parser.tables


def fragment_text(fragment: str) -> str:
    parser = VisibleTextParser()
    parser.feed(fragment)
    return normalize(parser.text())


def iter_h3_sections(raw: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    pattern = re.compile(r"(?is)<h3\b[^>]*>(.*?)</h3>(.*?)(?=<h[23]\b|</body>|$)")
    for match in pattern.finditer(raw):
        heading = fragment_text(match.group(1))
        body = match.group(2)
        if heading:
            sections.append((heading, body))
    return sections


def redact(text: str, limit: int = 180) -> str:
    cleaned = normalize(text)
    for pattern, replacement in REDACTIONS:
        cleaned = pattern.sub(replacement, cleaned)
    if len(cleaned) > limit:
        cleaned = cleaned[: limit - 1].rstrip() + "..."
    return cleaned


def split_paths(value: str | None) -> list[Path]:
    if not value:
        return []
    out: list[Path] = []
    for raw in re.split(r"[;|]", value):
        raw = raw.strip()
        if raw:
            out.append(Path(raw).expanduser())
    return out


def existing_paths(value: str | None) -> list[Path]:
    return [path for path in split_paths(value) if path.exists() and path.is_file()]


def is_ashare(path: Path) -> bool:
    name = path.name.lower()
    parent = str(path.parent).lower()
    return "ashare" in name or "preview_a" in name or "a_close" in name or "a_premarket" in name or "ashare" in parent


def is_post(path: Path) -> bool:
    name = path.name.lower()
    return any(token in name for token in ("close", "post", "validation", "after"))


def source_label(path: Path) -> str:
    lower = str(path).lower()
    name = path.name.lower()
    if "market-news-agent" in lower:
        return "Market News Agent"
    if "technical" in lower or "trading" in lower or "ashare-rq-agent" in lower or name.startswith("preview_ashare"):
        return "Trading Recommendation Agent"
    return "Market News Agent"



def is_standalone_market_number(line: str) -> bool:
    """Filter orphan index levels/percentages extracted from tables into highlights."""
    text = normalize(line).replace(",", "")
    return bool(re.fullmatch(r"[+-]?(?:\d{1,7}(?:\.\d+)?|\d+(?:\.\d+)?%)", text))


def is_global_index_heading(line: str) -> bool:
    text = normalize(line).lower().replace(" ", "")
    return (
        "过去24小时全球主要股指" in text
        or "globalmajorindices" in text
        or "majorglobalindices" in text
        or "globalindices" in text
    )

def meaningful_lines(path: Path, limit: int = 8) -> list[str]:
    lines: list[str] = []
    seen: set[str] = set()
    for raw in visible_text(path).splitlines():
        line = redact(raw, 190)
        if not line or line in seen:
            continue
        if len(line) < 8:
            continue
        if any(hint.lower() in line.lower() for hint in NOISE_HINTS):
            continue
        if line in HEADER_HINTS:
            continue
        if is_global_index_heading(line):
            continue
        if is_standalone_market_number(line):
            continue
        if len(line) <= 5 and re.search(r"^[A-Z0-9.^+-]+$", line):
            continue
        seen.add(line)
        lines.append(line)
        if len(lines) >= limit:
            break
    return lines


def generated_at(path: Path) -> str | None:
    text = visible_text(path)
    patterns = [
        r"生成时间[:：]\s*([^\n\r]+)",
        r"Generated(?: at)?[:：]\s*([^\n\r]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I)
        if match:
            return redact(match.group(1), 90)
    return None


def compact_tables(path: Path, max_tables: int = 2, max_rows: int = 5, max_cols: int = 5) -> list[dict]:
    out: list[dict] = []
    for table in parse_tables(path):
        if not table:
            continue
        header = [redact(cell, 70) for cell in table[0][:max_cols]]
        rows = []
        for row in table[1 : max_rows + 1]:
            cleaned = [redact(cell, 100) for cell in row[:max_cols]]
            if any(cleaned):
                rows.append(cleaned)
        if header or rows:
            out.append({"headers": header, "rows": rows})
        if len(out) >= max_tables:
            break
    return out


def safe_int(value: object) -> int | None:
    match = re.search(r"\d+", normalize(value))
    return int(match.group(0)) if match else None


def safe_float(value: object) -> float | None:
    match = re.search(r"-?\d+(?:\.\d+)?", normalize(value).replace(",", ""))
    return float(match.group(0)) if match else None


def pct(value: float | None) -> str:
    if value is None:
        return "--"
    return f"{value * 100:.2f}%"


def parse_percent_value(value: object) -> float | None:
    text = normalize(value).replace(",", "")
    match = re.search(r"([+-]?\d+(?:\.\d+)?)\s*%", text)
    if not match:
        return None
    return float(match.group(1)) / 100.0


def parse_ashare_maturity_validation(source: str | None, previous: dict | None = None) -> dict:
    paths = existing_paths(source)
    path = latest(paths)
    if path is None:
        preserved = (previous or {}).get("ashare_maturity_validation") or (previous or {}).get("ashare_signal_tracking")
        if isinstance(preserved, dict):
            return preserved
        return {"ok": False}

    text = visible_text(path)
    rows: list[dict] = []
    returns: list[float] = []

    for table in parse_tables(path):
        candidate_rows: list[dict] = []
        for row in table[1:]:
            if len(row) < 7:
                continue
            signal_date = normalize(row[0])
            stock = normalize(row[1])
            final_return = normalize(row[5])
            if not re.fullmatch(r"20\d{2}-\d{2}-\d{2}", signal_date):
                continue
            if not re.fullmatch(r"\d{6}\.(?:XSHG|XSHE|BJ|XBEI)", stock):
                continue
            return_value = parse_percent_value(final_return)
            if return_value is not None:
                returns.append(return_value)
            holding_days = safe_int(row[4])
            result = "Win" if (return_value is not None and return_value > 0) else "Loss"
            candidate_rows.append(
                {
                    "signal_date": signal_date,
                    "stock": stock,
                    "entry": redact(row[2], 80),
                    "exit": redact(row[3], 80),
                    "holding_period": f"{holding_days} trading days" if holding_days is not None else redact(row[4], 50),
                    "final_return": final_return,
                    "return_value": return_value,
                    "result": result,
                }
            )
        if len(candidate_rows) > len(rows):
            rows = candidate_rows

    matured_count = len(rows)
    win_count = sum(1 for value in returns if value > 0)
    win_rate = win_count / matured_count if matured_count else None
    average_return = sum(returns) / len(returns) if returns else None
    median_return = None
    if returns:
        ordered = sorted(returns)
        middle = len(ordered) // 2
        if len(ordered) % 2:
            median_return = ordered[middle]
        else:
            median_return = (ordered[middle - 1] + ordered[middle]) / 2

    tracking_count = None
    tracking_match = re.search(r"仍在跟踪[^0-9]*(\d+)", text)
    if tracking_match:
        tracking_count = int(tracking_match.group(1))

    summary_match = re.search(
        r"已到推荐持有期[^0-9]*(\d+).*?胜[^0-9]*(\d+).*?胜率[^0-9]*([0-9.]+%).*?平均收益[^0-9+-]*([+-]?[0-9.]+%).*?中位数收益[^0-9+-]*([+-]?[0-9.]+%)",
        text,
        flags=re.S,
    )
    if summary_match:
        matured_count = int(summary_match.group(1))
        win_count = int(summary_match.group(2))
        win_rate_text = summary_match.group(3)
        average_return_text = summary_match.group(4)
        median_return_text = summary_match.group(5)
    else:
        win_rate_text = pct(win_rate) if win_rate is not None else "--"
        average_return_text = pct(average_return) if average_return is not None else "--"
        median_return_text = pct(median_return) if median_return is not None else "--"

    stamp = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M local")

    stats = [
        {"label": "Win rate", "value": win_rate_text},
        {"label": "Average return", "value": average_return_text},
        {"label": "Median return", "value": median_return_text},
        {"label": "Still tracking", "value": str(tracking_count) if tracking_count is not None else "--"},
    ]

    return {
        "ok": True,
        "market": "A-share technical validation",
        "title": "Maturity validation digest",
        "updated_at": stamp,
        "matured_count": matured_count,
        "win_count": win_count,
        "win_rate": win_rate_text,
        "average_return": average_return_text,
        "median_return": median_return_text,
        "tracking_count": tracking_count,
        "stats": stats,
        "rows": rows,
        "public_notes": [
            "Generated from the maturity-validation section of the daily A-share technical-analysis email.",
            "Records are shown after they reach the recommended holding horizon.",
            "Model internals, raw data, local paths, credentials, and private execution rules are withheld.",
        ],
    }


def post_market_section_highlights(path: Path) -> list[str]:
    if not is_post(path) or path.suffix.lower() not in {".html", ".htm"}:
        return []

    raw = read_text(path)
    highlights: list[str] = []
    for heading, body in iter_h3_sections(raw):
        if heading.startswith("市场情绪"):
            p_match = re.search(r"(?is)<p\b[^>]*>(.*?)</p>", body)
            summary = fragment_text(p_match.group(1) if p_match else body)
            if summary:
                highlights.append(redact(f"{heading} - {summary}", 260))
        elif heading == "主要驱动":
            items = [fragment_text(item) for item in re.findall(r"(?is)<li\b[^>]*>(.*?)</li>", body)]
            items = [item for item in items if item][:3]
            if items:
                highlights.append(redact("主要驱动 - " + "；".join(items), 260))
        elif heading == "下一交易日关注":
            items = [fragment_text(item) for item in re.findall(r"(?is)<li\b[^>]*>(.*?)</li>", body)]
            items = [item for item in items if item][:3]
            if items:
                highlights.append(redact("下一交易日关注 - " + "；".join(items), 260))

    ordered: list[str] = []
    seen_prefixes: set[str] = set()
    for line in highlights:
        prefix = line.split(" - ", 1)[0].strip()
        if prefix not in seen_prefixes:
            ordered.append(line)
            seen_prefixes.add(prefix)
        if len(ordered) >= 3:
            break
    return ordered


def pre_market_news_highlights(path: Path) -> list[str]:
    if is_post(path) or source_label(path) != "Market News Agent":
        return []

    highlights: list[str] = []
    for table in parse_tables(path):
        if len(table) < 2:
            continue
        headers = [normalize(cell) for cell in table[0]]
        if not headers:
            continue
        first_header = headers[0]
        if first_header in {"事件/数据", "Event/Data"}:
            prefix = "宏观"
        elif first_header in {"新闻", "News"}:
            prefix = "公司/市场"
        else:
            continue
        for row in table[1:]:
            if not row:
                continue
            title = redact(row[0], 210)
            if not title:
                continue
            highlights.append(f"{prefix} - {title}")
            if len(highlights) >= 5:
                break
        if len(highlights) >= 5:
            break

    ordered: list[str] = []
    seen: set[str] = set()
    for line in highlights:
        if line not in seen:
            ordered.append(line)
            seen.add(line)
        if len(ordered) >= 5:
            break
    return ordered


def pick_report_title(lines: list[str], fallback: str) -> str:
    title_hints = ("盘前", "收盘", "总结", "技术分析", "机会扫描", "成熟期验证", "复盘")
    for line in lines:
        if any(hint in line for hint in title_hints) and "生成时间" not in line:
            return line
    for line in lines:
        if "生成时间" not in line and "覆盖窗口" not in line:
            return line
    return fallback


def report_from_path(path: Path) -> dict:
    lines = meaningful_lines(path)
    if source_label(path) == "Market News Agent" and is_post(path):
        title = "A股收盘总结" if is_ashare(path) else "美股收盘总结"
    elif source_label(path) == "Market News Agent" and not is_post(path):
        title = "A股盘前重要金融新闻" if is_ashare(path) else "美股盘前重要金融新闻"
    elif source_label(path) == "Trading Recommendation Agent" and is_ashare(path) and not is_post(path):
        title = "A股开盘信息"
    else:
        title = pick_report_title(lines, path.stem.replace("_", " "))
    section_highlights = pre_market_news_highlights(path) or post_market_section_highlights(path)
    fallback_highlights = [line for line in lines if line != title and "生成时间" not in line]
    highlights = section_highlights[:3] if section_highlights else fallback_highlights[:5]
    stamp = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M local")
    return {
        "source": source_label(path),
        "title": title,
        "generated_at": generated_at(path) or stamp,
        "updated_at": stamp,
        "highlights": highlights,
        "tables": compact_tables(path),
    }


def clean_report_sections(sections: list[dict]) -> list[dict]:
    """Apply the public highlight filters even when preserving previous JSON."""
    for section in sections:
        for report in section.get("reports", []):
            report["highlights"] = [
                line
                for line in report.get("highlights", [])
                if not is_global_index_heading(line) and not is_standalone_market_number(line)
            ]
    return sections


def latest(paths: list[Path]) -> Path | None:
    if not paths:
        return None
    return max(paths, key=lambda p: p.stat().st_mtime)


def build_section(section_id: str, title: str, candidates: list[Path]) -> dict:
    # Keep only the latest report per agent type inside the section. This avoids dumping old emails.
    chosen: list[Path] = []
    for label in ("Market News Agent", "Trading Recommendation Agent"):
        path = latest([p for p in candidates if source_label(p) == label])
        if path:
            chosen.append(path)
    reports = [report_from_path(path) for path in chosen]
    updated = (
        datetime.fromtimestamp(max(path.stat().st_mtime for path in chosen)).strftime("%Y-%m-%d %H:%M local")
        if chosen
        else "waiting for latest report"
    )
    return {
        "id": section_id,
        "title": title,
        "updated_at": updated,
        "summary": "Latest web-formatted report digest. Click to expand; click again to collapse.",
        "reports": reports,
    }


def build_report_sections(
    news_source: str | None,
    trading_source: str | None,
    trading_close_source: str | None,
    ashare_trading_source: str | None,
    ashare_trading_close_source: str | None,
) -> list[dict]:
    news_paths = existing_paths(news_source)
    trading_pre_paths = existing_paths(trading_source) + existing_paths(ashare_trading_source)
    trading_post_paths = existing_paths(trading_close_source) + existing_paths(ashare_trading_close_source)
    all_paths = news_paths + trading_pre_paths + trading_post_paths

    a_pre = [p for p in all_paths if is_ashare(p) and not is_post(p)]
    a_post = [p for p in all_paths if is_ashare(p) and is_post(p)]
    us_pre = [p for p in all_paths if not is_ashare(p) and not is_post(p)]
    us_post = [p for p in all_paths if not is_ashare(p) and is_post(p)]

    return [
        build_section("a-share-pre-market", "A share pre market", a_pre),
        build_section("a-share-post-market", "A share post market", a_post),
        build_section("us-pre-market", "US pre market", us_pre),
        build_section("us-post-market", "US post market", us_post),
    ]


def build_payload(args: argparse.Namespace, previous: dict | None = None) -> dict:
    news_source = args.news_htmls or args.news_html
    has_sources = any(
        [
            news_source,
            args.trading_html,
            args.trading_close_html,
            args.ashare_trading_html,
            args.ashare_trading_close_html,
        ]
    )
    if not has_sources and previous and isinstance(previous.get("report_sections"), list):
        sections = clean_report_sections(previous["report_sections"])
        scope = "accordion_report_digest_preserved_from_previous_refresh"
    else:
        sections = clean_report_sections(
            build_report_sections(
                news_source,
                args.trading_html,
                args.trading_close_html,
                args.ashare_trading_html,
                args.ashare_trading_close_html,
            )
        )
        scope = "accordion_report_digest_latest_only"

    ashare_maturity_validation = parse_ashare_maturity_validation(args.ashare_signal_html, previous)

    return {
        "ok": True,
        "published_at": datetime.now().strftime("%Y-%m-%d %H:%M local"),
        "scope": scope,
        "ashare_maturity_validation": ashare_maturity_validation,
        "ashare_signal_tracking": ashare_maturity_validation,
        "report_sections": sections,
        "briefs": [
            {
                "id": "market-news-agent",
                "market": "News Agent",
                "title": "Market News Agent",
                "updated_at": "daily after email delivery",
                "summary": "Turns macro, market, and company news into concise report digests for the public showcase.",
                "tags": ["macro context", "company catalysts", "market sentiment"],
                "bullets": [
                    "Publishes only the latest web-formatted digest by market/session.",
                    "Keeps raw feeds, prompts, sources, paths, keys, and recipient details out of the repository.",
                    "Uses collapsible sections so the homepage stays readable.",
                ],
            },
            {
                "id": "trading-recommendation-agent",
                "market": "Trading Agent",
                "title": "Trading Recommendation Agent",
                "updated_at": "daily after email delivery",
                "summary": "Publishes compact opportunity and validation summaries without exposing implementation details.",
                "tags": ["technical scan", "validation loop", "latest only"],
                "bullets": [
                    "Pre-market and post-market content is grouped into the same four market/session sections.",
                    "Only concise highlights and small table excerpts are displayed.",
                    "Core model logic, training process, private logs, and data-source details remain private.",
                ],
            },
            {
                "id": "portfolio-safe-disclosure",
                "market": "Disclosure",
                "title": "Public Boundary",
                "updated_at": "always on",
                "summary": "The page is a portfolio display layer, not a raw email archive.",
                "tags": ["showcase only", "summarized", "no secrets"],
                "bullets": [
                    "No credentials, infrastructure addresses, true local paths, raw logs, or private recipients are published.",
                    "Email reports are transformed into concise web summaries instead of copied verbatim.",
                    "Content is for system-demonstration purposes and is not financial advice.",
                ],
            },
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish concise public report digests.")
    parser.add_argument("--news-html", default=os.getenv("NEWS_AGENT_PUBLIC_SOURCE"))
    parser.add_argument("--news-htmls", default=os.getenv("NEWS_AGENT_PUBLIC_SOURCES"))
    parser.add_argument("--trading-html", default=os.getenv("TRADING_AGENT_PUBLIC_SOURCE"))
    parser.add_argument("--trading-close-html", default=os.getenv("TRADING_AGENT_CLOSE_SOURCE"))
    parser.add_argument("--ashare-trading-html", default=os.getenv("ASHARE_TRADING_AGENT_PUBLIC_SOURCE"))
    parser.add_argument("--ashare-trading-close-html", default=os.getenv("ASHARE_TRADING_AGENT_CLOSE_SOURCE"))
    parser.add_argument("--ashare-signal-html", default=os.getenv("ASHARE_SIGNAL_PUBLIC_SOURCE"))
    parser.add_argument("--output", default="data/agent-briefs.json")
    args = parser.parse_args()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    previous = None
    if output.exists():
        try:
            previous = json.loads(output.read_text(encoding="utf-8", errors="ignore"))
        except json.JSONDecodeError:
            previous = None
    payload = build_payload(args, previous)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote public report digest data to {output}")


if __name__ == "__main__":
    main()
