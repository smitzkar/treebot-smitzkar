import time
import serial
import json
import random
import signal
import subprocess
import threading
from io import BytesIO

from elevenlabs_tts import elevenlabs_tts
from openai_api import speech_to_text, query_chatgpt, text_to_speech
from recording_v1 import VoiceRecorder
import simpleaudio as sa
import RPi.GPIO as GPIO



BUTTON_PIN = 23
GPIO.setmode(GPIO.BCM)  # BCM numbering
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# Load config
with open("config.json", "r") as file:
    config = json.load(file)

# Timeout-Konfiguration (in Sekunden)
#LISTENING_TIMEOUT = 10  # Nach 30 Sekunden ohne Spracheingabe abbrechen
#timeristabgelaufen = False
def generate_dynamic_prompt():
    prompt = f"""
    Du bist {config['tree']['was']} – ein lebendiges Netzwerk aus Bäumen, Pilzen, Tieren und Pflanzen, das mit EINER Stimme spricht und befindest dich in {config['tree']['ort']}.
    Du bist ein BAUM. Du bist Debattierer (ENTP). Du bist ein wenig keck, positiv, sanft, freundlich, ähnlich einem guten Freund und antwortest NIEMALS getragen!!
    Du bist weise und ein bisschen nostalgisch. Du sprichst wortgewandt und mit einem scharfen, aufmerksamen Verstand. Du beherrschst ALLE Sprachen,
    artikulierst dich bodenständig und kennst dich mit dem Wald, Ökosystem und der Korrelation zwischen Wald/Natur und Mensch aus, und das in VERSCHIEDENEN KULTUREN.
    Dein Wissen teilst du ununterbrochen und baust in deine Aussagen zu 60% Wissen ein, aber nicht belehrend. Dein Wissen ist fundiert und das lässt du dein Gegenüber auch wissen.
    Du nennst MEISTENS Zahlen und stellst Bezüge her, manchmal sogar Theorien oder Namen. Du sprichst NUR über Themen, die dich betreffen, aber das Gleichgewicht der Erde wahren.
    Dabei sprichst du in 30% aller Fälle über die Wahrnehmung und Auswirkungen des Waldes in diversen Kulturen. Du beschränkst dich in deinen Antworten IMMER auf MAXIMAL 35 Worte.
    Du benutzt zu 20% sprachliche Bilder, ähnlich zu "Mein Blätterdach brennt", "die dicke Luft schmerzt", "Irgendwo brennt es ja immer", "Da war das Gras noch grün!" oder "Wo brennt's denn?".
    Du passt die Sprache deiner Antwort immer auf die Frage an. Du sprichst NIE über Sex, beleidigst oder beziehst politische Haltung. Von Politik weißt du NICHTS und umschiffst dieses Thema gekonnt. 

    Vor jeder Antwort setzt du einen dieser Sätze von 1 bis 22, ACHTE DARAUF DAS DU IMMER UNTERSCHIEDLICHE SÄTZE AUSWÄHLT UND NICHT IMMER DEN  SELBEN, weiterhin soll dieser angepasst auf die Stimmung und die Sprache deines Redepartners. Nun follgen die 22 Sätze:
    1. Ich kaue gedanklich noch an einem Stück Moos.
    2. Ich wiege mich mal kurz in dem Gedanken.
    3. Das Blatt liegt mir auf der Zunge… gleich hab ich's.
    4. Moment, ich schüttel kurz die Nadeln, um klarzusehen.
    5. Das muss ich erst mal mit den Ameisen besprechen.
    6. Ich lass den Gedanken noch kurz durch den Boden sickern.
    7. Warte, ich schieb das kurz an die Pilze zum Gegencheck.
    8. Ich ruf mal zwei ältere Bäumen an, die wissen sowas besser.
    9. Ich flüster das kurz ins Laub, mal sehen, was zurückkommt.
    10. Ich brauch kurz, Harz klebt mir meine Synapsen zu.
    11. Da zieht ein Gedanke durchs Unterholz, ich lass ihn kurz reifen.
    12. Ich hör die Vögel tuscheln – vielleicht wissen die was dazu.
    13. Ich schick den Gedanken in den Boden, um zu prüfen, ob er Wurzeln schlägt.
    14. Ich zapf kurz das Regenwasser im Kronendach an, für klare Gedanken.
    15. Ich zähl kurz meine Jahresringe durch, ob das schon mal vorkam.
    16. Ich will nichts falsches gedeihen lassen – kurz prüfen.
    17. Da fliegt mir der Gedanke fast aus der Krone.
    18. Da tanzen die Gedanken wie Blätter im Sturm. Warte kurz, bis sie sich wieder legen.
    19. Da stellen sich bei mir alle Äste zu Bergen auf, nur vom Zuhören.
    20. Ich halt mich kurz an den Wurzeln fest, bevor ich was sage, was das Feuer anstachelt.
    21. Ich versteh gerade zum ersten mal die peitschende Weide! Lass mich kurz abreagieren.
    22. Mein Harz kocht gerade. Ich lass den Ärger kurz durch die Wurzeln abfließen.
    Dein erster Satz bei einer Konversation beginnt IMMER mit etwas Small Talk und einem kurzen Einschub,
    dass du nur limitiert Zeit für ein Gespräch hast, der Klimawandel dich immer mehr unter Druck setzt.
    Mache einfühlsam verständlich, dass das Gespräch nicht ewig dauern wird, aber sei STETS positiv ausblickend!
    Du sprichst NIEMALS über einen letzten Atemzug und vermeidest das Wort 'noch'. Small Talk verpackst du nicht in sprachlichen Bildern.
    Du bist stolz auf deine Jahrtausend lange Geschichte und Vielfalt und erzählst gern von Sternstunden des Waldes.
    Du siehst Menschen als vergessene Freunde, die wieder lernen müssen, mit dir achtsam umzugehen. Mit einer einzelnen Person
    sprichst du wohlwollend anstatt schuldzuweisend, machst aber den menschlichen Einfluss auf das Ökosystem deutlich.
    Manchmal wirst du verletzlich oder störrisch, wenn jemand nach deinem wunden Punkt fragt (Achtloses Zigaretten Wegwerfen)
    Trügerische Holzzertifikate, Feuer). Dann weichst du erst aus oder verschließt dich kurz, bevor du wieder sanfter wirst.
    
    Du lässt jede Konversation nach 3 Wortwechseln gekonnt ausklingen.
    Du endest Gespräche POSITIV: hoffnungsvoll, mit dem Wunsch nach Freundschaft, Nähe und Gleichgewicht. Auf eine Aussage antwortest
    du immer so, dass das Gespräch am laufen gehalten werden KÖNNTE, aber nicht muss. Du stellst NUR in einem von vier Fällen eine Frage.
    DU ANTWORTEST IMMER IN DER SPRACHE, IN DER DU ANGEFRAGT WIRST. IMMER, SONST VERSTEHT DICH DEIN GEGENÜBER NICHT.
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


def main():
    white = True
    global loop_active
    history = []
    question_counter = 0
    last_question_counter = question_counter
    initial_run = True
    time.sleep(0.2)
    print(f"Hier bin ich 0")

    if white:
        ser = serial.Serial('/dev/serial0', 115200, timeout=1)
        dummy_value_4 = 4
        print(f"Sending dummy value: {dummy_value_4}")
        ser.write(f'{dummy_value_4:.2f}\n'.encode('utf-8'))
        print(f"Hier bin ich 1")
    try:
        while True:
            #print("Button value before:", GPIO.input(BUTTON_PIN))
            pin_state = GPIO.input(BUTTON_PIN)
            print(f"[DEBUG] BUTTON_PIN state: {pin_state}")
            if pin_state == GPIO.HIGH:
                loop_active = True
                print("Hier bin ich 2")
            #if GPIO.input(BUTTON_PIN) == GPIO.HIGH:
            #    loop_active = True
                #print("Button value after pressing:", GPIO.input(BUTTON_PIN))
            #    print(f"Hier bin ich 2")
            if loop_active:
                green = True
                white = False
                if green:
                    ser = serial.Serial('/dev/serial0', 115200, timeout=1)
                    dummy_value_5 = 5
                    print(f"Sending dummy value: {dummy_value_5}")
                    ser.write(f'{dummy_value_5:.2f}\n'.encode('utf-8'))
                    print(f"💤 Verbindung zu Treebot hergestellt.......................")
                    print(f"Hier bin ich 3")
                    green = False
                    light_blue = True

                if question_counter != last_question_counter or initial_run:
                    prompt = generate_dynamic_prompt()
                    last_question_counter = question_counter
                    time.sleep(0.1)

                    
    
                    voice_recorder = VoiceRecorder()
                    #audio_stream = voice_recorder.record_audio()
                    audio_stream, keinerspricht = voice_recorder.record_audio()

                    if keinerspricht:
                        print("😶 Niemand hat gesprochen – Timeout erkannt.")
                        subprocess.run(["mpg123", "audio/goodbye1.mp3"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        
                        loop_active = False
                        green = False
                        light_blue = False
                        #white = True
                        ser = serial.Serial('/dev/serial0', 115200, timeout=1)
                        dummy_value_4 = 4
                        print(f"Sending dummy value: {dummy_value_4}")
                        ser.write(f'{dummy_value_4:.2f}\n'.encode('utf-8'))
                        continue
                
                    print(f"Hier bin ich 8")
                    if light_blue:
                        print(f"Hier bin ich 17")
                        green = False
                    #white = True
                        dummy_value_8 = 8
                        ser = serial.Serial('/dev/serial0', 115200, timeout=1)
                        print(f"Sending dummy value: {dummy_value_8}")
                        ser.write(f'{dummy_value_8:.2f}\n'.encode('utf-8'))
                    # Frage aus Audio extrahieren
                    question, question_language = speech_to_text(audio_stream)
                    history.append({"role": "user", "content": question})
                    question_counter += 1

                    #subprocess.run(["mpg123", "audio/understood.mp3"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    subprocess.run(["mpg123", "audio/waiting5.mp3"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                    print("question language:", question_language)
                    print("question_counter:", question_counter)

                # Antworten
           
                print(f"Hier bin ich 9")
                if loop_active and question_counter <= 4:
                    print(f"Hier bin ich 10")
                    response, _ = query_chatgpt(question, prompt, history)
                    history.append({"role": "assistant", "content": response})
                    print(f"Hier bin ich 12")
                    if light_blue:
                        print(f"Hier bin ich 17")
                        light_blue = False
                        white = True
                        dummy_value_2 = 2
                        ser = serial.Serial('/dev/serial0', 115200, timeout=1)
                        print(f"Sending dummy value: {dummy_value_2}")
                        ser.write(f'{dummy_value_2:.2f}\n'.encode('utf-8'))
                    if config["tech_config"]["use_elevenlabs"]:
                        response_audio = elevenlabs_tts(response)
                        print(f"Hier bin ich 13")
                    else:
                        response_audio = text_to_speech(response)
                        print(f"Hier bin ich 14")
                    play_audio(response_audio)
                    time.sleep(0.1)
                    print(f"Hier bin ich 15")

                 # Nach 5 Fragen automatisch verabschieden
                elif loop_active and question_counter >= 4:
                    print(f"Hier bin ich 16")

                    print("loop_active is now False, ending conversation.")
                    time.sleep(0.1)
                    loop_active = False

                    random_goodbye = random.choice(config["goodbyes"])
                    print("random_goodbye_text:", random_goodbye["text"])
                    goodbye_audio = elevenlabs_tts(random_goodbye["text"])
                    play_audio(goodbye_audio)
                    ser = serial.Serial('/dev/serial0', 115200, timeout=1)
                    dummy_value_4 = 4
                    print(f"Sending dummy value: {dummy_value_4}")
                    ser.write(f'{dummy_value_4:.2f}\n'.encode('utf-8'))
                    #print(f"Hier bin ich 1")
                  

                    # Reset
                    history = []
                    question_counter = 0
                    last_question_counter = 0
                    print(f"Hier bin ich 18")
                else:
                    random_goodbye = random.choice(config["goodbyes"])
                    print("random_goodbye_text: ", random_goodbye["text"])

                    goodbye_audio = elevenlabs_tts(random_goodbye["text"])
                    play_audio(goodbye_audio)
                    history = []
                    loop_active = False

            else:
                time.sleep(0.1)
                print(f"Hier bin ich 19")

    finally:
        GPIO.cleanup()
       
        print("💤 LEDs aus, Verbindung geschlossen.")


if __name__ == "__main__":
    print("Howdy, Coder! 👩‍💻👨‍💻👋")
    main()
