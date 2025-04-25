# accessicommand/config/manager.py
import json
import os
import traceback

DEFAULT_CONFIG = {
    "bindings": [],
    "settings": {
        "voice_detector": {
            "pause_threshold": 0.4,
            "energy_threshold": 350
        },
        "facial_detector": {
            # Add default thresholds for face later
        }
    }
}

class ConfigManager:
    """Handles loading and saving application configuration from/to a JSON file."""

    def __init__(self, config_path="config.json"):
        """
        Initializes the ConfigManager.

        Args:
            config_path (str): The path to the configuration file.
        """
        self.config_path = config_path
        self.config_data = {}
        self._load_or_create_config()

    def _load_or_create_config(self):
        """Loads config from file or creates a default one if it doesn't exist."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config_data = json.load(f)
                print(f"ConfigManager: Configuration loaded from '{self.config_path}'")
                # Optional: Validate structure or merge with defaults if keys are missing
            except json.JSONDecodeError:
                print(f"ERROR: Invalid JSON in '{self.config_path}'. Using default config.")
                self.config_data = DEFAULT_CONFIG.copy()
                self._save_config() # Save the default one to fix the file
            except Exception as e:
                print(f"ERROR: Failed to load config file '{self.config_path}': {e}")
                traceback.print_exc()
                self.config_data = DEFAULT_CONFIG.copy() # Use default on other errors
        else:
            print(f"ConfigManager: Config file not found at '{self.config_path}'. Creating default.")
            self.config_data = DEFAULT_CONFIG.copy()
            self._save_config()

    def _save_config(self):
        """Saves the current configuration data to the file."""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=4) # Use indent for readability
            # print(f"ConfigManager: Configuration saved to '{self.config_path}'") # Can be noisy
            return True
        except Exception as e:
            print(f"ERROR: Failed to save config file '{self.config_path}': {e}")
            traceback.print_exc()
            return False

    def get_config(self):
        """Returns the entire loaded configuration dictionary."""
        return self.config_data

    def get_bindings(self):
        """Returns the list of bindings from the configuration."""
        # Ensure "bindings" key exists and is a list
        return self.config_data.get("bindings", [])

    def set_bindings(self, bindings_list):
        """
        Updates the bindings in the configuration data and saves the file.

        Args:
            bindings_list (list): The new list of binding dictionaries.

        Returns:
            bool: True if saving was successful, False otherwise.
        """
        if isinstance(bindings_list, list):
            self.config_data["bindings"] = bindings_list
            return self._save_config()
        else:
            print("ERROR: set_bindings requires a list.")
            return False

    def get_settings(self):
        """Returns the settings dictionary from the configuration."""
        return self.config_data.get("settings", {})

    def get_setting(self, key, default=None):
         """Gets a specific setting value, returning default if not found."""
         # Simple dot notation access could be added here for nested keys if needed
         return self.config_data.get("settings", {}).get(key, default)

    def update_setting(self, key, value):
        """
        Updates a specific setting in the configuration data and saves the file.

        Args:
            key (str): The key of the setting to update.
            value (any): The new value for the setting.

        Returns:
            bool: True if saving was successful, False otherwise.
        """
        if "settings" not in self.config_data:
            self.config_data["settings"] = {}
        self.config_data["settings"][key] = value
        return self._save_config()