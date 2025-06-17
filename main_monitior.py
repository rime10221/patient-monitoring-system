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