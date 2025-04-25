import speech_recognition as sr
import pyautogui
import threading
import time

class VoiceListener:
    def __init__(self, action_map=None, energy_threshold=300, pause_threshold=0.8):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.running = False
        self.thread = None
        self._is_listening = False

        self.recognizer.energy_threshold = energy_threshold
        self.recognizer.pause_threshold = pause_threshold

        if action_map is None:
            self.trigger_actions = {
                "record": lambda: pyautogui.press('e'),
                "next": lambda: pyautogui.press('down'),
                "back": lambda: pyautogui.press('left'),
                "go": lambda: pyautogui.press('right'),
                "select": lambda: pyautogui.press('enter'),
                "stop": lambda: pyautogui.press('esc'),
                
            }
        else:
            self.trigger_actions = action_map

        print("Voice Listener: Adjusting for ambient noise...")
        with self.microphone as source:
            try:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            except Exception as e:
                print(f"Error adjusting for ambient noise: {e}. Using default threshold.")
        print(f"Voice Listener: Ready. Adjusted energy threshold: {self.recognizer.energy_threshold:.2f}")
        print(f"Voice Listener: Commands: {list(self.trigger_actions.keys())}")

    def _listen_and_process(self):
        print("Voice Listener: Starting background listening thread...")
        while self.running:
            audio = None
            try:
                with self.microphone as source:
                    print("Voice Listener: Waiting for phrase...")
                    self._is_listening = True
                    audio = self.recognizer.listen(source, timeout=None, phrase_time_limit=5)
                    self._is_listening = False
                    print("Voice Listener: Detected speech, processing...")

                try:
                    recognized_text = self.recognizer.recognize_google(audio).lower()
                    print(f"Voice Listener: Heard: '{recognized_text}'")

                    action_performed = False
                    for phrase, action in self.trigger_actions.items():
                        if phrase in recognized_text:
                            print(f"Voice Listener: Trigger '{phrase}' detected. Performing action.")
                            try:
                                action()
                                action_performed = True
                                time.sleep(0.5)
                                break
                            except Exception as action_e:
                                print(f"Voice Listener: Error executing action for '{phrase}': {action_e}")

                    if not action_performed and recognized_text:
                        print(f"Voice Listener: Heard '{recognized_text}', but no matching command found.")

                except sr.UnknownValueError:
                    print("Voice Listener: Could not understand audio or silence detected.")
                except sr.RequestError as e:
                    print(f"Voice Listener: Network error - Could not request results; {e}")
                except Exception as e:
                    print(f"Voice Listener: An unexpected error occurred during recognition: {e}")

            except sr.WaitTimeoutError:
                self._is_listening = False
                pass
            except Exception as e:
                self._is_listening = False
                print(f"Voice Listener: An error occurred in the main listening loop: {e}")
                time.sleep(2)

        print("Voice Listener: Stopped background listening thread.")

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._listen_and_process, daemon=True)
            self.thread.start()
            print("Voice Listener: Background thread started.")
        else:
            print("Voice Listener: Already running.")

    def stop(self):
        if self.running:
            print("Voice Listener: Stopping background thread...")
            self.running = False
            if self.thread:
                self.thread.join(timeout=2.0)
                if self.thread.is_alive():
                    print("Voice Listener: Warning - Thread did not stop cleanly.")
            print("Voice Listener: Background thread stopped.")
        else:
            print("Voice Listener: Already stopped.")

if __name__ == "__main__":
    print("--- Running listeners.py directly ---")
    listener = VoiceListener()
    listener.start()
    print("\nListener is active in the background.")
    print("Say one of the commands:", list(listener.trigger_actions.keys()))
    print("Press Ctrl+C in this terminal to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nCtrl+C detected. Shutting down...")
    except Exception as main_e:
        print(f"\nAn error occurred in the main loop: {main_e}")
    finally:
        listener.stop()
        print("--- Listener script finished ---")
