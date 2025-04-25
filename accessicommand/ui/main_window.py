# accessicommand/ui/main_window.py
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox # For showing messages

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
        self.config_manager = config_manager # Store config manager for later use

        self.root.title("AccessiCommand")
        # self.root.geometry("350x150") # Optional: Set initial size

        # --- Styling ---
        self.style = ttk.Style()
        self.style.theme_use('clam') # Or 'alt', 'default', 'vista', etc.

        # --- Main Frame ---
        self.main_frame = ttk.Frame(self.root, padding="10 10 10 10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # --- Status Label ---
        self.status_var = tk.StringVar(value="Status: Idle")
        self.status_label = ttk.Label(self.main_frame, textvariable=self.status_var, font=("Segoe UI", 10))
        self.status_label.grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 10))

        # --- Control Buttons ---
        self.start_button = ttk.Button(self.main_frame, text="Start Engine", command=self.start_engine)
        self.start_button.grid(row=1, column=0, padx=5, pady=5, sticky=tk.EW)

        self.stop_button = ttk.Button(self.main_frame, text="Stop Engine", command=self.stop_engine, state=tk.DISABLED)
        self.stop_button.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)

        # --- Configuration Button (Placeholder) ---
        self.config_button = ttk.Button(self.main_frame, text="Configure...", command=self.open_configuration)
        self.config_button.grid(row=2, column=0, columnspan=2, padx=5, pady=10, sticky=tk.EW)

        # --- Make columns expandable ---
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.columnconfigure(1, weight=1)

        print("GUI Initialized.")

    def update_status(self, message):
        """Updates the status label."""
        self.status_var.set(f"Status: {message}")
        print(f"GUI Status: {message}")

    def start_engine(self):
        """Starts the engine and updates button states."""
        print("GUI: Start button pressed.")
        try:
            self.engine.start() # Call the engine's start method
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
            self.engine.stop() # Call the engine's stop method
            self.update_status("Stopped")
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.config_button.config(state=tk.NORMAL) # Re-enable config when stopped
        except Exception as e:
            messagebox.showerror("Engine Stop Error", f"Error stopping engine:\n{e}")
            self.update_status("Error Stopping")

    def open_configuration(self):
        """Opens the configuration window (placeholder)."""
        # --- TODO: Implement Configuration Window ---
        print("GUI: Configure button pressed (Not implemented yet).")
        messagebox.showinfo("Configure", "Configuration window not yet implemented.")
        # Example:
        # config_win = tk.Toplevel(self.root)
        # config_ui = ConfigDialog(config_win, self.config_manager, self.engine) # Pass manager and engine
        # -------------------------------------------

    def on_close(self):
        """Handles window closing: stops the engine first."""
        print("GUI: Window closing...")
        if self.engine.is_running:
            self.stop_engine() # Attempt graceful stop
        self.root.destroy() # Close the window