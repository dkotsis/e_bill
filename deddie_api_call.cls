VERSION 1.0 CLASS
BEGIN
  MultiUse = -1  'True
END
Attribute VB_Name = "Sheet1"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = True


Private Sub CommandButton1_Click()

' ������ API Caller 1.00 | Panagiotis Drakakis 6/3/2024

    Dim http As Object
    Set http = CreateObject("WinHttp.WinHttpRequest.5.1")
    Dim body, supplyNumbertxt, taxNumbertxt, fromDatetxt, toDatetxt, analysisTypetxt, classTypetxt, confirmedDataFlagtxt, hourAnalysisFlagtxt As String
    Dim i As Double
    Dim sName As String
    
    ' Get Values from excel sheet
    
    analysisTypetxt = Cells(9, 8)
    classTypetxt = Cells(10, 8)
    confirmedDataFlagtxt = Cells(11, 8)
    fromDatetxt = Cells(7, 8)
    hourAnalysisFlagtxt = Cells(12, 8)
    supplyNumbertxt = Cells(5, 8)
    taxNumbertxt = Cells(6, 8)
    toDatetxt = Cells(8, 8)
            
    ' Check if the values are correct
    
    If supplyNumbertxt = "0" Or Not IsNumeric(supplyNumbertxt) Then
        MsgBox "���������� ������� �������!"
        Exit Sub
    End If
    
    If taxNumbertxt = "0" Or Not IsNumeric(taxNumbertxt) Or Len(taxNumbertxt) <> 9 Then
        MsgBox "��������� ���!"
        Exit Sub
    End If
    
    ' Make API Body
    
    body = "{" & """analysisType""" & ":" & """" & analysisTypetxt & """" & "," _
               & """classType""" & ":" & """" & classTypetxt & """" & "," _
               & """confirmedDataFlag""" & ":" & """" & confirmedDataFlagtxt & """" & "," _
               & """fromDate""" & ":" & """" & fromDatetxt & """" & "," _
               & """hourAnalysisFlag""" & ":" & """" & hourAnalysisFlagtxt & """" & "," _
               & """supplyNumber""" & ":" & """" & supplyNumbertxt & """" & "," _
               & """taxNumber""" & ":" & """" & taxNumbertxt & """" & "," _
               & """toDate""" & ":" & """" & toDatetxt & """" & "}"
    
    http.Open "POST", "https://apps.deddie.gr/mdp/rest/getCurves", False
    http.SetRequestHeader "token", "9eaa5cb27e25e6e8f6ab33a147d9a"
    http.SetRequestHeader "scope", "API"
    http.SetRequestHeader "Content-Type", "application/json;charset=utf-8"
    http.Send (body)
    
    ' Check Connection Status, If <> 200 stop the procedure
    
    If http.Status = 200 Then
        Cells(17, 2).Value = "�������� �������"
        Cells(17, 2).Interior.ColorIndex = 43

    Else
        Cells(17, 2).Value = "������ : " & http.Status & " - " & http.StatusText
        Cells(17, 2).Interior.ColorIndex = 3
        Exit Sub
    End If
    
' Parse the Response

Dim JSON As Object
Set JSON = JsonConverter.ParseJson(http.ResponseText)
    
    sName = supplyNumbertxt & (Format(Now, "(dd.mm.yy)hh.mm.ss"))
    
    ' Check if sheet exist if so, delete it! (This statement should not be triggered... in theory)
    
    If WorksheetExists(sName) Then
        Sheets(sName).Delete
    End If
    
    ' Create a new sheet and name it properly!

    Sheets.Add(After:=Sheets(Sheets.Count)).Name = sName
    Sheets(sName).Activate
    
    ' Place the responded data
    i = 2
    
    Sheets(sName).Cells(1, 1) = "����������"
    Sheets(sName).Cells(1, 2) = "��������"
    
    For Each c In JSON("curves")
        Sheets(sName).Cells(i, 2) = c("consumption")
        Sheets(sName).Cells(i, 1) = (Format(c("meterDate"), "mm/dd/yyyy hh:mm"))
        i = i + 1
    Next c
    
    Sheets(sName).UsedRange.EntireColumn.AutoFit
    
    CommandButton1.Caption = "�������"
    
    Sheets("APIForm").Cells(17, 2).Value = "������������ " & i - 2 & " ��������."
    Sheets("APIForm").Cells(17, 2).Interior.ColorIndex = 33
    Sheets("APIForm").Activate

End Sub

Private Sub cmdMSubmit_Click()
    Dim x, offset, totalSupplyNumber As Integer
    Dim supplyNumbertmp As String
    
    Dim http As Object
    Set http = CreateObject("WinHttp.WinHttpRequest.5.1")
    Dim body, supplyNumbertxt, taxNumbertxt, fromDatetxt, toDatetxt, analysisTypetxt, classTypetxt, confirmedDataFlagtxt, hourAnalysisFlagtxt As String
    Dim i As Double
    Dim sName As String
    
    ' Get Values from excel sheet
    
    analysisTypetxt = Cells(9, 8)
    classTypetxt = Cells(10, 8)
    confirmedDataFlagtxt = Cells(11, 8)
    fromDatetxt = Cells(7, 8)
    hourAnalysisFlagtxt = Cells(12, 8)
    taxNumbertxt = Cells(6, 8)
    toDatetxt = Cells(8, 8)

    totalSupplyNumber = Cells(13, 8).Value
    
    
    x = 0
    i = 2
    
    sName = "REPORT - " & (Format(Now, "(dd.mm.yy)hh.mm.ss"))
    
    If WorksheetExists(sName) Then
        Sheets(sName).Delete
    End If
    
    ' Create a new sheet and name it properly!

    Sheets.Add(After:=Sheets(Sheets.Count)).Name = sName
    
    
    For x = 1 To totalSupplyNumber
        
        supplyNumbertxt = Cells(18 + x, 2).Value

        body = "{" & """analysisType""" & ":" & """" & analysisTypetxt & """" & "," _
                & """classType""" & ":" & """" & classTypetxt & """" & "," _
                & """confirmedDataFlag""" & ":" & """" & confirmedDataFlagtxt & """" & "," _
                & """fromDate""" & ":" & """" & fromDatetxt & """" & "," _
                & """hourAnalysisFlag""" & ":" & """" & hourAnalysisFlagtxt & """" & "," _
                & """supplyNumber""" & ":" & """" & supplyNumbertxt & """" & "," _
                & """taxNumber""" & ":" & """" & taxNumbertxt & """" & "," _
                & """toDate""" & ":" & """" & toDatetxt & """" & "}"
    
        http.Open "POST", "https://apps.deddie.gr/mdp/rest/getCurves", False
        http.SetRequestHeader "token", "9be1deeb6982562f168cd8256fe1750d8fb355cb"
        http.SetRequestHeader "scope", "API"
        http.SetRequestHeader "Content-Type", "application/json;charset=utf-8"
        http.Send (body)
    
    ' Check Connection Status, If <> 200 stop the procedure
    
    If http.Status = 200 Then
        Cells(17, 2).Value = "�������� �������"
        Cells(17, 2).Interior.ColorIndex = 43

    Else
        Cells(17, 2).Value = "������ : " & http.Status & " - " & http.StatusText
        Cells(17, 2).Interior.ColorIndex = 3
        Exit Sub
    End If
    
    '----
    
    ' Parse the Response

    Dim JSON As Object
    Set JSON = JsonConverter.ParseJson(http.ResponseText)
    

    
    ' Place the responded data

    Sheets(sName).Cells(1, 1) = "������� �������"
    Sheets(sName).Cells(1, 2) = "����������"
    Sheets(sName).Cells(1, 3) = "��������"
    
    For Each c In JSON("curves")
        Sheets(sName).Cells(i, 3) = c("consumption")
        Sheets(sName).Cells(i, 2) = (Format(c("meterDate"), "mm/dd/yyyy hh:mm"))
        Sheets(sName).Cells(i, 1) = supplyNumbertxt
        i = i + 1
    Next c
    
    Sheets(sName).UsedRange.EntireColumn.AutoFit
    
    CommandButton1.Caption = "�������"
    
    Sheets("APIForm").Cells(17, 2).Value = "������������ " & i - 2 & " ��������."
    Sheets("APIForm").Cells(17, 2).Interior.ColorIndex = 33
    Sheets("APIForm").Activate
    '----
    
    
    Next x
    
    
    
End Sub


' Notify the user SOMEHOW that the script is working... I know... It's not the best solution, but hey! Better than nothing!
Private Sub CommandButton1_MouseDown(ByVal Button As Integer, ByVal Shift As Integer, ByVal x As Single, ByVal Y As Single)
    CommandButton1.Caption = "�������� ����������..."
    ActiveWorkbook.RefreshAll
End Sub

' Check If Worksheet Exist Function
Function WorksheetExists(sName As String) As Boolean
    WorksheetExists = Evaluate("ISREF('" & sName & "'!A1)")
End Function




