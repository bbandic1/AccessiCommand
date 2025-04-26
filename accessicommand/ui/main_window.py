# accessicommand/ui/main_window.py
import tkinter as tk
from tkinter import ttk, messagebox, font

try:
    from .config_dialog import ConfigDialog
    _config_dialog_imported = True
except ImportError: print("ERROR importing ConfigDialog"); _config_dialog_imported = False
import sys # For exiting application (optional)

class AppGUI:
    """ Main application window using Tkinter. """
    def __init__(self, root, engine, config_manager): # Engine passed in
        self.root = root
        self.engine = engine # Store engine reference
        self.config_manager = config_manager

        # --- Styling (Keep your 'pretty' styling code here) ---
        self.root.title("AccessiCommand"); self.root.configure(bg='#2E2E2E')
        self.default_font=font.nametofont("TkDefaultFont"); self.default_font.configure(family="Segoe UI",size=10)
        self.button_font=font.Font(family="Segoe UI",size=10); self.heading_font=font.Font(family="Segoe UI",size=10,weight="bold"); self.status_font = font.Font(family="Segoe UI", size=11, weight="bold")
        self.style=ttk.Style(); self.style.theme_use('clam')
        BG_COLOR='#2E2E2E'; FG_COLOR='#FFFFFF'; ACCENT_COLOR='#0078D7'; BUTTON_BG='#4A4A4A'; BUTTON_FG=FG_COLOR; BUTTON_ACTIVE_BG='#5A5A5A'; BUTTON_DISABLED_FG='#888888'; LABELFRAME_BG=BG_COLOR; LABELFRAME_FG=FG_COLOR; TREE_BG='#3C3C3C'; TREE_FG=FG_COLOR; TREE_FIELD_BG='#505050'; TREE_HEADING_BG='#4A4A4A'; TREE_HEADING_FG=FG_COLOR; ODD_ROW_BG=TREE_BG; EVEN_ROW_BG='#444444'
        self.style.configure('.', background=BG_COLOR, foreground=FG_COLOR, font=self.default_font)
        self.style.configure('TFrame', background=BG_COLOR); self.style.configure('TLabel', background=BG_COLOR, foreground=FG_COLOR)
        self.style.configure('TLabelframe', background=LABELFRAME_BG, borderwidth=1, relief=tk.GROOVE); self.style.configure('TLabelframe.Label', background=LABELFRAME_BG, foreground=LABELFRAME_FG, font=self.heading_font)
        self.style.configure('TButton', background=BUTTON_BG, foreground=BUTTON_FG, font=self.button_font, padding=(10, 5), borderwidth=1, relief=tk.FLAT)
        self.style.map('TButton', background=[('active', BUTTON_ACTIVE_BG), ('disabled', BG_COLOR)], foreground=[('disabled', BUTTON_DISABLED_FG)], relief=[('pressed', tk.SUNKEN), ('!pressed', tk.FLAT)])

        # --- UI Layout ---
        self.main_frame = ttk.Frame(self.root, padding="15 15 15 15", style='TFrame'); self.main_frame.grid(row=0, column=0, sticky="nsew"); self.root.columnconfigure(0, weight=1); self.root.rowconfigure(0, weight=1)
        self.status_var = tk.StringVar(value="Status: Idle"); self.status_label = ttk.Label(self.main_frame, textvariable=self.status_var, font=self.status_font, style='TLabel', anchor=tk.W); self.status_label.grid(row=0, column=0, columnspan=2, sticky=tk.EW, pady=(0, 15))
        button_frame = ttk.Frame(self.main_frame, style='TFrame'); button_frame.grid(row=1, column=0, columnspan=2, pady=5, sticky=tk.EW)
        self.start_button = ttk.Button(button_frame, text="START ENGINE", command=self.start_engine, style='TButton', width=18); self.start_button.pack(side=tk.LEFT, padx=(0, 5), expand=True, fill=tk.X)
        self.stop_button = ttk.Button(button_frame, text="STOP ENGINE", command=self.stop_engine, state=tk.DISABLED, style='TButton', width=18); self.stop_button.pack(side=tk.LEFT, padx=(5, 0), expand=True, fill=tk.X)
        self.config_button = ttk.Button(self.main_frame, text="CONFIGURE BINDINGS", command=self.open_configuration, style='TButton'); self.config_button.grid(row=2, column=0, columnspan=2, padx=0, pady=(15, 5), sticky=tk.EW)

        print("GUI Initialized.")

    def update_status(self, message):
        self.status_var.set(f"Status: {message}"); print(f"GUI Status: {message}")

    def start_engine(self):
        print("GUI: Start button pressed.")
        if self.engine:
            if self.engine.is_running: print("GUI: Engine already running."); return
            try:
                print("GUI: Calling engine.start()..."); self.engine.start()
                if self.engine.is_running: self.update_status("Running"); self.start_button.config(state=tk.DISABLED); self.stop_button.config(state=tk.NORMAL); self.config_button.config(state=tk.DISABLED)
                else: messagebox.showerror("Start Error", "Engine start failed."); self.update_status("Error Starting"); self._reset_buttons()
            except Exception as e: messagebox.showerror("Start Error", f"{e}"); self.update_status("Error Starting"); self._reset_buttons()
        else: messagebox.showerror("Start Error", "Engine unavailable.")

    def stop_engine(self):
        print("GUI: Stop button pressed.")
        if self.engine and self.engine.is_running:
            try: print("GUI: Calling engine.stop()..."); self.engine.stop(); self._reset_buttons()
            except Exception as e: messagebox.showerror("Stop Error", f"{e}"); self.update_status("Error Stopping")
        else: print("GUI: Engine not running or unavailable.")

    def _reset_buttons(self):
        """Helper to set buttons to the stopped state."""
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.config_button.config(state=tk.NORMAL)
        self.update_status("Stopped / Ready") # Or just "Stopped"

    def open_configuration(self):
        print("GUI: Configure button pressed.")
        if _config_dialog_imported:
            # ConfigDialog now needs signal callback
            config_dialog = ConfigDialog(self.root, self.config_manager, self.engine, self.signal_config_saved)
        else: messagebox.showerror("Error", "Config dialog failed to import.")

    def signal_config_saved(self):
        """Called by ConfigDialog after save and engine stop."""
        print("GUI: Config saved signal received.")
        self._reset_buttons() # Set buttons to stopped state
        self.update_status("Config Saved. Ready to Start.")

# --- In AppGUI class ---
        # --- In AppGUI class ---
    def execute_ui_command(self, command_phrase):
        """Parses and executes commands directed at the GUI."""
        print(f"GUI: Received UI command phrase: '{command_phrase}'")
        command = command_phrase.lower().strip()
        try:
            # Get current button states for checking
            start_state = str(self.start_button.cget('state')) # Get state as string for reliable comparison
            stop_state = str(self.stop_button.cget('state'))
            config_state = str(self.config_button.cget('state'))
            print(f"DEBUG GUI: Matching '{command}'. Btn States: Start={start_state}, Stop={stop_state}, Config={config_state}") # Log states

            # --- Check for START command ---
            # Only invoke if start button is currently enabled ('normal')
            if ("start" in command or "run" in command or "activate" in command):
                print(f"DEBUG GUI: Checking START condition. Start state is '{start_state}'.") # Explicit check
                if start_state == tk.NORMAL:
                    print("GUI Action: Invoking Start Button via voice")
                    self.start_button.invoke() # Simulate button click
                else:
                    print("GUI Info: Start button is disabled, cannot invoke via voice.")
                return # Processed this intent

            # --- Check for STOP command ---
            # Only invoke if stop button is currently enabled ('normal')
            elif ("stop" in command or "pause" in command or "halt" in command):
                print(f"DEBUG GUI: Checking STOP condition. Stop state is '{stop_state}'.") # Explicit check
                if stop_state == tk.NORMAL:
                    print("GUI Action: Invoking Stop Button via voice")
                    self.stop_button.invoke()
                else:
                    print("GUI Info: Stop button is disabled, cannot invoke via voice.")
                return # Processed this intent

            # --- Check for CONFIG command ---
            # Only invoke if config button is currently enabled ('normal')
            elif ("config" in command or "setting" in command or "binding" in command or "option" in command):
                 print(f"DEBUG GUI: Checking CONFIG condition. Config state is '{config_state}'.") # Explicit check
                 if config_state == tk.NORMAL:
                     print("GUI Action: Invoking Configure Button via voice")
                     self.config_button.invoke()
                 else:
                     print("GUI Info: Configure button is disabled, cannot invoke via voice.")
                 return # Processed this intent

            # --- Check for CLOSE command ---
            elif "close" in command or "exit" in command or "quit" in command:
                 print("GUI Action: Closing application via voice")
                 self.on_close() # Call the close handler
                 return # Processed this intent

            # --- If no known command matched ---
            else:
                 print(f"GUI Warn: No matching keywords or target button disabled for command: '{command}'")


        except Exception as e:
            print(f"ERROR executing UI command '{command}': {e}")
            traceback.print_exc()
            self.update_status("Error in UI command")

    def on_close(self): # Keep as before
        print("GUI: Window closing...")
        if self.engine and self.engine.is_running: self.stop_engine()
        self.root.destroy()