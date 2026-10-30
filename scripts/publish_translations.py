"""Attach locally authored translations. No network, model calls or credentials."""
from __future__ import annotations
import json
from pathlib import Path
import re

def visible_excerpts(payload: dict) -> list[str]:
    strings = []
    def walk(value):
        if isinstance(value, list):
            for item in value: walk(item)
        elif isinstance(value, str) and re.search(r'[A-Za-z\u4e00-\u9fff]', value):
            if not re.fullmatch(r'\d{6}\.(?:XSHG|XSHE)|[A-Z]{1,6}', value): strings.append(value)
    for section in payload.get('report_sections', []):
        for report in section.get('reports', []):
            walk(report.get('title', ''))
            walk(report.get('highlights', []))
            for table in report.get('tables', []):
                walk(table.get('headers', [])); walk(table.get('rows', []))
    return list(dict.fromkeys(strings))

def add_local_translations(payload: dict) -> None:
    wanted = visible_excerpts(payload)
    try:
        path = Path(__file__).resolve().parents[1] / 'data' / 'digest-translations.json'
        catalog = json.loads(path.read_text(encoding='utf-8'))
        pairs = {source: catalog[source] for source in wanted if source in catalog
                 and isinstance(catalog[source], dict)
                 and all(isinstance(catalog[source].get(lang), str) and catalog[source][lang].strip() for lang in ('zh','en'))}
    except (OSError, ValueError, TypeError):
        pairs = {}
    payload['localized_text'] = pairs
    payload['translation_status'] = {'mode': 'local_only', 'total': len(wanted),
        'translated': len(pairs), 'complete': len(wanted) == len(pairs)}
