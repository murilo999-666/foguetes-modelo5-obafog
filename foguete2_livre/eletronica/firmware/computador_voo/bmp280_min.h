// bmp280_min.h — driver mínimo do BMP280/BME280 (só pressão e temperatura), sem biblioteca.
// Fórmulas de compensação: datasheet Bosch BMP280 rev 1.26, seção 8.2 (versão em ponto flutuante).
// Aceita chip ID 0x58 (BMP280) e 0x60 (BME280): módulos "BMP280" baratos às vezes vêm com BME.
#pragma once
#include <Arduino.h>
#include <Wire.h>

class BMP280min {
 public:
  uint8_t endereco = 0, chip_id = 0;

  bool begin(TwoWire& w = Wire) {
    wire_ = &w;
    for (uint8_t a : {0x76, 0x77}) {
      endereco = a;
      chip_id = ler8(0xD0);
      if (chip_id == 0x58 || chip_id == 0x60) break;
      endereco = 0;
    }
    if (!endereco) return false;
    escrever8(0xE0, 0xB6);                 // reset
    delay(5);
    lerCalibracao();
    // oversampling: temperatura x1, pressão x4 (~11,5 ms por medida); modo normal
    // IIR desligado: quem filtra é o Kalman (IIR atrasaria o apogeu)
    escrever8(0xF5, (0b000 << 5) | (0b000 << 2));   // t_standby 0,5 ms, filtro off
    escrever8(0xF4, (0b001 << 5) | (0b011 << 2) | 0b11);
    return true;
  }

  // lê pressão (Pa) e temperatura (C); false se a leitura falhou
  bool ler(float& pressao, float& temperatura) {
    uint8_t b[6];
    if (!lerBloco(0xF7, b, 6)) return false;
    int32_t adc_p = ((int32_t)b[0] << 12) | ((int32_t)b[1] << 4) | (b[2] >> 4);
    int32_t adc_t = ((int32_t)b[3] << 12) | ((int32_t)b[4] << 4) | (b[5] >> 4);
    if (adc_p == 0x80000 || adc_t == 0x80000) return false;   // medida ainda não pronta
    double v1 = (adc_t / 16384.0 - T1 / 1024.0) * T2;
    double v2 = (adc_t / 131072.0 - T1 / 8192.0) * (adc_t / 131072.0 - T1 / 8192.0) * T3;
    double t_fine = v1 + v2;
    temperatura = (float)(t_fine / 5120.0);
    v1 = t_fine / 2.0 - 64000.0;
    v2 = v1 * v1 * P6 / 32768.0;
    v2 = v2 + v1 * P5 * 2.0;
    v2 = v2 / 4.0 + P4 * 65536.0;
    v1 = (P3 * v1 * v1 / 524288.0 + P2 * v1) / 524288.0;
    v1 = (1.0 + v1 / 32768.0) * P1;
    if (v1 == 0.0) return false;
    double p = 1048576.0 - adc_p;
    p = (p - v2 / 4096.0) * 6250.0 / v1;
    v1 = P9 * p * p / 2147483648.0;
    v2 = p * P8 / 32768.0;
    pressao = (float)(p + (v1 + v2 + P7) / 16.0);
    return true;
  }

 private:
  TwoWire* wire_ = nullptr;
  uint16_t T1 = 0, P1 = 0;
  int16_t T2 = 0, T3 = 0, P2 = 0, P3 = 0, P4 = 0, P5 = 0, P6 = 0, P7 = 0, P8 = 0, P9 = 0;

  uint8_t ler8(uint8_t reg) {
    uint8_t v = 0;
    lerBloco(reg, &v, 1);
    return v;
  }
  void escrever8(uint8_t reg, uint8_t v) {
    wire_->beginTransmission(endereco);
    wire_->write(reg);
    wire_->write(v);
    wire_->endTransmission();
  }
  bool lerBloco(uint8_t reg, uint8_t* dst, uint8_t n) {
    wire_->beginTransmission(endereco);
    wire_->write(reg);
    if (wire_->endTransmission(false) != 0) return false;
    if (wire_->requestFrom((int)endereco, (int)n) != n) return false;
    for (uint8_t i = 0; i < n; i++) dst[i] = wire_->read();
    return true;
  }
  void lerCalibracao() {
    uint8_t c[24];
    lerBloco(0x88, c, 24);
    auto u16 = [&](int i) { return (uint16_t)(c[i] | (c[i + 1] << 8)); };
    auto s16 = [&](int i) { return (int16_t)(c[i] | (c[i + 1] << 8)); };
    T1 = u16(0); T2 = s16(2); T3 = s16(4);
    P1 = u16(6); P2 = s16(8); P3 = s16(10); P4 = s16(12); P5 = s16(14);
    P6 = s16(16); P7 = s16(18); P8 = s16(20); P9 = s16(22);
  }
};
