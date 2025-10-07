#include <Arduino.h>

#define LED_PIN 2

void setup() {
  // Initialize serial communication at 115200 baud rate
  Serial.begin(115200);

  // Initialize LED pin as output
  pinMode(LED_PIN, OUTPUT);

  // Turn off LED initially (HIGH = OFF for active low LED)
  digitalWrite(LED_PIN, HIGH);

  // Wait for serial port to connect
  while (!Serial) {
    ; // wait for serial port to connect. Needed for native USB
  }

  Serial.println("ESP8266 LED Control Ready!");
  Serial.println("Commands:");
  Serial.println("  'on' or '1' - Turn LED ON");
  Serial.println("  'off' or '0' - Turn LED OFF");
  Serial.println("  'status' or 's' - Get LED status");
}

void loop() {
  // Check if data is available on serial port
  if (Serial.available() > 0) {
    // Read the incoming string
    String command = Serial.readStringUntil('\n');
    command.trim();        // Remove any whitespace
    command.toLowerCase(); // Convert to lowercase for easier comparison

    // Process the command
    if (command == "on" || command == "1") {
      digitalWrite(LED_PIN, LOW); // LOW = ON for active low LED
      Serial.println("LED turned ON");
    } else if (command == "off" || command == "0") {
      digitalWrite(LED_PIN, HIGH); // HIGH = OFF for active low LED
      Serial.println("LED turned OFF");
    } else if (command == "status" || command == "s") {
      int ledState = digitalRead(LED_PIN);
      Serial.print("LED is currently: ");
      Serial.println(ledState ? "OFF" : "ON"); // Inverted for active low LED
    } else if (command.length() > 0) {
      Serial.println("Unknown command: " + command);
      Serial.println("Valid commands: on, off, status");
    }
  }
}