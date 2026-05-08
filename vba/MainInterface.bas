Attribute VB_Name = "MainInterface"
'==============================================================================
' Terminal Optimizer - Main Interface Module
'==============================================================================
' This module provides the main user interface functions for running the
' terminal optimization calculation from Excel.
'
' Author: Terminal Optimizer Team
' Version: 1.0
' Last Updated: 2025-12-19
'==============================================================================

Option Explicit

' Configuration constants
Private Const PYTHON_SCRIPT = "terminal_optimizer\main.py"
Private Const LOG_FILE = "calculation_log.txt"

'==============================================================================
' Main Calculation Runner
'==============================================================================

Public Sub RunCalculation()
    '--------------------------------------------------------------------------
    ' Main entry point for running the optimization calculation
    ' Called from the "Calculate Plan" ribbon button
    '--------------------------------------------------------------------------
    On Error GoTo ErrorHandler
    
    Dim startTime As Double
    startTime = Timer
    
    ' Show progress form
    Dim progressForm As ProgressForm
    Set progressForm = New ProgressForm
    progressForm.Show vbModeless
    progressForm.UpdateProgress 0, "Начало расчета..."
    DoEvents
    
    ' Step 1: Validate inputs
    progressForm.UpdateProgress 10, "Проверка входных данных..."
    DoEvents
    
    If Not ValidateInputs() Then
        progressForm.Hide
        Unload progressForm
        MsgBox "Ошибка валидации входных данных!" & vbCrLf & vbCrLf & _
               "Проверьте, что все обязательные листы заполнены корректно.", _
               vbExclamation, "Ошибка валидации"
        Exit Sub
    End If
    
    ' Step 2: Export data to CSV (if needed) or use Excel directly
    progressForm.UpdateProgress 20, "Подготовка данных..."
    DoEvents
    
    ' Excel file path
    Dim excelPath As String
    excelPath = ThisWorkbook.FullName
    
    ' Step 3: Check Python installation
    progressForm.UpdateProgress 30, "Проверка Python..."
    DoEvents
    
    If Not CheckPythonInstallation() Then
        progressForm.Hide
        Unload progressForm
        MsgBox "Python не найден!" & vbCrLf & vbCrLf & _
               "Установите Python 3.8 или выше и добавьте его в PATH.", _
               vbCritical, "Ошибка Python"
        Exit Sub
    End If
    
    ' Step 4: Run Python script
    progressForm.UpdateProgress 40, "Запуск расчета..."
    DoEvents
    
    Dim scriptPath As String
    scriptPath = GetScriptPath()
    
    If Not RunPythonScript(scriptPath, excelPath, progressForm) Then
        progressForm.Hide
        Unload progressForm
        MsgBox "Ошибка при выполнении расчета!" & vbCrLf & vbCrLf & _
               "Проверьте лог-файл для деталей: " & LOG_FILE, _
               vbCritical, "Ошибка расчета"
        Exit Sub
    End If
    
    ' Step 5: Import results
    progressForm.UpdateProgress 90, "Импорт результатов..."
    DoEvents
    
    Dim fso As Object
    Set fso = CreateObject("Scripting.FileSystemObject")
    Dim baseName As String
    Dim extension As String
    baseName = fso.GetBaseName(excelPath)
    extension = "." & fso.GetExtensionName(excelPath)
    
    Dim resultsPath As String
    resultsPath = fso.GetParentFolderName(excelPath) & "\" & baseName & "_optimized" & extension
    
    ImportResults resultsPath
    
    ' Step 6: Refresh output sheets
    RefreshOutputSheets
    
    ' Complete
    progressForm.UpdateProgress 100, "Готово!"
    Application.Wait (Now + TimeValue("0:00:01"))
    progressForm.Hide
    Unload progressForm
    
    ' Calculate elapsed time
    Dim elapsedTime As Double
    elapsedTime = Timer - startTime
    
    ' Show success message
    MsgBox "Расчет успешно завершен!" & vbCrLf & vbCrLf & _
           "Время выполнения: " & Format(elapsedTime, "0.0") & " сек", _
           vbInformation, "Успех"
    
    ' Activate first output sheet
    On Error Resume Next
    Worksheets("Output_Schedule").Activate
    On Error GoTo 0
    
    Exit Sub

ErrorHandler:
    On Error Resume Next
    progressForm.Hide
    Unload progressForm
    On Error GoTo 0
    
    MsgBox "Непредвиденная ошибка: " & Err.Description & vbCrLf & vbCrLf & _
           "Номер ошибки: " & Err.Number, vbCritical, "Ошибка"
End Sub

'==============================================================================
' Input Validation
'==============================================================================

Private Function ValidateInputs() As Boolean
    '--------------------------------------------------------------------------
    ' Validate that all required input sheets have data
    ' Returns: True if validation passes
    '--------------------------------------------------------------------------
    On Error GoTo ValidationError
    
    ValidateInputs = False
    
    ' Check required sheets exist
    Dim requiredSheets As Variant
    requiredSheets = Array("Input_Vessels", "Input_Rail", "Input_Demand", _
                          "Input_CurrentState")
    
    Dim sheetName As Variant
    Dim ws As Worksheet
    
    For Each sheetName In requiredSheets
        On Error Resume Next
        Set ws = Worksheets(CStr(sheetName))
        On Error GoTo ValidationError
        
        If ws Is Nothing Then
            MsgBox "Отсутствует лист: " & sheetName, vbExclamation, "Ошибка"
            Exit Function
        End If
        
        ' Check sheet has headers and at least one row of data
        If ws.Cells(1, 1).Value = "" Then
            MsgBox "Лист '" & sheetName & "' не имеет заголовков!", _
                   vbExclamation, "Ошибка"
            Exit Function
        End If
    Next sheetName
    
    ' Check Vessels sheet has data (required)
    Set ws = Worksheets("Input_Vessels")
    If ws.Cells(2, 1).Value = "" Then
        MsgBox "Лист 'Input_Vessels' не содержит данных!" & vbCrLf & _
               "Необходимо добавить хотя бы одно судно.", _
               vbExclamation, "Ошибка"
        Exit Function
    End If
    
    ' Validate date formats in Vessels
    Dim lastRow As Long
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row
    
    Dim i As Long
    For i = 2 To lastRow
        If ws.Cells(i, 1).Value <> "" Then
            ' Check ETA column (column 2)
            If Not IsDate(ws.Cells(i, 2).Value) Then
                MsgBox "Неверный формат даты в строке " & i & " листа 'Input_Vessels'", _
                       vbExclamation, "Ошибка"
                Exit Function
            End If
            
            ' Check volume is positive
            If Not IsNumeric(ws.Cells(i, 4).Value) Or ws.Cells(i, 4).Value <= 0 Then
                MsgBox "Неверный объем в строке " & i & " листа 'Input_Vessels'", _
                       vbExclamation, "Ошибка"
                Exit Function
            End If
        End If
    Next i
    
    ValidateInputs = True
    Exit Function
    
ValidationError:
    MsgBox "Ошибка валидации: " & Err.Description, vbExclamation, "Ошибка"
    ValidateInputs = False
End Function

'==============================================================================
' Python Integration
'==============================================================================

Private Function CheckPythonInstallation() As Boolean
    '--------------------------------------------------------------------------
    ' Check if Python is installed and accessible
    ' Returns: True if Python is available
    '--------------------------------------------------------------------------
    On Error GoTo PythonError
    
    CheckPythonInstallation = False
    
    ' Try to run python --version
    Dim result As String
    result = RunCommand("python --version")
    
    If InStr(result, "Python") > 0 Then
        CheckPythonInstallation = True
    Else
        ' Try python3
        result = RunCommand("python3 --version")
        If InStr(result, "Python") > 0 Then
            CheckPythonInstallation = True
        End If
    End If
    
    Exit Function
    
PythonError:
    CheckPythonInstallation = False
End Function

Private Function GetScriptPath() As String
    '--------------------------------------------------------------------------
    ' Get the full path to the Python script
    ' Returns: Full path to main.py
    '--------------------------------------------------------------------------
    Dim workbookDir As String
    workbookDir = ThisWorkbook.Path
    
    ' Check if script exists in same directory
    Dim scriptPath As String
    scriptPath = workbookDir & "\" & PYTHON_SCRIPT
    
    If Dir(scriptPath) = "" Then
        ' Try parent directory
        Dim parentDir As String
        parentDir = Left(workbookDir, InStrRev(workbookDir, "\") - 1)
        scriptPath = parentDir & "\" & PYTHON_SCRIPT
    End If
    
    GetScriptPath = scriptPath
End Function

Private Function RunPythonScript(scriptPath As String, excelPath As String, _
                                 progressForm As ProgressForm) As Boolean
    '--------------------------------------------------------------------------
    ' Run the Python optimization script
    ' Args:
    '   scriptPath: Path to the Python script
    '   excelPath: Path to the Excel workbook
    '   progressForm: Progress form to update
    ' Returns: True if successful
    '--------------------------------------------------------------------------
    On Error GoTo ScriptError
    
    RunPythonScript = False
    
    ' Build command
    Dim cmd As String
    cmd = "python """ & scriptPath & """ --excel """ & excelPath & """ --output-excel"
    
    ' Add optional arguments from Settings sheet
    Dim wsSettings As Worksheet
    On Error Resume Next
    Set wsSettings = Worksheets("Settings")
    On Error GoTo ScriptError
    
    If Not wsSettings Is Nothing Then
        ' Run Mode
        Dim runMode As String
        runMode = LCase(Trim(wsSettings.Range("B2").Value))
        If runMode = "palm only" Then
            cmd = cmd & " --mode palm_only"
        ElseIf runMode = "sunflower only" Then
            cmd = cmd & " --mode sunflower_only"
        End If
        
        ' Optimize Sequence
        Dim optimize As String
        optimize = LCase(Trim(wsSettings.Range("B3").Value))
        If optimize = "yes" Or optimize = "true" Then
            cmd = cmd & " --optimize"
        End If
        
        ' Vessel Filter
        Dim vesselID As String
        vesselID = Trim(wsSettings.Range("B4").Value)
        If vesselID <> "" Then
            cmd = cmd & " --vessel """ & vesselID & """"
        End If
    End If
    
    ' Write command to log
    WriteLog "Running command: " & cmd
    
    ' Create WScript.Shell object for better process control
    Dim shell As Object
    Set shell = CreateObject("WScript.Shell")
    
    ' Run command and wait
    Dim exitCode As Long
    exitCode = shell.Run("cmd /c " & cmd & " > """ & LOG_FILE & """ 2>&1", 0, True)
    
    ' Check exit code
    If exitCode = 0 Then
        RunPythonScript = True
        WriteLog "Script completed successfully"
    Else
        WriteLog "Script failed with exit code: " & exitCode
    End If
    
    Exit Function
    
ScriptError:
    WriteLog "Error running script: " & Err.Description
    RunPythonScript = False
End Function

Private Function RunCommand(cmd As String) As String
    '--------------------------------------------------------------------------
    ' Run a shell command and return output
    ' Args:
    '   cmd: Command to run
    ' Returns: Command output
    '--------------------------------------------------------------------------
    On Error Resume Next
    
    Dim shell As Object
    Set shell = CreateObject("WScript.Shell")
    
    Dim exec As Object
    Set exec = shell.exec("cmd /c " & cmd)
    
    ' Wait for completion (with timeout)
    Dim timeout As Double
    timeout = Timer + 5 ' 5 second timeout
    
    Do While exec.Status = 0 And Timer < timeout
        DoEvents
    Loop
    
    If exec.Status = 1 Then
        RunCommand = exec.StdOut.ReadAll
    Else
        RunCommand = ""
    End If
End Function

'==============================================================================
' Output Management
'==============================================================================

Public Sub ClearOutputs()
    '--------------------------------------------------------------------------
    ' Clear all output sheets
    ' Called from the "Clear Results" ribbon button
    '--------------------------------------------------------------------------
    On Error Resume Next
    
    Dim response As VbMsgBoxResult
    response = MsgBox("Очистить все результаты расчета?" & vbCrLf & vbCrLf & _
                      "Это действие нельзя отменить.", _
                      vbQuestion + vbYesNo, "Подтверждение")
    
    If response <> vbYes Then Exit Sub
    
    ' List of output sheets to clear
    Dim outputSheets As Variant
    outputSheets = Array("Output_Operations", "Output_TankBalance", "Output_RailSchedule", _
                        "Output_Warnings", "Output_Recommendations", "Output_RailDaily", "Output_Validation")
    
    Dim sheetName As Variant
    Dim ws As Worksheet
    
    For Each sheetName In outputSheets
        Set ws = Nothing
        Set ws = Worksheets(CStr(sheetName))
        
        If Not ws Is Nothing Then
            ' Clear all data except headers (row 1)
            ws.Range("A2:ZZ" & ws.Rows.Count).ClearContents
            ws.Range("A2:ZZ" & ws.Rows.Count).ClearFormats
        End If
    Next sheetName
    
    MsgBox "Результаты очищены", vbInformation, "Готово"
End Sub

Public Sub ExportToPDF()
    '--------------------------------------------------------------------------
    ' Export selected sheets to PDF
    ' Called from the "Export PDF" ribbon button
    '--------------------------------------------------------------------------
    On Error GoTo ExportError
    
    ' Ask user for save location
    Dim fileName As Variant
    fileName = Application.GetSaveAsFilename( _
        InitialFileName:="Terminal_Plan_" & Format(Now, "yyyy-mm-dd_hhmm") & ".pdf", _
        FileFilter:="PDF Files (*.pdf), *.pdf", _
        Title:="Сохранить план как PDF")
    
    If fileName = False Then Exit Sub ' User cancelled
    
    ' Select sheets to export
    Dim sheetsToExport As Variant
    sheetsToExport = Array("Output_Gantt", "Output_Railway", "Output_Costs")
    
    Dim ws As Worksheet
    Dim sheetArray() As Worksheet
    ReDim sheetArray(0 To UBound(sheetsToExport))
    
    Dim i As Long
    For i = 0 To UBound(sheetsToExport)
        On Error Resume Next
        Set ws = Worksheets(CStr(sheetsToExport(i)))
        On Error GoTo ExportError
        
        If Not ws Is Nothing Then
            Set sheetArray(i) = ws
        End If
    Next i
    
    ' Export to PDF
    ThisWorkbook.Sheets(sheetArray).ExportAsFixedFormat _
        Type:=xlTypePDF, _
        fileName:=CStr(fileName), _
        Quality:=xlQualityStandard, _
        IncludeDocProperties:=True, _
        IgnorePrintAreas:=False, _
        OpenAfterPublish:=True
    
    MsgBox "PDF экспортирован успешно!", vbInformation, "Успех"
    
    Exit Sub
    
ExportError:
    MsgBox "Ошибка при экспорте PDF: " & Err.Description, vbExclamation, "Ошибка"
End Sub

'==============================================================================
' Helper Functions
'==============================================================================

Private Sub RefreshOutputSheets()
    '--------------------------------------------------------------------------
    ' Refresh all output sheets (recalculate, reformat)
    '--------------------------------------------------------------------------
    On Error Resume Next
    
    ' Recalculate workbook
    Application.CalculateFull
    
    ' Auto-fit columns in output sheets
    Dim outputSheets As Variant
    outputSheets = Array("Output_Operations", "Output_TankBalance", "Output_RailSchedule", _
                        "Output_Warnings", "Output_Recommendations", "Output_RailDaily", "Output_Validation")
    
    Dim sheetName As Variant
    Dim ws As Worksheet
    
    For Each sheetName In outputSheets
        Set ws = Nothing
        Set ws = Worksheets(CStr(sheetName))
        
        If Not ws Is Nothing Then
            ws.Columns.AutoFit
        End If
    Next sheetName
End Sub

Private Sub ImportResults(resultsPath As String)
    '--------------------------------------------------------------------------
    ' Import results from the optimized file generated by Python
    '--------------------------------------------------------------------------
    On Error Resume Next
    
    If Dir(resultsPath) = "" Then
        ' Try checking if it exists without checking Dir (sometimes unreliable with network paths)
        ' But for now, just log and exit
        ' MsgBox "Файл с результатами не найден: " & resultsPath, vbExclamation, "Ошибка импорта"
        Exit Sub
    End If
    
    Dim sourceWb As Workbook
    Set sourceWb = Workbooks.Open(resultsPath, ReadOnly:=True)
    
    If sourceWb Is Nothing Then Exit Sub
    
    Dim sheetNames As Variant
    sheetNames = Array("Output_Operations", "Output_TankBalance", "Output_RailSchedule", _
                      "Output_Warnings", "Output_Recommendations", "Output_RailDaily", "Output_Validation")
    
    Dim sheetName As Variant
    Dim sourceWs As Worksheet
    Dim targetWs As Worksheet
    
    For Each sheetName In sheetNames
        Set sourceWs = Nothing
        Set targetWs = Nothing
        
        On Error Resume Next
        Set sourceWs = sourceWb.Worksheets(CStr(sheetName))
        Set targetWs = ThisWorkbook.Worksheets(CStr(sheetName))
        On Error GoTo 0
        
        If Not sourceWs Is Nothing And Not targetWs Is Nothing Then
            targetWs.Cells.Clear
            sourceWs.Cells.Copy Destination:=targetWs.Cells(1, 1)
        End If
    Next sheetName
    
    sourceWb.Close SaveChanges:=False
End Sub

Private Sub WriteLog(message As String)
    '--------------------------------------------------------------------------
    ' Write a message to the log file
    ' Args:
    '   message: Message to write
    '--------------------------------------------------------------------------
    Dim logPath As String
    logPath = ThisWorkbook.Path & "\" & LOG_FILE

    Dim fileNum As Integer
    Dim fileOpened As Boolean
    fileOpened = False

    On Error GoTo LogError

    fileNum = FreeFile
    Open logPath For Append As #fileNum
    fileOpened = True

    Print #fileNum, Format(Now, "yyyy-mm-dd hh:mm:ss") & " - " & message

    Close #fileNum
    fileOpened = False

    Exit Sub

LogError:
    ' Ensure file handle is closed in case of error
    If fileOpened Then
        On Error Resume Next
        Close #fileNum
        On Error GoTo 0
        fileOpened = False
    End If
End Sub

Public Sub ShowHelp()
    '--------------------------------------------------------------------------
    ' Show help/instructions
    ' Called from the "Help" ribbon button
    '--------------------------------------------------------------------------
    On Error Resume Next
    
    ' Try to navigate to Instructions sheet
    Dim ws As Worksheet
    Set ws = Worksheets("Instructions")
    
    If Not ws Is Nothing Then
        ws.Activate
    Else
        ' Show message box with basic help
        MsgBox "Инструкция по использованию Terminal Optimizer:" & vbCrLf & vbCrLf & _
               "1. Заполните входные данные на листах Input_*" & vbCrLf & _
               "2. Нажмите 'Calculate Plan' для запуска расчета" & vbCrLf & _
               "3. Просмотрите результаты на листах Output_*" & vbCrLf & _
               "4. Используйте 'Export PDF' для сохранения отчета" & vbCrLf & vbCrLf & _
               "Для подробной информации см. документацию.", _
               vbInformation, "Помощь"
    End If
End Sub
