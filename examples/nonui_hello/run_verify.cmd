@echo off
setlocal
set "CJ_BUILD_TOOLS=%USERPROFILE%\.cangjie-sdk\6.0\cangjie\build-tools"
if exist "%CJ_BUILD_TOOLS%\bin" set "PATH=%CJ_BUILD_TOOLS%\bin;%PATH%"
if exist "%CJ_BUILD_TOOLS%\lib" set "PATH=%CJ_BUILD_TOOLS%\lib;%PATH%"
if exist "%CJ_BUILD_TOOLS%\tools\bin" set "PATH=%CJ_BUILD_TOOLS%\tools\bin;%PATH%"
if exist "%CJ_BUILD_TOOLS%\tools\lib" set "PATH=%CJ_BUILD_TOOLS%\tools\lib;%PATH%"
if exist "%CJ_BUILD_TOOLS%\third_party\llvm\bin" set "PATH=%CJ_BUILD_TOOLS%\third_party\llvm\bin;%PATH%"
if exist "%CJ_BUILD_TOOLS%\runtime\lib\windows_x86_64_cjnative" set "PATH=%CJ_BUILD_TOOLS%\runtime\lib\windows_x86_64_cjnative;%PATH%"

cjpm.exe build
exit /b %errorlevel%
