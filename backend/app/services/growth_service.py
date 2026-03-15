from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

BASE_DIR = Path(__file__).resolve().parents[5]
BACKLOG_PATH = BASE_DIR / 'projects' / 'claw-evolution-backlog.json'
REPORT_PATH = BASE_DIR / 'projects' / 'claw-growth-report.md'
LOG_PATH = BASE_DIR / 'projects' / 'claw-evolution-log.md'


def load_backlog() -> Dict[str, Any]:
    return json.loads(BACKLOG_PATH.read_text(encoding='utf-8'))


def get_growth_summary() -> Dict[str, Any]:
    backlog = load_backlog().get('items', [])
    open_proposals = [x for x in backlog if x.get('status') == 'proposed']
    implemented = [x for x in backlog if x.get('status') == 'implemented']
    best = open_proposals[0] if open_proposals else (implemented[0] if implemented else None)
    return {
        'signal': 'high' if len(open_proposals) >= 3 else ('medium' if open_proposals else 'low'),
        'openProposals': len(open_proposals),
        'implemented': len(implemented),
        'bestNextMove': {
            'title': best.get('title'),
            'type': best.get('type'),
            'complexity': best.get('complexity'),
        } if best else None,
    }


def get_growth_proposals() -> List[Dict[str, Any]]:
    return load_backlog().get('items', [])


def get_growth_timeline() -> List[Dict[str, Any]]:
    if not LOG_PATH.exists():
        return []
    lines = LOG_PATH.read_text(encoding='utf-8').splitlines()
    items: List[Dict[str, Any]] = []
    current = None
    for line in lines:
        if line.startswith('### '):
            if current:
                items.append(current)
            current = {'title': line.replace('### ', '').strip(), 'details': []}
        elif current and line.strip().startswith('- '):
            current['details'].append(line.strip()[2:])
    if current:
        items.append(current)
    return items


def get_growth_report() -> Dict[str, Any]:
    text = REPORT_PATH.read_text(encoding='utf-8') if REPORT_PATH.exists() else ''
    return {
        'path': str(REPORT_PATH),
        'content': text,
    }
