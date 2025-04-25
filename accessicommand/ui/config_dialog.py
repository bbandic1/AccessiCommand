# accessicommand/ui/config_dialog.py
import tkinter as tk
from tkinter import ttk, messagebox
import traceback

# --- Import necessary components ---
# Need registry to get available actions
# Need detector event constants for dropdowns
try:
    from accessicommand.actions.registry import get_available_action_ids
    # Import event constants directly from detectors for dropdown population
    from accessicommand.detectors.facial_detector import (
        LEFT_BLINK_EVENT, RIGHT_BLINK_EVENT, MOUTH_OPEN_START_EVENT, MOUTH_OPEN_STOP_EVENT,
        BOTH_EYES_CLOSED_START_EVENT, BOTH_EYES_CLOSED_STOP_EVENT, EYEBROWS_RAISED_START_EVENT,
        EYEBROWS_RAISED_STOP_EVENT, HEAD_TILT_LEFT_START_EVENT, HEAD_TILT_LEFT_STOP_EVENT,
        HEAD_TILT_RIGHT_START_EVENT, HEAD_TILT_RIGHT_STOP_EVENT
    )
    from accessicommand.detectors.hand_detector import (
        OPEN_PALM_EVENT, FIST_EVENT, THUMBS_UP_EVENT, POINTING_INDEX_EVENT,
        VICTORY_EVENT, GESTURE_NONE_EVENT
    )
    _imports_valid = True
except ImportError as e:
    print(f"ERROR importing components in config_dialog.py: {e}")
    print("       Ensure all detector and registry files exist and imports are correct.")
    _imports_valid = False
    # Define dummy values if imports fail, so GUI can still load partially
    def get_available_action_ids(): return ["ACTION_NOT_FOUND"]
    LEFT_BLINK_EVENT="DUMMY_LEFT_BLINK"; RIGHT_BLINK_EVENT="DUMMY_RIGHT_BLINK" # etc.
    OPEN_PALM_EVENT="DUMMY_OPEN_PALM"; FIST_EVENT="DUMMY_FIST" # etc.


# --- Define Event Lists for Dropdowns ---
# Consolidate known event strings from detectors
FACE_EVENT_LIST = sorted([
    LEFT_BLINK_EVENT, RIGHT_BLINK_EVENT, MOUTH_OPEN_START_EVENT, MOUTH_OPEN_STOP_EVENT,
    BOTH_EYES_CLOSED_START_EVENT, BOTH_EYES_CLOSED_STOP_EVENT, EYEBROWS_RAISED_START_EVENT,
    EYEBROWS_RAISED_STOP_EVENT, HEAD_TILT_LEFT_START_EVENT, HEAD_TILT_LEFT_STOP_EVENT,
    HEAD_TILT_RIGHT_START_EVENT, HEAD_TILT_RIGHT_STOP_EVENT
])
HAND_EVENT_LIST = sorted([
    OPEN_PALM_EVENT, FIST_EVENT, THUMBS_UP_EVENT, POINTING_INDEX_EVENT,
    VICTORY_EVENT, GESTURE_NONE_EVENT # Include NONE? Maybe not, user shouldn't bind to 'None'.
])
# Remove NONE for user selection
if GESTURE_NONE_EVENT in HAND_EVENT_LIST:
    HAND_EVENT_LIST.remove(GESTURE_NONE_EVENT)

TRIGGER_TYPES = ["voice", "face", "hand"]


class ConfigDialog:
    """ Configuration dialog window using Tkinter/ttk. """
    def __init__(self, parent, config_manager, engine):
        """
        Args:
            parent (tk.Tk or tk.Toplevel): The parent window.
            config_manager (ConfigManager): Instance for loading/saving config.
            engine (Engine): Instance for triggering reloads.
        """
        if not _imports_valid:
            messagebox.showerror("Import Error", "Failed to load required components for Config Dialog.")
            return

        self.parent = parent
        self.config_manager = config_manager
        self.engine = engine

        # Create a Toplevel window (a separate window)
        self.top = tk.Toplevel(parent)
        self.top.title("Configure Bindings")
        self.top.transient(parent) # Keep it on top of the parent
        self.top.grab_set() # Make it modal (block interaction with parent)
        # self.top.geometry("600x500") # Optional: Adjust size

        # --- Internal list to hold bindings being edited ---
        self.current_bindings = [] # Start empty, load later

        # --- Main Frame ---
        main_frame = ttk.Frame(self.top, padding="10")
        main_frame.pack(expand=True, fill=tk.BOTH)

        # --- Bindings List Section ---
        list_frame = ttk.LabelFrame(main_frame, text="Current Bindings", padding="10")
        list_frame.pack(pady=10, fill=tk.BOTH, expand=True)

        # Treeview setup
        columns = ("type", "event", "action")
        self.bindings_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=10)
        self.bindings_tree.heading("type", text="Trigger Type")
        self.bindings_tree.heading("event", text="Trigger Event")
        self.bindings_tree.heading("action", text="Action ID")
        self.bindings_tree.column("type", width=80, anchor=tk.W)
        self.bindings_tree.column("event", width=200, anchor=tk.W)
        self.bindings_tree.column("action", width=200, anchor=tk.W)

        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.bindings_tree.yview)
        self.bindings_tree.configure(yscrollcommand=scrollbar.set)

        self.bindings_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        # Delete Button
        delete_button = ttk.Button(list_frame, text="Delete Selected", command=self._delete_selected_binding)
        delete_button.grid(row=1, column=0, columnspan=2, pady=(5,0), sticky="e")

        # --- Add Binding Section ---
        add_frame = ttk.LabelFrame(main_frame, text="Add New Binding", padding="10")
        add_frame.pack(pady=10, fill=tk.X)

        # Labels
        ttk.Label(add_frame, text="Type:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Label(add_frame, text="Event:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Label(add_frame, text="Action:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)

        # Inputs
        self.trigger_type_var = tk.StringVar()
        self.trigger_type_combo = ttk.Combobox(add_frame, textvariable=self.trigger_type_var,
                                               values=TRIGGER_TYPES, state="readonly", width=15)
        self.trigger_type_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        self.trigger_type_combo.bind("<<ComboboxSelected>>", self._update_trigger_event_options)

        # Frame to hold either Entry or Combobox for Trigger Event
        self.trigger_event_input_frame = ttk.Frame(add_frame)
        self.trigger_event_input_frame.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)
        self.trigger_event_input_widget = None # Placeholder for Entry or Combobox
        self.trigger_event_var = tk.StringVar() # Variable for the input widget

        self.action_id_var = tk.StringVar()
        self.action_id_combo = ttk.Combobox(add_frame, textvariable=self.action_id_var,
                                            values=[], state="readonly", width=35) # Populate later
        self.action_id_combo.grid(row=2, column=1, padx=5, pady=5, sticky=tk.EW)

        # Add Button
        add_button = ttk.Button(add_frame, text="Add Binding", command=self._add_binding)
        add_button.grid(row=3, column=1, padx=5, pady=(10, 5), sticky=tk.E)

        add_frame.columnconfigure(1, weight=1) # Make input column expandable

        # --- Bottom Buttons (Save/Cancel) ---
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10, fill=tk.X, side=tk.BOTTOM)

        save_button = ttk.Button(button_frame, text="Save & Close", command=self._save_and_close)
        save_button.pack(side=tk.RIGHT, padx=5)

        cancel_button = ttk.Button(button_frame, text="Cancel", command=self._cancel)
        cancel_button.pack(side=tk.RIGHT)

        # --- Initial Population ---
        self._populate_action_dropdown()
        self._load_bindings()
        self._update_trigger_event_options() # Set initial state of event input

        # Center window
        self.top.update_idletasks() # Ensure window size is calculated
        parent_geo = self.parent.geometry().split('+')
        parent_x = int(parent_geo[1])
        parent_y = int(parent_geo[2])
        win_width = self.top.winfo_width()
        win_height = self.top.winfo_height()
        self.top.geometry(f"+{parent_x + 50}+{parent_y + 50}") # Position relative to parent

    def _load_bindings(self):
        """Loads bindings from config manager and populates treeview."""
        try:
            # Clear existing tree items
            for item in self.bindings_tree.get_children():
                self.bindings_tree.delete(item)

            self.current_bindings = self.config_manager.get_bindings() # Get fresh list
            # Sort for consistent display? Optional.
            # self.current_bindings.sort(key=lambda x: (x.get('trigger_type',''), x.get('trigger_event','')))

            for i, binding in enumerate(self.current_bindings):
                # Use get() with defaults for safety
                ttype = binding.get('trigger_type', 'N/A')
                tevent = binding.get('trigger_event', 'N/A')
                taction = binding.get('action_id', 'N/A')
                # Use index 'i' as the item ID for easy reference later
                self.bindings_tree.insert("", tk.END, iid=str(i), values=(ttype, tevent, taction))

        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load bindings:\n{e}")
            traceback.print_exc()

    def _populate_action_dropdown(self):
        """Populates the Action ID combobox."""
        try:
            action_ids = get_available_action_ids()
            self.action_id_combo['values'] = sorted(action_ids)
            if action_ids:
                self.action_id_combo.current(0) # Select first item by default
        except Exception as e:
            messagebox.showerror("Action Load Error", f"Failed to get action IDs:\n{e}")
            self.action_id_combo['values'] = []

    def _update_trigger_event_options(self, event=None):
        """Updates the Trigger Event input based on Trigger Type selection."""
        selected_type = self.trigger_type_var.get()
        self.trigger_event_var.set("") # Clear previous value

        # Remove the old widget if it exists
        if self.trigger_event_input_widget:
            self.trigger_event_input_widget.destroy()
            self.trigger_event_input_widget = None

        # Create new widget based on type
        if selected_type == "voice":
            self.trigger_event_input_widget = ttk.Entry(self.trigger_event_input_frame,
                                                        textvariable=self.trigger_event_var, width=35)
        elif selected_type == "face":
            self.trigger_event_input_widget = ttk.Combobox(self.trigger_event_input_frame,
                                                           textvariable=self.trigger_event_var,
                                                           values=FACE_EVENT_LIST, state="readonly", width=35)
            if FACE_EVENT_LIST: self.trigger_event_input_widget.current(0)
        elif selected_type == "hand":
            self.trigger_event_input_widget = ttk.Combobox(self.trigger_event_input_frame,
                                                           textvariable=self.trigger_event_var,
                                                           values=HAND_EVENT_LIST, state="readonly", width=35)
            if HAND_EVENT_LIST: self.trigger_event_input_widget.current(0)
        else: # Default or empty selection
             self.trigger_event_input_widget = ttk.Entry(self.trigger_event_input_frame,
                                                         textvariable=self.trigger_event_var, state=tk.DISABLED, width=35)

        if self.trigger_event_input_widget:
            self.trigger_event_input_widget.pack(expand=True, fill=tk.X)

    def _add_binding(self):
        """Adds a new binding to the internal list and updates the treeview."""
        ttype = self.trigger_type_var.get()
        tevent = self.trigger_event_var.get()
        taction = self.action_id_var.get()

        if not ttype or not tevent or not taction:
            messagebox.showwarning("Missing Input", "Please select/enter values for Type, Event, and Action.")
            return

        # Basic validation (add more complex checks if needed)
        if ttype == "voice" and not tevent.strip():
             messagebox.showwarning("Invalid Input", "Voice trigger event cannot be empty.")
             return

        # Create new binding dict
        new_binding = {
            "trigger_type": ttype,
            "trigger_event": tevent.lower().strip(), # Store voice events lowercase and stripped
            "action_id": taction
        }

        # Check for duplicates? Optional, depends on desired behavior.
        # for existing in self.current_bindings:
        #     if existing['trigger_type'] == new_binding['trigger_type'] and \
        #        existing['trigger_event'] == new_binding['trigger_event']:
        #         if messagebox.askyesno("Duplicate Trigger", f"A binding for {ttype} -> {tevent} already exists. Overwrite?"):
        #              # Find index and replace? Or just prevent duplicates?
        #              pass # For now, allow duplicates
        #         else:
        #              return

        # Add to internal list
        self.current_bindings.append(new_binding)

        # Add to treeview (use new list length - 1 as index/iid)
        new_iid = str(len(self.current_bindings) - 1)
        self.bindings_tree.insert("", tk.END, iid=new_iid,
                                  values=(new_binding["trigger_type"],
                                          new_binding["trigger_event"],
                                          new_binding["action_id"]))
        self.bindings_tree.see(new_iid) # Scroll to the new item

        # Clear input fields (optional)
        # self.trigger_event_var.set("")
        # self.action_id_combo.set("") # Or set back to default
        # self.trigger_type_combo.set("") # Or set back to default

        print(f"GUI: Added binding - {new_binding}")

    def _delete_selected_binding(self):
        """Deletes the selected binding(s) from the list and treeview."""
        selected_items = self.bindings_tree.selection() # Get tuple of selected item IDs (our indices)
        if not selected_items:
            messagebox.showwarning("No Selection", "Please select one or more bindings to delete.")
            return

        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete {len(selected_items)} selected binding(s)?"):
            # Need to delete from internal list based on treeview iid (which we set as index)
            # Iterate backwards through selected indices to avoid messing up indices during deletion
            indices_to_delete = sorted([int(iid) for iid in selected_items], reverse=True)

            deleted_count = 0
            for index in indices_to_delete:
                if 0 <= index < len(self.current_bindings):
                    removed = self.current_bindings.pop(index)
                    print(f"GUI: Deleted binding - {removed}")
                    deleted_count += 1
                else:
                    print(f"WARN: Index {index} out of bounds for internal bindings list.")

            # Reload the entire treeview from the modified internal list
            # This correctly handles shifting indices after deletion
            if deleted_count > 0:
                self._load_bindings() # Reload will use the updated self.current_bindings
            else:
                 messagebox.showerror("Delete Error", "Could not delete selected items (index mismatch?).")


    def _save_and_close(self):
        """Saves the current bindings to the config file and closes."""
        print("GUI: Saving configuration...")
        try:
            success = self.config_manager.set_bindings(self.current_bindings)
            if success:
                print("GUI: Configuration saved successfully.")
                messagebox.showinfo("Saved", "Bindings saved successfully.")
                # Trigger engine reload *after* saving and before closing
                if self.engine:
                    print("GUI: Requesting engine configuration reload.")
                    try:
                        # Run reload in a separate thread to avoid blocking GUI?
                        # For now, run directly - might cause slight UI freeze if reload is slow
                        self.engine.reload_configuration()
                    except Exception as reload_e:
                         messagebox.showerror("Reload Error", f"Failed to trigger engine reload:\n{reload_e}")
                self.top.destroy() # Close the dialog
            else:
                messagebox.showerror("Save Error", "Failed to save bindings to the configuration file.")
        except Exception as e:
            messagebox.showerror("Save Error", f"An unexpected error occurred during save:\n{e}")
            traceback.print_exc()

    def _cancel(self):
        """Closes the dialog without saving."""
        print("GUI: Configuration cancelled.")
        self.top.destroy()