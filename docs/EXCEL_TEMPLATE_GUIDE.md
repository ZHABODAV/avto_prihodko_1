# Terminal Optimizer - Excel Template Setup Guide

## Overview

This guide provides complete instructions for setting up the `terminal_template.xlsx` file with all necessary worksheets, data validation, VBA macros, and user interface elements.

## Table of Contents

1. [Worksheet Structure](#worksheet-structure)
2. [Data Validation Rules](#data-validation-rules)
3. [VBA Integration](#vba-integration)
4. [Custom Ribbon Setup](#custom-ribbon-setup)
5. [Testing Checklist](#testing-checklist)

---

## Worksheet Structure

### 1. Input_Vessels

**Purpose**: Enter vessel schedule with cargo details

**Column Headers** (Row 1):

| Column | Header | Data Type | Required | Example |
|--------|--------|-----------|----------|---------|
| A | vessel_id | Text | Yes | Victoria_002 |
| B | eta | DateTime | Yes | 2024-10-15 14:00 |
| C | cargo_type | Text (dropdown) | Yes | palm |
| D | total_volume | Number | Yes | 28500 |
| E | demurrage_rate | Number | Yes | 100000 |
| F | strategic_weight | Number | Yes | 2.0 |
| G | notes | Text | No | Complex palm cargo with 8 fractions |

**Example Row** (Row 2):

```
Victoria_002 | 2024-10-15 14:00 | palm | 28500 | 100000 | 2.0 | Complex palm cargo
```

**Comments** (Add to header cells):

- A1: "Unique vessel identifier (e.g., Victoria_002, Atlantic_003)"
- B1: "Expected arrival date and time (format: YYYY-MM-DD HH:MM)"
- C1: "Cargo type: 'sunflower' for export, 'palm' for import"
- D1: "Total cargo volume in tonnes"
- E1: "Demurrage cost in RUB per hour"
- F1: "Priority multiplier (1.0 = normal, 2.0 = high priority)"
- G1: "Additional notes and comments"

### 2. Input_Rail

**Purpose**: Enter railway delivery schedule

**Column Headers**:

| Column | Header | Data Type | Required | Example |
|--------|--------|-----------|----------|---------|
| A | date | Date | Yes | 2024-10-14 |
| B | time | Time | Yes | 08:00 |
| C | wagons | Integer | Yes | 18 |
| D | product | Text | Yes | sunflower |
| E | source | Text (dropdown) | Yes | own_production |
| F | notes | Text | No | Morning batch - Factory A |

**Dropdown Lists**:

- **source**: own_production, trading

**Example Row**:

```
2024-10-14 | 08:00 | 18 | sunflower | own_production | Morning batch
```

### 3. Input_Demand

**Purpose**: Client demand by week and product

**Column Headers**:

| Column | Header | Data Type | Required | Example |
|--------|--------|-----------|----------|---------|
| A | week | Integer | Yes | 42 |
| B | client_id | Text | Yes | CLI_001 |
| C | client_name | Text | Yes | Zavod Maslozhir |
| D | product | Text (dropdown) | Yes | palm_olein |
| E | volume | Number | Yes | 2000 |
| F | priority | Text (dropdown) | Yes | HIGH |
| G | penalty_rate | Number | Yes | 10000 |
| H | notes | Text | No | Strategic client |

**Dropdown Lists**:

- **priority**: HIGH, MEDIUM, LOW
- **product**: palm_oil, palm_olein, palm_stearin, palm_pfad, palm_oil_low3mcpd, palm_olein_low3mcpd

**Example Row**:

```
42 | CLI_001 | Zavod Maslozhir | palm_olein | 2000 | HIGH | 10000 | Strategic client
```

### 4. Input_CurrentState

**Purpose**: Current state of all storage tanks

**Column Headers**:

| Column | Header | Data Type | Required | Example |
|--------|--------|-----------|----------|---------|
| A | tank_id | Text | Yes | RVS_1 |
| B | current_volume | Number | Yes | 8500 |
| C | current_product | Text | No | sunflower |
| D | state | Text (dropdown) | Yes | available |
| E | state_entry_time | DateTime | No | 2024-10-14 10:00 |
| F | temperature | Number | No | 25 |
| G | notes | Text | No | Partially filled |

**Dropdown Lists**:

- **state**: idle, filling, discharging, analysis, cleaning, available

**Predefined Tank IDs**: RVS_1, RVS_2, RVS_3, RVS_5, SHT

**Example Row**:

```
RVS_1 | 8500 | sunflower | available | | 25 | Partially filled
```

### 5. Config_Parameters

**Purpose**: Configuration parameters and operational settings

**Format**: Two-column layout (Parameter name | Value)

**Default Parameters**:

| Parameter | Value | Description |
|-----------|-------|-------------|
| season | summer | Season mode (summer/winter) |
| rail_discharge_rate | 195 | Railway discharge rate (tonnes/hour) - summer |
| ship_load_rate_min | 500 | Minimum ship loading rate (tonnes/hour) |
| ship_load_rate_max | 900 | Maximum ship loading rate (tonnes/hour) |
| ship_discharge_line1 | 900 | Ship discharge rate for Line 1 (tonnes/hour) |
| ship_discharge_line2_tank | 500 | Ship discharge rate for Line 2 to tank (tonnes/hour) |
| ship_discharge_line2_direct | 146 | Ship discharge rate for Line 2 direct (tonnes/hour) |
| wagon_prep_time | 1.5 | Wagon preparation time (hours) |
| wagon_reject_rate | 0.12 | Wagon rejection rate (%) |
| berth_shift_time | 1.5 | Berth shifting time (hours) - summer |
| cleaning_time_standard | 48 | Standard tank cleaning time (hours) |
| cleaning_time_full | 72 | Full tank cleaning time (hours) |
| analysis_time | 72 | Quality analysis time (hours) |
| wagon_own_cost | 3000 | Cost per own wagon (RUB) |
| wagon_external_cost | 50000 | Cost per external wagon (RUB) |
| batch_extra_penalty | 50000 | Penalty for extra batch (RUB) |
| total_wagon_fleet | 500 | Total available wagons |

### 6. Reference Worksheets

#### Ref_TankConfig

Pre-filled tank configuration from `templates/tank_config.csv`:

| tank_id | capacity | allowed_products | is_swing | deadstock_sunflower | deadstock_palm |
|---------|----------|------------------|----------|---------------------|----------------|
| RVS_1 | 9900 | sunflower | No | 0.10 | |
| RVS_2 | 9900 | sunflower | No | 0.10 | |
| RVS_3 | 9900 | palm_oil\|palm_olein\|... | No | | 0.15 |
| RVS_5 | 2700 | sunflower\|palm_oil\|... | Yes | 0.10 | 0.10 |
| SHT | 2700 | palm_oil\|palm_olein\|... | No | | 0.10 |

#### Ref_ProductCompatibility

Pre-filled from `templates/product_compatibility_matrix.csv`:

Matrix showing cleaning hours required for product transitions.

#### Ref_OperationTimeStandards

Pre-filled from `templates/operation_time_standards.csv`:

Standard time norms for various operations.

#### Ref_PalmFractionPriorities

Pre-filled from `templates/palm_fraction_priorities.csv`:

Priority order for palm fraction processing.

### 7. Output Worksheets

Create empty output worksheets (will be filled by Python script):

- **Output_Schedule**: Detailed operation schedule
- **Output_Gantt**: Gantt chart visualization
- **Output_Railway**: Railway operations schedule
- **Output_Costs**: Cost breakdown and analysis
- **Output_Balance**: Tank balance over time
- **Output_Risks**: Risk analysis and alerts

Each output sheet should have:

- Row 1: Headers (leave empty, Python will fill)
- Row 2+: Data area

### 8. Instructions Sheet

Create an "Instructions" worksheet with user guide:

```
=================================
TERMINAL OPTIMIZER - ИНСТРУКЦИЯ
=================================

ПОРЯДОК РАБОТЫ:
---------------

1. ВВОД ДАННЫХ
   - Заполните лист "Input_Vessels" с информацией о судах
   - Заполните лист "Input_Rail" с расписанием прихода вагонов
   - Заполните лист "Input_Demand" с заказами клиентов
   - Обновите лист "Input_CurrentState" с текущим состоянием танков
   - При необходимости настройте параметры на листе "Config_Parameters"

2. ЗАПУСК РАСЧЕТА
   - Нажмите кнопку "Calculate Plan" на панели инструментов
   - Дождитесь завершения расчета (появится окно с прогрессом)
   - В случае ошибки проверьте лог-файл calculation_log.txt

3. ПРОСМОТР РЕЗУЛЬТАТОВ
   - Output_Schedule: детальное расписание всех операций
   - Output_Gantt: визуализация графика работ
   - Output_Railway: расписание работы с вагонами
   - Output_Costs: расчет стоимости и издержек
   - Output_Balance: баланс по танкам во времени
   - Output_Risks: анализ рисков и предупреждения

4. ЭКСПОРТ
   - Кнопка "Export PDF": сохранить отчет в PDF
   - Кнопка "Clear Results": очистить результаты

ТРЕБОВАНИЯ:
-----------
- Python 3.8 или выше
- Установленные библиотеки (см. requirements.txt)
- Модули terminal_optimizer в той же директории

ПОМОЩЬ:
-------
- Наведите курсор на заголовки столбцов для подсказок
- См. примеры во второй строке каждого листа
- Для расширенной помощи см. документацию в папке docs/
```

---

## Data Validation Rules

### Setting up Dropdown Lists

#### 1. cargo_type (Input_Vessels, Column C)

```vba
' In Excel: Data → Data Validation
Source: sunflower,palm
Input Message: "Select cargo type"
Error Alert: "Please select either 'sunflower' or 'palm'"
```

#### 2. priority (Input_Demand, Column F)

```vba
Source: HIGH,MEDIUM,LOW
Input Message: "Select priority level"
```

#### 3. source (Input_Rail, Column E)

```vba
Source: own_production,trading
Input Message: "Select sunflower source type"
```

#### 4. state (Input_CurrentState, Column D)

```vba
Source: idle,filling,discharging,analysis,cleaning,available
Input Message: "Select current tank state"
```

#### 5. product (Input_Demand, Column D)

```vba
Source: palm_oil,palm_olein,palm_stearin,palm_pfad,palm_oil_low3mcpd,palm_olein_low3mcpd
Input Message: "Select palm fraction"
```

### Number Validation

#### Volume fields (must be > 0)

Apply to:

- Input_Vessels: Column D (total_volume)
- Input_Demand: Column E (volume)

```vba
' Data Validation Settings
Allow: Decimal
Data: greater than
Minimum: 0
Error Alert: "Volume must be greater than 0"
```

#### Date/Time Validation

Apply to:

- Input_Vessels: Column B (eta)
- Input_Rail: Columns A, B (date, time)
- Input_CurrentState: Column E (state_entry_time)

```vba
' Format cells as Date/DateTime
Format: yyyy-mm-dd hh:mm
```

---

## VBA Integration

### Step 1: Enable Developer Tab

1. File → Options → Customize Ribbon
2. Check "Developer" in the right column
3. Click OK

### Step 2: Import VBA Modules

1. Open VBA Editor (Alt + F11)
2. File → Import File...
3. Import `vba/MainInterface.bas`
4. Repeat for any additional modules

### Step 3: Create Progress Form

1. In VBA Editor: Insert → UserForm
2. Name it "ProgressForm"
3. Add controls:
   - Label: "StatusLabel" (for status message)
   - Label: "PercentLabel" (for percentage)
   - Frame: "ProgressBarBackground" (width: 300, height: 20)
   - Frame: "ProgressBar" (width: 0, height: 20, inside ProgressBarBackground)

4. Import form code from `vba/ProgressForm.frm` or copy-paste the code

### Step 4: Set Macro Security

1. Developer → Macro Security
2. Select "Enable all macros"  (or "Disable all macros with notification")
3. Check "Trust access to the VBA project object model"

---

## Custom Ribbon Setup

### Method 1: Quick Access Toolbar (Simple)

1. Right-click Quick Access Toolbar
2. Select "Customize Quick Access Toolbar"
3. Choose "Macros" from dropdown
4. Add these macros:
   - `MainInterface.RunCalculation`
   - `MainInterface.ClearOutputs`
   - `MainInterface.ExportToPDF`
   - `MainInterface.ShowHelp`

### Method 2: Custom Ribbon (Advanced)

Create `customUI/customUI14.xml`:

```xml
<customUI xmlns="http://schemas.microsoft.com/office/2009/07/customui">
  <ribbon>
    <tabs>
      <tab id="TerminalOptimizer" label="Terminal Optimizer">
        <group id="MainGroup" label="Operations">
          
          <button id="btnCalculate" 
                  label="Calculate Plan" 
                  size="large"
                  imageMso="Calculate"
                  onAction="OnCalculateClick" />
          
          <button id="btnClear" 
                  label="Clear Results" 
                  size="large"
                  imageMso="RecordsDelete"
                  onAction="OnClearClick" />
          
          <button id="btnExport" 
                  label="Export PDF" 
                  size="large"
                  imageMso="FilePrintQuick"
                  onAction="OnExportClick" />
          
          <button id="btnHelp" 
                  label="Help" 
                  size="large"
                  imageMso="Help"
                  onAction="OnHelpClick" />
          
        </group>
      </tab>
    </tabs>
  </ribbon>
</customUI>
```

Add callback module `RibbonCallbacks.bas`:

```vba
'Callback for CustomUI
Sub OnCalculateClick(control As IRibbonControl)
    MainInterface.RunCalculation
End Sub

Sub OnClearClick(control As IRibbonControl)
    MainInterface.ClearOutputs
End Sub

Sub OnExportClick(control As IRibbonControl)
    MainInterface.ExportToPDF
End Sub

Sub OnHelpClick(control As IRibbonControl)
    MainInterface.ShowHelp
End Sub
```

**Note**: To add custom ribbon, you need to:

1. Save workbook as .xlsm (macro-enabled)
2. Rename to .zip
3. Add customUI folder with customUI14.xml and _rels folder
4. Rename back to .xlsm

Or use the **Office RibbonX Editor** tool (free download).

---

## Testing Checklist

### Excel Template Tests

- [ ] All input sheets have correct headers
- [ ] Example rows are filled in row 2
- [ ] All dropdown validations work correctly
- [ ] Number validation prevents negative values
- [ ] Date columns have proper formatting
- [ ] Config_Parameters has all default values
- [ ] Reference sheets are pre-filled
- [ ] Output sheets are present but empty
- [ ] Instructions sheet is complete

### VBA Tests

- [ ] RunCalculation macro starts successfully
- [ ] Progress form displays and updates
- [ ] Input validation catches empty vessels
- [ ] Input validation catches invalid dates
- [ ] Python script path is found correctly
- [ ] Python version check works
- [ ] ClearOutputs clears all output sheets
- [ ] ExportToPDF prompts for filename
- [ ] ShowHelp navigates to Instructions sheet
- [ ] Error messages are in Russian
- [ ] Log file is created

### Platform Tests

Platform-specific testing:

- [ ] Windows 10 with Excel 2016
- [ ] Windows 10 with Excel 2019
- [ ] Windows 11 with Excel 2019
- [ ] Windows 11 with Excel 365

### Localization Tests

- [ ] Russian locale displays correctly
- [ ] Date formats work (DD.MM.YYYY vs MM/DD/YYYY)
- [ ] Number formats work (comma vs period for decimals)
- [ ] Cyrillic characters in headers
- [ ] Cyrillic characters in data

### Integration Tests

- [ ] Run full calculation with test_case_1
- [ ] Run full calculation with test_case_2
- [ ] Run full calculation with test_case_3
- [ ] Verify output sheets are populated
- [ ] Verify Gantt chart is generated
- [ ] Verify costs are calculated
- [ ] Export to PDF works
- [ ] Re-run calculation updates results

### User Acceptance Tests

Have a real dispatcher test:

- [ ] Can understand instructions
- [ ] Can enter vessel data
- [ ] Can enter rail schedule
- [ ] Can run calculation
- [ ] Can interpret results
- [ ] Can export PDF
- [ ] Overall satisfaction rating

---

## File Organization

Final project structure:

```
prihodko/
├── terminal_template.xlsx          # Main Excel interface
├── terminal_optimizer/              # Python package
│   ├── __init__.py
│   ├── main.py                      # Entry point
│   ├── domain_models.py
│   ├── excel_io.py
│   ├── sequence_generator.py
│   ├── balance_calculator.py
│   ├── wagon_manager.py
│   ├── critical_point.py
│   ├── risk_analysis.py
│   └── validation.py
├── templates/                       # Reference data
│   ├── tank_config.csv
│   ├── product_compatibility_matrix.csv
│   ├── operation_time_standards.csv
│   └── palm_fraction_priorities.csv
├── test_data/                       # Test scenarios
├── docs/                            # Documentation
│   ├── EXCEL_TEMPLATE_GUIDE.md     # This file
│   ├── PROJECT_STATUS.md
│   └── README.md
├── vba/                             # VBA source code
│   ├── MainInterface.bas
│   ├── ProgressForm.frm
│   └── RibbonCallbacks.bas (optional)
└── requirements.txt                 # Python dependencies
```

---

## Troubleshooting

### Common Issues

**1. "Python not found"**

- Solution: Install Python 3.8+, add to PATH
- Verify: Run `python --version` in Command Prompt

**2. "Script failed with exit code"**

- Solution: Check `calculation_log.txt` for details
- Verify Python packages: `pip install -r requirements.txt`

**3. "Output sheets not updating"**

- Solution: Ensure Python script completes successfully
- Check that Excel file path has no special characters

**4. "Macro security warning"**

- Solution: Enable macro content when prompted
- Or adjust security settings in Trust Center

**5. "Export PDF fails"**

- Solution: Ensure output sheets have data
- Try selecting just one sheet to export

### Getting Help

- Check documentation in `docs/` folder
- Review calculation log file
- Contact development team

---

## Appendix: VBA Code Reference

### Complete VBA Module List

1. **MainInterface.bas** - Main calculation and UI logic
2. **ProgressForm.frm** - Progress dialog
3. **RibbonCallbacks.bas** - Custom ribbon callbacks (optional)

### Excel Formula Examples

#### Dynamic Named Ranges

Create named ranges for dropdowns:

```
Name: CargoTypes
Refers to: ={"sunflower";"palm"}

Name: PriorityLevels
Refers to: ={"HIGH";"MEDIUM";"LOW"}

Name: TankStates
Refers to: ={"idle";"filling";"discharging";"analysis";"cleaning";"available"}
```

Then use in Data Validation: `=CargoTypes`

---

## Version History

- **v1.0** (2025-12-19): Initial template design
- Future: Excel365 dynamic arrays, Power Query integration

---

**End of Excel Template Setup Guide**
