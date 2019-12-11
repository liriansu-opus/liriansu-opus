@ECHO OFF

IF "%~1" == "" (
    %CODEENV%\Git\bin\bash.exe -l -i
) ELSE (
    %CODEENV%\Git\bin\bash.exe -c "%*"
)
