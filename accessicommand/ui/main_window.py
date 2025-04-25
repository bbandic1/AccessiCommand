# accessicommand/ui/main_window.py
import tkinter as tk
from tkinter import ttk, messagebox
# --- Import the dialog class ---
# Make sure this relative import works based on your structure
# (It should if main.py adds the project root to sys.path)
try:
    from .config_dialog import ConfigDialog
    _config_dialog_imported = True
except ImportError:
    print("ERROR: Could not import ConfigDialog from ui.config_dialog")
    _config_dialog_imported = False


class AppGUI:
    """ Main application window using Tkinter. """
    def __init__(self, root, engine, config_manager):
        """
        Initializes the main GUI window.

        Args:
            root (tk.Tk): The root Tkinter window.
            engine (Engine): The application's core engine instance.
            config_manager (ConfigManager): The configuration manager instance.
        """
        self.root = root
        self.engine = engine
        self.config_manager = config_manager # Store config manager

        self.root.title("AccessiCommand")
        self.style = ttk.Style(); self.style.theme_use('clam')
        self.main_frame = ttk.Frame(self.root, padding="10 10 10 10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1); self.root.rowconfigure(0, weight=1)

        # Status Label
        self.status_var = tk.StringVar(value="Status: Idle")
        self.status_label = ttk.Label(self.main_frame, textvariable=self.status_var, font=("Segoe UI", 10))
        self.status_label.grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 10))

        # Control Buttons
        self.start_button = ttk.Button(self.main_frame, text="Start Engine", command=self.start_engine)
        self.start_button.grid(row=1, column=0, padx=5, pady=5, sticky=tk.EW)
        self.stop_button = ttk.Button(self.main_frame, text="Stop Engine", command=self.stop_engine, state=tk.DISABLED)
        self.stop_button.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)

        # Configuration Button
        self.config_button = ttk.Button(self.main_frame, text="Configure Bindings", command=self.open_configuration) # Use descriptive text
        self.config_button.grid(row=2, column=0, columnspan=2, padx=5, pady=10, sticky=tk.EW)

        self.main_frame.columnconfigure(0, weight=1); self.main_frame.columnconfigure(1, weight=1)
        print("GUI Initialized.")

    def update_status(self, message):
        """Updates the status label."""
        self.status_var.set(f"Status: {message}")
        print(f"GUI Status: {message}")

    def start_engine(self):
        """Starts the engine and updates button states."""
        print("GUI: Start button pressed.")
        try:
            self.engine.start()
            self.update_status("Running")
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.config_button.config(state=tk.DISABLED) # Disable config while running
        except Exception as e:
            messagebox.showerror("Engine Start Error", f"Failed to start engine:\n{e}")
            self.update_status("Error Starting")

    def stop_engine(self):
        """Stops the engine and updates button states."""
        print("GUI: Stop button pressed.")
        try:
            self.engine.stop()
            self.update_status("Stopped")
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.config_button.config(state=tk.NORMAL) # Re-enable config
        except Exception as e:
            messagebox.showerror("Engine Stop Error", f"Error stopping engine:\n{e}")
            self.update_status("Error Stopping")

    # --- CORRECTED METHOD ---
    def open_configuration(self):
        """Opens the configuration dialog window."""
        print("GUI: Configure button pressed.")
        if _config_dialog_imported:
            # Create and show the dialog, passing necessary components
            # The dialog is modal (grab_set) so execution implicitly waits here
            config_dialog = ConfigDialog(self.root, self.config_manager, self.engine)
            # Optional: wait for the window to be destroyed if needed, but grab_set usually handles modality
            # self.root.wait_window(config_dialog.top)
            print("GUI: ConfigDialog closed.") # Log when it returns
        else:
            # Fallback if import failed
            messagebox.showerror("Error", "Configuration dialog component failed to import.\nCheck console logs.")
    # ------------------------

    def on_close(self):
        """Handles window closing: stops the engine first."""
        print("GUI: Window closing...")
        if self.engine and self.engine.is_running: # Check if engine exists and is running
            self.stop_engine()
        self.root.destroy()