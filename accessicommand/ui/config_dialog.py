# accessicommand/ui/config_dialog.py
import tkinter as tk
from tkinter import ttk, messagebox, font # Import font
import traceback

# --- Imports ---
try:
    from accessicommand.actions.registry import get_available_action_ids
    # Import event constants directly from detectors
    # Assuming detectors export these lists or constants
    from accessicommand.detectors.facial_detector import (
        LEFT_BLINK_EVENT, RIGHT_BLINK_EVENT, MOUTH_OPEN_START_EVENT, MOUTH_OPEN_STOP_EVENT,
        BOTH_EYES_CLOSED_START_EVENT, BOTH_EYES_CLOSED_STOP_EVENT, EYEBROWS_RAISED_START_EVENT,
        EYEBROWS_RAISED_STOP_EVENT, HEAD_TILT_LEFT_START_EVENT, HEAD_TILT_LEFT_STOP_EVENT,
        HEAD_TILT_RIGHT_START_EVENT, HEAD_TILT_RIGHT_STOP_EVENT
    )
    FACE_EVENT_LIST = sorted([ # Define list locally if not exported
        LEFT_BLINK_EVENT, RIGHT_BLINK_EVENT, MOUTH_OPEN_START_EVENT, MOUTH_OPEN_STOP_EVENT,
        BOTH_EYES_CLOSED_START_EVENT, BOTH_EYES_CLOSED_STOP_EVENT, EYEBROWS_RAISED_START_EVENT,
        EYEBROWS_RAISED_STOP_EVENT, HEAD_TILT_LEFT_START_EVENT, HEAD_TILT_LEFT_STOP_EVENT,
        HEAD_TILT_RIGHT_START_EVENT, HEAD_TILT_RIGHT_STOP_EVENT
    ])
    try:
        from accessicommand.detectors.hand_detector import (
            OPEN_PALM_EVENT, FIST_EVENT, THUMBS_UP_EVENT, POINTING_INDEX_EVENT,
            VICTORY_EVENT, GESTURE_NONE_EVENT
        )
        HAND_EVENT_LIST = sorted([ # Define list locally
            OPEN_PALM_EVENT, FIST_EVENT, THUMBS_UP_EVENT, POINTING_INDEX_EVENT,
            VICTORY_EVENT # Exclude GESTURE_NONE_EVENT from dropdown
        ])
    except ImportError:
        print("WARN: Hand detector events not found for config dialog.")
        HAND_EVENT_LIST = ["DUMMY_HAND_EVENT"]
    _imports_valid = True
except ImportError as e:
    print(f"ERROR importing components in config_dialog.py: {e}")
    _imports_valid = False
    def get_available_action_ids(): return ["ACTION_NOT_FOUND"]
    FACE_EVENT_LIST = ["DUMMY_FACE_EVENT"]
    HAND_EVENT_LIST = ["DUMMY_HAND_EVENT"]

TRIGGER_TYPES = ["voice", "face", "hand"]


class ConfigDialog:
    """ Configuration dialog window using Tkinter/ttk. """
    # --- Corrected __init__ signature ---
    def __init__(self, parent, config_manager, engine, restart_signal_callback):
        if not _imports_valid: messagebox.showerror("Import Error", "Failed Config Dialog load."); return

        self.parent = parent
        self.config_manager = config_manager
        self.engine = engine
        # --- Store the callback ---
        self.signal_main_gui = restart_signal_callback # Use the passed callback

        self.top = tk.Toplevel(parent); self.top.title("Configure Bindings")
        self.top.configure(bg='#2E2E2E'); self.top.transient(parent); self.top.grab_set()

        # Fonts & Styling
        self.default_font=font.nametofont("TkDefaultFont"); self.default_font.configure(family="Segoe UI",size=10)
        self.button_font=font.Font(family="Segoe UI",size=10); self.heading_font=font.Font(family="Segoe UI",size=10,weight="bold")
        self.style=ttk.Style(); self.style.theme_use('clam')
        BG_COLOR='#2E2E2E'; FG_COLOR='#FFFFFF'; ACCENT_COLOR='#0078D7'; BUTTON_BG='#4A4A4A'; BUTTON_FG=FG_COLOR; BUTTON_ACTIVE_BG='#5A5A5A'; BUTTON_DISABLED_FG='#888888'; LABELFRAME_BG=BG_COLOR; LABELFRAME_FG=FG_COLOR; TREE_BG='#3C3C3C'; TREE_FG=FG_COLOR; TREE_FIELD_BG='#505050'; TREE_HEADING_BG='#4A4A4A'; TREE_HEADING_FG=FG_COLOR; ODD_ROW_BG=TREE_BG; EVEN_ROW_BG='#444444'
        self.style.configure('.', background=BG_COLOR, foreground=FG_COLOR, font=self.default_font)
        self.style.configure('TFrame', background=BG_COLOR); self.style.configure('TLabel', background=BG_COLOR, foreground=FG_COLOR)
        self.style.configure('TLabelframe', background=LABELFRAME_BG, borderwidth=1, relief=tk.GROOVE); self.style.configure('TLabelframe.Label', background=LABELFRAME_BG, foreground=LABELFRAME_FG, font=self.heading_font)
        self.style.configure('TButton', background=BUTTON_BG, foreground=BUTTON_FG, font=self.button_font, padding=(8, 4), borderwidth=1, relief=tk.FLAT)
        self.style.map('TButton', background=[('active', BUTTON_ACTIVE_BG), ('disabled', BG_COLOR)], foreground=[('disabled', BUTTON_DISABLED_FG)], relief=[('pressed', tk.SUNKEN), ('!pressed', tk.FLAT)])
        self.style.configure("Treeview", background=TREE_BG, foreground=TREE_FG, fieldbackground=TREE_FIELD_BG, rowheight=25)
        self.style.map("Treeview", background=[('selected', ACCENT_COLOR)], foreground=[('selected', FG_COLOR)])
        self.style.configure("Treeview.Heading", background=TREE_HEADING_BG, foreground=TREE_HEADING_FG, font=self.heading_font, relief=tk.FLAT, padding=(5,5))
        self.style.map("Treeview.Heading", relief=[('active', tk.GROOVE), ('!active', tk.FLAT)])
        self.style.configure('TCombobox', fieldbackground=TREE_FIELD_BG, background=BUTTON_BG, foreground=FG_COLOR, arrowcolor=FG_COLOR, selectbackground=ACCENT_COLOR, selectforeground=FG_COLOR)
        self.style.configure('TEntry', fieldbackground=TREE_FIELD_BG, foreground=FG_COLOR, insertcolor=FG_COLOR)

        self.current_bindings = []
        main_frame = ttk.Frame(self.top, padding="15", style='TFrame'); main_frame.pack(expand=True, fill=tk.BOTH)
        list_frame = ttk.LabelFrame(main_frame, text="Current Bindings", padding="10", style='TLabelframe'); list_frame.pack(pady=10, fill=tk.BOTH, expand=True)
        columns = ("type", "event", "action"); self.bindings_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=12); self.bindings_tree.heading("type", text="Type"); self.bindings_tree.heading("event", text="Event"); self.bindings_tree.heading("action", text="Action")
        self.bindings_tree.column("type", width=100, anchor=tk.W, stretch=False); self.bindings_tree.column("event", width=220, anchor=tk.W); self.bindings_tree.column("action", width=220, anchor=tk.W)
        self.bindings_tree.tag_configure('oddrow', background=ODD_ROW_BG, foreground=TREE_FG); self.bindings_tree.tag_configure('evenrow', background=EVEN_ROW_BG, foreground=TREE_FG)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.bindings_tree.yview); self.bindings_tree.configure(yscrollcommand=scrollbar.set)
        self.bindings_tree.grid(row=0, column=0, sticky="nsew"); scrollbar.grid(row=0, column=1, sticky="ns"); list_frame.rowconfigure(0, weight=1); list_frame.columnconfigure(0, weight=1)
        delete_button = ttk.Button(list_frame, text="Delete Selected", command=self._delete_selected_binding, style='TButton'); delete_button.grid(row=1, column=0, columnspan=2, pady=(10,0), sticky="e")
        add_frame = ttk.LabelFrame(main_frame, text="Add New Binding", padding="10", style='TLabelframe'); add_frame.pack(pady=10, fill=tk.X)
        ttk.Label(add_frame, text="Type:", style='TLabel').grid(row=0, column=0, padx=5, pady=5, sticky=tk.W); ttk.Label(add_frame, text="Event:", style='TLabel').grid(row=1, column=0, padx=5, pady=5, sticky=tk.W); ttk.Label(add_frame, text="Action:", style='TLabel').grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.trigger_type_var = tk.StringVar(); self.trigger_type_combo = ttk.Combobox(add_frame, textvariable=self.trigger_type_var, values=TRIGGER_TYPES, state="readonly", width=18, style='TCombobox'); self.trigger_type_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW); self.trigger_type_combo.bind("<<ComboboxSelected>>", self._update_trigger_event_options)
        self.trigger_event_input_frame = ttk.Frame(add_frame, style='TFrame'); self.trigger_event_input_frame.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW); self.trigger_event_input_widget = None; self.trigger_event_var = tk.StringVar()
        self.action_id_var = tk.StringVar(); self.action_id_combo = ttk.Combobox(add_frame, textvariable=self.action_id_var, values=[], state="readonly", width=40, style='TCombobox'); self.action_id_combo.grid(row=2, column=1, padx=5, pady=5, sticky=tk.EW)
        add_button = ttk.Button(add_frame, text="Add Binding", command=self._add_binding, style='TButton'); add_button.grid(row=0, rowspan=3, column=2, padx=(15, 5), pady=5, sticky="ns")
        add_frame.columnconfigure(1, weight=1)
        button_frame = ttk.Frame(main_frame, style='TFrame'); button_frame.pack(pady=(15, 0), fill=tk.X, side=tk.BOTTOM)
        save_button = ttk.Button(button_frame, text="Save & Close", command=self._save_and_close, style='TButton'); save_button.pack(side=tk.RIGHT, padx=5)
        cancel_button = ttk.Button(button_frame, text="Cancel", command=self._cancel, style='TButton'); cancel_button.pack(side=tk.RIGHT)

        self._populate_action_dropdown(); self._load_bindings(); self._update_trigger_event_options()
        self.top.update_idletasks(); parent_geo = self.parent.geometry().split('+'); parent_x = int(parent_geo[1]); parent_y = int(parent_geo[2]); self.top.geometry(f"+{parent_x + 50}+{parent_y + 50}")

    def _load_bindings(self):
        try:
            for item in self.bindings_tree.get_children(): self.bindings_tree.delete(item)
            self.current_bindings = self.config_manager.get_bindings()
            for i, binding in enumerate(self.current_bindings):
                ttype=binding.get('trigger_type','?'); tevent=binding.get('trigger_event','?'); taction=binding.get('action_id','?')
                tag = 'evenrow' if i % 2 == 0 else 'oddrow'
                self.bindings_tree.insert("", tk.END, iid=str(i), values=(ttype, tevent, taction), tags=(tag,))
        except Exception as e: messagebox.showerror("Load Error", f"{e}"); traceback.print_exc()

    def _populate_action_dropdown(self):
        try:
            action_ids = get_available_action_ids(); self.action_id_combo['values'] = sorted(action_ids)
            if action_ids: self.action_id_combo.current(0)
        except Exception as e: messagebox.showerror("Action Load Error", f"{e}"); self.action_id_combo['values'] = []

    def _update_trigger_event_options(self, event=None):
        selected_type = self.trigger_type_var.get(); self.trigger_event_var.set("")
        if self.trigger_event_input_widget: self.trigger_event_input_widget.destroy(); self.trigger_event_input_widget = None
        if selected_type == "voice": self.trigger_event_input_widget = ttk.Entry(self.trigger_event_input_frame, textvariable=self.trigger_event_var, width=35, style='TEntry')
        elif selected_type == "face": self.trigger_event_input_widget = ttk.Combobox(self.trigger_event_input_frame, textvariable=self.trigger_event_var, values=FACE_EVENT_LIST, state="readonly", width=35, style='TCombobox');
        elif selected_type == "hand": self.trigger_event_input_widget = ttk.Combobox(self.trigger_event_input_frame, textvariable=self.trigger_event_var, values=HAND_EVENT_LIST, state="readonly", width=35, style='TCombobox');
        else: self.trigger_event_input_widget = ttk.Entry(self.trigger_event_input_frame, textvariable=self.trigger_event_var, state=tk.DISABLED, width=35, style='TEntry')
        if self.trigger_event_input_widget and selected_type in ("face", "hand"):
             if selected_type == "face" and FACE_EVENT_LIST: self.trigger_event_input_widget.current(0)
             if selected_type == "hand" and HAND_EVENT_LIST: self.trigger_event_input_widget.current(0)
        if self.trigger_event_input_widget: self.trigger_event_input_widget.pack(expand=True, fill=tk.X)

    def _add_binding(self):
        ttype=self.trigger_type_var.get(); tevent=self.trigger_event_var.get(); taction=self.action_id_var.get()
        if not ttype or not tevent or not taction: messagebox.showwarning("Missing Input", "Select Type, Event, Action."); return
        if ttype == "voice" and not tevent.strip(): messagebox.showwarning("Invalid Input", "Voice trigger required."); return
        new_binding = {"trigger_type":ttype, "trigger_event":tevent.lower().strip(), "action_id":taction}
        self.current_bindings.append(new_binding); new_iid = str(len(self.current_bindings) - 1)
        tag = 'evenrow' if (len(self.current_bindings) - 1) % 2 == 0 else 'oddrow'
        self.bindings_tree.insert("",tk.END, iid=new_iid, values=(new_binding["trigger_type"], new_binding["trigger_event"], new_binding["action_id"]), tags=(tag,))
        self.bindings_tree.see(new_iid); print(f"GUI: Added binding - {new_binding}")

    def _delete_selected_binding(self):
        selected_items = self.bindings_tree.selection()
        if not selected_items: messagebox.showwarning("No Selection", "Select bindings to delete."); return
        if messagebox.askyesno("Confirm Delete", f"Delete {len(selected_items)} binding(s)?"):
            indices_to_delete = sorted([int(iid) for iid in selected_items], reverse=True)
            deleted_count = 0
            try:
                for index in indices_to_delete:
                    if 0 <= index < len(self.current_bindings): removed = self.current_bindings.pop(index); print(f"GUI: Deleted - {removed}"); deleted_count += 1
                    else: print(f"WARN: Index {index} out of bounds.")
                if deleted_count > 0: self._load_bindings() # Reload treeview
                else: messagebox.showerror("Delete Error", "Could not delete items.");
            except ValueError: messagebox.showerror("Delete Error", "Invalid selection."); print("ERROR: Invalid index during delete.")
            except Exception as e: messagebox.showerror("Delete Error", f"{e}"); traceback.print_exc()

    # --- Corrected _save_and_close ---
    def _save_and_close(self):
        """Saves bindings, stops engine, signals main GUI, and closes."""
        print("GUI: Save & Close requested.")
        if self.current_bindings is None: print("ERROR: Bindings list is None."); return

        print(f"GUI: Saving {len(self.current_bindings)} bindings...")
        try:
            save_success = self.config_manager.set_bindings(self.current_bindings)
            if save_success:
                print("GUI: Config save successful.")
                if self.engine and self.engine.is_running:
                    print("GUI: Stopping engine after save...")
                    try: self.engine.stop()
                    except Exception as stop_e: print(f"ERROR stopping engine: {stop_e}")

                # Signal the main GUI that changes were saved and engine stopped
                if callable(self.signal_main_gui): # Check if callback exists
                     print("GUI: Signaling main window for state update.")
                     self.signal_main_gui() # Call the callback passed from main_window
                else:
                     print("WARN: No signal callback available to update main GUI state.")

                messagebox.showinfo("Saved", "Bindings saved.\nPlease click 'Start Engine' on the main window to apply changes.")
                self.top.destroy() # Close this dialog
            else:
                messagebox.showerror("Save Error", "Failed to save bindings.\nCheck console.")
        except Exception as e:
            print(f"ERROR during save/close: {e}"); traceback.print_exc()
            messagebox.showerror("Save Error", f"Unexpected error:\n{e}")
    # --- END Correction ---

    def _cancel(self):
        print("GUI: Configuration cancelled.")
        self.top.destroy()