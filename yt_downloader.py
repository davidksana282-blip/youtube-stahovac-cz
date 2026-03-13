#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Universal Video Downloader  –  YouTube, TikTok, Instagram, X, Facebook, Vimeo, Twitch, Reddit, SoundCloud + more
Dependencies install automatically on first run.
"""

import sys, os
if sys.platform == "win32":
    import ctypes
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

APP_DIR      = os.path.dirname(os.path.abspath(sys.argv[0]))
CONFIG_FILE  = os.path.join(APP_DIR, "downloader_config.json")
HISTORY_FILE = os.path.join(APP_DIR, "downloader_history.json")

import subprocess, importlib, importlib.util

REQUIRED = [("yt_dlp", "yt-dlp"), ("customtkinter", "customtkinter")]
_missing = [(m, p) for m, p in REQUIRED if not importlib.util.find_spec(m)]

if _missing:
    import tkinter as tk
    from tkinter import ttk
    _splash = tk.Tk()
    _splash.title("Installing..." if True else "")
    _splash.geometry("420x130")
    _splash.resizable(False, False)
    _splash.configure(bg="#1a1a2e")
    tk.Label(_splash, text="First run – installing dependencies...",
             bg="#1a1a2e", fg="white", font=("Segoe UI", 11)).pack(pady=(18, 6))
    _lbl = tk.Label(_splash, text="", bg="#1a1a2e", fg="#67e8f9", font=("Segoe UI", 10))
    _lbl.pack()
    _bar = ttk.Progressbar(_splash, length=360, mode="indeterminate")
    _bar.pack(pady=8); _bar.start(12)

    def _do_install():
        for mod, pkg in _missing:
            _splash.after(0, _lbl.config, {"text": f"Installing: {pkg}"})
            cmd = [sys.executable, "-m", "pip", "install", pkg, "-q"]
            # Parametr --break-system-packages pouze na Linuxu
            if sys.platform.startswith("linux"):
                cmd.insert(-1, "--break-system-packages")
            subprocess.check_call(cmd)
        _splash.after(0, _splash.destroy)

    import threading
    threading.Thread(target=_do_install, daemon=True).start()
    _splash.mainloop()

import json, shutil, threading, datetime, re
from pathlib import Path
import customtkinter as ctk
import yt_dlp

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ══════════════════════════════════════════════════════════════════
#  Translations
# ══════════════════════════════════════════════════════════════════

STRINGS = {
    "cs": {
        "app_title":          "Universal Video Downloader",
        "sources_bar":        "  YouTube  |  TikTok  |  Instagram  |  X/Twitter  |  Facebook  |  Vimeo  |  Twitch  |  Reddit  |  SoundCloud  |  a další...",
        "ffmpeg_missing":     "  ffmpeg není nalezen – merge videa/MP3 nebude fungovat.",
        "ffmpeg_download":    "Stáhnout ffmpeg",
        "ffmpeg_installing":  "Stahuji ffmpeg přes winget...",
        "ffmpeg_done":        "✅ ffmpeg úspěšně nainstalován!",
        "ffmpeg_restart":     "ffmpeg nainstalován – restart aplikace může být nutný.",
        "ffmpeg_failed":      "Instalace ffmpeg selhala: ",
        "url_label":          "URL videa / playlistu:",
        "url_placeholder":    "https://  (YouTube, TikTok, Instagram, X, Facebook, Vimeo...)",
        "btn_load":           "Načíst",
        "btn_loading":        "Načítám...",
        "source_label":       "  Zdroj: ",
        "folder_label":       "Cílová složka:",
        "btn_change":         "Změnit",
        "info_default":       "Zadejte URL a klikněte na Načíst",
        "tab_video":          "Video",
        "tab_mp3":            "MP3 / Audio",
        "tab_playlist":       "Playlist",
        "tab_history":        "Historie",
        "quality_label":      "Dostupné kvality:",
        "formats_empty":      "Nejprve načtěte video...",
        "mp3_quality_label":  "Kvalita MP3:",
        "mp3_note":           "Pro MP3 je vyžadován ffmpeg.",
        "mp3_best":           "nejlepší",
        "playlist_items":     "Položky playlistu:",
        "pl_download_all":    "Stáhnout vše",
        "pl_download_sel":    "Pouze vybrané",
        "pl_check_all":       "✔ Označit vše",
        "pl_uncheck_all":     "✘ Odznačit vše",
        "pl_empty":           "Načtěte playlist...",
        "pl_count":           "položek",
        "pl_playlist_fmt":    "Playlist",
        "history_label":      "Stažené soubory:",
        "btn_clear_hist":     "Vymazat historii",
        "history_empty":      "Zatím žádné stažené soubory.",
        "btn_open":           "Otevřít",
        "btn_dl_video":       "⬇  Stáhnout video",
        "btn_dl_mp3":         "🎵 Stáhnout MP3",
        "status_ready":       "Připraveno",
        "status_loading":     "Načítám informace...",
        "status_loaded":      "Načteno. Vyberte kvalitu a stáhněte.",
        "status_dl_video":    "Stahuji video...",
        "status_dl_audio":    "Stahuji audio ({q} kbps)...",
        "status_merging":     "Spojuji video + audio (ffmpeg)...",
        "status_done":        "✅ Hotovo! Uloženo do: ",
        "status_no_url":      "Zadejte URL.",
        "status_no_fmt":      "Vyberte kvalitu.",
        "status_no_sel":      "Nevybrána žádná položka.",
        "status_err":         "Chyba: ",
        "status_dl_frag":     "Stahuji část {i}/{n}",
        "status_dl_vid_n":    "Video {n}: Stahuji...",
        "no_formats":         "Žádné video formáty.",
        "playlist_qual":      "Playlist: použije se nejlepší dostupná kvalita.",
        "settings_title":     "Nastavení",
        "settings_lang":      "Jazyk aplikace:",
        "settings_save":      "Uložit",
        "settings_close":     "Zavřít",
        "unknown_source":     "Neznámý zdroj",
        "playlist_badge":     "PLAYLIST",
        "lang_pick_title":    "Vítejte / Welcome",
        "lang_pick_msg":      "Vyberte jazyk aplikace:\nChoose application language:",
        "lang_pick_btn":      "Potvrdit / Confirm",
    },
    "en": {
        "app_title":          "Universal Video Downloader",
        "sources_bar":        "  YouTube  |  TikTok  |  Instagram  |  X/Twitter  |  Facebook  |  Vimeo  |  Twitch  |  Reddit  |  SoundCloud  |  and more...",
        "ffmpeg_missing":     "  ffmpeg not found – video merge and MP3 conversion won't work.",
        "ffmpeg_download":    "Download ffmpeg",
        "ffmpeg_installing":  "Downloading ffmpeg via winget...",
        "ffmpeg_done":        "✅ ffmpeg installed successfully!",
        "ffmpeg_restart":     "ffmpeg installed – app restart may be required.",
        "ffmpeg_failed":      "ffmpeg installation failed: ",
        "url_label":          "Video / Playlist URL:",
        "url_placeholder":    "https://  (YouTube, TikTok, Instagram, X, Facebook, Vimeo...)",
        "btn_load":           "Load",
        "btn_loading":        "Loading...",
        "source_label":       "  Source: ",
        "folder_label":       "Download folder:",
        "btn_change":         "Change",
        "info_default":       "Enter a URL and click Load",
        "tab_video":          "Video",
        "tab_mp3":            "MP3 / Audio",
        "tab_playlist":       "Playlist",
        "tab_history":        "History",
        "quality_label":      "Available qualities:",
        "formats_empty":      "Load a video first...",
        "mp3_quality_label":  "MP3 Quality:",
        "mp3_note":           "ffmpeg is required for MP3 conversion.",
        "mp3_best":           "best",
        "playlist_items":     "Playlist items:",
        "pl_download_all":    "Download all",
        "pl_download_sel":    "Selected only",
        "pl_check_all":       "✔ Select all",
        "pl_uncheck_all":     "✘ Deselect all",
        "pl_empty":           "Load a playlist...",
        "pl_count":           "items",
        "pl_playlist_fmt":    "Playlist",
        "history_label":      "Downloaded files:",
        "btn_clear_hist":     "Clear history",
        "history_empty":      "No downloads yet.",
        "btn_open":           "Open",
        "btn_dl_video":       "⬇  Download video",
        "btn_dl_mp3":         "🎵 Download MP3",
        "status_ready":       "Ready",
        "status_loading":     "Loading info...",
        "status_loaded":      "Loaded. Select quality and download.",
        "status_dl_video":    "Downloading video...",
        "status_dl_audio":    "Downloading audio ({q} kbps)...",
        "status_merging":     "Merging video + audio (ffmpeg)...",
        "status_done":        "✅ Done! Saved to: ",
        "status_no_url":      "Enter a URL.",
        "status_no_fmt":      "Select a quality.",
        "status_no_sel":      "No item selected.",
        "status_err":         "Error: ",
        "status_dl_frag":     "Downloading part {i}/{n}",
        "status_dl_vid_n":    "Video {n}: Downloading...",
        "no_formats":         "No video formats found.",
        "playlist_qual":      "Playlist: best available quality will be used.",
        "settings_title":     "Settings",
        "settings_lang":      "Application language:",
        "settings_save":      "Save",
        "settings_close":     "Close",
        "unknown_source":     "Unknown source",
        "playlist_badge":     "PLAYLIST",
        "lang_pick_title":    "Welcome / Vítejte",
        "lang_pick_msg":      "Choose application language:\nVyberte jazyk aplikace:",
        "lang_pick_btn":      "Confirm / Potvrdit",
    },
}

# ══════════════════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════════════════

def _fmt_size(b):
    if b >= 1 << 30: return f"{b/(1<<30):.2f} GB"
    if b >= 1 << 20: return f"{b/(1<<20):.1f} MB"
    return f"{b/1024:.0f} KB"

def detect_ffmpeg():
    return shutil.which("ffmpeg") is not None

def load_config():
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f: return json.load(f)
    except Exception: return {}

def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception: pass

def load_history():
    try:
        with open(HISTORY_FILE, encoding="utf-8") as f: return json.load(f)
    except Exception: return []

def save_history(h):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(h[-200:], f, ensure_ascii=False, indent=2)
    except Exception: pass

def append_history(entry):
    h = load_history(); h.append(entry); save_history(h)

SOURCE_PATTERNS = [
    (r"youtube\.com|youtu\.be",      "YouTube",    "#e94560"),
    (r"tiktok\.com",                  "TikTok",     "#69c9d0"),
    (r"instagram\.com",               "Instagram",  "#c13584"),
    (r"twitter\.com|x\.com",         "X / Twitter","#1d9bf0"),
    (r"facebook\.com|fb\.watch",     "Facebook",   "#1877f2"),
    (r"vimeo\.com",                   "Vimeo",      "#1ab7ea"),
    (r"twitch\.tv",                   "Twitch",     "#9147ff"),
    (r"reddit\.com|v\.redd\.it",     "Reddit",     "#ff4500"),
    (r"dailymotion\.com",             "Dailymotion","#0066dc"),
    (r"soundcloud\.com",              "SoundCloud", "#ff5500"),
]

def detect_source(url, unknown_label="Unknown source"):
    for pattern, name, color in SOURCE_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            return name, color
    return unknown_label, "gray"

def is_playlist(url):
    return bool(re.search(r"list=|/playlist/|/sets/", url, re.IGNORECASE))

# ══════════════════════════════════════════════════════════════════
#  Language picker dialog
# ══════════════════════════════════════════════════════════════════

def pick_language():
    """Shows a simple language picker, returns 'cs' or 'en'."""
    result = {"lang": "cs"}
    s = STRINGS["cs"]  # use bilingual strings from cs block

    dlg = ctk.CTk()
    dlg.title(s["lang_pick_title"])
    dlg.geometry("380x220")
    dlg.resizable(False, False)

    ctk.CTkLabel(dlg, text=s["lang_pick_msg"],
        font=ctk.CTkFont(size=14), justify="center").pack(pady=(30, 16))

    lang_var = ctk.StringVar(value="cs")
    row = ctk.CTkFrame(dlg, fg_color="transparent")
    row.pack()
    ctk.CTkRadioButton(row, text="Čeština 🇨🇿", variable=lang_var, value="cs",
        font=ctk.CTkFont(size=14)).pack(side="left", padx=20)
    ctk.CTkRadioButton(row, text="English 🇬🇧", variable=lang_var, value="en",
        font=ctk.CTkFont(size=14)).pack(side="left", padx=20)

    def confirm():
        result["lang"] = lang_var.get()
        dlg.destroy()

    ctk.CTkButton(dlg, text=s["lang_pick_btn"], height=40, width=180,
        font=ctk.CTkFont(size=13, weight="bold"),
        fg_color="#e94560", hover_color="#c73652",
        command=confirm).pack(pady=20)

    dlg.mainloop()
    return result["lang"]

# ══════════════════════════════════════════════════════════════════
#  Main app
# ══════════════════════════════════════════════════════════════════

class DownloaderApp(ctk.CTk):
    def __init__(self, lang: str):
        super().__init__()
        self._lang = lang
        self._cfg  = load_config()
        self._s    = STRINGS[lang]

        self.download_path    = self._cfg.get("download_path", str(Path.home() / "Downloads"))
        self.formats          = []
        self.current_info     = None
        self._indeterminate   = False
        self._ffmpeg_ok       = detect_ffmpeg()
        self._downloaded_path = None
        self._download_is_mp3 = False
        self._is_playlist     = False
        self._playlist_items  = []
        self._playlist_checks = []

        self.title(self._s["app_title"])
        self.geometry("860x950")
        self.resizable(True, True)
        self.minsize(680, 800)

        self._build_ui()
        self._check_ffmpeg_banner()

    # ──────────────────────── Shortcut ────────────────────────────
    def _(self, key, **kwargs):
        t = self._s.get(key, key)
        return t.format(**kwargs) if kwargs else t

    # ──────────────────────── Build UI ────────────────────────────
    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="#1a1a2e", corner_radius=0)
        header.pack(fill="x")
        ctk.CTkLabel(header, text=f"  {self._('app_title')}",
            font=ctk.CTkFont(family="Segoe UI", size=21, weight="bold"),
            text_color="#e94560").pack(side="left", padx=20, pady=13)

        # Settings gear button in header
        ctk.CTkButton(header, text="⚙", width=40, height=34,
            font=ctk.CTkFont(size=18), fg_color="transparent", hover_color="#2a2a4a",
            command=self._open_settings).pack(side="right", padx=12, pady=6)

        # Sources bar
        sources_bar = ctk.CTkFrame(self, fg_color="#0d0d1a", corner_radius=0)
        sources_bar.pack(fill="x")
        ctk.CTkLabel(sources_bar, text=self._("sources_bar"),
            font=ctk.CTkFont(size=11), text_color="#555").pack(side="left", padx=16, pady=5)

        # ffmpeg banner (hidden by default)
        self.ffmpeg_banner = ctk.CTkFrame(self, fg_color="#3b1a00", corner_radius=0)
        self.ffmpeg_banner_lbl = ctk.CTkLabel(self.ffmpeg_banner,
            text=self._("ffmpeg_missing"),
            font=ctk.CTkFont(size=12), text_color="#fde68a", anchor="w")
        self.ffmpeg_banner_lbl.pack(side="left", padx=14, pady=8, fill="x", expand=True)
        self.ffmpeg_dl_btn = ctk.CTkButton(self.ffmpeg_banner,
            text=self._("ffmpeg_download"), width=160, height=30,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#e94560", hover_color="#c73652", command=self._download_ffmpeg)
        self.ffmpeg_dl_btn.pack(side="right", padx=10, pady=6)

        # URL
        url_frame = ctk.CTkFrame(self, fg_color="transparent")
        url_frame.pack(fill="x", padx=20, pady=(14, 0))
        ctk.CTkLabel(url_frame, text=self._("url_label"),
            font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w")
        input_row = ctk.CTkFrame(url_frame, fg_color="transparent")
        input_row.pack(fill="x", pady=(4, 0))
        self.url_entry = ctk.CTkEntry(input_row,
            placeholder_text=self._("url_placeholder"),
            height=44, font=ctk.CTkFont(size=13))
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.url_entry.bind("<Return>", lambda e: self.fetch_formats())
        self.url_entry.bind("<KeyRelease>", self._on_url_change)
        self.fetch_btn = ctk.CTkButton(input_row, text=self._("btn_load"),
            width=110, height=44, font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#e94560", hover_color="#c73652", command=self.fetch_formats)
        self.fetch_btn.pack(side="left")

        badge_row = ctk.CTkFrame(url_frame, fg_color="transparent")
        badge_row.pack(fill="x", pady=(5, 0))
        self.source_badge   = ctk.CTkLabel(badge_row, text="",
            font=ctk.CTkFont(size=11, weight="bold"), text_color="gray", anchor="w")
        self.source_badge.pack(side="left")
        self.playlist_badge = ctk.CTkLabel(badge_row, text="",
            font=ctk.CTkFont(size=11, weight="bold"), text_color="#fde68a", anchor="w")
        self.playlist_badge.pack(side="left", padx=(12, 0))

        # Folder
        folder_frame = ctk.CTkFrame(self, fg_color="transparent")
        folder_frame.pack(fill="x", padx=20, pady=(8, 0))
        ctk.CTkLabel(folder_frame, text=self._("folder_label"),
            font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w")
        folder_row = ctk.CTkFrame(folder_frame, fg_color="transparent")
        folder_row.pack(fill="x", pady=(4, 0))
        self.folder_label_w = ctk.CTkLabel(folder_row, text=self.download_path,
            font=ctk.CTkFont(size=12), text_color="gray", anchor="w")
        self.folder_label_w.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(folder_row, text=self._("btn_change"), width=100, height=32,
            font=ctk.CTkFont(size=12), command=self.choose_folder).pack(side="left", padx=(8, 0))

        # Video info box
        self.info_frame = ctk.CTkFrame(self, fg_color="#16213e", corner_radius=10)
        self.info_frame.pack(fill="x", padx=20, pady=(10, 0))
        self.video_title_label = ctk.CTkLabel(self.info_frame, text=self._("info_default"),
            font=ctk.CTkFont(size=13), text_color="gray", wraplength=780, justify="left")
        self.video_title_label.pack(anchor="w", padx=14, pady=(8, 2))
        self.video_meta_label = ctk.CTkLabel(self.info_frame, text="",
            font=ctk.CTkFont(size=11), text_color="#888", anchor="w")
        self.video_meta_label.pack(anchor="w", padx=14, pady=(0, 8))

        # Tabs
        self.tab_view = ctk.CTkTabview(self, height=210)
        self.tab_view.pack(fill="both", expand=True, padx=20, pady=(10, 0))
        self.tab_video    = self.tab_view.add(self._("tab_video"))
        self.tab_mp3      = self.tab_view.add(self._("tab_mp3"))
        self.tab_playlist = self.tab_view.add(self._("tab_playlist"))
        self.tab_history  = self.tab_view.add(self._("tab_history"))

        # Video tab
        ctk.CTkLabel(self.tab_video, text=self._("quality_label"),
            font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", pady=(0, 6))
        self.format_var = ctk.StringVar(value="")
        self.formats_scroll = ctk.CTkScrollableFrame(self.tab_video, height=140)
        self.formats_scroll.pack(fill="both", expand=True)
        ctk.CTkLabel(self.formats_scroll, text=self._("formats_empty"),
            text_color="gray", font=ctk.CTkFont(size=12)).pack(pady=20)

        # MP3 tab
        mp3_inner = ctk.CTkFrame(self.tab_mp3, fg_color="transparent")
        mp3_inner.pack(fill="both", expand=True)
        ctk.CTkLabel(mp3_inner, text=self._("mp3_quality_label"),
            font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", pady=(4, 6))
        self.mp3_quality_var = ctk.StringVar(value=self._cfg.get("mp3_quality", "320"))
        q_row = ctk.CTkFrame(mp3_inner, fg_color="transparent")
        q_row.pack(anchor="w")
        for lbl, val in [("320 kbps", "320"), ("256 kbps", "256"), ("192 kbps", "192"), ("128 kbps", "128"), ("96 kbps", "96")]:
            ctk.CTkRadioButton(q_row, text=lbl, variable=self.mp3_quality_var, value=val,
                font=ctk.CTkFont(size=13), command=self._save_config).pack(side="left", padx=(0, 14), pady=4)
        ctk.CTkLabel(mp3_inner, text=self._("mp3_note"),
            font=ctk.CTkFont(size=11), text_color="gray").pack(anchor="w", pady=(10, 0))

        # Playlist tab
        self._build_playlist_tab()

        # History tab
        self._build_history_tab()

        # Download buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(14, 0))
        btn_frame.grid_columnconfigure(0, weight=1)
        btn_frame.grid_columnconfigure(1, weight=1)
        self.download_video_btn = ctk.CTkButton(btn_frame,
            text=self._("btn_dl_video"), height=56,
            font=ctk.CTkFont(size=17, weight="bold"),
            fg_color="#e94560", hover_color="#c73652", corner_radius=12,
            command=self.download_video, state="disabled")
        self.download_video_btn.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.download_mp3_btn = ctk.CTkButton(btn_frame,
            text=self._("btn_dl_mp3"), height=56,
            font=ctk.CTkFont(size=17, weight="bold"),
            fg_color="#1565c0", hover_color="#0d47a1", corner_radius=12,
            command=self.download_mp3, state="disabled")
        self.download_mp3_btn.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        # Progress panel
        prog_outer = ctk.CTkFrame(self, fg_color="#16213e", corner_radius=12)
        prog_outer.pack(fill="x", padx=20, pady=(14, 16))
        top_row = ctk.CTkFrame(prog_outer, fg_color="transparent")
        top_row.pack(fill="x", padx=16, pady=(12, 4))
        self.phase_label = ctk.CTkLabel(top_row, text=self._("status_ready"),
            font=ctk.CTkFont(size=13, weight="bold"), text_color="gray", anchor="w")
        self.phase_label.pack(side="left", fill="x", expand=True)
        self.pct_label = ctk.CTkLabel(top_row, text="",
            font=ctk.CTkFont(size=13, weight="bold"), text_color="gray", anchor="e", width=60)
        self.pct_label.pack(side="right")
        self.progress_bar = ctk.CTkProgressBar(prog_outer, height=16, corner_radius=8)
        self.progress_bar.pack(fill="x", padx=16, pady=(0, 8))
        self.progress_bar.set(0)
        detail_row = ctk.CTkFrame(prog_outer, fg_color="transparent")
        detail_row.pack(fill="x", padx=16, pady=(0, 12))
        self.speed_label = ctk.CTkLabel(detail_row, text="", font=ctk.CTkFont(size=12), text_color="#67e8f9", anchor="w")
        self.speed_label.pack(side="left")
        self.eta_label = ctk.CTkLabel(detail_row, text="", font=ctk.CTkFont(size=12), text_color="#fde68a")
        self.eta_label.pack(side="left", padx=(20, 0))
        self.size_label = ctk.CTkLabel(detail_row, text="", font=ctk.CTkFont(size=12), text_color="gray", anchor="e")
        self.size_label.pack(side="right")

    # ── Playlist tab ───────────────────────────────────────────────
    def _build_playlist_tab(self):
        top = ctk.CTkFrame(self.tab_playlist, fg_color="transparent")
        top.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(top, text=self._("playlist_items"),
            font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")
        self.playlist_count_label = ctk.CTkLabel(top, text="",
            font=ctk.CTkFont(size=12), text_color="gray")
        self.playlist_count_label.pack(side="left", padx=(10, 0))

        # Download mode radio
        self.playlist_mode_var = ctk.StringVar(value="all")
        mode_row = ctk.CTkFrame(self.tab_playlist, fg_color="transparent")
        mode_row.pack(fill="x", pady=(0, 4))
        ctk.CTkRadioButton(mode_row, text=self._("pl_download_all"),
            variable=self.playlist_mode_var, value="all",
            font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 20))
        ctk.CTkRadioButton(mode_row, text=self._("pl_download_sel"),
            variable=self.playlist_mode_var, value="selected",
            font=ctk.CTkFont(size=12)).pack(side="left")

        # Select all / deselect all buttons
        sel_row = ctk.CTkFrame(self.tab_playlist, fg_color="transparent")
        sel_row.pack(fill="x", pady=(0, 4))
        ctk.CTkButton(sel_row, text=self._("pl_check_all"), width=130, height=28,
            font=ctk.CTkFont(size=12), fg_color="#1565c0", hover_color="#0d47a1",
            command=self._playlist_select_all).pack(side="left", padx=(0, 8))
        ctk.CTkButton(sel_row, text=self._("pl_uncheck_all"), width=130, height=28,
            font=ctk.CTkFont(size=12), fg_color="#3b3b3b", hover_color="#555",
            command=self._playlist_deselect_all).pack(side="left")

        self.playlist_scroll = ctk.CTkScrollableFrame(self.tab_playlist, height=100)
        self.playlist_scroll.pack(fill="both", expand=True)
        ctk.CTkLabel(self.playlist_scroll, text=self._("pl_empty"),
            text_color="gray", font=ctk.CTkFont(size=12)).pack(pady=12)

    def _playlist_select_all(self):
        for v in self._playlist_checks: v.set(True)

    def _playlist_deselect_all(self):
        for v in self._playlist_checks: v.set(False)

    # ── History tab ────────────────────────────────────────────────
    def _build_history_tab(self):
        top = ctk.CTkFrame(self.tab_history, fg_color="transparent")
        top.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(top, text=self._("history_label"),
            font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")
        ctk.CTkButton(top, text=self._("btn_clear_hist"), width=140, height=28,
            font=ctk.CTkFont(size=12), fg_color="#3b3b3b", hover_color="#555",
            command=self._clear_history).pack(side="right")
        self.history_scroll = ctk.CTkScrollableFrame(self.tab_history, height=140)
        self.history_scroll.pack(fill="both", expand=True)
        self._refresh_history_ui()

    def _refresh_history_ui(self):
        for w in self.history_scroll.winfo_children(): w.destroy()
        history = load_history()
        if not history:
            ctk.CTkLabel(self.history_scroll, text=self._("history_empty"),
                text_color="gray", font=ctk.CTkFont(size=12)).pack(pady=20)
            return
        for entry in reversed(history):
            row = ctk.CTkFrame(self.history_scroll, fg_color="#0f3460", corner_radius=8)
            row.pack(fill="x", pady=3, padx=4)
            icon = "MP3" if entry.get("type") == "mp3" else "MP4"
            left = ctk.CTkFrame(row, fg_color="transparent")
            left.pack(side="left", fill="x", expand=True, padx=10, pady=6)
            src = entry.get("source", "")
            title_txt = f"[{icon}] [{src}]  {entry.get('title','?')}" if src else f"[{icon}]  {entry.get('title','?')}"
            ctk.CTkLabel(left, text=title_txt, font=ctk.CTkFont(size=12, weight="bold"),
                anchor="w", wraplength=520).pack(anchor="w")
            meta = "  |  ".join(filter(None, [entry.get("quality",""), entry.get("size",""), entry.get("date","")]))
            ctk.CTkLabel(left, text=meta, font=ctk.CTkFont(size=11),
                text_color="gray", anchor="w").pack(anchor="w")
            dest = entry.get("path", "")
            if dest and os.path.exists(dest):
                ctk.CTkButton(row, text=self._("btn_open"), width=70, height=32,
                    font=ctk.CTkFont(size=12), fg_color="#1565c0", hover_color="#0d47a1",
                    command=lambda p=dest: self._open_in_explorer(p)).pack(side="right", padx=8)

    def _clear_history(self):
        save_history([]); self._refresh_history_ui()

    @staticmethod
    def _open_in_explorer(path):
        if sys.platform == "win32":
            subprocess.Popen(f'explorer /select,"{path}"')
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", path])
        else:
            subprocess.Popen(["xdg-open", os.path.dirname(path)])

    # ── Settings dialog ────────────────────────────────────────────
    def _open_settings(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title(self._("settings_title"))
        dlg.geometry("340x200")
        dlg.resizable(False, False)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text=self._("settings_title"),
            font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(20, 10))
        ctk.CTkLabel(dlg, text=self._("settings_lang"),
            font=ctk.CTkFont(size=13)).pack()

        lang_var = ctk.StringVar(value=self._lang)
        row = ctk.CTkFrame(dlg, fg_color="transparent")
        row.pack(pady=8)
        ctk.CTkRadioButton(row, text="Čeština 🇨🇿", variable=lang_var, value="cs",
            font=ctk.CTkFont(size=13)).pack(side="left", padx=16)
        ctk.CTkRadioButton(row, text="English 🇬🇧", variable=lang_var, value="en",
            font=ctk.CTkFont(size=13)).pack(side="left", padx=16)

        def save_lang():
            new_lang = lang_var.get()
            self._cfg["language"] = new_lang
            save_config(self._cfg)
            dlg.destroy()
            # Restart the app with new language
            self._restart_with_lang(new_lang)

        btns = ctk.CTkFrame(dlg, fg_color="transparent")
        btns.pack(pady=12)
        ctk.CTkButton(btns, text=self._("settings_save"), width=110, height=36,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#e94560", hover_color="#c73652",
            command=save_lang).pack(side="left", padx=8)
        ctk.CTkButton(btns, text=self._("settings_close"), width=110, height=36,
            font=ctk.CTkFont(size=13), fg_color="#3b3b3b", hover_color="#555",
            command=dlg.destroy).pack(side="left", padx=8)

    def _restart_with_lang(self, lang):
        """Destroy and rebuild the whole window with the new language."""
        self._lang = lang
        self._s    = STRINGS[lang]
        # Destroy all children and rebuild
        for w in self.winfo_children(): w.destroy()
        self._build_ui()
        self._check_ffmpeg_banner()
        # Reset state
        self.formats = []
        self.current_info = None
        self._is_playlist = False
        self._playlist_items = []
        self._playlist_checks = []

    # ── ffmpeg ─────────────────────────────────────────────────────
    def _check_ffmpeg_banner(self):
        if not self._ffmpeg_ok:
            self.ffmpeg_banner.pack(fill="x")
            self.ffmpeg_banner.pack_configure(before=self.winfo_children()[2])

    def _download_ffmpeg(self):
        if sys.platform == "win32":
            self._set_phase(self._("ffmpeg_installing"), "yellow")
            self.ffmpeg_dl_btn.configure(state="disabled")
            threading.Thread(target=self._ffmpeg_install_thread, daemon=True).start()
        else:
            import webbrowser; webbrowser.open("https://ffmpeg.org/download.html")

    def _ffmpeg_install_thread(self):
        # Instalace FFmpeg pouze na Windows pomocí winget
        if sys.platform != "win32":
            self.after(0, self._set_phase, self._("ffmpeg_failed") + "winget is Windows-only", "red")
            self.after(0, lambda: self.ffmpeg_dl_btn.configure(state="normal"))
            return
        
        try:
            subprocess.run(["winget", "install", "--id", "Gyan.FFmpeg", "-e", "--silent"],
                check=True, capture_output=True)
            new_path = subprocess.check_output(
                ["powershell", "-Command",
                 "[System.Environment]::GetEnvironmentVariable('PATH','Machine')"],
                text=True).strip()
            os.environ["PATH"] = new_path + os.pathsep + os.environ.get("PATH", "")
            self._ffmpeg_ok = detect_ffmpeg()
            if self._ffmpeg_ok:
                self.after(0, self.ffmpeg_banner.pack_forget)
                self.after(0, self._set_phase, self._("ffmpeg_done"), "green")
            else:
                self.after(0, self._set_phase, self._("ffmpeg_restart"), "yellow")
                self.after(0, lambda: self.ffmpeg_dl_btn.configure(state="normal"))
        except Exception as e:
            self.after(0, self._set_phase, self._("ffmpeg_failed") + str(e), "red")
            self.after(0, lambda: self.ffmpeg_dl_btn.configure(state="normal"))

    # ── Config ─────────────────────────────────────────────────────
    def choose_folder(self):
        from tkinter import filedialog
        folder = filedialog.askdirectory(initialdir=self.download_path)
        if folder:
            self.download_path = folder
            self.folder_label_w.configure(text=folder)
            self._save_config()

    def _save_config(self):
        self._cfg["download_path"] = self.download_path
        self._cfg["mp3_quality"]   = self.mp3_quality_var.get()
        self._cfg["language"]      = self._lang
        save_config(self._cfg)

    # ── URL live detection ─────────────────────────────────────────
    def _on_url_change(self, event=None):
        url = self.url_entry.get().strip()
        if not url:
            self.source_badge.configure(text=""); self.playlist_badge.configure(text=""); return
        src, color = detect_source(url, self._("unknown_source"))
        self.source_badge.configure(text=self._("source_label") + src, text_color=color)
        self.playlist_badge.configure(text=self._("playlist_badge") if is_playlist(url) else "")

    # ── Fetch ──────────────────────────────────────────────────────
    def fetch_formats(self):
        url = self.url_entry.get().strip()
        if not url:
            self._set_phase(self._("status_no_url"), "red"); return
        self.fetch_btn.configure(state="disabled", text=self._("btn_loading"))
        self._set_phase(self._("status_loading"), "gray")
        self._start_indeterminate()
        self._is_playlist = is_playlist(url)
        threading.Thread(target=self._fetch_thread, args=(url,), daemon=True).start()

    def _fetch_thread(self, url):
        try:
            opts = {"quiet": True, "no_warnings": True}
            if self._is_playlist:
                opts["extract_flat"] = "in_playlist"
                opts["playlistend"]  = 200
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
            self.current_info = info
            self.after(0, self._populate_info, info)
        except Exception as e:
            self.after(0, self._stop_indeterminate)
            self.after(0, self._set_phase, self._("status_err") + str(e), "red")
            self.after(0, lambda: self.fetch_btn.configure(state="normal", text=self._("btn_load")))

    def _populate_info(self, info):
        self._stop_indeterminate()
        entries = info.get("entries")

        if entries is not None:
            # ── PLAYLIST ──────────────────────────────────────────
            self._is_playlist    = True
            self._playlist_items = list(entries)
            count = len(self._playlist_items)
            title = info.get("title") or info.get("playlist_title") or self._("pl_playlist_fmt")

            self.video_title_label.configure(
                text=f"{self._('pl_playlist_fmt').upper()}: {title}", text_color="#fde68a")
            self.video_meta_label.configure(text=f"{count} {self._('pl_count')}")
            self.playlist_count_label.configure(text=f"({count} {self._('pl_count')})")

            for w in self.playlist_scroll.winfo_children(): w.destroy()
            self._playlist_checks = []
            for i, entry in enumerate(self._playlist_items, 1):
                var = ctk.BooleanVar(value=(i == 1))  # Only first item checked by default
                row = ctk.CTkFrame(self.playlist_scroll, fg_color="transparent")
                row.pack(fill="x", pady=1)
                t = entry.get("title") or entry.get("url") or f"Video {i}"
                ctk.CTkCheckBox(row, text=f"{i}. {t}", variable=var,
                    font=ctk.CTkFont(size=11)).pack(anchor="w")
                self._playlist_checks.append(var)

            self.tab_view.set(self._("tab_playlist"))
            for w in self.formats_scroll.winfo_children(): w.destroy()
            ctk.CTkLabel(self.formats_scroll, text=self._("playlist_qual"),
                text_color="gray", font=ctk.CTkFont(size=12)).pack(pady=20)
            self.formats = []
            self.format_var.set("best")

        else:
            # ── SINGLE VIDEO ──────────────────────────────────────
            self._is_playlist    = False
            self._playlist_items = []
            title    = info.get("title", "?")
            duration = info.get("duration") or 0
            mins, secs = divmod(int(duration), 60)
            uploader = info.get("uploader") or info.get("channel") or ""
            src, _   = detect_source(self.url_entry.get().strip(), self._("unknown_source"))

            self.video_title_label.configure(text=title, text_color="white")
            meta_parts = [p for p in [uploader, f"{mins}:{secs:02d}" if duration else "", src] if p]
            self.video_meta_label.configure(text="  |  ".join(meta_parts))

            for w in self.formats_scroll.winfo_children(): w.destroy()
            seen, video_formats = set(), []
            for f in info.get("formats", []):
                if f.get("vcodec", "none") == "none": continue
                res = f.get("height") or 0; fps = f.get("fps") or 0
                ext = f.get("ext", "?");    fid = f.get("format_id", "")
                key = (res, ext)
                if key in seen: continue
                seen.add(key)
                label  = f"{res}p" if res else "?"
                label += f"  {fps:.0f}fps" if fps else ""
                label += f"  [{ext}]"
                tbr = f.get("tbr")
                if tbr: label += f"  ~{tbr:.0f}kbps"
                video_formats.append((res, label, fid))

            video_formats.sort(key=lambda x: x[0], reverse=True)
            if not video_formats:
                ctk.CTkLabel(self.formats_scroll, text=self._("no_formats"),
                    text_color="gray").pack(pady=20)
                self.formats = []
                # Deaktivovat tlačítka, pokud nejsou žádné formáty
                self.download_video_btn.configure(state="disabled")
                self.download_mp3_btn.configure(state="normal")  # MP3 může fungovat i bez video formátů
                self.fetch_btn.configure(state="normal", text=self._("btn_load"))
                self._set_phase(self._("no_formats"), "red")
                return
            else:
                self.format_var.set(video_formats[0][2])
                for _, label, fid in video_formats:
                    ctk.CTkRadioButton(self.formats_scroll, text=label,
                        variable=self.format_var, value=fid,
                        font=ctk.CTkFont(size=13)).pack(anchor="w", pady=3, padx=8)
            self.formats = video_formats

        self.download_video_btn.configure(state="normal")
        self.download_mp3_btn.configure(state="normal")
        self.fetch_btn.configure(state="normal", text=self._("btn_load"))
        self._set_phase(self._("status_loaded"), "green")

    # ── Download ───────────────────────────────────────────────────
    def download_video(self):
        if not self.current_info: return
        if not self._is_playlist:
            fmt = self.format_var.get()
            if not fmt: self._set_phase(self._("status_no_fmt"), "red"); return
        self._start_download(self.format_var.get(), is_mp3=False)

    def download_mp3(self):
        if not self.current_info: return
        self._start_download(None, is_mp3=True)

    def _start_download(self, fmt, is_mp3):
        self.download_video_btn.configure(state="disabled")
        self.download_mp3_btn.configure(state="disabled")
        self.progress_bar.set(0); self._clear_details()
        self._downloaded_path = None
        self._download_is_mp3 = is_mp3
        url = self.url_entry.get().strip()
        threading.Thread(target=self._download_thread, args=(url, fmt, is_mp3), daemon=True).start()

    def _download_thread(self, url, fmt, is_mp3):
        try:
            outtmpl = os.path.join(self.download_path, "%(title)s.%(ext)s")

            if self._is_playlist:
                if self.playlist_mode_var.get() == "selected":
                    selected = [i+1 for i, v in enumerate(self._playlist_checks) if v.get()]
                    if not selected:
                        self.after(0, self._set_phase, self._("status_no_sel"), "red")
                        self.after(0, self._re_enable_btns); return
                    playlist_items = ",".join(str(i) for i in selected)
                else:
                    playlist_items = "1-200"
                outtmpl = os.path.join(self.download_path,
                    "%(playlist_title)s", "%(playlist_index)s - %(title)s.%(ext)s")
            else:
                playlist_items = None

            if is_mp3:
                quality = self.mp3_quality_var.get()
                ydl_opts = {
                    "format": "bestaudio/best", "outtmpl": outtmpl,
                    "postprocessors": [{"key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3", "preferredquality": quality}],
                    "progress_hooks": [self._progress_hook],
                }
                if playlist_items: ydl_opts["playlist_items"] = playlist_items
                self.after(0, self._set_phase,
                    self._("status_dl_audio", q=quality), "cyan")
            else:
                fmt_str = ("bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
                           if self._is_playlist else
                           f"{fmt}[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best")
                ydl_opts = {
                    "format": fmt_str, "outtmpl": outtmpl,
                    "merge_output_format": "mp4",
                    "progress_hooks": [self._progress_hook],
                }
                if playlist_items: ydl_opts["playlist_items"] = playlist_items
                self.after(0, self._set_phase, self._("status_dl_video"), "cyan")

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                result = ydl.extract_info(url)
                if not self._is_playlist and result:
                    fn = ydl.prepare_filename(result)
                    self._downloaded_path = os.path.splitext(fn)[0] + (".mp3" if is_mp3 else ".mp4")

            self.after(0, self._download_done)
        except Exception as e:
            self.after(0, self._set_phase, self._("status_err") + str(e), "red")
            self.after(0, self._re_enable_btns)

    def _progress_hook(self, d):
        status = d.get("status")
        if status == "downloading":
            total      = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes") or 0
            speed      = d.get("speed") or 0
            eta        = d.get("eta")
            frag_idx   = d.get("fragment_index")
            frag_count = d.get("fragment_count")

            if total > 0:
                pct = downloaded / total
                self.after(0, self.progress_bar.set, pct)
                self.after(0, self.pct_label.configure,
                    {"text": f"{pct*100:.0f}%", "text_color": "#67e8f9"})
                self.after(0, self.size_label.configure,
                    {"text": f"{_fmt_size(downloaded)} / {_fmt_size(total)}"})
            else:
                self.after(0, self._start_indeterminate)

            phase = self._("status_dl_video")
            if frag_idx and frag_count:
                phase = self._("status_dl_frag", i=frag_idx, n=frag_count)
            vidnum = d.get("info_dict", {}).get("playlist_index")
            if vidnum: phase = self._("status_dl_vid_n", n=vidnum)

            self.after(0, self._set_phase, phase, "cyan")
            self.after(0, self.speed_label.configure,
                {"text": f"  {speed/1024/1024:.2f} MB/s" if speed > 0 else ""})
            if eta and eta > 0:
                m, s = divmod(int(eta), 60)
                self.after(0, self.eta_label.configure,
                    {"text": f"ETA {m}:{s:02d}" if m else f"ETA {s}s"})

        elif status == "finished":
            self._stop_indeterminate()
            self.after(0, self.progress_bar.set, 0.99)
            self.after(0, self.pct_label.configure, {"text": "99%", "text_color": "#fde68a"})
            self.after(0, self._set_phase, self._("status_merging"), "yellow")
            self.after(0, self.speed_label.configure, {"text": ""})
            self.after(0, self.eta_label.configure,   {"text": ""})

    def _download_done(self):
        self._stop_indeterminate()
        self.progress_bar.set(1.0)
        self.pct_label.configure(text="100%", text_color="#4ade80")
        self._set_phase(self._("status_done") + self.download_path, "green")
        self._re_enable_btns()

        info    = self.current_info or {}
        is_mp3  = self._download_is_mp3
        quality = self.mp3_quality_var.get() + " kbps" if is_mp3 else \
                  next((lbl for _, lbl, fid in self.formats if fid == self.format_var.get()),
                       self._("mp3_best"))
        path     = self._downloaded_path or ""
        
        # Bezpečné získání velikosti souboru - kontrola existence a typu
        size_str = ""
        if path and os.path.isfile(path):
            try:
                size_str = _fmt_size(os.path.getsize(path))
            except (OSError, FileNotFoundError):
                size_str = ""
        
        # Pro playlisty nastavit cestu k výstupní složce
        if self._is_playlist and not path:
            playlist_title = info.get("title") or info.get("playlist_title") or "playlist"
            path = os.path.join(self.download_path, playlist_title)
        
        src, _   = detect_source(self.url_entry.get().strip(), self._("unknown_source"))

        append_history({
            "date":    datetime.datetime.now().strftime("%d.%m.%Y %H:%M"),
            "title":   info.get("title", "?"),
            "url":     info.get("webpage_url", self.url_entry.get().strip()),
            "source":  src,
            "type":    "mp3" if is_mp3 else "video",
            "quality": quality,
            "size":    size_str,
            "path":    path,
        })
        self.after(0, self._refresh_history_ui)

    def _re_enable_btns(self):
        self.download_video_btn.configure(state="normal")
        self.download_mp3_btn.configure(state="normal")

    def _clear_details(self):
        self.pct_label.configure(text="")
        self.speed_label.configure(text="")
        self.eta_label.configure(text="")
        self.size_label.configure(text="")

    # ── Indeterminate bar ──────────────────────────────────────────
    def _start_indeterminate(self):
        if self._indeterminate: return
        self._indeterminate = True; self._ind_val = 0.0; self._ind_dir = 1
        self._animate_ind()

    def _stop_indeterminate(self):
        self._indeterminate = False

    def _animate_ind(self):
        if not self._indeterminate: return
        self._ind_val += self._ind_dir * 0.03
        if   self._ind_val >= 1.0: self._ind_val = 1.0; self._ind_dir = -1
        elif self._ind_val <= 0.0: self._ind_val = 0.0; self._ind_dir =  1
        self.progress_bar.set(self._ind_val)
        self.after(30, self._animate_ind)

    def _set_phase(self, msg, color="gray"):
        c = {"gray":"gray","red":"#e94560","green":"#4ade80","cyan":"#67e8f9","yellow":"#fde68a"}
        self.phase_label.configure(text=msg, text_color=c.get(color, color))


# ══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    cfg = load_config()

    # First run: ask for language
    if "language" not in cfg:
        chosen_lang = pick_language()
        cfg["language"] = chosen_lang
        save_config(cfg)
    else:
        chosen_lang = cfg.get("language", "cs")

    app = DownloaderApp(lang=chosen_lang)
    app.mainloop()
