# accessicommand/ui/main_window.py
import tkinter as tk
from tkinter import ttk, messagebox, font  # Import font module

try:
    from .config_dialog import ConfigDialog
    _config_dialog_imported = True
except ImportError:
    print("ERROR: Could not import ConfigDialog from ui.config_dialog")
    _config_dialog_imported = False

class AppGUI:
    """ Main application window using Tkinter. """
    # --- Pass the callback needed by ConfigDialog ---
    def __init__(self, root, engine, config_manager): # Remove restart_callback, not needed here
        self.root = root
        self.engine = engine
        self.config_manager = config_manager

        self.root.title("AccessiCommand")
        self.root.configure(bg='#2E2E2E') # Dark background for the root window

        # --- Define Fonts ---
        self.default_font = font.nametofont("TkDefaultFont")
        self.default_font.configure(family="Segoe UI", size=10) # Cleaner default font
        self.status_font = font.Font(family="Segoe UI", size=11, weight="bold")
        self.button_font = font.Font(family="Segoe UI", size=10, weight="bold")
        # --- Define heading_font needed for style ---
        self.heading_font = font.Font(family="Segoe UI", size=10, weight="bold")

        # --- Styling ---
        self.style = ttk.Style()
        self.style.theme_use('clam') # Or 'alt', 'default', 'vista', etc.

        # Define Colors
        BG_COLOR = '#2E2E2E'; FG_COLOR = '#FFFFFF'; ACCENT_COLOR = '#0078D7'; BUTTON_BG = '#4A4A4A'; BUTTON_FG = FG_COLOR; BUTTON_ACTIVE_BG = '#5A5A5A'; BUTTON_DISABLED_FG = '#888888'; LABELFRAME_BG = BG_COLOR; LABELFRAME_FG = FG_COLOR

        # Configure Styles
        self.style.configure('.', background=BG_COLOR, foreground=FG_COLOR, font=self.default_font)
        self.style.configure('TFrame', background=BG_COLOR)
        self.style.configure('TLabel', background=BG_COLOR, foreground=FG_COLOR)
        self.style.configure('TLabelframe', background=LABELFRAME_BG, borderwidth=1, relief=tk.GROOVE)
        # --- Use the defined heading_font ---
        self.style.configure('TLabelframe.Label', background=LABELFRAME_BG, foreground=LABELFRAME_FG, font=self.heading_font)

        self.style.configure('TButton', background=BUTTON_BG, foreground=BUTTON_FG, font=self.button_font, padding=(10, 5), borderwidth=1, relief=tk.FLAT)
        self.style.map('TButton', background=[('active', BUTTON_ACTIVE_BG), ('disabled', BG_COLOR)], foreground=[('disabled', BUTTON_DISABLED_FG)], relief=[('pressed', tk.SUNKEN), ('!pressed', tk.FLAT)])

        # --- Main Frame ---
        self.main_frame = ttk.Frame(self.root, padding="15 15 15 15", style='TFrame')
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1); self.root.rowconfigure(0, weight=1)

        # Status Label
        self.status_var = tk.StringVar(value="Status: Idle"); self.status_label = ttk.Label(self.main_frame, textvariable=self.status_var, font=self.status_font, style='TLabel', anchor=tk.W); self.status_label.grid(row=0, column=0, columnspan=2, sticky=tk.EW, pady=(0, 15))

        # Control Buttons Frame
        button_frame = ttk.Frame(self.main_frame, style='TFrame'); button_frame.grid(row=1, column=0, columnspan=2, pady=5, sticky=tk.EW)
        self.start_button = ttk.Button(button_frame, text="START ENGINE", command=self.start_engine, style='TButton', width=18); self.start_button.pack(side=tk.LEFT, padx=(0, 5), expand=True, fill=tk.X)
        self.stop_button = ttk.Button(button_frame, text="STOP ENGINE", command=self.stop_engine, state=tk.DISABLED, style='TButton', width=18); self.stop_button.pack(side=tk.LEFT, padx=(5, 0), expand=True, fill=tk.X)

        # Configuration Button
        self.config_button = ttk.Button(self.main_frame, text="CONFIGURE BINDINGS", command=self.open_configuration, style='TButton'); self.config_button.grid(row=2, column=0, columnspan=2, padx=0, pady=(15, 5), sticky=tk.EW)

        print("GUI Initialized with new style.")

    def update_status(self, message):
        self.status_var.set(f"Status: {message}"); print(f"GUI Status: {message}")

    def start_engine(self):
        print("GUI: Start button pressed.")
        if self.engine:
            if self.engine.is_running: print("GUI: Engine already running."); return
            try:
                print("GUI: Calling engine.start() (will reload/re-init if needed)...")
                self.engine.start() # Engine's start handles re-init now
                if self.engine.is_running:
                    self.update_status("Running"); self.start_button.config(state=tk.DISABLED); self.stop_button.config(state=tk.NORMAL); self.config_button.config(state=tk.DISABLED)
                else: # Start might fail (e.g., no camera)
                    messagebox.showerror("Start Error", "Engine start completed but failed to activate detectors. Check logs."); self.update_status("Error Starting"); self.start_button.config(state=tk.NORMAL); self.stop_button.config(state=tk.DISABLED); self.config_button.config(state=tk.NORMAL)
            except Exception as e: messagebox.showerror("Start Error", f"{e}"); self.update_status("Error Starting"); self.start_button.config(state=tk.NORMAL); self.stop_button.config(state=tk.DISABLED); self.config_button.config(state=tk.NORMAL)
        else: messagebox.showerror("Start Error", "Engine instance unavailable.")

    def stop_engine(self):
        print("GUI: Stop button pressed.")
        if self.engine and self.engine.is_running:
            try:
                print("GUI: Calling engine.stop()..."); self.engine.stop(); self.update_status("Stopped"); self.start_button.config(state=tk.NORMAL); self.stop_button.config(state=tk.DISABLED); self.config_button.config(state=tk.NORMAL)
            except Exception as e: messagebox.showerror("Stop Error", f"{e}"); self.update_status("Error Stopping")
        else: print("GUI: Engine not running or unavailable.")

    # --- CORRECTED open_configuration ---
    def open_configuration(self):
        """Opens the configuration dialog window."""
        print("GUI: Configure button pressed.")
        if _config_dialog_imported:
            # Pass the callback method from this instance
            config_dialog = ConfigDialog(self.root, self.config_manager, self.engine, self.signal_config_saved)
            print("GUI: ConfigDialog opened.")
        else:
            messagebox.showerror("Error", "Config dialog failed to import.")
    # --- END CORRECTION ---

    # --- Method called by ConfigDialog ---
    def signal_config_saved(self):
        """Called by ConfigDialog after successful save and engine stop."""
        print("GUI: Received signal: config saved, engine stopped.")
        self.update_status("Config Saved. Ready to Start.")
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.config_button.config(state=tk.NORMAL)

    def on_close(self):
        print("GUI: Window closing...")
        if self.engine and self.engine.is_running: self.stop_engine()
        self.root.destroy()