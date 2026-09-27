"""Moldes em papel (A4, escala 1:1) — imprimir em "tamanho real" (sem ajustar à página).

    python gerar_moldes.py <diametro_paraquedas_mm>

Gera:
  foguete2_livre/moldes/molde_gomo_paraquedas_<D>mm.pdf  (1/8 do paraquedas octogonal)
  foguete1_obafog/moldes/transferidor_haste.pdf          (lê a elevação da haste com fio de prumo)
Confira a régua de 100 mm impressa em cada folha antes de cortar.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
A4 = (210.0, 297.0)


def folha():
    fig = plt.figure(figsize=(A4[0] / 25.4, A4[1] / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, A4[0]); ax.set_ylim(0, A4[1]); ax.set_aspect("equal"); ax.axis("off")
    return fig, ax


def regua(ax, x0, y0):
    ax.plot([x0, x0 + 100], [y0, y0], "k", lw=1)
    for i in range(0, 101, 10):
        ax.plot([x0 + i, x0 + i], [y0, y0 + (3 if i % 50 else 5)], "k", lw=0.8)
    ax.text(x0 + 50, y0 + 6, "100 mm (confira antes de cortar)", ha="center", fontsize=7)


def gomo(D: float) -> Path:
    fig, ax = folha()
    s = D * math.tan(math.radians(22.5))       # lado do octógono (entre faces = D)
    h = D / 2
    cx, base_y = A4[0] / 2, 30.0
    ax_ = [(cx - s / 2, base_y), (cx + s / 2, base_y), (cx, base_y + h), (cx - s / 2, base_y)]
    ax.plot(*zip(*ax_), "k", lw=1.2)
    ax.plot([cx, cx], [base_y, base_y + h], "k--", lw=0.5)
    r_furo = 0.05 * D
    t = [math.radians(a) for a in range(-112, -67)]
    ax.plot([cx + r_furo * math.cos(a) for a in t], [base_y + h + r_furo * math.sin(a) for a in t], "k:", lw=1)
    ax.text(cx, base_y + h + 4, "centro (furo de alívio opcional)", ha="center", fontsize=7)
    ax.text(cx, base_y - 8, f"borda externa: {s:.0f} mm — reforce os 2 cantos com fita e amarre uma linha em cada", ha="center", fontsize=7)
    ax.text(cx, base_y + h * 0.45, f"1/8 DO PARAQUEDAS\nOctógono de {D:.0f} mm entre faces\n"
            f"Corte 8 destes (ou gire o molde 8 vezes\nsobre o plástico dobrado)", ha="center", fontsize=9)
    ax.text(10, 285, "Foguete 2 — molde do paraquedas", fontsize=12, weight="bold")
    ax.text(10, 277, "Material: saco de lixo grosso (~35 µm) ou ripstop. 8 linhas de nylon, cada uma com o "
            f"comprimento de {D:.0f} mm,", fontsize=7)
    ax.text(10, 272, "presas nos 8 cantos com fita (dobre a fita sobre a linha). Junte as 8 pontas num nó e "
            "prenda no cordão de choque.", fontsize=7)
    regua(ax, 55, 12)
    saida = RAIZ / "foguete2_livre" / "moldes" / f"molde_gomo_paraquedas_{D:.0f}mm.pdf"
    saida.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(saida); plt.close(fig)
    return saida


def transferidor() -> Path:
    """Borda reta encostada na haste, furo do fio na ponta da borda voltada para o ALTO
    da haste. Com a haste a theta graus do horizonte, o prumo aponta, no referencial da
    borda, para (-sen theta, -cos theta): cai do lado da BASE. A escala já vem em theta."""
    fig, ax = folha()
    R = 95.0
    cx, cy = 175.0, 215.0                      # furo do fio (lado da PONTA da haste)
    ax.plot([cx - R - 12, cx + 12], [cy, cy], "k", lw=1.5)           # borda reta
    ax.text(cx - R / 2, cy + 4, "← BASE da haste      encoste esta borda na haste      PONTA →",
            ha="center", fontsize=7)
    ax.add_patch(plt.Circle((cx, cy), 1.5, fill=False, lw=1))
    ax.text(cx - 2, cy + 9, "furo: fio + porca", fontsize=6, ha="center")
    for theta in range(20, 81):
        L = 8 if theta % 5 == 0 else 4
        sx, sy = -math.sin(math.radians(theta)), -math.cos(math.radians(theta))
        ax.plot([cx + (R - L) * sx, cx + R * sx], [cy + (R - L) * sy, cy + R * sy], "k",
                lw=0.9 if theta % 5 == 0 else 0.4)
        if theta % 5 == 0:
            ax.text(cx + (R + 8) * sx, cy + (R + 8) * sy, f"{theta}°", ha="center", va="center",
                    fontsize=8, weight="bold" if theta in (45, 50) else "normal")
    arco = [math.radians(t) for t in range(20, 81)]
    ax.plot([cx - R * math.sin(a) for a in arco], [cy - R * math.cos(a) for a in arco], "k", lw=1)
    ax.text(12, 285, "Transferidor da haste — lê a ELEVAÇÃO direto", fontsize=12, weight="bold")
    txt = chr(10).join([
        '1. Cole esta folha num papelão e recorte pela borda reta.',
        '2. Fure o centro marcado; passe um fio com uma porca (prumo).',
        '3. Encoste a borda reta na haste, com o furo para o lado da PONTA (alto) da haste.',
        '4. O fio pendurado cruza a escala na elevação da haste acima do horizonte.',
        '',
        'A haste de aço de 6 mm da Jornada VERGA com o próprio peso: a ponta fica ~2° mais baixa',
        'que a base. Meça na METADE DE CIMA da haste (é o ângulo com que o foguete sai),',
        'ou meça perto da base e some 2°. Confira de novo com o foguete já colocado.',
    ])
    ax.text(12, 95, txt, fontsize=8, va="top")
    regua(ax, 55, 15)
    saida = RAIZ / "foguete1_obafog" / "moldes" / "transferidor_haste.pdf"
    saida.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(saida); plt.close(fig)
    return saida


if __name__ == "__main__":
    D = float(sys.argv[1]) if len(sys.argv) > 1 else 380.0
    print(gomo(D))
    print(transferidor())
