import json
import os
import sys
import winreg
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QSlider, QComboBox, 
                             QColorDialog, QCheckBox, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

_CONFIG_FILE = "config.json"

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("LoreWise Settings")
        self.setFixedWidth(350)
        # Ensure settings are always on top of the game/overlay
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self._setup_ui()
        self._load_current_settings()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # 1. Hotkey
        layout.addWidget(QLabel("Global Hotkey (e.g., ctrl+g):"))
        self._hotkey_input = QLineEdit()
        layout.addWidget(self._hotkey_input)

        # 2. Opacity
        layout.addWidget(QLabel("Overlay Opacity:"))
        self._opacity_slider = QSlider(Qt.Horizontal)
        self._opacity_slider.setRange(40, 100)
        layout.addWidget(self._opacity_slider)

        # 3. Theme Mode
        layout.addWidget(QLabel("Theme Mode:"))
        self._theme_mode = QComboBox()
        self._theme_mode.addItems(["Default (LoreBlue)", "Custom Color"])
        self._theme_mode.currentIndexChanged.connect(self._toggle_color_btn)
        layout.addWidget(self._theme_mode)

        # 4. Color Picker
        self._color_btn = QPushButton("Pick Custom Color")
        self._color_btn.clicked.connect(self._pick_color)
        self._selected_color = "#3498db"
        layout.addWidget(self._color_btn)

        # 5. Startup Checkbox
        self._startup_check = QCheckBox("Launch LoreWise on System Startup")
        layout.addWidget(self._startup_check)

        layout.addSpacing(10)

        # 6. Action Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save && Restart")
        save_btn.setStyleSheet("font-weight: bold; padding: 5px;")
        save_btn.clicked.connect(self._save_settings)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _toggle_color_btn(self):
        self._color_btn.setEnabled(self._theme_mode.currentIndex() == 1)

    def _pick_color(self):
        color = QColorDialog.getColor(QColor(self._selected_color), self)
        if color.isValid():
            self._selected_color = color.name()
            self._color_btn.setStyleSheet(f"background: {self._selected_color}; color: white;")

    def _load_current_settings(self):
        # Load Config JSON
        try:
            if os.path.exists(_CONFIG_FILE):
                with open(_CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    self._hotkey_input.setText(data.get("hotkey", "ctrl+g"))
                    self._opacity_slider.setValue(int(data.get("opacity", 0.95) * 100))
                    self._theme_mode.setCurrentText(data.get("theme_mode", "Default"))
                    self._selected_color = data.get("accent_color", "#3498db")
                    self._color_btn.setStyleSheet(f"background: {self._selected_color}; color: white;")
        except: pass
        self._toggle_color_btn()

        # Check Windows Registry for Startup status
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
            winreg.QueryValueEx(key, "LoreWise")
            self._startup_check.setChecked(True)
            winreg.CloseKey(key)
        except:
            self._startup_check.setChecked(False)

    def _save_settings(self):
        # 1. Save to JSON
        new_config = {
            "hotkey": self._hotkey_input.text().lower().replace(" ", ""),
            "opacity": self._opacity_slider.value() / 100.0,
            "theme_mode": self._theme_mode.currentText(),
            "accent_color": self._selected_color
        }
        with open(_CONFIG_FILE, "w") as f:
            json.dump(new_config, f, indent=2)

        # 2. Handle Startup Registry
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
            if self._startup_check.isChecked():
                # Detect if we are running as a script or a packaged EXE
                if getattr(sys, 'frozen', False):
                    path = sys.executable
                else:
                    path = os.path.realpath(sys.argv[0])
                winreg.SetValueEx(key, "LoreWise", 0, winreg.REG_SZ, f'"{path}"')
            else:
                try: winreg.DeleteValue(key, "LoreWise")
                except: pass
            winreg.CloseKey(key)
        except Exception as e:
            QMessageBox.warning(self, "Registry Error", f"Could not update startup settings: {e}")

        self.accept()