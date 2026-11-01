Attribute VB_Name = "ReportMacro"
'==========================================================================
' One-click monthly KPI report
' 1. Asks for a month's CSV extract (from sql/06_monthly_extract.sql)
' 2. Checks the columns, loads the rows into the Data sheet
' 3. Recalculates the Report sheet (KPI vs target, PASS / FAIL)
' 4. Saves the Report sheet as reports\KPI_Report_YYYY-MM.pdf
'==========================================================================
Option Explicit

Private Const EXPECTED_HEADER As String = _
    "order_id,order_date,market,shipping_mode,customer_segment,category," & _
    "days_real,days_scheduled,sales,discount,order_item_total,profit"

Public Sub GenerateReport()
    Dim csvPath As Variant, src As Workbook, wsData As Worksheet, wsRep As Worksheet
    Dim header As String, c As Long, lastRow As Long, monthTag As String, outDir As String, outFile As String

    csvPath = Application.GetOpenFilename("CSV files (*.csv),*.csv", , "Choose the month's order extract")
    If VarType(csvPath) = vbBoolean Then Exit Sub          ' user pressed Cancel

    Application.ScreenUpdating = False
    Set wsData = ThisWorkbook.Worksheets("Data")
    Set wsRep = ThisWorkbook.Worksheets("Report")

    ' --- open the CSV and check it has the expected columns ---
    Set src = Workbooks.Open(Filename:=csvPath, Local:=False)
    With src.Worksheets(1)
        For c = 1 To 12
            header = header & IIf(c > 1, ",", "") & LCase$(Trim$(.Cells(1, c).Value))
        Next c
        If header <> EXPECTED_HEADER Then
            src.Close SaveChanges:=False
            Application.ScreenUpdating = True
            MsgBox "This file does not have the expected columns." & vbCrLf & _
                   "Expected: " & EXPECTED_HEADER, vbExclamation, "KPI report"
            Exit Sub
        End If
        lastRow = .Cells(.Rows.Count, 1).End(xlUp).Row

        ' --- replace the old month's data ---
        wsData.Cells.ClearContents
        .Range(.Cells(1, 1), .Cells(lastRow, 12)).Copy Destination:=wsData.Range("A1")
    End With
    src.Close SaveChanges:=False
    wsData.Range("B2:B" & lastRow).NumberFormat = "yyyy-mm-dd hh:mm"

    ' --- recalculate and read the month ---
    Application.Calculate
    monthTag = Format(Application.WorksheetFunction.Min(wsData.Range("B2:B" & lastRow)), "yyyy-mm")

    ' --- save the Report sheet as a PDF ---
    outDir = ThisWorkbook.Path & Application.PathSeparator & "reports"
    If Dir(outDir, vbDirectory) = "" Then MkDir outDir
    outFile = outDir & Application.PathSeparator & "KPI_Report_" & monthTag & ".pdf"
    wsRep.ExportAsFixedFormat Type:=xlTypePDF, Filename:=outFile, Quality:=xlQualityStandard, _
                              IncludeDocProperties:=False, OpenAfterPublish:=False

    Application.ScreenUpdating = True
    wsRep.Activate
    MsgBox "Report for " & monthTag & " is ready." & vbCrLf & _
           Application.WorksheetFunction.CountIf(wsRep.Range("E8:E13"), "PASS") & " of 6 KPIs passed." & vbCrLf & _
           "Saved: " & outFile, vbInformation, "KPI report"
End Sub
