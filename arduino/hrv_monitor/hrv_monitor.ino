// ПУЛЬСОМЕТР - СЫРОЙ СИГНАЛ БЕЗ ФИЛЬТРАЦИИ
const int PULSE_PIN = A0;
const int BUZZER_PIN = 8;
const int LED_PIN = 9;

unsigned long lastBeatTime = 0;
bool beatDetected = false;
const int THRESHOLD = 520;

void setup() {
  Serial.begin(115200);
  
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(LED_PIN, OUTPUT);
  
  digitalWrite(BUZZER_PIN, LOW);
  digitalWrite(LED_PIN, LOW);
  
  Serial.println("RAW_SIGNAL_START");
}

void loop() {
  // 1. Чтение СЫРОГО сигнала
  int rawValue = analogRead(PULSE_PIN);
  
  // 2. Обнаружение удара по СЫРОМУ сигналу
  if (rawValue > THRESHOLD && !beatDetected) {
    beatDetected = true;
    
    unsigned long currentTime = millis();
    if (lastBeatTime > 0) {
      long timeBetweenBeats = currentTime - lastBeatTime;
      
      // Фильтр физиологически возможных значений
      if (timeBetweenBeats > 300 && timeBetweenBeats < 1500) {
        int beatsPerMinute = 60000 / timeBetweenBeats;
        
        if (beatsPerMinute >= 40 && beatsPerMinute <= 180) {
          // Отправляем RR интервал
          Serial.print("RR:");
          Serial.println(timeBetweenBeats);
          
          // Короткий сигнал
          digitalWrite(BUZZER_PIN, HIGH);
          digitalWrite(LED_PIN, HIGH);
          delay(20);
          digitalWrite(BUZZER_PIN, LOW);
          digitalWrite(LED_PIN, LOW);
        }
      }
    }
    lastBeatTime = currentTime;
  }
  
  // Сброс флага обнаружения
  if (rawValue < THRESHOLD - 50) {
    beatDetected = false;
  }
  
  // 3. Отправка СЫРЫХ данных для графика
  // Формат: rawValue,0 (второе значение не используется)
  Serial.print(rawValue);
  Serial.println(",0");
  
  delay(10);
}