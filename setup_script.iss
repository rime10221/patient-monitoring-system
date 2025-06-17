; 대기환자 모니터링 시스템 설치 스크립트
; Inno Setup 사용

#define MyAppName "대기환자 모니터링 시스템"
#define MyAppVersion "1.0"
#define MyAppPublisher "사용자"
#define MyAppExeName "대기환자모니터.exe"

[Setup]
; 기본 설정
AppId={{ED95B53A-2C13-4FD5-9E64-F76E85DAA2E2}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=setup
OutputBaseFilename=PatientMonitor_Setup
Compression=lzma
SolidCompression=yes
; 관리자 권한 불필요
PrivilegesRequired=lowest
; 디자인 설정
WizardStyle=modern
; 한국어 설정
SetupIconFile=app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "바탕화면에 아이콘 만들기"; GroupDescription: "아이콘:"; Flags: unchecked
Name: "quicklaunchicon"; Description: "빠른 실행에 아이콘 만들기"; GroupDescription: "아이콘:"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "monitoring_voice.mp3"; DestDir: "{app}"; Flags: ignoreversion
Source: "monitor_config.json"; DestDir: "{app}"; Flags: ignoreversion
; 아래 줄에 추가 파일 지정

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
// 사용자 PC에 Inno Setup이 설치되어 있어야 이 스크립트를 컴파일할 수 있습니다.
// 설치 과정에서 추가 작업이 필요한 경우 여기에 코드 작성