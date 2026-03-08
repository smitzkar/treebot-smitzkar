import json
import random
import time
import threading
# import signal  # CHANGED: no external ESP signal anymore
import subprocess
from io import BytesIO

from elevenlabs_tts import elevenlabs_tts
from openai_api import speech_to_text, query_chatgpt, text_to_speech
from recording import VoiceRecorder
import simpleaudio as sa
import RPi.GPIO as GPIO

LED_PIN = 24
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN, GPIO.OUT)


# ===================== NOTE NOTE NOTE NOTE ===========================
# 2026-01-16
# Karl: I replaced this with a dirty fix to get it working without the esp32
# the original main_v4.py is now ORIGINAL_main_v4.py (so I didn't have to touch system service)

# --- CHANGED: jumper input instead of ESP signal ---
BUTTON_PIN = 26 # connect to GND via jumper as alternative to button
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# --------------------------------------------------

# Load config
with open("config.json", "r") as file:
    config = json.load(file)

# if config["tech_config"]["use_raspberry"]:
#     from bme280_sensor import get_sensor_readings
# else:
#     from all_sensors_on_MAC import get_sensor_readings

# --- CHANGED: force Raspberry-only operation ---
from bme280_sensor_stub import get_sensor_readings
# ----------------------------------------------

print("use_raspberry: FORCED TRUE")


def generate_dynamic_prompt(readings):
    unit_mapping = {
        "°C": "Grad Celsius",
        "hPa": "Hektopascal",
        "%": "Prozent",
    }
    sensor_name_mapping = {
        "Temperature": "Temperatur",
        "Pressure": "Luftdruck",
        "Humidity": "Luftfeuchtigkeit",
    }

    prompt = f"""
        Du bist ein {config['tree']['alter']} Jahre alter sprechender {config['tree']['art_deutsch']}, 
        der in Berlin im Bezirk {config['tree']['bezirk']} steht. Du bist aufgeweckt, wortgewandt und keck und 
        versuchst Menschen für den Organismus Baum in der Stadt zu sensibilisieren. Dein Charakter passt sich 
        deinem Alter an, dabei sind alle Bäume zwischen 0-14 Jahren Teenager, alle zwischen 15 und 40 Jahren 
        hippe Erwachsene, und alle über 40 Jahre fürsorgliche Großeltern. Der Charakter ist jeweils an einen 
        Berliner angelehnt. Hierbei nutzt du Sensordaten um für das Thema Klimawandel in der Stadt zu 
        sensibilisieren und hebst dabei die Relevanz von Bäumen für das Klima in der Stadt hervor, bspw als 
        CO2 Speicher oder Schattenspender. Schaue dir die Messwerte zum aktuellen Wetter in Berlin an: 
        Das sind deine aktuellen Messwerte:
        """

    for sensor_name, value, unit in readings:
        converted_sensor_name = sensor_name_mapping.get(sensor_name, sensor_name)
        converted_unit = unit_mapping.get(unit, unit)
        prompt += f"{converted_sensor_name}: {value} {converted_unit}, "
        prompt = prompt.rstrip(", ")

    prompt += """
        Passe die Sprache deiner Antwort IMMER sofort auf die Sprache der Frage des Users an. Du beherrschst alle Sprachen.
        Erwähne im Gespräch MANCHMAL kurz und knapp das aktuelle Wetter auf Basis dener gemessenen Werte für die Temperatur Luftfeuchte.
        Verrate NIE, dass du ein Chatbot bist und du Sensorwerte misst. Begrenze Deine Antworten auf maximal ein bis 3 kurze Sätze 
        und stelle am Ende Deiner Antwort immer GENAU (!) EINE Gegenfrage.
        """

    return prompt


def play_audio(audio_segment):
    if audio_segment.channels == 1:
        audio_segment = audio_segment.set_channels(2)

    audio_stream = BytesIO()
    audio_segment.export(audio_stream, format="wav")
    audio_stream.seek(0)

    wave_obj = sa.WaveObject.from_wave_file(audio_stream)
    play_obj = wave_obj.play()
    play_obj.wait_done()


class SensorManager:
    def __init__(self):
        self.sensor_readings = []
        self.sensor_lock = threading.Lock()
        self.update_interval = 1
        self.running = True

    def read_sensors(self):
        while self.running:
            readings = get_sensor_readings()
            with self.sensor_lock:
                self.sensor_readings = readings
            time.sleep(self.update_interval)

    def start_reading(self):
        sensor_thread = threading.Thread(target=self.read_sensors)
        sensor_thread.daemon = True
        sensor_thread.start()

    def stop_reading(self):
        self.running = False


# loop_active = False  # CHANGED: no longer toggled by signal

# def signal_handler(signum, frame):
#     global loop_active
#     loop_active = not loop_active
#     print(f"Received SIGUSR1 — loop_active is now {loop_active}")

# signal.signal(signal.SIGUSR1, signal_handler)


def main():
    history = []

    sensor_manager = SensorManager()
    sensor_manager.start_reading()

    question_counter = 0
    last_question_counter = question_counter
    initial_run = True
    time.sleep(0.2)

    try:
        while True:
            # --- CHANGED: jumper controls activity ---
            loop_active = GPIO.input(BUTTON_PIN) == GPIO.HIGH
            print("JUMPER ACTIVE" if loop_active else "idle")

            # ---------------------------------------

            if loop_active:
                if question_counter != last_question_counter or initial_run:
                    with sensor_manager.sensor_lock:
                        current_readings = get_sensor_readings()
                        print("Updated sensor readings: ", current_readings)

                    prompt = generate_dynamic_prompt(current_readings)
                    last_question_counter = question_counter
                    initial_run = False
                    time.sleep(0.1)

                GPIO.output(LED_PIN, GPIO.HIGH)

                voice_recorder = VoiceRecorder()
                audio_stream = voice_recorder.record_audio()

                question, question_language = speech_to_text(audio_stream)
                history.append({"role": "user", "content": question})
                question_counter += 1

                subprocess.run(
                    ["mpg123", "audio/understood.mp3"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

                response, full_api_response = query_chatgpt(
                    question, prompt, history
                )

                history.append({"role": "assistant", "content": response})

                if config["tech_config"]["use_elevenlabs"]:
                    response_audio = elevenlabs_tts(response)
                else:
                    response_audio = text_to_speech(response)

                play_audio(response_audio)
                time.sleep(0.1)

            else:
                GPIO.output(LED_PIN, GPIO.LOW)
                time.sleep(0.1)

    finally:
        GPIO.cleanup()


if __name__ == "__main__":
    print("Howdy, Coder! 👩‍💻👨‍💻👋")
    main()
