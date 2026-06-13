import sys
import threading
import ctypes
import os
import traceback
import json
import psutil
import win32gui
import win32process

# 1. OPTIMIZATION: Set before any imports
os.environ["QTWEBENGINE_DISABLE_GPU"] = "1" 

from PyQt5.QtCore import QObject, pyqtSignal, QTimer, Qt
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction, QDialog, QMessageBox, QInputDialog

# Import local modules
try:
    from core.game_detector import GameDetector, _USER_MAPPINGS
    from core.hotkey_manager import HotkeyManager
    from ui.overlay import Overlay
    from ui.settings_dialog import SettingsDialog
except Exception as e:
    print(f"CRITICAL ERROR (Module Import): {e}")
    sys.exit(1)

def is_admin():
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False

class HotkeyBridge(QObject):
    trigger = pyqtSignal()

def main():
    # 2. DPI SETTINGS: Sharp UI on 4K/1440p
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    try:
        print("--- LoreWise Startup ---")
        if not is_admin():
            print("WARNING: Not running as Admin. Hotkeys will likely fail.")

        overlay = Overlay()
        detector = GameDetector()
        bridge = HotkeyBridge()

        # --- LOGIC: Toggling ---
        def toggle_logic():
            active_game = detector.get_active_game()
            overlay.toggle(active_game)

        bridge.trigger.connect(toggle_logic)

        # --- LOGIC: Linking (Interpretation Layer) ---
        def link_current_window():
            """Learn a new EXE name by linking it to a game in games.json"""
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd or hwnd == int(overlay.winId()):
                QMessageBox.warning(None, "Error", "Please tab into your game first, then use this option from the tray.")
                return

            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                proc = psutil.Process(pid)
                exe_name = proc.name().lower()
                
                # Get list of known games
                game_names = [g["name"] for g in detector._games.values()]
                item, ok = QInputDialog.getItem(None, "Interpret Game Window", 
                                              f"Associate '{exe_name}' with:", 
                                              game_names, 0, False)
                if ok and item:
                    # Find the key for the selected game
                    game_key = [k for k, v in detector._games.items() if v["name"] == item][0]
                    
                    # Update detector and save to file
                    detector._user_mappings[exe_name] = game_key
                    with open(_USER_MAPPINGS, "w", encoding="utf-8") as f:
                        json.dump(detector._user_mappings, f, indent=2)
                    
                    QMessageBox.information(None, "LoreWise", f"Success! {exe_name} is now linked to {item}.")
            except Exception as e:
                QMessageBox.critical(None, "Error", f"Could not link window: {e}")

        # --- LOGIC: Settings ---
        def open_settings():
            dialog = SettingsDialog()
            if dialog.exec_() == QDialog.Accepted:
                os.execl(sys.executable, sys.executable, *sys.argv)

        # --- TRAY ICON ---
        tray = QSystemTrayIcon(QApplication.style().standardIcon(QApplication.style().SP_ComputerIcon), app)
        menu = QMenu()
        
        link_act = QAction("Link Active Window to Game...", menu)
        link_act.triggered.connect(link_current_window)
        
        set_act = QAction("Settings", menu)
        set_act.triggered.connect(open_settings)
        
        quit_act = QAction("Exit LoreWise", menu)
        quit_act.triggered.connect(app.quit)
        
        menu.addAction(link_act)
        menu.addSeparator()
        menu.addAction(set_act)
        menu.addAction(quit_act)
        
        tray.setContextMenu(menu)
        tray.show()

        # --- HOTKEY THREAD ---
        def on_press():
            bridge.trigger.emit()

        hotkey_mgr = HotkeyManager(callback=on_press)
        t = threading.Thread(target=hotkey_mgr.listen, daemon=True)
        t.start()

        print("LoreWise is active. (Running as Admin recommended)")
        sys.exit(app.exec_())

    except Exception as e:
        error_msg = traceback.format_exc()
        QMessageBox.critical(None, "LoreWise Crash", f"Fatal error:\n\n{error_msg}")
        sys.exit(1)

if __name__ == "__main__":
    main()