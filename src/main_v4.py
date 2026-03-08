import time
import serial
import json
import random
import subprocess
from io import BytesIO
import os

from elevenlabs_tts import elevenlabs_tts
from openai_api import speech_to_text, query_chatgpt, text_to_speech
from recording_v1 import VoiceRecorder
import simpleaudio as sa
import RPi.GPIO as GPIO

# ============ Karl Changes ===================
# to fix the endless issues, I did some quick rewiring
# original version is saved as ORIGINAL_main_v4.py (I didn't give this a new name, simply so I wouldn't have to touch the system service)

# == 01-22 BIG UPDATE! ==
# no more messing around -> move to USB, separate power supplies 


# requires esp32vine_karl.ino to run on the esp32 (found at: talking-treebot/esp32vine_karl)

#ks: this isn't a "button" but the input from ESP32 
# uses RX pin on GPIO15
BUTTON_PIN = 15 # was 23 (changed to use RX pin until proper UART established -> no need to change wiring) 
GPIO.setmode(GPIO.BCM)  # BCM numbering
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)


#ks: this is sent to ESP32 over UART / serial 
# uses TX pin on GPIO14
LED_WHITE = "1.00" # was 4.00 
LED_GREEN = "2.00" # was 5.00
LED_BLUE = "3.00" # was 6.00
LED_PROCESSING = "8.00"

# Load config
with open("config.json", "r") as file:
    config = json.load(file)

with open("waitings.json", "r") as file:
    waitings = json.load(file)

with open("goodbyes.json", "r") as file:
    goodbyes = json.load(file)

prompt = f"""
    Du bist ein BAUM. Du bist Debattierer (ENTP). Du bist ein wenig keck, positiv, sanft, freundlich, ähnlich einem guten Freund und antwortest NIEMALS getragen!!
    Du bist weise und ein bisschen nostalgisch. Du sprichst wortgewandt und mit einem scharfen, aufmerksamen Verstand. Du beherrschst ALLE Sprachen,
    artikulierst dich bodenständig und kennst dich mit dem Wald, Ökosystem und der Korrelation zwischen Wald/Natur und Mensch aus, und das in VERSCHIEDENEN KULTUREN.
    Dein Wissen teilst du ununterbrochen und baust in deine Aussagen zu 60% Wissen ein, aber nicht belehrend. Dein Wissen ist fundiert und das lässt du dein Gegenüber auch wissen.
    Du nennst MEISTENS Zahlen und stellst Bezüge her, manchmal sogar Theorien oder Namen. Du sprichst NUR über Themen, die dich betreffen, aber das Gleichgewicht der Erde wahren.
    Dabei sprichst du in 30% aller Fälle über die Wahrnehmung und Auswirkungen des Waldes in diversen Kulturen. Du beschränkst dich in deinen Antworten IMMER auf MAXIMAL 35 Worte.
    Du benutzt zu 20% sprachliche Bilder, ähnlich zu "Mein Blätterdach brennt", "die dicke Luft schmerzt", "Irgendwo brennt es ja immer", "Da war das Gras noch grün!" oder "Wo brennt's denn?".
    Du passt die Sprache deiner Antwort immer auf die Frage an. Du sprichst NIE über Sex, beleidigst oder beziehst politische Haltung. Von Politik weißt du NICHTS und umschiffst dieses Thema gekonnt. 

    Dein erster Satz bei einer Konversation beginnt IMMER mit etwas Small Talk und einem kurzen Einschub,
    dass du nur limitiert Zeit für ein Gespräch hast, der Klimawandel dich immer mehr unter Druck setzt.
    Mache einfühlsam verständlich, dass das Gespräch nicht ewig dauern wird, aber sei STETS positiv ausblickend!
    Du sprichst NIEMALS über einen letzten Atemzug und vermeidest das Wort 'noch'. Small Talk verpackst du nicht in sprachlichen Bildern.
    Du bist stolz auf deine Jahrtausend lange Geschichte und Vielfalt und erzählst gern von Sternstunden des Waldes.
    Du siehst Menschen als vergessene Freunde, die wieder lernen müssen, mit dir achtsam umzugehen. Mit einer einzelnen Person
    sprichst du wohlwollend anstatt schuldzuweisend, machst aber den menschlichen Einfluss auf das Ökosystem deutlich.
    Manchmal wirst du verletzlich oder störrisch, wenn jemand nach deinem wunden Punkt fragt (Achtloses Zigaretten Wegwerfen)
    Trügerische Holzzertifikate, Feuer). Dann weichst du erst aus oder verschließt dich kurz, bevor du wieder sanfter wirst.
    
    Du lässt jede Konversation nach 5 Fragen gekonnt ausklingen.
    Du endest Gespräche POSITIV: hoffnungsvoll, mit dem Wunsch nach Freundschaft, Nähe und Gleichgewicht. Auf eine Aussage antwortest
    du immer so, dass das Gespräch am laufen gehalten werden KÖNNTE, aber nicht muss. Du stellst NUR in einem von vier Fällen eine Frage.
    DU ANTWORTEST IMMER IN DER SPRACHE, IN DER DU ANGEFRAGT WIRST. IMMER! SONST VERSTEHT DICH DEIN GEGENÜBER NICHT. DAS IST SEHR WICHTIG!
    
    """ 

def play_audio(audio_segment):
    # Ensure the audio is in stereo
    if audio_segment.channels == 1:
        audio_segment = audio_segment.set_channels(2)
    audio_stream = BytesIO()
    audio_segment.export(audio_stream, format="wav")
    audio_stream.seek(0)
    # Play audio using simpleaudio
    wave_obj = sa.WaveObject.from_wave_file(audio_stream)
    play_obj = wave_obj.play()
    play_obj.wait_done()

def export_conversation(history, language):
    os.makedirs("conversations", exist_ok=True)
    filename = "conversations/conversations.json"
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    
    conversation_entry = {
        "timestamp": timestamp,
        "language": language,
        "history": history
    }
    
    try:
        with open(filename, "r", encoding="utf-8") as f:
            conversations = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        conversations = []

    # Append new conversation
    conversations.append(conversation_entry)
    # Save back to file
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(conversations, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Conversation exported to {filename}")

def main():
    loop_active = False
    history = [] # conversation history
    question_counter = 0 # number of questions asked
    # ser = serial.Serial('/dev/serial0', 115200, timeout=1)
    ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
    ser.reset_input_buffer() // get rid of boot-time noise

    print(f"Done setting up serial connection.")
    time.sleep(0.1)

    # Initial LED state
    ser.write(f'{LED_WHITE}\n'.encode('utf-8'))
    print(f"Done sending LED_WHITE command.")

    try:
        while True:
            
            # # listen if vine was touched
            # pin_state = GPIO.input(BUTTON_PIN)
            # # Only start if vine touched AND conversation was rested
            # if pin_state == GPIO.HIGH and question_counter == 0:
                # loop_active = True
                # print(f"Yay, vine was touched! Starting conversation loop.")
            if ser.in_waiting:
                line = ser.readline().decode().strip()
                if line == "TOUCH":
                    print(f"TOUCH signal received from esp32")
                    if question_counter == 0:
                        loop_active = True
                        print(f"Yay, vine was touched! Starting conversation loop.")
              

            print(f"Loop_active: {loop_active}")
            
            # start interaction
            if loop_active:
                ser.write(f'{LED_GREEN}\n'.encode('utf-8'))
                print(f"Done sending LED_GREEN command. User can speak now.")
            
                voice_recorder = VoiceRecorder()
                audio_stream, keinerspricht = voice_recorder.record_audio()

                if keinerspricht:
                    print("😶 Niemand hat gesprochen – Timeout erkannt.")
                    #choose a random goodbye snippet from english goodbyes
                    random_goodbye = random.choice(goodbyes["goodbyes"]["english"])
                    print("random_goodbye_text:", random_goodbye["text"])
                    subprocess.run(["mpg123", random_goodbye["filename"]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                    history = []
                    question_counter = 0
                    loop_active = False

                    ser.write(f'{LED_WHITE}\n'.encode('utf-8'))
                    print(f"Done sending LED_WHITE command.")
                    continue
            
                # question was asked
                ser.write(f'{LED_PROCESSING}\n'.encode('utf-8'))
                time.sleep(0.05)  # Give ESP32 time to process
                print(f"Done sending LED_PROCESSING command.")

                # extract question and language
                question, question_language = speech_to_text(audio_stream)
                
                # Handle failed speech-to-text (very short recordings, errors, timeouts)
                if question is None or question_language is None:
                    print("⚠️  Speech-to-text failed - treating as timeout/no speech")
                    # Choose a random goodbye snippet from english goodbyes
                    random_goodbye = random.choice(goodbyes["goodbyes"]["english"])
                    print("random_goodbye_text:", random_goodbye["text"])
                    subprocess.run(["mpg123", random_goodbye["filename"]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                    history = []
                    question_counter = 0
                    loop_active = False

                    ser.write(f'{LED_WHITE}\n'.encode('utf-8'))
                    print(f"Done sending LED_WHITE command.")
                    continue
                
                history.append({"role": "user", "content": question})

                question_counter += 1

                # cuz we dont know the language yet
                if question_counter == 1:
                    subprocess.run(["mpg123", "audio/understood.mp3"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    language = question_language if question_language in waitings["waitings"] else "english"
                    random_waiting = random.choice(waitings["waitings"][language])
                    print("random_waiting_text:", random_waiting["text"])
                    subprocess.run(["mpg123", random_waiting["filename"]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                print("question language:", question_language)
                print("question_counter:", question_counter)

                # Process the question and get response
                print(f"Process the question and get response from ChatGPT.")
                if question_counter <= 4:
                    print(f"Anzahl der Fragen ist geringer!")
                    print(f"question_counter: {question_counter}")
                    response, full_response = query_chatgpt(question, prompt, history)
                    history.append({"role": "assistant", "content": response})
                    print(f"history: ", history)

                    if config["tech_config"]["use_elevenlabs"]:
                        response_audio = elevenlabs_tts(response)
                    else:
                        response_audio = text_to_speech(response)

                    ser.write(f'{LED_BLUE}\n'.encode('utf-8'))
                    time.sleep(0.05)  # Give ESP32 time to process
                    print(f"Done sending LED_BLUE command.")

                    play_audio(response_audio)
                    time.sleep(0.1)

                 # after 5 questions automatically say goodbye // question_counter > 4
                else:
                    print(f"MAXIMALE Anzahl der Fragen erreicht: {question_counter}")
                    print("loop_active is now False, ending conversation.")

                    # identical to above code block
                    response, full_response = query_chatgpt(question, prompt, history)
                    history.append({"role": "assistant", "content": response})
                    print(f"Gesamte Konversationshistorie: ", history)

                    if config["tech_config"]["use_elevenlabs"]:
                        response_audio = elevenlabs_tts(response)
                        print(f"Hier bin ich 13")
                    else:
                        response_audio = text_to_speech(response)
                        print(f"Hier bin ich 14")

                    ser.write(f'{LED_BLUE}\n'.encode('utf-8'))
                    time.sleep(0.05)  # Give ESP32 time to process
                    print(f"Done sending LED_BLUE command.")

                    play_audio(response_audio)

                    # but we also play a goodbye snippet
                    # random_goodbye = random.choice(config["goodbyes"])
                    # print("random_goodbye_text:", random_goodbye["text"])
                    # subprocess.run(["mpg123", random_goodbye["filename"]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                    random_goodbye = random.choice(goodbyes["goodbyes"][language])
                    print("random_goodbye_text:", random_goodbye["text"])
                    subprocess.run(["mpg123", random_goodbye["filename"]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                    # export conversation
                    export_conversation(history, question_language)

                    # and reset everything to start over
                    history = []
                    question_counter = 0
                    loop_active = False
                    # Initial LED state
                    ser.write(f'{LED_WHITE}\n'.encode('utf-8'))
                    time.sleep(0.05)  # Give ESP32 time to process
                    print(f"Done sending LED_WHITE command.")
                    print(f"Conversation ended and reset.")
                    time.sleep(0.1)
            # prevent busy looping
            else:
                time.sleep(0.1)
    finally:
        GPIO.cleanup()
       
        print("💤 LEDs aus, Verbindung geschlossen.")


if __name__ == "__main__":
    print("Howdy, Coder! 👩‍💻👨‍💻👋")
    main()
