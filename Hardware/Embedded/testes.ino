// Loopback RS232 — ESP32-S3
// TX = GPIO11  |  RX = GPIO10
// Conectar: TX_OUT do CI --> RX_IN do CI (lado RS232)

#define RS232_TX  11
#define RS232_RX  10
#define BAUD      9600

void setup() {
  Serial.begin(115200);           // monitor serial (USB)
  Serial1.begin(BAUD, SERIAL_8N1, RS232_RX, RS232_TX);

  Serial.println("=== Loopback RS232 iniciado ===");
  Serial.printf("Baud: %d | TX: GPIO%d | RX: GPIO%d\n",
                BAUD, RS232_TX, RS232_RX);
  Serial.println("Aguardando loopback fisico no CI...");
}

void loop() {
  // Envia mensagem de teste a cada 1 segundo
  static uint32_t lastSend = 0;
  static uint16_t counter  = 0;

  if (millis() - lastSend >= 1000) {
    lastSend = millis();
    String msg = "PING " + String(counter++);
    Serial1.println(msg);
    Serial.print("TX: ");
    Serial.println(msg);
  }

  // Lê tudo que voltar pelo RX
  while (Serial1.available()) {
    String received = Serial1.readStringUntil('\n');
    received.trim();
    if (received.length() > 0) {
      Serial.print("RX: ");
      Serial.println(received);

      // Verifica se o eco bate com o esperado
      if (received.startsWith("PING")) {
        Serial.println("  ✓ Loopback OK");
      } else {
        Serial.println("  ✗ Dado inesperado!");
      }
    }
  }
}