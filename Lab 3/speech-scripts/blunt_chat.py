#!/usr/bin/env python3
"""Listen for speech, rewrite it bluntly with OpenAI, and speak the result."""

import argparse
import json
import math
import os
import sys
import threading
import time
from pathlib import Path

import board
import digitalio
import numpy as np
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
import sounddevice as sd
import adafruit_rgb_display.st7789 as st7789
from adafruit_seesaw import seesaw, rotaryio
from adafruit_seesaw import digitalio as seesaw_digitalio
from faster_whisper import WhisperModel
from openai import OpenAI
from digitalio import Pull

from echo_bot import DEFAULT_VAD, DEFAULT_VOICE, SAMPLE_RATE, Speaker
from listen import build_vad


SYSTEM_PROMPT = (
    "Rewrite the USER's speech as what they would say DIRECTLY TO THE PERSON THEY "
    "ARE TALKING TO if they suddenly lost all social filter. Do not analyze, narrate, "
    "or describe the USER's feelings, motives, or communication strategy. Never say "
    "things like 'I'm annoyed', 'I'm trying to be nice', 'I secretly want', or 'I'm "
    "making an excuse'. Instead, directly confront, confess, complain, flirt, reject, "
    "admit, or say whatever the USER is holding back. Infer the real subtext from the "
    "specific situation, wording, hedging, nervousness, vagueness, and context. Focus "
    "on the unsaid part; do not waste words repeating information already stated or "
    "obvious. Make bold but plausible interpretations. Be unhinged, funny, blunt, "
    "specific, and slightly exaggerated. Usually 1-2 punchy sentences. Return a JSON "
    "object with exactly two fields: `text_response`, containing only what the USER "
    "would actually say to the other person, and `emotion`, containing exactly one "
    "of anger, tiredness, aversion, jealousy, or desire. The emotion is "
    "the USER's underlying hidden emotion. The caller also supplies a sassiness "
    "value from 0 to 50 that controls how rude and unfiltered the response should be. "
    "Do not include markdown or extra fields."
)

SASSINESS_MAX = 50
DISPLAY_LOCK = threading.Lock()

EMOTION_COLORS = {
    "anger": (255, 41, 0),
    "tiredness": (44, 66, 110),
    "aversion": (95, 184, 162),
    "jealousy": (193, 232, 65),
    "desire": (238, 77, 255),
}
EMOTIONS = frozenset(EMOTION_COLORS)

# SYSTEM_PROMPT = (
#     "Rewrite the USER's speech as what the USER would say DIRECTLY TO THE PERSON THEY "
#     "ARE TALKING TO if the USER suddenly lost all social filter. The hidden meaning "
#     "must belong to the USER. Never transfer the USER's feelings, intentions, desires, "
#     "hesitation, attraction, rejection, or frustration onto the other person. Pay close "
#     "attention to WHO wants what, WHO is avoiding what, and WHO is making the move. "
#     "Infer what the USER is trying to communicate through their choice of words and "
#     "behavior. If the USER keeps inventing reasons or opportunities to spend time with "
#     "someone, consider whether the USER wants closeness or is making a move. If the USER "
#     "claims they want something but gives an absurdly vague, distant, or impractical "
#     "alternative, consider whether the USER actually wants the other person to take the "
#     "hint and stop asking. These are reasoning principles, not fixed interpretations; "
#     "always use the specific context. "
#     "Do not analyze, narrate, or describe the USER's feelings, motives, or communication "
#     "strategy. Never say things like 'I'm annoyed', 'I'm trying to be nice', 'I secretly "
#     "want', or 'I'm making an excuse'. Instead, directly confront, confess, complain, "
#     "flirt, reject, admit, or say whatever the USER is holding back TO THE OTHER PERSON. "
#     "Focus on the unsaid part rather than repeating information already established. "
#     "Make bold but plausible interpretations. Be unhinged, funny, blunt, specific, and "
#     "slightly exaggerated. Usually 1-2 punchy sentences. Return only what the USER would "
#     "actually say to the other person."
# )

FEW_SHOT_MESSAGES = [
    {
        "role": "user",
        "content": (
            "I would love to hang out, but I'm really busy this month. "
            "Maybe hit me up in like three months or something."
        ),
    },
    {
        "role": "assistant",
        "content": json.dumps(
            {
                "text_response": "Please take the fucking hint. I don't want to hang out with you.",
                "emotion": "aversion",
            }
        ),
    },
    {
        "role": "user",
        "content": (
            "If you're free, I'd love to grab coffee sometime. Or we could study "
            "together, or I could help you with something. I'm basically always free."
        ),
    },
    {
        "role": "assistant",
        "content": json.dumps(
            {
                "text_response": (
                    "I like you and I'm desperately looking for an excuse to spend time "
                    "with you. Coffee? Studying? Literally anything?"
                ),
                "emotion": "desire",
            }
        ),
    },
    {
        "role": "user",
        "content": (
            "Yeah, I can make that change, but since it wasn't in the initial brief, "
            "it'll probably take me about a week. Sorry."
        ),
    },
    {
        "role": "assistant",
        "content": json.dumps(
            {
                "text_response": (
                    "No shit it'll take a week. You added a huge change that you never "
                    "fucking told me about."
                ),
                "emotion": "anger",
            }
        ),
    },
]

def blunt_response(
    client: OpenAI,
    model: str,
    history: list[dict[str, str]],
    text: str,
    sassiness: int,
) -> tuple[str, str]:
    """Ask the LLM to rewrite one transcript using the conversation as context."""
    messages = history[-4:] + [{"role": "user", "content": text}]
    sassiness_prompt = (
        f"Set the level of rudeness and lack of filtering to {sassiness} out of "
        f"{SASSINESS_MAX}. At 0, maintain some semblance of politeness. At "
        f"{SASSINESS_MAX}, be as exaggeratedly rude and unfiltered as possible."
    )
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": f"{SYSTEM_PROMPT} {sassiness_prompt}"},
            *FEW_SHOT_MESSAGES,
            *messages,
        ],
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("OpenAI returned an empty response")
    try:
        result = json.loads(content)
    except json.JSONDecodeError as error:
        raise RuntimeError("OpenAI returned invalid JSON") from error

    reply = result.get("text_response")
    emotion = result.get("emotion")
    if not isinstance(reply, str) or not reply.strip():
        raise RuntimeError("OpenAI JSON is missing a text_response")
    if not isinstance(emotion, str) or emotion not in EMOTIONS:
        raise RuntimeError(f"OpenAI JSON has an invalid emotion: {emotion!r}")
    return reply.strip(), emotion


def setup_display():
    """Initialize the ST7789 display using the Lab 2 screen wiring."""
    cs_pin = digitalio.DigitalInOut(board.D5)
    dc_pin = digitalio.DigitalInOut(board.D25)
    reset_pin = digitalio.DigitalInOut(board.D24)
    display = st7789.ST7789(
        board.SPI(),
        cs=cs_pin,
        dc=dc_pin,
        rst=reset_pin,
        baudrate=24000000,
        width=135,
        height=240,
        x_offset=53,
        y_offset=40,
    )
    backlight = digitalio.DigitalInOut(board.D22)
    backlight.switch_to_output()
    backlight.value = True
    return display


def emotion_background(emotion: str) -> tuple[int, int, int]:
    """Return the color assigned to an emotion."""
    return EMOTION_COLORS[emotion]


def draw_interface(
    display,
    background: tuple[int, int, int],
    sassiness: int,
    label: str = "Unfilter Me",
) -> None:
    """Draw the sassiness control over the current full-screen background."""
    canvas_width = display.height
    canvas_height = display.width
    image = Image.new("RGB", (canvas_width, canvas_height), background)
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24
    )
    label_box = draw.textbbox((0, 0), label, font=font)
    label_width = label_box[2] - label_box[0]
    label_x = (canvas_width - label_width) // 2
    draw.text((label_x + 1, 7), label, font=font, fill=(0, 0, 0))
    draw.text((label_x, 6), label, font=font, fill=(255, 255, 255))

    bar_x = 12
    bar_width = canvas_width - 24
    bar_height = 16
    bar_y = canvas_height - bar_height - 10
    draw.rectangle(
        (bar_x, bar_y, bar_x + bar_width, bar_y + bar_height),
        outline=(255, 255, 255),
    )
    fill_width = int((bar_width - 3) * sassiness / SASSINESS_MAX)
    if fill_width:
        draw.rectangle(
            (bar_x + 2, bar_y + 2, bar_x + 1 + fill_width, bar_y + bar_height - 2),
            fill=(255, 255, 255),
        )
    with DISPLAY_LOCK:
        display.image(image, 90)


def setup_encoder():
    """Initialize the Qwiic rotary encoder and its push button."""
    i2c = board.I2C()
    seesaw_device = seesaw.Seesaw(i2c, addr=0x36)
    encoder = rotaryio.IncrementalEncoder(seesaw_device)
    encoder.position = 0
    button = seesaw_digitalio.DigitalIO(seesaw_device, 24)
    button.switch_to_input(pull=Pull.UP)
    return encoder, button


def pulse_while_idle(
    display,
    active_event: threading.Event,
    state: dict[str, int],
    state_lock: threading.Lock,
) -> None:
    """Pulse the display between soft grey and white while waiting for speech."""
    period = 2.4
    while True:
        if active_event.is_set():
            time.sleep(0.05)
            continue

        phase = (math.sin(time.monotonic() * 2 * math.pi / period) + 1) / 2
        gray = int(110 * phase)
        with state_lock:
            sassiness = state["sassiness"]
        draw_interface(display, (gray, gray, gray), sassiness)
        active_event.wait(0.06)


def main() -> None:
    
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description=__doc__)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="tiny.en", help="Whisper model size")
    parser.add_argument("--llm-model", default="gpt-5.6-luna", help="OpenAI chat model")
    parser.add_argument("--vad-model", type=Path, default=DEFAULT_VAD)
    parser.add_argument("--voice", type=Path, default=DEFAULT_VOICE)
    parser.add_argument("--min-silence", type=float, default=0.4,
                        help="seconds of silence that end a turn (default: 0.4)")
    parser.add_argument("--min-speech", type=float, default=0.4,
                        help="ignore speech bursts shorter than this (default: 0.4)")
    args = parser.parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("OPENAI_API_KEY is not set. Export it before running this script.")
    for path, what in ((args.vad_model, "VAD model"), (args.voice, "Piper voice")):
        if not path.is_file():
            sys.exit(f"{what} not found at {path}. Run ./setup.sh first.")

    print("Loading models...", flush=True)
    recognizer = WhisperModel(args.model, device="cpu", compute_type="int8")
    speaker = Speaker(args.voice)
    display = setup_display()
    encoder, button = setup_encoder()
    state = {"sassiness": 0}
    state_lock = threading.Lock()
    active_event = threading.Event()
    active_event.set()
    pulse_thread = threading.Thread(
        target=pulse_while_idle,
        args=(display, active_event, state, state_lock),
        daemon=True,
    )
    pulse_thread.start()
    client = OpenAI()
    vad, window = build_vad(args.vad_model, args.min_silence, args.min_speech)
    history: list[dict[str, str]] = []
    last_utterance = None
    last_button = button.value

    active_event.clear()
    print(f"Ready. Endpointing after {args.min_silence}s of silence. Ctrl-C to stop.\n")

    buffer = np.empty(0, dtype=np.float32)
    samples_per_read = int(0.1 * SAMPLE_RATE)

    with sd.InputStream(channels=1, dtype="float32", samplerate=SAMPLE_RATE) as stream:
        while True:
            chunk, _ = stream.read(samples_per_read)
            position = encoder.position
            sassiness = max(0, min(SASSINESS_MAX, position))
            with state_lock:
                state["sassiness"] = sassiness

            buffer = np.concatenate([buffer, chunk.reshape(-1)])

            while len(buffer) > window:
                vad.accept_waveform(buffer[:window])
                buffer = buffer[window:]

            while not vad.empty():
                last_utterance = np.array(vad.front.samples, dtype=np.float32)
                vad.pop()
                print(
                    f"  speech chunk ready: {len(last_utterance) / SAMPLE_RATE:.1f}s"
                )

            current_button = button.value
            button_pressed = last_button and not current_button
            last_button = current_button
            if button_pressed and last_utterance is not None:
                active_event.set()
                phase = (math.sin(time.monotonic() * 2 * math.pi / 2.4) + 1) / 2
                gray = int(110 * phase)
                draw_interface(
                    display,
                    (gray, gray, gray),
                    sassiness,
                    label="Unfiltering...",
                )
                try:
                    whisper_started = time.perf_counter()
                    segments, _ = recognizer.transcribe(
                        last_utterance, beam_size=1
                    )
                    heard = " ".join(segment.text.strip() for segment in segments)
                    print(
                        f"  whisper: {time.perf_counter() - whisper_started:.2f}s"
                    )
                    last_utterance = None
                    if not heard:
                        continue
                    print(f"  heard: {heard}")

                    llm_started = time.perf_counter()
                    reply, emotion = blunt_response(
                        client, args.llm_model, history, heard, sassiness
                    )
                    print(f"  llm: {time.perf_counter() - llm_started:.2f}s")
                    history.extend([
                        {"role": "user", "content": heard},
                        {
                            "role": "assistant",
                            "content": json.dumps(
                                {"text_response": reply, "emotion": emotion}
                            ),
                        },
                    ])
                    print(f"  blunt: {reply}")
                    print(f"  emotion: {emotion}")
                    draw_interface(
                        display,
                        emotion_background(emotion),
                        sassiness,
                        label="Unfiltering...",
                    )
                    t0 = time.perf_counter()
                    stream.abort()
                    try:
                        speaker.say(reply)
                    finally:
                        stream.start()
                        buffer = np.empty(0, dtype=np.float32)
                        vad.reset()
                    print(f"  spoken in {time.perf_counter() - t0:.2f}s\n")
                except Exception as error:
                    print(f"  response error: {error}", file=sys.stderr)
                finally:
                    active_event.clear()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")