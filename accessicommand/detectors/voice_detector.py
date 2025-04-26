# accessicommand/detectors/voice_detector.py
import speech_recognition as sr
import threading
import time
import traceback

# --- Constants ---
DEFAULT_PAUSE_THRESHOLD = 0.5 # Default pause threshold
DEFAULT_ENERGY_THRESHOLD = 350
PHRASE_TIME_LIMIT = 5 # Allow slightly longer phrases for UI commands
WHISPER_MODEL_SIZE = "tiny.en"

# --- Define UI Command Keywords (Hardcoded here for now) ---
# These are words that, if present, suggest the command is for the UI
UI_KEYWORDS = {"start", "stop", "config", "configuration", "settings", "bindings", "open", "click", "press", "engine", "window", "gui", "ui"}

class VoiceDetector:
    """
    Listens for speech, identifies UI commands vs system triggers,
    and emits events via a provided handler function.
    Uses Whisper for offline recognition.
    """
    def __init__(self, event_handler,
                 system_trigger_words, # Words for system actions bindings
                 energy_threshold=DEFAULT_ENERGY_THRESHOLD,
                 pause_threshold=DEFAULT_PAUSE_THRESHOLD,
                 device_index=None):
        """
        Initializes the VoiceDetector.

        Args:
            event_handler (callable): Function for emitting events.
                                      Signature: event_handler(type: str, data: any)
                                      Types: "voice" (system trigger), "ui_command" (raw phrase)
            system_trigger_words (list | set): Lowercase words/phrases for system bindings.
            energy_threshold (int): Mic sensitivity.
            pause_threshold (float): Silence duration to end phrase.
            device_index (int | None): Mic index.
        """
        # --- Initialization Logging ---
        print("[VD LOG] Initializing VoiceDetector...")
        self.recognizer = sr.Recognizer()
        mic_init_success = False
        try:
            print(f"[VD LOG] Attempting mic index: {device_index}")
            self.microphone = sr.Microphone(device_index=device_index)
            mic_init_success = True; print("[VD LOG] Microphone initialized.")
        except Exception as e:
            print(f"ERROR: Mic init failed (idx: {device_index}): {e}. Using default.")
            try: self.microphone = sr.Microphone(); mic_init_success = True; print("[VD LOG] Default microphone initialized.")
            except Exception as e_default: print(f"ERROR: Default mic init failed: {e_default}"); self.microphone = None

        self.running = False; self.thread = None; self._is_listening = False

        if not callable(event_handler): print("WARN [VD]: No valid event_handler. Events not emitted."); self.event_handler = lambda d, e: None
        else: self.event_handler = event_handler; print("[VD LOG] Event handler registered.")

        # Store SYSTEM trigger words
        self.system_trigger_words = set(str(word).lower() for word in system_trigger_words if isinstance(word, str) and word)
        if not self.system_trigger_words: print("WARN [VD]: No system trigger words provided.")
        else: print(f"[VD LOG] System Triggers: {sorted(list(self.system_trigger_words))}")

        # Log UI Keywords
        print(f"[VD LOG] UI Keywords: {sorted(list(UI_KEYWORDS))}")

        # Apply recognizer settings
        self.recognizer.energy_threshold = energy_threshold; self.recognizer.pause_threshold = pause_threshold
        self.recognizer.non_speaking_duration = pause_threshold; self.recognizer.dynamic_energy_threshold = True
        print(f"[VD LOG] Recognizer settings: energy={energy_threshold}, pause={pause_threshold}, non_speak={pause_threshold}, dynamic=True")

        # Ambient noise adjustment
        if mic_init_success:
            print("[VD LOG] Adjusting for ambient noise...")
            try:
                with self.microphone as source: self.recognizer.adjust_for_ambient_noise(source, duration=1)
                print(f"[VD LOG] Ambient noise adjusted. Energy threshold: {self.recognizer.energy_threshold:.2f}")
            except Exception as e: print(f"WARN [VD]: Adjust ambient noise failed: {e}.")
        else: print("WARN [VD]: Skipping ambient noise adjustment.")
        print("--- Voice Detector Initialized ---")
        # --- End Initialization Logging ---

    # --- ADDED BACK UI COMMAND LOGIC ---
    def _process_speech(self, audio_data):
        """ Processes audio, checks for UI keywords OR system triggers. """
        print("[VD LOG] Processing received audio data...")
        try:
            print(f"[VD LOG] Transcribing using Whisper model: {WHISPER_MODEL_SIZE}...")
            recognized_text = self.recognizer.recognize_whisper(
                audio_data, model=WHISPER_MODEL_SIZE, language="english"
            ).lower()
            cleaned_text = recognized_text.strip(" .,!?\"'\n\t")
            # Use a set of words for efficient checking
            words_set = set(cleaned_text.split())

            if not words_set: print("[VD LOG] Transcription empty."); return

            print(f"[VD LOG] Heard: '{cleaned_text}' (Word set: {words_set})")

            # --- Check for UI Keywords ---
            found_ui_keywords = words_set.intersection(UI_KEYWORDS)
            if found_ui_keywords:
                print(f"[VD LOG] Detected UI keywords: {found_ui_keywords}. Emitting full phrase as 'ui_command'.")
                try:
                    print(f"[VD LOG] Calling event handler: type='ui_command', data='{cleaned_text}'")
                    self.event_handler("ui_command", cleaned_text) # Send the whole phrase
                    print("[VD LOG] Event handler call completed for ui_command.")
                except Exception as handler_e: print(f"ERROR [VD]: UI event handler failed: {handler_e}"); traceback.print_exc()
                # --- IMPORTANT: Return after handling UI command to prevent system trigger check ---
                return
            else:
                print("[VD LOG] No UI keywords found in phrase.")

            # --- Check for System Trigger Words (only if no UI keywords found) ---
            processed_system_trigger = False
            # Use the original split order if needed, but set check is fine for individual words
            for word in cleaned_text.split(): # Iterate original order
                 cleaned_word = word.strip(".,!?\"'") # Clean individual word
                 if not cleaned_word: continue

                 if cleaned_word in self.system_trigger_words:
                     trigger_found_in_phrase = True # Flag that at least one trigger was found
                     print(f"[VD LOG] System trigger detected: '{cleaned_word}'")
                     try:
                         print(f"[VD LOG] Calling event handler: type='voice', data='{cleaned_word}'")
                         self.event_handler("voice", cleaned_word) # Emit specific trigger word
                         print(f"[VD LOG] Event handler call completed for '{cleaned_word}'.")
                         processed_system_trigger = True
                         # Decide: Process all triggers in phrase or just the first? Processing all now.
                     except Exception as handler_e: print(f"ERROR [VD]: System event handler failed for '{cleaned_word}': {handler_e}"); traceback.print_exc()

            if not processed_system_trigger:
                 print(f"[VD LOG] No registered system trigger words found in '{cleaned_text}'.")

        except sr.UnknownValueError: print("[VD LOG] Whisper could not understand audio.")
        except sr.RequestError as e: print(f"ERROR [VD]: RequestError: {e}")
        except Exception as e: print(f"ERROR [VD]: Recognition/Processing: {e}"); traceback.print_exc()
        finally: print("[VD LOG] Finished processing audio data.")
    # --- END UPDATED METHOD ---


    def _listen_loop(self):
        """ The core listening loop. """
        print("[VD LOG] Background listening thread started.")
        if self.microphone is None: print("ERROR [VD]: Mic uninitialized."); self.running = False; return

        while self.running:
            audio_data = None
            if not self.running: print("[VD LOG] Exiting listen loop."); break
            # print("[VD LOG] Listening...") # Very noisy log
            self._is_listening = True
            try:
                with self.microphone as source:
                    audio_data = self.recognizer.listen(source, timeout=None, phrase_time_limit=PHRASE_TIME_LIMIT)
                self._is_listening = False
                # print("[VD LOG] Speech detected/timeout.") # Noisy

                if audio_data and self.running:
                     self._process_speech(audio_data)
                # else: print("[VD LOG] No audio data received from listen.") # Noisy

            except sr.WaitTimeoutError: self._is_listening = False; continue
            except OSError as e: print(f"ERROR [VD] Mic OS Error: {e}"); time.sleep(2); self._is_listening = False
            except Exception as e: print(f"ERROR [VD] Listen loop: {e}"); traceback.print_exc(); time.sleep(1); self._is_listening = False
        print("[VD LOG] Background listening thread finished.")

    def start(self):
        """ Starts the listening thread. """
        if self.running: print("[VD LOG] Already running."); return
        if self.microphone is None: print("ERROR [VD]: Cannot start - mic uninitialized."); return
        print("--- Voice Detector Starting ---"); self.running = True
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()
        if self.thread.is_alive(): print("[VD LOG] Voice Detector started successfully.")
        else: print("ERROR [VD]: Failed to start thread."); self.running = False

    def stop(self):
        """ Stops the listening thread. """
        if not self.running: print("[VD LOG] Already stopped."); return
        print("--- Voice Detector Stopping ---"); self.running = False
        if self.thread and self.thread.is_alive():
            print("[VD LOG] Waiting for thread join..."); join_timeout = max(self.recognizer.pause_threshold*2, 1.5); self.thread.join(timeout=join_timeout)
            if self.thread.is_alive(): print("WARN [VD]: Thread join timeout.")
            else: print("[VD LOG] Thread joined.")
        self.thread = None; print("[VD LOG] Voice Detector stopped.")

# Removed __main__ block