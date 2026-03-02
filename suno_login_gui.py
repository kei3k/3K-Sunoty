import tkinter as tk
from tkinter import messagebox
import os
import threading
from selenium_suno import SunoBrowserAutomation
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SunoLoginGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Suno Login Tool")
        self.root.geometry("400x250")
        
        # Center the window
        self.center_window()

        # Styling
        self.bg_color = "#f0f0f0"
        self.root.configure(bg=self.bg_color)
        
        # Header
        self.header_label = tk.Label(
            root, 
            text="Suno Basic Login", 
            font=("Arial", 16, "bold"),
            bg=self.bg_color
        )
        self.header_label.pack(pady=20)

        # Status
        self.status_label = tk.Label(
            root, 
            text="Trạng thái: Chưa đăng nhập", 
            font=("Arial", 10),
            bg=self.bg_color,
            fg="gray"
        )
        self.status_label.pack(pady=10)

        # Login Button
        self.login_btn = tk.Button(
            root, 
            text="Đăng Nhập Lần Đầu (Login First Time)", 
            command=self.start_login_thread,
            font=("Arial", 12),
            bg="#4CAF50",
            fg="white",
            padx=10,
            pady=5,
            relief=tk.RAISED
        )
        self.login_btn.pack(pady=20)

        # User Data Directory (Persistence)
        self.user_data_dir = os.path.join(os.getcwd(), "chrome_profile")
        if not os.path.exists(self.user_data_dir):
            os.makedirs(self.user_data_dir)

    def center_window(self):
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def start_login_thread(self):
        """Start login in a separate thread to keep GUI responsive"""
        self.login_btn.config(state=tk.DISABLED, text="Đang mở trình duyệt...")
        threading.Thread(target=self.perform_login, daemon=True).start()

    def perform_login(self):
        automation = None
        try:
            self.update_status("Đang khởi động Chrome...", "blue")
            
            # Initialize with persistent profile
            automation = SunoBrowserAutomation(
                headless=False,
                user_data_dir=self.user_data_dir
            )
            
            self.update_status("Đang truy cập Suno.ai...", "blue")
            automation.navigate_to_suno()
            
            self.update_status("Vui lòng đăng nhập thủ công...", "orange")
            result = automation.wait_for_login(timeout=600)  # 10 minutes timeout
            
            if result:
                self.update_status("Đăng nhập thành công! ✅", "green")
                messagebox.showinfo("Thành công", "Đã phát hiện đăng nhập! Cookie đã được lưu.")
            else:
                self.update_status("Hết thời gian chờ đăng nhập.", "red")
                messagebox.showerror("Lỗi", "Hết thời gian chờ đăng nhập.")

        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            self.update_status(f"Lỗi: {str(e)}", "red")
            messagebox.showerror("Lỗi hệ thống", str(e))
        
        finally:
            self.root.after(0, lambda: self.login_btn.config(state=tk.NORMAL, text="Đăng Nhập Lần Đầu (Login First Time)"))
            if automation:
                # We typically want to keep it open or close it? 
                # For login tool, maybe close it after success or let user close it.
                # Let's ask user or just close it to save state cleanly.
                automation.close()

    def update_status(self, text, color):
        self.root.after(0, lambda: self.status_label.config(text=f"Trạng thái: {text}", fg=color))

if __name__ == "__main__":
    root = tk.Tk()
    app = SunoLoginGUI(root)
    root.mainloop()
