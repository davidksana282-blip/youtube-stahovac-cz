#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube Downloader
Vyžaduje: pip install yt-dlp customtkinter
"""

# ── Skryj konzoli na Windows ───────────────────────────────────────────────────
import sys, os

if sys.platform == "win32":
    import ctypes
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

# ── Cesta k adresáři skriptu (pro config + historii) ──────────────────────────
APP_DIR      = os.path.dirname(os.path.abspath(sys.argv[0]))
CONFIG_FILE  = os.path.join(APP_DIR, "yt_downloader_config.json")
HISTORY_FILE = os.path.join(APP_DIR, "yt_downloader_history.json")

# ── Auto-instalace závislostí ──────────────────────────────────────────────────
import subprocess, importlib

def _ensure(pkg, import_as=None):
    try:
        importlib.import_module(import_as or pkg)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg,
                               "--break-system-packages", "-q"])

_ensure("yt_dlp", "yt_dlp")
_ensure("customtkinter")

import json, shutil, threading, datetime
from pathlib import Path

import customtkinter as ctk
import yt_dlp

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

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
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def load_history():
    try:
        with open(HISTORY_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_history(history):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history[-200:], f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def append_history(entry: dict):
    h = load_history()
    h.append(entry)
    save_history(h)

# ══════════════════════════════════════════════════════════════════
#  Hlavní okno
# ══════════════════════════════════════════════════════════════════

class YTDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("YouTube Downloader")
        self.geometry("820x900")
        self.resizable(True, True)
        self.minsize(660, 780)

        self._cfg          = load_config()
        self.download_path = self._cfg.get("download_path", str(Path.home() / "Downloads"))
        self.formats       = []
        self.current_info  = None
        self._indeterminate = False
        self._ffmpeg_ok    = detect_ffmpeg()
        self._downloaded_path = None
        self._download_is_mp3 = False

        self._build_ui()
        self._check_ffmpeg_banner()

    # ──────────────────────────── UI ──────────────────────────────

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="#1a1a2e", corner_radius=0)
        header.pack(fill="x")
        ctk.CTkLabel(
            header, text="  YouTube Downloader",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color="#e94560",
        ).pack(side="left", padx=20, pady=14)

        # ffmpeg banner
        self.ffmpeg_banner = ctk.CTkFrame(self, fg_color="#3b1a00", corner_radius=0)
        self.ffmpeg_banner_label = ctk.CTkLabel(
            self.ffmpeg_banner,
            text="  ffmpeg neni nalezen  mergovani videa a MP3 nebude fungovat.",
            font=ctk.CTkFont(size=12), text_color="#fde68a", anchor="w",
        )
        self.ffmpeg_banner_label.pack(side="left", padx=14, pady=8, fill="x", expand=True)
        self.ffmpeg_dl_btn = ctk.CTkButton(
            self.ffmpeg_banner, text="Stahnout ffmpeg",
            width=160, height=30,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#e94560", hover_color="#c73652",
            command=self._download_ffmpeg,
        )
        self.ffmpeg_dl_btn.pack(side="right", padx=10, pady=6)

        # URL
        url_frame = ctk.CTkFrame(self, fg_color="transparent")
        url_frame.pack(fill="x", padx=20, pady=(14, 0))
        ctk.CTkLabel(url_frame, text="URL videa:", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w")
        input_row = ctk.CTkFrame(url_frame, fg_color="transparent")
        input_row.pack(fill="x", pady=(4, 0))
        self.url_entry = ctk.CTkEntry(
            input_row, placeholder_text="https://www.youtube.com/watch?v=...",
            height=42, font=ctk.CTkFont(size=13),
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.url_entry.bind("<Return>", lambda e: self.fetch_formats())
        self.fetch_btn = ctk.CTkButton(
            input_row, text="Nacist", width=110, height=42,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#e94560", hover_color="#c73652",
            command=self.fetch_formats,
        )
        self.fetch_btn.pack(side="left")

        # Složka
        folder_frame = ctk.CTkFrame(self, fg_color="transparent")
        folder_frame.pack(fill="x", padx=20, pady=(10, 0))
        ctk.CTkLabel(folder_frame, text="Cilova slozka:", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w")
        folder_row = ctk.CTkFrame(folder_frame, fg_color="transparent")
        folder_row.pack(fill="x", pady=(4, 0))
        self.folder_label = ctk.CTkLabel(
            folder_row, text=self.download_path,
            font=ctk.CTkFont(size=12), text_color="gray", anchor="w",
        )
        self.folder_label.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(
            folder_row, text="Zmenit", width=100, height=32,
            font=ctk.CTkFont(size=12), command=self.choose_folder,
        ).pack(side="left", padx=(8, 0))

        # Info o videu
        self.info_frame = ctk.CTkFrame(self, fg_color="#16213e", corner_radius=10)
        self.info_frame.pack(fill="x", padx=20, pady=(12, 0))
        self.video_title_label = ctk.CTkLabel(
            self.info_frame, text="Zadejte URL a kliknete na Nacist",
            font=ctk.CTkFont(size=13), text_color="gray",
            wraplength=740, justify="left",
        )
        self.video_title_label.pack(anchor="w", padx=14, pady=10)

        # Záložky
        self.tab_view = ctk.CTkTabview(self, height=210)
        self.tab_view.pack(fill="both", expand=True, padx=20, pady=(10, 0))
        self.tab_video   = self.tab_view.add("Video")
        self.tab_mp3     = self.tab_view.add("MP3 / Audio")
        self.tab_history = self.tab_view.add("Historie")

        # Video tab
        ctk.CTkLabel(self.tab_video, text="Dostupne kvality:", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", pady=(0, 6))
        self.format_var     = ctk.StringVar(value="")
        self.formats_scroll = ctk.CTkScrollableFrame(self.tab_video, height=140)
        self.formats_scroll.pack(fill="both", expand=True)
        ctk.CTkLabel(self.formats_scroll, text="Nejprve nactete video...", text_color="gray", font=ctk.CTkFont(size=12)).pack(pady=20)

        # MP3 tab
        mp3_inner = ctk.CTkFrame(self.tab_mp3, fg_color="transparent")
        mp3_inner.pack(fill="both", expand=True)
        ctk.CTkLabel(mp3_inner, text="Kvalita MP3:", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", pady=(4, 6))
        self.mp3_quality_var = ctk.StringVar(value=self._cfg.get("mp3_quality", "320"))
        q_row = ctk.CTkFrame(mp3_inner, fg_color="transparent")
        q_row.pack(anchor="w")
        for lbl, val in [("320 kbps (nejlepsi)", "320"), ("256 kbps", "256"), ("192 kbps", "192"), ("128 kbps", "128"), ("96 kbps", "96")]:
            ctk.CTkRadioButton(q_row, text=lbl, variable=self.mp3_quality_var, value=val,
                               font=ctk.CTkFont(size=13), command=self._save_config).pack(side="left", padx=(0, 14), pady=4)
        ctk.CTkLabel(mp3_inner, text="Pro MP3 je vyzadovan ffmpeg.", font=ctk.CTkFont(size=11), text_color="gray").pack(anchor="w", pady=(10, 0))

        # Historie tab
        self._build_history_tab()

        # Velká tlačítka
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(14, 0))
        btn_frame.grid_columnconfigure(0, weight=1)
        btn_frame.grid_columnconfigure(1, weight=1)

        self.download_video_btn = ctk.CTkButton(
            btn_frame, text="Stahnout video",
            height=56, font=ctk.CTkFont(size=17, weight="bold"),
            fg_color="#e94560", hover_color="#c73652", corner_radius=12,
            command=self.download_video, state="disabled",
        )
        self.download_video_btn.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.download_mp3_btn = ctk.CTkButton(
            btn_frame, text="Stahnout MP3",
            height=56, font=ctk.CTkFont(size=17, weight="bold"),
            fg_color="#1565c0", hover_color="#0d47a1", corner_radius=12,
            command=self.download_mp3, state="disabled",
        )
        self.download_mp3_btn.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        # Progress panel
        prog_outer = ctk.CTkFrame(self, fg_color="#16213e", corner_radius=12)
        prog_outer.pack(fill="x", padx=20, pady=(14, 16))

        top_row = ctk.CTkFrame(prog_outer, fg_color="transparent")
        top_row.pack(fill="x", padx=16, pady=(12, 4))
        self.phase_label = ctk.CTkLabel(
            top_row, text="Pripraveno",
            font=ctk.CTkFont(size=13, weight="bold"), text_color="gray", anchor="w",
        )
        self.phase_label.pack(side="left", fill="x", expand=True)
        self.pct_label = ctk.CTkLabel(
            top_row, text="", font=ctk.CTkFont(size=13, weight="bold"),
            text_color="gray", anchor="e", width=60,
        )
        self.pct_label.pack(side="right")

        self.progress_bar = ctk.CTkProgressBar(prog_outer, height=16, corner_radius=8)
        self.progress_bar.pack(fill="x", padx=16, pady=(0, 8))
        self.progress_bar.set(0)

        detail_row = ctk.CTkFrame(prog_outer, fg_color="transparent")
        detail_row.pack(fill="x", padx=16, pady=(0, 12))
        self.speed_label = ctk.CTkLabel(detail_row, text="", font=ctk.CTkFont(size=12), text_color="#67e8f9", anchor="w")
        self.speed_label.pack(side="left")
        self.eta_label = ctk.CTkLabel(detail_row, text="", font=ctk.CTkFont(size=12), text_color="#fde68a", anchor="center")
        self.eta_label.pack(side="left", padx=(20, 0))
        self.size_label = ctk.CTkLabel(detail_row, text="", font=ctk.CTkFont(size=12), text_color="gray", anchor="e")
        self.size_label.pack(side="right")

    def _build_history_tab(self):
        top = ctk.CTkFrame(self.tab_history, fg_color="transparent")
        top.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(top, text="Stazene soubory:", font=ctk.CTkFont(size=13, weight="bold")).pack(side="left", anchor="w")
        ctk.CTkButton(top, text="Vymazat historii", width=140, height=28,
                      font=ctk.CTkFont(size=12), fg_color="#3b3b3b", hover_color="#555",
                      command=self._clear_history).pack(side="right")
        self.history_scroll = ctk.CTkScrollableFrame(self.tab_history, height=140)
        self.history_scroll.pack(fill="both", expand=True)
        self._refresh_history_ui()

    def _refresh_history_ui(self):
        for w in self.history_scroll.winfo_children():
            w.destroy()
        history = load_history()
        if not history:
            ctk.CTkLabel(self.history_scroll, text="Zatim zadne stazene soubory.", text_color="gray",
                         font=ctk.CTkFont(size=12)).pack(pady=20)
            return
        for entry in reversed(history):
            row = ctk.CTkFrame(self.history_scroll, fg_color="#0f3460", corner_radius=8)
            row.pack(fill="x", pady=3, padx=4)
            icon    = "MP3" if entry.get("type") == "mp3" else "MP4"
            title   = entry.get("title", "Nezname")
            quality = entry.get("quality", "")
            size    = entry.get("size", "")
            ts      = entry.get("date", "")

            left = ctk.CTkFrame(row, fg_color="transparent")
            left.pack(side="left", fill="x", expand=True, padx=10, pady=6)
            ctk.CTkLabel(left, text=f"[{icon}]  {title}", font=ctk.CTkFont(size=12, weight="bold"),
                         anchor="w", wraplength=500).pack(anchor="w")
            meta = "  |  ".join(filter(None, [quality, size, ts]))
            ctk.CTkLabel(left, text=meta, font=ctk.CTkFont(size=11), text_color="gray", anchor="w").pack(anchor="w")

            dest = entry.get("path", "")
            if dest and os.path.exists(dest):
                ctk.CTkButton(row, text="Otevrit", width=70, height=32, font=ctk.CTkFont(size=12),
                              fg_color="#1565c0", hover_color="#0d47a1",
                              command=lambda p=dest: self._open_in_explorer(p)
                              ).pack(side="right", padx=8)

    def _clear_history(self):
        save_history([])
        self._refresh_history_ui()

    @staticmethod
    def _open_in_explorer(path):
        if sys.platform == "win32":
            subprocess.Popen(f'explorer /select,"{path}"')
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", path])
        else:
            subprocess.Popen(["xdg-open", os.path.dirname(path)])

    # ffmpeg banner
    def _check_ffmpeg_banner(self):
        if not self._ffmpeg_ok:
            self.ffmpeg_banner.pack(fill="x", after=self.winfo_children()[0])

    def _download_ffmpeg(self):
        if sys.platform == "win32":
            self._set_phase("Stahuji ffmpeg pres winget...", "yellow")
            self.ffmpeg_dl_btn.configure(state="disabled")
            threading.Thread(target=self._ffmpeg_install_thread, daemon=True).start()
        else:
            import webbrowser
            webbrowser.open("https://ffmpeg.org/download.html")

    def _ffmpeg_install_thread(self):
        try:
            subprocess.run(
                ["winget", "install", "--id", "Gyan.FFmpeg", "-e", "--silent"],
                check=True, capture_output=True
            )
            new_path = subprocess.check_output(
                ["powershell", "-Command",
                 "[System.Environment]::GetEnvironmentVariable('PATH','Machine')"],
                text=True
            ).strip()
            os.environ["PATH"] = new_path + os.pathsep + os.environ.get("PATH", "")
            self._ffmpeg_ok = detect_ffmpeg()
            if self._ffmpeg_ok:
                self.after(0, self.ffmpeg_banner.pack_forget)
                self.after(0, self._set_phase, "ffmpeg uspesne nainstalovan!", "green")
            else:
                self.after(0, self._set_phase, "ffmpeg nainstalovan - restart aplikace muze byt nutny.", "yellow")
                self.after(0, lambda: self.ffmpeg_dl_btn.configure(state="normal"))
        except Exception as e:
            self.after(0, self._set_phase, f"Instalace ffmpeg selhala: {e}", "red")
            self.after(0, lambda: self.ffmpeg_dl_btn.configure(state="normal"))

    # Config & složka
    def choose_folder(self):
        from tkinter import filedialog
        folder = filedialog.askdirectory(initialdir=self.download_path)
        if folder:
            self.download_path = folder
            self.folder_label.configure(text=folder)
            self._save_config()

    def _save_config(self):
        self._cfg["download_path"] = self.download_path
        self._cfg["mp3_quality"]   = self.mp3_quality_var.get()
        save_config(self._cfg)

    # Fetch formátů
    def fetch_formats(self):
        url = self.url_entry.get().strip()
        if not url:
            self._set_phase("Zadejte URL videa.", "red")
            return
        self.fetch_btn.configure(state="disabled", text="Nacitam...")
        self._set_phase("Nacitam informace o videu...", "gray")
        self._start_indeterminate()
        threading.Thread(target=self._fetch_thread, args=(url,), daemon=True).start()

    def _fetch_thread(self, url):
        try:
            with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
                info = ydl.extract_info(url, download=False)
                self.current_info = info
                self.after(0, self._populate_formats, info)
        except Exception as e:
            self.after(0, self._stop_indeterminate)
            self.after(0, self._set_phase, f"Chyba: {e}", "red")
            self.after(0, lambda: self.fetch_btn.configure(state="normal", text="Nacist"))

    def _populate_formats(self, info):
        self._stop_indeterminate()
        title    = info.get("title", "Nezname video")
        duration = info.get("duration", 0)
        mins, secs = divmod(int(duration), 60)
        self.video_title_label.configure(
            text=f"{title}  |  {mins}:{secs:02d}", text_color="white",
        )
        for w in self.formats_scroll.winfo_children():
            w.destroy()

        seen, video_formats = set(), []
        for f in info.get("formats", []):
            if f.get("vcodec", "none") == "none":
                continue
            res = f.get("height") or 0
            fps = f.get("fps") or 0
            ext = f.get("ext", "?")
            fid = f.get("format_id", "")
            key = (res, ext)
            if key in seen:
                continue
            seen.add(key)
            label  = f"{res}p" if res else "?"
            label += f"  {fps:.0f}fps" if fps else ""
            label += f"  [{ext}]"
            tbr = f.get("tbr")
            if tbr:
                label += f"  ~{tbr:.0f}kbps"
            video_formats.append((res, label, fid))

        video_formats.sort(key=lambda x: x[0], reverse=True)

        if not video_formats:
            ctk.CTkLabel(self.formats_scroll, text="Zadne formaty nenalezeny.", text_color="gray").pack(pady=20)
        else:
            self.format_var.set(video_formats[0][2])
            for _, label, fid in video_formats:
                ctk.CTkRadioButton(
                    self.formats_scroll, text=label,
                    variable=self.format_var, value=fid,
                    font=ctk.CTkFont(size=13),
                ).pack(anchor="w", pady=3, padx=8)

        self.formats = video_formats
        self.download_video_btn.configure(state="normal")
        self.download_mp3_btn.configure(state="normal")
        self.fetch_btn.configure(state="normal", text="Nacist")
        self._set_phase("Video nacteno. Vyberte kvalitu a stahnete.", "green")

    # Stahování
    def download_video(self):
        if not self.current_info:
            return
        fmt = self.format_var.get()
        if not fmt:
            self._set_phase("Vyberte kvalitu.", "red")
            return
        self._start_download(fmt, is_mp3=False)

    def download_mp3(self):
        if not self.current_info:
            return
        self._start_download(None, is_mp3=True)

    def _start_download(self, fmt, is_mp3):
        self.download_video_btn.configure(state="disabled")
        self.download_mp3_btn.configure(state="disabled")
        self.progress_bar.set(0)
        self._clear_details()
        self._downloaded_path = None
        self._download_is_mp3 = is_mp3
        url = self.url_entry.get().strip()
        threading.Thread(target=self._download_thread, args=(url, fmt, is_mp3), daemon=True).start()

    def _download_thread(self, url, fmt, is_mp3):
        try:
            outtmpl = os.path.join(self.download_path, "%(title)s.%(ext)s")
            if is_mp3:
                quality = self.mp3_quality_var.get()
                ydl_opts = {
                    "format": "bestaudio/best",
                    "outtmpl": outtmpl,
                    "postprocessors": [{"key": "FFmpegExtractAudio",
                                        "preferredcodec": "mp3",
                                        "preferredquality": quality}],
                    "progress_hooks": [self._progress_hook],
                }
                self.after(0, self._set_phase, f"Stahuji audio ({quality} kbps)...", "cyan")
            else:
                format_str = f"{fmt}[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
                ydl_opts = {
                    "format": format_str,
                    "outtmpl": outtmpl,
                    "merge_output_format": "mp4",
                    "progress_hooks": [self._progress_hook],
                }
                self.after(0, self._set_phase, "Stahuji video...", "cyan")

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info     = ydl.extract_info(url)
                filename = ydl.prepare_filename(info)
                if is_mp3:
                    filename = os.path.splitext(filename)[0] + ".mp3"
                else:
                    filename = os.path.splitext(filename)[0] + ".mp4"
                self._downloaded_path = filename

            self.after(0, self._download_done)
        except Exception as e:
            self.after(0, self._set_phase, f"Chyba: {e}", "red")
            self.after(0, self._re_enable_btns)

    def _progress_hook(self, d):
        status = d.get("status")
        if status == "downloading":
            total      = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes") or 0
            speed      = d.get("speed") or 0
            eta        = d.get("eta")

            if total > 0:
                pct = downloaded / total
                self.after(0, self.progress_bar.set, pct)
                self.after(0, self.pct_label.configure, {"text": f"{pct*100:.0f}%", "text_color": "#67e8f9"})
                self.after(0, self.size_label.configure, {"text": f"{_fmt_size(downloaded)} / {_fmt_size(total)}"})
            else:
                self.after(0, self._start_indeterminate)

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
            self.after(0, self._set_phase, "Spojuji video + audio (ffmpeg)...", "yellow")
            self.after(0, self.speed_label.configure, {"text": ""})
            self.after(0, self.eta_label.configure,   {"text": ""})

    def _download_done(self):
        self._stop_indeterminate()
        self.progress_bar.set(1.0)
        self.pct_label.configure(text="100%", text_color="#4ade80")
        self._set_phase(f"Hotovo!  Ulozeno do: {self.download_path}", "green")
        self._re_enable_btns()

        # Zápis do historie
        info    = self.current_info or {}
        is_mp3  = self._download_is_mp3
        quality = self.mp3_quality_var.get() + " kbps" if is_mp3 else \
                  next((lbl for res, lbl, fid in self.formats if fid == self.format_var.get()), "")
        path    = self._downloaded_path or ""
        size_str = _fmt_size(os.path.getsize(path)) if path and os.path.exists(path) else ""

        append_history({
            "date":    datetime.datetime.now().strftime("%d.%m.%Y %H:%M"),
            "title":   info.get("title", "Nezname"),
            "url":     info.get("webpage_url", self.url_entry.get().strip()),
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

    # Indeterminate animace
    def _start_indeterminate(self):
        if self._indeterminate:
            return
        self._indeterminate = True
        self._ind_val = 0.0
        self._ind_dir = 1
        self._animate_ind()

    def _stop_indeterminate(self):
        self._indeterminate = False

    def _animate_ind(self):
        if not self._indeterminate:
            return
        self._ind_val += self._ind_dir * 0.03
        if   self._ind_val >= 1.0: self._ind_val = 1.0; self._ind_dir = -1
        elif self._ind_val <= 0.0: self._ind_val = 0.0; self._ind_dir =  1
        self.progress_bar.set(self._ind_val)
        self.after(30, self._animate_ind)

    def _set_phase(self, msg, color="gray"):
        c = {"gray": "gray", "red": "#e94560", "green": "#4ade80",
             "cyan": "#67e8f9", "yellow": "#fde68a"}
        self.phase_label.configure(text=msg, text_color=c.get(color, color))


if __name__ == "__main__":
    app = YTDownloaderApp()
    app.mainloop()
