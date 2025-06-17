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
    
    # 자동 영역 탐지 기능 주석 처리 (요청사항 #1)
    """
    def auto_detect_region(self, template_text: str = "대기") -> Optional[Tuple[int, int, int, int]]:
        # 템플릿 기반 자동 영역 탐지
        try:
            # 전체 화면 캡처
            full_screen = self.capture_region()
            if full_screen is None:
                return None
            
            logger.info("OCR 자동 탐지 실패, 템플릿 매칭 시도...")
            return self.template_based_detection(full_screen)
            
        except Exception as e:
            logger.error(f"영역 자동 탐지 실패: {e}")
            return None
    
    def template_based_detection(self, image: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        # 템플릿 매칭 기반 영역 탐지
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # 텍스트 영역 탐지를 위한 전처리
            adaptive_thresh = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            
            # 윤곽선 찾기
            contours, _ = cv2.findContours(adaptive_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # 텍스트 영역으로 추정되는 윤곽선 필터링
            text_regions = []
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                if 20 <= w <= 200 and 10 <= h <= 50:
                    aspect_ratio = w / h
                    if 1 <= aspect_ratio <= 10:
                        text_regions.append((x, y, w, h))
            
            if text_regions:
                largest_region = max(text_regions, key=lambda r: r[2] * r[3])
                x, y, w, h = largest_region
                
                margin = 50
                expanded_region = (
                    max(0, x - margin),
                    max(0, y - margin),
                    min(image.shape[1] - x + margin, w + 2 * margin),
                    min(image.shape[0] - y + margin, h + 2 * margin)
                )
                
                logger.info(f"템플릿 매칭 기반 탐지된 영역: {expanded_region}")
                return expanded_region
            
            logger.warning("템플릿 매칭으로도 적절한 영역을 찾을 수 없습니다.")
            return None
            
        except Exception as e:
            logger.error(f"템플릿 매칭 실패: {e}")
            return None
    """

class ImageChangeDetector:
    """영역 변화 감지 클래스"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.previous_image = None
        self.change_threshold = 0.05  # 5% 이상 변화 시 감지
        self.min_change_pixels = 100   # 최소 변화 픽셀 수
        
    def detect_change(self, current_image: np.ndarray) -> bool:
        """이미지 변화 감지"""
        try:
            if current_image is None:
                return False
            
            # 전처리: 그레이스케일 변환 및 크기 정규화
            processed_current = self.preprocess_for_comparison(current_image)
            
            # 첫 번째 실행 시 기준 이미지 저장
            if self.previous_image is None:
                self.previous_image = processed_current.copy()
                logger.info("🔍 기준 이미지 설정 완료")
                return False
            
            # 이미지 크기가 다르면 리사이즈
            if processed_current.shape != self.previous_image.shape:
                processed_current = cv2.resize(processed_current, 
                                             (self.previous_image.shape[1], self.previous_image.shape[0]))
            
            # 변화량 계산
            change_detected = self.calculate_change(self.previous_image, processed_current)
            
            # 변화 감지된 경우 기준 이미지 업데이트
            if change_detected:
                logger.info("📸 변화 감지! 기준 이미지 업데이트")
                self.previous_image = processed_current.copy()
                
                # 디버그 모드에서 비교 이미지 저장
                if self.config.config.get('debug_mode', False):
                    cv2.imwrite('debug_change_detected.png', processed_current)
                    logger.info("디버그: 변화 감지 시점 이미지 저장됨")
            
            return change_detected
            
        except Exception as e:
            logger.error(f"변화 감지 실패: {e}")
            return False
    
    def preprocess_for_comparison(self, image: np.ndarray) -> np.ndarray:
        """비교용 이미지 전처리"""
        try:
            # 그레이스케일 변환
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            # 가우시안 블러로 노이즈 제거 (미세한 변화 무시)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # 히스토그램 평활화 (조명 변화 보정)
            equalized = cv2.equalizeHist(blurred)
            
            return equalized
            
        except Exception as e:
            logger.error(f"비교용 전처리 실패: {e}")
            return image
    
    def calculate_change(self, prev_img: np.ndarray, curr_img: np.ndarray) -> bool:
        """두 이미지 간 변화량 계산"""
        try:
            # 절대 차이 계산
            diff = cv2.absdiff(prev_img, curr_img)
            
            # 임계값 적용 (작은 변화 제거)
            threshold_value = 30  # 0-255 범위에서 30 이상 차이만 인정
            _, thresh = cv2.threshold(diff, threshold_value, 255, cv2.THRESH_BINARY)
            
            # 변화된 픽셀 수 계산
            changed_pixels = cv2.countNonZero(thresh)
            total_pixels = prev_img.shape[0] * prev_img.shape[1]
            change_ratio = changed_pixels / total_pixels
            
            # 디버그 정보
            if self.config.config.get('debug_mode', False):
                logger.info(f"변화 분석: {changed_pixels}/{total_pixels} 픽셀 ({change_ratio:.3f}%), "
                          f"임계값: {self.change_threshold:.3f}")
                
                # 변화 이미지 저장
                cv2.imwrite('debug_diff.png', diff)
                cv2.imwrite('debug_thresh.png', thresh)
            
            # 변화 조건 확인
            change_detected = (
                change_ratio >= self.change_threshold and 
                changed_pixels >= self.min_change_pixels
            )
            
            if change_detected:
                logger.info(f"✅ 변화 감지됨! 변화율: {change_ratio:.3f}% (임계값: {self.change_threshold:.3f}%)")
            
            return change_detected
            
        except Exception as e:
            logger.error(f"변화량 계산 실패: {e}")
            return False
    
    def reset_baseline(self):
        """기준 이미지 리셋"""
        self.previous_image = None
        logger.info("🔄 기준 이미지 리셋됨")
    
    def set_sensitivity(self, threshold: float, min_pixels: int = None):
        """감도 조정"""
        self.change_threshold = max(0.01, min(1.0, threshold))  # 1%~100% 범위
        if min_pixels:
            self.min_change_pixels = max(10, min_pixels)
        
        logger.info(f"🎛️ 감도 조정: 임계값={self.change_threshold:.3f}, 최소픽셀={self.min_change_pixels}")

class NotificationGUI:
    """알림 GUI 클래스 - 완전히 새로 작성"""
    
    def __init__(self, config_manager=None):
        """초기화 메서드 - config_manager는 선택적 매개변수"""
        self.alert_windows = []
        self.config = config_manager
        self.sound_player = None
        logger.info(f"NotificationGUI 초기화 완료: config={config_manager is not None}")
    
    def play_alert_sound(self):
        """알림음 재생 함수"""
        try:
            if PYGAME_AVAILABLE:
                sound_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "monitoring_voice.mp3")
                
                if os.path.exists(sound_path):
                    pygame.mixer.music.load(sound_path)
                    pygame.mixer.music.play()
                    logger.info(f"알림음 재생: {sound_path}")
                    return True
                else:
                    logger.warning(f"알림음 파일을 찾을 수 없음: {sound_path}")
            else:
                logger.warning("pygame이 설치되지 않아 알림음을 재생할 수 없습니다.")
            return False
        except Exception as e:
            logger.error(f"알림음 재생 실패: {e}")
            return False
    
    def stop_alert_sound(self):
        """알림음 중지 함수"""
        try:
            if PYGAME_AVAILABLE and pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
                logger.info("알림음 중지됨")
        except Exception as e:
            logger.error(f"알림음 중지 실패: {e}")
    
    def show_change_alert(self, change_number: int):
        """영역 변화 알림 창 표시"""
        try:
            root = tk.Tk()
            root.withdraw()  # 메인 창 숨기기
            
            alert_window = tk.Toplevel(root)
            alert_window.title("영역 변화 감지")
            alert_window.geometry("350x180")
            alert_window.configure(bg='#fff3cd')
            
            alert_window.attributes('-topmost', True)
            alert_window.attributes('-alpha', 0.95)
            
            # 화면 중앙 배치
            screen_width = alert_window.winfo_screenwidth()
            screen_height = alert_window.winfo_screenheight()
            x = (screen_width // 2) - 175
            y = (screen_height // 2) - 90
            alert_window.geometry(f"+{x}+{y}")
            
            # 메시지 프레임
            msg_frame = tk.Frame(alert_window, bg='#fff3cd')
            msg_frame.pack(expand=True, fill='both', padx=20, pady=20)
            
            # 제목
            title_label = tk.Label(
                msg_frame,
                text="🔔 영역 변화 감지",
                font=('맑은 고딕', 16, 'bold'),
                bg='#fff3cd',
                fg='#856404'
            )
            title_label.pack(pady=(0, 15))
            
            # 메시지
            message_label = tk.Label(
                msg_frame,
                text=f"모니터링 영역에 변화가 감지되었습니다!\n\n변화 횟수: {change_number}회",
                font=('맑은 고딕', 12),
                bg='#fff3cd',
                fg='#333333',
                justify='center'
            )
            message_label.pack(pady=(0, 15))
            
            # 시간
            time_label = tk.Label(
                msg_frame,
                text=datetime.now().strftime("%H:%M:%S"),
                font=('맑은 고딕', 10),
                bg='#fff3cd',
                fg='#666666'
            )
            time_label.pack(pady=(0, 15))
            
            # 알림음 재생
            self.play_alert_sound()
            
            # 알림창 닫기 함수
            def close_alert():
                self.stop_alert_sound()
                alert_window.destroy()
                root.destroy()
            
            # 확인 버튼
            ok_button = tk.Button(
                msg_frame,
                text="확인",
                command=close_alert,
                font=('맑은 고딕', 11),
                bg='#ffc107',
                fg='black',
                relief='flat',
                padx=25,
                pady=5
            )
            ok_button.pack()
            
            # 엔터키로 알림창 닫기
            alert_window.bind('<Return>', lambda event: close_alert())
            
            # 자동 닫기
            alert_duration = int(self.config.config.get('alert_duration', 5.0) * 1000)
            alert_window.after(alert_duration, close_alert)
            
            self.alert_windows.append(alert_window)
            logger.info(f"알림 창 표시: 영역 변화 #{change_number}")
            
            # 별도 이벤트 루프로 실행
            alert_window.mainloop()
            
        except Exception as e:
            logger.error(f"알림 창 표시 실패: {e}")
    
    def show_patient_alert(self, count: int):
        """대기환자 알림 (호환성 유지)"""
        self.show_change_alert(count)

class PatientQueueMonitor:
    """환자 대기열 모니터링 클래스 - 변화 감지 방식"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.screen_capture = ScreenCapture(config_manager)
        self.change_detector = ImageChangeDetector(config_manager)
        self.notification_gui = NotificationGUI(config_manager)
        
        self.is_monitoring = False
        self.monitor_thread = None
        self.change_count = 0
        
    def detect_change(self, image: np.ndarray) -> bool:
        """변화 감지"""
        change_detected = self.change_detector.detect_change(image)
        
        if change_detected:
            self.change_count += 1
            logger.info(f"📈 영역 변화 #{self.change_count} 감지됨!")
            return True
        
        return False
    
    def run_continuous_monitoring(self):
        """연속 모니터링 실행"""
        logger.info("🔍 영역 변화 모니터링 시작")
        consecutive_failures = 0
        max_failures = 5
        
        while self.is_monitoring:
            try:
                region = self.config.config.get('monitoring_region')
                if not region:
                    logger.warning("모니터링 영역이 설정되지 않았습니다.")
                    time.sleep(5)
                    continue
                
                captured_image = self.screen_capture.capture_region(region)
                
                if captured_image is not None:
                    if self.detect_change(captured_image):
                        self.notification_gui.show_change_alert(self.change_count)
                    
                    consecutive_failures = 0
                else:
                    consecutive_failures += 1
                    logger.debug(f"화면 캡처 실패 {consecutive_failures}/{max_failures}")
                    
                    if consecutive_failures >= max_failures:
                        logger.warning("연속 화면 캡처 실패. 설정을 확인해주세요.")
                        consecutive_failures = 0
                
                time.sleep(self.config.config['monitoring_interval'])
                
            except Exception as e:
                logger.error(f"모니터링 중 오류: {e}")
                time.sleep(2)
    
    def start_monitoring(self):
        """모니터링 시작"""
        if not self.is_monitoring:
            self.change_count = 0
            self.change_detector.reset_baseline()
            
            self.is_monitoring = True
            self.monitor_thread = threading.Thread(target=self.run_continuous_monitoring)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
    
    def stop_monitoring(self):
        """모니터링 중지"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=3)
    
    def set_change_sensitivity(self, threshold: float):
        """변화 감지 감도 조정"""
        self.change_detector.set_sensitivity(threshold)

class CalibrationTool:
    """초기 설정 및 보정 도구"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.screen_capture = ScreenCapture(config_manager)
        self.region_selector = ScreenRegionSelector()
        self.root = None
        self.monitor = None
        
    def run_calibration_gui(self):
        """보정 GUI 실행"""
        self.root = tk.Tk()
        self.root.title("대기환자 모니터 설정")
        self.root.geometry("500x750")
        self.root.resizable(True, True)
        
        # 스크롤 가능한 메인 프레임 생성
        main_canvas = tk.Canvas(self.root)
        scrollbar = tk.Scrollbar(self.root, orient="vertical", command=main_canvas.yview)
        scrollable_frame = tk.Frame(main_canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        )
        
        main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        main_canvas.configure(yscrollcommand=scrollbar.set)
        
        # 메인 프레임
        main_frame = tk.Frame(scrollable_frame, padx=30, pady=20)
        main_frame.pack(fill='both', expand=True)
        
        # 제목
        title_label = tk.Label(
            main_frame,
            text="🏥 대기환자 모니터링 시스템",
            font=('맑은 고딕', 18, 'bold'),
            fg='#2c5aa0'
        )
        title_label.pack(pady=(0, 20))
        
        # Tesseract 상태 확인 섹션
        status_frame = tk.LabelFrame(main_frame, text="시스템 상태", font=('맑은 고딕', 10), pady=10)
        status_frame.pack(fill='x', pady=(0, 20))
        
        self.check_system_status(status_frame)
        
        # 영역 설정 섹션
        region_frame = tk.LabelFrame(main_frame, text="모니터링 영역 설정", font=('맑은 고딕', 10), pady=10)
        region_frame.pack(fill='x', pady=(0, 20))
        
        # 설명
        desc_label = tk.Label(
            region_frame,
            text="변화를 감지할 화면 영역을 설정해주세요.",
            font=('맑은 고딕', 10),
            justify='center',
            wraplength=400
        )
        desc_label.pack(pady=(0, 15))
        
        # 버튼 프레임
        button_frame = tk.Frame(region_frame)
        button_frame.pack(pady=10)
        
        # 수동 선택 버튼 (자동 영역 탐지 버튼 제거)
        manual_button = tk.Button(
            button_frame,
            text="✋ 수동 영역 선택 (드래그)",
            command=self.manual_select_region,
            font=('맑은 고딕', 11),
            bg='#7ed321',
            fg='white',
            padx=20,
            pady=8,
            relief='flat'
        )
        manual_button.pack(pady=5, fill='x')
        
        # 현재 설정 표시
        self.status_label = tk.Label(
            region_frame,
            text="",
            font=('맑은 고딕', 9),
            fg='gray',
            wraplength=400,
            justify='center'
        )
        self.status_label.pack(pady=(15, 0))
        self.update_status_display()
        
        # 고급 설정 섹션
        advanced_frame = tk.LabelFrame(main_frame, text="고급 설정", font=('맑은 고딕', 10), pady=10)
        advanced_frame.pack(fill='x', pady=(0, 20))
        
        # 모니터링 주기 설정
        interval_frame = tk.Frame(advanced_frame)
        interval_frame.pack(fill='x', pady=5)
        
        tk.Label(interval_frame, text="모니터링 주기:", font=('맑은 고딕', 10)).pack(side='left')
        
        self.interval_var = tk.DoubleVar(value=self.config.config['monitoring_interval'])
        interval_scale = tk.Scale(
            interval_frame,
            from_=1.0, to=10.0, resolution=0.5,
            orient='horizontal',
            variable=self.interval_var,
            command=self.update_interval
        )
        interval_scale.pack(side='right', fill='x', expand=True, padx=(10, 0))
        
        # 변화 감지 감도 설정
        sensitivity_frame = tk.Frame(advanced_frame)
        sensitivity_frame.pack(fill='x', pady=5)
        
        tk.Label(sensitivity_frame, text="변화 감지 민감도:", font=('맑은 고딕', 10)).pack(side='left')
        
        self.sensitivity_var = tk.DoubleVar(value=self.config.config.get('change_sensitivity', 0.05))
        sensitivity_scale = tk.Scale(
            sensitivity_frame,
            from_=0.01, to=0.20, resolution=0.01,
            orient='horizontal',
            variable=self.sensitivity_var,
            command=self.update_sensitivity
        )
        sensitivity_scale.pack(side='right', fill='x', expand=True, padx=(10, 0))
        
        # 알림창 유지 시간 설정 (요청사항 #4)
        alert_duration_frame = tk.Frame(advanced_frame)
        alert_duration_frame.pack(fill='x', pady=5)
        
        tk.Label(alert_duration_frame, text="알림창 유지 시간(초):", font=('맑은 고딕', 10)).pack(side='left')
        
        self.alert_duration_var = tk.DoubleVar(value=self.config.config.get('alert_duration', 5.0))
        alert_duration_scale = tk.Scale(
            alert_duration_frame,
            from_=1.0, to=20.0, resolution=1.0,
            orient='horizontal',
            variable=self.alert_duration_var,
            command=self.update_alert_duration
        )
        alert_duration_scale.pack(side='right', fill='x', expand=True, padx=(10, 0))
        
        # 설명 라벨
        sens_desc = tk.Label(
            advanced_frame,
            text="💡 민감도가 낮을수록(0.01) 작은 변화도 감지, 높을수록(0.20) 큰 변화만 감지",
            font=('맑은 고딕', 8),
            fg='gray',
            wraplength=400,
            justify='left'
        )
        sens_desc.pack(anchor='w', pady=2)
        
        # 디버그 모드
        self.debug_var = tk.BooleanVar(value=self.config.config.get('debug_mode', False))
        debug_check = tk.Checkbutton(
            advanced_frame,
            text="디버그 모드 (변화 감지 상세 로깅)",
            variable=self.debug_var,
            command=self.toggle_debug_mode,
            font=('맑은 고딕', 10)
        )
        debug_check.pack(anchor='w', pady=5)
        
        # 테스트 및 실행 버튼 섹션
        control_frame = tk.LabelFrame(main_frame, text="테스트 및 실행", font=('맑은 고딕', 10), pady=10)
        control_frame.pack(fill='x', pady=(0, 20))
        
        # 테스트 버튼
        test_button = tk.Button(
            control_frame,
            text="🧪 설정 테스트",
            command=self.test_current_setup,
            font=('맑은 고딕', 11),
            bg='#f39c12',
            fg='white',
            padx=20,
            pady=8,
            relief='flat'
        )
        test_button.pack(fill='x', pady=(5, 10))
        
        # 시작 버튼
        start_button = tk.Button(
            control_frame,
            text="🚀 모니터링 시작",
            command=self.start_monitoring,
            font=('맑은 고딕', 12, 'bold'),
            bg='#e74c3c',
            fg='white',
            padx=30,
            pady=10,
            relief='flat'
        )
        start_button.pack(fill='x', pady=(0, 5))
        
        # 종료 시 정리
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 스크롤바 배치
        main_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 마우스 휠 스크롤 바인딩
        def _on_mousewheel(event):
            main_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        main_canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        self.root.mainloop()
    
    def check_system_status(self, parent_frame):
        """시스템 상태 확인 및 표시"""
        # Tesseract 상태
        tesseract_status, tesseract_msg = TesseractSetup.check_tesseract_installation()
        
        tesseract_frame = tk.Frame(parent_frame)
        tesseract_frame.pack(fill='x', pady=2)
        
        tesseract_icon = "✅" if tesseract_status else "❌"
        tesseract_label = tk.Label(
            tesseract_frame,
            text=f"{tesseract_icon} Tesseract OCR: {tesseract_msg}",
            font=('맑은 고딕', 9),
            anchor='w'
        )
        tesseract_label.pack(side='left', fill='x', expand=True)
        
        # PyAutoGUI 상태
        pyautogui_frame = tk.Frame(parent_frame)
        pyautogui_frame.pack(fill='x', pady=2)
        
        pyautogui_icon = "✅" if PYAUTOGUI_AVAILABLE else "❌"
        pyautogui_msg = "설치됨" if PYAUTOGUI_AVAILABLE else "설치 필요"
        pyautogui_label = tk.Label(
            pyautogui_frame,
            text=f"{pyautogui_icon} PyAutoGUI: {pyautogui_msg}",
            font=('맑은 고딕', 9),
            anchor='w'
        )
        pyautogui_label.pack(side='left', fill='x', expand=True)
        
        # Pygame 상태 (알림음 재생용)
        pygame_frame = tk.Frame(parent_frame)
        pygame_frame.pack(fill='x', pady=2)
        
        pygame_icon = "✅" if PYGAME_AVAILABLE else "❌"
        pygame_msg = "설치됨" if PYGAME_AVAILABLE else "설치 필요 (알림음 재생)"
        pygame_label = tk.Label(
            pygame_frame,
            text=f"{pygame_icon} Pygame: {pygame_msg}",
            font=('맑은 고딕', 9),
            anchor='w'
        )
        pygame_label.pack(side='left', fill='x', expand=True)
        
        # 알림음 파일 확인
        sound_frame = tk.Frame(parent_frame)
        sound_frame.pack(fill='x', pady=2)
        
        sound_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "monitoring_voice.mp3")
        sound_exists = os.path.exists(sound_path)
        sound_icon = "✅" if sound_exists else "❌"
        sound_msg = "있음" if sound_exists else "없음 (알림음 재생 불가)"
        sound_label = tk.Label(
            sound_frame,
            text=f"{sound_icon} 알림음 파일: {sound_msg}",
            font=('맑은 고딕', 9),
            anchor='w'
        )
        sound_label.pack(side='left', fill='x', expand=True)
    
    def update_status_display(self):
        """현재 설정 상태 표시 업데이트"""
        current_region = self.config.config.get('monitoring_region')
        if current_region:
            x, y, w, h = current_region
            status_text = f"✅ 설정된 영역: 위치({x}, {y}) 크기({w}×{h})"
            self.status_label.config(text=status_text, fg='green')
        else:
            self.status_label.config(text="⚠️ 모니터링 영역이 설정되지 않았습니다", fg='red')
    
    def update_sensitivity(self, value):
        """변화 감지 민감도 업데이트"""
        sensitivity = float(value)
        self.config.config['change_sensitivity'] = sensitivity
        self.config.save_config()
        logger.info(f"변화 감지 민감도 설정: {sensitivity:.2f}")
    
    def update_interval(self, value):
        """모니터링 주기 업데이트"""
        self.config.config['monitoring_interval'] = float(value)
        self.config.save_config()
    
    def update_alert_duration(self, value):
        """알림창 유지 시간 업데이트"""
        self.config.config['alert_duration'] = float(value)
        self.config.save_config()
        logger.info(f"알림창 유지 시간 설정: {float(value):.1f}초")
    
    def toggle_debug_mode(self):
        """디버그 모드 토글"""
        self.config.config['debug_mode'] = self.debug_var.get()
        self.config.save_config()
    
    # 자동 영역 탐지 메서드 주석 처리 (요청사항 #1)
    """
    def auto_detect_region(self):
        # 자동 영역 탐지
        try:
            progress_window = tk.Toplevel(self.root)
            progress_window.title("자동 탐지 중...")
            progress_window.geometry("300x100")
            progress_window.transient(self.root)
            progress_window.grab_set()
            
            progress_label = tk.Label(progress_window, text="화면에서 텍스트 영역을 찾고 있습니다...", 
                                    font=('맑은 고딕', 10))
            progress_label.pack(expand=True)
            
            progress_window.update()
            
            region = self.screen_capture.auto_detect_region()
            
            progress_window.destroy()
            
            if region:
                self.config.config['monitoring_region'] = region
                self.config.save_config()
                self.update_status_display()
                
                x, y, w, h = region
                messagebox.showinfo("성공", 
                    f"영역이 자동으로 설정되었습니다!\n\n"
                    f"위치: ({x}, {y})\n"
                    f"크기: {w} × {h}\n\n"
                    f"이제 '설정 테스트'를 클릭하여 확인해보세요.")
            else:
                messagebox.showwarning("실패", 
                    "자동 탐지에 실패했습니다.\n\n"
                    "수동 영역 선택을 사용해주세요.")
                
        except Exception as e:
            messagebox.showerror("오류", f"자동 탐지 중 오류가 발생했습니다:\n{str(e)}")
    """
    
    def manual_select_region(self):
        """수동 영역 선택"""
        try:
            messagebox.showinfo("안내", 
                "화면이 반투명해지면 마우스로 드래그하여\n"
                "모니터링할 영역을 선택하세요.\n\n"
                "- 드래그로 영역 선택\n"
                "- ESC키로 취소\n"
                "- 선택 완료 후 자동으로 설정됩니다")
            
            self.root.iconify()
            self.root.after(500, self._perform_region_selection)
            
        except Exception as e:
            messagebox.showerror("오류", f"수동 선택 중 오류가 발생했습니다:\n{str(e)}")
    
    def _perform_region_selection(self):
        """실제 영역 선택 수행"""
        try:
            region = self.region_selector.select_region()
            
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
            
            if region:
                self.config.config['monitoring_region'] = region
                self.config.save_config()
                self.update_status_display()
                
                x, y, w, h = region
                messagebox.showinfo("✅ 영역 설정 성공", 
                    f"영역이 수동으로 설정되었습니다!\n\n"
                    f"📍 위치: ({x}, {y})\n"
                    f"📏 크기: {w} × {h}\n\n"
                    f"💡 이제 '설정 테스트'를 클릭하여 확인해보세요.")
            else:
                messagebox.showinfo("❌ 선택 취소", "영역 선택이 취소되었습니다.")
                
        except Exception as e:
            self.root.deiconify()
            self.root.focus_force()
            messagebox.showerror("❌ 오류", f"영역 선택 중 오류가 발생했습니다:\n{str(e)}")
    
    def test_current_setup(self):
        """현재 설정 테스트 - 변화 감지 방식"""
        try:
            region = self.config.config.get('monitoring_region')
            if not region:
                messagebox.showwarning("경고", "먼저 모니터링 영역을 설정해주세요.")
                return
            
            test_window = tk.Toplevel(self.root)
            test_window.title("변화 감지 테스트 중...")
            test_window.geometry("400x350")
            test_window.transient(self.root)
            
            text_widget = tk.Text(test_window, wrap='word', font=('맑은 고딕', 10))
            text_widget.pack(fill='both', expand=True, padx=10, pady=10)
            
            def log_to_widget(message):
                text_widget.insert('end', message + '\n')
                text_widget.see('end')
                test_window.update()
            
            log_to_widget("🧪 변화 감지 테스트 시작...\n")
            
            log_to_widget("1. 화면 캡처 테스트...")
            captured_image = self.screen_capture.capture_region(region)
            
            if captured_image is not None:
                log_to_widget("   ✅ 화면 캡처 성공")
                
                log_to_widget("2. 변화 감지 시스템 초기화...")
                change_detector = ImageChangeDetector(self.config)
                
                change_detector.detect_change(captured_image)
                log_to_widget("   ✅ 기준 이미지 설정 완료")
                
                sensitivity = self.config.config.get('change_sensitivity', 0.05)
                change_detector.set_sensitivity(sensitivity)
                log_to_widget(f"   ✅ 변화 감지 민감도: {sensitivity:.2f}")
                
                log_to_widget("3. 변화 감지 테스트...")
                log_to_widget("   💡 이제 모니터링 영역을 변경해보세요!")
                log_to_widget("   (예: 마우스 클릭, 텍스트 변경 등)")
                
                for i in range(10):
                    time.sleep(1)
                    test_image = self.screen_capture.capture_region(region)
                    if test_image is not None:
                        if change_detector.detect_change(test_image):
                            log_to_widget(f"   🎉 변화 감지됨! ({i+1}초 시점)")
                            
                            notification_gui = NotificationGUI(self.config)
                            notification_gui.show_change_alert(1)
                            
                            log_to_widget("   ✅ 알림 표시 성공")
                            log_to_widget("\n🎉 모든 테스트 통과!")
                            log_to_widget("변화 감지 시스템이 올바르게 작동합니다.")
                            break
                    
                    log_to_widget(f"   ⏰ 변화 감지 대기 중... ({i+1}/10초)")
                else:
                    log_to_widget("   ⚠️ 10초 동안 변화가 감지되지 않음")
                    log_to_widget("   💡 민감도를 낮추거나 영역을 다시 확인하세요")
                    
            else:
                log_to_widget("   ❌ 화면 캡처 실패")
                log_to_widget("   → 영역 설정을 다시 확인하세요")
            
            close_button = tk.Button(test_window, text="닫기", command=test_window.destroy)
            close_button.pack(pady=10)
            
        except Exception as e:
            messagebox.showerror("오류", f"테스트 중 오류가 발생했습니다:\n{str(e)}")
    
    def start_monitoring(self):
        """모니터링 시작"""
        try:
            region = self.config.config.get('monitoring_region')
            if not region:
                messagebox.showwarning("경고", "먼저 모니터링 영역을 설정해주세요.")
                return
            
            if self.monitor:
                self.monitor.stop_monitoring()
            
            self.monitor = PatientQueueMonitor(self.config)
            
            sensitivity = self.config.config.get('change_sensitivity', 0.05)
            self.monitor.set_change_sensitivity(sensitivity)
            
            self.monitor.start_monitoring()
            
            self.root.iconify()
            
            messagebox.showinfo("시작", 
                "✅ 영역 변화 모니터링이 시작되었습니다!\n\n"
                "- 모니터링 영역에 변화가 생기면 알림이 표시됩니다\n"
                "- 민감도는 설정에서 조절할 수 있습니다\n"
                "- 중지하려면 작업 표시줄에서 프로그램을 종료하세요")
            
        except Exception as e:
            messagebox.showerror("오류", f"모니터링 시작 중 오류가 발생했습니다:\n{str(e)}")
    
    def on_closing(self):
        """프로그램 종료 시 정리"""
        try:
            if self.monitor:
                self.monitor.stop_monitoring()
            self.root.destroy()
        except:
            pass

def main():
    """메인 실행 함수"""
    try:
        # 의존성 체크
        missing_deps = []
        if not TESSERACT_AVAILABLE:
            missing_deps.append("pytesseract")
        if not PYAUTOGUI_AVAILABLE:
            missing_deps.append("pyautogui")
        if not PYGAME_AVAILABLE:
            missing_deps.append("pygame")
        
        if missing_deps:
            print(f"경고: 다음 라이브러리가 설치되지 않았습니다: {', '.join(missing_deps)}")
            print("pip install opencv-python pillow pytesseract pyautogui pygame 명령으로 설치하세요.")
        
        # 설정 관리자 초기화
        config_manager = ConfigManager()
        
        # 보정 도구 실행
        calibration_tool = CalibrationTool(config_manager)
        calibration_tool.run_calibration_gui()
        
    except Exception as e:
        logger.error(f"프로그램 실행 중 오류: {e}")
        try:
            messagebox.showerror("오류", f"프로그램 실행 중 오류가 발생했습니다:\n{e}")
        except:
            print(f"오류: {e}")

if __name__ == "__main__":
    main()
