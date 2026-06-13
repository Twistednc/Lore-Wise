import win32gui
import win32process
import psutil
import time
import json
from PyQt5.QtCore import Qt, QTimer, QRect, QPropertyAnimation, QEasingCurve, QUrl
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QApplication, QShortcut
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtGui import QKeySequence, QColor, QCursor
from core.game_detector import GameDetector

PANEL_WIDTH = 400

class Overlay(QWidget):
    def __init__(self):
        super().__init__()
        self._game = None
        self._visible = False
        self._animating = False
        self._last_show_time = 0
        self._last_loaded_wiki = None 
        self._detector = GameDetector()
        
        # Default Theme (Will be overridden by config)
        self._accent_color = "#3498db"
        self._load_config()

        # 1. WINDOW ATTRIBUTES
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setObjectName("panel")
        self.update_styles()
        
        self._setup_ui()

        # 2. ANIMATION
        self._anim = QPropertyAnimation(self, b"geometry")
        self._anim.setDuration(300)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.finished.connect(self._on_anim_finished)

        # 3. SYNC TIMER (Auto-Hide and Position Locking)
        self._sync_timer = QTimer()
        self._sync_timer.timeout.connect(self._sync_logic)
        self._sync_timer.start(200)

    def _load_config(self):
        try:
            if os.path.exists("config.json"):
                with open("config.json", "r") as f:
                    data = json.load(f)
                    self.setWindowOpacity(data.get("opacity", 0.95))
                    if data.get("theme_mode") == "Custom Color":
                        self._accent_color = data.get("accent_color", "#3498db")
        except: pass

    def update_styles(self):
        self.setStyleSheet(f"""
            QWidget#panel {{ 
                background: #0f0f12; 
                border-left: 2px solid {self._accent_color}; 
            }}
        """)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)

        # --- COMPACT HEADER ---
        self.header = QWidget()
        self.header.setFixedHeight(32)
        self.header.setStyleSheet("background: #16161a; border-bottom: 1px solid #333;")
        h_layout = QHBoxLayout(self.header)
        h_layout.setContentsMargins(10, 0, 10, 0)
        h_layout.setSpacing(6)
        
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search wiki...")
        self._search.setFixedHeight(22)
        self._search.setStyleSheet(f"""
            QLineEdit {{
                background: #232326; color: white; border: 1px solid #3d3d42;
                padding: 0px 8px; border-radius: 4px; font-weight: bold; font-size: 12px;
            }}
            QLineEdit:focus {{ border: 1px solid {self._accent_color}; }}
        """)
        self._search.returnPressed.connect(self._on_search)

        btn_css = f"""
            QPushButton {{ 
                background: transparent; color: #777; font-size: 14px; 
                border: none; width: 20px; height: 32px; 
            }} 
            QPushButton:hover {{ color: {self._accent_color}; }}
        """
        
        self.btn_back = QPushButton("←")
        self.btn_back.setStyleSheet(btn_css)
        self.btn_back.clicked.connect(lambda: self._browser.back())
        self.btn_fwd = QPushButton("→")
        self.btn_fwd.setStyleSheet(btn_css)
        self.btn_fwd.clicked.connect(lambda: self._browser.forward())
        self.btn_ref = QPushButton("↻")
        self.btn_ref.setStyleSheet(btn_css)
        self.btn_ref.clicked.connect(lambda: self._browser.reload())

        h_layout.addWidget(self._search)
        h_layout.addWidget(self.btn_back)
        h_layout.addWidget(self.btn_fwd)
        h_layout.addWidget(self.btn_ref)
        layout.addWidget(self.header)

        # --- BROWSER ---
        self._browser = QWebEngineView()
        self._browser.page().setBackgroundColor(QColor("#0f0f12"))
        ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 14_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1"
        self._browser.page().profile().setHttpUserAgent(ua)
        self._browser.setStyleSheet("background: #0f0f12;")
        layout.addWidget(self._browser)

        QShortcut(QKeySequence("Escape"), self).activated.connect(self.hide_panel)

    def _sync_logic(self):
        if self._animating or not self._visible: return
        if time.time() - self._last_show_time < 2.0: return
        
        # HOVER PROTECTION: Don't hide if mouse is over overlay
        if self.geometry().contains(QCursor.pos()): return

        # FOCUS CHECK: Hide if neither overlay nor game has focus
        fg_hwnd = win32gui.GetForegroundWindow()
        if fg_hwnd != int(self.winId()):
            active_game = self._detector.get_active_game()
            if not active_game or (self._game and active_game.process != self._game.process):
                self.hide_panel()

    def toggle(self, game_info):
        if self._animating: return
        if self._visible: self.hide_panel()
        elif game_info: self.show_panel(game_info)

    def show_panel(self, game):
        self._game = game
        if game.wiki_base and self._last_loaded_wiki != game.wiki_base:
            self._browser.load(QUrl(f"https://{game.wiki_base}"))
            self._last_loaded_wiki = game.wiki_base

        rect = self._detector.get_window_rect(game.process)
        screen = QApplication.primaryScreen().geometry()

        if rect:
            x, y, w, h = rect
            end_r = QRect(x + w - PANEL_WIDTH, y, PANEL_WIDTH, h)
            start_r = QRect(x + w, y, PANEL_WIDTH, h)
        else:
            end_r = QRect(screen.width() - PANEL_WIDTH, 0, PANEL_WIDTH, screen.height())
            start_r = QRect(screen.width(), 0, PANEL_WIDTH, screen.height())

        self.setGeometry(start_r)
        self.show()
        self._animating = True
        self._visible = True
        self._last_show_time = time.time()
        
        self._anim.stop()
        self._anim.setStartValue(start_r)
        self._anim.setEndValue(end_r)
        self._anim.start()
        
        self.raise_()
        self.activateWindow()
        self._search.setFocus()
        self._search.selectAll()

    def hide_panel(self):
        if not self._visible or self._animating: return
        self._animating = True
        curr = self.geometry()
        screen_right = QApplication.primaryScreen().geometry().right()
        target_r = QRect(screen_right + 10, curr.y(), PANEL_WIDTH, curr.height())
        
        self._anim.stop()
        self._anim.setStartValue(curr)
        self._anim.setEndValue(target_r)
        self._anim.start()

    def _on_anim_finished(self):
        self._animating = False
        if self.geometry().x() >= (QApplication.primaryScreen().geometry().right() - 50):
            self.hide()
            self._visible = False

    def _on_search(self):
        q = self._search.text().strip()
        if not q or not self._game: return
        url = f"https://{self._game.wiki_base}/wiki/Special:Search?query={q}"
        self._browser.load(QUrl(url))
        self._browser.setFocus()