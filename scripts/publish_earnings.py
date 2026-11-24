"""Publish current earnings through the shared cached, multi-source calendar service."""
from __future__ import annotations
import argparse
import datetime as dt
import importlib.util
import json
import os
from pathlib import Path
import sys
import uuid

PUBLIC_PATH = Path(__file__).resolve().parents[1] / "data" / "agent-briefs.json"


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name('.' + path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def earnings_module():
    default = Path(__file__).resolve().parents[2] / 'technical-analysis-agent' / 'us_earnings_calendar.py'
    path = Path(os.getenv('US_EARNINGS_MODULE') or default)
    sys.path.insert(0, str(path.parent))
    try:
        spec = importlib.util.spec_from_file_location('showcase_earnings_source', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def build_earnings_snapshot(path=None, *, module=None, now=None):
    """Every existing publication may recover a failed calendar; shared TTL/cooldown bounds requests."""
    try:
        module = module or earnings_module()
        return module.build_public_snapshot(now=now)
    except Exception:
        # Never freeze a weeks-old failure as if it were the latest check.
        return {'status': 'unavailable', 'checked_at': (now or dt.datetime.now(dt.timezone.utc)).isoformat(),
                'market_date': None, 'limit': 10, 'companies': []}


def publish_snapshot(path, snapshot):
    payload = read_json(path)
    old = payload.get('us_upcoming_earnings') or {}
    if snapshot.get('market_date') and (old.get('market_date') or '') > snapshot['market_date']:
        raise ValueError('Refusing an older calendar event')
    payload['us_upcoming_earnings'] = snapshot
    write_json(path, payload)


def refresh_published_earnings(path, *, close_date, now=None, state_dir=None, module=None, target_day=None):
    module = module or earnings_module()
    now = now or dt.datetime.now(module.NY)
    close_day = dt.date.fromisoformat(close_date)
    if now.tzinfo is None or now < module.release_window_start(close_day):
        raise ValueError('US close has not completed')
    day = target_day or module.public_session_date(module.release_window_start(close_day))
    if day <= close_day:
        raise ValueError('Target must follow completed US session')
    if now >= module.release_window_start(day):
        return {'state': 'expired_event_skipped', 'target': day.isoformat()}
    snapshot = build_earnings_snapshot(module=module, now=now)
    if snapshot.get('market_date') != day.isoformat():
        raise ValueError('Calendar target mismatch')
    snapshot.update(trigger='after_us_close_email', close_market_date=close_date)
    publish_snapshot(path, snapshot)
    result = {'state': 'validated' if snapshot['status'] in ('ready', 'empty') else 'temporarily_unavailable',
              'target': day.isoformat(), 'checked_at': now.isoformat(), 'snapshot': snapshot}
    folder = Path(state_dir) if state_dir else module.default_cache_dir() / 'web_refresh_v2'
    write_json(folder / (close_date + '.json'), result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--after-us-close', required=True)
    parser.add_argument('--output', type=Path, default=PUBLIC_PATH)
    args = parser.parse_args()
    result = refresh_published_earnings(args.output, close_date=args.after_us_close)
    print(json.dumps({k: v for k, v in result.items() if k != 'snapshot'}))
