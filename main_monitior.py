# main_monitor.py - 개선된 대기환자 모니터링 시스템 (변화 감지 방식)
import time
import threading
import logging
from typing import Optional, Tuple, List
import cv2
import numpy as np
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import messagebox, ttk, filedialog
import re
import json
import os
import sys
from datetime import datetime
import subprocess
import urllib.request
import zipfile

# OCR 라이브러리 동적 import
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    print("⚠️ pytesseract가 설치되지 않았습니다.")
    print("설치: pip install pytesseract")

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    print("⚠️ pyautogui가 설치되지 않았습니다.")
    print("설치: pip install pyautogui")

# 오디오 플레이어 import
try:
    import pygame
    PYGAME_AVAILABLE = True
    # Pygame 초기화
    pygame.init()
except ImportError:
    PYGAME_AVAILABLE = False
    print("⚠️ pygame이 설치되지 않았습니다.")
    print("설치: pip install pygame")

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('patient_monitor.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TesseractSetup:
    """Tesseract OCR 자동 설정 클래스"""
    
    @staticmethod
    def check_tesseract_installation():
        """Tesseract 설치 확인 및 자동 설정"""
        try:
            if not TESSERACT_AVAILABLE:
                return False, "pytesseract 라이브러리가 설치되지 않았습니다."
            
            # Tesseract 실행 파일 경로 확인
            tesseract_cmd = pytesseract.pytesseract.tesseract_cmd
            
            # Windows에서 기본 설치 경로 확인
            if sys.platform.startswith('win'):
                possible_paths = [
                    r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                    r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
                    r'C:\Users\{}\AppData\Local\Tesseract-OCR\tesseract.exe'.format(os.getenv('USERNAME')),
                ]
                
                for path in possible_paths:
                    if os.path.exists(path):
                        pytesseract.pytesseract.tesseract_cmd = path
                        tesseract_cmd = path
                        break
            
            # Tesseract 버전 확인
            result = subprocess.run([tesseract_cmd, '--version'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                # 한국어 언어팩 확인
                lang_result = subprocess.run([tesseract_cmd, '--list-langs'], 
                                           capture_output=True, text=True, timeout=10)
                
                has_korean = 'kor' in lang_result.stdout
                
                if not has_korean:
                    # 한국어 언어팩 자동 설치 시도
                    install_msg = TesseractSetup.try_install_korean_pack(tesseract_cmd)
                    return True, f"Tesseract 설치됨. 한국어팩: {install_msg}"
                else:
                    return True, f"Tesseract 설치됨. 한국어팩: 있음"
            else:
                return False, "Tesseract 실행 파일을 찾을 수 없습니다."
                
        except subprocess.TimeoutExpired:
            return False, "Tesseract 응답 시간 초과"
        except FileNotFoundError:
            return False, "Tesseract가 설치되지 않았습니다."
        except Exception as e:
            return False, f"Tesseract 확인 중 오류: {e}"
    
    @staticmethod
    def try_install_korean_pack(tesseract_cmd):
        """한국어 언어팩 자동 설치 시도"""
        try:
            # Tesseract 설치 경로 찾기
            tesseract_dir = os.path.dirname(tesseract_cmd)
            tessdata_dir = os.path.join(tesseract_dir, 'tessdata')
            
            if not os.path.exists(tessdata_dir):
                return "tessdata 폴더를 찾을 수 없음"
            
            kor_file = os.path.join(tessdata_dir, 'kor.traineddata')
            
            if os.path.exists(kor_file):
                return "이미 설치됨"
            
            # 한국어 언어팩 다운로드 URL
            kor_url = "https://github.com/tesseract-ocr/tessdata/raw/main/kor.traineddata"
            
            logger.info("한국어 언어팩 다운로드 시도...")
            
            import urllib.request
            urllib.request.urlretrieve(kor_url, kor_file)
            
            # 설치 확인
            if os.path.exists(kor_file):
                logger.info("✅ 한국어 언어팩 설치 완료")
                return "자동 설치 완료"
            else:
                return "자동 설치 실패"
                
        except Exception as e:
            logger.error(f"한국어 언어팩 설치 실패: {e}")
            return f"설치 실패: {str(e)}"

class ScreenRegionSelector:
    """화면 영역 선택 도구 - 마우스 드래그로 영역 선택"""
    
    def __init__(self):
        self.start_x = None
        self.start_y = None
        self.end_x = None
        self.end_y = None
        self.selecting = False
        self.selection_window = None
        self.canvas = None
        self.rect_id = None
        
    def select_region(self) -> Optional[Tuple[int, int, int, int]]:
        """마우스 드래그로 화면 영역 선택"""
        try:
            if not PYAUTOGUI_AVAILABLE:
                messagebox.showerror("오류", "pyautogui가 설치되지 않았습니다.")
                return None
            
            # 전체 화면 캡처
            screenshot = pyautogui.screenshot()
            screen_width, screen_height = screenshot.size
            
            # 선택 창 생성
            self.selection_window = tk.Toplevel()
            self.selection_window.title("영역 선택 - 드래그하여 선택하세요")
            self.selection_window.attributes('-fullscreen', True)
            self.selection_window.attributes('-alpha', 0.3)
            self.selection_window.attributes('-topmost', True)
            
            # 캔버스 생성
            self.canvas = tk.Canvas(
                self.selection_window,
                width=screen_width,
                height=screen_height,
                highlightthickness=0,
                cursor='crosshair'
            )
            self.canvas.pack(fill='both', expand=True)
            
            # 배경 이미지 설정 (선택적)
            try:
                # PIL Image를 Tkinter에서 사용 가능한 형태로 변환
                screenshot_resized = screenshot.resize((screen_width//2, screen_height//2))
                self.bg_image = ImageTk.PhotoImage(screenshot_resized)
                self.canvas.create_image(screen_width//2, screen_height//2, image=self.bg_image)
            except:
                pass  # 배경 이미지 실패 시 무시
            
            # 이벤트 바인딩
            self.canvas.bind('<Button-1>', self.on_click)
            self.canvas.bind('<B1-Motion>', self.on_drag)
            self.canvas.bind('<ButtonRelease-1>', self.on_release)
            
            # ESC 키로 취소
            self.selection_window.bind('<Escape>', lambda e: self.cancel_selection())
            self.selection_window.focus_set()
            
            # 안내 텍스트
            instruction_text = "마우스를 드래그하여 모니터링할 영역을 선택하세요\nESC: 취소, 드래그 완료 후 자동으로 선택됩니다"
            self.canvas.create_text(
                screen_width//2, 50,
                text=instruction_text,
                fill='red',
                font=('맑은 고딕', 16, 'bold'),
                justify='center'
            )
            
            # 모달 대기
            self.selection_window.wait_window()
            
            # 선택된 영역 반환
            if all(coord is not None for coord in [self.start_x, self.start_y, self.end_x, self.end_y]):
                x = min(self.start_x, self.end_x)
                y = min(self.start_y, self.end_y)
                width = abs(self.end_x - self.start_x)
                height = abs(self.end_y - self.start_y)
                
                if width > 10 and height > 10:  # 최소 크기 확인
                    return (x, y, width, height)
            
            return None
            
        except Exception as e:
            logger.error(f"영역 선택 중 오류: {e}")
            if self.selection_window:
                self.selection_window.destroy()
            return None
    
    def on_click(self, event):
        """마우스 클릭 시작"""
        self.start_x = event.x
        self.start_y = event.y
        self.selecting = True
        
        # 기존 사각형 제거
        if self.rect_id:
            self.canvas.delete(self.rect_id)
    
    def on_drag(self, event):
        """마우스 드래그 중"""
        if self.selecting:
            # 기존 사각형 제거
            if self.rect_id:
                self.canvas.delete(self.rect_id)
            
            # 새 사각형 그리기
            self.rect_id = self.canvas.create_rectangle(
                self.start_x, self.start_y, event.x, event.y,
                outline='red', width=3, fill='yellow', stipple='gray25'
            )
    
    def on_release(self, event):
        """마우스 드래그 완료"""
        if self.selecting:
            self.end_x = event.x
            self.end_y = event.y
            self.selecting = False
            
            # 선택 완료 메시지
            width = abs(self.end_x - self.start_x)
            height = abs(self.end_y - self.start_y)
            
            if width > 10 and height > 10:
                self.canvas.create_text(
                    (self.start_x + self.end_x) // 2,
                    (self.start_y + self.end_y) // 2,
                    text=f"선택 완료!\n{width}x{height}",
                    fill='blue',
                    font=('맑은 고딕', 14, 'bold'),
                    justify='center'
                )
                
                # 1초 후 창 닫기
                self.selection_window.after(1000, self.selection_window.destroy)
            else:
                self.cancel_selection()
    
    def cancel_selection(self):
        """선택 취소"""
        self.start_x = self.start_y = self.end_x = self.end_y = None
        if self.selection_window:
            self.selection_window.destroy()

class ConfigManager:
    """설정 관리 클래스"""
    
    def __init__(self, config_file='monitor_config.json'):
        self.config_file = config_file
        self.default_config = {
            'monitoring_region': None,
            'monitoring_interval': 2.0,
            'change_sensitivity': 0.05,
            'alert_duration': 5.0,
            'debug_mode': False
        }
        self.config = self.load_config()
    
    def load_config(self) -> dict:
        """설정 파일 로드"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    for key, value in self.default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
            else:
                return self.default_config.copy()
        except Exception as e:
            logger.error(f"설정 로드 실패: {e}")
            return self.default_config.copy()
    
    def save_config(self):
        """설정 파일 저장"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            logger.info("설정 저장 완료")
        except Exception as e:
            logger.error(f"설정 저장 실패: {e}")

class ScreenCapture:
    """화면 캡처 클래스"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        
    def capture_region(self, region: Optional[Tuple[int, int, int, int]] = None) -> Optional[np.ndarray]:
        """지정 영역 화면 캡처"""
        try:
            if not PYAUTOGUI_AVAILABLE:
                logger.error("pyautogui가 설치되지 않았습니다.")
                return None
            
            if region:
                x, y, w, h = region
                screenshot = pyautogui.screenshot(region=(x, y, w, h))
            else:
                screenshot = pyautogui.screenshot()
            
            # PIL Image를 OpenCV 형식으로 변환
            img_array = np.array(screenshot)
            img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            
            return img_bgr
            
        except Exception as e:
            logger.error(f"화면 캡처 실패: {e}")
            return None