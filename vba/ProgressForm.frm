VERSION 5.00
Begin {C62A69F0-16DC-11CE-9E98-00AA00574A4F} ProgressForm 
   Caption         =   "Расчет - Terminal Optimizer"
   ClientHeight    =   2040
   ClientLeft      =   120
   ClientTop       =   465
   ClientWidth     =   6615
   OleObjectBlob   =   "ProgressForm.frx":0000
   StartUpPosition =   1  'CenterOwner
End
Attribute VB_Name = "ProgressForm"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
'==============================================================================
' Terminal Optimizer - Progress Form
'==============================================================================
' This form shows progress during calculation
'
' Author: Terminal Optimizer Team
' Version: 1.0
'==============================================================================

Option Explicit

Public Sub UpdateProgress(percentComplete As Integer, statusMessage As String)
    '--------------------------------------------------------------------------
    ' Update the progress bar and status message
    ' Args:
    '   percentComplete: Progress percentage (0-100)
    '   statusMessage: Status message to display
    '--------------------------------------------------------------------------
    
    ' Ensure percent is in valid range
    If percentComplete < 0 Then percentComplete = 0
    If percentComplete > 100 Then percentComplete = 100
    
    ' Update progress bar
    Me.ProgressBar.Width = Me.ProgressBarBackground.Width * (percentComplete / 100)
    
    ' Update labels
    Me.PercentLabel.Caption = percentComplete & "%"
    Me.StatusLabel.Caption = statusMessage
    
    ' Refresh the form
    Me.Repaint
    DoEvents
End Sub

Private Sub UserForm_Initialize()
    '--------------------------------------------------------------------------
    ' Initialize the form controls
    '--------------------------------------------------------------------------
    
    ' Set initial progress to 0
    UpdateProgress 0, "Инициализация..."
End Sub
