{
  "bindings": [
    {
      "trigger_type": "face",      // "face", "voice", "hand"
      "trigger_event": "LEFT_WINK", // Specific event ID from detector
      "action_id": "PRESS_LEFT"     // ID from action registry
    },
    {
      "trigger_type": "face",
      "trigger_event": "MOUTH_OPEN",
      "action_id": "PRESS_DOWN"
    },
    {
      "trigger_type": "voice",
      "trigger_event": "record",     // Keyword from voice detector config
      "action_id": "PRESS_SPACE"
    }
    // ... more bindings
  ],
  "settings": { // Other app settings
    "facial_detector_thresholds": { "ear": 0.20, "mar": 0.35 },
    "voice_detector_settings": { "energy": 300, "pause": 0.8 }
    // etc.
  }
}