from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

BASE_DIR = Path('/home/ubuntu/csbot_admin_system/user_attachment/extracted/ved/txt')
OUT_JSON = Path('/home/ubuntu/csbot_admin_system/user_attachment/adverse_analysis.json')
OUT_MD = Path('/home/ubuntu/csbot_admin_system/user_attachment/adverse_analysis.md')

SCORE_RE = re.compile(r'Your credit score:\s*(\d{3})', re.I)

REASON_PATTERNS = [
    r'Insufficient length of credit history',
    r'Insufficient credit history',
    r'Income or credit history insufficient for loan',
    r'Requested amount unsupported by income',
    r'Proportion of balances to credit limits on bank/national revolving or other revolving accounts is too high',
    r'Too many accounts with balances',
    r'RiskView Consumer Inquiry',
    r'Proportion of loan balances to loan amounts is too high',
    r'Number of accounts with delinquency',
    r'Lack of recent installment loan information',
    r'High debt in relation to income',
    r'Serious delinquency, and public record or collection filed',
    r'Serious delinquency, public record, or collection filed',
    r'Serious delinquency',
    r'Lack of recent revolving account information',
    r'Time since delinquency is too recent or unknown',
    r'Lack of recent bank/national revolving information',
    r'Too many inquiries last 12 months',
    r'No recent bank/national revolving balances',
    r'No recent revolving balances',
    r'Unable to find credit profile at TransUnion',
    r'Too many consumer finance company accounts',
    r'Insufficient number of open accounts',
    r'Insufficient number of accounts',
    r'High number of recent inquiries',
    r'Derogatory public record or collection filed',
    r'Too few accounts currently paid as agreed',
]

reason_regexes = [re.compile(p, re.I) for p in REASON_PATTERNS]


def normalize_reason(reason: str) -> str:
    text = re.sub(r'\s+', ' ', reason).strip().rstrip('.')
    replacements = {
        'Serious delinquency, public record, or collection filed': 'Serious delinquency, and public record or collection filed',
        'Derogatory public record or collection filed': 'Serious delinquency, and public record or collection filed',
    }
    return replacements.get(text, text)


records = []
reason_counter = Counter()
score_counter = Counter()

for txt_path in sorted(BASE_DIR.glob('*.txt')):
    text = txt_path.read_text(encoding='utf-8', errors='ignore')
    score_match = SCORE_RE.search(text)
    score = int(score_match.group(1)) if score_match else None
    reasons = []
    for rx in reason_regexes:
        for match in rx.finditer(text):
            reason = normalize_reason(match.group(0))
            if reason not in reasons:
                reasons.append(reason)
    if score is not None:
        score_counter[score] += 1
    for reason in reasons:
        reason_counter[reason] += 1
    records.append(
        {
            'file': txt_path.name,
            'score': score,
            'reasons': reasons,
            'reason_count': len(reasons),
        }
    )

payload = {
    'file_count': len(records),
    'unique_reason_count': len(reason_counter),
    'reasons': [{'reason': reason, 'count': count} for reason, count in reason_counter.most_common()],
    'scores': [{'score': score, 'count': count} for score, count in sorted(score_counter.items())],
    'records': records,
}
OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

lines = []
lines.append('# Adverse PDF analysis')
lines.append('')
lines.append(f'- Files analyzed: {len(records)}')
lines.append(f'- Unique reasons found: {len(reason_counter)}')
lines.append('')
lines.append('## Top reasons')
lines.append('')
lines.append('| Reason | Count |')
lines.append('|---|---:|')
for reason, count in reason_counter.most_common():
    lines.append(f'| {reason} | {count} |')
lines.append('')
lines.append('## Scores')
lines.append('')
lines.append('| Score | Count |')
lines.append('|---|---:|')
for score, count in sorted(score_counter.items()):
    lines.append(f'| {score} | {count} |')
OUT_MD.write_text('\n'.join(lines) + '\n', encoding='utf-8')

print(str(OUT_JSON))
print(str(OUT_MD))
