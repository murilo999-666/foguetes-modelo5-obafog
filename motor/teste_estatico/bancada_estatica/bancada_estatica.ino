/*
  Bancada de teste estático — motor oficial OBAFOG Modelo 5
  Arduino Uno/Nano + HX711 + célula de carga de barra (5 kg)

  LIGAÇÃO
    HX711 VCC -> 5V   GND -> GND   DT -> D3   SCK -> D2
    Célula de carga -> HX711 (E+ vermelho, E- preto, A- branco, A+ verde; se o
    empuxo sair negativo, troque A+ com A-)
    LED no D13 (o da placa) indica o estado.

  80 Hz, NÃO 10 Hz: a placa verde comum do HX711 vem com o pino RATE (15) no GND
  = 10 amostras/s, o que dá só ~12 pontos numa queima de 1,2 s. Levante o pino 15
  (ou corte a trilha do jumper "RATE") e ligue-o ao VCC: passa a 80 amostras/s.
  Confira no comando 'r' (mostra a taxa medida).

  SEGURANÇA: a bancada fica no mesmo lugar e com o mesmo protocolo do lançamento
  (fio de ignição de 25 m, protetor facial, professor junto). O Arduino grava
  sozinho quando o empuxo passa do gatilho; ninguém precisa ficar perto do
  motor. Depois da queima, espere 1 minuto, chegue e peça 'd' pela serial.

  COMANDOS (Monitor Serial, 115200, "Nova linha")
    t          tara (zera com o motor já montado, antes de ligar o squib)
    c 500      calibra com um peso conhecido em gramas (ex.: 500 g)
    r          mostra leitura atual e a taxa de amostragem
    a          ARMA: espera empuxo > gatilho e grava 6 s
    d          despeja a última gravação em CSV (i, t_ms, empuxo_N)
    e          despeja a gravação salva na EEPROM (sobrevive a desligar a placa)

  A curva é gravada em RAM e copiada para a EEPROM (1024 bytes: cabe tudo).
*/
#include <EEPROM.h>
#include <HX711.h>   // "HX711 Arduino Library" (Bogdan Necula), no Gerenciador de Bibliotecas

const uint8_t PIN_DT = 3;
const uint8_t PIN_SCK = 2;
const uint8_t PIN_LED = 13;

const int N_AMOSTRAS = 480;      // 6 s a 80 Hz
const int N_PRE = 24;            // 0,3 s antes do gatilho
const float GATILHO_N = 0.5;     // começa a gravar acima disto

HX711 cel;
float fatorEscala = 1.0f;        // contagens por grama (comando 'c'); fica na EEPROM
int16_t curva[N_AMOSTRAS];       // empuxo em centinewton (0,01 N)
unsigned long duracaoMs = 0;     // tempo total da gravação
int nGravadas = 0;

// EEPROM: [0..3] fator | [4..7] duracao | [8..9] n | [10..] amostras
const int EE_FATOR = 0, EE_DUR = 4, EE_N = 8, EE_DADOS = 10;

float lerNewton() {
  // leitura de 1 amostra, sem média (a média esconderia o pico)
  long bruto = cel.read() - cel.get_offset();
  float gramas = bruto / fatorEscala;
  return gramas * 0.00980665f;
}

void piscar(int vezes, int ms) {
  for (int i = 0; i < vezes; i++) {
    digitalWrite(PIN_LED, HIGH); delay(ms);
    digitalWrite(PIN_LED, LOW);  delay(ms);
  }
}

void salvarEEPROM() {
  EEPROM.put(EE_FATOR, fatorEscala);
  EEPROM.put(EE_DUR, duracaoMs);
  EEPROM.put(EE_N, (int16_t)nGravadas);
  for (int i = 0; i < nGravadas; i++) EEPROM.put(EE_DADOS + 2 * i, curva[i]);
}

void despejar(bool daEEPROM) {
  int16_t n = nGravadas;
  unsigned long dur = duracaoMs;
  if (daEEPROM) { EEPROM.get(EE_N, n); EEPROM.get(EE_DUR, dur); }
  if (n <= 0 || n > N_AMOSTRAS) { Serial.println(F("# nada gravado")); return; }
  Serial.println(F("# i,t_ms,empuxo_N"));
  Serial.print(F("# taxa_hz=")); Serial.println(1000.0 * n / dur, 2);
  for (int i = 0; i < n; i++) {
    int16_t v = curva[i];
    if (daEEPROM) EEPROM.get(EE_DADOS + 2 * i, v);
    float t = (float)dur * i / n - (float)dur * N_PRE / n;   // t = 0 no gatilho
    Serial.print(i); Serial.print(',');
    Serial.print(t, 1); Serial.print(',');
    Serial.println(v / 100.0, 3);
  }
  Serial.println(F("# fim"));
}

void gravar() {
  Serial.println(F("# ARMADO: aguardando empuxo..."));
  int16_t pre[N_PRE];
  int ip = 0;
  bool cheio = false;
  // espera o gatilho mantendo um anel com o que veio antes
  while (true) {
    if (Serial.available() && Serial.read() == 'x') { Serial.println(F("# desarmado")); return; }
    if (!cel.is_ready()) continue;
    float f = lerNewton();
    pre[ip] = (int16_t)constrain(f * 100.0f, -32000, 32000);
    ip = (ip + 1) % N_PRE;
    if (ip == 0) cheio = true;
    digitalWrite(PIN_LED, (millis() / 500) % 2);      // pisca devagar: armado
    if (f > GATILHO_N && cheio) break;
  }
  unsigned long t0 = millis();
  for (int i = 0; i < N_PRE; i++) curva[i] = pre[(ip + i) % N_PRE];
  int i = N_PRE;
  digitalWrite(PIN_LED, HIGH);
  while (i < N_AMOSTRAS) {
    if (!cel.is_ready()) continue;
    curva[i++] = (int16_t)constrain(lerNewton() * 100.0f, -32000, 32000);
  }
  unsigned long dt = millis() - t0;
  nGravadas = N_AMOSTRAS;
  // a janela gravada inclui o pré-gatilho: estima a duração total pela taxa
  duracaoMs = (unsigned long)((float)dt * N_AMOSTRAS / (N_AMOSTRAS - N_PRE));
  digitalWrite(PIN_LED, LOW);
  salvarEEPROM();
  Serial.println(F("# gravado e salvo na EEPROM. Mande 'd' para ver."));
  piscar(5, 80);
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_LED, OUTPUT);
  cel.begin(PIN_DT, PIN_SCK);
  EEPROM.get(EE_FATOR, fatorEscala);
  if (!(fatorEscala > 1.0f && fatorEscala < 1.0e7f)) fatorEscala = 400.0f;   // valor típico; calibre
  // sem travar se o HX711 não responder: só avisa (diagnóstico informa, não bloqueia)
  if (!cel.wait_ready_timeout(1000)) Serial.println(F("# AVISO: HX711 nao respondeu (confira DT/SCK/VCC)"));
  cel.set_offset(cel.read_average(20));
  Serial.println(F("# Bancada OBAFOG M5 pronta. Comandos: t c r a d e"));
}

void loop() {
  if (!Serial.available()) return;
  char cmd = Serial.read();
  if (cmd == 't') {
    cel.set_offset(cel.read_average(30));
    Serial.println(F("# tara feita"));
  } else if (cmd == 'c') {
    float g = Serial.parseFloat();
    if (g > 0) {
      long bruto = cel.read_average(30) - cel.get_offset();
      fatorEscala = bruto / g;
      EEPROM.put(EE_FATOR, fatorEscala);
      Serial.print(F("# fator = ")); Serial.println(fatorEscala, 3);
    }
  } else if (cmd == 'r') {
    unsigned long t0 = millis(); int n = 0; float soma = 0;
    while (millis() - t0 < 1000) if (cel.is_ready()) { soma += lerNewton(); n++; }
    Serial.print(F("# leitura media ")); Serial.print(soma / max(n, 1), 3);
    Serial.print(F(" N | taxa ")); Serial.print(n); Serial.println(F(" Hz (quer 80)"));
  } else if (cmd == 'a') {
    gravar();
  } else if (cmd == 'd') {
    despejar(false);
  } else if (cmd == 'e') {
    despejar(true);
  }
}
