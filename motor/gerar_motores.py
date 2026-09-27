"""Família de curvas de empuxo do motor oficial da OBAFOG (Modelo 5) para o OpenRocket.

O motor é tratado como CAIXA-PRETA: não se reconstrói a química nem a balística
interna. A curva é montada só com o que foi medido ou publicado, e o que não se
sabe vira faixa de incerteza. Quando houver teste estático (pasta
teste_estatico/), a curva medida substitui esta família.

DADOS FIRMES (fonte entre parênteses)
  - 22 g de propelente por motor                 (regulamento 2026, p.11; vídeo 216)
  - cano PVC marrom soldável 20 mm x 100 mm      (regulamento 2026, p.11; vídeo 210)
  - cap 20 mm com furo de 7 mm, NÃO colado       (vídeo 210: salta como alívio de pressão)
  - tempo de queima ~1,2 s (1,2 a 1,25 s)        (live 208, 1:29:35, dados de muitos testes estáticos)
  - "todas as curvas muito parecidas"            (live 208, 1:28:00) -> dispersão pequena entre motores

FAIXA DE IMPULSO (não medida para este motor; limitada por medições publicadas)
  - piso ~ 7 N.s  (Isp 32 s): KNSu a frio, KNO3 impuro, sem fusão, bocal de argila,
    medido em voo -> v_e = 380 m/s, Isp ~ 39 s (RBEF, "Minifoguete a propelente
    sólido", 33 g, eletroduto 3/4"). Aqui o bocal é um furo em plástico que erode,
    então pode render menos.
  - teto ~ 11,5 N.s (Isp 53 s): KNSu a frio PRENSADO (3-10 t) com tubeira metálica
    rende Isp real de 63 a 82 s (Marchi/GFCS-UFPR 2021). O motor da OBA é
    compactado por queda de peso e tem tubeira de plástico, então fica abaixo.
  - CHECAGEM COM OS VOOS DA OBA (scripts/calibrar_com_voos_oba.py): garrafas PET
    de 500 mL estáveis (1,0-1,6 cal, 130-150 g) dão no OpenRocket 114-162 m com
    7 N.s e 158-211 m com 9 N.s; a OBA mostra ~100 m repetidos (às vezes >150 m).
    Ou o motor rende MENOS que 7 N.s, ou o OpenRocket subestima o arrasto de uma
    garrafa artesanal (fita, aleta torta, coifa rombuda) -- provavelmente as duas.
    Por isso: NOMINAL = 7 N.s (Isp 32 s) e cenário pessimista de 5 N.s (Isp 23 s).

FORMATO (não publicado) -> 3 envelopes: REG (pico no início), NEU (patamar),
PRO (cresce até o fim). A saída da vara depende muito disso; o alcance, pouco.

MASSAS (estimadas, conferir na balança)
  - tubo PVC 20x1,5 mm, 100 mm: 12,4 g   | papel-alumínio + cola: 1,5 g
  - cap 20 mm: ~5 g -> NÃO entra no .eng; o foguete leva um componente de massa
    próprio atrás do tubo (o CG real do motor fica mais para trás que o centro).
  - total no .eng = 22 + 12,4 + 1,5 = 35,9 g ; vazio = 13,9 g
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

G0 = 9.80665
M_PROP = 0.022            # kg
M_CASE_NO_CAP = 0.0139    # kg (tubo + plugue de alumínio); o cap vai à parte
DIAM_MM = 20              # diâmetro do tubo (o cap tem ~24,6 mm, fica fora do foguete)
LEN_MM = 103              # tubo 100 mm + fundo do cap ~3 mm

# envelopes normalizados (tau = t/tb); cada um é reescalado para média 1
SHAPES = {
    "NEU": [(0.00, 0.0), (0.03, 0.9), (0.06, 1.15), (0.15, 1.08), (0.50, 1.02),
            (0.85, 0.98), (0.93, 0.70), (1.00, 0.0)],
    "REG": [(0.00, 0.0), (0.03, 1.2), (0.07, 1.90), (0.15, 1.45), (0.35, 1.05),
            (0.60, 0.85), (0.85, 0.72), (0.93, 0.45), (1.00, 0.0)],
    "PRO": [(0.00, 0.0), (0.04, 0.55), (0.10, 0.62), (0.40, 0.90), (0.70, 1.20),
            (0.88, 1.40), (0.94, 0.90), (1.00, 0.0)],
}
IMPULSES = {"I05": 5.0, "I07": 7.0, "I09": 9.0, "I115": 11.5}   # N.s (nominal I07)
TB_NOMINAL = 1.2


def curva(shape: str, impulso: float, tb: float, n: int = 400) -> tuple[np.ndarray, np.ndarray]:
    pts = np.array(SHAPES[shape], dtype=float)
    tau = np.linspace(0.0, 1.0, n)
    f = np.interp(tau, pts[:, 0], pts[:, 1])
    f /= np.trapezoid(f, tau)                  # média 1 no intervalo [0,1]
    t = tau * tb
    F = f * impulso / tb
    return t, F


def reamostrar(t: np.ndarray, F: np.ndarray, shape: str, tb: float) -> list[tuple[float, float]]:
    """Guarda os vértices do envelope (formato fiel) + pontos intermediários."""
    pts = np.array(SHAPES[shape])
    tt = sorted(set(np.round(np.concatenate([pts[:, 0] * tb, np.linspace(0, tb, 25)]), 4)))
    out = []
    for ti in tt:
        fi = float(np.interp(ti, t, F))
        out.append((max(ti, 0.0), max(fi, 0.0)))
    # RASP: primeiro ponto com t>0, último ponto com empuxo zero
    out = [(max(a, 0.001), b) for a, b in out if not (a == 0.0 and b == 0.0)]
    out[-1] = (tb, 0.0)
    return out


def escrever_eng(nome: str, shape: str, impulso: float, tb: float, pasta: Path) -> dict:
    t, F = curva(shape, impulso, tb)
    pts = reamostrar(t, F, shape, tb)
    # impulso real depois da reamostragem (o OpenRocket integra os pontos)
    tp = np.array([0.0] + [a for a, _ in pts]); Fp = np.array([0.0] + [b for _, b in pts])
    imp = float(np.trapezoid(Fp, tp))
    isp = imp / (M_PROP * G0)
    total = M_PROP + M_CASE_NO_CAP
    linhas = [
        f"; OBAFOG Modelo 5 - motor oficial (PVC 20x100, 22 g, cap 7 mm) - CURVA ESTIMADA",
        f"; envelope {shape} | impulso {imp:.2f} N.s | Isp {isp:.1f} s | queima {tb:.2f} s | "
        f"pico {F.max():.1f} N | medio {imp/tb:.2f} N",
        f"; massa sem o cap ({total*1000:.1f} g); o cap (~5 g) e um componente de massa do foguete",
        f"; substituir pela curva do teste estatico assim que houver (motor/teste_estatico/)",
        f"{nome} {DIAM_MM} {LEN_MM} P {M_PROP:.4f} {total:.4f} OBAFOG-est",
    ]
    for a, b in pts:
        linhas.append(f"   {a:.4f} {b:.3f}")
    linhas.append(";")
    (pasta / f"{nome}.eng").write_text("\n".join(linhas) + "\n", encoding="ascii")
    return {"nome": nome, "shape": shape, "impulso": imp, "isp": isp, "tb": tb,
            "pico": float(F.max()), "medio": imp / tb}


def main() -> None:
    pasta = Path(__file__).parent / "eng"
    pasta.mkdir(exist_ok=True)
    rows = []
    for shape in SHAPES:
        for tag, imp in IMPULSES.items():
            rows.append(escrever_eng(f"OBAFOG-M5_{shape}_{tag}", shape, imp, TB_NOMINAL, pasta))
    # sensibilidade ao tempo de queima (envelope NEU, impulso nominal)
    for tb in (1.0, 1.4):
        rows.append(escrever_eng(f"OBAFOG-M5_NEU_I07_tb{int(tb*10):02d}", "NEU", 7.0, tb, pasta))
    print(f"{'motor':28s} {'imp N.s':>8s} {'Isp s':>6s} {'tb s':>5s} {'pico N':>7s} {'medio N':>8s}")
    for r in rows:
        print(f"{r['nome']:28s} {r['impulso']:8.2f} {r['isp']:6.1f} {r['tb']:5.2f} "
              f"{r['pico']:7.1f} {r['medio']:8.2f}")


if __name__ == "__main__":
    main()
