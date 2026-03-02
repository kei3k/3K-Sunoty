import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import subprocess
import os
import sys
import threading
import logging
import queue
import time
import json
import json
from selenium_suno import SunoBrowserAutomation
import warnings

# Suppress harmless Google API warnings
warnings.filterwarnings("ignore", category=FutureWarning, module="google.api_core")

# Configure logging for GUI
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SunoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Suno Remix & Automation Tool")
        self.root.geometry("1000x800")
        
        self.bg_color = "#f0f0f0"
        self.root.configure(bg=self.bg_color)
        
        # User Data Directory (Persistence)
        self.user_data_dir = os.path.join(os.getcwd(), "chrome_profile")
        if not os.path.exists(self.user_data_dir):
            os.makedirs(self.user_data_dir)

        # Thread-safe logging queue
        self.log_queue = queue.Queue()
        
        self.create_widgets()
        
        # Start queue polling
        self.check_queue()

    def check_queue(self):
        """Check queue for new messages and update UI"""
        while not self.log_queue.empty():
            try:
                msg = self.log_queue.get_nowait()
                self.text_output.insert(tk.END, msg)
                self.text_output.see(tk.END)
            except queue.Empty:
                pass
        
        # Schedule next check
        self.root.after(100, self.check_queue)

    def append_output(self, text):
        """Queue text for main thread to display"""
        self.log_queue.put(text)

    def create_widgets(self):
        # --- Login Section ---
        login_frame = tk.LabelFrame(self.root, text="1. Suno Account Setup", padx=10, pady=10, bg=self.bg_color)
        login_frame.pack(fill="x", padx=10, pady=5)

        self.login_status = tk.Label(login_frame, text="Status: Checking...", bg=self.bg_color, fg="blue")
        self.login_status.pack(side="left", padx=5)

        self.login_btn = tk.Button(login_frame, text="Login Suno (First Time)", command=self.start_login_thread, bg="#4CAF50", fg="white")
        self.login_btn.pack(side="right", padx=5)

        # --- Tabs ---
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="x", padx=10, pady=5, expand=False)

        # Tab 1: Remix
        self.tab_remix = tk.Frame(self.notebook, bg=self.bg_color)
        self.notebook.add(self.tab_remix, text="  🎵 Single Remix  ")
        self.setup_remix_tab()

        # Tab 2: BATCH Remix (NEW)
        self.tab_batch = tk.Frame(self.notebook, bg=self.bg_color)
        self.notebook.add(self.tab_batch, text="  📋 Batch Remix (Multi-Song)  ")
        self.setup_batch_tab()

        # Tab 2.5: Download Only (NEW)
        self.tab_download = tk.Frame(self.notebook, bg=self.bg_color)
        self.notebook.add(self.tab_download, text="  📥 Download Only  ")
        self.setup_download_tab()

        # Tab 3: Single Copyright Check
        self.tab_copyright = tk.Frame(self.notebook, bg=self.bg_color)
        self.notebook.add(self.tab_copyright, text="  © Single Check  ")
        self.setup_copyright_tab()

        # Tab 4: Batch Copyright Check
        self.tab_batch_cp = tk.Frame(self.notebook, bg=self.bg_color)
        self.notebook.add(self.tab_batch_cp, text="  📚 Batch Copyright Check  ")
        self.setup_batch_copyright_tab()

        # --- Output Section ---
        tk.Label(self.root, text="Process Output:", bg=self.bg_color).pack(anchor="w", padx=10)
        self.text_output = scrolledtext.ScrolledText(self.root, width=80, height=20, bg="#1e1e1e", fg="#00ff00", font=("Consolas", 10))
        self.text_output.pack(fill="both", expand=True, padx=10, pady=5)

    def setup_remix_tab(self):
        frame = self.tab_remix
        
        # Song Path
        tk.Label(frame, text="Song Path (MP3):", bg=self.bg_color).grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.entry_song_path = tk.Entry(frame, width=40)
        self.entry_song_path.grid(row=0, column=1, padx=5, pady=5)
        tk.Button(frame, text="Browse", command=self.browse_file).grid(row=0, column=2, padx=5, pady=5)

        # Song Name
        tk.Label(frame, text="Song Name:", bg=self.bg_color).grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.entry_song_name = tk.Entry(frame, width=40)
        self.entry_song_name.grid(row=1, column=1, padx=5, pady=5)

        # Channel ID
        tk.Label(frame, text="YouTube Channel ID:", bg=self.bg_color).grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.entry_channel_id = tk.Entry(frame, width=40)
        self.entry_channel_id.grid(row=2, column=1, padx=5, pady=5)
        self.entry_channel_id.insert(0, "UCMee3KgPjZOl7f4gEmUni2Q")

        # Custom Prompt (Priority) - Now the ONLY Main Input
        tk.Label(frame, text="Prompt / Style Description:", bg=self.bg_color, font=("Arial", 10, "bold")).grid(row=3, column=0, sticky="w", padx=5, pady=5)
        self.entry_prompt = tk.Entry(frame, width=50) # Widen standard entry
        self.entry_prompt.grid(row=3, column=1, padx=5, pady=5, columnspan=2, sticky="w")
        
        # Output Prompt Presets Row
        # Use a LabelFrame for better visibility
        preset_frame = tk.LabelFrame(frame, text="Saved Prompts Manager", bg=self.bg_color, padx=5, pady=5)
        preset_frame.grid(row=4, column=0, columnspan=3, sticky="ew", padx=5, pady=5)
        
        tk.Label(preset_frame, text="Select Preset:", bg=self.bg_color).grid(row=0, column=0, sticky="w", padx=5)
        
        self.preset_var = tk.StringVar()
        self.combo_presets = ttk.Combobox(preset_frame, textvariable=self.preset_var, state="readonly", width=30)
        self.combo_presets.grid(row=0, column=1, padx=5)
        self.combo_presets.bind("<<ComboboxSelected>>", self.load_preset_selection)
        
        # Buttons with colors
        tk.Button(preset_frame, text="💾 Save Current Prompt", command=self.save_preset_dialog, bg="#4CAF50", fg="white", font=("Arial", 9, "bold")).grid(row=0, column=2, padx=5)
        tk.Button(preset_frame, text="❌ Delete Selected", command=self.delete_preset, bg="#ff4444", fg="white", font=("Arial", 9)).grid(row=0, column=3, padx=5)

        # Initialize Data
        self.presets = {}
        self.load_settings()

        # Action Buttons
        btn_frame = tk.Frame(frame, bg=self.bg_color)
        btn_frame.grid(row=5, column=0, columnspan=3, pady=20, sticky="ew")
        
        tk.Button(btn_frame, text="RUN REMIX (Generation Only)", command=lambda: self.run_remix(remix_only=True), bg="#2196F3", fg="white", font=("Arial", 11, "bold"), pady=8).pack(side="left", expand=True, fill="x", padx=20)
        # tk.Button(btn_frame, text="Full Flow (Beta)", command=lambda: self.run_remix(remix_only=False), bg="gray", fg="white").pack(side="right", padx=5)

    def setup_batch_tab(self):
        """Setup the Batch Remix tab with song queue"""
        frame = self.tab_batch
        
        # Initialize batch queue
        self.batch_queue = []
        
        # --- Add Song Section ---
        add_frame = tk.LabelFrame(frame, text="Add Song to Queue", padx=10, pady=10, bg=self.bg_color)
        add_frame.pack(fill="x", padx=10, pady=5)
        
        # Song Path
        tk.Label(add_frame, text="Song Path:", bg=self.bg_color).grid(row=0, column=0, sticky="w", padx=5, pady=3)
        self.batch_entry_path = tk.Entry(add_frame, width=35)
        self.batch_entry_path.grid(row=0, column=1, padx=5, pady=3)
        tk.Button(add_frame, text="Browse", command=self.batch_browse_file).grid(row=0, column=2, padx=5, pady=3)
        
        # Song Name
        tk.Label(add_frame, text="Song Name:", bg=self.bg_color).grid(row=1, column=0, sticky="w", padx=5, pady=3)
        self.batch_entry_name = tk.Entry(add_frame, width=35)
        self.batch_entry_name.grid(row=1, column=1, padx=5, pady=3)
        
        # Prompt
        tk.Label(add_frame, text="Prompt/Style:", bg=self.bg_color).grid(row=2, column=0, sticky="w", padx=5, pady=3)
        self.batch_entry_prompt = tk.Entry(add_frame, width=35)
        self.batch_entry_prompt.grid(row=2, column=1, padx=5, pady=3)
        
        # Saved Presets Dropdown
        tk.Label(add_frame, text="Load Preset:", bg=self.bg_color).grid(row=3, column=0, sticky="w", padx=5, pady=3)
        self.batch_preset_var = tk.StringVar()
        self.batch_combo_presets = ttk.Combobox(add_frame, textvariable=self.batch_preset_var, state="readonly", width=32)
        self.batch_combo_presets.grid(row=3, column=1, padx=5, pady=3)
        self.batch_combo_presets.bind("<<ComboboxSelected>>", self.batch_load_preset)
        
        # Update preset list
        self.update_batch_presets()
        
        # Add Button
        tk.Button(add_frame, text="➕ Add to Queue", command=self.batch_add_song, bg="#4CAF50", fg="white", font=("Arial", 10, "bold")).grid(row=0, column=3, rowspan=3, padx=10, pady=5, sticky="ns")
        
        # --- Queue Table ---
        queue_frame = tk.LabelFrame(frame, text=f"Song Queue (0/20 songs)", padx=10, pady=10, bg=self.bg_color)
        queue_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.queue_label_frame = queue_frame  # Reference to update title
        
        # Treeview for queue
        columns = ("Name", "Prompt", "Path")
        self.batch_tree = ttk.Treeview(queue_frame, columns=columns, show="headings", height=8)
        self.batch_tree.heading("Name", text="Song Name")
        self.batch_tree.heading("Prompt", text="Prompt/Style")
        self.batch_tree.heading("Path", text="File Path")
        self.batch_tree.column("Name", width=150)
        self.batch_tree.column("Prompt", width=200)
        self.batch_tree.column("Path", width=200)
        self.batch_tree.pack(side="left", fill="both", expand=True)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(queue_frame, orient="vertical", command=self.batch_tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.batch_tree.configure(yscrollcommand=scrollbar.set)
        
        # --- Control Buttons ---
        ctrl_frame = tk.Frame(frame, bg=self.bg_color)
        ctrl_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Button(ctrl_frame, text="❌ Remove Selected", command=self.batch_remove_song, bg="#ff4444", fg="white").pack(side="left", padx=5)
        tk.Button(ctrl_frame, text="🗑️ Clear All", command=self.batch_clear_queue, bg="#ff8800", fg="white").pack(side="left", padx=5)
        
        # Wait time setting
        tk.Label(ctrl_frame, text="Wait after create (min):", bg=self.bg_color).pack(side="left", padx=(20, 5))
        self.batch_wait_var = tk.StringVar(value="10")
        tk.Entry(ctrl_frame, textvariable=self.batch_wait_var, width=5).pack(side="left")
        
        # START Button
        tk.Button(ctrl_frame, text="🚀 START BATCH CREATE & DOWNLOAD", command=self.run_batch_remix, bg="#9C27B0", fg="white", font=("Arial", 12, "bold"), pady=10).pack(side="right", padx=10)

    def batch_browse_file(self):
        """Browse for audio file in batch tab"""
        filename = filedialog.askopenfilename(filetypes=[("Audio files", "*.mp3 *.wav")])
        if filename:
            self.batch_entry_path.delete(0, tk.END)
            self.batch_entry_path.insert(0, filename)
            # Auto-fill name from filename
            basename = os.path.splitext(os.path.basename(filename))[0]
            if not self.batch_entry_name.get():
                self.batch_entry_name.insert(0, basename)

    def batch_add_song(self):
        """Add song to batch queue"""
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
            messagebox.showwarning("Limit Reached", "Maximum 20 songs per batch")
            return
        
        # Add to queue
        song = {"path": path, "name": name, "prompt": prompt or "Cover"}
        self.batch_queue.append(song)
        
        # Update tree
        self.batch_tree.insert("", "end", values=(name, prompt or "Cover", path))
        
        # Clear inputs
        self.batch_entry_path.delete(0, tk.END)
        self.batch_entry_name.delete(0, tk.END)
        self.batch_entry_prompt.delete(0, tk.END)
        
        # Update count
        self.queue_label_frame.config(text=f"Song Queue ({len(self.batch_queue)}/20 songs)")

    def batch_remove_song(self):
        """Remove selected song from queue"""
        selected = self.batch_tree.selection()
        if not selected:
            return
        for item in selected:
            idx = self.batch_tree.index(item)
            self.batch_tree.delete(item)
            if idx < len(self.batch_queue):
                self.batch_queue.pop(idx)
        self.queue_label_frame.config(text=f"Song Queue ({len(self.batch_queue)}/20 songs)")

    def batch_clear_queue(self):
        """Clear entire queue"""
        if self.batch_queue and messagebox.askyesno("Confirm", "Clear all songs from queue?"):
            self.batch_queue = []
            for item in self.batch_tree.get_children():
                self.batch_tree.delete(item)
            self.queue_label_frame.config(text="Song Queue (0/20 songs)")

    def setup_download_tab(self):
        """Setup the Download Only tab - for downloading covers after batch creation"""
        frame = self.tab_download
        
        # --- Info Section ---
        info_frame = tk.LabelFrame(frame, text="📥 Download Cover Songs from Suno", padx=10, pady=10, bg=self.bg_color)
        info_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(info_frame, text="Sử dụng tab này để tải bài hát sau khi đã tạo xong bằng Batch Remix.", 
                 bg=self.bg_color, font=("Arial", 10)).pack(anchor="w", pady=5)
        tk.Label(info_frame, text="• Mỗi bài input tạo ra 2 cover outputs", bg=self.bg_color).pack(anchor="w")
        tk.Label(info_frame, text="• Mỗi output = 1 MP3 + 1 Video", bg=self.bg_color).pack(anchor="w")
        tk.Label(info_frame, text="• Ví dụ: 4 bài input → 8 outputs → 16 files (8 MP3 + 8 Video)", bg=self.bg_color).pack(anchor="w")
        
        # --- Input Section ---
        input_frame = tk.LabelFrame(frame, text="Download Settings", padx=10, pady=10, bg=self.bg_color)
        input_frame.pack(fill="x", padx=10, pady=10)
        
        # Number of INPUT songs
        tk.Label(input_frame, text="Số bài INPUT đã tạo:", bg=self.bg_color, font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.download_input_count = tk.StringVar(value="4")
        tk.Entry(input_frame, textvariable=self.download_input_count, width=10, font=("Arial", 12)).grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        # Calculated outputs
        self.download_output_label = tk.Label(input_frame, text="→ 8 outputs (8 MP3 + 8 Video = 16 files)", bg=self.bg_color, fg="blue")
        self.download_output_label.grid(row=0, column=2, padx=10, pady=5, sticky="w")
        
        # Update label when input changes
        def update_output_calc(*args):
            try:
                num_input = int(self.download_input_count.get())
                num_output = num_input * 2
                num_files = num_output * 2
                self.download_output_label.config(text=f"→ {num_output} outputs ({num_output} MP3 + {num_output} Video = {num_files} files)")
            except:
                self.download_output_label.config(text="→ Invalid input")
        
        self.download_input_count.trace_add("write", update_output_calc)
        
        # --- Action Buttons ---
        btn_frame = tk.Frame(frame, bg=self.bg_color)
        btn_frame.pack(fill="x", padx=20, pady=20)
        
        tk.Button(btn_frame, text="🚀 START DOWNLOAD", command=self.run_download_only, 
                  bg="#4CAF50", fg="white", font=("Arial", 14, "bold"), pady=15).pack(side="left", fill="x", expand=True, padx=(0, 10))
                  
        tk.Button(btn_frame, text="⛔ STOP", command=self.stop_process, 
                  bg="#FF5252", fg="white", font=("Arial", 14, "bold"), pady=15).pack(side="right", padx=(10, 0))
        
        # --- Notes ---
        notes_frame = tk.LabelFrame(frame, text="Notes", padx=10, pady=10, bg=self.bg_color)
        notes_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(notes_frame, text="• Browser sẽ mở và navigate tới Suno Create page", bg=self.bg_color).pack(anchor="w")
        tk.Label(notes_frame, text="• Tự động filter Cover songs và download từng bài", bg=self.bg_color).pack(anchor="w")
        tk.Label(notes_frame, text="• Files sẽ được lưu vào thư mục Downloads mặc định", bg=self.bg_color).pack(anchor="w")
        
        self.stop_flag = False

    def stop_process(self):
        """Stop current running process"""
        if messagebox.askyesno("Confirm Stop", "Bạn có chắc muốn dừng quá trình không?"):
            self.stop_flag = True
            self.append_output("\n🛑 Đang gửi lệnh STOP... Vui lòng đợi tiến trình dừng hẳn.\n")

    def run_download_only(self):
        """Run download only - Phase 3 separated from batch flow"""
        try:
            num_input = int(self.download_input_count.get())
            if num_input <= 0:
                messagebox.showerror("Error", "Số lượng bài phải > 0")
                return
        except:
            messagebox.showerror("Error", "Vui lòng nhập số hợp lệ")
            return
        
        num_output = num_input * 2
        
        self.text_output.delete(1.0, tk.END)
        self.append_output(f"=== DOWNLOAD ONLY MODE ===\n")
        self.append_output(f"Input songs: {num_input}\n")
        self.append_output(f"Expected outputs: {num_output} (each input = 2 covers)\n")
        self.append_output(f"Expected files: {num_output * 2} (MP3 + Video per output)\n\n")
        
        self.stop_flag = False
        
        def download_worker():
            browser = None
            try:
                import time
                
                # Initialize browser
                if self.stop_flag: return
                self.append_output("🌐 Starting browser...\n")
                browser = SunoBrowserAutomation(user_data_dir=self.user_data_dir)
                
                # Navigate to Suno and wait for login
                if self.stop_flag: 
                    browser.close()
                    return
                self.append_output("🔗 Navigating to Suno.ai...\n")
                browser.navigate_to_suno()
                
                self.append_output("⏳ Waiting for login (check browser window)...\n")
                if not browser.wait_for_login(timeout=300):  # 5 minute timeout
                    self.append_output("❌ Login timeout! Please login to Suno first.\n")
                    browser.close()
                    return
                
                if self.stop_flag:
                    self.append_output("🛑 Process stopped by user.\n")
                    browser.close()
                    return
                
                self.append_output("✅ Login detected! Starting download...\n\n")
                
                # Call batch_download directly
                self.append_output(f"=== PHASE 3: DOWNLOADING {num_output} SONGS ===\n")
                
                downloaded = browser.batch_download(
                    num_input, 
                    log_callback=self.append_output,
                    stop_check_callback=lambda: self.stop_flag
                )
                
                if self.stop_flag:
                    self.append_output(f"\n🛑 Stopped! Downloaded: {downloaded}/{num_output} songs\n")
                else:
                    self.append_output(f"\n✅ Downloads complete: {downloaded}/{num_output} songs\n")
                    self.append_output(f"   Files: {downloaded} MP3 + {downloaded} Video = {downloaded * 2} total\n")
                
                # Keep browser open for downloads to complete if not stopped immediately?
                # If stopped, we usually want to close.
                # Keep browser open for downloads to complete if not stopped immediately?
                # If stopped, we usually want to close.
                # User requested removal of 60s wait since we now verify file completion in selenium_suno.py
                
                
                browser.close()
                if not self.stop_flag:
                    self.append_output("\n=== DOWNLOAD COMPLETE ===\n")
                    self.append_output("Check your Downloads folder!\n")
                    messagebox.showinfo("Done", f"Download complete!\n{downloaded} songs downloaded.")
                else:
                    self.append_output("\n=== STOPPED ===\n")
                
            except Exception as e:
                self.append_output(f"\n❌ Error: {e}\n")
                import traceback
                traceback.print_exc()
            finally:
                if browser:
                    try:
                        browser.close()
                    except:
                        pass
        
        thread = threading.Thread(target=download_worker, daemon=True)
        thread.start()


    def run_batch_remix(self):
        """Run batch remix process"""
        if not self.batch_queue:
            messagebox.showerror("Error", "Queue is empty. Add songs first!")
            return
        
        try:
            wait_minutes = int(self.batch_wait_var.get())
        except:
            wait_minutes = 10
        
        self.text_output.delete(1.0, tk.END)
        self.append_output(f"=== BATCH REMIX START ===\n")
        self.append_output(f"Songs in queue: {len(self.batch_queue)}\n")
        self.append_output(f"Wait time after creation: {wait_minutes} minutes\n\n")
        
        def batch_worker():
            browser = None
            try:
                import time
                
                # Initialize browser
                self.append_output("🌐 Starting browser...\n")
                browser = SunoBrowserAutomation(user_data_dir=self.user_data_dir)
                
                # Navigate to Suno and wait for login
                self.append_output("🔗 Navigating to Suno.ai...\n")
                browser.navigate_to_suno()
                
                self.append_output("⏳ Waiting for login (check browser window)...\n")
                if not browser.wait_for_login(timeout=300):  # 5 minute timeout
                    self.append_output("❌ Login timeout! Please login to Suno first.\n")
                    browser.close()
                    return
                
                self.append_output("✅ Login detected! Starting batch creation...\n\n")
                
                # Phase 1: Create all songs
                self.append_output("=== PHASE 1: CREATING SONGS ===\n")
                created_count = 0
                failed_songs = []
                
                for i, song in enumerate(self.batch_queue):
                    self.append_output(f"\n[{i+1}/{len(self.batch_queue)}] Creating: {song['name']}\n")
                    
                    try:
                        # Pass log callback to show detailed steps in GUI
                        success = browser.create_song_only(
                            audio_path=song['path'],
                            title=song['name'],
                            prompt=song['prompt'],
                            log_callback=self.append_output
                        )
                        
                        if success:
                            created_count += 1
                            self.append_output(f"✅ DONE: {song['name']}\n")
                        else:
                            failed_songs.append(song['name'])
                            self.append_output(f"❌ FAILED: {song['name']}\n")
                    except Exception as e:
                        failed_songs.append(song['name'])
                        self.append_output(f"❌ Error: {str(e)[:100]}\n")
                        
                        # Check if browser session is still valid
                        try:
                            browser.driver.current_url
                        except:
                            self.append_output("⚠️ Browser session lost! Attempting to recover...\n")
                            try:
                                browser.close()
                            except:
                                pass
                            browser = SunoBrowserAutomation(user_data_dir=self.user_data_dir)
                            browser.navigate_to_suno()
                            time.sleep(5)  # Give time for session to restore
                
                self.append_output(f"\n=== Creation Complete: {created_count}/{len(self.batch_queue)} ===\n")
                if failed_songs:
                    self.append_output(f"⚠️ Failed songs: {', '.join(failed_songs)}\n")
                
                if created_count == 0:
                    self.append_output("\n❌ No songs created. Aborting.\n")
                    browser.close()
                    return
                
                # Phase 2: Wait for generation
                self.append_output(f"\n=== PHASE 2: WAITING {wait_minutes} MINUTES ===\n")
                for remaining in range(wait_minutes * 60, 0, -30):
                    mins = remaining // 60
                    secs = remaining % 60
                    self.append_output(f"⏳ Waiting: {mins}m {secs}s remaining...\n")
                    time.sleep(30)
                
                # Phase 3: Download all
                self.append_output(f"\n=== PHASE 3: DOWNLOADING ALL SONGS ===\n")
                downloaded = browser.batch_download(created_count, log_callback=self.append_output)
                self.append_output(f"\n✅ Downloads complete: {downloaded} songs\n")
                
                browser.close()
                self.append_output("\n=== BATCH COMPLETE ===\n")
                self.append_output("Check your Downloads folder!\n")
                
            except Exception as e:
                self.append_output(f"\n❌ Error: {e}\n")
                import traceback
                traceback.print_exc()
            finally:
                if browser:
                    try:
                        browser.close()
                    except:
                        pass
        
        thread = threading.Thread(target=batch_worker, daemon=True)
        thread.start()

    def setup_copyright_tab(self):
        frame = self.tab_copyright
        tk.Label(frame, text="Video/Audio Path:", bg=self.bg_color).grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.entry_cp_file = tk.Entry(frame, width=40)
        self.entry_cp_file.grid(row=0, column=1, padx=5, pady=5)
        tk.Button(frame, text="Browse", command=self.browse_cp_file).grid(row=0, column=2, padx=5, pady=5)
        
        tk.Label(frame, text="YouTube Channel ID:", bg=self.bg_color).grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.entry_cp_channel = tk.Entry(frame, width=40)
        self.entry_cp_channel.grid(row=1, column=1, padx=5, pady=5)
        
        # Load default channel ID if available
        # You might want to sync this with tab 1 or load from config
        self.entry_cp_channel.insert(0, "UCMee3KgPjZOl7f4gEmUni2Q")
        
        tk.Button(frame, text="RUN COPYRIGHT CHECK (Test Video)", command=self.run_copyright_check, bg="#FF9800", fg="white", font=("Arial", 10, "bold")).grid(row=2, column=0, columnspan=2, pady=10, sticky="ew")
        
        # Auto-delete Option
        self.auto_delete_var = tk.BooleanVar(value=True)
        tk.Checkbutton(frame, text="Auto-delete from Studio after check", variable=self.auto_delete_var, bg=self.bg_color).grid(row=2, column=2, padx=5)

    def browse_cp_file(self):
        filename = filedialog.askopenfilename(filetypes=[("Media files", "*.mp4 *.mp3 *.wav")])
        if filename:
            self.entry_cp_file.delete(0, tk.END)
            self.entry_cp_file.insert(0, filename)
            
    def browse_file(self):
        filename = filedialog.askopenfilename(filetypes=[("MP3 files", "*.mp3")])
        if filename:
            self.entry_song_path.delete(0, tk.END)
            self.entry_song_path.insert(0, filename)

    def run_copyright_check(self):
        file_path = self.entry_cp_file.get()
        channel_id = self.entry_cp_channel.get()
        auto_delete = self.auto_delete_var.get()
        
        if not file_path or not channel_id:
            messagebox.showerror("Error", "Please fill in all fields")
            return
            
        self.text_output.delete(1.0, tk.END)
        self.append_output(f"Starting Copyright Check...\nFile: {file_path}\nChannel: {channel_id}\nAuto Detail: {auto_delete}\n\n")
        
        def worker():
            try:
                cmd = [
                    sys.executable,
                    "scripts/3_copyright_check.py",
                    file_path,
                    "--channel-id", channel_id
                ]
                
                if not auto_delete:
                    cmd.append("--keep-video")
                
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=os.getcwd())

                for line in iter(process.stdout.readline, ''):
                    self.append_output(line)
                
                process.stdout.close()
                process.wait()
                
                if process.returncode == 0:
                    self.append_output("\nCopyright Check Completed Successfully!\n")
                else:
                    self.append_output("\nCopyright Check Failed or Found Issues.\n")

            except Exception as e:
                self.append_output(f"\nError: {str(e)}\n")

        threading.Thread(target=worker).start()

    def setup_batch_copyright_tab(self):
        """Setup Batch Copyright Check Tab"""
        frame = self.tab_batch_cp
        
        # Initialize queue
        self.batch_cp_queue = []
        
        # --- Toolbar ---
        # --- Toolbar ---
        tool_frame = tk.LabelFrame(frame, text="Batch Actions", padx=10, pady=10, bg=self.bg_color)
        tool_frame.pack(fill="x", padx=10, pady=5)
        
        # Left side: File Actions
        tk.Button(tool_frame, text="📂 Add Files", command=self.batch_cp_add_files, bg="#2196F3", fg="white", font=("Arial", 10, "bold")).pack(side="left", padx=5)
        tk.Button(tool_frame, text="❌ Remove", command=self.batch_cp_remove, bg="#ff4444", fg="white").pack(side="left", padx=5)
        
        # API Account (Left Middle)
        tk.Label(tool_frame, text=" |  API:", bg=self.bg_color, font=("Arial", 10, "bold")).pack(side="left", padx=5)
        self.api_profile_var = tk.StringVar(value="default")
        self.api_profile_combo = ttk.Combobox(tool_frame, textvariable=self.api_profile_var, state="readonly", width=12)
        self.api_profile_combo.pack(side="left", padx=2)
        tk.Button(tool_frame, text="➕", command=self.add_api_account, width=3, bg="#00C851", fg="white").pack(side="left", padx=2)
        tk.Button(tool_frame, text="🔑", command=self.verify_api_account, width=3, bg="#FFBB33", fg="white").pack(side="left", padx=2)
        
        # Right side: Options
        self.batch_cp_auto_delete = tk.BooleanVar(value=False)
        tk.Checkbutton(tool_frame, text="Auto-delete", variable=self.batch_cp_auto_delete, bg=self.bg_color).pack(side="right", padx=10)
        
        # Channel ID override
        self.batch_cp_channel_entry = tk.Entry(tool_frame, width=20)
        self.batch_cp_channel_entry.pack(side="right", padx=2)
        self.batch_cp_channel_entry.insert(0, "UCMee3KgPjZOl7f4gEmUni2Q")
        tk.Label(tool_frame, text="Chan ID:", bg=self.bg_color).pack(side="right", padx=2)

        self.refresh_api_profiles()
        
        # New Check Recent Button
        tk.Button(tool_frame, text="🔍 Check Recent Details", command=self.run_batch_scan_recent, bg="#9C27B0", fg="white", font=("Arial", 9, "bold")).pack(side="right", padx=10)




        # --- Queue Table ---
        queue_frame = tk.LabelFrame(frame, text="Check Queue (0 files)", padx=10, pady=10, bg=self.bg_color)
        queue_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.cp_queue_label = queue_frame
        
        columns = ("File", "Status", "Result")
        self.batch_cp_tree = ttk.Treeview(queue_frame, columns=columns, show="headings", height=20)
        self.batch_cp_tree.heading("File", text="File Name")
        self.batch_cp_tree.heading("Status", text="Status")
        self.batch_cp_tree.heading("Result", text="Detail/Risk")
        self.batch_cp_tree.column("File", width=300)
        self.batch_cp_tree.column("Status", width=150)
        self.batch_cp_tree.column("Result", width=300)
        
        # Scrollbar
        sb = ttk.Scrollbar(queue_frame, orient="vertical", command=self.batch_cp_tree.yview)
        self.batch_cp_tree.configure(yscrollcommand=sb.set)
        
        self.batch_cp_tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        
        # Context Menu
        self.batch_cp_menu = tk.Menu(self.batch_cp_tree, tearoff=0)
        self.batch_cp_menu.add_command(label="▶️ Watch Video", command=self.batch_cp_open_video)
        self.batch_cp_menu.add_command(label="🛠️ Open in YouTube Studio", command=self.batch_cp_open_studio)
        self.batch_cp_menu.add_separator()
        self.batch_cp_menu.add_command(label="❌ Remove", command=self.batch_cp_remove)
        
        self.batch_cp_tree.bind("<Button-3>", self.show_batch_cp_menu) # Right click

        # --- Start Button ---
        tk.Button(frame, text="🚀 START BATCH CHECK", command=self.run_batch_copyright_check, bg="#4CAF50", fg="white", font=("Arial", 12, "bold"), pady=10).pack(fill="x", padx=20, pady=10)

    def show_batch_cp_menu(self, event):
        item = self.batch_cp_tree.identify_row(event.y)
        if item:
            self.batch_cp_tree.selection_set(item)
            self.batch_cp_menu.post(event.x_root, event.y_root)

    def get_selected_video_id(self):
        selected = self.batch_cp_tree.selection()
        if not selected: return None
        item_id = selected[0]
        values = self.batch_cp_tree.item(item_id)['values']
        # Result column format: "ID: xxxxx" or similar. 
        # But we stored ID in Result column in previous steps?
        # Let's check format: "✅ Uploaded", "ID: video_id"
        # Or "⏳ Polling...", "ID: video_id"
        detail = values[2]
        if "ID: " in detail:
            return detail.split("ID: ")[1].split()[0] # Extract ID safely
        return None

    def batch_cp_open_video(self):
        vid = self.get_selected_video_id()
        if vid:
            import webbrowser
            webbrowser.open(f"https://youtu.be/{vid}")
        else:
            messagebox.showinfo("Info", "No Video ID found for this item.")
            
    def batch_cp_open_studio(self):
        vid = self.get_selected_video_id()
        if vid:
            import webbrowser
            # Studio Direct Link to Copyright Tab for specific video
            webbrowser.open(f"https://studio.youtube.com/video/{vid}/copyright")
        else:
            # Fallback to general content
            webbrowser.open("https://studio.youtube.com/channel/UCMee3KgPjZOl7f4gEmUni2Q/videos/upload")

    def batch_cp_add_files(self):
        files = filedialog.askopenfilenames(filetypes=[("Media files", "*.mp4 *.mp3 *.wav")])
        if files:
            for f in files:
                name = os.path.basename(f)
                if any(q['path'] == f for q in self.batch_cp_queue):
                    continue
                self.batch_cp_queue.append({'path': f, 'name': name, 'status': 'Pending'})
                self.batch_cp_tree.insert("", "end", values=(name, "Pending", "Waiting..."))
            self.cp_queue_label.config(text=f"Check Queue ({len(self.batch_cp_queue)} files)")

    def batch_cp_remove(self):
        selected = self.batch_cp_tree.selection()
        if not selected: return
        for item in selected:
            idx = self.batch_cp_tree.index(item)
            self.batch_cp_tree.delete(item)
            if idx < len(self.batch_cp_queue):
                self.batch_cp_queue.pop(idx)
        self.cp_queue_label.config(text=f"Check Queue ({len(self.batch_cp_queue)} files)")

    def batch_cp_clear(self):
        if messagebox.askyesno("Confirm", "Clear all files?"):
            self.batch_cp_queue = []
            for item in self.batch_cp_tree.get_children():
                self.batch_cp_tree.delete(item)
            self.cp_queue_label.config(text="Check Queue (0 files)")

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
        
        self.text_output.delete(1.0, tk.END)
        self.append_output(f"=== BATCH COPYRIGHT CHECK STARTED ===\nMode: Upload ALL -> Poll ALL\nFiles: {len(self.batch_cp_queue)}\nAccount: {profile_name}\n\n")
        
        def worker():
            import json
            import concurrent.futures
            
            # PHASE 1: UPLOAD ALL (PARALLEL)
            self.append_output(f"--- PHASE 1: UPLOADING (Parallel Max 3) ---\n")
            
            uploaded_items = []
            
            def upload_single_video(task_info):
                idx = task_info['index']
                item = task_info['item']
                
                # Update UI from thread (risk accepted for Tkinter)
                try:
                    tree_item = self.batch_cp_tree.get_children()[idx]
                    self.batch_cp_tree.item(tree_item, values=(item['name'], "⬆️ Uploading...", "Processing"))
                except:
                    pass
                    
                self.append_output(f"Started Upload: {item['name']}...\n")
                
                try:
                    cmd = [
                        sys.executable,
                        "scripts/3_copyright_check.py",
                        item['path'],
                        "--channel-id", channel_id,
                        "--mode", "upload",
                        "--profile", profile_name
                    ]
                    
                    # Use Popen to read stream
                    process = subprocess.Popen(
                        cmd, 
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.STDOUT, # Merge stderr to see errors
                        text=True, 
                        cwd=os.getcwd(),
                        bufsize=1,
                        universal_newlines=True
                    )
                    
                    # Read stdout for progress (simplified)
                    video_id = None
                    full_output = ""
                    
                    for line in process.stdout:
                        line = line.strip()
                        if line:
                            self.append_output(line + "\n")
                            full_output += line + "\n"
                            # Parse progress (simplified)
                            if "Uploading" in line:
                                pass # Could update % here if script outputted it
                            if "Video ID:" in line:
                                parts = line.split("Video ID:")
                                if len(parts) > 1:
                                    video_id = parts[1].strip()

                    process.wait()
                    
                    if process.returncode == 0:
                        # Try to parse JSON last line? No, just rely on video_id extraction
                        if not video_id:
                             # Fallback extraction from output string if line parsing failed
                             import re
                             match = re.search(r"Video ID: ([a-zA-Z0-9_-]+)", full_output)
                             if match:
                                 video_id = match.group(1)

                        if video_id:
                             self.append_output(f"✅ Upload Success: {item['name']} -> {video_id}\n")
                             try: self.batch_cp_tree.item(tree_item, values=(item['name'], "✅ Uploaded", f"ID: {video_id}"))
                             except: pass
                             return {'index': idx, 'item': item, 'video_id': video_id, 'name': item['name']}
                        else:
                             self.append_output(f"❌ Upload Failed (No ID): {item['name']}\n")
                             try: self.batch_cp_tree.item(tree_item, values=(item['name'], "❌ Upload Error", "No ID"))
                             except: pass
                    else:
                        self.append_output(f"❌ Upload Failed: {item['name']}\n")
                        try: self.batch_cp_tree.item(tree_item, values=(item['name'], "❌ Upload Error", "Process Failed"))
                        except: pass

                except Exception as e:
                    self.append_output(f"❌ Error: {item['name']} - {e}\n")
                    try: self.batch_cp_tree.item(tree_item, values=(item['name'], "❌ Error", str(e)))
                    except: pass
                
                return None

            # Execute Uploads
            tasks = []
            for i, item in enumerate(self.batch_cp_queue):
                tasks.append({'index': i, 'item': item})
                
            # CHANGED: max_workers=1 to prevent "uploadLimitExceeded" (Serial Mode)
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                futures = [executor.submit(upload_single_video, t) for t in tasks]
                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    if result:
                        uploaded_items.append(result)
            
            # PHASE 2: BATCH SCAN (Effective Check)
            if not uploaded_items:
                self.append_output("\n⚠️ No videos uploaded successfully. Stopping.\n")
                return

            self.append_output(f"\n--- PHASE 2: CHECKING COPYRIGHT STATUS (Batch Scan) ---\n")
            self.append_output("⏳ Waiting 10s for YouTube processing...\n")
            time.sleep(10)
            
            try:
                cmd = [
                    sys.executable,
                    "scripts/3_copyright_check.py",
                    "--mode", "scan",
                    "--profile", profile_name
                ]
                if channel_id:
                    cmd.extend(["--channel-id", channel_id])
                
                process = subprocess.Popen(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.STDOUT, 
                    text=True, 
                    cwd=os.getcwd(),
                    bufsize=1,
                    universal_newlines=True
                )
                
                scan_results = []
                
                # Collect all output
                full_output = ""
                for line in process.stdout:
                    line = line.strip()
                    if line:
                        self.append_output(line + "\n")
                        full_output += line + "\n"
                              
                process.wait()
                
                # Parse JSON result from output
                # The script outputs JSON at the end with format: {"status": "success", "scanned": N, "details": [...]}
                self.append_output("\n[SYNC] Parsing scan results...\n")
                
                try:
                    # Find JSON in output - look for the final JSON block with "scanned" key
                    import re
                    # Find JSON that contains "scanned" (the final result)
                    json_match = re.search(r'\{\s*"status"\s*:\s*"success"\s*,\s*"scanned"\s*:', full_output)
                    
                    if json_match:
                        json_start = json_match.start()
                        json_str = full_output[json_start:]
                        # Find the matching closing brace
                        brace_count = 0
                        json_end = 0
                        for i, c in enumerate(json_str):
                            if c == '{':
                                brace_count += 1
                            elif c == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    json_end = i + 1
                                    break
                        
                        if json_end > 0:
                            json_str = json_str[:json_end]
                            result_data = json.loads(json_str)
                            
                            if result_data.get('status') == 'success' and 'details' in result_data:
                                for res in result_data['details']:
                                    vid_title = res.get('video_title', '')
                                    has_cp = res.get('has_copyright', False)
                                    scan_results.append({
                                        'title': vid_title,
                                        'status': 'COPYRIGHT' if has_cp else 'CLEAN'
                                    })
                                self.append_output(f"[INFO] Parsed {len(scan_results)} video statuses from scan.\n")
                            else:
                                self.append_output(f"[WARNING] Scan returned: {result_data.get('status', 'unknown')}\n")
                                if 'message' in result_data:
                                    self.append_output(f"[WARNING] Message: {result_data.get('message')}\n")
                    else:
                        self.append_output("[WARNING] Could not find JSON result in output.\n")
                        self.append_output(f"[DEBUG] Output length: {len(full_output)} chars\n")
                        self.append_output(f"[DEBUG] Output preview: {full_output[:500]}...\n")
                        
                except json.JSONDecodeError as je:
                    self.append_output(f"[WARNING] JSON parse error: {je}\n")
                except Exception as pe:
                    self.append_output(f"[WARNING] Parse error: {pe}\n")
                    import traceback
                    self.append_output(f"[DEBUG] {traceback.format_exc()}\n")
                
                self.append_output(f"\n[SYNC] Updating Queue Statuses ({len(scan_results)} results)...\n")
                
                # Debug: print uploaded items and scan results for comparison
                self.append_output(f"[DEBUG] Uploaded items: {[i['name'] for i in uploaded_items]}\n")
                self.append_output(f"[DEBUG] Scan result titles: {[r['title'][:50] for r in scan_results[:5]]}...\n")
                
                for item in uploaded_items:
                    found = False
                    # Normalize item name for matching
                    item_name = item['name']
                    item_name_clean = item_name.replace('(Cover)', '').replace('(Remix)', '').replace('_', ' ').strip()
                    
                    for res in scan_results:
                         scan_title = res['title']
                         # Remove common prefixes from scan title
                         scan_clean = scan_title.replace('[TEST] Copyright Check - ', '').replace('_', ' ').strip()
                         
                         # Try multiple matching strategies:
                         # 1. Exact match (after cleaning)
                         # 2. Item name in scan title
                         # 3. Scan title in item name  
                         # 4. First 20 chars match
                         match = False
                         if item_name == scan_title:
                             match = True
                         elif item_name_clean.lower() == scan_clean.lower():
                             match = True
                         elif item_name_clean[:10].lower() in scan_clean.lower():
                             match = True
                         elif scan_clean[:10].lower() in item_name_clean.lower():
                             match = True
                         
                         if match:
                             found = True
                             status_text = "SAFE" if res['status'] == 'CLEAN' else "COPYRIGHT"
                             msg = "No issues" if res['status'] == 'CLEAN' else "Claims Found"
                             self.append_output(f"[MATCH] {item['name'][:40]}... -> {status_text}\n")
                             try:
                                 tree_item = self.batch_cp_tree.get_children()[item['index']]
                                 self.batch_cp_tree.item(tree_item, values=(item['name'], status_text, msg))
                                 self.append_output(f"[UPDATE] Tree item {item['index']} updated.\n")
                             except Exception as te:
                                 self.append_output(f"[ERROR] Tree update failed: {te}\n")
                             break
                    
                    if not found:
                         self.append_output(f"[NO MATCH] {item['name'][:30]}... (key: {item_name_clean[:10]})\n")
                         try:
                             tree_item = self.batch_cp_tree.get_children()[item['index']]
                             self.batch_cp_tree.item(tree_item, values=(item['name'], "Unknown", "Not found in scan"))
                         except: pass

            except Exception as e:
                self.append_output(f"❌ Scan Error: {e}\n")

            self.append_output("\n=== BATCH PROCESS COMPLETE ===\n")
            messagebox.showinfo("Done", "Batch Check Completed!")

        threading.Thread(target=worker, daemon=True).start()

    def run_batch_scan_recent(self):
        """Run standalone scan of recent videos"""
        profile_name = self.api_profile_var.get()
        channel_id = self.batch_cp_channel_entry.get()
        
        self.text_output.delete(1.0, tk.END)
        self.append_output(f"=== CHECKING RECENT UPLOADS ===\nAccount: {profile_name}\nChannel: {channel_id}\n\n")
        
        def worker():
            try:
                cmd = [
                    sys.executable,
                    "scripts/3_copyright_check.py",
                    "--mode", "scan",
                    "--profile", profile_name
                ]
                if channel_id:
                    cmd.extend(["--channel-id", channel_id])
                
                process = subprocess.Popen(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.STDOUT, 
                    text=True, 
                    cwd=os.getcwd(),
                    bufsize=1,
                    universal_newlines=True
                )
                
                for line in process.stdout:
                    line = line.strip()
                    if line:
                        keyword = ""
                        if "[ALERT]" in line or "COPYRIGHT" in line:
                             keyword = "❌"
                        elif "[SUCCESS]" in line or "CLEAN" in line:
                             keyword = "✅"
                        elif "[INFO]" in line:
                             keyword = "ℹ️"
                             
                        self.append_output(f"{keyword} {line}\n")
                
                process.wait()
                self.append_output("\n=== SCAN COMPLETE ===\n")
                
            except Exception as e:
                self.append_output(f"\n❌ Error: {e}\n")
        
        threading.Thread(target=worker, daemon=True).start()

    def update_batch_presets(self):
        """Update the preset list in Batch tab from loaded settings"""
        if hasattr(self, 'batch_combo_presets'):
            preset_names = list(self.presets.keys())
            self.batch_combo_presets['values'] = preset_names
            if preset_names:
                self.batch_combo_presets.current(0)

    def batch_load_preset(self, event=None):
        """Load selected preset prompt into batch entry"""
        name = self.batch_preset_var.get()
        if name in self.presets:
            prompt = self.presets[name]
            self.batch_entry_prompt.delete(0, tk.END)
            self.batch_entry_prompt.insert(0, prompt)

    def run_remix(self, test_mode=False, remix_only=False):
        song_path = self.entry_song_path.get()
        song_name = self.entry_song_name.get()
        channel_id = self.entry_channel_id.get()
        # style = self.style_var.get() removed

        if not song_path or not song_name or not channel_id:
            messagebox.showerror("Error", "Please fill in all fields")
            return
        
        # Require prompt now since style is gone
        custom_prompt = self.entry_prompt.get()
        if not custom_prompt:
             messagebox.showerror("Error", "Please enter a Prompt/Style description")
             return

        self.text_output.delete(1.0, tk.END)
        self.append_output(f"Starting remix process (Remix Only: {remix_only})...\n")

        def worker():
            try:
                cmd = [
                    sys.executable,
                    "scripts/2_remix_with_suno_advanced.py",
                    song_path,
                    "--song-name", song_name,
                    "--channel-id", channel_id,
                    # "--style", style removed
                ]
                
                # Add custom prompt if present
                custom_prompt = self.entry_prompt.get()
                if custom_prompt:
                    cmd.extend(["--prompt", custom_prompt])
                    # Save settings when running
                    self.save_settings()

                if remix_only:
                    cmd.append("--remix-only")
                
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=os.getcwd())

                for line in iter(process.stdout.readline, ''):
                    self.append_output(line)
                
                process.stdout.close()
                process.wait()
                
                if process.returncode == 0:
                    self.append_output("\nProcess completed successfully!\n")
                else:
                    self.append_output("\nProcess failed.\n")

            except Exception as e:
                self.append_output(f"\nError: {str(e)}\n")

        threading.Thread(target=worker).start()

    def start_login_thread(self):
        self.login_btn.config(state=tk.DISABLED, text="Opening Browser...")
        threading.Thread(target=self.perform_login, daemon=True).start()

    def perform_login(self):
        automation = None
        try:
            self.update_status("Starting Chrome...", "blue")
            
            automation = SunoBrowserAutomation(
                headless=False,
                user_data_dir=self.user_data_dir
            )
            
            self.update_status("Navigating to Suno...", "blue")
            automation.navigate_to_suno()
            
            self.update_status("Waiting for manual login...", "orange")
            result = automation.wait_for_login(timeout=600)
            
            if result:
                # Extract and Save Cookies
                self.update_status("Login Detected! Extracting cookies...", "blue")
                cookie_str = automation.get_cookies_as_string()
                
                if cookie_str:
                    self.save_cookies_to_env(cookie_str)
                    self.update_status("Login Success! Cookies Saved.", "green")
                    messagebox.showinfo("Success", "Login successful!\nCookies have been saved to .env file.")
                else:
                    self.update_status("Login Success, but failed to extract cookies.", "orange")
            else:
                self.update_status("Login Timeout.", "red")

        except Exception as e:
            self.update_status(f"Error: {str(e)}", "red")
            messagebox.showerror("System Error", str(e))
        
        finally:
            self.root.after(0, lambda: self.login_btn.config(state=tk.NORMAL, text="Login Suno (First Time)"))
            if automation:
                automation.close()

    def save_cookies_to_env(self, cookie_str):
        env_path = ".env"
        new_lines = []
        cookie_found = False
        
        try:
            if os.path.exists(env_path):
                with open(env_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    for line in lines:
                        if line.startswith("SUNO_COOKIE="):
                            new_lines.append(f"SUNO_COOKIE=\"{cookie_str}\"\n")
                            cookie_found = True
                        else:
                            new_lines.append(line)
            
            if not cookie_found:
                new_lines.append(f"\nSUNO_COOKIE=\"{cookie_str}\"\n")
                
            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
                
            self.append_output(f"Updated .env with new cookies.")
            
        except Exception as e:
            self.append_output(f"Failed to save cookies to .env: {e}")

    def refresh_api_profiles(self):
        """Load available API profiles into combobox."""
        try:
            # Lazy import to avoid circular dependency issues at top level
            sys.path.append(os.path.join(os.getcwd(), 'scripts')) 
            from modules.youtube_auth import list_available_profiles
            
            profiles = list_available_profiles()
            self.api_profile_combo['values'] = profiles
            
            # Keep current selection if valid, else default
            current = self.api_profile_var.get()
            if current not in profiles and profiles:
                self.api_profile_var.set(profiles[0])
            elif not current and profiles:
                self.api_profile_var.set('default')
                
        except Exception as e:
            logger.error(f"Failed to refresh profiles: {e}")

    def add_api_account(self):
        """Import a new client_secret json file as an account."""
        file_path = filedialog.askopenfilename(
            title="Select Client Secret JSON",
            filetypes=[("JSON Files", "*.json")]
        )
        if not file_path:
            return
            
        # Ask for a name
        from tkinter import simpledialog
        name = simpledialog.askstring("Account Name", "Enter a name for this account (e.g. account2):")
        if not name: 
            return
            
        # Sanitize name
        safe_name = "".join([c for c in name if c.isalnum() or c in (' ', '_', '-')]).strip()
        if not safe_name:
            messagebox.showerror("Error", "Invalid name")
            return

        # Copy to credentials folder
        try:
            import shutil
            dest_dir = os.path.join(os.getcwd(), 'credentials')
            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir)
                
            dest_path = os.path.join(dest_dir, f"{safe_name}.json")
            if os.path.exists(dest_path):
                if not messagebox.askyesno("Confirm", f"Account '{safe_name}' already exists. Overwrite?"):
                    return
            
            shutil.copy2(file_path, dest_path)
            messagebox.showinfo("Success", f"Account '{safe_name}' added! Please select it and run a check to authorize.")
            self.refresh_api_profiles()
            self.api_profile_var.set(safe_name)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add account: {e}")

    def verify_api_account(self):
        """Launch external script to verify auth."""
        try:
            script_path = os.path.abspath(os.path.join("scripts", "check_auth.py"))
            
            if sys.platform == 'win32':
                # Open in new CMD window so user can interact/login
                # Use CREATE_NEW_CONSOLE (0x10) to spawn independent window
                subprocess.Popen(
                    [sys.executable, script_path],
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                    cwd=os.getcwd()
                )
            else:
                messagebox.showinfo("Info", "Please run scripts/check_auth.py in terminal")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def update_status(self, text, color):
        self.root.after(0, lambda: self.login_status.config(text=f"Status: {text}", fg=color))

    def load_settings(self):
        try:
            if os.path.exists("settings.json"):
                with open("settings.json", "r", encoding='utf-8') as f:
                    import json
                    data = json.load(f)
                    
                    # Load Current Prompt
                    if "custom_prompt" in data:
                        self.entry_prompt.delete(0, tk.END)
                        self.entry_prompt.insert(0, data["custom_prompt"])
                    
                    # Load Presets
                    self.presets = data.get("presets", {})
                    self.update_preset_combo()
                    
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")

    def save_settings(self):
        try:
            data = {}
            # Try to preserve existing data (like presets) if we are just calling save_settings for the prompt
            if os.path.exists("settings.json"):
                try:
                    with open("settings.json", "r", encoding='utf-8') as f:
                        import json
                        data = json.load(f)
                except:
                    pass
            
            data["custom_prompt"] = self.entry_prompt.get()
            data["presets"] = self.presets
            
            with open("settings.json", "w", encoding='utf-8') as f:
                import json
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

    # --- Preset Management ---
    def update_preset_combo(self):
        names = list(self.presets.keys())
        self.combo_presets['values'] = names
        if names:
            self.combo_presets.current(0)

    def save_preset_dialog(self):
        from tkinter import simpledialog
        prompt_content = self.entry_prompt.get()
        if not prompt_content:
            messagebox.showwarning("Warning", "Prompt is empty!")
            return
            
        name = simpledialog.askstring("Save Preset", "Enter name for this prompt preset:")
        if name:
            self.presets[name] = prompt_content
            self.save_settings()
            self.update_preset_combo()
            self.preset_var.set(name)
            messagebox.showinfo("Success", f"Saved preset '{name}'")

    def load_preset_selection(self, event):
        name = self.preset_var.get()
        if name in self.presets:
            content = self.presets[name]
            self.entry_prompt.delete(0, tk.END)
            self.entry_prompt.insert(0, content)

    def delete_preset(self):
        name = self.preset_var.get()
        if name and name in self.presets:
            if messagebox.askyesno("Confirm", f"Delete preset '{name}'?"):
                del self.presets[name]
                self.save_settings()
                self.update_preset_combo()
                self.entry_prompt.delete(0, tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = SunoApp(root)
    root.mainloop()
