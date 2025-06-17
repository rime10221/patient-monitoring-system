@echo off
:: 대기환자 모니터링 시스템 제거 스크립트

echo ===================================
echo 대기환자 모니터링 시스템 제거 프로그램
echo ===================================
echo.

:: 설치 경로 확인
set DEFAULT_PATH=%USERPROFILE%\대기환자모니터
set UNINSTALL_PATH=

if exist "C:\Program Files\대기환자모니터\대기환자모니터.exe" (
    set UNINSTALL_PATH=C:\Program Files\대기환자모니터
) else if exist "%DEFAULT_PATH%\대기환자모니터.exe" (
    set UNINSTALL_PATH=%DEFAULT_PATH%
) else (
    echo 설치된 프로그램을 찾을 수 없습니다.
    echo 다음 경로에서 프로그램이 발견되지 않았습니다:
    echo - C:\Program Files\대기환자모니터
    echo - %DEFAULT_PATH%
    echo.
    echo 직접 제거할 경로를 입력하세요:
    set /p UNINSTALL_PATH="경로 (취소하려면 빈 값): "
    
    if "%UNINSTALL_PATH%"=="" (
        echo 제거가 취소되었습니다.
        goto :eof
    )
)

echo.
echo 제거할 프로그램 경로: %UNINSTALL_PATH%
echo.

:: 제거 확인
set /p CONFIRM="이 경로에서 프로그램을 제거하시겠습니까? (Y/N, 기본값: Y): "
if /i "%CONFIRM%"=="N" (
    echo 제거가 취소되었습니다.
    goto :eof
)

:: 프로세스 종료
echo.
echo 실행 중인 프로그램 종료 중...
taskkill /f /im 대기환자모니터.exe >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo - 프로그램 종료 완료
) else (
    echo - 실행 중인 프로그램이 없음
)

:: 바로가기 삭제
echo 바로가기 삭제 중...
if exist "%USERPROFILE%\Desktop\대기환자 모니터링.lnk" (
    del "%USERPROFILE%\Desktop\대기환자 모니터링.lnk"
    echo - 바탕화면 바로가기 삭제 완료
)

if exist "%APPDATA%\Microsoft\Windows\Start Menu\Programs\대기환자 모니터링" (
    rmdir /s /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\대기환자 모니터링"
    echo - 시작 메뉴 바로가기 삭제 완료
)

:: 프로그램 파일 삭제
echo 프로그램 파일 삭제 중...
if exist "%UNINSTALL_PATH%" (
    rmdir /s /q "%UNINSTALL_PATH%"
    echo - 프로그램 폴더 삭제 완료
) else (
    echo - 프로그램 폴더가 이미 삭제되었습니다.
)

:: 제거 완료 메시지
echo.
echo ====================================
echo 제거가 완료되었습니다!
echo ====================================
echo.
echo 다음 항목이 제거되었습니다:
echo - 프로그램 파일
echo - 바탕화면 바로가기
echo - 시작 메뉴 바로가기
echo.

pause