@echo off
setlocal

if defined DEVECO_CANGJIE_HOME (
  set "CJ_BUILD_TOOLS=%DEVECO_CANGJIE_HOME%\build-tools"
) else (
  set "CJ_BUILD_TOOLS="
  for /f "delims=" %%d in ('dir /b /ad "%USERPROFILE%\.cangjie-sdk" 2^>nul ^| sort /r') do (
    if exist "%USERPROFILE%\.cangjie-sdk\%%d\cangjie\build-tools" (
      set "CJ_BUILD_TOOLS=%USERPROFILE%\.cangjie-sdk\%%d\cangjie\build-tools"
      goto :found_tools
    )
  )
)

:found_tools
if not "%CJ_BUILD_TOOLS%"=="" (
  if exist "%CJ_BUILD_TOOLS%\bin" set "PATH=%CJ_BUILD_TOOLS%\bin;%PATH%"
  if exist "%CJ_BUILD_TOOLS%\lib" set "PATH=%CJ_BUILD_TOOLS%\lib;%PATH%"
  if exist "%CJ_BUILD_TOOLS%\tools\bin" set "PATH=%CJ_BUILD_TOOLS%\tools\bin;%PATH%"
  if exist "%CJ_BUILD_TOOLS%\tools\lib" set "PATH=%CJ_BUILD_TOOLS%\tools\lib;%PATH%"
  if exist "%CJ_BUILD_TOOLS%\third_party\llvm\bin" set "PATH=%CJ_BUILD_TOOLS%\third_party\llvm\bin;%PATH%"
  if exist "%CJ_BUILD_TOOLS%\runtime\lib\windows_x86_64_cjnative" set "PATH=%CJ_BUILD_TOOLS%\runtime\lib\windows_x86_64_cjnative;%PATH%"
)

cjpm.exe build
exit /b %errorlevel%
