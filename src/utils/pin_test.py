import RPi.GPIO as GPIO
import time

# --- Pin setup ---
BUTTON_PIN = 23
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)  # Pull-Down Widerstand

last_button_state = None  # Status merken

try:
    print("Drücke den Button...")
    while True:
        current_state = GPIO.input(BUTTON_PIN)
        
        # Nur ausgeben, wenn sich der Status ändert
        if current_state != last_button_state:
            if current_state == GPIO.HIGH:
                print("🔘 Button gedrückt")
            else:
                print("🔘 Button losgelassen")
        
        last_button_state = current_state
        time.sleep(0.05)  # Kurze Pause, um CPU zu schonen / Entprellen

except KeyboardInterrupt:
    print("\nBeende Programm...")

finally:
    GPIO.cleanup()
    print("GPIOs freigegeben")
