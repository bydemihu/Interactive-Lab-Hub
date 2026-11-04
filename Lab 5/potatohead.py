#!/usr/bin/env python3
import json
import time
import wave
from datetime import datetime

try:
    import board
    import adafruit_bno055
    import adafruit_ltr390
except ImportError as error:
    board = None
    adafruit_bno055 = None
    adafruit_ltr390 = None
    print(f"I2C sensor libraries unavailable: {error}")

try:
    import sounddevice as sd
except ImportError:
    sd = None

try:
    import speech_recognition as sr
except ImportError:
    sr = None


DURATION_SECONDS = 30
SAMPLE_INTERVAL_SECONDS = 0.5
AUDIO_FILE = "potatohead_speech.wav"


class OptionalSensor:
    def __init__(self, name, create_sensor, read_sensor):
        self.name = name
        self.create_sensor = create_sensor
        self.read_sensor = read_sensor
        self.sensor = None

    def read(self):
        try:
            if self.sensor is None:
                self.sensor = self.create_sensor()
            return self.read_sensor(self.sensor)
        except Exception as error:
            print(f"{self.name} unavailable: {error}")
            self.sensor = None
            return None


def create_ltr390():
    if board is None or adafruit_ltr390 is None:
        raise RuntimeError("Adafruit I2C libraries are not installed")
    return adafruit_ltr390.LTR390(board.I2C())


def read_ltr390(sensor):
    return {
        "ambient_light": sensor.light,
        "uv": sensor.uvs,
    }


def create_bno055():
    if board is None or adafruit_bno055 is None:
        raise RuntimeError("Adafruit I2C libraries are not installed")
    return adafruit_bno055.BNO055_I2C(board.I2C())


def read_bno055(sensor):
    return {
        "acceleration": sensor.acceleration,
        "gyroscope": sensor.gyro,
        "magnetometer": sensor.magnetic,
        "euler": sensor.euler,
        "quaternion": sensor.quaternion,
    }


def start_microphone_recording():
    if sd is None:
        print("Microphone unavailable: sounddevice is not installed")
        return None
    try:
        device = sd.query_devices(kind="input")
        sample_rate = int(device["default_samplerate"])
        recording = sd.rec(
            int(sample_rate * DURATION_SECONDS),
            samplerate=sample_rate,
            channels=1,
            dtype="float32",
            blocking=False,
        )
        return {"recording": recording, "sample_rate": sample_rate, "device": device["name"]}
    except Exception as error:
        print(f"Microphone recording unavailable: {error}")
        return None


def save_recording(recording):
    if recording is None:
        return None

    try:
        sd.wait()
        samples = (recording["recording"][:, 0] * 32767).clip(-32768, 32767)
        pcm = samples.astype("int16").tobytes()
        with wave.open(AUDIO_FILE, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(recording["sample_rate"])
            wav_file.writeframes(pcm)
        return AUDIO_FILE
    except Exception as error:
        print(f"Could not save microphone recording: {error}")
        return None


def transcribe_recording(audio_file):
    if audio_file is None:
        return None
    if sr is None:
        print("Speech-to-text unavailable: SpeechRecognition is not installed")
        return None

    try:
        recognizer = sr.Recognizer()
        with sr.AudioFile(audio_file) as source:
            audio = recognizer.record(source)
        return recognizer.recognize_google(audio)
    except sr.UnknownValueError:
        print("Speech-to-text could not understand the recording")
    except sr.RequestError as error:
        print(f"Speech-to-text service unavailable: {error}")
    except Exception as error:
        print(f"Speech-to-text failed: {error}")
    return None


sensors = {
    "ltr390": OptionalSensor("LTR390", create_ltr390, read_ltr390),
    "bno055": OptionalSensor("BNO055", create_bno055, read_bno055),
}


def main():
    end_time = time.monotonic() + DURATION_SECONDS
    frame_number = 0
    recording = start_microphone_recording()

    try:
        while time.monotonic() < end_time:
            frame_started = time.monotonic()
            frame_number += 1
            frame = {
                "frame": frame_number,
                "timestamp": datetime.now().isoformat(timespec="milliseconds"),
                # The SparkX VL53L3CX has no supported Python driver.
                "vl53l3cx": None,
                "ltr390": sensors["ltr390"].read(),
                "bno055": sensors["bno055"].read(),
                "microphone": {"status": "recording"} if recording else None,
            }
            print(json.dumps(frame), flush=True)
            elapsed = time.monotonic() - frame_started
            time.sleep(max(0, SAMPLE_INTERVAL_SECONDS - elapsed))
    except KeyboardInterrupt:
        if recording:
            sd.stop()
        print("\nStopped by user.")
        return

    audio_file = save_recording(recording)
    transcript = transcribe_recording(audio_file)
    print(json.dumps({
        "type": "speech_transcription",
        "audio_file": audio_file,
        "transcript": transcript,
    }), flush=True)


if __name__ == "__main__":
    main()
