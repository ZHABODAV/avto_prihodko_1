# Структура Данных и Таблицы Модели Терминала

---

## 1. ВХОДНЫЕ ТАБЛИЦЫ (что вводит пользователь)

### Таблица 1.1: Vessels (Расписание судов)

| vessel_id    | eta              | cargo_type | total_volume | demurrage_rate | strategic_weight | notes |
|:----------   |:----             |:-----------|:------------:|:---------------|:-----------------|:------|
| Victoria_001 | 2024-10-15 14:00 | palm       | 28500        | 100000         | 2.0              |       |
| Atlantic_002 | 2024-10-18 08:00 | sunflower  | 35000        | 90000          | 1.0              |       |

**Связанная таблица 1.1.1: Cargo Plan {H}** (для каждого судна с пальмой)

| vessel_id    | hold_id | fraction     | volume |
|:----------   |:--------|:---------    |:------:|
| Victoria_001 | H1      | Palm Oil     | 12000  |
| Victoria_001 | H2      | Palm Oil     | 8000   |
| Victoria_001 | H3      | Olein        | 3000   |
| Victoria_001 | H4      | Stearin      | 2500   |
| Victoria_001 | H5      | Olein        | 1500   |
| Victoria_001 | H6      | PFAD         | 800    |
| Victoria_001 | H7      | Low3MCPD Oil | 700    |

---

### Таблица 1.2: Rail Schedule (График ж/д подач подсолнечника)

| date       | time  | wagons | source         | notes     |
|:-----      |:----- |:------:|:-------        |:------    |
| 2024-10-10 | 08:00 | 18     | own_production | Завод A   |
| 2024-10-10 | 14:00 | 18     | own_production | Завод A   |
| 2024-10-10 | 20:00 | 18     | trading        | Трейдер B |
| 2024-10-11 | 02:00 | 18     | trading        | Трейдер B |

---

### Таблица 1.3: Client Demand Matrix (Матрица заявок на пальму)

| week | client_id | client_name    | product  | volume | priority | penalty_rate |
|:-----|:----------|:------------   |:-------- |:------:|:--------:|:------------:|
| 42   | CLI_001   | Завод Масложир | Olein    | 2000   | HIGH     | 10000        |
| 42   | CLI_001   | Завод Масложир | Stearin  | 500    | HIGH     | 10000        |
| 42   | CLI_002   | Трейдер АБВ    | Palm Oil | 5000   | MEDIUM   | 1000         |
| 43   | CLI_001   | Завод Масложир | Olein    | 1500   | HIGH     | 10000        |

---

### Таблица 1.4: Current Inventory (Текущее состояние РВС)

| tank_id | current_volume | current_product | state | state_entry_time | temperature |
|:--------|:-------------:|:----------------|:------|:-----------------|:-----------:|
| RVS_1 | 8500 | Sunflower | available | - | - |
| RVS_2 | 9900 | Sunflower | analysis | 2024-10-09 10:00 | - |
| RVS_3 | 0 | None | idle | - | - |
| RVS_5 | 2700 | Palm Olein | discharging | 2024-10-09 18:00 | 35 |
| ШТ | 0 | None | idle | - | - |

---

### Таблица 1.5: Parameters (Настройки)

| parameter | value | unit | notes |
|:----------|:------|:-----|:------|
| season | winter | - | Влияет на rail_rate и berth_shift_time |
| rail_discharge_rate | 146 | т/ч | 3×18×65/24 для зимы |
| ship_load_rate_min | 500 | т/ч | Минимум |
| ship_load_rate_max | 900 | т/ч | Максимум |
| ship_discharge_line1 | 900 | т/ч | В большой бак |
| ship_discharge_line2_tank | 500 | т/ч | В ШТ |
| ship_discharge_line2_direct | 146 | т/ч | Прямо в ЖДЦ |
| wagon_prep_time | 1.5 | hours | Preparation после слива |
| wagon_reject_rate | 0.12 | - | 12% отбраковываются |
| berth_shift_time | 3.0 | hours | Зима |
| cleaning_time_standard | 48 | hours | Sun↔Palm |
| cleaning_time_full | 72 | hours | Для Low3MCPD |
| analysis_time | 72 | hours | - |

---

### Таблица 1.6: Economic Parameters

| parameter | value | unit |
|:----------|:-----:|:----:|
| wagon_own_cost | 3000 | руб/сутки |
| wagon_external_cost | 50000 | руб/вагон (с доставкой) |
| batch_extra_penalty | 50000 | руб (за 5-ю подачу) |

---

### Таблица 1.7: Fleet & Lead Times

| parameter | value | unit |
|:----------|:-----:|:-----|
| total_wagon_fleet | 500 | вагонов |
| leadtime_production_in | 3 | дней |
| leadtime_trading_in | 5 | дней |
| leadtime_client_A_out | 5 | дней |
| leadtime_client_B_out | 12 | дней |
| leadtime_return | 2 | дней |

---

### Таблица 1.8: Historical Delays (для Markov калибровки)

| route | departure_date | arrival_date | delay_days | reason |
|:------|:--------------|:-------------|:----------:|:-------|
| Own_Prod→Terminal | 2024-09-01 | 2024-09-04 | 0 | - |
| Own_Prod→Terminal | 2024-09-05 | 2024-09-09 | 1 | Congestion |
| Terminal→Client_A | 2024-09-10 | 2024-09-16 | 1 | Weather |
| ... | ... | ... | ... | ... |

(Минимум 100-200 записей для статистической значимости)

---

## 2. СПРАВОЧНЫЕ ТАБЛИЦЫ (системные константы)

### Таблица 2.1: Tank Configuration

| tank_id | capacity | allowed_products | is_swing | deadstock |
|:--------|:--------:|:-----------------|:--------:|:---------:|
| RVS_1 | 9900 | sunflower | No | 0.10 |
| RVS_2 | 9900 | sunflower | No | 0.10 |
| RVS_3 | 9900 | palm_* | No | 0.15 |
| RVS_5 | 2700 | sunflower, palm_* | Yes | 0.10 |
| ШТ | 2700 | palm_* | No | 0.10 |

---

### Таблица 2.2: Product Compatibility Matrix

| from_product | to_product | compatible | cleaning_hours |
|:-------------|:-----------|:----------:|:--------------:|
| Sunflower | Sunflower | Yes | 0 |
| Sunflower | Palm Oil | No | 48 |
| Sunflower | Palm Olein | No | 48 |
| Sunflower | Low3MCPD | No | 72 |
| Palm Oil | Palm Olein | Yes (same family) | 12 |
| Palm Olein | Palm Stearin | Partial | 12 |
| Low3MCPD | Standard | No | 168 |

---

### Таблица 2.3: Operation Time Standards

| operation_type | min_hours | typical_hours | max_hours | dependencies |
|:---------------|:---------:|:-------------:|:---------:|:-------------|
| Berthing | 24 | 48 | 168 | None |
| Unberthing | 2 | 4 | 8 | All ops complete |
| Tank_Fill_Large | 8 | 12 | 20 | Tank available |
| Tank_Fill_Small | 4 | 6 | 10 | Tank available |
| Tank_Discharge | 6 | 10 | 16 | Analysis passed |
| Ship_Load | 24 | 40 | 60 | Stock available |
| Ship_Discharge | 20 | 36 | 55 | Tank available |
| Cleaning | 48 | 60 | 168 | Tank empty |
| Analysis | 72 | 72 | 96 | Settling complete |
| Rail_Batch | 5 | 6.5 | 10 | Wagons available |

---

### Таблица 2.4: Palm Fraction Priorities (из CSV п.3.2)

| sequence | fraction_name | typical_volume_range | line_preference |
|:--------:|:--------------|:--------------------:|:----------------|
| 1 | Palm Olein Low3MCPD | <10% партии | Line2 → ШТ |
| 2 | Palm Olein | 10-20% | Line2 → ШТ or Direct |
| 3 | Palm Oil Low3MCPD | <10% | Line1 → RVS-5 |
| 4 | Palm Oil | >50% | Line1 → RVS-3,5 |
| 5 | Palm Stearin | 10-20% | Line2 |
| 6 | Кокосовое масло | <10% | Line2 |
| 7 | Пальмоядровое | <10% | Line2 |
| 8 | PFAD | <10% | Line2 → Direct |

---

## 3. РАСЧЕТНЫЕ ТАБЛИЦЫ (генерируются моделью)

### Таблица 3.1: Generated Operations Sequence

| op_id | vessel_id | op_type | product | source | target | volume | start_time | duration | end_time | line |
|:------|:----------|:--------|:--------|:-------|:-------|:------:|:-----------|:---------|:---------|:-----|
| OP001 | Victoria | Berthing | - | Sea | Berth_Palm | - | 2024-10-15 14:00 | 24h | 2024-10-16 14:00 | - |
| OP002 | Victoria | Discharge | Palm Oil | H1,H2 | RVS_3 | 12000 | 2024-10-16 14:00 | 13.3h | 2024-10-17 03:20 | Line1 |
| OP003 | Victoria | Discharge | Olein | H3 | ШТ | 3000 | 2024-10-16 14:00 | 6h | 2024-10-16 20:00 | Line2 |
| OP004 | Victoria | - | - | ШТ | Rail | 3000 | 2024-10-16 21:00 | 20.5h | 2024-10-17 17:30 | - |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |

**Примечания к столбцам:**

- `line` - какая линия пальмы (для судов с пальмой)
- `source/target` - откуда/куда
- операции могут быть parallel (одинаковый start_time на разных lines)

---

### Таблица 3.2: Tank Balances (почасовой баланс)

| hour | date_time | RVS_1_in | RVS_1_out | RVS_1_balance | RVS_2_in | RVS_2_out | RVS_2_balance | RVS_3_in | RVS_3_out | RVS_3_balance | RVS_5_in | RVS_5_out | RVS_5_balance | ШТ_in | ШТ_out | ШТ_balance | total |
|:----:|:----------|:--------:|:---------:|:-------------:|:--------:|:---------:|:-------------:|:--------:|:---------:|:-------------:|:--------:|:---------:|:-------------:|:-----:|:------:|:----------:|:-----:|
| 0 | 2024-10-15 00:00 | 0 | 0 | 8500 | 0 | 0 | 9900 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 18400 |
| 1 | 2024-10-15 01:00 | 195 | 0 | 8695 | 0 | 0 | 9900 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 18595 |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |

**Формат как в вашем CSV** - баланс приход/расход/остаток для каждого бака.

---

### Таблица 3.3: Wagon Balance (баланс вагонов)

| day | batch_id | operation | product | wagons_arrived | wagons_discharged | wagons_to_prepare | wagons_ready | wagons_loaded | wagons_departed | wagons_on_site |
|:----|:---------|:----------|:--------|:--------------:|:-----------------:|:-----------------:|:------------:|:-------------:|:---------------:|:--------------:|
| 2024-10-15 | B1 | Discharge Sun | Sunflower | 18 | 18 | 18 | 0 | 0 | 0 | 18 |
| 2024-10-15 | B2 | Discharge Sun | Sunflower | 18 | 18 | 36 | 0 | 0 | 0 | 36 |
| 2024-10-15 | - | Prepare | - | 0 | 0 | 0 | 31 | 0 | 0 | 36 |
| 2024-10-15 | B3 | Load Palm | Olein | 0 | 0 | 0 | 31 | 18 | 0 | 36 |
| 2024-10-16 | B4 | Depart | Olein | 0 | 0 | 0 | 13 | 18 | 18 | 18 |

**Логика столбцов:**

- `wagons_to_prepare` = cumulative грязных вагонов после слива подсолнечника
- `wagons_ready` = wagons_to_prepare × (1 - reject_rate) после T_prep часов
- отслеживает looping: слили подсолнечник → готовы под пальму

---

### Таблица 3.4: Resource Gantt (занятость ресурсов)

| resource_id | hour_0 | hour_1 | hour_2 | ... | hour_720 |
|:------------|:------:|:------:|:------:|:---:|:--------:|
| Berth_Palm | - | - | Victoria | Victoria | Victoria |
| Berth_Sun | - | - | - | Atlantic | Atlantic |
| RVS_1 | Idle | Filling | Filling | Full | Discharging |
| RVS_3 | Idle | Idle | Receiving | Full | Full |
| ШТ | Idle | Receiving | Full | Discharging | Idle |
| Rail_Platform | Batch_Sun | Idle | Batch_Palm | Batch_Palm | Idle |
| Line1 | - | Active | Active | Idle | - |
| Line2 | - | →ШТ | ШТ→Rail | Direct | - |

**Визуальный формат** - для Gantt chart генерации.

---

## 4. ПРОМЕЖУТОЧНЫЕ РАСЧЕТНЫЕ ТАБЛИЦЫ

### Таблица 4.1: Flow Distribution (распределение потоков)

| hour | source | destination | product | flow_rate | volume_cumulative | operation_id |
|:-----|:-------|:-----------|:--------|:---------:|:-----------------:|:-------------|
| 14 | Rail | RVS_1 | Sunflower | 195 | 195 | OP_Rail_001 |
| 15 | Rail | RVS_1 | Sunflower | 195 | 390 | OP_Rail_001 |
| 38 | RVS_1 | Ship | Sunflower | 700 | 700 | OP_Load_Sun_001 |
| 38 | Rail | Ship | Sunflower | 195 | 895 | OP_Direct_001 |
| 39 | RVS_1 | Ship | Sunflower | 700 | 1400 | OP_Load_Sun_001 |
| 39 | Rail | Ship | Sunflower | 0 | 1400 | - |

**Показывает:**

- Откуда куда идет поток в каждый час
- Direct variant отдельной строкой (Rail → Ship)
- Cumulative volume для tracking

---

### Таблица 4.2: Constraint Violations Check

|hour| constraint_type|resource|violation|severity|details|
|:-----|:----------------|:---------|:----------|:---------|:--------|
|45|Capacity|RVS_3|Overfill attempt|ERROR|Tried to add 1200т, only 900т space |
| 72 | Resource conflict | Rail_Platform | Overlap | ERROR | Batch_B starts before Batch_A ends |
| 96 | Batch limit | Rail_Platform | Exceeded | WARNING | 5 batches requested, limit 4 |

**Empty если все ок**, иначе список проблем.

---

### Таблица 4.3: Critical Points (узкие места)

| time | resource | situation | risk | mitigation |
|:-----|:---------|:----------|:-----|:-----------|
| 2024-10-16 22:00 | RVS_1 | Tank level 1500т при loading 700т/ч | HIGH | Осушится через 2ч если ж/д не подвезет |
| 2024-10-17 10:00 | ШТ | Filling 2000т, осталось 700т space | MEDIUM | Заполнится через 1.4ч |
| 2024-10-18 14:00 | Wagons | Нужно 120, доступно 95 (forecast) | HIGH | Заказать 30 external |

---

## 5. ВЫХОДНЫЕ ТАБЛИЦЫ (Results)

### Таблица 5.1: Operations Timeline (финальная последовательность)

| op_id | vessel | operation | product | start | duration | end | resource | volume | wagons | notes |
|:------|:-------|:----------|:--------|:------|:---------|:----|:---------|:------:|:------:|:------|
| 1 | Victoria | Berthing | - | 15.10 14:00 | 24h | 16.10 14:00 | Berth_Palm | - | - | Документы |
| 2 | Victoria | Discharge | Palm Oil | 16.10 14:00 | 13.3h | 17.10 03:20 | Line1→RVS_3 | 12000 | - | Параллельно с OP3 |
| 3 | Victoria | Discharge | Olein | 16.10 14:00 | 6h | 16.10 20:00 | Line2→ШТ | 3000 | - | Параллельно с OP2 |
| 4 | - | Transfer | Olein | 16.10 21:00 | 20.5h | 17.10 17:30 | ШТ→Rail | 3000 | 47 | Освобождение ШТ |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |

---

### Таблица 5.2: Railway Dispatcher Schedule (для ж/д диспетчера)

| date | shift | time | action | wagons | product | destination | tank_source | priority |
|:-----|:------|:-----|:-------|:------:|:--------|:------------|:------------|:---------|
| 15.10 | Утро | 08:00 | Подать под слив | 18 | Sunflower | RVS_1 | - | NORMAL |
| 15.10 | День | 14:00 | Убрать порожние | 18 | - | Подготовка | - | NORMAL |
| 15.10 | Вечер | 18:00 | Подать под налив | 18 | Olein | Client_A | RVS_3 | HIGH |
| 15.10 | Ночь | 00:00 | Отправить груженые | 18 | Olein | Client_A | - | HIGH |

**ФОРМАТ ПОНЯТНЫЙ ДИСПЕТЧЕРУ** - по сменам, четкие команды.

---

### Таблица 5.3: Cost Summary

| category | item | quantity | unit_cost | total_cost | notes |
|:---------|:-----|:--------:|:---------:|:----------:|:------|
| Demurrage | Vessel Victoria | 0 часов | 100000 | 0 | On time |
| Demurrage | Vessel Atlantic | 4 часа | 90000 | 360000 | Weather delay |
| Wagons | Own wagons days | 150 wagon-days | 3000 | 450000 | - |
| Wagons | External ordered | 30 wagons | 50000 | 1500000 | For Victoria |
| Penalties | Client_A shortage | 0 т | 10000 | 0 | Met demand |
| **TOTAL** | | | | **2,310,000** | |

---

### Таблица 5.4: Risk Forecast

| date | risk_type | probability | impact_RUB | expected_loss | recommendation | cost_of_mitigation |
|:-----|:----------|:-----------:|:----------:|:-------------:|:---------------|:------------------:|
| 18.10 | Wagon shortage | 65% | 2,400,000 | 1,560,000 | Order 30 external by 16.10 | 1,500,000 |
| 20.10 | ШТ overflow | 40% | 500,000 | 200,000 | Shift fraction B +4h | 0 |
| 22.10 | Railway delay | 25% | 1,200,000 | 300,000 | Increase RVS safety stock | 0 |

**Decision support format** - что ожидать и что делать.

---

## 6. СВЯЗИ МЕЖДУ ТАБЛИЦАМИ (Data Flow)

```
INPUTS:
┌─────────────────┐
│ 1.1 Vessels     │────┐
│ 1.1.1 Cargo {H} │    │
└─────────────────┘    │
┌─────────────────┐    │
│ 1.2 Rail Sched  │────┤
└─────────────────┘    │         ┌──────────────────┐
┌─────────────────┐    ├────────→│ SEQUENCE         │
│ 1.3 Demand      │────┤         │ GENERATOR        │
└─────────────────┘    │         └──────────────────┘
┌─────────────────┐    │                   │
│ 1.4 Inventory   │────┘                   │
└─────────────────┘                        ↓
                                 ┌──────────────────┐
REFERENCES:                      │ 3.1 Operations   │
┌─────────────────┐              │ Timeline         │
│ 2.1 Tanks       │──┐           └──────────────────┘
│ 2.2 Compat      │  │                    │
│ 2.3 Times       │  │                    ↓
│ 2.4 Priorities  │  │         ┌──────────────────┐
└─────────────────┘  └────────→│ BALANCE          │
                                │ CALCULATOR       │
                                └──────────────────┘
                                         │
                                         ↓
                           ┌──────────────────────────┐
                           │ 3.2 Tank Balances        │
                           │ 3.3 Wagon Balance        │
                           │ 3.4 Resource Gantt       │
                           └──────────────────────────┘
                                         │
                                         ↓
                                ┌─────────────────┐
                                │ VALIDATOR       │
                                └─────────────────┘
                                         │
                           ┌─────────────┴─────────────┐
                           ↓                           ↓
                    ┌──────────┐              ┌────────────┐
                    │ 3.4      │              │ 5.1        │
                    │ Warnings │              │ Final      │
                    │ Errors   │              │ Timeline   │
                    └──────────┘              └────────────┘

OUTPUTS:
                    ┌────────────────────────────────┐
                    │ 5.2 Railway Schedule           │
                    │ 5.3 Cost Summary               │
                    │ 5.4 Risk Forecast              │
                    └────────────────────────────────┘
```

---

## 7. ФОРМАТ ФАЙЛОВ

### Excel Workbook Structure

```
terminal_planner.xlsx:

Sheet "Input_Vessels":
  - Таблица 1.1 + 1.1.1 (судна и их cargo plans)

Sheet "Input_Rail":
  - Таблица 1.2 (график ж/д)

Sheet "Input_Demand":
  - Таблица 1.3 (матрица заявок)

Sheet "Input_CurrentState":
  - Таблица 1.4 (текущие остатки в РВС)

Sheet "Config_Parameters":
  - Таблица 1.5 (настройки)
  - Таблица 1.6 (экономика)
  - Таблица 1.7 (fleet & lead times)

Sheet "Reference_Tanks":
  - Таблица 2.1 (конфигурация РВС)

Sheet "Reference_Compatibility":
  - Таблица 2.2 (матрица совместимости)

Sheet "Reference_Times":
  - Таблица 2.3 (стандарты времени)

Sheet "Reference_Priorities":
  - Таблица 2.4 (приоритеты фракций)

Sheet "Output_Operations":
  - Таблица 5.1 (последовательность операций)

Sheet "Output_Balances":
  - Таблица 3.2 (балансы РВС по часам)

Sheet "Output_Railway":
  - Таблица 5.2 (график для ж/д)

Sheet "Output_Gantt":
  - Таблица 3.4 (визуальная диаграмма)

Sheet "Output_Costs":
  - Таблица 5.3 (стоимость)

Sheet "Output_Risks":
  - Таблица 5.4 (риски и рекомендации)

Sheet "Debug_Wagons":
  - Таблица 3.3 (детальный баланс вагонов)

Sheet "Debug_Violations":
  - Таблица 3.4 (ошибки если есть)
```

---

## 8. DATA VALIDATION RULES

### Для каждой входной таблицы

**Vessels (1.1):**

- vessel_id: unique, not null
- eta: datetime, not in past
- cargo_type: must be "sunflower" or "palm"
- total_volume: > 0, < 50000 (realistic limit)
- demurrage_rate: > 0

**Cargo Plan (1.1.1):**

- Sum of volumes = total_volume (tolerance ±1%)
- All fractions valid product names
- No duplicate hold_ids для одного судна

**Current Inventory (1.4):**

- current_volume ≤ capacity
- current_product in allowed_products для этого танка
- state in valid states list

**Client Demand (1.3):**

- week numbers sequential
- volumes > 0
- priority in {HIGH, MEDIUM, LOW}

---

## 9. CALCULATED FIELDS (что вычисляется автоматически)

### В таблице Operations

**duration** - рассчитывается как:

```
IF op_type = "Discharge" AND destination = Tank:
  duration = volume / rate_discharge[line]

IF op_type = "Discharge" AND destination = Rail:
  duration = volume / rate_direct

IF op_type = "Load" AND source = Tank:
  duration = volume / rate_load

IF op_type = "Cleaning":
  duration = lookup(from_product, to_product, compatibility_matrix)
```

**end_time** = start_time + duration

**wagons** (если операция с ЖДЦ):

```
wagons = CEILING(volume / 65)
```

### В таблице Tank Balances

**RVS_X_balance[t]:**

```
= RVS_X_balance[t-1] + RVS_X_in[t] - RVS_X_out[t]
```

**Где RVS_X_in[t]** = sum of all Q_in для этого танка в час t

**Где RVS_X_out[t]** = sum of all Q_out

### В таблице Costs

**total_cost:**

```
= SUM(demurrage costs) 
  + SUM(wagon costs) 
  + SUM(penalty costs)
```

---

## 10. USER INTERACTION WORKFLOW

### Workflow

1. **Пользователь заполняет:**
   - Sheet "Input_Vessels" (копирует из номинации)
   - Sheet "Input_CurrentState" (из SCADA или вручную)
   - Sheet "Input_Demand" (из контрактов)

2. **Нажимает кнопку "Calculate"** (macro)

3. **Программа:**
   - Загружает все Input sheets
   - Validates данные
   - Генерирует sequence (эвристика)
   - Рассчитывает балансы
   - Проверяет constraints
   - Заполняет Output sheets

4. **Пользователь проверяет Output_Operations:**
   - Видит предложенный sequence
   - Может изменить (поменять местами строки)
   - Отметить "Lock" некоторые операции

5. **Нажимает "Recalculate":**
   - Программа пересчитывает с учетом locks
   - Updates outputs

6. **Экспорт:**
   - "Output_Railway" распечатывается для ж/д диспетчера
   - "Output_Gantt" для визуального контроля
   - "Output_Risks" для планерки
