from ledStrip_v3 import WS2812B_SPI, puls_red, puls_blue, puls_white
import time

# LED-Streifen initialisieren
strip = WS2812B_SPI(num_pixels=16)

try:
    
    #puls_white(strip)
    time.sleep(5)  # 5 Sekunden weiß anzeigen (oder länger)
    
    print("Rot pulsieren...")
    puls_red(strip, cycles=6)

    print("Blau pulsieren...")
    puls_blue(strip, cycles=6)
    #puls_white(strip,cycles=6)

finally:
    strip.fill((0, 0, 0))
    strip.show()
    strip.close()
