"""Monta os STL na posição de voo e gera uma imagem de cada foguete (Python do sistema).

    python render_previews.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import trimesh  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]


def carregar(p: Path, dz: float) -> trimesh.Trimesh:
    m = trimesh.load(p, process=False)
    m.apply_translation([0, 0, dz])
    return m


def montar(pasta: Path, params: dict, foguete: str) -> list[tuple[trimesh.Trimesh, str]]:
    Lfc = params.get("fincan_len", 100.0)
    pecas = []
    pref = "F1" if foguete == "f1" else "F2"
    pecas.append((carregar(pasta / f"{pref}_lata_aletas_v1.stl", 0.0), "#ff7f0e"))
    topo = Lfc
    if params["body_len"] > 1:
        pecas.append((carregar(pasta / f"{pref}_tubo_corpo_v1.stl", Lfc), "#ffbb78"))
        topo = Lfc + params["body_len"]
    nome_ogiva = "F1_ogiva_v1.stl" if foguete == "f1" else "F2_ogiva_baia_v1.stl"
    pecas.append((carregar(pasta / nome_ogiva, topo - params["nose_shoulder"]), "#d62728"))
    return pecas


def render(pecas, titulo: str, saida: Path, motor: bool = True) -> None:
    fig = plt.figure(figsize=(5.2, 9))
    ax = fig.add_subplot(111, projection="3d")
    zs = []
    for m, cor in pecas:
        # decima a malha só para o desenho
        f = m.faces                                   # todos os triângulos (pular faz buracos)
        tri = m.vertices[f]
        # sombreamento simples pela normal (luz de cima/frente)
        n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
        luz = np.array([0.5, -0.6, 0.62]); luz /= np.linalg.norm(luz)
        k = 0.35 + 0.65 * np.clip(n @ luz, 0, 1)
        base = np.array(matplotlib.colors.to_rgb(cor))
        cores = np.clip(base[None, :] * k[:, None], 0, 1)
        ax.add_collection3d(Poly3DCollection(tri, facecolors=cores, edgecolors="none"))
        zs.append(m.vertices[:, 2])
    if motor:
        # motor (cano cinza) com o cap para fora da lata
        th = np.linspace(0, 2 * np.pi, 40)
        for z0, z1, r, cor in ((-21.0 + 18, 82.0, 10.0, "#7f7f7f"), (-21.0, -3.0, 12.3, "#bcbd22")):
            X = np.outer(r * np.cos(th), [1, 1]); Y = np.outer(r * np.sin(th), [1, 1])
            Z = np.outer(np.ones_like(th), [z0, z1])
            ax.plot_surface(X, Y, Z, color=cor, linewidth=0, alpha=0.9)
    z = np.concatenate(zs)
    zmin, zmax = min(z.min(), -25), z.max()
    meio = 0.5 * (zmin + zmax); meia = 0.5 * (zmax - zmin)
    ax.set_xlim(-meia * 0.35, meia * 0.35); ax.set_ylim(-meia * 0.35, meia * 0.35); ax.set_zlim(zmin, zmax)
    ax.set_box_aspect((0.7, 0.7, 2.0))
    ax.view_init(elev=12, azim=35)
    ax.set_axis_off()
    ax.set_title(titulo, fontsize=10)
    fig.tight_layout()
    saida.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(saida, dpi=130)
    plt.close(fig)


def main() -> None:
    casos = [("f1", "foguete1_obafog", "F1_construtivel_v1", "Foguete 1 — variante A"),
             ("f1", "foguete1_obafog", "F1_construtivel_v1B_ogiva_curta", "Foguete 1 — variante B"),
             ("f2", "foguete2_livre", "F2_29mm_v1", "Foguete 2 — 29 mm"),
             ("f2", "foguete2_livre", "F2_26mm_v1", "Foguete 2 — 26 mm")]
    for fog, pasta, versao, titulo in casos:
        d = RAIZ / pasta / "stl" / versao
        if not (d / "params_cad.json").exists():
            print("sem STL:", versao)
            continue
        params = json.loads((d / "params_cad.json").read_text(encoding="utf-8"))
        pecas = montar(d, params, fog)
        saida = RAIZ / pasta / "graficos" / f"{versao}_vista.png"
        render(pecas, titulo, saida)
        print(saida)


if __name__ == "__main__":
    main()
