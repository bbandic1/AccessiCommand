import speech_recognition as sr
import pyautogui
import threading
import time
import queue 
import traceback 


DEFAULT_PAUSE_THRESHOLD = 0.4 
DEFAULT_ENERGY_THRESHOLD = 350 
PHRASE_TIME_LIMIT = 3         
WHISPER_MODEL = "tiny.en"     
ACTION_DELAY = 0.02          

class VoiceListener:
    def __init__(self, action_map=None, energy_threshold=DEFAULT_ENERGY_THRESHOLD, pause_threshold=DEFAULT_PAUSE_THRESHOLD):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone() 
        self.running = False
        self.thread = None
        self._is_listening = False

        self.recognizer.energy_threshold = energy_threshold
        self.recognizer.pause_threshold = pause_threshold
        self.recognizer.non_speaking_duration = pause_threshold
        # -------------------------------------------------
        self.recognizer.dynamic_energy_threshold = True 

        if action_map is None:
            self.trigger_actions = {
                "record": lambda: pyautogui.press('space'),
                "next": lambda: pyautogui.press('down'),
                "back": lambda: pyautogui.press('left'),
                "go": lambda: pyautogui.press('right'),
                "select": lambda: pyautogui.press('enter'),
                "stop": lambda: pyautogui.press('esc'),
            }
        else:
            self.trigger_actions = {k.lower(): v for k, v in action_map.items()}

        print("--- Voice Listener Initializing ---")
        print(f"Model: {WHISPER_MODEL}, Pause Threshold: {self.recognizer.pause_threshold}s, Non-Speaking Duration: {self.recognizer.non_speaking_duration}s") # Log both
        print(f"Commands: {list(self.trigger_actions.keys())}")
        print("Adjusting for ambient noise...")
        with self.microphone as source:
            try:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            except Exception as e:
                print(f"WARN: Error adjusting for ambient noise: {e}. Using threshold: {self.recognizer.energy_threshold}")
        print(f"Ready. Adjusted energy threshold: {self.recognizer.energy_threshold:.2f}")
        print("------------------------------------")


    def _process_audio_and_act(self, audio_data):
        """Processes recognized audio."""
        try:
            recognized_text = self.recognizer.recognize_whisper(
                audio_data,
                model=WHISPER_MODEL,
                language="english"
            ).lower()

            cleaned_text_for_log = recognized_text.strip(" .,!?\"'\n\t")
            raw_words = cleaned_text_for_log.split() 

            if not raw_words:
                print("Voice Listener: Heard silence or unintelligible.")
                return

            print(f"Voice Listener: Heard: '{cleaned_text_for_log}' (Raw Words: {raw_words})")

            action_performed_this_utterance = False
            for raw_word in raw_words:
                word = raw_word.strip(".,!?\"'")
                if not word: 
                    continue

                action = self.trigger_actions.get(word)
                if action:
                    print(f"Action: Trigger word '{word}' (from '{raw_word}') -> Executing.")
                    try:
                        action()
                        action_performed_this_utterance = True
                        time.sleep(ACTION_DELAY) 
                    except Exception as action_e:
                        print(f"ERROR: executing action for '{word}': {action_e}")

            if not action_performed_this_utterance and cleaned_text_for_log:
                print(f"Info: Heard '{cleaned_text_for_log}', but no matching command words found after cleaning.")


        except sr.UnknownValueError:
            print("Voice Listener: Could not understand audio.")
        except sr.RequestError as e:
            print(f"ERROR: Could not request results (Network issue?): {e}")
        except Exception as e:
            print(f"ERROR: Unexpected error during recognition/action: {e}")
            print("--- Recognition/Action Traceback ---")
            traceback.print_exc()
            print("-----------------------------------")


    def _listen_loop(self):
        """The core listening loop running in a background thread."""
        print("Voice Listener: Background listening thread started.")
        while self.running:
            audio_data = None
            if not self.running: break

            try:
                with self.microphone as source:
                    print("Voice Listener: Waiting for phrase...")
                    self._is_listening = True
                    audio_data = self.recognizer.listen(
                        source,
                        timeout=None, 
                        phrase_time_limit=PHRASE_TIME_LIMIT
                    )
                    self._is_listening = False
                    print("Voice Listener: Processing speech...")

                if audio_data and self.running:
                     self._process_audio_and_act(audio_data)

            except sr.WaitTimeoutError:
                self._is_listening = False
                continue 
            except OSError as e:
                 self._is_listening = False
                 print(f"ERROR: Microphone OS Error: {e}. Check microphone connection/permissions.")
                 time.sleep(2) 
            except Exception as e:
                self._is_listening = False
                print(f"ERROR: Unexpected error in listening loop: {e}")
                print("--- Listening Loop Traceback ---")
                traceback.print_exc()
                print("-----------------------------")
                time.sleep(1) 

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
            self.running = False 
            if self.thread:
                join_timeout = max(self.recognizer.pause_threshold * 2, 1.5) 
                self.thread.join(timeout=join_timeout)
                if self.thread.is_alive():
                    print("WARN: Listener thread did not stop cleanly.")
            print("Voice Listener: Service stopped.")
        else:
            print("Voice Listener: Service already stopped.")


if __name__ == "__main__":
    print("--- Running Voice Listener Directly ---")

    listener = VoiceListener()

    listener.start()

    print("\nListener active. Speak commands.")
    print("Press Ctrl+C in this terminal to stop.")

    try:
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
        listener.stop()
        print("--- Voice Listener script finished ---")