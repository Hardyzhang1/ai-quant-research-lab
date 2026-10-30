"""Read the public calendar summary from the existing private mail service."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path


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
