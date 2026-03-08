import spidev
import time
import threading

class WS2812B_SPI:
    """WS2812B über SPI mit stabilem Timing (1→1110 / 0→1000 @ 3.2 MHz).
    Thread-sicher (RLock) und optional redundante Frames gegen sporadische Bitfehler.
    """
    def __init__(self, spi_bus=0, spi_device=0, num_pixels=16, redundant_frames=2):
        self.num_pixels = num_pixels
        self.spi = spidev.SpiDev()
        self.spi.open(spi_bus, spi_device)
        self.spi.max_speed_hz = 3_200_000
        self.spi.mode = 0
        self.spi.lsbfirst = False
        self.pixels = [(0, 0, 0)] * num_pixels
        self._lock = threading.RLock()
        self._redundant = max(1, int(redundant_frames))

    @staticmethod
    def _encode_bit(bit: int) -> int:
        # 1 → 1110 (langes HIGH), 0 → 1000 (kurzes HIGH)
        return 0b1110 if bit else 0b1000

    def _byte_to_spi(self, byte: int):
        out, current, count = [], 0, 0
        for i in range(8):
            encoded = self._encode_bit((byte >> (7 - i)) & 1)
            for j in range(4):
                current = (current << 1) | ((encoded >> (3 - j)) & 1)
                count += 1
                if count == 8:
                    out.append(current); current = 0; count = 0
        if count:
            out.append(current << (8 - count))
        return out  # 4 Bytes

    def fill(self, color):
        with self._lock:
            self.pixels = [color] * self.num_pixels

    def set_pixel(self, index, color):
        if 0 <= index < self.num_pixels:
            with self._lock:
                self.pixels[index] = color

    def _build_frame(self):
        spi_data = []
        for r, g, b in self.pixels:
            for byte in (g, r, b):  # GRB
                spi_data.extend(self._byte_to_spi(byte))
        return spi_data

    def show(self):
        with self._lock:
            frame = self._build_frame()
            for _ in range(self._redundant):
                self.spi.xfer2(frame)
            time.sleep(0.0002)  # Reset > 50 µs (großzügig)

    def close(self):
        with self._lock:
            self.spi.close()
