import os
import re
import threading
import tkinter as tk
from tkinter import filedialog, colorchooser, messagebox, ttk
from collections import Counter

class SVGRecolorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SVG Color Batcher")
        self.root.geometry("500x450")
        self.root.resizable(False, False)
        
        # Data State
        self.folder_path = ""
        self.svg_files = []
        self.color_counts = Counter()
        self.selected_original_color = tk.StringVar()
        self.target_color = "#FF0000" # Default red placeholder

        # Style configuration
        style = ttk.Style()
        style.configure("TButton", padding=6)
        style.configure("TLabel", padding=4)

        self._init_ui()

    def _init_ui(self):
        # --- Section 1: Folder Selection ---
        frame_top = ttk.LabelFrame(self.root, text="Source", padding=10)
        frame_top.pack(fill="x", padx=10, pady=5)

        self.btn_select = ttk.Button(frame_top, text="Select Folder", command=self.select_folder)
        self.btn_select.pack(side="left")

        self.lbl_path = ttk.Label(frame_top, text="No folder selected", foreground="gray")
        self.lbl_path.pack(side="left", padx=10, fill="x", expand=True)

        # --- Section 2: Analysis & Selection ---
        frame_mid = ttk.LabelFrame(self.root, text="Analysis", padding=10)
        frame_mid.pack(fill="both", expand=True, padx=10, pady=5)

        self.btn_analyze = ttk.Button(frame_mid, text="Find Top Colors", command=self.start_analysis, state="disabled")
        self.btn_analyze.pack(anchor="w")

        self.lbl_status = ttk.Label(frame_mid, text="Ready")
        self.lbl_status.pack(anchor="w", pady=(5, 0))

        self.progress = ttk.Progressbar(frame_mid, mode='indeterminate')
        
        # Color Radio Buttons Container
        self.frame_colors = ttk.Frame(frame_mid)
        self.frame_colors.pack(fill="both", expand=True, pady=10)

        # --- Section 3: Replacement ---
        frame_bot = ttk.LabelFrame(self.root, text="Actions", padding=10)
        frame_bot.pack(fill="x", padx=10, pady=10)

        # Target Color Picker
        frame_picker = ttk.Frame(frame_bot)
        frame_picker.pack(fill="x", pady=5)
        
        ttk.Label(frame_picker, text="Change to:").pack(side="left")
        self.lbl_preview = tk.Label(frame_picker, bg=self.target_color, width=4, relief="solid")
        self.lbl_preview.pack(side="left", padx=5)
        
        btn_pick = ttk.Button(frame_picker, text="Pick Color", command=self.pick_target_color)
        btn_pick.pack(side="left")

        # Execute Button
        self.btn_apply = ttk.Button(frame_bot, text="Replace & Save All", command=self.apply_changes, state="disabled")
        self.btn_apply.pack(side="right")

    def select_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.folder_path = path
            self.lbl_path.config(text=f".../{os.path.basename(path)}")
            self.lbl_path.configure(foreground="black")
            self.btn_analyze.config(state="normal")
            self.lbl_status.config(text="Folder loaded. Click 'Find Top Colors'.")
            # Reset previous data
            self.color_counts.clear()
            for widget in self.frame_colors.winfo_children():
                widget.destroy()

    def start_analysis(self):
        if not self.folder_path: 
            return
        
        self.btn_analyze.config(state="disabled")
        self.btn_select.config(state="disabled")
        self.progress.pack(fill="x", pady=5)
        self.progress.start(10)
        self.lbl_status.config(text="Scanning files...")
        
        # Run in thread to keep UI responsive
        threading.Thread(target=self._analyze_thread, daemon=True).start()

    def _analyze_thread(self):
        svgs = [f for f in os.listdir(self.folder_path) if f.lower().endswith('.svg')]
        self.svg_files = svgs
        
        temp_counter = Counter()
        # Regex to capture hex codes (6 or 3 digits). Case insensitive flag used later.
        # This ignores alpha channels (#RRGGBBAA) to keep it simple/standard, 
        # but captures standard web colors.
        hex_pattern = re.compile(r'#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b')

        for f in svgs:
            try:
                with open(os.path.join(self.folder_path, f), 'r', encoding='utf-8') as file:
                    content = file.read()
                    matches = hex_pattern.findall(content)
                    # Normalize to lowercase for counting, but we will handle replacement carefully
                    temp_counter.update([m.lower() for m in matches])
            except Exception:
                continue # Skip unreadable files

        self.root.after(0, self._analysis_complete, temp_counter)

    def _analysis_complete(self, counter):
        self.color_counts = counter
        self.progress.stop()
        self.progress.pack_forget()
        self.btn_analyze.config(state="normal")
        self.btn_select.config(state="normal")
        
        # Clear old radio buttons
        for widget in self.frame_colors.winfo_children():
            widget.destroy()

        top_3 = self.color_counts.most_common(3)
        
        if not top_3:
            self.lbl_status.config(text="No Hex colors found in SVGs.")
            return

        self.lbl_status.config(text=f"Found {sum(self.color_counts.values())} color instances.")
        
        ttk.Label(self.frame_colors, text="Select a color to replace:").pack(anchor="w", pady=(0,5))

        for color, count in top_3:
            row = ttk.Frame(self.frame_colors)
            row.pack(fill="x", pady=2)
            
            # Color swatch
            swatch = tk.Label(row, bg=color, width=3, relief="solid")
            swatch.pack(side="left", padx=(0, 10))
            
            # Radio button
            rb = ttk.Radiobutton(
                row, 
                text=f"{color.upper()} ({count} matches)", 
                variable=self.selected_original_color, 
                value=color
            )
            rb.pack(side="left")

        # Select the first one by default
        self.selected_original_color.set(top_3[0][0])
        self.btn_apply.config(state="normal")

    def pick_target_color(self):
        color = colorchooser.askcolor(title="Choose replacement color")[1]
        if color:
            self.target_color = color
            self.lbl_preview.config(bg=color)

    def apply_changes(self):
        orig = self.selected_original_color.get()
        target = self.target_color
        
        if not orig or not target: 
            return

        count_replaced = 0
        files_changed = 0

        # Case-insensitive replacement logic
        # We need to escape the hex string just in case, though usually safe
        pattern = re.compile(re.escape(orig), re.IGNORECASE)

        for f in self.svg_files:
            full_path = os.path.join(self.folder_path, f)
            try:
                with open(full_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                
                # Check if file has the color before writing to disk (saves IO)
                if pattern.search(content):
                    new_content, n = pattern.subn(target, content)
                    if n > 0:
                        with open(full_path, 'w', encoding='utf-8') as file:
                            file.write(new_content)
                        count_replaced += n
                        files_changed += 1
            except Exception as e:
                print(f"Error processing {f}: {e}")

        messagebox.showinfo(
            "Complete", 
            f"Replaced {count_replaced} instances in {files_changed} files.\n"
            f"Changed {orig.upper()} to {target.upper()}"
        )
        
        # Trigger re-analysis to update counts
        self.start_analysis()

if __name__ == "__main__":
    root = tk.Tk()
    # Set a higher scaling factor for high-DPI displays if needed
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
        
    app = SVGRecolorApp(root)
    root.mainloop()