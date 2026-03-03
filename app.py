"""
3K Sunoty - Suno Remix & Automation Tool
Modern Dark UI with CustomTkinter (matching 3K-Orchestrator)
"""
import customtkinter as ctk
from tkinter import filedialog, messagebox
import tkinter as tk
from tkinter import ttk
import subprocess
import os
import sys
import threading
import logging
import queue
import time
import json
from selenium_suno import SunoBrowserAutomation
import warnings
warnings.filterwarnings("ignore", category=FutureWarning, module="google.api_core")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Colors (matching 3K-Orchestrator)
COLORS = {
    'bg_dark': '#0f0f0f',
    'bg_card': '#1a1a1a',
    'bg_hover': '#252525',
    'bg_input': '#1e1e1e',
    'accent': '#6366f1',
    'accent_hover': '#818cf8',
    'success': '#22c55e',
    'warning': '#f59e0b',
    'error': '#ef4444',
    'text': '#ffffff',
    'text_dim': '#9ca3af',
    'border': '#2d2d2d',
    'purple': '#9C27B0',
    'blue': '#3b82f6',
    'orange': '#f97316',
}


class LogPanel(ctk.CTkFrame):
    """Shared log output panel"""
    def __init__(self, parent):
        super().__init__(parent, fg_color=COLORS['bg_card'], corner_radius=12)
        
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=(10, 5))
        
        ctk.CTkLabel(header, text="📋 Process Output", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
        ctk.CTkButton(header, text="Clear", width=60, height=28, fg_color=COLORS['bg_hover'],
                       hover_color=COLORS['border'], command=self.clear).pack(side="right")
        
        self.log_text = ctk.CTkTextbox(self, font=ctk.CTkFont(family="Consolas", size=12),
                                        fg_color=COLORS['bg_dark'], text_color="#00ff00",
                                        corner_radius=8, height=200)
        self.log_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))
    
    def log(self, message):
        self.log_text.insert("end", message)
        self.log_text.see("end")
    
    def clear(self):
        self.log_text.delete("1.0", "end")


class SunoApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("🎵 3K Sunoty")
        self.geometry("1100x850")
        self.configure(fg_color=COLORS['bg_dark'])
        
        self.user_data_dir = os.path.join(os.getcwd(), "chrome_profile")
        self.msg_queue = queue.Queue()
        self.presets = {}
        self.batch_queue = []
        self.batch_cp_queue = []
        self.stop_flag = False
        
        self._build_ui()
        self.load_settings()
        self.check_queue()
    
    def check_queue(self):
        try:
            while True:
                msg = self.msg_queue.get_nowait()
                self.log_panel.log(msg)
        except queue.Empty:
            pass
        self.after(100, self.check_queue)
    
    def append_output(self, text):
        self.msg_queue.put(text)
    
    # ======= BUILD UI =======
    def _build_ui(self):
        # Header
        self._build_header()
        
        # Main content
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=20, pady=(10, 20))
        
        # Tabs
        self.tabview = ctk.CTkTabview(main, fg_color=COLORS['bg_card'], 
                                       segmented_button_fg_color=COLORS['bg_hover'],
                                       segmented_button_selected_color=COLORS['accent'],
                                       segmented_button_selected_hover_color=COLORS['accent_hover'],
                                       segmented_button_unselected_color=COLORS['bg_hover'],
                                       segmented_button_unselected_hover_color=COLORS['border'],
                                       corner_radius=12)
        self.tabview.pack(fill="both", expand=True, pady=(0, 10))
        
        # Add tabs
        self.tab_remix = self.tabview.add("🎵 Single Remix")
        self.tab_batch = self.tabview.add("📋 Batch Remix")
        self.tab_download = self.tabview.add("📥 Download")
        self.tab_batch_cp = self.tabview.add("© Copyright Check")
        
        self.setup_remix_tab()
        self.setup_batch_tab()
        self.setup_download_tab()
        self.setup_batch_copyright_tab()
        
        # Log panel at bottom
        self.log_panel = LogPanel(main)
        self.log_panel.pack(fill="both", expand=True)
    
    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent", height=60)
        header.pack(fill="x", padx=20, pady=(15, 5))
        header.pack_propagate(False)
        
        ctk.CTkLabel(header, text="🎵 3K Sunoty", font=ctk.CTkFont(size=24, weight="bold"),
                      text_color=COLORS['text']).pack(side="left")
        
        self.status_badge = ctk.CTkLabel(header, text="● Ready", font=ctk.CTkFont(size=13),
                                          text_color=COLORS['success'], fg_color=COLORS['bg_card'],
                                          corner_radius=8, padx=12, pady=4)
        self.status_badge.pack(side="left", padx=(20, 0))
        
        # Login button  
        ctk.CTkButton(header, text="🔑 Login Suno", width=120, height=36,
                       fg_color=COLORS['bg_card'], hover_color=COLORS['bg_hover'],
                       command=self.start_login_thread).pack(side="right")
    
    # ======= REMIX TAB =======
    def setup_remix_tab(self):
        frame = self.tab_remix
        
        # Card for inputs
        card = ctk.CTkFrame(frame, fg_color=COLORS['bg_card'], corner_radius=12)
        card.pack(fill="x", padx=10, pady=10)
        
        # Song Path
        row1 = ctk.CTkFrame(card, fg_color="transparent")
        row1.pack(fill="x", padx=15, pady=(15, 5))
        ctk.CTkLabel(row1, text="Song Path (MP3):", width=160, anchor="w").pack(side="left")
        self.entry_song_path = ctk.CTkEntry(row1, placeholder_text="Select MP3 file...")
        self.entry_song_path.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(row1, text="Browse", width=80, fg_color=COLORS['bg_hover'],
                       hover_color=COLORS['border'], command=self.browse_file).pack(side="right")
        
        # Song Name
        row2 = ctk.CTkFrame(card, fg_color="transparent")
        row2.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(row2, text="Song Name:", width=160, anchor="w").pack(side="left")
        self.entry_song_name = ctk.CTkEntry(row2, placeholder_text="Enter song name...")
        self.entry_song_name.pack(side="left", fill="x", expand=True)
        
        # Channel ID
        row3 = ctk.CTkFrame(card, fg_color="transparent")
        row3.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(row3, text="YouTube Channel ID:", width=160, anchor="w").pack(side="left")
        self.entry_channel_id = ctk.CTkEntry(row3)
        self.entry_channel_id.pack(side="left", fill="x", expand=True)
        self.entry_channel_id.insert(0, "UCMee3KgPjZOl7f4gEmUni2Q")
        
        # Prompt
        row4 = ctk.CTkFrame(card, fg_color="transparent")
        row4.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(row4, text="Prompt / Style:", width=160, anchor="w",
                      font=ctk.CTkFont(weight="bold")).pack(side="left")
        self.entry_prompt = ctk.CTkEntry(row4, placeholder_text="Enter style description...")
        self.entry_prompt.pack(side="left", fill="x", expand=True)
        
        # Preset management
        preset_card = ctk.CTkFrame(card, fg_color=COLORS['bg_hover'], corner_radius=8)
        preset_card.pack(fill="x", padx=15, pady=(5, 15))
        
        preset_row = ctk.CTkFrame(preset_card, fg_color="transparent")
        preset_row.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(preset_row, text="Preset:", width=60).pack(side="left")
        self.preset_var = tk.StringVar()
        self.combo_presets = ctk.CTkComboBox(preset_row, variable=self.preset_var, width=200,
                                              command=self.load_preset_selection,
                                              fg_color=COLORS['bg_input'],
                                              border_color=COLORS['border'])
        self.combo_presets.pack(side="left", padx=5)
        
        ctk.CTkButton(preset_row, text="💾 Save", width=80, fg_color=COLORS['success'],
                       hover_color="#16a34a", command=self.save_preset_dialog).pack(side="left", padx=2)
        ctk.CTkButton(preset_row, text="❌ Delete", width=80, fg_color=COLORS['error'],
                       hover_color="#dc2626", command=self.delete_preset).pack(side="left", padx=2)
        ctk.CTkButton(preset_row, text="✏️ Manage", width=90, fg_color=COLORS['blue'],
                       hover_color="#2563eb", command=self.open_preset_manager).pack(side="left", padx=2)
        
        # Run button
        ctk.CTkButton(frame, text="🚀 RUN REMIX", height=45, font=ctk.CTkFont(size=14, weight="bold"),
                       fg_color=COLORS['accent'], hover_color=COLORS['accent_hover'],
                       command=lambda: self.run_remix(remix_only=True)).pack(fill="x", padx=10, pady=10)
    
    # ======= BATCH REMIX TAB =======
    def setup_batch_tab(self):
        frame = self.tab_batch
        
        # Add Song card
        add_card = ctk.CTkFrame(frame, fg_color=COLORS['bg_card'], corner_radius=12)
        add_card.pack(fill="x", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(add_card, text="➕ Add Song to Queue", font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", padx=15, pady=(10, 5))
        
        # Song Path
        r1 = ctk.CTkFrame(add_card, fg_color="transparent")
        r1.pack(fill="x", padx=15, pady=3)
        ctk.CTkLabel(r1, text="Path:", width=80, anchor="w").pack(side="left")
        self.batch_entry_path = ctk.CTkEntry(r1, placeholder_text="Select audio file...")
        self.batch_entry_path.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(r1, text="Browse", width=70, fg_color=COLORS['bg_hover'],
                       hover_color=COLORS['border'], command=self.batch_browse_file).pack(side="right")
        
        # Name + Prompt
        r2 = ctk.CTkFrame(add_card, fg_color="transparent")
        r2.pack(fill="x", padx=15, pady=3)
        ctk.CTkLabel(r2, text="Name:", width=80, anchor="w").pack(side="left")
        self.batch_entry_name = ctk.CTkEntry(r2, width=200, placeholder_text="Song name...")
        self.batch_entry_name.pack(side="left", padx=(0, 10))
        ctk.CTkLabel(r2, text="Style:", width=50).pack(side="left")
        self.batch_entry_prompt = ctk.CTkEntry(r2, placeholder_text="Prompt/Style...")
        self.batch_entry_prompt.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        # Preset + Add button
        r3 = ctk.CTkFrame(add_card, fg_color="transparent")
        r3.pack(fill="x", padx=15, pady=(3, 10))
        ctk.CTkLabel(r3, text="Preset:", width=80, anchor="w").pack(side="left")
        self.batch_preset_var = tk.StringVar()
        self.batch_combo_presets = ctk.CTkComboBox(r3, variable=self.batch_preset_var, width=200,
                                                     command=self.batch_load_preset,
                                                     fg_color=COLORS['bg_input'],
                                                     border_color=COLORS['border'])
        self.batch_combo_presets.pack(side="left", padx=(0, 10))
        ctk.CTkButton(r3, text="➕ Add to Queue", width=130, fg_color=COLORS['success'],
                       hover_color="#16a34a", command=self.batch_add_song).pack(side="right")
        
        # Queue table (using ttk Treeview with dark styling)
        queue_frame = ctk.CTkFrame(frame, fg_color=COLORS['bg_card'], corner_radius=12)
        queue_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.queue_label = ctk.CTkLabel(queue_frame, text="📋 Song Queue (0/20)",
                                         font=ctk.CTkFont(size=13, weight="bold"))
        self.queue_label.pack(anchor="w", padx=15, pady=(10, 5))
        
        # Style the treeview dark
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Dark.Treeview", background=COLORS['bg_dark'], foreground=COLORS['text'],
                        fieldbackground=COLORS['bg_dark'], borderwidth=0, rowheight=28,
                        font=('Segoe UI', 10))
        style.configure("Dark.Treeview.Heading", background=COLORS['bg_hover'], foreground=COLORS['text'],
                        font=('Segoe UI', 10, 'bold'), borderwidth=0)
        style.map("Dark.Treeview", background=[("selected", COLORS['accent'])])
        
        tree_frame = ctk.CTkFrame(queue_frame, fg_color="transparent")
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        columns = ("Name", "Prompt", "Path")
        self.batch_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=6, style="Dark.Treeview")
        self.batch_tree.heading("Name", text="Song Name")
        self.batch_tree.heading("Prompt", text="Prompt/Style")
        self.batch_tree.heading("Path", text="File Path")
        self.batch_tree.column("Name", width=180)
        self.batch_tree.column("Prompt", width=200)
        self.batch_tree.column("Path", width=250)
        self.batch_tree.pack(side="left", fill="both", expand=True)
        
        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.batch_tree.yview)
        sb.pack(side="right", fill="y")
        self.batch_tree.configure(yscrollcommand=sb.set)
        
        # Controls
        ctrl = ctk.CTkFrame(frame, fg_color="transparent")
        ctrl.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkButton(ctrl, text="❌ Remove", width=100, fg_color=COLORS['error'],
                       hover_color="#dc2626", command=self.batch_remove_song).pack(side="left", padx=2)
        ctk.CTkButton(ctrl, text="🗑️ Clear", width=80, fg_color=COLORS['orange'],
                       hover_color="#ea580c", command=self.batch_clear_queue).pack(side="left", padx=2)
        
        ctk.CTkLabel(ctrl, text="Wait (min):").pack(side="left", padx=(20, 5))
        self.batch_wait_var = tk.StringVar(value="10")
        ctk.CTkEntry(ctrl, textvariable=self.batch_wait_var, width=50).pack(side="left")
        
        ctk.CTkButton(ctrl, text="🚀 START BATCH CREATE & DOWNLOAD", height=40,
                       font=ctk.CTkFont(size=13, weight="bold"),
                       fg_color=COLORS['purple'], hover_color="#7B1FA2",
                       command=self.run_batch_remix).pack(side="right", padx=5)
    
    # ======= DOWNLOAD TAB =======
    def setup_download_tab(self):
        frame = self.tab_download
        
        card = ctk.CTkFrame(frame, fg_color=COLORS['bg_card'], corner_radius=12)
        card.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(card, text="📥 Download Cover Songs from Suno",
                      font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=15, pady=(15, 5))
        
        info_text = "• Mỗi bài input tạo ra 2 cover outputs\n• Mỗi output = 1 MP3 + 1 Video\n• Ví dụ: 4 bài input → 8 outputs → 16 files"
        ctk.CTkLabel(card, text=info_text, text_color=COLORS['text_dim'],
                      justify="left").pack(anchor="w", padx=15, pady=(0, 10))
        
        # Input count
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=15, pady=(0, 15))
        ctk.CTkLabel(row, text="Số bài INPUT đã tạo:", font=ctk.CTkFont(weight="bold")).pack(side="left")
        self.download_input_count = tk.StringVar(value="4")
        ctk.CTkEntry(row, textvariable=self.download_input_count, width=60,
                      font=ctk.CTkFont(size=14)).pack(side="left", padx=10)
        self.download_output_label = ctk.CTkLabel(row, text="→ 8 outputs (16 files)",
                                                    text_color=COLORS['blue'])
        self.download_output_label.pack(side="left")
        self.download_input_count.trace_add("write", self._update_download_calc)
        
        # Buttons
        btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkButton(btn_row, text="🚀 START DOWNLOAD", height=50,
                       font=ctk.CTkFont(size=14, weight="bold"),
                       fg_color=COLORS['success'], hover_color="#16a34a",
                       command=self.run_download_only).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(btn_row, text="⛔ STOP", height=50, width=100,
                       font=ctk.CTkFont(size=14, weight="bold"),
                       fg_color=COLORS['error'], hover_color="#dc2626",
                       command=self.stop_process).pack(side="right")
    
    def _update_download_calc(self, *args):
        try:
            n = int(self.download_input_count.get())
            out = n * 2
            self.download_output_label.configure(text=f"→ {out} outputs ({out * 2} files)")
        except:
            self.download_output_label.configure(text="→ Invalid")
    
    # ======= BATCH COPYRIGHT CHECK TAB =======
    def setup_batch_copyright_tab(self):
        frame = self.tab_batch_cp
        
        # Toolbar
        toolbar = ctk.CTkFrame(frame, fg_color=COLORS['bg_card'], corner_radius=12)
        toolbar.pack(fill="x", padx=10, pady=(10, 5))
        
        row1 = ctk.CTkFrame(toolbar, fg_color="transparent")
        row1.pack(fill="x", padx=15, pady=10)
        
        ctk.CTkButton(row1, text="📂 Add Files", width=110, fg_color=COLORS['blue'],
                       hover_color="#2563eb", command=self.batch_cp_add_files).pack(side="left", padx=2)
        ctk.CTkButton(row1, text="❌ Remove", width=90, fg_color=COLORS['error'],
                       hover_color="#dc2626", command=self.batch_cp_remove).pack(side="left", padx=2)
        
        # API Profile
        ctk.CTkLabel(row1, text="│  API:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(15, 5))
        self.api_profile_var = tk.StringVar(value="default")
        self.api_profile_combo = ctk.CTkComboBox(row1, variable=self.api_profile_var, width=130,
                                                   fg_color=COLORS['bg_input'],
                                                   border_color=COLORS['border'])
        self.api_profile_combo.pack(side="left", padx=2)
        ctk.CTkButton(row1, text="➕", width=35, fg_color=COLORS['success'],
                       hover_color="#16a34a", command=self.add_api_account).pack(side="left", padx=2)
        ctk.CTkButton(row1, text="🔑", width=35, fg_color=COLORS['warning'],
                       hover_color="#d97706", command=self.verify_api_account).pack(side="left", padx=2)
        
        # Right side options
        ctk.CTkButton(row1, text="🔍 Check Recent", width=130, fg_color=COLORS['purple'],
                       hover_color="#7B1FA2", command=self.run_batch_scan_recent).pack(side="right", padx=5)
        
        self.batch_cp_auto_delete = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(row1, text="Auto-delete", variable=self.batch_cp_auto_delete,
                          fg_color=COLORS['accent']).pack(side="right", padx=5)
        
        # Channel ID
        row2 = ctk.CTkFrame(toolbar, fg_color="transparent")
        row2.pack(fill="x", padx=15, pady=(0, 10))
        ctk.CTkLabel(row2, text="Channel ID:").pack(side="left")
        self.batch_cp_channel_entry = ctk.CTkEntry(row2, width=250)
        self.batch_cp_channel_entry.pack(side="left", padx=5)
        self.batch_cp_channel_entry.insert(0, "UCMee3KgPjZOl7f4gEmUni2Q")
        
        self.refresh_api_profiles()
        
        # Queue table
        queue_card = ctk.CTkFrame(frame, fg_color=COLORS['bg_card'], corner_radius=12)
        queue_card.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.cp_queue_label = ctk.CTkLabel(queue_card, text="📋 Check Queue (0 files)",
                                             font=ctk.CTkFont(size=13, weight="bold"))
        self.cp_queue_label.pack(anchor="w", padx=15, pady=(10, 5))
        
        tree_frame = ctk.CTkFrame(queue_card, fg_color="transparent")
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        columns = ("File", "Status", "Result")
        self.batch_cp_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=10, style="Dark.Treeview")
        self.batch_cp_tree.heading("File", text="File Name")
        self.batch_cp_tree.heading("Status", text="Status")
        self.batch_cp_tree.heading("Result", text="Detail/Risk")
        self.batch_cp_tree.column("File", width=300)
        self.batch_cp_tree.column("Status", width=150)
        self.batch_cp_tree.column("Result", width=300)
        self.batch_cp_tree.pack(side="left", fill="both", expand=True)
        
        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.batch_cp_tree.yview)
        sb.pack(side="right", fill="y")
        self.batch_cp_tree.configure(yscrollcommand=sb.set)
        
        # Context menu
        self.batch_cp_menu = tk.Menu(self.batch_cp_tree, tearoff=0)
        self.batch_cp_menu.add_command(label="▶️ Watch Video", command=self.batch_cp_open_video)
        self.batch_cp_menu.add_command(label="🛠️ Open in Studio", command=self.batch_cp_open_studio)
        self.batch_cp_menu.add_separator()
        self.batch_cp_menu.add_command(label="❌ Remove", command=self.batch_cp_remove)
        self.batch_cp_tree.bind("<Button-3>", self.show_batch_cp_menu)
        
        # Start button
        ctk.CTkButton(frame, text="🚀 START BATCH CHECK", height=45,
                       font=ctk.CTkFont(size=14, weight="bold"),
                       fg_color=COLORS['success'], hover_color="#16a34a",
                       command=self.run_batch_copyright_check).pack(fill="x", padx=10, pady=10)
    
    # ======= ACTIONS =======
    
    def browse_file(self):
        filename = filedialog.askopenfilename(filetypes=[("MP3 files", "*.mp3")])
        if filename:
            self.entry_song_path.delete(0, "end")
            self.entry_song_path.insert(0, filename)
    
    def batch_browse_file(self):
        filename = filedialog.askopenfilename(filetypes=[("Audio files", "*.mp3 *.wav")])
        if filename:
            self.batch_entry_path.delete(0, "end")
            self.batch_entry_path.insert(0, filename)
            basename = os.path.splitext(os.path.basename(filename))[0]
            if not self.batch_entry_name.get():
                self.batch_entry_name.insert(0, basename)
    
    def batch_add_song(self):
        path = self.batch_entry_path.get().strip()
        name = self.batch_entry_name.get().strip()
        prompt = self.batch_entry_prompt.get().strip()
        
        if not path:
            messagebox.showerror("Error", "Please select a song file")
            return
        if not name:
            messagebox.showerror("Error", "Please enter a song name")
            return
        if len(self.batch_queue) >= 20:
            messagebox.showwarning("Limit", "Maximum 20 songs per batch")
            return
        
        song = {"path": path, "name": name, "prompt": prompt or "Cover"}
        self.batch_queue.append(song)
        self.batch_tree.insert("", "end", values=(name, prompt or "Cover", path))
        
        self.batch_entry_path.delete(0, "end")
        self.batch_entry_name.delete(0, "end")
        self.batch_entry_prompt.delete(0, "end")
        self.queue_label.configure(text=f"📋 Song Queue ({len(self.batch_queue)}/20)")
    
    def batch_remove_song(self):
        selected = self.batch_tree.selection()
        if not selected: return
        for item in selected:
            idx = self.batch_tree.index(item)
            self.batch_tree.delete(item)
            if idx < len(self.batch_queue):
                self.batch_queue.pop(idx)
        self.queue_label.configure(text=f"📋 Song Queue ({len(self.batch_queue)}/20)")
    
    def batch_clear_queue(self):
        if self.batch_queue and messagebox.askyesno("Confirm", "Clear all songs?"):
            self.batch_queue = []
            for item in self.batch_tree.get_children():
                self.batch_tree.delete(item)
            self.queue_label.configure(text="📋 Song Queue (0/20)")
    
    def stop_process(self):
        if messagebox.askyesno("Confirm Stop", "Stop current process?"):
            self.stop_flag = True
            self.append_output("\n🛑 STOP signal sent...\n")
    
    # ======= COPYRIGHT CHECK ACTIONS =======
    
    def batch_cp_add_files(self):
        files = filedialog.askopenfilenames(filetypes=[("Video/Audio files", "*.mp4 *.mp3 *.wav *.avi *.mkv")])
        if files:
            for f in files:
                name = os.path.basename(f)
                if any(q['path'] == f for q in self.batch_cp_queue):
                    continue
                self.batch_cp_queue.append({'path': f, 'name': name, 'status': 'Pending'})
                self.batch_cp_tree.insert("", "end", values=(name, "Pending", "Waiting..."))
            self.cp_queue_label.configure(text=f"📋 Check Queue ({len(self.batch_cp_queue)} files)")
    
    def batch_cp_remove(self):
        selected = self.batch_cp_tree.selection()
        if not selected: return
        for item in selected:
            idx = self.batch_cp_tree.index(item)
            self.batch_cp_tree.delete(item)
            if idx < len(self.batch_cp_queue):
                self.batch_cp_queue.pop(idx)
        self.cp_queue_label.configure(text=f"📋 Check Queue ({len(self.batch_cp_queue)} files)")
    
    def show_batch_cp_menu(self, event):
        item = self.batch_cp_tree.identify_row(event.y)
        if item:
            self.batch_cp_tree.selection_set(item)
            self.batch_cp_menu.post(event.x_root, event.y_root)
    
    def get_selected_video_id(self):
        selected = self.batch_cp_tree.selection()
        if not selected: return None
        values = self.batch_cp_tree.item(selected[0])['values']
        detail = str(values[2])
        if "ID: " in detail:
            return detail.split("ID: ")[1].split()[0]
        return None
    
    def batch_cp_open_video(self):
        vid = self.get_selected_video_id()
        if vid:
            import webbrowser
            webbrowser.open(f"https://youtu.be/{vid}")
        else:
            messagebox.showinfo("Info", "No Video ID found.")
    
    def batch_cp_open_studio(self):
        vid = self.get_selected_video_id()
        import webbrowser
        if vid:
            webbrowser.open(f"https://studio.youtube.com/video/{vid}/copyright")
        else:
            webbrowser.open("https://studio.youtube.com")
    
    # ======= BATCH COPYRIGHT CHECK WORKER =======
    def run_batch_copyright_check(self):
        if not self.batch_cp_queue:
            messagebox.showwarning("Empty", "Please add files first!")
            return
        
        channel_id = self.batch_cp_channel_entry.get()
        if not channel_id:
            messagebox.showerror("Error", "Channel ID required")
            return
        
        auto_delete = self.batch_cp_auto_delete.get()
        profile_name = self.api_profile_var.get()
        
        self.log_panel.clear()
        self.append_output(f"=== BATCH COPYRIGHT CHECK ===\nFiles: {len(self.batch_cp_queue)} | Account: {profile_name}\n\n")
        
        def worker():
            import re
            import concurrent.futures
            
            # PHASE 1: UPLOAD ALL
            self.append_output("--- PHASE 1: UPLOADING ---\n")
            uploaded_items = []
            
            def upload_single(task_info):
                idx = task_info['index']
                item = task_info['item']
                
                try:
                    tree_item = self.batch_cp_tree.get_children()[idx]
                    self.batch_cp_tree.item(tree_item, values=(item['name'], "⬆️ Uploading...", "Processing"))
                except: pass
                
                self.append_output(f"⬆️ Uploading: {item['name']}...\n")
                
                try:
                    cmd = [
                        sys.executable, "scripts/3_copyright_check.py",
                        item['path'], "--channel-id", channel_id,
                        "--mode", "upload", "--profile", profile_name
                    ]
                    
                    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                                text=True, cwd=os.getcwd(), bufsize=1)
                    
                    video_id = None
                    full_output = ""
                    for line in process.stdout:
                        line = line.strip()
                        if line:
                            self.append_output(line + "\n")
                            full_output += line + "\n"
                            if "Video ID:" in line:
                                parts = line.split("Video ID:")
                                if len(parts) > 1:
                                    video_id = parts[1].strip()
                    
                    process.wait()
                    
                    if process.returncode == 0 and not video_id:
                        match = re.search(r"Video ID: ([a-zA-Z0-9_-]+)", full_output)
                        if match:
                            video_id = match.group(1)
                    
                    if video_id:
                        self.append_output(f"✅ Uploaded: {item['name']} → {video_id}\n")
                        try: self.batch_cp_tree.item(tree_item, values=(item['name'], "✅ Uploaded", f"ID: {video_id}"))
                        except: pass
                        return {'index': idx, 'item': item, 'video_id': video_id, 'name': item['name']}
                    else:
                        self.append_output(f"❌ Upload Failed: {item['name']}\n")
                        try: self.batch_cp_tree.item(tree_item, values=(item['name'], "❌ Error", "No ID"))
                        except: pass
                
                except Exception as e:
                    self.append_output(f"❌ Error: {item['name']} - {e}\n")
                    try: self.batch_cp_tree.item(tree_item, values=(item['name'], "❌ Error", str(e)[:50]))
                    except: pass
                
                return None
            
            tasks = [{'index': i, 'item': item} for i, item in enumerate(self.batch_cp_queue)]
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                futures = [executor.submit(upload_single, t) for t in tasks]
                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    if result:
                        uploaded_items.append(result)
            
            # PHASE 2: WAIT FOR PROCESSING + CHECK EACH VIDEO
            if not uploaded_items:
                self.append_output("\n⚠️ No videos uploaded. Stopping.\n")
                return
            
            self.append_output(f"\n--- PHASE 2: WAITING FOR YOUTUBE PROCESSING ---\n")
            self.append_output(f"⏳ YouTube needs ~5 minutes to process Content ID.\n")
            self.append_output(f"   Waiting 5 minutes before checking copyright...\n\n")
            
            # Wait 5 minutes with countdown
            wait_seconds = 300  # 5 minutes
            for remaining in range(wait_seconds, 0, -30):
                mins = remaining // 60
                secs = remaining % 60
                self.append_output(f"⏳ {mins}m {secs}s remaining...\n")
                time.sleep(30)
            
            self.append_output(f"\n--- PHASE 3: CHECKING EACH VIDEO's COPYRIGHT PAGE ---\n")
            
            try:
                # Import studio checker and check each video individually
                sys.path.insert(0, os.path.join(os.getcwd(), 'scripts'))
                from modules.youtube_studio_checker import YouTubeStudioChecker
                
                checker = YouTubeStudioChecker()
                
                for item in uploaded_items:
                    vid_id = item['video_id']
                    self.append_output(f"\n🔍 Checking: {item['name']} (ID: {vid_id})...\n")
                    
                    try:
                        tree_item = self.batch_cp_tree.get_children()[item['index']]
                        self.batch_cp_tree.item(tree_item, values=(item['name'], "🔍 Checking...", f"ID: {vid_id}"))
                    except: pass
                    
                    result = checker.check_copyright_by_video_id(vid_id, max_retries=3)
                    
                    has_cp = result.get('has_copyright', False)
                    restriction = result.get('restriction_text', 'Unknown')
                    
                    if has_cp:
                        status_text = "⚠️ COPYRIGHT"
                        msg = f"Claims Found - {restriction}"
                        self.append_output(f"⚠️ COPYRIGHT FOUND: {item['name']}\n")
                    else:
                        status_text = "✅ SAFE"
                        msg = "No issues"
                        self.append_output(f"✅ CLEAN: {item['name']}\n")
                    
                    try:
                        tree_item = self.batch_cp_tree.get_children()[item['index']]
                        self.batch_cp_tree.item(tree_item, values=(item['name'], status_text, msg))
                    except: pass
                    
                    time.sleep(2)  # Brief pause between checks
                
                checker.close()
                
            except Exception as e:
                self.append_output(f"❌ Check Error: {e}\n")
                import traceback
                self.append_output(traceback.format_exc() + "\n")
            
            self.append_output("\n=== BATCH COMPLETE ===\n")
            messagebox.showinfo("Done", "Batch Check Completed!")
        
        threading.Thread(target=worker, daemon=True).start()
    
    def run_batch_scan_recent(self):
        profile_name = self.api_profile_var.get()
        channel_id = self.batch_cp_channel_entry.get()
        
        self.log_panel.clear()
        self.append_output(f"=== CHECKING RECENT UPLOADS ===\nAccount: {profile_name}\n\n")
        
        def worker():
            try:
                sys.path.insert(0, os.path.join(os.getcwd(), 'scripts'))
                from modules.youtube_studio_checker import YouTubeStudioChecker
                
                checker = YouTubeStudioChecker()
                self.append_output("🔍 Scanning recent videos and checking each copyright page...\n")
                
                results = checker.check_recent_videos(limit=20)
                
                self.append_output(f"\n=== RESULTS ({len(results)} videos) ===\n")
                for i, res in enumerate(results):
                    title = res.get('video_title', 'Unknown')[:50]
                    has_cp = res.get('has_copyright', False)
                    
                    if has_cp:
                        self.append_output(f"❌ COPYRIGHT: [{i+1}] {title}\n")
                    else:
                        self.append_output(f"✅ CLEAN: [{i+1}] {title}\n")
                
                checker.close()
                self.append_output("\n=== SCAN COMPLETE ===\n")
            except Exception as e:
                self.append_output(f"\n❌ Error: {e}\n")
                import traceback
                self.append_output(traceback.format_exc() + "\n")
        
        threading.Thread(target=worker, daemon=True).start()
    
    # ======= SINGLE REMIX =======
    def run_remix(self, remix_only=False):
        song_path = self.entry_song_path.get()
        song_name = self.entry_song_name.get()
        channel_id = self.entry_channel_id.get()
        custom_prompt = self.entry_prompt.get()
        
        if not song_path or not song_name or not channel_id:
            messagebox.showerror("Error", "Please fill in all fields")
            return
        if not custom_prompt:
            messagebox.showerror("Error", "Please enter a Prompt/Style")
            return
        
        self.log_panel.clear()
        self.append_output(f"Starting remix...\nSong: {song_name}\nPrompt: {custom_prompt}\n\n")
        
        def worker():
            try:
                cmd = [sys.executable, "scripts/2_remix_with_suno_advanced.py",
                       song_path, "--song-name", song_name, "--channel-id", channel_id]
                if custom_prompt:
                    cmd.extend(["--prompt", custom_prompt])
                    self.save_settings()
                if remix_only:
                    cmd.append("--remix-only")
                
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                            text=True, cwd=os.getcwd())
                for line in iter(process.stdout.readline, ''):
                    self.append_output(line)
                process.stdout.close()
                process.wait()
                
                if process.returncode == 0:
                    self.append_output("\n✅ Process completed!\n")
                else:
                    self.append_output("\n❌ Process failed.\n")
            except Exception as e:
                self.append_output(f"\n❌ Error: {str(e)}\n")
        
        threading.Thread(target=worker).start()
    
    # ======= BATCH REMIX =======
    def run_batch_remix(self):
        if not self.batch_queue:
            messagebox.showerror("Error", "Queue is empty!")
            return
        
        try:
            wait_minutes = int(self.batch_wait_var.get())
        except:
            wait_minutes = 10
        
        self.log_panel.clear()
        self.append_output(f"=== BATCH REMIX ===\nSongs: {len(self.batch_queue)} | Wait: {wait_minutes}min\n\n")
        
        def batch_worker():
            browser = None
            try:
                self.append_output("🌐 Starting browser...\n")
                browser = SunoBrowserAutomation(user_data_dir=self.user_data_dir)
                
                self.append_output("🔗 Navigating to Suno.ai...\n")
                browser.navigate_to_suno()
                
                self.append_output("⏳ Waiting for login...\n")
                if not browser.wait_for_login(timeout=300):
                    self.append_output("❌ Login timeout!\n")
                    browser.close()
                    return
                
                self.append_output("✅ Login detected!\n\n=== PHASE 1: CREATING ===\n")
                created_count = 0
                failed_songs = []
                
                for i, song in enumerate(self.batch_queue):
                    self.append_output(f"\n[{i+1}/{len(self.batch_queue)}] Creating: {song['name']}\n")
                    try:
                        success = browser.create_song_only(
                            audio_path=song['path'], title=song['name'],
                            prompt=song['prompt'], log_callback=self.append_output)
                        if success:
                            created_count += 1
                            self.append_output(f"✅ DONE: {song['name']}\n")
                        else:
                            failed_songs.append(song['name'])
                            self.append_output(f"❌ FAILED: {song['name']}\n")
                    except Exception as e:
                        failed_songs.append(song['name'])
                        self.append_output(f"❌ Error: {str(e)[:100]}\n")
                        try: browser.driver.current_url
                        except:
                            self.append_output("⚠️ Browser lost! Recovering...\n")
                            try: browser.close()
                            except: pass
                            browser = SunoBrowserAutomation(user_data_dir=self.user_data_dir)
                            browser.navigate_to_suno()
                            time.sleep(5)
                
                self.append_output(f"\n=== Created: {created_count}/{len(self.batch_queue)} ===\n")
                if failed_songs:
                    self.append_output(f"⚠️ Failed: {', '.join(failed_songs)}\n")
                
                if created_count == 0:
                    self.append_output("\n❌ No songs created. Aborting.\n")
                    browser.close()
                    return
                
                # Phase 2: Wait
                self.append_output(f"\n=== PHASE 2: WAITING {wait_minutes}min ===\n")
                for remaining in range(wait_minutes * 60, 0, -30):
                    self.append_output(f"⏳ {remaining // 60}m {remaining % 60}s remaining...\n")
                    time.sleep(30)
                
                # Phase 3: Download
                self.append_output(f"\n=== PHASE 3: DOWNLOADING ===\n")
                downloaded = browser.batch_download(created_count, log_callback=self.append_output)
                self.append_output(f"\n✅ Downloads: {downloaded} songs\n")
                
                browser.close()
                self.append_output("\n=== BATCH COMPLETE ===\n")
                
            except Exception as e:
                self.append_output(f"\n❌ Error: {e}\n")
            finally:
                if browser:
                    try: browser.close()
                    except: pass
        
        threading.Thread(target=batch_worker, daemon=True).start()
    
    # ======= DOWNLOAD ONLY =======
    def run_download_only(self):
        try:
            num_input = int(self.download_input_count.get())
            if num_input <= 0:
                messagebox.showerror("Error", "Number must be > 0")
                return
        except:
            messagebox.showerror("Error", "Invalid number")
            return
        
        num_output = num_input * 2
        self.log_panel.clear()
        self.append_output(f"=== DOWNLOAD ONLY ===\nInputs: {num_input} → Outputs: {num_output}\n\n")
        self.stop_flag = False
        
        def download_worker():
            browser = None
            try:
                if self.stop_flag: return
                self.append_output("🌐 Starting browser...\n")
                browser = SunoBrowserAutomation(user_data_dir=self.user_data_dir)
                
                if self.stop_flag: browser.close(); return
                self.append_output("🔗 Navigating to Suno.ai...\n")
                browser.navigate_to_suno()
                
                self.append_output("⏳ Waiting for login...\n")
                if not browser.wait_for_login(timeout=300):
                    self.append_output("❌ Login timeout!\n")
                    browser.close()
                    return
                
                if self.stop_flag:
                    self.append_output("🛑 Stopped.\n")
                    browser.close()
                    return
                
                self.append_output(f"✅ Login! Downloading {num_output} songs...\n")
                downloaded = browser.batch_download(num_input, log_callback=self.append_output,
                                                     stop_check_callback=lambda: self.stop_flag)
                
                if self.stop_flag:
                    self.append_output(f"\n🛑 Stopped! Downloaded: {downloaded}/{num_output}\n")
                else:
                    self.append_output(f"\n✅ Complete: {downloaded}/{num_output} songs\n")
                
                browser.close()
                if not self.stop_flag:
                    messagebox.showinfo("Done", f"Downloaded {downloaded} songs!")
            except Exception as e:
                self.append_output(f"\n❌ Error: {e}\n")
            finally:
                if browser:
                    try: browser.close()
                    except: pass
        
        threading.Thread(target=download_worker, daemon=True).start()
    
    # ======= LOGIN =======
    def start_login_thread(self):
        self.status_badge.configure(text="● Logging in...", text_color=COLORS['warning'])
        threading.Thread(target=self.perform_login, daemon=True).start()
    
    def perform_login(self):
        automation = None
        try:
            automation = SunoBrowserAutomation(headless=False, user_data_dir=self.user_data_dir)
            automation.navigate_to_suno()
            
            self.append_output("⏳ Waiting for manual login in browser...\n")
            result = automation.wait_for_login(timeout=600)
            
            if result:
                cookie_str = automation.get_cookies_as_string()
                if cookie_str:
                    self.save_cookies_to_env(cookie_str)
                    self.after(0, lambda: self.status_badge.configure(text="● Logged In", text_color=COLORS['success']))
                    messagebox.showinfo("Success", "Login successful! Cookies saved.")
                else:
                    self.after(0, lambda: self.status_badge.configure(text="● Login OK (no cookies)", text_color=COLORS['warning']))
            else:
                self.after(0, lambda: self.status_badge.configure(text="● Login Timeout", text_color=COLORS['error']))
        except Exception as e:
            self.after(0, lambda: self.status_badge.configure(text="● Error", text_color=COLORS['error']))
            messagebox.showerror("Error", str(e))
        finally:
            if automation:
                automation.close()
    
    def save_cookies_to_env(self, cookie_str):
        env_path = ".env"
        new_lines = []
        cookie_found = False
        try:
            if os.path.exists(env_path):
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f.readlines():
                        if line.startswith("SUNO_COOKIE="):
                            new_lines.append(f'SUNO_COOKIE="{cookie_str}"\n')
                            cookie_found = True
                        else:
                            new_lines.append(line)
            if not cookie_found:
                new_lines.append(f'\nSUNO_COOKIE="{cookie_str}"\n')
            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
            self.append_output("✅ Cookies saved to .env\n")
        except Exception as e:
            self.append_output(f"❌ Failed to save cookies: {e}\n")
    
    # ======= API PROFILES =======
    def refresh_api_profiles(self):
        try:
            sys.path.append(os.path.join(os.getcwd(), 'scripts'))
            from modules.youtube_auth import list_available_profiles
            profiles = list_available_profiles()
            self.api_profile_combo.configure(values=profiles)
            current = self.api_profile_var.get()
            if current not in profiles and profiles:
                self.api_profile_var.set(profiles[0])
        except Exception as e:
            logger.error(f"Failed to refresh profiles: {e}")
    
    def add_api_account(self):
        file_path = filedialog.askopenfilename(title="Select Client Secret JSON", filetypes=[("JSON", "*.json")])
        if not file_path: return
        
        dialog = ctk.CTkInputDialog(text="Enter account name:", title="New Account")
        name = dialog.get_input()
        if not name: return
        
        safe_name = "".join(c for c in name if c.isalnum() or c in ' _-').strip()
        if not safe_name:
            messagebox.showerror("Error", "Invalid name")
            return
        
        try:
            import shutil
            dest_dir = os.path.join(os.getcwd(), 'credentials')
            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, f"{safe_name}.json")
            
            if os.path.exists(dest_path):
                if not messagebox.askyesno("Confirm", f"'{safe_name}' exists. Overwrite?"):
                    return
            
            shutil.copy2(file_path, dest_path)
            messagebox.showinfo("Success", f"Account '{safe_name}' added!")
            self.refresh_api_profiles()
            self.api_profile_var.set(safe_name)
        except Exception as e:
            messagebox.showerror("Error", f"Failed: {e}")
    
    def verify_api_account(self):
        try:
            script_path = os.path.abspath(os.path.join("scripts", "check_auth.py"))
            if sys.platform == 'win32':
                subprocess.Popen([sys.executable, script_path],
                                  creationflags=subprocess.CREATE_NEW_CONSOLE, cwd=os.getcwd())
            else:
                messagebox.showinfo("Info", "Run scripts/check_auth.py in terminal")
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    # ======= SETTINGS & PRESETS =======
    def load_settings(self):
        try:
            if os.path.exists("settings.json"):
                with open("settings.json", "r", encoding='utf-8') as f:
                    data = json.load(f)
                    if "custom_prompt" in data:
                        self.entry_prompt.delete(0, "end")
                        self.entry_prompt.insert(0, data["custom_prompt"])
                    self.presets = data.get("presets", {})
                    self.update_preset_combo()
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
    
    def save_settings(self):
        try:
            data = {}
            if os.path.exists("settings.json"):
                try:
                    with open("settings.json", "r", encoding='utf-8') as f:
                        data = json.load(f)
                except: pass
            data["custom_prompt"] = self.entry_prompt.get()
            data["presets"] = self.presets
            with open("settings.json", "w", encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
    
    def update_preset_combo(self):
        names = list(self.presets.keys())
        self.combo_presets.configure(values=names)
        if names:
            self.preset_var.set(names[0])
        self.update_batch_presets()
    
    def update_batch_presets(self):
        if hasattr(self, 'batch_combo_presets'):
            names = list(self.presets.keys())
            self.batch_combo_presets.configure(values=names)
            if names:
                self.batch_preset_var.set(names[0])
    
    def save_preset_dialog(self):
        prompt = self.entry_prompt.get()
        if not prompt:
            messagebox.showwarning("Warning", "Prompt is empty!")
            return
        dialog = ctk.CTkInputDialog(text="Enter preset name:", title="Save Preset")
        name = dialog.get_input()
        if name:
            self.presets[name] = prompt
            self.save_settings()
            self.update_preset_combo()
            self.preset_var.set(name)
            messagebox.showinfo("Success", f"Saved '{name}'")
    
    def load_preset_selection(self, choice=None):
        name = self.preset_var.get()
        if name in self.presets:
            self.entry_prompt.delete(0, "end")
            self.entry_prompt.insert(0, self.presets[name])
    
    def batch_load_preset(self, choice=None):
        name = self.batch_preset_var.get()
        if name in self.presets:
            self.batch_entry_prompt.delete(0, "end")
            self.batch_entry_prompt.insert(0, self.presets[name])
    
    def delete_preset(self):
        name = self.preset_var.get()
        if name and name in self.presets:
            if messagebox.askyesno("Confirm", f"Delete '{name}'?"):
                del self.presets[name]
                self.save_settings()
                self.update_preset_combo()
                self.entry_prompt.delete(0, "end")
    
    def open_preset_manager(self):
        """Open a full preset manager dialog."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("✏️ Preset Manager")
        dialog.geometry("700x500")
        dialog.configure(fg_color=COLORS['bg_dark'])
        dialog.transient(self)
        dialog.grab_set()
        dialog.after(100, dialog.lift)
        
        # Header
        ctk.CTkLabel(dialog, text="✏️ Preset Manager", font=ctk.CTkFont(size=18, weight="bold")).pack(
            anchor="w", padx=20, pady=(15, 5))
        ctk.CTkLabel(dialog, text="Add, edit, or delete prompt presets",
                      text_color=COLORS['text_dim']).pack(anchor="w", padx=20, pady=(0, 10))
        
        # Main content
        content = ctk.CTkFrame(dialog, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        
        # Left: Preset list
        left = ctk.CTkFrame(content, fg_color=COLORS['bg_card'], corner_radius=10, width=200)
        left.pack(side="left", fill="y", padx=(0, 10))
        left.pack_propagate(False)
        
        ctk.CTkLabel(left, text="Presets", font=ctk.CTkFont(weight="bold")).pack(padx=10, pady=(10, 5))
        
        list_frame = ctk.CTkScrollableFrame(left, fg_color="transparent")
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Right: Editor
        right = ctk.CTkFrame(content, fg_color=COLORS['bg_card'], corner_radius=10)
        right.pack(side="left", fill="both", expand=True)
        
        ctk.CTkLabel(right, text="Preset Name:", font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=15, pady=(15, 3))
        name_entry = ctk.CTkEntry(right, placeholder_text="Preset name...")
        name_entry.pack(fill="x", padx=15, pady=(0, 10))
        
        ctk.CTkLabel(right, text="Prompt Content:", font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=15, pady=(5, 3))
        prompt_textbox = ctk.CTkTextbox(right, fg_color=COLORS['bg_dark'], height=200,
                                          font=ctk.CTkFont(size=13))
        prompt_textbox.pack(fill="both", expand=True, padx=15, pady=(0, 10))
        
        # State
        selected_preset = [None]  # mutable container
        preset_buttons = []
        
        def select_preset(name):
            selected_preset[0] = name
            name_entry.delete(0, "end")
            name_entry.insert(0, name)
            prompt_textbox.delete("1.0", "end")
            prompt_textbox.insert("1.0", self.presets.get(name, ""))
            # Highlight selected button
            for btn, btn_name in preset_buttons:
                if btn_name == name:
                    btn.configure(fg_color=COLORS['accent'])
                else:
                    btn.configure(fg_color=COLORS['bg_hover'])
        
        def refresh_list():
            for widget in list_frame.winfo_children():
                widget.destroy()
            preset_buttons.clear()
            for pname in self.presets:
                btn = ctk.CTkButton(list_frame, text=pname, anchor="w",
                                     fg_color=COLORS['bg_hover'], hover_color=COLORS['border'],
                                     height=32, command=lambda n=pname: select_preset(n))
                btn.pack(fill="x", pady=1)
                preset_buttons.append((btn, pname))
        
        def save_current():
            new_name = name_entry.get().strip()
            new_prompt = prompt_textbox.get("1.0", "end").strip()
            if not new_name:
                messagebox.showwarning("Warning", "Preset name is empty!", parent=dialog)
                return
            if not new_prompt:
                messagebox.showwarning("Warning", "Prompt content is empty!", parent=dialog)
                return
            
            old_name = selected_preset[0]
            # If renaming (old name exists and differs from new name)
            if old_name and old_name != new_name and old_name in self.presets:
                del self.presets[old_name]
            
            self.presets[new_name] = new_prompt
            self.save_settings()
            self.update_preset_combo()
            selected_preset[0] = new_name
            refresh_list()
            select_preset(new_name)
            messagebox.showinfo("Saved", f"Preset '{new_name}' saved!", parent=dialog)
        
        def add_new():
            selected_preset[0] = None
            name_entry.delete(0, "end")
            prompt_textbox.delete("1.0", "end")
            name_entry.focus()
            for btn, _ in preset_buttons:
                btn.configure(fg_color=COLORS['bg_hover'])
        
        def delete_current():
            name = selected_preset[0]
            if name and name in self.presets:
                if messagebox.askyesno("Confirm", f"Delete '{name}'?", parent=dialog):
                    del self.presets[name]
                    self.save_settings()
                    self.update_preset_combo()
                    selected_preset[0] = None
                    name_entry.delete(0, "end")
                    prompt_textbox.delete("1.0", "end")
                    refresh_list()
        
        # Editor buttons
        btn_row = ctk.CTkFrame(right, fg_color="transparent")
        btn_row.pack(fill="x", padx=15, pady=(0, 15))
        
        ctk.CTkButton(btn_row, text="💾 Save", width=90, fg_color=COLORS['success'],
                       hover_color="#16a34a", command=save_current).pack(side="left", padx=2)
        ctk.CTkButton(btn_row, text="➕ New", width=80, fg_color=COLORS['accent'],
                       hover_color=COLORS['accent_hover'], command=add_new).pack(side="left", padx=2)
        ctk.CTkButton(btn_row, text="🗑️ Delete", width=90, fg_color=COLORS['error'],
                       hover_color="#dc2626", command=delete_current).pack(side="left", padx=2)
        
        refresh_list()
        
        # Select first preset if exists
        if self.presets:
            first = list(self.presets.keys())[0]
            select_preset(first)


if __name__ == "__main__":
    app = SunoApp()
    app.mainloop()
