# ledstrip.py  (veya ledstrip_v3.py)
import spidev, time

class WS2812B_SPI:
    """WS2812B via SPI, 3.2MHz, bit-per-bit 1110/1000 encode."""
    def __init__(self, spi_bus=0, spi_device=0, num_pixels=16):
        self.num_pixels = num_pixels
        self.spi = spidev.SpiDev()
        self.spi.open(spi_bus, spi_device)
        self.spi.max_speed_hz = 3_200_000   # kritik: 3.2 MHz
        self.spi.mode = 0
        self.spi.lsbfirst = False
        self.pixels = [(0, 0, 0)] * num_pixels

    @staticmethod
    def _encode_bit(bit):
        # 1 -> 1110 (yüksek uzun), 0 -> 1000 (yüksek kısa)
        return 0b1110 if bit else 0b1000

    def _byte_to_spi(self, byte):
        # Her bir bit için 4 SPI biti (toplam 8*4=32 SPI bit = 4 byte)
        out = []
        current = 0
        count = 0
        for i in range(8):
            encoded = self._encode_bit((byte >> (7 - i)) & 1)
            # 4 biti sırayla current içine itelim
            for j in range(4):
                current = (current << 1) | ((encoded >> (3 - j)) & 1)
                count += 1
                if count == 8:
                    out.append(current)
                    current = 0
                    count = 0
        if count:  # normalde kalmaz
            out.append(current << (8 - count))
        return out  # 4 byte

    def fill(self, color):
        self.pixels = [color] * self.num_pixels

    def set_pixel(self, index, color):
        if 0 <= index < self.num_pixels:
            self.pixels[index] = color

    def show(self):
        spi_data = []
        for r, g, b in self.pixels:
            # WS2812B beklentisi GRB sırası:
            for byte in (g, r, b):
                spi_data.extend(self._byte_to_spi(byte))
        self.spi.xfer2(spi_data)
        time.sleep(0.00008)  # >50 µs reset

    def close(self):
        self.spi.close()
