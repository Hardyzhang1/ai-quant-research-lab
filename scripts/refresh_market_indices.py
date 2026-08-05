#!/usr/bin/env python
"""Build a public-safe major-index performance snapshot for GitHub Pages."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import urllib.request
try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None


TENCENT_INDICES = [
    ("China", "SSE Composite", "sh000001"),
    ("China", "CSI 300", "sh000300"),
    ("Hong Kong", "Hang Seng", "hkHSI"),
    ("United States", "S&P 500", "us.INX"),
    ("United States", "Nasdaq", "us.IXIC"),
    ("United States", "Dow Jones", "us.DJI"),
]

CNBC_INDICES = {
    ".N225": ("Japan", "Nikkei 225"),
    ".FTSE": ("United Kingdom", "FTSE 100"),
    ".GDAXI": ("Germany", "DAX"),
    ".FCHI": ("France", "CAC 40"),
}

DISPLAY_ORDER = [
    "SSE Composite",
    "CSI 300",
    "Hang Seng",
    "Nikkei 225",
    "FTSE 100",
    "DAX",
    "CAC 40",
    "S&P 500",
    "Nasdaq",
    "Dow Jones",
]


def shanghai_tz() -> dt.tzinfo:
    if ZoneInfo is not None:
        try:
            return ZoneInfo("Asia/Shanghai")
        except Exception:
            pass
    return dt.timezone(dt.timedelta(hours=8), name="Asia/Shanghai")


def market_session_status(region: str, now: dt.datetime) -> str:
    """Small display-only status mirroring the email's index table intent."""
    hour = now.hour + now.minute / 60
    if region in {"China", "Hong Kong"}:
        return "Latest close" if hour >= 15.0 else "Intraday"
    if region == "Japan":
        return "Latest close" if hour >= 14.0 else "Intraday"
    if region in {"United Kingdom", "Germany", "France"}:
        return "Latest / overseas"
    if region == "United States":
        return "Latest / overnight"
    return "Latest"


def fetch_tencent(now: dt.datetime) -> list[dict]:
    lookup = {code: (region, name) for region, name, code in TENCENT_INDICES}
    url = "https://qt.gtimg.cn/q=" + ",".join(lookup)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://gu.qq.com/"})
    with urllib.request.urlopen(req, timeout=25) as response:
        payload = response.read().decode("gbk", "replace")

    rows = []
    for match in re.finditer(r'v_([^=]+)="([^"]*)";', payload):
        code, raw = match.groups()
        if code not in lookup:
            continue
        fields = raw.split("~")
        try:
            last = float(fields[3])
            previous = float(fields[4])
        except (IndexError, TypeError, ValueError):
            continue
        if last <= 0 or previous <= 0:
            continue
        region, name = lookup[code]
        rows.append({
            "region": region,
            "name": name,
            "symbol": code,
            "last": round(last, 2),
            "change_pct": round((last / previous - 1) * 100, 2),
            "status": market_session_status(region, now),
        })
    return rows


def fetch_cnbc(now: dt.datetime) -> list[dict]:
    symbols = "%7C".join(CNBC_INDICES)
    url = f"https://quote.cnbc.com/quote-html-webservice/quote.htm?symbols={symbols}&output=json"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=25) as response:
        raw_rows = json.loads(response.read()).get("QuickQuoteResult", {}).get("QuickQuote", [])

    rows = []
    for row in raw_rows:
        symbol = row.get("symbol")
        if symbol not in CNBC_INDICES:
            continue
        try:
            last = float(str(row["last"]).replace(",", ""))
            change_pct = float(str(row["change_pct"]).replace("%", ""))
        except (KeyError, TypeError, ValueError):
            continue
        region, name = CNBC_INDICES[symbol]
        rows.append({
            "region": region,
            "name": name,
            "symbol": symbol,
            "last": round(last, 2),
            "change_pct": round(change_pct, 2),
            "status": market_session_status(region, now),
        })
    return rows


def build_payload() -> dict:
    now = dt.datetime.now(shanghai_tz())
    errors = []
    rows: list[dict] = []
    for label, fn in (("tencent", fetch_tencent), ("cnbc", fetch_cnbc)):
        try:
            rows.extend(fn(now))
        except Exception as exc:  # Keep publishing briefs even if one quote source is flaky.
            errors.append(f"{label}: {exc}")

    rows = sorted(rows, key=lambda row: DISPLAY_ORDER.index(row["name"]) if row["name"] in DISPLAY_ORDER else 99)
    return {
        "ok": bool(rows),
        "published_at": now.strftime("%Y-%m-%d %H:%M:%S Asia/Shanghai"),
        "as_of": now.strftime("%Y-%m-%d"),
        "scope": "major_global_indices_latest_vs_previous_close",
        "note": "Latest level and change versus previous close. Session timing differs by market.",
        "indices": rows,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/index-performance.json")
    args = parser.parse_args()

    payload = build_payload()
    with open(args.output, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(f"Wrote {args.output} with {len(payload['indices'])} index rows.")
    return 0 if payload["indices"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
