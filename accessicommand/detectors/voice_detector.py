import speech_recognition as sr
import threading
import time
import traceback 

DEFAULT_PAUSE_THRESHOLD = 0.4
DEFAULT_ENERGY_THRESHOLD = 350
PHRASE_TIME_LIMIT = 3
WHISPER_MODEL = "tiny.en"


class VoiceDetector:
    """
    Listens for specific trigger words using the microphone and emits events
    when they are detected via a provided handler function.
    Uses Whisper for offline recognition.
    """
    def __init__(self, trigger_words, event_handler,
                 energy_threshold=DEFAULT_ENERGY_THRESHOLD,
                 pause_threshold=DEFAULT_PAUSE_THRESHOLD,
                 device_index=None): 
        """
        Initializes the VoiceDetector.

        Args:
            trigger_words (list | set): A collection of lowercase words/phrases to listen for.
            event_handler (callable): Function to call when a trigger is detected.
                                      Expected signature: event_handler(detector_type: str, event_data: any)
                                      Example call: event_handler("voice", "next")
            energy_threshold (int): Minimum audio energy level to trigger listening.
            pause_threshold (float): Seconds of silence after speech to determine phrase end.
            device_index (int | None): The index of the microphone device to use. None for default.
        """
        self.recognizer = sr.Recognizer()
        try:
            self.microphone = sr.Microphone(device_index=device_index)
        except Exception as e:
            print(f"ERROR: Failed to initialize microphone (index: {device_index}): {e}")
            print("       Falling back to default microphone.")
            self.microphone = sr.Microphone()

        self.running = False
        self.thread = None
        self._is_listening = False 

        if not callable(event_handler):
            print("WARN: No valid event_handler provided to VoiceDetector. Events will be detected but not emitted.")
            self.event_handler = lambda detector_type, event_data: None
        else:
            self.event_handler = event_handler

        self.trigger_words = set(str(word).lower() for word in trigger_words if word) 
        if not self.trigger_words:
             print("WARN: No trigger words provided to VoiceDetector. It will listen but trigger no events.")

        self.recognizer.energy_threshold = energy_threshold
        self.recognizer.pause_threshold = pause_threshold
        self.recognizer.non_speaking_duration = pause_threshold 
        self.recognizer.dynamic_energy_threshold = True

        print("--- Voice Detector Initializing ---")
        print(f"Model: {WHISPER_MODEL}, Pause Threshold: {self.recognizer.pause_threshold}s, Non-Speaking Duration: {self.recognizer.non_speaking_duration}s")
        print(f"Listening for Trigger Words: {sorted(list(self.trigger_words))}")
        print("Adjusting for ambient noise...")
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            print(f"Ready. Adjusted energy threshold: {self.recognizer.energy_threshold:.2f}")
        except Exception as e:
            print(f"WARN: Error adjusting for ambient noise: {e}. Using threshold: {self.recognizer.energy_threshold}")
        print("------------------------------------")


    def _process_speech(self, audio_data):
        """Processes recognized audio and calls the event handler for trigger words."""
        try:
            recognized_text = self.recognizer.recognize_whisper(
                audio_data,
                model=WHISPER_MODEL,
                language="english"
            ).lower()

            cleaned_text_for_log = recognized_text.strip(" .,!?\"'\n\t")
            raw_words = cleaned_text_for_log.split() 

            if not raw_words:
                return

            print(f"Voice Detector: Heard: '{cleaned_text_for_log}' (Raw Words: {raw_words})")

            words_processed_count = 0
            for raw_word in raw_words:
                word = raw_word.strip(".,!?\"'")
                if not word: continue 

                words_processed_count += 1
                if word in self.trigger_words:
                    print(f"Voice Detector: Trigger word detected: '{word}' (from '{raw_word}')")
                    try:
                        self.event_handler("voice", word)
                    except Exception as handler_e:
                        print(f"ERROR: executing event handler for 'voice', '{word}': {handler_e}")
                        print("--- Event Handler Traceback ---")
                        traceback.print_exc()
                        print("-----------------------------")



        except sr.UnknownValueError:
            pass 
        except sr.RequestError as e:
            print(f"ERROR: Could not request results (Network issue?): {e}")
        except Exception as e:
            print(f"ERROR: Unexpected error during recognition: {e}")
            print("--- Recognition Traceback ---")
            traceback.print_exc()
            print("---------------------------")


    def _listen_loop(self):
        """The core listening loop running in a background thread."""
        print("Voice Detector: Background listening thread started.")
        while self.running:
            audio_data = None
            if not self.running: break 

            try:
                with self.microphone as source:
                    self._is_listening = True
                    audio_data = self.recognizer.listen(
                        source,
                        timeout=None, 
                        phrase_time_limit=PHRASE_TIME_LIMIT
                    )
                    self._is_listening = False

                if audio_data and self.running: 
                     self._process_speech(audio_data)

            except sr.WaitTimeoutError:
                self._is_listening = False
                continue # Loop again
            except OSError as e:
                 self._is_listening = False
                 print(f"ERROR: Microphone OS Error: {e}. Check device/connection.")
                 time.sleep(2)
            except Exception as e:
                self._is_listening = False
                print(f"ERROR: Unexpected error in listening loop: {e}")
                print("--- Listening Loop Traceback ---")
                traceback.print_exc()
                print("-----------------------------")
                time.sleep(1) 

        print("Voice Detector: Background listening thread stopped.")

    def start(self):
        """Starts the listening thread if not already running."""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._listen_loop, daemon=True)
            self.thread.start()
            print("Voice Detector: Started.")
        else:
            print("Voice Detector: Already running.")

    def stop(self):
        """Stops the listening thread gracefully."""
        if self.running:
            print("Voice Detector: Stopping...")
            self.running = False 
            if self.thread and self.thread.is_alive():
                join_timeout = max(self.recognizer.pause_threshold * 2, 1.5)
                self.thread.join(timeout=join_timeout)
                if self.thread.is_alive():
                    print("WARN: Voice Detector thread did not stop cleanly.")
            print("Voice Detector: Stopped.")
        else:
            print("Voice Detector: Already stopped.")
