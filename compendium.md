# Финальный Методологический Компендиум + План Реализации

---

# ЧАСТЬ I: МЕТОДОЛОГИЧЕСКИЙ КОМПЕНДИУМ

## 1. АРХИТЕКТУРА СИСТЕМЫ (4 слоя)

### Слой 1: Физика терминала (Terminal Physics)
**Компоненты:**
- Резервуарный парк: РВС 1-5, ШТ
- Трубопроводная сеть: Line 1 (главная), Line 2 (вспомогательная)
- Насосные станции с переменной производительностью
- Причалы: отдельные для пальмы и подсолнечника

### Слой 2: Операционная логистика (Operations)
**Компоненты:**
- Ж/Д эстакада: 4 подачи/сутки по 18 вагонов (hard limit)
- Маневровые циклы: слив/налив + preparation
- Looping вагонов: подсолнечник → подготовка → пальма
- Перешвартовка: 1.5ч (лето) / 3ч (зима)

### Слой 3: Внешняя сеть (Supply Chain)
**Компоненты:**
- Парк вагонов N_total в обороте
- Lead times: заводы → терминал, терминал → клиенты
- Статистика задержек РЖД (для Марковских цепей)
- Матрица спроса клиентов по неделям

### Слой 4: Управление и UX (Decision Support)
**Компоненты:**
- Sequence management: автогенерация + редактирование
- Двухэтапная оптимизация: время → стоимость
- Risk alerts на основе вероятностных прогнозов

---

## 2. МАТЕМАТИЧЕСКАЯ МОДЕЛЬ

### 2.1 Обозначения

**Индексы:**
- t ∈ T - время (час)
- k ∈ K = {1,2,3,5,ШТ} - танки
- p ∈ P - продукты
- f ∈ F - фракции пальмы (до 8)
- j ∈ J - суда
- c ∈ C - клиенты

**Константы:**
```
Емкости танков:
V_max[1] = V_max[2] = V_max[3] = 9900 т
V_max[5] = V_max[ШТ] = 2700 т

Deadstock:
d[sunflower] = 0.10
d[palm_fractions] = 0.10-0.20

Производительность:
Rate_discharge[summer] = 195 т/ч (4×18×65/24)
Rate_discharge[winter] = 146 т/ч (3×18×65/24)
Rate_ship_load = 500-900 т/ч
Rate_ship_discharge[Line1] = 900 т/ч (в бак 9900)
Rate_ship_discharge[Line2] = 500 т/ч (в бак 2700) или 146 т/ч (прямо ЖДЦ)

Время операций:
T_berthing = 24-168 ч (документы)
T_analysis = 72 ч
T_cleaning[RVS-5] = 48-72 ч
T_cleanup_ship = 48 ч
T_berth_shift = 1.5 ч (лето) / 3 ч (зима)
```

### 2.2 Переменные состояния

**Непрерывные:**
- S[k,p,t] - запас продукта p в танке k в момент t [тонны]
- Q_in[k,p,t] - входящий поток [т/ч]
- Q_out[k,p,t] - исходящий поток <br/>[т/ч]

**Бинарные (0/1):**
- X[k,p,t] - танк k содержит продукт p
- Y_clean[k,t] - танк k в режиме зачистки
- Z_berth[j,t] - судно j у причала

**Целочисленные:**
- N_wagons[t] - количество вагонов
- N_batches[d] - количество подач в день d

### 2.3 Уравнения баланса

**Материальный баланс танка:**

Для каждого k, p, t:

> S[k,p,t] = S[k,p,t-1] + Q_in[k,p,t] - Q_out[k,p,t]

**Ограничения вместимости:**

> 0 ≤ S[k,p,t] ≤ V_max[k] × (1 - d[p])

**Эксклюзивность продукта:**

> Сумма по p от X[k,p,t] ≤ 1

**Связь непрерывной и бинарной переменной:**

> S[k,p,t] ≤ V_max[k] × X[k,p,t]

### 2.4 Каргоплан судна {H}

**Структура:**

Для судна j с n танками:

> Vessel[j] = {(H_1, fraction_1, volume_1), ..., (H_n, fraction_n, volume_n)}

**Пример:**
```
Судно "Victoria" с пальмой:
H_1: Palm Oil, 12000т
H_2: Palm Oil, 8000т
H_3: Olein, 3000т
H_4: Stearin, 2500т
H_5: Olein, 1500т
H_6: PFAD, 800т
...
```

**Constraint на выгрузку:**

Фракция f из танка H_i может выгружаться только если:
1. Танк H_i доступен (не заблокирован другими операциями судна)
2. Есть свободная береговая линия (Line 1 или Line 2)
3. Есть емкость на берегу (РВС или вагоны)

### 2.5 Логика Swing Tank (РВС-5)

**State Machine:**

States = {Empty, Sun, Palm, Cleaning}

**Transition Rules:**

Если X[5, sun, t-1] = 1 И нужен переход на X[5, palm, t] = 1:

ТОГДА для всех τ ∈ [t - T_clean, t-1]:
- Y_clean[5, τ] = 1
- Q_in[5, p, τ] = 0
- Q_out[5, p, τ] = 0

Где T_clean ∈ {48, 72, 168} часов в зависимости от продуктов.

### 2.6 Модель параллельных линий (пальма)

**Line 1 (Main):**
Судно → РВС-3 или РВС-5

Скорость: 900 т/ч

**Line 2 (Auxiliary):**
Судно → {ШТ ИЛИ прямо ЖДЦ}

Скорость: 500 т/ч (ШТ) или 146 т/ч (прямо ЖДЦ)

**Mutex ШТ:**

Нельзя одновременно Q_ship→ШТ > 0 И Q_ШТ→ЖДЦ > 0

**Приоритет освобождения ШТ:**

Если S[ШТ, t] > 2000т (>74% заполнения):

Priority(discharge ШТ→ЖДЦ) = MAXIMUM

### 2.7 Модель вагонов (Markov Chain)

**Состояния вагона:**

States = {Loading, EnRoute, Stuck, AtClient, Returning, Available}

**Переходы (пример матрицы):**

```
         Load  EnRt  Stck  AtCl  Retr  Avbl
Load  [  0    0.9   0.1    0     0     0  ]
EnRt  [  0    0.6  0.15  0.25   0     0  ]
Stck  [  0    0.5   0.4   0.1    0     0  ]
AtCl  [  0     0     0    0.8   0.2    0  ]
Retr  [  0     0     0     0    0.7   0.3 ]
Avbl  [ 1.0    0     0     0     0     0  ]
```

**Прогноз:**

Вектор состояния π(t+1) = π(t) · P

Ожидаемое количество доступных вагонов:

> E[N_available, t] = N_total × π_Available[t]

Для консервативного планирования: P90 quantile.

### 2.8 Целевая функция (финальная)

**Этап I (минимизация времени):**

> min T_makespan = max_j (T_departure[j] - T_arrival[j])

**Этап II (минимизация затрат):**

> min Z = C_dem × T_delay + C_ext × N_ext_wagons + C_batch_extra × N_extra_batches + C_penalty × Unmet_demand

Где веса:
- C_dem ≈ 100,000 руб/час (доминирует)
- C_ext ≈ 50,000 руб/вагон
- C_batch_extra ≈ 50,000-150,000 руб (soft constraint)
- C_penalty - зависит от клиента

---

## 3. АЛГОРИТМЫ

### 3.1 Heuristic Sequence Generation (Этап I)

**Rule 1: Large to Main Line**
```
Для каждой фракции f в {H}:
  IF volume[f] > 5000:
    Assign f → Line1 → RVS-3 или RVS-5
  ELSE:
    Assign f → Line2 → ШТ или Direct_Rail
```

**Rule 2: SHT Priority**
```
WHILE discharge_in_progress:
  IF S[ШТ] > 2000:
    PAUSE Line2_ship_discharge
    FORCE discharge_ШТ→Rail
  ELSE:
    RESUME Line2_ship_discharge
```

**Rule 3: RVS-5 Allocation**
```
IF sunflower_volume > 19800 (РВС-1+2):
  USE RVS-5 для подсолнечника
  ELSE prefer keep RVS-5 для пальмы (избежать зачистки)
```

### 3.2 Flow-Through Logic (подсолнечник)

**Критическая точка старта:**

> S_start = V_ship - (Rate_rail × T_loading)

Где T_loading = V_ship / Rate_ship

**Пример расчета:**
```
V_ship = 38,000т
Rate_ship = 700 т/ч
T_loading = 54ч
Rate_rail = 195 т/ч
Подвоз за время погрузки = 195 × 54 = 10,530т
S_start = 38,000 - 10,530 = 27,470т
+ Safety margin 10% = 30,217т

Проверка: 30,217т ≤ Capacity (29,700т РВС 1+2+5)?
НЕТ → проблема
Решение: либо снизить Rate_ship до 600 т/ч, либо увеличить Rate_rail
```

### 3.3 Wagon Looping

**Трансформация:**

После слива подсолнечника через время T_prep:

> W_palm_ready[t] = W_discharged[t - T_prep] × (1 - K_reject)

Где:
- T_prep = 1-6 часов (осмотр + маневры + промывка)
- K_reject = 0.10-0.15 (10-15% отбраковка)

**Решение "Buy or Wait":**

```
Gap[t] = Demand_palm[t] - (W_own_available[t] + W_returning[t])

IF Gap[t] > 0:
  Cost_wait = P(delay) × C_demurrage × Expected_delay
  Cost_buy = Gap × C_external
  
  IF Cost_buy < Cost_wait:
    Order external wagons
  ELSE:
    Wait (accept delay risk)
```

---

## 4. ВХОДНЫЕ ПАРАМЕТРЫ (Classification)

### 4.1 Пользовательские (меняются каждый рейс)

**А. Судно:**
```
vessel_id: str
eta: datetime
cargo_type: "sunflower" | "palm"
total_volume: float (тонны)
cargo_plan {H}: Dict[tank_id, (fraction, volume)]
  Пример: {"H1": ("Palm Oil", 12000), "H2": ("Olein", 3000), ...}
sequence_constraints: List (если капитан задает порядок)
demurrage_rate: float (руб/час)
strategic_weight: float (1.0 = normal, 2.0 = приоритетный)
```

**Б. Текущее состояние терминала:**
```
Для каждого РВС:
  current_volume: float
  current_product: str | None
  state: "idle" | "filling" | "analysis" | "discharging" | "cleaning"
  state_entry_time: datetime
```

**В. Ж/Д график (входящий):**
```
Список поставок подсолнечника:
  date: datetime
  wagons_count: int
  source: "own_production" | "trading"
```

**Г. Матрица спроса (исходящий):**
```
По неделям и клиентам:
Week 42:
  Client_A: {"olein": 2000т, "stearin": 500т}
  Client_B: {"palm_oil": 5000т}
Week 43:
  ...
```

**Д. UX Tuning:**
```
season: "summer" | "winter" (влияет на скорости и время перешвартовки)
equipment_status: {"RVS_3": "available", "Pump_Line1": "50%", ...}
operation_time_adjustments: {
  "berthing": +2h (из-за шторма),
  "cleaning_RVS5": 72h (вместо 48h)
}
```

### 4.2 Административные (настраиваются редко)

**А. Парк и логистика:**
```
N_total: int (общий парк вагонов)
lead_times: Dict[route, days]
  {"own_production→terminal": 3, 
   "terminal→client_A": 5,
   "client_A→terminal": 2}
delay_statistics: Dict (для Markov)
  {"stuck_probability": 0.15, "mean_delay": 1.5days}
```

**Б. Экономика:**
```
C_demurrage: Dict[vessel_type, float]
  {"palm_import": 100000 руб/ч, "sunflower_export": 90000 руб/ч}
C_wagon_own: 3000 руб/сутки
C_wagon_external: 50000 руб (с доставкой)
C_batch_extra: 50000 руб (5-я подача)
C_penalty[client]: Dict
  {"client_strategic": 10000 руб/тонна недопоставки,
   "client_spot": 1000 руб/тонна}
```

### 4.3 Системные константы (hard-coded)

```
Tank_allocation:
  RVS_1: ["sunflower"]
  RVS_2: ["sunflower"]
  RVS_3: ["palm_*"]
  RVS_5: ["sunflower", "palm_*"] - требует cleaning
  ШТ: ["palm_*"]

Product_compatibility_matrix:
  (sunflower, sunflower): cleaning = 0h
  (sunflower, palm): cleaning = 48h
  (palm, sunflower): cleaning = 48h
  (palm_olein, palm_stearin): cleaning = 12h
  (low3mcpd, standard): cleaning = 168h

Rail_batch_limit:
  contractual = 4 подачи/день
  physical_max = 6 (теоретически)
```

---

## 5. CONSTRAINTS (Ограничения)

### 5.1 Hard Constraints (нельзя нарушить)

**1. Capacity:**
> 0 ≤ S[k,p,t] ≤ V_max[k] × (1 - deadstock[p])

**2. Product exclusivity:**
> Сумма X[k,p,t] по всем p ≤ 1

**3. Flow conservation:**
> S[k,t] = S[k,t-1] + Σ Q_in - Σ Q_out

**4. Resource exclusivity (tank):**

Для операций i,j на одном танке k:

> end_time[i] ≤ start_time[j] ИЛИ end_time[j] ≤ start_time[i]

**5. Precedence:**

Если operation B зависит от operation A:

> start[B] ≥ end[A]

**6. Railway batch limit (HARD теперь):**

> N_batches[d] ≤ 4 для каждого дня d

**7. ШТ mutex:**

Нельзя одновременно заполнять ШТ И выгружать из ШТ в ЖДЦ.

### 5.2 Soft Constraints (можно нарушить за штраф)

**1. Preferred tank usage:**

Предпочтение использовать dedicated tanks вместо swing.

Штраф за использование РВС-5 = opportunity cost.

**2. Client prioritization:**

Strategic clients должны обслуживаться первыми.

Штраф за задержку strategic client выше.

### 5.3 Conditional Constraints

**1. Cleaning requirement:**

> IF X[k, p1, t-1] = 1 AND X[k, p2, t] = 1 AND p1 ≠ p2
> THEN Y_clean[k, τ] = 1 для τ ∈ [t-T_clean, t-1]
> AND Q_in[k, *, τ] = Q_out[k, *, τ] = 0

**2. Analysis blocking:**

> IF tank.state = "analysis" for fraction f
> THEN Q_out[k, f, t] = 0
> UNTIL analysis_complete AND analysis_result = "pass"

---

## 6. OBJECTIVE FUNCTIONS (Целевые функции)

### 6.1 Stage I: Time Minimization

> min T_makespan = max over all vessels j of (T_departure[j] - T_arrival[j])

Subject к all hard constraints.

### 6.2 Stage II: Cost Minimization

> min Z = Σ_j (C_dem[j] × weight[j] × Delay[j])
>       + Σ_t (C_ext × N_ext_wagons[t])
>       + Σ_c (C_penalty[c] × Unmet[c])

Где:
- Delay[j] = actual_departure - planned_departure
- N_ext_wagons - количество заказанных внешних вагонов
- Unmet[c] - недопоставка клиенту c

---

## 7. АЛГОРИТМЫ (Логика работы)

### 7.1 Auto-Sequence Generation

**Input:** Cargo plan {H} с 8 фракциями

**Steps:**

1. **Classify fractions by size:**
   - Large (>5000т) → candidates for Line1 → RVS big
   - Small (<3000т) → candidates for Line2 → ШТ or Direct

2. **Sort by compatibility:**
   - Group compatible fractions (можно грузить подряд без cleaning)
   - Minimize cleaning operations

3. **Allocate to lines:**
   - Largest fraction → Line1 → RVS-3
   - If RVS-3 fills, next large → RVS-5 (if clean)
   - Small fractions → Line2

4. **Check feasibility:**
   - ШТ не переполняется при любой sequence
   - Вагонов хватает для всех Direct operations
   - Timeline не превышает demurrage limits

5. **Output:** Ordered list of operations with tentative times

### 7.2 Local Recomputation (при user edit)

**Trigger:** Пользователь меняет местами operations A и B

**Steps:**

1. **Identify affected:**
   - Find all operations depending on A or B
   - Mark as "needs_recompute"

2. **Lock unchanged:**
   - All other operations: fix their start_times

3. **Partial re-optimization:**
   - Optimize only affected operations
   - Respect user's swap constraint

4. **Validation:**
   - Check if new sequence создает conflicts
   - If yes → reject change, show reason
   - If no → update solution

### 7.3 Wagon Availability Forecast

**Input:** Current wagon distribution, Markov matrix

**Steps:**

1. **Initialize state vector:**
   ```
   π[0] = current distribution
   Пример: {Loading: 20, EnRoute: 150, AtClient: 200, Returning: 100, Available: 30}
   ```

2. **Iterate for horizon days:**
   ```
   For day = 1 to 30:
     π[day] = π[day-1] · P (matrix multiplication)
   ```

3. **Extract forecast:**
   ```
   For each day:
     E[available] = N_total × π_Available[day]
     P90[available] = calculate 90th percentile from distribution
   ```

4. **Output:** 
   ```
   Day 1: E=35, P90=28
   Day 2: E=42, P90=33
   ...
   Day 18: E=85, P90=70 ← судно прибывает, нужно 120 вагонов
   → GAP detected, recommend order 50 external
   ```

---

## 8. OUTPUTS (Выходные данные)

### 8.1 Gantt Chart

**Format:** Excel таблица

**Rows (resources):**
- Berth_Palm
- Berth_Sun
- RVS-1, RVS-2, RVS-3, RVS-5, ШТ
- Rail_Platform
- Line1, Line2

**Columns:** Часы (или дни)

**Cells:** Operations
- Color-coded: зеленый = loading/discharging, желтый = analysis, красный = cleaning
- Text: "Discharge Olein 3000t"

**Interactive:**
- User can drag blocks (change sequence)
- Locked blocks (fixed by user)

### 8.2 Railway Schedule

**Format:** Таблица по сменам

| День | Смена | Время | Операция | Вагонов | Продукт |Destination | Notes |
|:-----|:------|:------|:---------|:-------:|:--------|:-----------|:------|
| 15.10 | День | 08:00 | Подать под слив | 18 | Подсолнечник | РВС-1 | - |
| 15.10 | День | 14:00 | Убрать пустые | 18 | - | На подготовку | 1.5ч |
| 15.10 | Вечер | 18:00 | Подать под налив | 18 | Олеин | Client A | - |
| 15.10 | Ночь | 02:00 | Отправить полные | 18 | Олеин | Client A | - |

### 8.3 Economic Report

| Item | Calculation | Amount (RUB) |
|:-----|:------------|:------------:|
| Vessel demurrage | Σ(C_dem × delays) | 0 (on time) |
| Own wagons | Σ(days × 3000) | 450,000 |
| External wagons | Σ(count × 50000) | 1,500,000 |
| Client penalties | Σ(shortages × C_pen) | 0 |
| **TOTAL** | | **1,950,000** |

Сравнение с baseline: -15% cost reduction.

### 8.4 Risk Alerts

**Format:** Priority list

| Date | Event | Probability | Impact | Recommendation |
|:-----|:------|:----------:|:------:|:---------------|
| 18.10 | Wagon shortage для "Victoria" | 65% | 2.4M RUB | Order 30 external by Day 16 |
| 20.10 | ШТ overflow risk | 40% | Operational disruption | Shift fraction B discharge +4h |
| 22.10 | Railway delay forecast | 25% | 1.2M RUB | Increase RVS safety stock |

---

## 9. EXPLANATION FOR 12-YEAR-OLD MATH OLYMPIAD WINNER

**The Problem:**

You have a **flow network optimization problem with:**
- Directed graph G(nodes, edges)
- Multi-commodity flow (8 different "colored" liquids)
- Capacity constraints on nodes (tanks) and edges (pipes)
- Discrete events (trains arrive in batches)
- Stochastic elements (trains may be delayed)

**The Complexity:**

**1. Combinatorial Explosion:**
- 8 fractions on vessel
- 5 tanks on shore
- 2 pipelines
- How many ways to discharge vessel? Millions!

**2. Stochastic Inputs:**
- Trains don't arrive on schedule, they follow probability distributions
- We use **Markov Chains**: wagon = chip moving on board
- Each turn, roll dice to see: arrived? stuck? still traveling?

**3. Multi-Objective:**
- Can't just "go fast" or "go cheap"
- Need balance
- But NOT equal weights: vessel delays cost 800× more than wagon delays

**4. Temporal Constraints:**
- Some operations MUST precede others
- Some resources can't be shared simultaneously
- Time windows (vessel can't berth before ETA)

**The Solution Method:**

**Step 1: Split the Problem**
- First find ANY valid schedule (ignore cost)
- Then optimize cost (given that schedule)

**Step 2: Use Penalties**
- Allow rule-breaking but assign cost
- "You can order 5th train batch, but costs 50K penalty"
- "You can delay strategic client, but costs 10M penalty"

**Step 3: Solver Finds Minimum**
- Computer tries millions of combinations
- Finds the one where total penalty is minimum
- This is your optimal solution

**Step 4: Handle Randomness**
- Run 1000 simulations with random train delays
- See in how many simulations we fail
- If >20% failure rate → add safety buffer

**The Beauty:**
This is **stochastic combinatorial optimization** - one of the hardest classes of problems. But solvable with smart decomposition and heuristics.

---

# ЧАСТЬ II: РЕАЛИСТИЧНЫЙ ПЛАН РЕАЛИЗАЦИИ

---

## SCOPE DEFINITION

**Что строим (MVP):**

Программа которая:
1. Читает параметры судна (фракции пальмы или объем подсолнечника)
2. Учитывает текущие остатки в РВС
3. Автоматически генерирует sequence операций
4. Рассчитывает балансы по часам
5. Проверяет ограничения (вместимость, лимит ж/д)
6. Выводит Excel таблицу (как в вашем CSV)

**Опционально (если нужно):**
7. Оптимизация sequence для минимизации времени
8. Учет вагонов и looping
9. Risk alerts

---

## TIMELINE & TEAM

**Команда:** 1 разработчик (Python опыт)

**MVP (без оптимизации):** 6-8 недель

**С базовой оптимизацией:** +3-4 недели

**С полным функционалом:** +4-6 недель

**Total: 13-18 недель** для полной версии

---

## PHASE 0: Подготовка (Недели 1-2)

### Неделя 1: Требования и дизайн

**Задачи:**
1. Создать спецификацию входного формата:
   - YAML или JSON для описания судна
   - Excel template для загрузки данных
   
2. Задокументировать все бизнес-правила:
   - Какие РВС под какие продукты
   - Приоритеты фракций (из п.3.2 второго CSV)
   - Матрица cleaning times
   
3. Создать test cases:
   - Простой: 1 судно с подсолнечником 25000т
   - Средний: 1 судно с пальмой 4 фракции
   - Сложный: как в вашем CSV (8 фракций + подсолнечник)

**Deliverable:**
- requirements.md
- input_format_spec.yaml
- test_cases/ с 3 примерами
- compatibility_matrix.csv

### Неделя 2: Setup и базовые структуры

**Задачи:**
1. Setup проекта:
   - Git repository
   - Virtual environment
   - requirements.txt (pandas, openpyxl, pyyaml)

2. Базовые классы:
   ```
   class Tank:
     - tank_id, capacity, allowed_products
     - current_volume, current_product
     - can_accept(product, volume)
     - get_available_capacity()
   
   class Vessel:
     - vessel_id, eta, cargo_type, total_volume
     - cargo_plan: Dict[tank_id, (fraction, volume)]
     - get_fractions()
   
   class Operation:
     - op_id, op_type, start, duration
     - resource_id
     - product, volume
   ```

3. Unit tests для классов

**Deliverable:**
- domain_models.py (~300 lines)
- tests/ с coverage >80%

---

## PHASE 1: Калькулятор балансов (Недели 3-4)

### Неделя 3: Balance Engine

**Задачи:**
1. Реализовать balance calculator:
   ```
   def calculate_tank_balance(operations, initial_state, horizon_hours):
     """
     Для списка операций рассчитывает балансы по часам
     Returns: DataFrame с колонками [hour, RVS_1, RVS_2, ..., total]
     """
   ```

2. Реализовать validation:
   ```
   def validate_sequence(operations, tanks):
     """
     Проверяет:
     - Нет overfill
     - Нет product mixing без cleaning
     - Precedence соблюдены
     Returns: (is_valid, violations_list)
     """
   ```

3. Tests на примерах:
   - Воспроизвести балансы из вашего CSV
   - Accuracy check: совпадение ±1%

**Deliverable:**
- balance_calculator.py (~400 lines)
- validation.py (~200 lines)
- Работает на test_case_simple

### Неделя 4: Wagon Calculation

**Задачи:**
1. Wagon balance:
   ```
   def calculate_wagon_requirement(operations):
     """
     Для каждой операции с ЖДЦ:
     - Считает вагонов = CEILING(volume / 65)
     - Распределяет по дням
     - Проверяет лимит 4 подачи
     """
   ```

2. Batch scheduling:
   ```
   def distribute_to_batches(wagons_per_day):
     """
     Распределяет вагоны по 4 подачам в сутки
     Returns: детальный график по часам
     """
   ```

3. Integration test:
   - Full calculation на test_case_medium
   - Output совпадает с ожидаемым

**Deliverable:**
- wagon_manager.py (~300 lines)
- Полный расчет работает end-to-end

---

## PHASE 2: Sequence Generator (Недели 5-6)

### Неделя 5: Heuristic Generator

**Задачи:**
1. Реализовать правила из методологии:
   ```
   def generate_palm_sequence(cargo_plan, tank_status):
     """
     Распределяет фракции по линиям:
     - Large → Line1 → RVS-3,5
     - Small → Line2 → ШТ or Direct
     Returns: List[Operation]
     """
   ```

2. Правила приоритета (из CSV п.3.2):
   - Порядок: Low3MCPD Olein → Olein → Low3MCPD Oil → Oil
   - Учет совместимости

3. Tank allocation logic:
   ```
   def allocate_tanks(fractions, tank_status):
     """
     Минимизирует cleaning operations
     Максимизирует utilization
     """
   ```

**Deliverable:**
- sequence_generator.py (~400 lines)
- Генерирует reasonable sequence для test cases

### Неделя 6: Sunflower Flow-Through

**Задачи:**
1. Critical point calculator:
   ```
   def calc_start_point(vessel_volume, rail_rate, ship_rate):
     """
     S_start = V_ship - (rate_rail × T_loading)
     + safety margin
     """
   ```

2. Continuous monitoring logic:
   ```
   def check_tank_level_critical(current_level, ship_rate, rail_rate, hours_remaining):
     """
     Проверяет: хватит ли до конца погрузки
     Returns: (is_safe, recommended_action)
     """
   ```

3. Direct variant trigger:
   ```
   def should_activate_direct(tank_level, ship_rate, pump_rate):
     """
     Решает использовать ли booster
     """
   ```

**Deliverable:**
- sunflower_handler.py (~300 lines)
- Работает на test_case_sunflower_38kt

---

## PHASE 3: Excel Integration (Неделя 7)

### Задачи:

1. **Excel reader:**
   ```
   def load_from_excel(filepath):
     """
     Читает листы:
     - "Vessels": расписание судов
     - "Current_Inventory": состояние РВС
     - "Client_Demand": матрица заявок
     Returns: Scenario object
     """
   ```

2. **Excel writer:**
   ```
   def write_to_excel(solution, filepath):
     """
     Создает листы:
     - "Balance": балансы по РВС (как в вашем CSV)
     - "Operations": список операций
     - "Railway_Schedule": график для ж/д
     - "Warnings": alerts и риски
     """
   ```

3. **VBA Integration:**
   - Кнопка "Calculate" в Excel
   - Calls Python через subprocess
   - Shows progress bar

**Deliverable:**
- excel_io.py (~400 lines)
- terminal_template.xlsx
- run_calculation.bat

---

## PHASE 4: Testing & Documentation (Неделя 8)

### Задачи:

1. **Comprehensive testing:**
   - Все test cases проходят
   - Результаты совпадают с ручным расчетом
   - Edge cases (пустые танки, overfill attempts)

2. **Performance:**
   - Расчет 30-day scenario за <30 секунд
   - Memory usage <500MB

3. **Documentation:**
   - README.md: установка и запуск
   - USER_GUIDE.md: как пользоваться
   - Примеры расчетов

4. **Error handling:**
   - Понятные сообщения об ошибках
   - Validation input data
   - Graceful failures

**Deliverable:**
- Полностью работающая система (MVP)
- Bug-free на всех test cases
- Документация

---

## OPTIONAL PHASE 5: Optimization (Недели 9-12)

### Неделя 9-10: Stage I Solver

**Задачи:**
1. Формулировка CP model (OR-Tools):
   - Variables: start_time для каждой operation
   - Constraints: capacity, precedence, resources
   - Objective: minimize makespan

2. Integration с sequence generator:
   - Use heuristic как warm start
   - Improve через optimization

### Неделя 11: Stage II Economic

**Задачи:**
1. Формулировка MILP (PuLP):
   - Variables: N_external_wagons
   - Constraints: wagon availability
   - Objective: minimize cost

2. Integration с Markov forecast

### Неделя 12: Integration

**Задачи:**
1. Два режима в Excel:
   - "Quick Calculate" (heuristic, 10 sec)
   - "Optimize" (solver, 2-5 min)

2. Comparison results

---

## CODE STRUCTURE (финальная)

```
terminal_optimizer/
├── main.py                    # точка входа (100 lines)
├── domain_models.py           # Tank, Vessel, etc (300 lines)
├── balance_calculator.py      # материальные балансы (400 lines)
├── sequence_generator.py      # heuristic sequence (400 lines)
├── sunflower_handler.py       # flow-through logic (300 lines)
├── wagon_manager.py           # wagon calculation (300 lines)
├── excel_io.py                # Excel интеграция (400 lines)
├── validation.py              # проверки (200 lines)
├── optimizer.py               # optional: MILP solver (500 lines)
├── config.py                  # конфигурация (100 lines)
└── utils.py                   # helpers (200 lines)

Total: ~2,700 lines (MVP) или ~3,200 (с оптимизацией)
```

---

## SUCCESS CRITERIA

**MVP Acceptance:**
- [ ] Воспроизводит результаты из CSV файла с точностью ±2%
- [ ] Обрабатывает судно с 8 фракциями
- [ ] Генерирует Excel output в нужном формате
- [ ] Работает за <1 минуты для 30-day scenario
- [ ] Пользователь может запустить без Python знаний

**With Optimization:**
- [ ] Находит sequence быстрее heuristic на ≥10%
- [ ] Solve time <5 минут
- [ ] Solutions feasible (проходят validation)