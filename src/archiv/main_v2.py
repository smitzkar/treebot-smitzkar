import time
import serial
import json
import random
import signal
import subprocess
from io import BytesIO

from elevenlabs_tts import elevenlabs_tts
from openai_api import speech_to_text, query_chatgpt, text_to_speech
from recording import VoiceRecorder
import simpleaudio as sa
import RPi.GPIO as GPIO



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
loop_active = False

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
    
    try:
        while True:
            print("Button value before:", GPIO.input(BUTTON_PIN))
            if GPIO.input(BUTTON_PIN) == GPIO.HIGH:
                loop_active = True
                print("Button value after pressing:", GPIO.input(BUTTON_PIN))
            
            if loop_active:
                green = True
                if green:
                    ser = serial.Serial('/dev/serial0', 115200, timeout=1)
                    dummy_value = 1
                    print(f"Sending dummy value: {dummy_value}")
                    ser.write(f'{dummy_value:.2f}\n'.encode('utf-8'))

                if question_counter != last_question_counter or initial_run:
                    prompt = generate_dynamic_prompt()
                    last_question_counter = question_counter
                    time.sleep(0.1)

        
                    # Aufnahme starten
                    voice_recorder = VoiceRecorder()
                    audio_stream = voice_recorder.record_audio()
                   
                    if green:
                        green = False
                        blue = True
                        dummy_value_1 = 2
                        print(f"Sending dummy value: {dummy_value_1}")
                        ser.write(f'{dummy_value_1:.2f}\n'.encode('utf-8'))

                    # Frage aus Audio extrahieren
                    question, question_language = speech_to_text(audio_stream)
                    history.append({"role": "user", "content": question})
                    question_counter += 1

                    subprocess.run(["mpg123", "audio/understood.mp3"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
                    print("question language:", question_language)
                    print("question_counter:", question_counter)

                    #ser = serial.Serial('/dev/serial0', 115200, timeout=1)
                    #dummy_value_2 = 2
                    #print(f"Sending dummy value: {dummy_value_2}")
                    #ser.write(f'{dummy_value_2:.2f}\n'.encode('utf-8'))

                # Antworten

                if loop_active and question_counter <= 2:
                    if blue:
                        blue = False
                        white = True
                        dummy_value_2 = 3
                        print(f"Sending dummy value: {dummy_value_2}")
                        ser.write(f'{dummy_value_1:.2f}\n'.encode('utf-8'))
                    response, _ = query_chatgpt(question, prompt, history)
                    history.append({"role": "assistant", "content": response})

                    if config["tech_config"]["use_elevenlabs"]:
                        response_audio = elevenlabs_tts(response, filename)
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
                    if white:
                        white = False
                        dummy_value_3 = 4
                        print(f"Sending dummy value: {dummy_value_3}")
                        ser.write(f'{dummy_value_2:.2f}\n'.encode('utf-8'))

                    # Reset
                    history = []
                    question_counter = 0
                    last_question_counter = 0

            else:
                time.sleep(0.1)

    finally:
        GPIO.cleanup()
       
        print("💤 LEDs aus, Verbindung geschlossen.")


if __name__ == "__main__":
    print("Howdy, Coder! 👩‍💻👨‍💻👋")
    main()
