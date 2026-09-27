// voo.h — lógica de voo PORTÁTIL (sem Arduino): filtro de Kalman + máquina de estados.
//
// O mesmo arquivo compila no ESP32-C3 (computador_voo.ino) e no PC (../../sil/teste_voo.cpp),
// onde é testado com as trajetórias simuladas no OpenRocket + ruído de barômetro.
//
// Entrada: pressão (Pa) com carimbo de tempo (ms).  Saída: "abrir" (solta a ogiva/paraquedas).
//
// Estados:
//   PREPARO  -> ligado no chão, servo destravado, espera o operador (ou o tempo) armar
//   ARMADO   -> servo travado, pressão do chão sendo acompanhada, espera decolagem
//   SUBIDA   -> decolou; depois do bloqueio procura o apogeu (ou vence o tempo de backup)
//   DESCIDA  -> paraquedas comandado; espera pousar
//   POUSADO  -> parado no chão: salva o voo, liga o Wi-Fi, bipa o apogeu
#pragma once
#include <math.h>
#include <stdint.h>

namespace voo {

enum class Estado : uint8_t { PREPARO = 0, ARMADO = 1, SUBIDA = 2, DESCIDA = 3, POUSADO = 4 };

inline const char* nome(Estado e) {
  switch (e) {
    case Estado::PREPARO: return "PREPARO";
    case Estado::ARMADO: return "ARMADO";
    case Estado::SUBIDA: return "SUBIDA";
    case Estado::DESCIDA: return "DESCIDA";
    case Estado::POUSADO: return "POUSADO";
  }
  return "?";
}

struct Config {
  // tempos contados a partir da DETECÇÃO da decolagem (que chega ~0,4 s depois do real)
  float bloqueio_s     = 1.6f;   // nunca abre antes (queima de ~1,2 s + margem)
  float backup_s       = 8.5f;   // abre por tempo se o apogeu não foi detectado (apogeu de 11,5 N.s ~7,8 s)
  float h_decolagem_m  = 4.0f;   // decolagem = altitude filtrada acima disto...
  float v_decolagem_ms = 6.0f;   // ...e subindo mais rápido que isto
  float v_apogeu_ms    = -0.3f;  // apogeu = velocidade filtrada abaixo disto...
  int   n_apogeu       = 4;      // ...por N amostras seguidas (80 ms a 50 Hz)
  float queda_apogeu_m = 2.5f;   // ...ou altitude caiu isto abaixo do máximo
  float h_min_abrir_m  = 12.0f;  // não abre por apogeu abaixo disto (backup abre em qualquer altura)
  float v_pouso_ms     = 0.8f;   // pouso = |v suavizada| menor que isto...
  float t_pouso_s      = 3.0f;   // ...durante este tempo
  float t_descida_max_s = 120.0f; // ...ou, por garantia, este tempo depois da abertura
  float porta_sigma    = 6.0f;   // rejeita medida com resíduo > 6 sigma (picos do sensor)
  float sigma_h_m      = 0.35f;  // ruído do barômetro (m); o .ino mede no chão e corrige
  float sigma_a_prop   = 60.0f;  // m/s2: incerteza da aceleração durante a propulsão
  float sigma_a_voo    = 10.0f;  // m/s2: depois da queima
  float tau_chao_s     = 60.0f;  // pressão do chão acompanhada devagar enquanto ARMADO
};

inline float altitude_de_pressao(float p, float p0) {
  return 44330.0f * (1.0f - powf(p / p0, 0.190295f));   // atmosfera padrão (relativa ao chão)
}

// Kalman de 2 estados [h, v] com aceleração desconhecida tratada como ruído branco
struct Kalman2 {
  float h = 0, v = 0, P00 = 1, P01 = 0, P10 = 0, P11 = 1;
  int rejeitadas = 0;
  void reset(float h0) { h = h0; v = 0; P00 = 1; P01 = P10 = 0; P11 = 1; rejeitadas = 0; }
  // porta > 0: ignora a medida se o resíduo passar de porta*sigma (pico de sensor)
  void passo(float dt, float z, float sigma_a, float sigma_z, float porta = 0) {
    h += v * dt;
    const float q = sigma_a * sigma_a, dt2 = dt * dt, dt3 = dt2 * dt, dt4 = dt3 * dt;
    const float n00 = P00 + dt * (P10 + P01) + dt2 * P11 + q * dt4 * 0.25f;
    const float n01 = P01 + dt * P11 + q * dt3 * 0.5f;
    const float n10 = P10 + dt * P11 + q * dt3 * 0.5f;
    const float n11 = P11 + q * dt2;
    const float S = n00 + sigma_z * sigma_z;
    const float K0 = n00 / S, K1 = n10 / S;
    const float r = z - h;
    if (porta > 0 && r * r > porta * porta * S && rejeitadas < 5) {
      // só predição: aceita no máximo 5 seguidas (se for real, o filtro volta a seguir)
      P00 = n00; P01 = n01; P10 = n10; P11 = n11;
      rejeitadas++;
      return;
    }
    rejeitadas = 0;
    h += K0 * r;
    v += K1 * r;
    P00 = (1 - K0) * n00; P01 = (1 - K0) * n01;
    P10 = n10 - K1 * n00; P11 = n11 - K1 * n01;
  }
};

struct Saida {
  bool abrir = false;         // true UMA vez: soltar a ogiva agora
  bool mudou_estado = false;
};

class Computador {
 public:
  Config cfg;
  Estado estado = Estado::PREPARO;
  Kalman2 kf;
  float p0 = 101325.0f;       // pressão do chão
  float h_bruto = 0;          // altitude sem filtro (log)
  float h_max = 0;            // apogeu registrado (filtrado)
  uint32_t t_decolagem = 0, t_abertura = 0;
  const char* motivo = "";    // "velocidade", "queda", "tempo"
  bool decolagem_externa = false;   // acelerômetro (opcional) viu a decolagem
  float v_suave = 0;                // velocidade passada num filtro de ~1 s

  void armar(float p_chao, uint32_t t_ms) {
    p0 = p_chao;
    kf.reset(0);
    h_max = 0;
    cont_ = 0;
    t_ant_ = t_ms;
    parado_desde_ = 0;
    decolagem_externa = false;
    v_suave = 0;
    motivo = "";
    estado = Estado::ARMADO;
  }

  // o .ino chama quando o acelerômetro passa de ~3 g (opcional; sem ele, só barômetro)
  void sinal_decolagem() { decolagem_externa = true; }

  Saida passo(uint32_t t_ms, float pressao_pa) {
    Saida s;
    if (estado == Estado::PREPARO) { t_ant_ = t_ms; return s; }
    float dt = (t_ms - t_ant_) * 1e-3f;
    t_ant_ = t_ms;
    if (dt <= 0 || dt > 0.5f) dt = 0.02f;           // amostra perdida: não explode o filtro
    h_bruto = altitude_de_pressao(pressao_pa, p0);
    const bool propulsao = (estado == Estado::SUBIDA) &&
                           ((t_ms - t_decolagem) * 1e-3f < cfg.bloqueio_s);
    const bool armado_parado = (estado == Estado::ARMADO) && !decolagem_externa;
    // a porta anti-pico só vale fora da propulsão e fora do chão armado (lá a decolagem
    // legítima produz resíduo grande)
    const bool usa_porta = (estado == Estado::DESCIDA || estado == Estado::POUSADO ||
                            (estado == Estado::SUBIDA && !propulsao));
    kf.passo(dt, h_bruto, (propulsao || estado == Estado::ARMADO) ? cfg.sigma_a_prop : cfg.sigma_a_voo,
             cfg.sigma_h_m, usa_porta ? cfg.porta_sigma : 0.0f);
    v_suave += (dt / (1.0f + dt)) * (kf.v - v_suave);    // passa-baixa de ~1 s (só para o pouso)
    const Estado antes = estado;
    switch (estado) {
      case Estado::ARMADO: {
        if (armado_parado && fabsf(kf.v) < 1.0f && fabsf(kf.h) < 2.0f) {
          // acompanha a pressão do chão devagar (tempo, sol) enquanto espera
          const float a = dt / cfg.tau_chao_s;
          p0 += a * (pressao_pa - p0);
        }
        const bool pelo_baro = kf.h > cfg.h_decolagem_m && kf.v > cfg.v_decolagem_ms;
        if (pelo_baro || (decolagem_externa && kf.h > 1.0f)) {
          estado = Estado::SUBIDA;
          t_decolagem = t_ms;
          h_max = kf.h;
        }
        break;
      }
      case Estado::SUBIDA: {
        if (kf.h > h_max) h_max = kf.h;
        const float tv = (t_ms - t_decolagem) * 1e-3f;
        if (tv < cfg.bloqueio_s) break;             // ainda queimando: nunca abre
        cont_ = (kf.v < cfg.v_apogeu_ms) ? cont_ + 1 : 0;
        const bool alto = h_max > cfg.h_min_abrir_m;
        if (alto && cont_ >= cfg.n_apogeu) motivo = "velocidade";
        else if (alto && (h_max - kf.h) > cfg.queda_apogeu_m) motivo = "queda";
        else if (tv > cfg.backup_s) motivo = "tempo";
        if (motivo[0] != '\0') {
          estado = Estado::DESCIDA;
          t_abertura = t_ms;
          s.abrir = true;
          parado_desde_ = 0;
        }
        break;
      }
      case Estado::DESCIDA: {
        if (fabsf(v_suave) < cfg.v_pouso_ms && kf.h < h_max - 5.0f) {
          if (parado_desde_ == 0) parado_desde_ = t_ms;
          if ((t_ms - parado_desde_) * 1e-3f > cfg.t_pouso_s) estado = Estado::POUSADO;
        } else {
          parado_desde_ = 0;
        }
        if ((t_ms - t_abertura) * 1e-3f > cfg.t_descida_max_s) estado = Estado::POUSADO;
        break;
      }
      default:
        break;
    }
    s.mudou_estado = (estado != antes);
    return s;
  }

 private:
  uint32_t t_ant_ = 0, parado_desde_ = 0;
  int cont_ = 0;
};

}  // namespace voo
