import tkinter as tk
from tkinter import scrolledtext, font
import threading
import os
import sys

# Import our bot module directly
import bot

class IORedirector:
    def __init__(self, text_widget, root):
        self.text_widget = text_widget
        self.root = root

    def write(self, message):
        # We must route insertions to the main Tkinter thread
        self.root.after(0, self.append_text, message)

    def append_text(self, message):
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.insert(tk.END, message)
        self.text_widget.see(tk.END)
        self.text_widget.config(state=tk.DISABLED)

    def flush(self):
        pass

class BotLauncherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Discord Attendance Bot Launcher")
        self.root.geometry("600x450")
        self.root.configure(bg="#2b2d31")
        
        self.bot_thread = None
        
        # UI Styling
        self.bg_color = "#2b2d31"
        self.fg_color = "#dbdee1"
        self.btn_start_color = "#23a559"
        self.btn_stop_color = "#da373c"
        
        custom_font = font.Font(family="Helvetica", size=12)
        title_font = font.Font(family="Helvetica", size=16, weight="bold")
        
        # Header
        header = tk.Label(root, text="Discord Attendance Bot", font=title_font, bg=self.bg_color, fg="white", pady=15)
        header.pack()
        
        # Buttons Frame
        btn_frame = tk.Frame(root, bg=self.bg_color)
        btn_frame.pack(pady=10)
        
        self.start_btn = tk.Button(btn_frame, text="▶ Start Bot", font=custom_font, bg=self.btn_start_color, fg="white", 
                                   activebackground="#1d8749", activeforeground="white", width=15, relief="flat", command=self.start_bot)
        self.start_btn.pack(side=tk.LEFT, padx=10)
        
        self.stop_btn = tk.Button(btn_frame, text="⏹ Stop Bot", font=custom_font, bg=self.btn_stop_color, fg="white", 
                                  activebackground="#a1282c", activeforeground="white", width=15, relief="flat", command=self.stop_bot, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=10)
        
        # Status Label
        self.status_label = tk.Label(root, text="Status: OFFLINE", font=custom_font, bg=self.bg_color, fg="#80848e")
        self.status_label.pack(pady=5)
        
        # Logs Terminal
        log_label = tk.Label(root, text="System Logs:", font=font.Font(family="Helvetica", size=10), bg=self.bg_color, fg=self.fg_color)
        log_label.pack(anchor="w", padx=20)
        
        self.log_area = scrolledtext.ScrolledText(root, height=12, bg="#1e1f22", fg="#dbdee1", font=("Consolas", 10), relief="flat")
        self.log_area.pack(padx=20, pady=5, fill=tk.BOTH, expand=True)
        self.log_area.config(state=tk.DISABLED)
        
        # Redirect stdout and stderr so print() calls go to our UI log_area
        self.io_redirector = IORedirector(self.log_area, self.root)
        sys.stdout = self.io_redirector
        sys.stderr = self.io_redirector
        
        print("Ready. Click 'Start Bot' to bring the bot online.\n")

    def start_bot(self):
        if self.bot_thread is None or not self.bot_thread.is_alive():
            self.start_btn.config(state=tk.DISABLED, bg="#1e1f22", fg="#80848e")
            self.stop_btn.config(state=tk.NORMAL, bg=self.btn_stop_color, fg="white")
            self.status_label.config(text="Status: RUNNING", fg=self.btn_start_color)
            
            # Start the bot in a separate thread so the GUI remains responsive
            self.bot_thread = threading.Thread(target=self.run_bot_thread, daemon=True)
            self.bot_thread.start()

    def run_bot_thread(self):
        try:
            bot.start_bot()
        except Exception as e:
            print(f"Error starting bot: {e}\n")
        finally:
            self.root.after(0, self.bot_finished)

    def stop_bot(self):
        if self.bot_thread and self.bot_thread.is_alive():
            print("Stopping bot...\n")
            # Signal the bot to stop safely
            try:
                bot.stop_bot()
            except Exception as e:
                print(f"Error while stopping bot: {e}")

    def bot_finished(self):
        self.reset_ui()

    def reset_ui(self):
        self.bot_thread = None
        self.start_btn.config(state=tk.NORMAL, bg=self.btn_start_color, fg="white")
        self.stop_btn.config(state=tk.DISABLED, bg="#1e1f22", fg="#80848e")
        self.status_label.config(text="Status: OFFLINE", fg="#80848e")

def main():
    root = tk.Tk()
    app = BotLauncherApp(root)
    
    # Handle window close event
    def on_closing():
        if app.bot_thread and app.bot_thread.is_alive():
            app.stop_bot()
            root.after(2000, root.destroy) # Wait slightly for orderly shutdown
        else:
            root.destroy()
            
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
