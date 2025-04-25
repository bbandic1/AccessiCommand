# listeners.py / voice_controller.py (Save as appropriate name)
import speech_recognition as sr
import pyautogui
import threading
import time
import queue # Kept import, though not used in this version for simplicity
import traceback # Import traceback at the top

# --- Configuration Constants ---
# You might move these to a config file later
DEFAULT_PAUSE_THRESHOLD = 0.4 # Seconds. Lower = faster response, but more likely to cut off mid-phrase. Adjust based on testing.
DEFAULT_ENERGY_THRESHOLD = 350 # Adjust if needed based on mic sensitivity / background noise
PHRASE_TIME_LIMIT = 3         # Max seconds to record AFTER speech starts. Keep it short for commands.
WHISPER_MODEL = "tiny.en"     # Fastest English-only model. Options: tiny.en, base.en, small.en, medium.en (larger = slower but more accurate)
ACTION_DELAY = 0.02           # Tiny delay between consecutive actions triggered by speech (e.g., "go go") to help OS/games register them.

class VoiceListener:
    def __init__(self, action_map=None, energy_threshold=DEFAULT_ENERGY_THRESHOLD, pause_threshold=DEFAULT_PAUSE_THRESHOLD):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone() # Consider specifying device_index if multiple mics
        self.running = False
        self.thread = None
        self._is_listening = False # Flag to indicate active listening phase

        # --- Recognizer Settings ---
        self.recognizer.energy_threshold = energy_threshold
        self.recognizer.pause_threshold = pause_threshold
        # --- FIX: Explicitly set non_speaking_duration ---
        # Ensure it's valid and <= pause_threshold. Setting it equal is safe.
        self.recognizer.non_speaking_duration = pause_threshold
        # -------------------------------------------------
        self.recognizer.dynamic_energy_threshold = True # Keep this, can be helpful

        # --- Action Map ---
        if action_map is None:
            # Define your single-word trigger commands
            self.trigger_actions = {
                "record": lambda: pyautogui.press('space'),
                "next": lambda: pyautogui.press('down'),
                "back": lambda: pyautogui.press('left'),
                "go": lambda: pyautogui.press('right'),
                "select": lambda: pyautogui.press('enter'),
                "stop": lambda: pyautogui.press('esc'),
                # Add more single-word commands
            }
        else:
            # Ensure keys are lowercase if loading from external source
            self.trigger_actions = {k.lower(): v for k, v in action_map.items()}

        print("--- Voice Listener Initializing ---")
        print(f"Model: {WHISPER_MODEL}, Pause Threshold: {self.recognizer.pause_threshold}s, Non-Speaking Duration: {self.recognizer.non_speaking_duration}s") # Log both
        print(f"Commands: {list(self.trigger_actions.keys())}")
        print("Adjusting for ambient noise...")
        with self.microphone as source:
            try:
                # Adjust for ambient noise after setting all parameters
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            except Exception as e:
                print(f"WARN: Error adjusting for ambient noise: {e}. Using threshold: {self.recognizer.energy_threshold}")
        print(f"Ready. Adjusted energy threshold: {self.recognizer.energy_threshold:.2f}")
        print("------------------------------------")


    def _process_audio_and_act(self, audio_data):
        """Processes recognized audio."""
        try:
            # --- Use Whisper for Recognition ---
            recognized_text = self.recognizer.recognize_whisper(
                audio_data,
                model=WHISPER_MODEL,
                language="english"
            ).lower()

            # --- Clean text minimally and split into words ---
            cleaned_text = recognized_text.strip(" .,!?\"'\n\t")
            words = cleaned_text.split()

            if not words:
                print("Voice Listener: Heard silence or unintelligible.")
                return

            print(f"Voice Listener: Heard: '{cleaned_text}' (Words: {words})")

            action_performed_this_utterance = False
            # --- Process Words Sequentially ---
            for word in words:
                action = self.trigger_actions.get(word) # Direct dictionary lookup
                if action:
                    print(f"Action: Trigger word '{word}' -> Executing.")
                    try:
                        action() # Perform the action
                        action_performed_this_utterance = True
                        time.sleep(ACTION_DELAY) # Small delay for repeats
                    except Exception as action_e:
                        print(f"ERROR: executing action for '{word}': {action_e}")

            if not action_performed_this_utterance:
                print(f"Info: Heard '{cleaned_text}', but no matching command words found.")

        except sr.UnknownValueError:
            print("Voice Listener: Could not understand audio.")
        except sr.RequestError as e:
            print(f"ERROR: Could not request results (Network issue?): {e}")
        except Exception as e:
            print(f"ERROR: Unexpected error during recognition/action: {e}")
            # Keep traceback for debugging this part too
            print("--- Recognition/Action Traceback ---")
            traceback.print_exc()
            print("-----------------------------------")


    def _listen_loop(self):
        """The core listening loop running in a background thread."""
        print("Voice Listener: Background listening thread started.")
        while self.running:
            audio_data = None
            if not self.running: break # Exit loop cleanly if stop signal received

            try:
                # Ensure microphone is accessed safely
                with self.microphone as source:
                    print("Voice Listener: Waiting for phrase...")
                    self._is_listening = True
                    # Listen for audio data - This is where the AssertionError happened
                    audio_data = self.recognizer.listen(
                        source,
                        timeout=None, # Wait indefinitely for speech
                        phrase_time_limit=PHRASE_TIME_LIMIT
                    )
                    self._is_listening = False
                    print("Voice Listener: Processing speech...")

                # Process the captured audio if available and still running
                if audio_data and self.running:
                     self._process_audio_and_act(audio_data)

            except sr.WaitTimeoutError:
                self._is_listening = False
                continue # Should not happen with timeout=None
            except OSError as e:
                 self._is_listening = False
                 print(f"ERROR: Microphone OS Error: {e}. Check microphone connection/permissions.")
                 time.sleep(2) # Wait before retrying if mic error
            except Exception as e:
                self._is_listening = False
                # Print specific error and full traceback for debugging
                print(f"ERROR: Unexpected error in listening loop: {e}")
                print("--- Listening Loop Traceback ---")
                traceback.print_exc()
                print("-----------------------------")
                time.sleep(1) # Prevent rapid error looping

        print("Voice Listener: Background listening thread stopped.")

    def start(self):
        """Starts the listening thread."""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._listen_loop, daemon=True)
            self.thread.start()
            print("Voice Listener: Service started.")
        else:
            print("Voice Listener: Service already running.")

    def stop(self):
        """Stops the listening thread gracefully."""
        if self.running:
            print("Voice Listener: Stopping service...")
            self.running = False # Signal thread to stop
            if self.thread:
                # Wait a reasonable time for the thread to finish
                join_timeout = max(self.recognizer.pause_threshold * 2, 1.5) # Adjusted timeout slightly
                self.thread.join(timeout=join_timeout)
                if self.thread.is_alive():
                    print("WARN: Listener thread did not stop cleanly.")
            print("Voice Listener: Service stopped.")
        else:
            print("Voice Listener: Service already stopped.")


# --- Main execution block for direct testing ---
if __name__ == "__main__":
    print("--- Running Voice Listener Directly ---")

    # Create listener instance (using defaults or override here)
    listener = VoiceListener()
    # Example override: listener = VoiceListener(pause_threshold=0.35)

    listener.start()

    print("\nListener active. Speak commands.")
    print("Press Ctrl+C in this terminal to stop.")

    try:
        # Keep main thread alive while background thread runs
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nCtrl+C detected. Shutting down...")
    except Exception as main_e:
        print(f"\nERROR in main loop: {main_e}")
        print("--- Main Loop Traceback ---")
        traceback.print_exc()
        print("-------------------------")
    finally:
        # Ensure listener is stopped cleanly on exit
        listener.stop()
        print("--- Voice Listener script finished ---")