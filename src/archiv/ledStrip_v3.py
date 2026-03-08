import spidev
import time

class WS2812B_SPI:
    """WS2812B LED-Streifen über SPI mit korrektem Timing."""
    
    def __init__(self, spi_bus=0, spi_device=0, num_pixels=16):
        self.num_pixels = num_pixels
        self.spi = spidev.SpiDev()
        self.spi.open(spi_bus, spi_device)
        self.spi.max_speed_hz = 6400000
        self.spi.mode = 0
        self.spi.lsbfirst = False
        self.pixels = [(0, 0, 0)] * num_pixels

        # SPI-Bit-Mapping für WS2812B
        self.bit_map = {
            0b00: 0b10001000,
            0b01: 0b10001110,
            0b10: 0b11101000,
            0b11: 0b11101110,
        }

    def _byte_to_spi(self, byte):
        spi_bytes = []
        for i in range(3, -1, -1):
            bits = (byte >> (i * 2)) & 0b11
            spi_bytes.append(self.bit_map[bits])
        return spi_bytes

    def fill(self, color):
        self.pixels = [color] * self.num_pixels

    def set_pixel(self, index, color):
        if 0 <= index < self.num_pixels:
            self.pixels[index] = color

    def show(self):
        spi_data = []
        for r, g, b in self.pixels:
            for byte in [g, r, b]:
                spi_data.extend(self._byte_to_spi(byte))
        self.spi.xfer2(spi_data)
        time.sleep(0.0001)  # Reset >50µs

    def close(self):
        self.spi.close()


# === FERTIGE PULS-FUNKTIONEN ===
def puls_red(strip, steps=50, delay=0.03, cycles=6):
    """Lässt den LED-Streifen in Rot pulsieren."""
    for _ in range(cycles):
        # Fade UP
        for i in range(steps + 1):
            brightness = (i + 3) / steps
            strip.fill((int(255 * brightness), 0, 0))
            strip.show()
            time.sleep(delay)
        # Fade DOWN
        for i in range(steps, -1, -1):
            brightness = i / steps
            strip.fill((int(255 * brightness), 0, 0))
            strip.show()
            time.sleep(delay)


def puls_blue(strip, steps=50, delay=0.03, cycles=1):
    """Lässt den LED-Streifen in Blau pulsieren."""
    for _ in range(cycles):
        # Fade UP
        for i in range(steps + 1):
            brightness = i / steps
            strip.fill((0, 0, int(255 * brightness)))
            strip.show()
            time.sleep(delay)
        # Fade DOWN
        for i in range(steps, -1, -1):
            brightness = i / steps
            strip.fill((0, 0, int(255 * brightness)))
            strip.show()
            time.sleep(delay)

def init_leds(strip, color=(0, 255, 0), delay=0.05):
    """Schaltet jede LED nacheinander ein, um sicherzustellen, dass alle aktiv sind."""
    for i in range(strip.num_pixels):
        strip.set_pixel(i, color)
        strip.show()
        time.sleep(delay)
    # Danach alles an
    strip.fill(color)
    strip.show()
    time.sleep(0.5)


def puls_green(strip, steps=50, delay=0.05, cycles=1):
    """Lässt den LED-Streifen in Grün pulsieren (startet hell)."""
    # Initialisiere LEDs einmal komplett
    init_leds(strip, color=(0, 255, 0), delay=0.05)

    for _ in range(cycles):
        # Fade DOWN (hell → dunkel)
        for i in range(steps + 1):
            brightness = 1 - (i / steps)
            strip.fill((0, int(255 * brightness), 0))
            strip.show()
            time.sleep(delay)

        # Fade UP (dunkel → hell)
        for i in range(steps + 1):
            brightness = i / steps
            strip.fill((0, int(255 * brightness), 0))
            strip.show()
            time.sleep(delay)

def puls_white(strip):
    """Schaltet den LED-Streifen dauerhaft auf Weiß (volle Helligkeit)."""
    strip.fill((255, 255, 255))  # Alle LEDs auf Weiß
    strip.show()




#def puls_white(strip, steps=100, delay=0.03, cycles=1):
#    """Lässt den LED-Streifen in Weiß pulsieren."""
    
    #for _ in range(cycles):
     #   for i in range(steps + 1):
     #       brightness = i / steps
     #       val = int(255 * brightness)
     #       strip.fill((val, val, val))
     #       strip.show()
     #       time.sleep(delay)
     #   for i in range(steps, -1, -1):
     #       brightness = i / steps
     #       val = int(255 * brightness)
     #       strip.fill((val, val, val))
     #       strip.show()
     #       time.sleep(delay)

def leds_hochfahren(strip, farbe=(0, 255, 0), delay=0.1):
    """
    Schaltet die LEDs nacheinander ein.
    farbe: (R, G, B)
    delay: Wartezeit zwischen LEDs
    """
    strip.fill((0, 0, 0))  # alle aus
    strip.show()
    time.sleep(0.2)

    for i in range(strip.num_pixels):
        strip.set_pixel(i, farbe)
        strip.show()
        time.sleep(delay)