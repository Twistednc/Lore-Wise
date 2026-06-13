import os
import json
import psutil
import win32gui
import win32process
import win32api
import sys
from dataclasses import dataclass
from typing import Optional

@dataclass
class GameInfo:
    name: str
    wiki_base: str
    process: str

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def get_writable_path(filename):
    """ Get path to files next to the EXE (Writable) """
    # If bundled, sys.executable is the path to the EXE.
    # We want to save user data in a 'data' folder next to that EXE.
    base_path = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.abspath(".")
    
    data_dir = os.path.join(base_path, "data")
    if not os.path.exists(data_dir):
        try:
            os.makedirs(data_dir)
        except: pass # Fallback to base path if permissions fail
        
    return os.path.join(data_dir, filename)

# games.json is bundled (Read-Only)
_GAMES_FILE = get_resource_path(os.path.join("data", "games.json"))

# user_mappings.json is external (Writable)
_USER_MAPPINGS = get_writable_path("user_mappings.json")

class GameDetector:
    def __init__(self):
        self._games = self._load_json(_GAMES_FILE)
        self._user_mappings = self._load_json(_USER_MAPPINGS)

    def _load_json(self, path):
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except: pass
        return {}

    def get_file_description(self, path):
        """Extracts 'File Description' from EXE metadata."""
        try:
            lang, codepage = win32api.GetFileVersionInfo(path, '\\VarFileInfo\\Translation')[0]
            str_path = u'\\StringFileInfo\\%04X%04X\\FileDescription' % (lang, codepage)
            return win32api.GetFileVersionInfo(path, str_path)
        except: return ""

    def get_active_game(self) -> Optional[GameInfo]:
        """Interpretation Layer: Matches window to game metadata/path/title."""
        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd: return None
            
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            proc = psutil.Process(pid)
            exe_path = proc.exe()
            exe_name = os.path.basename(exe_path).lower()
            file_desc = self.get_file_description(exe_path).lower()
            win_title = win32gui.GetWindowText(hwnd).lower()

            # 1. Check User Mappings first
            if exe_name in self._user_mappings:
                key = self._user_mappings[exe_name]
                g = self._games.get(key)
                if g: return GameInfo(g["name"], g.get("wiki", ""), exe_name)

            # 2. Heuristic Search
            for key, g in self._games.items():
                name = g["name"].lower()
                known_exes = [e.lower() for e in g.get("exe", [])]
                known_dirs = [d.lower() for d in g.get("dirs", [])]

                # Match by Description (Metadata)
                if name != "" and name in file_desc: 
                    return GameInfo(g["name"], g.get("wiki", ""), exe_name)
                
                # Match by Directory path
                for d in known_dirs:
                    if d != "" and f"\\{d}\\" in exe_path.lower():
                        return GameInfo(g["name"], g.get("wiki", ""), exe_name)
                
                # Match by Filename or Window Title
                if exe_name in known_exes or (name != "" and name in win_title):
                    return GameInfo(g["name"], g.get("wiki", ""), exe_name)

        except: pass
        return None

    def get_window_rect(self, process_name):
        """Finds the bounding box of the game window."""
        def callback(hwnd, extra):
            if win32gui.IsWindowVisible(hwnd):
                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    if psutil.Process(pid).name().lower() == process_name.lower():
                        extra.append(win32gui.GetWindowRect(hwnd))
                except: pass
            return True
        
        rects = []
        win32gui.EnumWindows(callback, rects)
        if rects:
            r = rects[0]
            return (r[0], r[1], r[2]-r[0], r[3]-r[1])
        
        # Fallback to current foreground
        try:
            hwnd = win32gui.GetForegroundWindow()
            r = win32gui.GetWindowRect(hwnd)
            return (r[0], r[1], r[2]-r[0], r[3]-r[1])
        except: return None