# ONE CS Scoring Specification

## Назначение

Этот документ фиксирует рабочую бизнес-логику для двух разных итоговых метрик ONE CS. Первая метрика — **`productScore` по шкале 1–20** — отражает силу самого найденного credit profile и должна быть стабильной, простой и объяснимой. Вторая метрика — **`dataQualityScore` по шкале 1–10** — отражает практическое качество лида с учётом raw credit score, полноты анкеты и негативных факторов из adverse reasons. Таким образом, высокий raw credit score не гарантирует высокий `dataQualityScore`, если профиль тонкий, перегружен долгом, содержит делинквенции или показывает слабую пригодность для займа.

В качестве входных сигналов используются уже существующие и подтверждённые артефакты проекта и приложенного архива: `creditScore` в диапазоне `300..850`, `completenessScore` в диапазоне `0..1`, наличие ключевых полей анкеты, а также массив adverse reasons, извлечённый из Adverse Action Notice. По результатам анализа пользовательского архива уже подтверждены реальные причины, которые должны участвовать в расчёте: `Insufficient length of credit history`, `Insufficient credit history`, `Income or credit history insufficient for loan`, `Requested amount unsupported by income`, `Proportion of balances to credit limits ... is too high`, `Too many accounts with balances`, `RiskView Consumer Inquiry`, `Proportion of loan balances to loan amounts is too high`, `High debt in relation to income`, `Serious delinquency`, `Serious delinquency, and public record or collection filed`, `Number of accounts with delinquency`, `Too few accounts currently paid as agreed`, `Lack of recent installment loan information`, `Lack of recent revolving account information`, `Lack of recent bank/national revolving information`, `No recent revolving balances`, `No recent bank/national revolving balances`, `Too many inquiries last 12 months`, `High number of recent inquiries`, `Too many consumer finance company accounts`, `Insufficient number of open accounts`, `Insufficient number of accounts`, `Unable to find credit profile at TransUnion`.

## Product score 1–20

`productScore` не должен зависеть от формулировок adverse reasons. Он должен быть прямым, детерминированным преобразованием `creditScore`, чтобы пользователю и владельцу было легко сравнивать результаты между разными запусками и каналами. Для этого вводится линейное преобразование шкалы `300..850` в шкалу `1..20`.

| Поле | Правило |
|---|---|
| Вход | `creditScore: number \| null` |
| Если score отсутствует | `productScore = 1` |
| Если score присутствует | `productScore = clamp(1, 20, Math.round(((creditScore - 300) / 550) * 19) + 1)` |
| Примеры | `300 -> 1`, `575 -> 10`, `650 -> 13`, `720 -> 15`, `780 -> 18`, `850 -> 20` |

Такой подход отделяет собственно силу кредитного профиля от пригодности лида для бизнес-использования. Все adverse reasons при этом влияют не на `productScore`, а на `dataQualityScore`.

## Data quality 1–10

`dataQualityScore` должен быть итоговой практической оценкой качества лида. Базой для него является не только raw credit score, но и полнота записи, а также тяжесть adverse reasons. Формула строится так, чтобы профиль с хорошим credit score, но серьёзными отрицательными факторами, опускался в среднюю или низкую зону, а аккуратный профиль без тяжёлых негативных сигналов поднимался выше.

Базовая оценка определяется по raw credit score, затем корректируется на полноту записи, после чего уменьшается на сумму штрафов по adverse reasons. Итоговая оценка всегда ограничивается диапазоном `1..10` и округляется до одного знака после запятой.

### 1. Базовое качество по raw credit score

| Диапазон credit score | Базовый `dataQualityScore` |
|---|---:|
| `800–850` | 9.7 |
| `760–799` | 9.0 |
| `720–759` | 8.2 |
| `680–719` | 7.4 |
| `640–679` | 6.5 |
| `600–639` | 5.5 |
| `560–599` | 4.5 |
| `520–559` | 3.5 |
| `480–519` | 2.5 |
| `< 480` | 1.5 |
| score отсутствует | 2.0 |

### 2. Коррекция по полноте записи

`completenessScore` уже существует в текущем TypeScript-проекте и считается по наличию адреса, возраста, DOB, email, телефонов, credit score и SSN. Эта величина должна использоваться как мягкая корректировка, а не как замена итоговой оценки.

| Условие | Коррекция |
|---|---:|
| `completenessScore >= 0.95` | `+0.8` |
| `0.80–0.94` | `+0.5` |
| `0.65–0.79` | `+0.2` |
| `0.50–0.64` | `0.0` |
| `0.35–0.49` | `-0.5` |
| `< 0.35` | `-1.0` |

### 3. Штрафы по группам adverse reasons

Adverse reasons сначала нормализуются в группы. Затем суммируются штрафы, но общий штраф ограничивается потолком `6.5`, чтобы даже очень плохие профили не уходили ниже искусственного минимума быстрее, чем нужно.

| Группа | Входящие причины | Штраф |
|---|---|---:|
| `no_file` | `Unable to find credit profile at TransUnion` | 5.0 |
| `thin_file` | `Insufficient credit history`, `Insufficient length of credit history`, `Insufficient number of accounts`, `Insufficient number of open accounts` | 2.2 |
| `low_depth` | `Lack of recent installment loan information`, `Lack of recent revolving account information`, `Lack of recent bank/national revolving information`, `No recent revolving balances`, `No recent bank/national revolving balances`, `Too few accounts currently paid as agreed` | 1.4 |
| `affordability` | `Income or credit history insufficient for loan`, `Requested amount unsupported by income`, `High debt in relation to income`, `Proportion of loan balances to loan amounts is too high` | 2.0 |
| `utilization` | `Proportion of balances to credit limits on bank/national revolving or other revolving accounts is too high`, `Too many accounts with balances` | 1.6 |
| `delinquency` | `Serious delinquency`, `Number of accounts with delinquency`, `Time since delinquency is too recent or unknown` | 2.4 |
| `public_record` | `Serious delinquency, and public record or collection filed` | 3.2 |
| `inquiry_pressure` | `RiskView Consumer Inquiry`, `Too many inquiries last 12 months`, `High number of recent inquiries` | 1.0 |
| `consumer_finance` | `Too many consumer finance company accounts` | 0.8 |

### 4. Правила агрегации

Итоговая формула должна рассчитываться так:

| Шаг | Правило |
|---|---|
| 1 | `baseQuality = scoreBandValue(creditScore)` |
| 2 | `completenessAdjustment = completenessBandValue(completenessScore)` |
| 3 | `penalty = min(6.5, sum(uniqueReasonGroupPenalties))` |
| 4 | `bonus = 0.3`, если adverse reasons нет и `creditScore >= 720` |
| 5 | `dataQualityScore = clamp(1, 10, round1(baseQuality + completenessAdjustment + bonus - penalty))` |

Если adverse reason несколько раз повторяется в одном результате, он должен учитываться только один раз. Если в результате есть одновременно `public_record` и `delinquency`, оба штрафа допускаются, потому что они отражают разную тяжесть риска. Если пришёл `no_file`, итог всё равно рассчитывается, но почти всегда попадает в диапазон `1.0–2.0`.

## Бизнес-интерпретация диапазонов 1–10

| Диапазон | Интерпретация |
|---|---|
| `9.0–10.0` | Очень сильный и пригодный профиль: высокий score, полные данные, без существенных отрицательных факторов |
| `7.0–8.9` | Хороший рабочий профиль: пригоден для премиальной выдачи, но может иметь отдельные умеренные adverse signals |
| `5.0–6.9` | Средний профиль: usable, но требует осторожной интерпретации и не должен позиционироваться как сильный |
| `3.0–4.9` | Слабый профиль: есть заметные ограничения по долгу, глубине истории или affordability |
| `1.0–2.9` | Низкое качество: thin file, no file, тяжёлые delinquency/public record или серьёзная неполнота данных |

## Контракт результата ONE CS

Финальный серверный объект результата должен быть единым и одинаково использоваться в backend, UI, экспортах и админке.

| Поле | Тип | Назначение |
|---|---|---|
| `creditScore` | `number \| null` | Raw bureau score `300..850` |
| `productScore` | `number` | Итог по шкале `1..20` |
| `dataQualityScore` | `number` | Итог по шкале `1.0..10.0` |
| `adverseReasons` | `string[]` | Список нормализованных причин |
| `adverseReasonGroups` | `string[]` | Нормализованные группы штрафов |
| `status` | `success \| review \| decline \| no_file \| error` | Бизнес-статус результата |
| `priceUsd` | `number` | Цена конкретного запроса |
| `durationMs` | `number` | Длительность выполнения |
| `source` | `dashboard \| api \| telegram \| import` | Источник запроса |
| `explanations` | `string[]` | Короткие текстовые объяснения, почему результат получил такой quality |

## Правила статуса результата

| Условие | Статус |
|---|---|
| `creditScore === null` и найден `no_file` | `no_file` |
| `dataQualityScore >= 7.5` | `success` |
| `dataQualityScore >= 4.5 && dataQualityScore < 7.5` | `review` |
| `dataQualityScore < 4.5` | `decline` |
| Ошибка обработки/парсинга | `error` |

## Порядок внедрения

Сначала новая модель должна быть добавлена в shared-типизацию и серверный слой расчёта. Затем она должна появиться в mock-данных, safe flows, REST-ответах, bot-like пользовательском интерфейсе и в админских таблицах Jobs, Overview и exports. После этого потребуется покрыть логику Vitest-тестами на уровне `platformService`, `importedLeadFormat` и REST-слоя.
