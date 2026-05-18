#!/usr/bin/env python3
import json
import re
from pathlib import Path

ROOT = Path('/home/ubuntu/csbot_admin_system')
SCORING_FILE = ROOT / 'shared' / 'oneCsScoring.ts'
ANALYSIS_FILE = ROOT / 'user_attachment' / 'adverse_analysis.json'
OUTPUT_FILE = ROOT / 'user_attachment' / 'adverse_mapping_matrix.md'

source = SCORING_FILE.read_text(encoding='utf-8')
analysis = json.loads(ANALYSIS_FILE.read_text(encoding='utf-8'))

entry_pattern = re.compile(
    r'\{\s*\n\s*pattern:\s*/(.*?)/i,\s*\n\s*normalized:\s*"(.*?)",\s*\n\s*group:\s*"(.*?)"',
    re.S,
)
penalty_pattern = re.compile(r'\b([a-z_]+):\s*([0-9]+(?:\.[0-9]+)?)', re.M)

entries = []
for pattern, normalized, group in entry_pattern.findall(source):
    entries.append({
        'regex': pattern,
        'normalized': normalized,
        'group': group,
    })

penalties = {}
penalty_block_match = re.search(r'const GROUP_PENALTIES:.*?= \{(.*?)\n\};', source, re.S)
if penalty_block_match:
    for group, penalty in penalty_pattern.findall(penalty_block_match.group(1)):
        penalties[group] = penalty

rows = []
unmatched = []
for item in analysis['reasons']:
    reason = item['reason']
    count = item['count']
    matched = None
    for entry in entries:
        if re.search(entry['regex'], reason, re.I):
            matched = entry
            break
    if matched is None:
        unmatched.append(reason)
        rows.append((reason, count, 'NO', '—', '—', '—'))
    else:
        rows.append((
            reason,
            count,
            'YES',
            matched['normalized'],
            matched['group'],
            penalties.get(matched['group'], '—'),
        ))

lines = []
lines.append('# ONE CS Adverse Reason Mapping Matrix\n')
lines.append(f'Проверено файлов: **{analysis["file_count"]}**. Уникальных причин: **{analysis["unique_reason_count"]}**.\n')
lines.append('## Coverage Summary\n')
lines.append(f'- Covered reasons: **{len(rows) - len(unmatched)} / {len(rows)}**\n')
lines.append(f'- Unmatched reasons: **{len(unmatched)}**\n')
if unmatched:
    lines.append('- Unmatched list: ' + ', '.join(f'`{x}`' for x in unmatched) + '\n')
else:
    lines.append('- Все извлечённые причины покрыты текущим mapping-модулем `shared/oneCsScoring.ts`.\n')

lines.append('## Mapping Table\n')
lines.append('| Extracted reason | Count | Covered | Normalized reason | Reason group | Penalty |\n')
lines.append('|---|---:|---|---|---|---:|\n')
for reason, count, covered, normalized, group, penalty in rows:
    safe_reason = reason.replace('|', '\\|')
    safe_normalized = normalized.replace('|', '\\|') if normalized != '—' else normalized
    lines.append(f'| {safe_reason} | {count} | {covered} | {safe_normalized} | {group} | {penalty} |\n')

OUTPUT_FILE.write_text(''.join(lines), encoding='utf-8')
print(str(OUTPUT_FILE))
