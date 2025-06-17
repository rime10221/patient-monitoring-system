@echo off
:: 대기환자 모니터링 시스템 간이 설치 스크립트
:: 사용자 PC에 필요한 파일을 복사하고 바로가기를 생성합니다.

echo ===================================
echo 대기환자 모니터링 시스템 설치 프로그램
echo ===================================
echo.

:: 관리자 권한 확인
net session >nul 2>&1
if %errorLevel% == 0 (
    echo 관리자 권한으로 실행 중입니다.
) else (
    echo 참고: 일반 사용자 권한으로 실행 중입니다.
    echo 프로그램 폴더에 설치하려면 관리자 권한이 필요할 수 있습니다.
    echo.
)

:: 설치 경로 선택
set DEFAULT_PATH=%USERPROFILE%\대기환자모니터
set INSTALL_PATH=

echo 설치 경로를 선택하세요:
echo 1. 사용자 폴더에 설치 [%DEFAULT_PATH%]
echo 2. 프로그램 폴더에 설치 [C:\Program Files\대기환자모니터]
echo 3. 현재 폴더에 설치 [%CD%\대기환자모니터]
echo 4. 직접 경로 입력
set /p CHOICE="선택 (1-4, 기본값: 1): "

if "%CHOICE%"=="" set CHOICE=1
if "%CHOICE%"=="1" set INSTALL_PATH=%DEFAULT_PATH%
if "%CHOICE%"=="2" set INSTALL_PATH=C:\Program Files\대기환자모니터
if "%CHOICE%"=="3" set INSTALL_PATH=%CD%\대기환자모니터
if "%CHOICE%"=="4" (
    set /p INSTALL_PATH="설치 경로를 입력하세요: "
)

:: 경로가 선택되지 않은 경우 기본값 사용
if "%INSTALL_PATH%"=="" set INSTALL_PATH=%DEFAULT_PATH%

echo.
echo 선택한 설치 경로: %INSTALL_PATH%
echo.

:: 설치 확인
set /p CONFIRM="이 경로에 설치하시겠습니까? (Y/N, 기본값: Y): "
if /i "%CONFIRM%"=="N" (
    echo 설치가 취소되었습니다.
    goto :eof
)

:: 설치 디렉토리 생성
echo.
echo 설치 디렉토리 생성 중...
if not exist "%INSTALL_PATH%" mkdir "%INSTALL_PATH%"

:: 파일 복사
echo 파일 복사 중...
if exist "dist\대기환자모니터.exe" (
    copy "dist\대기환자모니터.exe" "%INSTALL_PATH%\" >nul
    echo - 대기환자모니터.exe 복사 완료
) else (
    echo 오류: 대기환자모니터.exe 파일이 없습니다.
    echo 먼저 build_setup.py 스크립트를 실행하여 실행 파일을 생성하세요.
    pause
    goto :eof
)

if exist "monitoring_voice.mp3" (
    copy "monitoring_voice.mp3" "%INSTALL_PATH%\" >nul
    echo - monitoring_voice.mp3 복사 완료
) else (
    echo 경고: monitoring_voice.mp3 파일이 없습니다. 알림음이 작동하지 않을 수 있습니다.
)

if exist "monitor_config.json" (
    copy "monitor_config.json" "%INSTALL_PATH%\" >nul
    echo - monitor_config.json 복사 완료
) else (
    echo 경고: monitor_config.json 파일이 없습니다. 기본 설정으로 초기화됩니다.
)

:: README 파일 생성
echo README.txt 생성 중...
echo # 대기환자 모니터링 시스템 > "%INSTALL_PATH%\README.txt"
echo. >> "%INSTALL_PATH%\README.txt"
echo ## 사용 방법 >> "%INSTALL_PATH%\README.txt"
echo 1. 대기환자모니터.exe 파일을 실행합니다. >> "%INSTALL_PATH%\README.txt"
echo 2. 화면의 지시에 따라 모니터링할 영역을 설정합니다. >> "%INSTALL_PATH%\README.txt"
echo 3. 모니터링 시작 버튼을 클릭하면 시스템이 작동합니다. >> "%INSTALL_PATH%\README.txt"
echo. >> "%INSTALL_PATH%\README.txt"
echo ## 주요 기능 >> "%INSTALL_PATH%\README.txt"
echo - 화면 특정 영역의 변화 감지 >> "%INSTALL_PATH%\README.txt"
echo - 변화 감지 시 알림음 재생 및 팝업 알림 >> "%INSTALL_PATH%\README.txt"
echo - 감도 조절 가능 >> "%INSTALL_PATH%\README.txt"
echo - 모니터링 간격 설정 >> "%INSTALL_PATH%\README.txt"

:: 바로가기 생성
echo 바로가기 생성 중...

:: 바탕화면 바로가기
set /p DESKTOP_SHORTCUT="바탕화면에 바로가기를 만드시겠습니까? (Y/N, 기본값: Y): "
if /i not "%DESKTOP_SHORTCUT%"=="N" (
    echo Set oWS = WScript.CreateObject("WScript.Shell") > CreateShortcut.vbs
    echo sLinkFile = oWS.SpecialFolders("Desktop") ^& "\대기환자 모니터링.lnk" >> CreateShortcut.vbs
    echo Set oLink = oWS.CreateShortcut(sLinkFile) >> CreateShortcut.vbs
    echo oLink.TargetPath = "%INSTALL_PATH%\대기환자모니터.exe" >> CreateShortcut.vbs
    echo oLink.WorkingDirectory = "%INSTALL_PATH%" >> CreateShortcut.vbs
    echo oLink.Description = "대기환자 모니터링 시스템" >> CreateShortcut.vbs
    echo oLink.Save >> CreateShortcut.vbs
    cscript //nologo CreateShortcut.vbs
    del CreateShortcut.vbs
    echo - 바탕화면 바로가기 생성 완료
)

:: 시작 메뉴 바로가기
set /p START_MENU_SHORTCUT="시작 메뉴에 바로가기를 만드시겠습니까? (Y/N, 기본값: Y): "
if /i not "%START_MENU_SHORTCUT%"=="N" (
    if not exist "%APPDATA%\Microsoft\Windows\Start Menu\Programs\대기환자 모니터링" (
        mkdir "%APPDATA%\Microsoft\Windows\Start Menu\Programs\대기환자 모니터링"
    )
    
    echo Set oWS = WScript.CreateObject("WScript.Shell") > CreateShortcut.vbs
    echo sLinkFile = "%APPDATA%\Microsoft\Windows\Start Menu\Programs\대기환자 모니터링\대기환자 모니터링.lnk" >> CreateShortcut.vbs
    echo Set oLink = oWS.CreateShortcut(sLinkFile) >> CreateShortcut.vbs
    echo oLink.TargetPath = "%INSTALL_PATH%\대기환자모니터.exe" >> CreateShortcut.vbs
    echo oLink.WorkingDirectory = "%INSTALL_PATH%" >> CreateShortcut.vbs
    echo oLink.Description = "대기환자 모니터링 시스템" >> CreateShortcut.vbs
    echo oLink.Save >> CreateShortcut.vbs
    cscript //nologo CreateShortcut.vbs
    del CreateShortcut.vbs
    echo - 시작 메뉴 바로가기 생성 완료
)

:: 설치 완료 메시지
echo.
echo ====================================
echo 설치가 완료되었습니다!
echo ====================================
echo.
echo 설치 경로: %INSTALL_PATH%
echo.
echo 프로그램을 실행하려면:
echo - 바탕화면의 '대기환자 모니터링' 바로가기를 클릭하거나
echo - 설치 폴더에서 '대기환자모니터.exe'를 직접 실행하세요.
echo.
echo 제거하려면 설치 폴더와 바로가기를 삭제하세요.
echo.

pause