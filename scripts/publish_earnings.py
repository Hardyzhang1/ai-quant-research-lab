"""Read the public calendar summary from the existing private mail service."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import uuid


def build_earnings_snapshot() -> dict:
    try:
        default = Path(__file__).resolve().parents[2] / "technical-analysis-agent" / "us_earnings_calendar.py"
        source = Path(os.getenv("US_EARNINGS_MODULE") or default)
        spec = importlib.util.spec_from_file_location("showcase_earnings_source", source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.build_public_snapshot()
    except Exception:
        # A calendar failure must not interrupt publication of other market digests.
        return {"status": "unavailable", "limit": 10, "companies": []}


def refresh_published_earnings(path: Path) -> None:
    """Replace just the public calendar, retaining the dates of the other reports."""
    snapshot = build_earnings_snapshot()
    if snapshot.get("status") not in {"ready", "empty"}:
        raise RuntimeError("Earnings calendar unavailable. Retry the close refresh.")
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    payload["us_upcoming_earnings"] = snapshot
    temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temp.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)
    print(f"Earnings {snapshot['market_date']}: {len(snapshot['companies'])} companies")


if __name__ == "__main__":
    refresh_published_earnings(Path(__file__).resolve().parents[1] / "data" / "agent-briefs.json")
