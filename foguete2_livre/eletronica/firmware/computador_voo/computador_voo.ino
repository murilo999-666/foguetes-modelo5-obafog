/*
  Computador de voo — Foguete 2 (livre)  |  ESP32-C3 SuperMini, core esp32 3.x
  Barômetro BMP280 (obrigatório) + MPU6050 (opcional) + micro servo (trava da ogiva)
  + buzzer (localizador) + LiPo 1S. A lógica de voo está em voo.h (testada no PC).

  PLACA na IDE: "ESP32C3 Dev Module", USB CDC On Boot: Enabled.
  Compilar: arduino-cli compile --fqbn esp32:esp32:esp32c3:CDCOnBoot=cdc computador_voo

  LIGAÇÃO (ver ../../ELETRONICA.md)
    GPIO6 SDA, GPIO7 SCL  -> BMP280 e MPU6050 (3V3, GND)
    GPIO5 -> sinal do servo (servo alimentado DIRETO na bateria, depois da chave)
    GPIO4 -> resistor 1k -> base do NPN (S8050/BC337); buzzer ativo entre bateria+ e coletor
    GPIO3 <- meio de um divisor 100k/100k da bateria (leitura de tensão)
    GPIO8 = LED azul da placa (acende em LOW)
    Bateria + (depois da chave) -> pino 5V da placa (regulador da placa faz 3,3 V)
  NUNCA ligar o USB com a chave da bateria ligada (o USB empurra 5 V na LiPo),
  a menos que exista um diodo Schottky (SS14/1N5817) entre bateria e pino 5V.

  OPERAÇÃO
    1. Liga (ogiva fora): servo DESTRAVADO, Wi-Fi "FOGUETE2" (senha foguete123), 1 bip a cada 2 s.
    2. Encaixa a ogiva. No celular, http://192.168.4.1 -> "Travar e armar"
       (ou espere 90 s: nos últimos 10 s ele bipa rápido e trava sozinho).
    3. ARMADO: servo travado, Wi-Fi desligado, bip duplo a cada 5 s = tudo certo.
       Bips rápidos contínuos = sensor com problema -> NÃO lançar.
    4. Depois do pouso: bipa o apogeu (ex.: 1-2-3 = 123 m), Wi-Fi volta, baixa /voo.csv.
*/
#include <LittleFS.h>
#include <WebServer.h>
#include <WiFi.h>
#include <Wire.h>
#include <esp_system.h>

#include "bmp280_min.h"
#include "voo.h"

// ---------------- pinos e ajustes ----------------
const int PIN_SDA = 6, PIN_SCL = 7, PIN_SERVO = 5, PIN_BUZZER = 4, PIN_BAT = 3, PIN_LED = 8;
const int SERVO_TRAVA_US = 1900;     // AJUSTAR na bancada: braço dentro da janela do tubo
const int SERVO_SOLTA_US = 1100;     // AJUSTAR: braço recolhido, ogiva livre
const uint32_t AUTO_ARMAR_MS = 90000;
const uint32_t PERIODO_MS = 20;      // 50 Hz
const char* WIFI_SSID = "FOGUETE2";
const char* WIFI_SENHA = "foguete123";

// ---------------- estado ----------------
BMP280min baro;
bool temMPU = false, baroOK = false;
voo::Computador fc;
WebServer web(80);
bool wifiLigado = false;
uint32_t tLigou = 0, tUltimaAmostra = 0, tServoMov = 0;
float pressao = 101325, temperatura = 25, vBat = 0;
int16_t az_mg = 0;

// sobrevive a reset por queda de tensão (não a desligar a bateria)
RTC_NOINIT_ATTR uint32_t rtcMagic;
RTC_NOINIT_ATTR uint8_t rtcEstado;
const uint32_t MAGIC = 0xF0E6E7E2;

// ---------------- log do voo em RAM (salvo na flash depois do pouso) ----------------
struct Amostra {
  uint32_t t;
  float h_bruto, h, v;
  int16_t az;
  uint8_t estado, flags;
};
const int N_LOG = 3000;              // 60 s a 50 Hz (~60 kB)
Amostra logv[N_LOG];
int iLog = 0, iInicio = -1, nLog = 0;
bool gravando = false, salvo = false;

// ---------------- servo por LEDC (sem biblioteca) ----------------
void servoPulso(int us) {
  // 50 Hz, 14 bits: período 20000 us = 16384 contagens
  ledcWrite(PIN_SERVO, (uint32_t)us * 16384UL / 20000UL);
  tServoMov = millis();
}
void servoDesliga() { ledcWrite(PIN_SERVO, 0); }

// ---------------- buzzer não bloqueante ----------------
void buzz(bool on) { digitalWrite(PIN_BUZZER, on ? HIGH : LOW); }
void padraoBip(uint32_t agora) {
  using E = voo::Estado;
  bool ligado = false;
  if (!baroOK) {                                   // erro: 5 Hz
    ligado = (agora / 100) % 2;
  } else if (fc.estado == E::PREPARO) {
    uint32_t restante = (agora - tLigou < AUTO_ARMAR_MS) ? AUTO_ARMAR_MS - (agora - tLigou) : 0;
    ligado = (restante < 10000) ? ((agora / 150) % 2) : ((agora % 2000) < 60);
  } else if (fc.estado == E::ARMADO) {
    uint32_t c = agora % 5000;
    ligado = c < 60 || (c > 180 && c < 240);
  } else if (fc.estado == E::POUSADO) {
    // bipa os dígitos do apogeu, depois 5 s de bip curto por segundo, repete
    int ap = (int)(fc.h_max + 0.5f);
    int d[3] = {ap / 100, (ap / 10) % 10, ap % 10};
    uint32_t ciclo = 16000, c = agora % ciclo;
    uint32_t pos = 0;
    ligado = false;
    for (int k = (ap >= 100 ? 0 : (ap >= 10 ? 1 : 2)); k < 3 && !ligado; k++) {
      int n = d[k] == 0 ? 1 : d[k];
      uint32_t dur = d[k] == 0 ? 600 : 150;
      for (int j = 0; j < n; j++) {
        if (c >= pos && c < pos + dur) { ligado = true; break; }
        pos += dur + 250;
      }
      pos += 700;
    }
    if (!ligado && c > 9000) ligado = (c % 1000) < 50;
  }
  buzz(ligado);
  digitalWrite(PIN_LED, ligado ? LOW : HIGH);
}

// ---------------- sensores ----------------
bool mpuInit() {
  Wire.beginTransmission(0x68);
  if (Wire.endTransmission() != 0) return false;
  auto w = [](uint8_t r, uint8_t v) { Wire.beginTransmission(0x68); Wire.write(r); Wire.write(v); Wire.endTransmission(); };
  w(0x6B, 0x00);        // acorda
  w(0x1C, 0x18);        // acelerômetro +-16 g (2048 LSB/g)
  w(0x1A, 0x03);        // filtro digital ~44 Hz
  return true;
}
bool mpuLerAz(int16_t& mg) {
  Wire.beginTransmission(0x68);
  Wire.write(0x3B);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(0x68, 6) != 6) return false;
  int16_t ax = (Wire.read() << 8) | Wire.read();
  int16_t ay = (Wire.read() << 8) | Wire.read();
  int16_t azr = (Wire.read() << 8) | Wire.read();
  // módulo da aceleração (orientação do módulo no berço não importa para detectar decolagem)
  float g = sqrtf((float)ax * ax + (float)ay * ay + (float)azr * azr) / 2048.0f;
  mg = (int16_t)constrain(g * 1000.0f, -32000.0f, 32000.0f);
  return true;
}

float lerBateria() { return analogReadMilliVolts(PIN_BAT) * 2.0f / 1000.0f; }

// ---------------- log ----------------
void registrar(uint32_t t, uint8_t flags) {
  if (iInicio >= 0 && !gravando) return;           // voo já gravado ou buffer cheio: não sobrescreve
  Amostra& a = logv[iLog];
  a.t = t; a.h_bruto = fc.h_bruto; a.h = fc.kf.h; a.v = fc.kf.v; a.az = az_mg;
  a.estado = (uint8_t)fc.estado; a.flags = flags;
  iLog = (iLog + 1) % N_LOG;
  if (gravando && ++nLog >= N_LOG - 1) gravando = false;   // cheio: congela
}

void salvarVoo() {
  if (salvo || iInicio < 0) return;
  File f = LittleFS.open("/voo.csv", "w");
  if (!f) return;
  f.printf("# apogeu_m=%.1f motivo=%s t_decolagem=%lu t_abertura=%lu bateria=%.2f\n",
           fc.h_max, fc.motivo, (unsigned long)fc.t_decolagem, (unsigned long)fc.t_abertura, vBat);
  f.println("t_ms,h_bruto_m,h_filtrado_m,v_ms,acel_mg,estado,flags");
  int n = min(nLog, N_LOG - 1);
  for (int k = 0; k < n; k++) {
    const Amostra& a = logv[(iInicio + k) % N_LOG];
    f.printf("%lu,%.2f,%.2f,%.2f,%d,%u,%u\n", (unsigned long)a.t, a.h_bruto, a.h, a.v, a.az, a.estado, a.flags);
  }
  f.close();
  salvo = true;
}

// ---------------- Wi-Fi (só no chão) ----------------
void paginaStatus() {
  String s = "<html><head><meta name=viewport content='width=device-width'><meta http-equiv=refresh content=2>"
             "<style>body{font-family:sans-serif;font-size:18px}a{display:block;margin:12px 0;padding:14px;"
             "background:#e8590c;color:#fff;text-align:center;border-radius:8px;text-decoration:none}</style>"
             "</head><body><h2>Foguete 2</h2>";
  s += "Estado: <b>" + String(voo::nome(fc.estado)) + "</b><br>";
  s += "Barometro: " + String(baroOK ? "OK" : "FALHA") + " | MPU6050: " + String(temMPU ? "sim" : "nao") + "<br>";
  s += "Bateria: " + String(vBat, 2) + " V" + String(vBat < 3.6 ? " (CARREGAR)" : "") + "<br>";
  s += "Altitude relativa: " + String(fc.kf.h, 1) + " m | ruido medido: " + String(fc.cfg.sigma_h_m, 2) + " m<br>";
  s += "Apogeu registrado: " + String(fc.h_max, 1) + " m (" + String(fc.motivo) + ")<br>";
  if (fc.estado == voo::Estado::PREPARO) {
    uint32_t r = AUTO_ARMAR_MS - min(AUTO_ARMAR_MS, millis() - tLigou);
    s += "Arma sozinho em " + String(r / 1000) + " s<br>";
    s += "<a href=/armar>Travar e armar</a><a href=/destravar>Destravar (teste)</a><a href=/travar>Travar (teste)</a>";
  }
  s += "<a href=/voo.csv>Baixar voo.csv</a></body></html>";
  web.send(200, "text/html", s);
}

void wifiLiga() {
  if (wifiLigado) return;
  WiFi.mode(WIFI_AP);
  WiFi.softAP(WIFI_SSID, WIFI_SENHA);
  static bool rotas = false;
  if (rotas) { web.begin(); wifiLigado = true; return; }
  rotas = true;
  web.on("/", paginaStatus);
  web.on("/armar", []() { armar(); web.sendHeader("Location", "/"); web.send(303); });
  web.on("/destravar", []() {
    if (fc.estado == voo::Estado::PREPARO || fc.estado == voo::Estado::POUSADO) servoPulso(SERVO_SOLTA_US);
    web.sendHeader("Location", "/"); web.send(303);
  });
  web.on("/travar", []() {
    if (fc.estado == voo::Estado::PREPARO) servoPulso(SERVO_TRAVA_US);
    web.sendHeader("Location", "/"); web.send(303);
  });
  web.on("/voo.csv", []() {
    File f = LittleFS.open("/voo.csv", "r");
    if (!f) { web.send(404, "text/plain", "sem voo gravado"); return; }
    web.streamFile(f, "text/csv");
    f.close();
  });
  web.begin();
  wifiLigado = true;
}

void wifiDesliga() {
  if (!wifiLigado) return;
  web.stop();
  WiFi.softAPdisconnect(true);
  WiFi.mode(WIFI_OFF);
  wifiLigado = false;
}

// ---------------- armar ----------------
float mediaPressao(int n) {
  float soma = 0; int ok = 0;
  for (int i = 0; i < n * 3 && ok < n; i++) {
    float p, t;
    if (baro.ler(p, t)) { soma += p; ok++; }
    delay(15);
  }
  return ok ? soma / ok : pressao;
}

void medirRuido() {
  // desvio da altitude bruta parado no chão -> ruído do Kalman
  const int n = 60;
  float h[n], p0 = mediaPressao(10), m = 0, v = 0;
  for (int i = 0; i < n; i++) {
    float p = p0, t;
    for (int k = 0; k < 20 && !baro.ler(p, t); k++) delay(2);   // limitado: nunca trava
    h[i] = voo::altitude_de_pressao(p, p0);
    m += h[i];
    delay(20);
  }
  m /= n;
  for (int i = 0; i < n; i++) v += (h[i] - m) * (h[i] - m);
  fc.cfg.sigma_h_m = constrain(sqrtf(v / (n - 1)), 0.1f, 1.5f);
}

void armar() {
  if (fc.estado != voo::Estado::PREPARO || !baroOK) return;
  servoPulso(SERVO_TRAVA_US);
  medirRuido();
  fc.armar(mediaPressao(20), millis());
  rtcMagic = MAGIC;
  rtcEstado = (uint8_t)fc.estado;
  wifiDesliga();
  iInicio = -1; nLog = 0; gravando = false; salvo = false;
}

// ---------------- setup / loop ----------------
void setup() {
  pinMode(PIN_BUZZER, OUTPUT); buzz(false);
  pinMode(PIN_LED, OUTPUT); digitalWrite(PIN_LED, HIGH);
  Serial.begin(115200);
  analogSetPinAttenuation(PIN_BAT, ADC_11db);
  ledcAttach(PIN_SERVO, 50, 14);
  Wire.begin(PIN_SDA, PIN_SCL, 400000);
  baroOK = baro.begin(Wire);
  temMPU = mpuInit();
  LittleFS.begin(true);
  tLigou = millis();
  vBat = lerBateria();

  // reset DURANTE o voo (queda de tensão)? então abre o paraquedas já: melhor que nunca abrir
  esp_reset_reason_t motivo = esp_reset_reason();
  bool resetEmVoo = (rtcMagic == MAGIC) &&
                    (rtcEstado == (uint8_t)voo::Estado::SUBIDA || rtcEstado == (uint8_t)voo::Estado::DESCIDA) &&
                    (motivo == ESP_RST_BROWNOUT || motivo == ESP_RST_PANIC || motivo == ESP_RST_WDT ||
                     motivo == ESP_RST_INT_WDT || motivo == ESP_RST_TASK_WDT);
  if (resetEmVoo) {
    servoPulso(SERVO_SOLTA_US);
    fc.estado = voo::Estado::DESCIDA;
    fc.motivo = "reset em voo";
    Serial.println("# reset em voo: paraquedas comandado");
  } else {
    servoPulso(SERVO_SOLTA_US);      // ogiva livre para encaixar
    wifiLiga();
  }
  rtcMagic = MAGIC;
  rtcEstado = (uint8_t)fc.estado;
  Serial.printf("# baro %s (0x%02X, id 0x%02X) | MPU %s | bateria %.2f V\n", baroOK ? "OK" : "FALHA",
                baro.endereco, baro.chip_id, temMPU ? "sim" : "nao", vBat);
}

void loop() {
  uint32_t agora = millis();
  if (wifiLigado) web.handleClient();

  // servo segura a posição o tempo todo (trava com torque); só desliga 5 s depois do pouso
  if (tServoMov && agora - tServoMov > 5000 && fc.estado == voo::Estado::POUSADO) {
    servoDesliga();
    tServoMov = 0;
  }

  // sensor com falha não trava a placa: tenta de novo a cada 500 ms (diagnóstico não bloqueia)
  static uint32_t tRetry = 0;
  if (!baroOK && agora - tRetry > 500) { tRetry = agora; baroOK = baro.begin(Wire); }

  if (fc.estado == voo::Estado::PREPARO && agora - tLigou > AUTO_ARMAR_MS) armar();

  if (agora - tUltimaAmostra >= PERIODO_MS) {
    tUltimaAmostra = agora;
    float p, t;
    bool ok = baroOK && baro.ler(p, t);
    if (ok) { pressao = p; temperatura = t; }
    if (temMPU && mpuLerAz(az_mg) && az_mg > 3000 && fc.estado == voo::Estado::ARMADO) fc.sinal_decolagem();
    voo::Estado antes = fc.estado;
    voo::Saida s = fc.passo(agora, pressao);
    if (s.abrir) servoPulso(SERVO_SOLTA_US);
    if (antes == voo::Estado::ARMADO && fc.estado == voo::Estado::SUBIDA) {
      gravando = true;
      nLog = 50;                                       // guarda 1 s antes da decolagem
      iInicio = (iLog - 50 + N_LOG) % N_LOG;
    }
    if (fc.estado != voo::Estado::PREPARO) registrar(agora, (ok ? 1 : 0) | (s.abrir ? 2 : 0));
    if (s.mudou_estado) {
      rtcEstado = (uint8_t)fc.estado;
      Serial.printf("# %lu ms: %s (h=%.1f v=%.1f %s)\n", (unsigned long)agora, voo::nome(fc.estado),
                    fc.kf.h, fc.kf.v, fc.motivo);
    }
    if (fc.estado == voo::Estado::POUSADO && !salvo) {
      gravando = false;
      salvarVoo();
      vBat = lerBateria();
      wifiLiga();
    }
    static uint32_t tBat = 0;
    if (agora - tBat > 5000 && fc.estado != voo::Estado::SUBIDA) { tBat = agora; vBat = lerBateria(); }
  }
  padraoBip(agora);
}
