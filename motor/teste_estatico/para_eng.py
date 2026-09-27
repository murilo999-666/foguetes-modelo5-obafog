"""Converte medições da bancada estática em curva .eng para o OpenRocket.

Uso:
    python para_eng.py teste1.csv teste2.csv teste3.csv  [--massa-cap 5.0]

Cada CSV é o que o Arduino imprime com o comando 'd' (linhas "i,t_ms,empuxo_N";
linhas começando com '#' são ignoradas). Cole a saída do Monitor Serial num
arquivo .csv por motor.

O que o script faz, por teste:
  1. tira o zero (média antes do gatilho);
  2. acha início e fim da queima (empuxo > 5% do pico);
  3. integra o impulso, calcula tempo de queima, empuxo médio e pico, Isp (22 g);
Depois faz a CURVA MÉDIA (reamostrada no tempo normalizado) e grava:
  - ../eng/OBAFOG-M5_MEDIDO.eng  (média)       -> use este no OpenRocket
  - ../eng/OBAFOG-M5_MEDIDO_min.eng / _max.eng (menor e maior impulso medidos)
  - resumo_testes.txt  e  curvas_medidas.png

Correção de peso: com o motor em pé (tubeira para cima, empurrando a célula para
baixo), a massa que queima também sai da leitura (~0,22 N ao longo da queima).
O script soma de volta essa rampa linear. Se a bancada for horizontal, use
--horizontal.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

G0 = 9.80665
M_PROP = 0.022
M_CASE_SEM_CAP = 0.0139


def ler(caminho: Path) -> tuple[np.ndarray, np.ndarray]:
    t, f = [], []
    for linha in caminho.read_text(encoding="utf-8", errors="ignore").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#"):
            continue
        partes = linha.split(",")
        if len(partes) < 3:
            continue
        t.append(float(partes[1]) / 1000.0)
        f.append(float(partes[2]))
    return np.array(t), np.array(f)


def analisar(t: np.ndarray, f: np.ndarray, horizontal: bool) -> dict:
    zero = np.median(f[t < 0]) if (t < 0).sum() >= 5 else 0.0
    f = f - zero
    pico = f.max()
    on = np.where(f > 0.05 * pico)[0]
    i0, i1 = on[0], on[-1]
    tq = t[i1] - t[i0]
    if not horizontal:
        # massa de propelente que sai durante a queima some da leitura vertical
        rampa = np.clip((t - t[i0]) / max(tq, 1e-3), 0, 1) * M_PROP * G0
        f = f + np.where(t >= t[i0], rampa, 0.0)
    tt = t[i0:i1 + 1] - t[i0]
    ff = np.clip(f[i0:i1 + 1], 0, None)
    imp = float(np.trapezoid(ff, tt))
    return {"t": tt, "f": ff, "impulso": imp, "tq": float(tq), "pico": float(ff.max()),
            "medio": imp / max(tq, 1e-3), "isp": imp / (M_PROP * G0)}


def escrever_eng(nome: str, t: np.ndarray, f: np.ndarray, caminho: Path, comentario: str) -> None:
    idx = np.linspace(0, len(t) - 1, min(len(t), 40)).astype(int)
    linhas = [f"; OBAFOG Modelo 5 - curva MEDIDA em bancada estatica | {comentario}",
              f"{nome} 20 103 P {M_PROP:.4f} {M_PROP + M_CASE_SEM_CAP:.4f} OBAFOG-medido"]
    ultimo = 0.0
    for i in idx:
        ti = max(float(t[i]), ultimo + 0.001)
        linhas.append(f"   {ti:.4f} {max(float(f[i]), 0.0):.3f}")
        ultimo = ti
    linhas.append(f"   {ultimo + 0.01:.4f} 0.000")
    linhas.append(";")
    caminho.write_text("\n".join(linhas) + "\n", encoding="ascii")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", nargs="+", type=Path)
    ap.add_argument("--horizontal", action="store_true")
    a = ap.parse_args()
    testes = [analisar(*ler(c), a.horizontal) | {"arquivo": c.name} for c in a.csv]
    saida_eng = Path(__file__).resolve().parents[1] / "eng"
    linhas = [f"{'teste':20s} {'imp N.s':>8s} {'tq s':>6s} {'pico N':>7s} {'medio N':>8s} {'Isp s':>6s}"]
    for r in testes:
        linhas.append(f"{r['arquivo']:20s} {r['impulso']:8.2f} {r['tq']:6.2f} {r['pico']:7.2f} "
                      f"{r['medio']:8.2f} {r['isp']:6.1f}")
    imps = np.array([r["impulso"] for r in testes])
    tqs = np.array([r["tq"] for r in testes])
    linhas.append(f"média: impulso {imps.mean():.2f} ± {imps.std(ddof=1) if len(imps) > 1 else 0:.2f} N.s, "
                  f"queima {tqs.mean():.2f} s")
    # curva média em tempo normalizado
    tau = np.linspace(0, 1, 200)
    fs = np.array([np.interp(tau, r["t"] / r["tq"], r["f"]) for r in testes])
    tq_m = float(tqs.mean())
    f_m = fs.mean(axis=0)
    f_m *= imps.mean() / np.trapezoid(f_m, tau * tq_m)     # preserva o impulso médio
    escrever_eng("OBAFOG-M5_MEDIDO", tau * tq_m, f_m, saida_eng / "OBAFOG-M5_MEDIDO.eng",
                 f"media de {len(testes)} testes, {imps.mean():.2f} N.s")
    for tag, r in (("min", testes[int(imps.argmin())]), ("max", testes[int(imps.argmax())])):
        escrever_eng(f"OBAFOG-M5_MEDIDO_{tag}", r["t"], r["f"], saida_eng / f"OBAFOG-M5_MEDIDO_{tag}.eng",
                     f"{r['arquivo']}, {r['impulso']:.2f} N.s")
    Path("resumo_testes.txt").write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print("\n".join(linhas))
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(7, 4))
        for r in testes:
            ax.plot(r["t"], r["f"], alpha=0.5, label=r["arquivo"])
        ax.plot(tau * tq_m, f_m, "k", lw=2.5, label="média")
        ax.set_xlabel("tempo (s)"); ax.set_ylabel("empuxo (N)"); ax.grid(alpha=0.3); ax.legend()
        fig.tight_layout(); fig.savefig("curvas_medidas.png", dpi=150)
    except Exception as e:  # gráfico é opcional
        print("sem gráfico:", e)
    print("gravado em", saida_eng)


if __name__ == "__main__":
    main()
