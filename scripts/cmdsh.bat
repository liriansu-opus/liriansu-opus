@ECHO OFF

IF "%~1" == "" (
    %CODEENV%\Git\usr\bin\bash.exe -l -i
) ELSE (
    cmd %*
)
