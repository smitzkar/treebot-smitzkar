import json
import random
import time
import signal
import subprocess
from io import BytesIO

from elevenlabs_tts import elevenlabs_tts
from openai_api import speech_to_text, query_chatgpt, text_to_speech
from recording import VoiceRecorder
import simpleaudio as sa
import RPi.GPIO as GPIO
from ledStrip_v6 import WS2812B_SPI

# ===== LED init =====
strip = WS2812B_SPI(num_pixels=16)

# ===== GPIO (opsiyonel; şimdilik kullanılmıyor) =====
BUTTON_PIN = 23
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# ===== Config =====
with open("config.json", "r") as file:
    config = json.load(file)

def generate_dynamic_prompt():
    return f"""
    Du bist {config['tree']['was']} – ein lebendiges Netzwerk aus Bäumen, Pilzen, Tieren und Pflanzen, das mit EINER Stimme spricht und befindest dich in {config['tree']['ort']}.
    Du bist ein BAUM. Du bist Debattierer (ENTP). Du bist ein wenig keck, positiv, sanft, freundlich, ähnlich einem guten Freund und antwortest NIEMALS getragen! Du bist weise und 
    ein bisschen nostalgisch. Du sprichst wortgewandt und mit einem scharfen, aufmerksamen Verstand. ...
    """

def play_audio(audio_segment):
    if audio_segment.channels == 1:
        audio_segment = audio_segment.set_channels(2)
    audio_stream = BytesIO()
    audio_segment.export(audio_stream, format="wav")
    audio_stream.seek(0)
    wave_obj = sa.WaveObject.from_wave_file(audio_stream)
    play_obj = wave_obj.play()
    play_obj.wait_done()

# ==== LED helper: sabit rengi güvenli şekilde "kilitle" (animasyonsuz) ====
def set_color(color, repeats=4, delay=0.006):
    """Aynı rengi art arda göndererek rengi kilitle (anti-flash)."""
    for _ in range(repeats):
        strip.fill(color)
        strip.show()
        time.sleep(delay)

# ===== loop control =====
loop_active = True
def signal_handler(signum, frame):
    global loop_active
    loop_active = not loop_active
    print(f"Received SIGUSR1 — loop_active is now {loop_active}")
signal.signal(signal.SIGUSR1, signal_handler)

def main():
    global loop_active
    history = []
    question_counter = 0
    last_question_counter = question_counter
    initial_run = True
    time.sleep(0.2)

    try:
        while True:
            loop_active = True
            if not loop_active:
                time.sleep(0.1)
                continue

            if question_counter != last_question_counter or initial_run:
                prompt = generate_dynamic_prompt()
                last_question_counter = question_counter
                time.sleep(0.05)

                # === LISTENING: sabit sönük yeşil ===
                set_color((0, 40, 0), repeats=5, delay=0.006)

                # Kayıt
                voice_recorder = VoiceRecorder()
                audio_stream = voice_recorder.record_audio()

                # Kayıt bitti → THINKING: sabit sönük mavi
                set_color((0, 0, 80), repeats=5, delay=0.006)

                # STT
                question, question_language = speech_to_text(audio_stream)
                print("question language:", question_language)

                # STT boşsa konuşma yok → IDLE (siyah)
                if not question or not str(question).strip():
                    print("No speech recognized, skipping response.")
                    set_color((0, 0, 0), repeats=4, delay=0.006)
                    initial_run = False
                    time.sleep(0.1)
                    continue

                history.append({"role": "user", "content": question})
                question_counter += 1

                subprocess.run(["mpg123", "audio/understood.mp3"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print("question_counter:", question_counter)

            # === ANSWER ===
            if loop_active and question_counter <= 2:
                response, _ = query_chatgpt(question, prompt, history)
                history.append({"role": "assistant", "content": response})

                # SPEAKING: sabit beyaz (hafif kısık)
                set_color((170, 170, 170), repeats=4, delay=0.006)

                if config["tech_config"]["use_elevenlabs"]:
                    response_audio = elevenlabs_tts(response)
                else:
                    response_audio = text_to_speech(response)
                play_audio(response_audio)

                # Konuşma bitti → IDLE
                set_color((0, 0, 0), repeats=4, delay=0.006)
                time.sleep(0.1)

            # === 2 sorudan sonra veda ve reset ===
            elif loop_active and question_counter >= 2:
                print("loop_active is now False, ending conversation.")
                time.sleep(0.1)
                loop_active = False

                random_goodbye = random.choice(config["goodbyes"])
                print("random_goodbye_text:", random_goodbye["text"])
                goodbye_audio = elevenlabs_tts(random_goodbye["text"])
                play_audio(goodbye_audio)

                history = []
                question_counter = 0
                last_question_counter = 0
                # Veda sonrası IDLE
                set_color((0, 0, 0), repeats=4, delay=0.006)

    finally:
        GPIO.cleanup()
        set_color((0, 0, 0), repeats=2, delay=0.004)
        strip.close()
        print("💤 LEDs aus, Verbindung geschlossen.")

if __name__ == "__main__":
    print("Howdy, Coder! 👩‍💻👨‍💻👋")
    main()
