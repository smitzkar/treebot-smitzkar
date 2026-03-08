#include <HardwareSerial.h>
#include <FastLED.h>

// ---------- UART to Raspberry Pi ----------
#define RXD2 16   // ESP32 RX2 (connect to Pi TX (GPIO14/BCM14))
#define TXD2 17   // ESP32 TX2 (connect to Pi RX (GPIO15/BCM15))
HardwareSerial PiSerial(2); // Serial2

// ---------- LED strip ----------
#define NUM_LEDS     144
#define LED_PIN      18
#define LED_TYPE     WS2812B
#define COLOR_ORDER  GRB
CRGB leds[NUM_LEDS];

// Modify these globals:
const int TOUCH_MARGIN = 20;        // How much below baseline = touch
const int RELEASE_MARGIN = 30;      // How much below baseline = release (higher for stability)
bool currentlyTouched = false;

// Add these variables at the top with other globals:
unsigned long lastRecalibration = 0;
const unsigned long recalibrationInterval = 300000; // 5 minutes
const int BASELINE_SAMPLES = 50;
int baselineReadings[BASELINE_SAMPLES];
int baselineIndex = 0;
bool baselineReady = false;

// --- Touch Sensor mit Median-Filter und 5s-Haltezeit ---
const int touchPin = 27;    // Touch input (ESP32: e.g. GPIO27)
const int ledPin   = 25;    // LED pin (GPIO25)

int threshold = 0;          // Touch-Schwelle (Kalibrierung)
bool calibrated = false;    // Kalibrierungs-Status

const int N = 31;           // Anzahl Samples für Median (ungerade)
int buffer[N];

// Timer für 2s Haltezeit
unsigned long mytouchStart = 0;
const unsigned long holdTime = 2000; // 2 Sekunden

// ---------- Pulse (breathing) control ----------
bool pulseActive = false;
bool wanderingDotsActive = false;
uint8_t pulseBPM = 12;       // lower = slower, smoother breathing
uint8_t minBright = 10;     // floor brightness
uint8_t maxBright = 160;    // 255 ceiling brightness

const uint16_t pulseIntervalMs = 20;
uint32_t lastPulseMs = 0;



// ---------- Helpers ----------
void startPulse(CRGB color) {
  wanderingDotsActive = false;
  pulseActive = true;
  fill_solid(leds, NUM_LEDS, color);
  FastLED.setBrightness(maxBright);
  FastLED.show();
}

void startWanderingDots() {
  pulseActive = false;
  wanderingDotsActive = true;
  fill_solid(leds, NUM_LEDS, CRGB::Blue);
  FastLED.show();
}

void updateWanderingDots() {
  static uint8_t offset = 0;
  static unsigned long lastUpdate = 0;
  
  if (millis() - lastUpdate < 120) return;
  lastUpdate = millis();
  
  const CRGB background = CRGB::Blue;
  const CRGB dotColor = CRGB::White;
  const int dotGroupCount = 3;
  const int dotGroupSizeMin = 4;
  const int dotGroupSizeMax = 16;

  fill_solid(leds, NUM_LEDS, background);

  for (int g = 0; g < dotGroupCount; g++) {
    int groupPos = (offset + (g * (NUM_LEDS / dotGroupCount))) % NUM_LEDS;
    int groupSize = random(dotGroupSizeMin, dotGroupSizeMax + 1);
    for (int i = 0; i < groupSize; i++) {
      leds[(groupPos + i) % NUM_LEDS] = dotColor;
    }
  }

  FastLED.show();
  offset = (offset - 5 + NUM_LEDS) % NUM_LEDS; //reverse direction
}


void stopPulse() {
  pulseActive = false;
  wanderingDotsActive = false;
  fill_solid(leds, NUM_LEDS, CRGB::Black);
  FastLED.show();
}

void updatePulse() {
  uint8_t brightness = beatsin8(pulseBPM, minBright, maxBright);
  FastLED.setBrightness(brightness);
  FastLED.show();
}

void handleCommand(const String& line) {
  if (line.equalsIgnoreCase("1") || line.equalsIgnoreCase("1.00")) {
    stopPulse();
    delay(100);
    startPulse(CRGB::White); // white pulsating
  } else if (line.equalsIgnoreCase("2") || line.equalsIgnoreCase("2.00")) {
    stopPulse();
    delay(100);
    startPulse(CRGB::Green); // green pulsating
  } else if (line.equalsIgnoreCase("3") || line.equalsIgnoreCase("3.00")) {
    stopPulse();
    delay(100);
    startPulse(CRGB::Blue); // blue pulsating
  } else if (line.equalsIgnoreCase("8") || line.equalsIgnoreCase("8.00")) {
    stopPulse();
    delay(100);
    startWanderingDots(); // blue and white dots
  } else if (line.equalsIgnoreCase("0") || line.equalsIgnoreCase("0.00")) {
    stopPulse();
  }
}

void setup() {
  Serial.begin(115200);
  PiSerial.begin(115200, SERIAL_8N1, RXD2, TXD2);
  PiSerial.setTimeout(5);
  PiSerial.println("ESP32 READY");

  pinMode(ledPin, OUTPUT);
  digitalWrite(ledPin, LOW);

  Serial.println("Calibration (5 seconds)... do not touch!");
  long sum = 0;
  int count = 0;
  unsigned long start = millis();

  while (millis() - start < 5000) {
    int val = touchRead(touchPin);
    sum += val;
    count++;
    delay(50);
  }

  threshold = (sum / count) - 20;
  calibrated = true;

  Serial.print("Calibration done. Threshold = ");
  Serial.println(threshold);

  FastLED.addLeds<LED_TYPE, LED_PIN, COLOR_ORDER>(leds, NUM_LEDS);
  FastLED.setBrightness(255);
  fill_solid(leds, NUM_LEDS, CRGB::Black);
  FastLED.show();

  Serial.println("[ESP32] Booted. Waiting for Pi commands...");
}

int readMedian(int pin) {
  for (int i = 0; i < N; i++) {
    buffer[i] = touchRead(pin);
    delay(2);
  }
  for (int i = 0; i < N - 1; i++) {
    for (int j = 0; j < N - i - 1; j++) {
      if (buffer[j] > buffer[j + 1]) {
        int tmp = buffer[j];
        buffer[j] = buffer[j + 1];
        buffer[j + 1] = tmp;
      }
    }
  }
  return buffer[N / 2];
}

// Add this function after readMedian():
void updateBaseline(int value) {
  // Only update baseline when NOT touched
  if (value >= threshold + 10) {  // Safety margin above threshold
    baselineReadings[baselineIndex] = value;
    baselineIndex = (baselineIndex + 1) % BASELINE_SAMPLES;
    if (baselineIndex == 0) baselineReady = true;
  }
}

int calculateBaselineThreshold() {
  if (!baselineReady) return threshold;
  
  long sum = 0;
  for (int i = 0; i < BASELINE_SAMPLES; i++) {
    sum += baselineReadings[i];
  }
  return (sum / BASELINE_SAMPLES) - 20;
}

void loop() {
  int val = readMedian(touchPin);
  Serial.print("Touch value: ");
  Serial.print(val);
  Serial.print(" | Threshold: ");
  Serial.println(threshold);

  // Update baseline with non-touch readings
  updateBaseline(val);

  // Periodic recalibration (every 5 minutes when idle)
  if (millis() - lastRecalibration > recalibrationInterval && mytouchStart == 0) {
    int newThreshold = calculateBaselineThreshold();
    // More conservative sanity check
    if (newThreshold > 0 && abs(newThreshold - threshold) < 15) {
      threshold = newThreshold;
      Serial.print("✓ Recalibrated threshold: ");
      Serial.println(threshold);
    } else {
      Serial.println("✗ Recalibration rejected - too much drift");
    }
    lastRecalibration = millis();
  }

  // Hysteresis-based touch detection
  if (calibrated) {
    if (!currentlyTouched && val < (threshold - TOUCH_MARGIN)) {
      // Touch detected
      currentlyTouched = true;
      mytouchStart = millis();
      Serial.println("→ Touch START");
    } 
    else if (currentlyTouched && val > (threshold - RELEASE_MARGIN)) {
      // Release detected
      currentlyTouched = false;
      mytouchStart = 0;
      digitalWrite(ledPin, LOW);
      Serial.println("← Touch RELEASE");
    }
    
    // Check hold time
    if (currentlyTouched && (millis() - mytouchStart >= holdTime)) {
      digitalWrite(ledPin, HIGH);
      Serial.println("✓ Held for 2s");
    }
  }

  // ----- Read commands from Raspberry Pi -----
  if (PiSerial.available()) {
    String line = PiSerial.readStringUntil('\n');
    line.trim();

    // 🧹 Entferne nicht druckbare Zeichen
    for (int i = 0; i < line.length(); i++) {
      if (line[i] < 32 || line[i] > 126) {
        line.remove(i, 1);
        i--;
      }
    }

    if (line.length()) {
      Serial.print("[ESP32] <- Pi: ");
      Serial.println(line);
      handleCommand(line);
    }
  }

  // ----- Optional: USB debug console -----
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd.length()) {
      handleCommand(cmd);
    }
  }

  if (pulseActive) {
    uint32_t now = millis();
    if (now - lastPulseMs >= pulseIntervalMs) {
      lastPulseMs = now;
      updatePulse();
    }
  } else if (wanderingDotsActive) {
    updateWanderingDots();
  }

  delay(1);
}
