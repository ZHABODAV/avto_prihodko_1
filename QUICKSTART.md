# Как получить результат работы приложения

## Способ 1: Через Excel (самый простой)

### Первый раз (настройка Excel)

1. Откройте файл `terminal_template.xlsx`
2. Нажмите Alt+F11 (откроется редактор VBA)
3. В меню выберите File → Import File
4. Найдите и выберите файл `vba/MainInterface.bas`
5. Закройте редактор VBA
6. В Excel: File → Options → Trust Center → Trust Center Settings → Macro Settings
7. Выберите "Enable all macros"
8. Перезапустите Excel

### Каждый раз (основная работа)

1. Откройте файл `terminal_template.xlsx`
2. Заполните данные в листах Input_Vessels, Input_CurrentState, Input_Rail
3. Нажмите кнопку "Calculate Plan" (если нет кнопки - нажмите Alt+F8, выберите RunCalculation)
4. Результаты появятся в листах Output_Operations, Output_TankBalance, Output_RailSchedule, Output_Warnings

## Способ 2: Через командную строку

1. Откройте командную строку в папке с программой
2. Запустите:

   ```
   run.bat
   ```

3. Программа создаст файл с результатами

## Способ 3: Через Python

1. Откройте командную строку
2. Активируйте виртуальное окружение:

   ```
   venv\Scripts\activate
   ```

3. Запустите:

   ```
   python -m terminal_optimizer --input terminal_template.xlsx --output results.xlsx
   ```

4. Результаты сохранятся в файл results.xlsx

## Что вы получите

В результате работы программы создаются 4 листа с данными:

1. **Output_Operations** - список всех операций по порядку (когда, что, куда)
2. **Output_TankBalance** - сколько продукта в каждом баке по часам
3. **Output_RailSchedule** - расписание вагонов
4. **Output_Warnings** - предупреждения о возможных проблемах

## Первичная установка

Если программа еще не установлена:

1. Запустите `install.bat`
2. Дождитесь завершения установки
3. После этого можете использовать любой из способов выше

## Проблемы

Если не работает:

- Проверьте, что установлен Python 3.9 или новее
- Проверьте, что Excel разрешает макросы
- Посмотрите файлы в папке logs для деталей ошибки
