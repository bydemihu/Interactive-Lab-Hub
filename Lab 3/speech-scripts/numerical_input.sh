#!/bin/bash

# Audio devices
MIC="plughw:CARD=Device_1,DEV=0"
SPEAKER="plughw:CARD=Device,DEV=0"

# Files
AUDIO="numerical_response.wav"
TRANSCRIPT="numerical_response.txt"

echo "Asking question..."
espeak "How many pets do you have?" --stdout | aplay -D "$SPEAKER"

sleep 1

echo "Recording answer... Speak now."
arecord -D "$MIC" \
    -f S16_LE \
    -r 48000 \
    -c 1 \
    -d 5 \
    "$AUDIO"

echo "Recording complete."
echo "Transcribing..."

python3 transcribe.py "$AUDIO" > "$TRANSCRIPT"

echo
echo "Respondent's answer:"
cat "$TRANSCRIPT"
echo

espeak "Thank you. Your response has been recorded." --stdout | aplay -D "$SPEAKER"

echo "Audio saved to: $AUDIO"
echo "Transcript saved to: $TRANSCRIPT"
