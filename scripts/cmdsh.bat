@ECHO OFF

IF "%~1" == "" (
    C:\CodeEnv\Git\usr\bin\bash.exe -l -i
) ELSE (
    cmd %*
)
