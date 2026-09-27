"""Figuras AUTÊNTICAS do OpenRocket (o mesmo desenhista da janela do programa):
vista lateral com CG/CP e o quadro de informações, e vista traseira.

Precisa de uma JVM NÃO headless (o RocketFigure consulta a tela ao ser criado; nenhuma
janela é aberta). Rodar com:
    set ORX_JVM_OPTS=-Djava.awt.headless=false
    <venv>\\python.exe render_openrocket.py <pasta_saida>
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from m5lib import RAIZ, Ctx, J, estabilidade_estatica

VERSOES = [
    ("foguete1_obafog/F1_construtivel_v1.ork", "F1_A"),
    ("foguete1_obafog/F1_construtivel_v1B_ogiva_curta.ork", "F1_B"),
    ("foguete2_livre/F2_29mm_v1.ork", "F2_29"),
    ("foguete2_livre/F2_26mm_v1.ork", "F2_26"),
]


def render(doc, tipo: str, largura: int, altura: int, caminho: Path, info: bool) -> None:
    c = Ctx.get()
    rocket = doc.getRocket()
    est = estabilidade_estatica(doc)
    RocketFigure = J("info.openrocket.swing.gui.scalefigure.RocketFigure")
    VT = J("info.openrocket.swing.gui.scalefigure.RocketPanel$VIEW_TYPE")
    BI = J("java.awt.image.BufferedImage")
    Dim = J("java.awt.Dimension")
    Color = J("java.awt.Color")
    RH = J("java.awt.RenderingHints")
    fig = RocketFigure(rocket)
    fig.setType(getattr(VT, tipo))
    if tipo == "SideView":
        fig.setDrawCarets(True)
        fig.addRelativeExtra(J("info.openrocket.swing.gui.figureelements.CGCaret")(est["cg_mm"] / 1000, 0.0))
        fig.addRelativeExtra(J("info.openrocket.swing.gui.figureelements.CPCaret")(est["cp_mm"] / 1000, 0.0))
        if info:
            cfg = rocket.getSelectedConfiguration()
            ri = J("info.openrocket.swing.gui.figureelements.RocketInfo")(cfg)
            ri.setCG(est["cg_mm"] / 1000)
            ri.setCP(est["cp_mm"] / 1000)
            ri.setLength(float(rocket.getLength()))
            ri.setDiameter(est["ref_mm"] / 1000)
            ri.setMassWithMotors(est["massa_g"] / 1000)
            ri.setMassWithoutMotors((est["massa_seca_g"] - 13.9) / 1000)
            ri.setMach(0.3)
            ri.setAOA(0.0)
            ri.setShowWarnings(False)
            sims = list(doc.getSimulations())
            if sims:
                c.b.run_simulation(sims[0])
                ri.setSimulation(sims[0])
                ri.setFlightData(sims[0].getSimulatedData())
            fig.addAbsoluteExtra(ri)
    fig.setSize(largura, altura)
    fig.updateFigure()
    fig.scaleTo(Dim(largura, altura))
    img = BI(largura, altura, BI.TYPE_INT_ARGB)
    g = img.createGraphics()
    g.setRenderingHint(RH.KEY_ANTIALIASING, RH.VALUE_ANTIALIAS_ON)
    g.setRenderingHint(RH.KEY_TEXT_ANTIALIASING, RH.VALUE_TEXT_ANTIALIAS_ON)
    g.setColor(Color.WHITE)
    g.fillRect(0, 0, largura, altura)
    fig.paint(g)
    g.dispose()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    J("javax.imageio.ImageIO").write(img, "png", J("java.io.File")(str(caminho)))


def recortar(caminho: Path, margem: int = 24) -> None:
    from PIL import Image, ImageChops
    im = Image.open(caminho).convert("RGB")
    fundo = Image.new("RGB", im.size, (255, 255, 255))
    bbox = ImageChops.difference(im, fundo).getbbox()
    if bbox:
        l, t, r, b = bbox
        im = im.crop((max(l - margem, 0), max(t - margem, 0), min(r + margem, im.width), min(b + margem, im.height)))
        im.save(caminho, optimize=True)


def main() -> None:
    saida = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "site_img"
    c = Ctx.get()
    for rel, tag in VERSOES:
        doc = c.b.load_document(str(RAIZ / rel))
        for tipo, (w, h), info in (("SideView", (2400, 820), True), ("BackView", (900, 900), False)):
            arq = saida / f"openrocket_{tag}_{'lateral' if tipo == 'SideView' else 'traseira'}.png"
            render(doc, tipo, w, h, arq, info)
            recortar(arq)
            print(arq, flush=True)


if __name__ == "__main__":
    main()
    os._exit(0)
