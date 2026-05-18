# ONE CS Adverse Reason Coverage

## Confirmed input coverage

По пользовательскому архиву было проанализировано **52 файла Adverse Action Notice** и извлечено **25 уникальных adverse reasons**. Автоматическая сверка с текущим модулем `shared/oneCsScoring.ts` подтвердила покрытие **25 из 25** причин без непокрытых случаев.

## Confirmed mapping status

| Metric | Value |
|---|---:|
| Files analyzed | 52 |
| Unique adverse reasons | 25 |
| Covered by current mapping | 25 |
| Unmatched reasons | 0 |

## Data quality model used in ONE CS

Текущая модель `dataQualityScore 1–10` строится как комбинированная оценка из трёх слоёв. Сначала берётся базовое качество из raw credit score `300–850`. Затем применяется поправка на `completenessScore` импортированной записи. После этого суммируются штрафы по группам adverse reasons, при этом итоговый штраф ограничивается сверху.

| Layer | Role in score |
|---|---|
| Credit score baseline | Даёт базовый уровень качества от низкого к высокому |
| Completeness adjustment | Корректирует уверенность в результате по полноте анкеты |
| Adverse reason penalties | Снижает итог по смысловым группам риска |

## Penalty groups

| Group | Penalty |
|---|---:|
| `no_file` | 5.0 |
| `thin_file` | 2.2 |
| `low_depth` | 1.4 |
| `affordability` | 2.0 |
| `utilization` | 1.6 |
| `delinquency` | 2.4 |
| `public_record` | 3.2 |
| `inquiry_pressure` | 1.0 |
| `consumer_finance` | 0.8 |

## Important conclusion

Подтверждено, что присланные пользователем adverse reasons полностью покрывают текущую матрицу нормализации и группировки. Это означает, что аналитическая часть шкалы `dataQualityScore 1–10` уже имеет подтверждённую входную базу и может считаться финализированной для дальнейшего системного внедрения в backend, UI, exports и серверное развёртывание.

## Related files

| Purpose | Path |
|---|---|
| Full extracted reason stats | `/home/ubuntu/csbot_admin_system/user_attachment/adverse_analysis.md` |
| Machine-readable extracted dataset | `/home/ubuntu/csbot_admin_system/user_attachment/adverse_analysis.json` |
| Coverage matrix | `/home/ubuntu/csbot_admin_system/user_attachment/adverse_mapping_matrix.md` |
| Current scoring implementation | `/home/ubuntu/csbot_admin_system/shared/oneCsScoring.ts` |
