# Eletrônica do Foguete 2 — computador de voo com paraquedas por servo

Objetivo: detectar o apogeu pelo barômetro e soltar a ogiva (o paraquedas sai empurrado
por uma mola), registrar o voo e ajudar a achar o foguete no chão. **Sem pólvora**: a
carga de ejeção comum usa pólvora negra, produto controlado, e o motor da OBAFOG não tem
carga de ejeção. Servo + mola é recarregável, testável na bancada quantas vezes quiser.

## O que é obrigatório e o que é opcional

| Item | Status | Por quê (número) |
|---|---|---|
| ESP32-C3 SuperMini | **obrigatório** | ~2 g, 22,5 x 18 mm; 23–28 mA com Wi-Fi desligado a 160 MHz (datasheet Espressif, modo modem-sleep, CPU rodando) |
| BMP280 (ou BMP390) | **obrigatório** | é quem vê o apogeu; precisão relativa ±0,12 hPa = ±1 m (datasheet Bosch rev 1.26) |
| Micro servo ~3,7 g | **obrigatório** | trava a ogiva; aceita 1S (3,7–4,2 V) — **conferir no anúncio**, varia por modelo |
| LiPo 1S 150–250 mAh | **obrigatório** | ver autonomia abaixo |
| Chave liga/desliga | **obrigatório** | desligar a bateria antes de plugar o USB (ver alerta) |
| Buzzer ativo 3–5 V + NPN (S8050/BC337) + 1 kΩ | **obrigatório na prática** | sem ele, achar o foguete no mato é sorte; o buzzer puxa ~20–30 mA, mais do que um GPIO deve fornecer — por isso o transistor |
| Divisor 100k/100k para ler a bateria | recomendado | mostra "CARREGAR" na página; custa 2 resistores |
| MPU6050 | **opcional** | melhora o instante da decolagem (acelerômetro vê em ~20 ms; o barômetro só em ~0,4 s). O teste SIL passou 100% **só com barômetro** |
| Diodo Schottky SS14/1N5817 bateria→5V | opcional | só necessário se você quiser plugar o USB com a bateria ligada |
| Capacitor 220–470 µF perto do servo | opcional | só se o servo resetar a placa ao mexer (na bancada dá para ver) |

## Ligação

```
                 chave
 LiPo+ ──────────o/ o────┬──────────────► pino 5V da SuperMini (regulador da placa -> 3V3)
                         ├──────────────► servo VCC (vermelho)
                         ├──[100k]──┬──[100k]── GND
                         │          └──────► GPIO3 (leitura da bateria)
                         └──► buzzer (+) ── buzzer (−) ──► coletor NPN
 LiPo− ─────────────────────── GND comum (placa, servo marrom/preto, sensores, emissor do NPN)

 GPIO4 ──[1k]──► base do NPN          GPIO5 ──► servo sinal (laranja/amarelo)
 GPIO6 ──► SDA  (BMP280, MPU6050)      GPIO7 ──► SCL (BMP280, MPU6050)
 3V3   ──► VCC dos sensores            GPIO8 = LED azul da placa (acende em LOW)
```

Por que esses pinos: no ESP32-C3 os pinos de boot são o **2, o 8 e o 9** (na SuperMini o 8
tem o LED e o 9 o botão BOOT); 18/19 são o USB. O ADC da bateria fica no ADC1 (GPIO3),
que funciona com o Wi-Fi ligado.

**ALERTA:** a bateria entra no pino 5V. Se o USB for plugado com a chave ligada, o USB
empurra 5 V na LiPo. Regra: **chave desligada para plugar o USB** (ou coloque o diodo).

## Orçamento de corrente e autonomia

| Consumidor | Corrente | Fonte |
|---|---|---|
| ESP32-C3, Wi-Fi desligado | 23–28 mA (+~10 mA acessando flash) | datasheet ESP32-C3 |
| ESP32-C3 com AP Wi-Fi (só no chão) | ~80–120 mA médio, picos de 300 mA | datasheet (TX/RX) |
| BMP280 a ~50 Hz | < 1 mA | datasheet |
| MPU6050 (opcional) | ~3,9 mA | datasheet InvenSense |
| Servo segurando | ~5–10 mA; movendo ~100–250 mA | **medir** (genérico) |
| Buzzer bipando | ~25 mA x fração do tempo | anúncio |
| LED da placa | ~2–5 mA | estimado |

Armado (Wi-Fi desligado): ~45 mA. Com 250 mAh e 80% útil: **250 x 0,8 / 45 ≈ 4,4 h** na
rampa. Com o AP ligado (preparo): ~1,5 h. Carregue antes de cada dia de lançamento.

## Massa (entra no OpenRocket como componentes de massa)

| Item | g |
|---|---|
| ESP32-C3 SuperMini | 2,0 |
| BMP280 | 1,0 |
| LiPo 250 mAh | 5,5 |
| micro servo | 3,7 |
| buzzer + NPN + resistores | 1,5 |
| fios e chave | 3,0 |
| berço impresso | 4,0 |
| **total** | **~20,7** |

Pese tudo na balança de cozinha (0,1 g) e corrija `F2_PADRAO` em `scripts/m5lib.py`.

## Firmware (`firmware/computador_voo/`)

- `voo.h` — lógica de voo **portátil** (Kalman de altitude/velocidade + estados). A mesma
  lógica roda no PC no teste SIL.
- `bmp280_min.h` — driver mínimo do BMP280/BME280 (sem biblioteca; aceita os dois chip IDs).
- `computador_voo.ino` — hardware, log, Wi-Fi.

Compila limpo com `--warnings all` (core esp32 3.3.12, placa "ESP32C3 Dev Module",
**USB CDC On Boot: Enabled**): 84% da flash, 30% da RAM (inclui 60 kB de log).

Estados: PREPARO → ARMADO → SUBIDA → DESCIDA → POUSADO.

| Regra | Valor | Por quê |
|---|---|---|
| Decolagem | altitude filtrada > 4 m **e** subindo > 6 m/s (ou acelerômetro > 3 g) | rajada no chão não passa nas duas |
| Bloqueio | 1,6 s depois da decolagem | motor queima ~1,2 s: nunca abre queimando |
| Apogeu | velocidade < −0,3 m/s por 4 amostras, **ou** caiu 2,5 m do máximo | só acima de 12 m |
| Backup | 8,5 s depois da decolagem | apogeu mais tardio simulado: 7,4 s (motor de 11,5 N·s) |
| Pouso | velocidade suavizada < 0,8 m/s por 3 s, ou 120 s depois da abertura | salva o voo, liga Wi-Fi, bipa o apogeu |
| Pico de sensor | resíduo > 6σ é ignorado (até 5 seguidas) | picos de ±60 Pa no teste |
| Reset em voo | se a placa reiniciar em SUBIDA/DESCIDA (queda de tensão), abre na hora | melhor abrir cedo que nunca |

## Teste SIL — o firmware real contra o OpenRocket (`sil/`)

`teste_voo.cpp` compila o `voo.h` no PC (`python -m ziglang c++`), recebe a trajetória do
OpenRocket, converte altitude em pressão, soma ruído de barômetro, rajadas no chão
(60 s armado), picos de ±60 Pa em 1% das amostras e 0,4 s de sensor congelado na
propulsão, e amostra a 50 Hz com jitter, como o `loop()`.

**Resultado: 480 de 480 casos aprovados** (6 motores x 2 ventos x 2 ruídos x picos x
falha x 5 sementes). Trajetórias do F2 de 29 mm, sem vento (com vento de 4 m/s o
apogeu cai 4–8 m e o resultado é o mesmo; tudo em `sil/resultado_sil.jsonl`):

| Trajetória | Apogeu | Abertura depois do apogeu (média / máx) | Velocidade vertical na abertura (máx) |
|---|---|---|---|
| 5 N·s | 58 m | 0,39 / 0,51 s | 4,9 m/s |
| 7 N·s (nominal) | 114 m | 0,39 / 0,55 s | 5,1 m/s |
| 9 N·s | 178 m | 0,41 / 0,59 s | 5,5 m/s |
| 11,5 N·s | 258 m | 0,39 / 0,52 s | 4,8 m/s |

Zero decolagem falsa no chão, pouso detectado em todos. A primeira versão da lógica
reprovou 210 casos (o pouso não era detectado com ruído) e abria 0,3 s **antes** do
apogeu no motor mais forte: foi o SIL que achou, e as correções estão no `voo.h`.

## Testes de bancada antes de voar

1. **Ruído do barômetro**: ligado e parado, a página mostra o ruído medido (esperado
   0,1–0,4 m). Acima de 0,8 m: sensor ruim, luz ou vento no furo.
2. **Trava**: "Destravar"/"Travar" pela página; o braço tem de entrar ~2 mm na janela do
   tubo e sair totalmente. Ajuste `SERVO_TRAVA_US`/`SERVO_SOLTA_US`.
3. **Ejeção no chão**: foguete montado, paraquedas dobrado, "Destravar" → a ogiva tem de
   sair e puxar o paraquedas para fora. Faça 10 vezes. Se enroscar, a mola é fraca ou o
   paraquedas está apertado demais.
4. **Voo de mão**: armado, suba uma escada ou um prédio (5–10 m) e desça: não pode abrir
   (fica abaixo de 12 m e não detecta decolagem) — mostra que não há disparo falso.
5. **Teste de elevador/carro** (opcional): subir 15 m ou mais e descer detecta "apogeu".
6. **Bateria**: > 3,9 V para voar.
