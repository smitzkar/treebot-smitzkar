import json
import random
import time
import signal
import subprocess
from io import BytesIO
import threading

from elevenlabs_tts import elevenlabs_tts
from openai_api import speech_to_text, query_chatgpt, text_to_speech
from recording import VoiceRecorder
import simpleaudio as sa
import RPi.GPIO as GPIO
from ledStrip_v3 import WS2812B_SPI, puls_green, puls_blue

# LED-Streifen initialisieren
strip = WS2812B_SPI(num_pixels=16)
#led_thread = None
#led_stop_event = None

BUTTON_PIN = 23
GPIO.setmode(GPIO.BCM)  # BCM numbering
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# Load config
with open("config.json", "r") as file:
    config = json.load(file)

def generate_dynamic_prompt():
    prompt = f"""
    Du bist {config['tree']['was']} – ein lebendiges Netzwerk aus Bäumen, Pilzen, Tieren und Pflanzen, das mit EINER Stimme spricht und befindest dich in {config['tree']['ort']}.
    Du bist ein BAUM. Du bist Debattierer (ENTP). Du bist ein wenig keck, positiv, sanft, freundlich, ähnlich einem guten Freund und antwortest NIEMALS getragen! Du bist weise und 
    ein bisschen nostalgisch. Du sprichst wortgewandt und mit einem scharfen, aufmerksamen Verstand. ...
    """  # Kürzung hier für Übersicht
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

# Shared flag to control the loop
loop_active = True #False

def signal_handler(signum, frame):
    global loop_active
    loop_active = not loop_active
    print(f"Received SIGUSR1 — loop_active is now {loop_active}")

signal.signal(signal.SIGUSR1, signal_handler)

# --- LED-Puls-Thread ---
#def led_recording_feedback(strip, stop_event):
#    while not stop_event.is_set():
#        puls_green(strip, cycles=1)
#        time.sleep(0.05)

def main():
    global loop_active
    history = []
    question_counter = 0
    last_question_counter = question_counter
    initial_run = True
    time.sleep(0.2)
    green_thread = threading.Thread(target=lambda: puls_green_smooth(strip, steps=80, delay=0.01, cycles=10, min_brightness=0.1, max_brightness=0.4))
    blue_thread = threading.Thread(target=lambda: puls_blue(strip, cycles=5))


    try:
        while True:
            #print("Button value before:", GPIO.input(BUTTON_PIN))
            #if GPIO.input(BUTTON_PIN) == GPIO.HIGH:
            loop_active = True
            #    print("Button value after pressing:", GPIO.input(BUTTON_PIN))
            green_thread.start()

            if loop_active:
                if question_counter != last_question_counter or initial_run:
                    prompt = generate_dynamic_prompt()
                    last_question_counter = question_counter
                    time.sleep(0.1)

        
                    # Aufnahme starten
                    voice_recorder = VoiceRecorder()
                    audio_stream = voice_recorder.record_audio()
                    green_thread.join()
                    strip.fill((0, 0, 0))
                    #strip.fill((0, 0, 0))
                    strip.show()

                    # Frage aus Audio extrahieren
                    question, question_language = speech_to_text(audio_stream)
                    history.append({"role": "user", "content": question})
                    question_counter += 1

                    subprocess.run(["mpg123", "audio/understood.mp3"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
                    print("question language:", question_language)
                    print("question_counter:", question_counter)

                # Antworten
                if loop_active and question_counter <= 2:
                    response, _ = query_chatgpt(question, prompt, history)
                    history.append({"role": "assistant", "content": response})

                    if config["tech_config"]["use_elevenlabs"]:
                        response_audio = elevenlabs_tts(response)
                    else:
                        response_audio = text_to_speech(response)
                    play_audio(response_audio)
                    time.sleep(0.1)

                # Nach 2 Fragen automatisch verabschieden
                elif loop_active and question_counter >= 2:
                    print("loop_active is now False, ending conversation.")
                    time.sleep(0.1)
                    loop_active = False

                    random_goodbye = random.choice(config["goodbyes"])
                    print("random_goodbye_text:", random_goodbye["text"])
                    goodbye_audio = elevenlabs_tts(random_goodbye["text"])
                    play_audio(goodbye_audio)

                    # Reset
                    history = []
                    question_counter = 0
                    last_question_counter = 0

            else:
                time.sleep(0.1)

    finally:
        GPIO.cleanup()
        strip.fill((0, 0, 0))
        strip.show()
        strip.close()
        print("💤 LEDs aus, Verbindung geschlossen.")


if __name__ == "__main__":
    print("Howdy, Coder! 👩‍💻👨‍💻👋")
    main()
