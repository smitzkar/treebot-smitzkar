import spidev
import time

class WS2812B_SPI:
    """WS2812B LED-Streifen über SPI mit stabilem Timing (1→1110 / 0→1000 Kodierung)."""
    
    def __init__(self, spi_bus=0, spi_device=0, num_pixels=16):
        self.num_pixels = num_pixels
        self.spi = spidev.SpiDev()
        self.spi.open(spi_bus, spi_device)
        # stabile Frequenz für WS2812B: ca. 3,2 MHz
        self.spi.max_speed_hz = 3_200_000
        self.spi.mode = 0
        self.spi.lsbfirst = False
        self.pixels = [(0, 0, 0)] * num_pixels

    def _encode_bit(self, bit: int) -> int:
        """Ein Datenbit in 4 SPI-Bits umwandeln (WS2812B-Protokoll)."""
        # 1 → 1110 (langes HIGH), 0 → 1000 (kurzes HIGH)
        return 0b1110 if bit else 0b1000

    def _byte_to_spi(self, byte: int):
        """Ein Byte (8 Bit) in 32 SPI-Bits (4 Bytes) umwandeln."""
        out = []
        current = 0
        count = 0
        for i in range(8):
            encoded = self._encode_bit((byte >> (7 - i)) & 1)
            for j in range(4):
                current = (current << 1) | ((encoded >> (3 - j)) & 1)
                count += 1
                if count == 8:
                    out.append(current)
                    current = 0
                    count = 0
        if count:
            out.append(current << (8 - count))
        return out  # 4 Bytes

    def fill(self, color):
        self.pixels = [color] * self.num_pixels

    def set_pixel(self, index, color):
        if 0 <= index < self.num_pixels:
            self.pixels[index] = color

    def show(self):
        spi_data = []
        for r, g, b in self.pixels:
            # WS2812B erwartet GRB-Reihenfolge
            for byte in (g, r, b):
                spi_data.extend(self._byte_to_spi(byte))
        self.spi.xfer2(spi_data)
        # Reset-Zeit >50 µs
        time.sleep(0.00008)

    def close(self):
        self.spi.close()


# === PULS-FUNKTIONEN ===
def puls_red(strip, steps=50, delay=0.03, cycles=6):
    """Lässt den LED-Streifen in Rot pulsieren."""
    for _ in range(cycles):
        for i in range(steps + 1):
            brightness = min((i + 3) / steps, 1.0)
            strip.fill((int(255 * brightness), 0, 0))
            strip.show()
            time.sleep(delay)
        for i in range(steps, -1, -1):
            brightness = i / steps
            strip.fill((int(255 * brightness), 0, 0))
            strip.show()
            time.sleep(delay)

def puls_blue(strip, steps=50, delay=0.03, cycles=1):
    """Lässt den LED-Streifen in Blau pulsieren."""
    for _ in range(cycles):
        for i in range(steps + 1):
            brightness = i / steps
            strip.fill((0, 0, int(255 * brightness)))
            strip.show()
            time.sleep(delay)
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
    strip.fill(color)
    strip.show()
    time.sleep(0.5)

def puls_green(strip, steps=50, delay=0.05, cycles=1):
    """Lässt den LED-Streifen in Grün pulsieren (startet hell)."""
    init_leds(strip, color=(0, 255, 0), delay=0.05)
    for _ in range(cycles):
        for i in range(steps + 1):
            brightness = 1 - (i / steps)
            strip.fill((0, int(255 * brightness), 0))
            strip.show()
            time.sleep(delay)
        for i in range(steps + 1):
            brightness = i / steps
            strip.fill((0, int(255 * brightness), 0))
            strip.show()
            time.sleep(delay)

def puls_white(strip):
    """Schaltet den LED-Streifen dauerhaft auf Weiß (volle Helligkeit)."""
    strip.fill((255, 255, 255))
    strip.show()

def leds_hochfahren(strip, farbe=(0, 255, 0), delay=0.1):
    """Schaltet die LEDs nacheinander ein."""
    strip.fill((0, 0, 0))
    strip.show()
    time.sleep(0.2)
    for i in range(strip.num_pixels):
        strip.set_pixel(i, farbe)
        strip.show()
        time.sleep(delay)
