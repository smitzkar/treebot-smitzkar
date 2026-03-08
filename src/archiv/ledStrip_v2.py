import spidev
import time

class WS2812B_SPI:
    """
    WS2812B über SPI mit korrektem Timing.
    Basiert auf: https://forums.raspberrypi.com/viewtopic.php?t=293582
    
    WS2812B Timing-Anforderungen:
    - T0H: 0.4µs ±150ns (Bit 0, HIGH)
    - T0L: 0.85µs ±150ns (Bit 0, LOW)
    - T1H: 0.8µs ±150ns (Bit 1, HIGH)
    - T1L: 0.45µs ±150ns (Bit 1, LOW)
    
    SPI @ 6.4 MHz = 156.25ns pro Bit
    - Bit 0: 110 (2x HIGH, 1x LOW) = 312.5ns HIGH, 156.25ns LOW ≈ T0
    - Bit 1: 1110 (3x HIGH, 1x LOW) = 468.75ns HIGH, 156.25ns LOW ≈ T1
    """
    
    def __init__(self, spi_bus=0, spi_device=0, num_pixels=16):
        self.num_pixels = num_pixels
        self.spi = spidev.SpiDev()
        self.spi.open(spi_bus, spi_device)
        
        # KRITISCH: 6.4 MHz für korrekte WS2812B Timing-Emulation
        self.spi.max_speed_hz = 6400000
        self.spi.mode = 0
        self.spi.lsbfirst = False
        
        # Pixel-Buffer (GRB Format)
        self.pixels = [(0, 0, 0)] * num_pixels
        
        # SPI-Byte-Mappings für WS2812B-Bits
        # Jedes WS2812B-Bit wird zu 4 SPI-Bits
        self.bit_map = {
            0b00: 0b1000_1000,  # 00 -> 10001000
            0b01: 0b1000_1110,  # 01 -> 10001110
            0b10: 0b1110_1000,  # 10 -> 11101000
            0b11: 0b1110_1110,  # 11 -> 11101110
        }
        
    def _byte_to_spi(self, byte):
        """Konvertiert ein Byte in SPI-Format für WS2812B."""
        spi_bytes = []
        for i in range(3, -1, -1):  # 4 Bit-Paare
            bits = (byte >> (i * 2)) & 0b11
            spi_bytes.append(self.bit_map[bits])
        return spi_bytes
    
    def fill(self, color):
        """Füllt alle Pixel mit einer Farbe (R, G, B)."""
        self.pixels = [color] * self.num_pixels
    
    def set_pixel(self, index, color):
        """Setzt einzelnes Pixel (R, G, B)."""
        if 0 <= index < self.num_pixels:
            self.pixels[index] = color
    
    def show(self):
        """Sendet Pixel-Daten via SPI."""
        spi_data = []
        
        for r, g, b in self.pixels:
            # WS2812B: GRB Reihenfolge!
            for byte in [g, r, b]:
                spi_data.extend(self._byte_to_spi(byte))
        
        # Sende Daten
        self.spi.xfer2(spi_data)
        
        # Reset-Signal: >50µs LOW (wird automatisch durch SPI-Pause erreicht)
        time.sleep(0.0001)  # 100µs Sicherheitspause
    
    def close(self):
        """Schließt SPI-Verbindung."""
        self.spi.close()


# === HAUPTPROGRAMM ===

if __name__ == "__main__":
    NUM_PIXELS = 16
    strip = WS2812B_SPI(spi_bus=0, spi_device=0, num_pixels=NUM_PIXELS)
    
    # Initial ausschalten
    strip.fill((0, 0, 0))
    strip.show()
    time.sleep(0.5)
    
    try:
        print("WS2812B Fade-Test mit korrektem SPI-Timing")
        print("Drücke Ctrl+C zum Beenden\n")
        
        steps = 100
        delay = 0.05
        base_color_rgb = (255, 0, 0)  # Rot
        
        cycle = 0
        
        while True:
            cycle += 1
            print(f"=== Zyklus {cycle} ===")
            
            # Fade UP
            print("Fade UP...")
            for i in range(steps + 1):
                brightness = i / steps
                r = int(base_color_rgb[0] * brightness)
                g = int(base_color_rgb[1] * brightness)
                b = int(base_color_rgb[2] * brightness)
                
                strip.fill((r, g, b))
                strip.show()
                
                if i % 20 == 0:
                    print(f"  Step {i:3d}/{steps} | Brightness: {brightness:.2f} | RGB: ({r:3d}, {g:3d}, {b:3d})")
                
                time.sleep(delay)
            
            time.sleep(0.3)
            
            # Fade DOWN
            print("Fade DOWN...")
            for i in range(steps, -1, -1):
                brightness = i / steps
                r = int(base_color_rgb[0] * brightness)
                g = int(base_color_rgb[1] * brightness)
                b = int(base_color_rgb[2] * brightness)
                
                strip.fill((r, g, b))
                strip.show()
                
                if i % 20 == 0:
                    print(f"  Step {i:3d}/{steps} | Brightness: {brightness:.2f} | RGB: ({r:3d}, {g:3d}, {b:3d})")
                
                time.sleep(delay)
            
            time.sleep(0.3)
            print()
    
    except KeyboardInterrupt:
        print("\n\nBeende Programm...")
        strip.fill((0, 0, 0))
        strip.show()
        time.sleep(0.2)
        strip.close()
        print("LEDs ausgeschaltet - SPI geschlossen")
    
    except Exception as e:
        print(f"\nFEHLER: {e}")
        strip.fill((0, 0, 0))
        strip.show()
        strip.close()