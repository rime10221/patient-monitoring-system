"""
대기환자 모니터링 시스템 배포 스크립트
- PyInstaller를 사용하여 독립 실행형 exe 파일 생성
- 필요한 리소스 파일 패키징
"""
import os
import sys
import shutil
import subprocess
import zipfile
from pathlib import Path

# 필요한 패키지 설치
def install_requirements():
    print("필요한 패키지 설치 중...")
    packages = [
        "pyinstaller",
        "opencv-python", 
        "numpy", 
        "pillow", 
        "pyautogui", 
        "pygame"
    ]
    
    for package in packages:
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", package], check=True)
            print(f"✓ {package} 설치 완료")
        except subprocess.CalledProcessError:
            print(f"✗ {package} 설치 실패")
            return False
    return True

# PyInstaller로 실행 파일 생성
def build_executable():
    print("\n실행 파일 생성 중...")
    
    # 임시 spec 파일 생성
    spec_content = """
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main_monitior.py'],
    pathex=[],
    binaries=[],
    datas=[('monitoring_voice.mp3', '.'), ('monitor_config.json', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='대기환자모니터',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app.ico',
)
"""
    
    # spec 파일 저장
    with open("monitor.spec", "w", encoding="utf-8") as f:
        f.write(spec_content)
    
    # 아이콘 파일 생성
    create_icon()
    
    # PyInstaller 실행
    try:
        subprocess.run(["pyinstaller", "--clean", "monitor.spec"], check=True)
        print("✓ 실행 파일 생성 성공")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ 실행 파일 생성 실패: {e}")
        return False

# 간단한 아이콘 생성 (PIL 사용)
def create_icon():
    try:
        from PIL import Image, ImageDraw
        
        if os.path.exists("app.ico"):
            return
            
        img = Image.new('RGBA', (256, 256), color=(255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        
        # 외부 원
        draw.ellipse((20, 20, 236, 236), fill=(44, 90, 160, 255))
        
        # 내부 원
        draw.ellipse((40, 40, 216, 216), fill=(255, 255, 255, 255))
        
        # 십자가 심볼
        draw.rectangle((108, 70, 148, 186), fill=(231, 76, 60, 255))
        draw.rectangle((70, 108, 186, 148), fill=(231, 76, 60, 255))
        
        # 아이콘 저장
        img.save('app.ico')
        print("✓ 앱 아이콘 생성 완료")
    except Exception as e:
        print(f"✗ 아이콘 생성 실패: {e}")

# 설치 프로그램 파일 생성
def create_installer():
    print("\n설치 프로그램 파일 생성 중...")
    
    # dist 폴더에서 exe 파일 찾기
    exe_path = None
    for file in os.listdir("dist"):
        if file.endswith(".exe"):
            exe_path = os.path.join("dist", file)
            break
    
    if not exe_path:
        print("✗ 생성된 exe 파일을 찾을 수 없습니다.")
        return False
    
    # 배포 파일들을 담을 폴더 생성
    dist_folder = "PatientMonitor_Setup"
    if os.path.exists(dist_folder):
        shutil.rmtree(dist_folder)
    os.makedirs(dist_folder)
    
    # exe 파일 복사
    shutil.copy(exe_path, os.path.join(dist_folder, "대기환자모니터.exe"))
    
    # README 파일 생성
    readme_content = """# 대기환자 모니터링 시스템

## 설치 방법
1. 대기환자모니터.exe 파일을 실행합니다.
2. 화면의 지시에 따라 모니터링할 영역을 설정합니다.
3. 모니터링 시작 버튼을 클릭하면 시스템이 작동합니다.

## 주요 기능
- 화면 특정 영역의 변화 감지
- 변화 감지 시 알림음 재생 및 팝업 알림
- 감도 조절 가능
- 모니터링 간격 설정

## 문의 사항
기술적인 문제나 문의사항이 있으면 연락주세요.
"""
    
    with open(os.path.join(dist_folder, "README.txt"), "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    # 설치 관련 정보 파일 생성
    install_content = """# 설치 안내

1. 대기환자모니터.exe 파일을 원하는 위치로 복사하세요.
2. 바로가기를 만들려면 exe 파일을 우클릭 후 '바로가기 만들기'를 선택하세요.
3. 프로그램 실행 후 사용 설정을 완료하세요.

* 주의: 처음 실행 시 Windows 보안 경고가 표시될 수 있습니다. 
  '추가 정보' > '실행' 버튼을 클릭하여 진행하세요.
"""
    
    with open(os.path.join(dist_folder, "설치안내.txt"), "w", encoding="utf-8") as f:
        f.write(install_content)
    
    # 전체 폴더를 zip으로 압축
    zip_path = f"{dist_folder}.zip"
    if os.path.exists(zip_path):
        os.remove(zip_path)
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(dist_folder):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, os.path.dirname(dist_folder))
                zipf.write(file_path, arcname)
    
    print(f"✓ 설치 파일 생성 완료: {zip_path}")
    print(f"✓ 설치 폴더 생성 완료: {dist_folder}")
    return True

# 정리 작업
def cleanup():
    print("\n임시 파일 정리 중...")
    temp_files = ["monitor.spec", "app.ico"]
    
    for file in temp_files:
        if os.path.exists(file):
            os.remove(file)
    
    # build 폴더 삭제 (선택적)
    if os.path.exists("build"):
        shutil.rmtree("build")
    
    print("✓ 정리 완료")

# 메인 실행 함수
def main():
    print("=" * 50)
    print("대기환자 모니터링 시스템 배포 파일 생성 도구")
    print("=" * 50)
    
    # 현재 디렉토리 확인
    current_dir = os.path.abspath(os.path.dirname(__file__))
    print(f"작업 디렉토리: {current_dir}")
    
    # 필수 파일 확인
    main_py = os.path.join(current_dir, "main_monitior.py")
    if not os.path.exists(main_py):
        print(f"✗ 오류: main_monitior.py 파일을 찾을 수 없습니다.")
        return
    
    # 음성 파일 확인
    voice_file = os.path.join(current_dir, "monitoring_voice.mp3")
    if not os.path.exists(voice_file):
        print(f"⚠ 경고: monitoring_voice.mp3 파일을 찾을 수 없습니다.")
        print("  알림음 기능이 작동하지 않을 수 있습니다.")
    
    # 설정 파일 확인
    config_file = os.path.join(current_dir, "monitor_config.json")
    if not os.path.exists(config_file):
        print(f"⚠ 경고: monitor_config.json 파일을 찾을 수 없습니다.")
        print("  기본 설정으로 초기화됩니다.")
    
    # 패키지 설치
    if not install_requirements():
        print("✗ 필요한 패키지 설치에 실패했습니다. 프로세스를 중단합니다.")
        return
    
    # 실행 파일 생성
    if not build_executable():
        print("✗ 실행 파일 생성에 실패했습니다. 프로세스를 중단합니다.")
        return
    
    # 설치 프로그램 생성
    create_installer()
    
    # 정리
    cleanup()
    
    print("\n✓ 모든 작업이 완료되었습니다!")
    print("  생성된 파일:")
    print("  - dist/대기환자모니터.exe")
    print("  - PatientMonitor_Setup/ (설치 폴더)")
    print("  - PatientMonitor_Setup.zip (배포용 압축 파일)")
    print("\n설치 방법: 압축 파일을 풀고 대기환자모니터.exe를 실행하세요.")

if __name__ == "__main__":
    main()