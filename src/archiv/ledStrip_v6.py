#!/usr/bin/env python3
# NeoPixel library strandtest example + Puls-Effekte (Grün/Blau)
# Author: Tony DiCola (original) — Puls-Erweiterung integriert

import time
from rpi_ws281x import *
import argparse

# LED strip configuration:
LED_COUNT      = 16     # Anzahl der LEDs.
LED_PIN        = 12     # GPIO-Pin (18/12/13/19 sind PWM/PCM-fähig; 18 ist Standard-PWM).
#LED_PIN       = 10     # SPI (/dev/spidev0.0) — nur falls SPI genutzt wird.
LED_FREQ_HZ    = 800000 # WS2812B-Frequenz (800 kHz)
LED_DMA        = 10     # DMA-Kanal
LED_BRIGHTNESS = 65     # 0..255
LED_INVERT     = False  # ggf. invertiertes Signal
LED_CHANNEL    = 0      # 0 oder 1 (je nach Pin)

# ------------------------------------------------------------
# Hilfsfunktionen (Original)
# ------------------------------------------------------------
def colorWipe(strip, color, wait_ms=50):
    """Färbt die LEDs nacheinander in 'color'."""
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
        strip.show()
        time.sleep(wait_ms/1000.0)

def theaterChase(strip, color, wait_ms=50, iterations=10):
    """Theater-Chase-Effekt."""
    for j in range(iterations):
        for q in range(3):
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i+q, color)
            strip.show()
            time.sleep(wait_ms/1000.0)
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i+q, 0)

def wheel(pos):
    """Erzeugt Regenbogenfarben über Position 0-255."""
    if pos < 85:
        return Color(pos * 3, 255 - pos * 3, 0)
    elif pos < 170:
        pos -= 85
        return Color(255 - pos * 3, 0, pos * 3)
    else:
        pos -= 170
        return Color(0, pos * 3, 255 - pos * 3)

def rainbow(strip, wait_ms=20, iterations=1):
    """Regenbogen über alle Pixel gleichzeitig."""
    for j in range(256*iterations):
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, wheel((i+j) & 255))
        strip.show()
        time.sleep(wait_ms/1000.0)

def rainbowCycle(strip, wait_ms=20, iterations=5):
    """Regenbogen gleichmäßig über den Streifen verteilt."""
    for j in range(256*iterations):
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, wheel((int(i * 256 / strip.numPixels()) + j) & 255))
        strip.show()
        time.sleep(wait_ms/1000.0)

def theaterChaseRainbow(strip, wait_ms=50):
    """Theater-Chase mit Regenbogenfarben."""
    for j in range(256):
        for q in range(3):
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i+q, wheel((i+j) % 255))
            strip.show()
            time.sleep(wait_ms/1000.0)
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i+q, 0)

# ------------------------------------------------------------
# Puls-Effekte (NEU)
# ------------------------------------------------------------
def _scale_color(r, g, b, k):
    """Skaliert eine RGB-Farbe mit Faktor k (0..1)."""
    return Color(int(r * k), int(g * k), int(b * k))

def puls_color(strip, base_rgb, steps=50, delay_ms=30, cycles=2, max_brightness=0.5):
    """Sanftes Pulsieren einer Basisfarbe (hell←→dunkel)."""
    r, g, b = base_rgb
    # Fade UP
    for _ in range(cycles):
        for i in range(steps + 1):
            k = (i / steps) * max_brightness
            c = _scale_color(r, g, b, k)
            for p in range(strip.numPixels()):
                strip.setPixelColor(p, c)
            strip.show()
            time.sleep(delay_ms/1000.0)
        # Fade DOWN
        for i in range(steps, -1, -1):
            k = (i / steps) * max_brightness
            c = _scale_color(r, g, b, k)
            for p in range(strip.numPixels()):
                strip.setPixelColor(p, c)
            strip.show()
            time.sleep(delay_ms/1000.0)

def puls_green(strip, steps=50, delay_ms=30, cycles=2, max_brightness=0.4):
    """Grün sanft pulsieren (ruhig, ohne Flackern)."""
    puls_color(strip, (0, 255, 0), steps=steps, delay_ms=delay_ms, cycles=cycles, max_brightness=max_brightness)

def puls_blue(strip, steps=50, delay_ms=30, cycles=2, max_brightness=0.5):
    """Blau sanft pulsieren."""
    puls_color(strip, (0, 0, 255), steps=steps, delay_ms=delay_ms, cycles=cycles, max_brightness=max_brightness)

# ------------------------------------------------------------
# Main
# ------------------------------------------------------------
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--clear', action='store_true', help='Clear the display on exit')
    args = parser.parse_args()

    # NeoPixel-Objekt erstellen
    strip = Adafruit_NeoPixel(
        LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL
    )
    strip.begin()

    print('Press Ctrl-C to quit.')
    if not args.clear:
        print('Use "-c" to clear LEDs on exit')

    try:
        while True:
            print('Puls-Effekte.')
            puls_green(strip, steps=40, delay_ms=20, cycles=2, max_brightness=0.35)
            puls_blue(strip,  steps=40, delay_ms=20, cycles=2, max_brightness=0.45)

            print('Color wipe animations.')
            colorWipe(strip, Color(255, 0, 0))  # Rot
            colorWipe(strip, Color(0, 255, 0))  # Grün
            colorWipe(strip, Color(0, 0, 255))  # Blau

            print('Theater chase animations.')
            theaterChase(strip, Color(127, 127, 127))  # Weiß
            theaterChase(strip, Color(127,   0,   0))  # Rot
            theaterChase(strip, Color(  0,   0, 127))  # Blau

            print('Rainbow animations.')
            rainbow(strip)
            rainbowCycle(strip)
            theaterChaseRainbow(strip)

    except KeyboardInterrupt:
        pass
    finally:
        print("💡 Turning off all LEDs before exit.")
        colorWipe(strip, Color(0, 0, 0), 10)
