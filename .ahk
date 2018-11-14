#NoEnv  ; Recommended for performance and compatibility with future AutoHotkey releases.
; #Warn  ; Enable warnings to assist with detecting common errors.
SendMode Input  ; Recommended for new scripts due to its superior speed and reliability.
SetWorkingDir %A_ScriptDir%  ; Ensures a consistent starting directory.

!f::
    InputBox, PR, PRPR, What's the PR number?
    Run, https://aria2.kezaihui.com/stdev/forseti-be/merge_requests/%PR%
Return

^!q::
    If WinActive("企业微信")
        WinClose, 企业微信
    Else
        Run, C:\CodeEnv\WXWork\2.6.1.1329\WXWorkCommand.exe
Return

