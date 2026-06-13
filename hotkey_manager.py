import keyboard
import json
import os

# Get the absolute path to the project root (where config.json is)
_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_CONFIG_FILE = os.path.join(_ROOT_DIR, "config.json")

def _load_hotkey() -> str:
    try:
        if os.path.exists(_CONFIG_FILE):
            with open(_CONFIG_FILE, "r") as f:
                key = json.load(f).get("hotkey", "ctrl+g")
                print(f"[DEBUG] Loaded hotkey from config: {key}")
                return key
    except Exception as e:
        print(f"[DEBUG] Error loading config.json: {e}")
    
    print("[DEBUG] Falling back to default hotkey: ctrl+g")
    return "ctrl+g"

class HotkeyManager:
    def __init__(self, callback):
        self._callback = callback
        self._hotkey = _load_hotkey()

    def listen(self):
        print(f"[DEBUG] Starting listener for: {self._hotkey}")
        try:
            # We use add_hotkey with a small lambda to ensure it's clean
            keyboard.add_hotkey(self._hotkey, lambda: self._callback(), suppress=False)
            keyboard.wait()
        except Exception as e:
            print(f"[DEBUG] Hotkey Listener Error: {e}")