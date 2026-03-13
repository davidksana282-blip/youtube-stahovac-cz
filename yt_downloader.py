#!/usr/bin/env python3
"""
YouTube Downloader s GUI
Vyžaduje: pip install yt-dlp customtkinter
Pro MP3: ffmpeg musí být nainstalovaný v systému
"""

import customtkinter as ctk
import threading
import subprocess
import sys
import os
import json
from pathlib import Path

# Pokud customtkinter není dostupný, fallback na tkinter
try:
    import customtkinter as ctk
    USE_CTK = True
except ImportError:
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog
    USE_CTK = False

try:
    import yt_dlp
except ImportError:
    print("Instaluji yt-dlp...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp"])
    import yt_dlp


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class YTDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("🎬 YouTube Downloader")
        self.geometry("750x620")
        self.resizable(True, True)
        self.minsize(600, 500)

        self.download_path = str(Path.home() / "Downloads")
        self.formats = []
        self.current_info = None

        self._build_ui()

    def _build_ui(self):
        # ── Nadpis ──────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color="#1a1a2e", corner_radius=0)
        header.pack(fill="x")
        ctk.CTkLabel(
            header,
            text="  🎬 YouTube Downloader",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color="#e94560",
        ).pack(side="left", padx=20, pady=14)

        # ── URL vstup ────────────────────────────────────────────
        url_frame = ctk.CTkFrame(self, fg_color="transparent")
        url_frame.pack(fill="x", padx=20, pady=(16, 0))

        ctk.CTkLabel(url_frame, text="URL videa:", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w")

        input_row = ctk.CTkFrame(url_frame, fg_color="transparent")
        input_row.pack(fill="x", pady=(4, 0))

        self.url_entry = ctk.CTkEntry(
            input_row,
            placeholder_text="https://www.youtube.com/watch?v=...",
            height=42,
            font=ctk.CTkFont(size=13),
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.url_entry.bind("<Return>", lambda e: self.fetch_formats())

        self.fetch_btn = ctk.CTkButton(
            input_row,
            text="🔍 Načíst",
            width=110,
            height=42,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#e94560",
            hover_color="#c73652",
            command=self.fetch_formats,
        )
        self.fetch_btn.pack(side="left")

        # ── Výstupní složka ──────────────────────────────────────
        folder_frame = ctk.CTkFrame(self, fg_color="transparent")
        folder_frame.pack(fill="x", padx=20, pady=(10, 0))

        ctk.CTkLabel(folder_frame, text="Cílová složka:", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w")

        folder_row = ctk.CTkFrame(folder_frame, fg_color="transparent")
        folder_row.pack(fill="x", pady=(4, 0))

        self.folder_label = ctk.CTkLabel(
            folder_row,
            text=self.download_path,
            font=ctk.CTkFont(size=12),
            text_color="gray",
            anchor="w",
        )
        self.folder_label.pack(side="left", fill="x", expand=True)

        ctk.CTkButton(
            folder_row,
            text="📁 Změnit",
            width=100,
            height=32,
            font=ctk.CTkFont(size=12),
            command=self.choose_folder,
        ).pack(side="left", padx=(8, 0))

        # ── Info o videu ─────────────────────────────────────────
        self.info_frame = ctk.CTkFrame(self, fg_color="#16213e", corner_radius=10)
        self.info_frame.pack(fill="x", padx=20, pady=(12, 0))

        self.video_title_label = ctk.CTkLabel(
            self.info_frame,
            text="Zadejte URL a klikněte na Načíst",
            font=ctk.CTkFont(size=13),
            text_color="gray",
            wraplength=680,
            justify="left",
        )
        self.video_title_label.pack(anchor="w", padx=14, pady=10)

        # ── Záložky Video / MP3 ──────────────────────────────────
        self.tab_view = ctk.CTkTabview(self, height=200)
        self.tab_view.pack(fill="both", expand=True, padx=20, pady=(10, 0))

        self.tab_video = self.tab_view.add("🎬 Video")
        self.tab_mp3 = self.tab_view.add("🎵 MP3 / Audio")

        # Video tab
        ctk.CTkLabel(
            self.tab_video,
            text="Dostupné kvality:",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(anchor="w", pady=(0, 6))

        self.format_var = ctk.StringVar(value="")
        self.formats_scroll = ctk.CTkScrollableFrame(self.tab_video, height=130)
        self.formats_scroll.pack(fill="both", expand=True)

        self.no_formats_label = ctk.CTkLabel(
            self.formats_scroll,
            text="Nejprve načtěte video...",
            text_color="gray",
            font=ctk.CTkFont(size=12),
        )
        self.no_formats_label.pack(pady=20)

        # MP3 tab
        mp3_inner = ctk.CTkFrame(self.tab_mp3, fg_color="transparent")
        mp3_inner.pack(fill="both", expand=True)

        ctk.CTkLabel(
            mp3_inner,
            text="Kvalita MP3:",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(anchor="w", pady=(4, 6))

        self.mp3_quality_var = ctk.StringVar(value="320")
        mp3_qualities = [("320 kbps (nejlepší)", "320"), ("256 kbps", "256"), ("192 kbps", "192"), ("128 kbps", "128"), ("96 kbps (nejmenší)", "96")]

        q_row = ctk.CTkFrame(mp3_inner, fg_color="transparent")
        q_row.pack(anchor="w")
        for label, val in mp3_qualities:
            ctk.CTkRadioButton(
                q_row,
                text=label,
                variable=self.mp3_quality_var,
                value=val,
                font=ctk.CTkFont(size=13),
            ).pack(side="left", padx=(0, 16), pady=4)

        ctk.CTkLabel(
            mp3_inner,
            text="ℹ️  Pro konverzi do MP3 je vyžadován ffmpeg nainstalovaný v systému.",
            font=ctk.CTkFont(size=11),
            text_color="gray",
        ).pack(anchor="w", pady=(8, 0))

        # ── Tlačítka stažení ─────────────────────────────────────
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(10, 0))

        self.download_video_btn = ctk.CTkButton(
            btn_frame,
            text="⬇️  Stáhnout video",
            height=44,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#e94560",
            hover_color="#c73652",
            command=self.download_video,
            state="disabled",
        )
        self.download_video_btn.pack(side="left", expand=True, fill="x", padx=(0, 6))

        self.download_mp3_btn = ctk.CTkButton(
            btn_frame,
            text="🎵 Stáhnout MP3",
            height=44,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#0f3460",
            hover_color="#16213e",
            command=self.download_mp3,
            state="disabled",
        )
        self.download_mp3_btn.pack(side="left", expand=True, fill="x", padx=(6, 0))

        # ── Progress ──────────────────────────────────────────────
        progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        progress_frame.pack(fill="x", padx=20, pady=(10, 16))

        self.progress_bar = ctk.CTkProgressBar(progress_frame, height=14)
        self.progress_bar.pack(fill="x")
        self.progress_bar.set(0)

        self.status_label = ctk.CTkLabel(
            progress_frame,
            text="Připraveno",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        self.status_label.pack(anchor="w", pady=(4, 0))

    # ── Logika ───────────────────────────────────────────────────

    def choose_folder(self):
        from tkinter import filedialog
        folder = filedialog.askdirectory(initialdir=self.download_path)
        if folder:
            self.download_path = folder
            self.folder_label.configure(text=folder)

    def fetch_formats(self):
        url = self.url_entry.get().strip()
        if not url:
            self._set_status("❌ Zadejte URL videa.", "red")
            return
        self.fetch_btn.configure(state="disabled", text="⏳ Načítám...")
        self._set_status("Načítám informace o videu...", "gray")
        self.progress_bar.set(0)
        threading.Thread(target=self._fetch_thread, args=(url,), daemon=True).start()

    def _fetch_thread(self, url):
        try:
            ydl_opts = {"quiet": True, "no_warnings": True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                self.current_info = info
                self.after(0, self._populate_formats, info)
        except Exception as e:
            self.after(0, self._set_status, f"❌ Chyba: {e}", "red")
            self.after(0, lambda: self.fetch_btn.configure(state="normal", text="🔍 Načíst"))

    def _populate_formats(self, info):
        # Titulek
        title = info.get("title", "Neznámé video")
        duration = info.get("duration", 0)
        mins, secs = divmod(int(duration), 60)
        self.video_title_label.configure(
            text=f"📹  {title}  |  ⏱ {mins}:{secs:02d}",
            text_color="white",
        )

        # Vyčisti staré radio buttony
        for widget in self.formats_scroll.winfo_children():
            widget.destroy()

        # Sbírej unikátní video formáty
        seen = set()
        video_formats = []
        for f in info.get("formats", []):
            vcodec = f.get("vcodec", "none")
            acodec = f.get("acodec", "none")
            if vcodec == "none":
                continue
            res = f.get("height") or 0
            fps = f.get("fps") or 0
            ext = f.get("ext", "?")
            fid = f.get("format_id", "")
            key = (res, ext)
            if key in seen:
                continue
            seen.add(key)
            has_audio = acodec != "none"
            label = f"{res}p" if res else "?"
            label += f"  {fps:.0f}fps" if fps else ""
            label += f"  [{ext}]"
            video_formats.append((res, label, fid, has_audio))

        # Seřaď od nejvyšší kvality
        video_formats.sort(key=lambda x: x[0], reverse=True)

        if not video_formats:
            ctk.CTkLabel(self.formats_scroll, text="Žádné video formáty nenalezeny.", text_color="gray").pack(pady=20)
        else:
            self.format_var.set(video_formats[0][2])  # default = nejlepší
            for _, label, fid, _ in video_formats:
                ctk.CTkRadioButton(
                    self.formats_scroll,
                    text=label,
                    variable=self.format_var,
                    value=fid,
                    font=ctk.CTkFont(size=13),
                ).pack(anchor="w", pady=3, padx=8)

        self.formats = video_formats
        self.download_video_btn.configure(state="normal")
        self.download_mp3_btn.configure(state="normal")
        self.fetch_btn.configure(state="normal", text="🔍 Načíst")
        self._set_status("✅ Video načteno. Vyberte kvalitu a stáhněte.", "green")

    def download_video(self):
        if not self.current_info:
            return
        fmt = self.format_var.get()
        if not fmt:
            self._set_status("❌ Vyberte kvalitu.", "red")
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
        url = self.url_entry.get().strip()
        threading.Thread(target=self._download_thread, args=(url, fmt, is_mp3), daemon=True).start()

    def _download_thread(self, url, fmt, is_mp3):
        try:
            if is_mp3:
                quality = self.mp3_quality_var.get()
                ydl_opts = {
                    "format": "bestaudio/best",
                    "outtmpl": os.path.join(self.download_path, "%(title)s.%(ext)s"),
                    "postprocessors": [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": quality,
                    }],
                    "progress_hooks": [self._progress_hook],
                }
                self.after(0, self._set_status, f"🎵 Stahuji MP3 ({quality} kbps)...", "cyan")
            else:
                # Stejny format jako: -f "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
                format_str = f"{fmt}[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
                ydl_opts = {
                    "format": format_str,
                    "outtmpl": os.path.join(self.download_path, "%(title)s.%(ext)s"),
                    "merge_output_format": "mp4",
                    "progress_hooks": [self._progress_hook],
                }
                self.after(0, self._set_status, "⬇️  Stahuji video se zvukem (m4a)...", "cyan")

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            self.after(0, self._download_done)
        except Exception as e:
            self.after(0, self._set_status, f"❌ Chyba při stahování: {e}", "red")
            self.after(0, self._re_enable_btns)

    def _progress_hook(self, d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
            downloaded = d.get("downloaded_bytes", 0)
            speed = d.get("speed", 0) or 0
            eta = d.get("eta", 0) or 0
            if total > 0:
                pct = downloaded / total
                self.after(0, self.progress_bar.set, pct)
            speed_str = f"{speed/1024/1024:.1f} MB/s" if speed > 0 else ""
            eta_str = f"ETA {eta}s" if eta > 0 else ""
            msg = f"⬇️  Stahuji...  {speed_str}  {eta_str}"
            self.after(0, self._set_status, msg, "cyan")
        elif d["status"] == "finished":
            self.after(0, self.progress_bar.set, 0.99)
            self.after(0, self._set_status, "⚙️  Zpracovávám soubor...", "yellow")

    def _download_done(self):
        self.progress_bar.set(1.0)
        self._set_status(f"✅ Hotovo! Uloženo do: {self.download_path}", "green")
        self._re_enable_btns()

    def _re_enable_btns(self):
        self.download_video_btn.configure(state="normal")
        self.download_mp3_btn.configure(state="normal")

    def _set_status(self, msg, color="gray"):
        colors = {"gray": "gray", "red": "#e94560", "green": "#4ade80", "cyan": "#67e8f9", "yellow": "#fde68a"}
        self.status_label.configure(text=msg, text_color=colors.get(color, color))


if __name__ == "__main__":
    app = YTDownloaderApp()
    app.mainloop()
