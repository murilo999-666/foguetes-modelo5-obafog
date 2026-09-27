// teste_voo.cpp — roda a LÓGICA DE VOO REAL (voo.h) no PC com trajetórias do OpenRocket.
//
// Compilar (sem Visual Studio):  python -m ziglang c++ -std=c++17 -O2 teste_voo.cpp -o teste_voo.exe
// Rodar:  teste_voo.exe <trajetoria.csv> <ruido_Pa> <semente> [picos=0/1] [falha=0/1] [log.csv]
//
// A trajetória vem do OpenRocket (t_s, altitude_m). O teste:
//   1. fica 60 s "no chão" (armado) com ruído e rajadas de pressão -> não pode detectar decolagem
//   2. converte altitude em pressão (atmosfera padrão) e soma ruído gaussiano do barômetro
//   3. amostra a 50 Hz com jitter de +-2 ms, como o loop do ESP32
//   4. opcional: picos de +-60 Pa em 1% das amostras; congelamento do sensor por 0,4 s na subida
// Saída: uma linha JSON com os tempos de decolagem, abertura (e o motivo) e pouso.
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <random>
#include <string>
#include <vector>

#include "../firmware/computador_voo/voo.h"

struct Ponto { double t, h; };

static std::vector<Ponto> ler_csv(const char* caminho) {
  std::vector<Ponto> v;
  FILE* f = std::fopen(caminho, "r");
  if (!f) { std::fprintf(stderr, "nao abriu %s\n", caminho); std::exit(2); }
  char linha[256];
  while (std::fgets(linha, sizeof linha, f)) {
    if (linha[0] == '#' || linha[0] == 't') continue;
    double t, h;
    if (std::sscanf(linha, "%lf,%lf", &t, &h) == 2) v.push_back({t, h});
  }
  std::fclose(f);
  return v;
}

static double interp(const std::vector<Ponto>& v, double t) {
  if (t <= v.front().t) return v.front().h;
  if (t >= v.back().t) return v.back().h;
  size_t lo = 0, hi = v.size() - 1;
  while (hi - lo > 1) { size_t m = (lo + hi) / 2; (v[m].t <= t ? lo : hi) = m; }
  double a = (t - v[lo].t) / (v[hi].t - v[lo].t);
  return v[lo].h + a * (v[hi].h - v[lo].h);
}

int main(int argc, char** argv) {
  if (argc < 4) { std::fprintf(stderr, "uso: teste_voo traj.csv ruido_Pa semente [picos] [falha] [log]\n"); return 1; }
  auto traj = ler_csv(argv[1]);
  const double ruido = std::atof(argv[2]);
  std::mt19937 rng((unsigned)std::atoi(argv[3]));
  const bool picos = argc > 4 && std::atoi(argv[4]);
  const bool falha = argc > 5 && std::atoi(argv[5]);
  FILE* log = argc > 6 ? std::fopen(argv[6], "w") : nullptr;
  if (log) std::fprintf(log, "t_s,h_real,h_bruto,h_filtrado,v_filtrada,estado\n");

  std::normal_distribution<double> n01(0.0, 1.0);
  std::uniform_real_distribution<double> u01(0.0, 1.0);
  const double P0 = 97000.0;                       // ~ 350 m de altitude
  auto pressao_de_h = [&](double h) { return P0 * std::pow(1.0 - h / 44330.0, 5.25588); };

  // apogeu real da trajetória
  double t_apo = 0, h_apo = -1;
  for (auto& p : traj) if (p.h > h_apo) { h_apo = p.h; t_apo = p.t; }
  const double t_fim = traj.back().t;

  voo::Computador fc;
  const double T_CHAO = 60.0;                      // tempo armado antes da decolagem
  double t = 0;
  uint32_t t_ms = 1000;
  fc.armar(pressao_de_h(0.0), t_ms);
  // o .ino mede o ruído no chão antes de armar: imita isso
  fc.cfg.sigma_h_m = std::fmax(0.1, ruido / 11.5);

  double t_dec = -1, t_abre = -1, t_pouso = -1, h_abre = 0;
  double congelado_ate = -1, p_congelado = 0;
  bool falso_no_chao = false;
  const char* motivo = "";
  while (t < T_CHAO + t_fim + 8.0) {
    double dt = 0.020 + (u01(rng) - 0.5) * 0.004; // jitter do loop
    t += dt;
    t_ms += (uint32_t)std::lround(dt * 1000.0);
    double tv = t - T_CHAO;                        // tempo de voo real (0 = ignição)
    double h = tv < 0 ? 0.0 : interp(traj, tv);
    double p = pressao_de_h(h) + ruido * n01(rng);
    if (tv < 0) p += 6.0 * std::sin(2 * 3.14159265358979 * 0.7 * t) * (u01(rng) < 0.5 ? 1 : -1) * 0.5;  // rajadas no chão
    if (picos && u01(rng) < 0.01) p += (u01(rng) < 0.5 ? -60.0 : 60.0);
    if (falha && tv > 0.8 && tv < 1.2) {           // sensor congela 0,4 s na propulsão
      if (congelado_ate < 0) { congelado_ate = 1.2; p_congelado = p; }
      p = p_congelado;
    }
    voo::Estado antes = fc.estado;
    voo::Saida s = fc.passo(t_ms, (float)p);
    if (antes == voo::Estado::ARMADO && fc.estado == voo::Estado::SUBIDA) {
      t_dec = tv;
      if (tv < 0) falso_no_chao = true;
    }
    if (s.abrir) { t_abre = tv; h_abre = h; motivo = fc.motivo; }
    if (antes != voo::Estado::POUSADO && fc.estado == voo::Estado::POUSADO) t_pouso = tv;
    if (log && tv > -1.0) std::fprintf(log, "%.3f,%.2f,%.2f,%.2f,%.2f,%d\n", tv, h, fc.h_bruto, fc.kf.h, fc.kf.v, (int)fc.estado);
  }
  if (log) std::fclose(log);
  // velocidade vertical real no instante da abertura
  double v_abre = 0;
  if (t_abre > 0) v_abre = (interp(traj, t_abre + 0.05) - interp(traj, t_abre - 0.05)) / 0.1;
  std::printf("{\"arquivo\":\"%s\",\"ruido_Pa\":%.1f,\"picos\":%d,\"falha\":%d,\"apogeu_real\":%.1f,"
              "\"t_apogeu\":%.2f,\"t_decolagem_detectada\":%.2f,\"falso_no_chao\":%d,\"t_abertura\":%.2f,"
              "\"atraso_abertura\":%.2f,\"h_abertura\":%.1f,\"v_vertical_abertura\":%.1f,\"motivo\":\"%s\","
              "\"apogeu_registrado\":%.1f,\"t_pouso_detectado\":%.2f,\"t_fim_traj\":%.2f}\n",
              argv[1], ruido, picos, falha, h_apo, t_apo, t_dec, falso_no_chao ? 1 : 0, t_abre,
              t_abre > 0 ? t_abre - t_apo : -99.0, h_abre, v_abre, motivo, fc.h_max, t_pouso, t_fim);
  return 0;
}
