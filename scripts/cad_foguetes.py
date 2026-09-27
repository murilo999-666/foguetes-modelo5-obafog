"""CAD paramétrico (manifold3d + trimesh) das peças impressas dos dois foguetes.

Usa as MESMAS cotas da m5lib/OpenRocket. Cada peça sai como sólido fechado
(o manifold garante watertight), em milímetros, JÁ NA ORIENTAÇÃO DE IMPRESSÃO:
eixo do foguete = Z, face que vai na mesa em z = 0.

Rodar com o Python do sistema (tem trimesh + manifold3d):
    python cad_foguetes.py f1 <params.json> <pasta_saida>
    python cad_foguetes.py f2 <params.json> <pasta_saida>
    python cad_foguetes.py gabaritos <pasta_saida>

Regras seguidas (skills 3d-modeling / 3d-printing):
  - paredes múltiplas do bico 0,4 mm (0,8 / 1,2 / 1,6 / 2,0 / 2,4)
  - nenhum balanço além de 45 graus: tetos cônicos, anéis e guias com cunha por baixo
  - furos compensados (+0,15 mm): o FDM fecha furo
  - aleta impressa em pé, junto da lata: a flexão da aleta fica no plano da camada
  - COTAS DE INTERFACE A CONFERIR (paquímetro): diâmetro do cano PVC, diâmetro e
    comprimento do cap, diâmetro da haste. Imprima os gabaritos antes.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import trimesh
from manifold3d import CrossSection, JoinType, Manifold, OpType

SEG = 144                         # segmentos de circunferência
N_PERFIL = 260                    # pontos do perfil da ogiva (menos = STL mais leve, para a web)
DENS = {"PLA": 1.24, "PETG": 1.27}   # g/cm3

# --- folgas e compensações (validar com os gabaritos) ---
FOLGA_OMBRO = 0.15                # mm por lado entre ombro e tubo
COMP_FURO = 0.15                  # mm a mais no diâmetro de furos
MOTOR_OD = 20.0                   # cano PVC soldável 20 (NBR 5648), CONFERIR
LUVA_ID = MOTOR_OD + 0.45 + COMP_FURO    # 20,6: cabe 1 volta de fita crepe
MOTOR_BARE = 85.0                 # tubo exposto à frente do cap (100 - 15 de bolsa)
FOLGA_CAP = 3.0                   # vão entre a lata e o cap: o cap precisa poder saltar
HASTE = 6.0                       # haste de aço da Jornada (6 mm x 1,5 m)
LUG_ID = HASTE + 1.5 + COMP_FURO  # 7,65 mm


# ---------------------------------------------------------------------------
# utilidades
# ---------------------------------------------------------------------------
def _ccw(pts):
    a = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        a += x1 * y2 - x2 * y1
    return pts if a > 0 else list(reversed(pts))


def _revolve(pts_rz) -> Manifold:
    """Revolve um polígono (r >= 0, z) em torno do eixo Z."""
    return Manifold.revolve(CrossSection([_ccw(list(pts_rz))]), SEG)


def tubo(r_ext: float, r_int: float, z0: float, z1: float) -> Manifold:
    if r_int <= 0:
        return Manifold.cylinder(z1 - z0, r_ext, r_ext, SEG).translate([0, 0, z0])
    return _revolve([(r_int, z0), (r_ext, z0), (r_ext, z1), (r_int, z1)])


def uniao(partes) -> Manifold:
    return Manifold.batch_boolean(list(partes), OpType.Add)


# ---------------------------------------------------------------------------
# perfis de ogiva (fórmulas do OpenRocket, Transition.Shape); x a partir da PONTA
# ---------------------------------------------------------------------------
def raio_ogiva(shape: str, x, L: float, R: float, param: float):
    x = np.clip(np.asarray(x, dtype=float), 0, L)
    s = shape.upper()
    if s == "CONICAL":
        return R * x / L
    if s == "ELLIPSOID":
        u = x / L
        return R * np.sqrt(np.clip(2 * u - u * u, 0, None))
    if s == "POWER":
        return R * (x / L) ** max(param, 1e-6)
    if s == "PARABOLIC":
        u = x / L
        return R * (2 * u - param * u * u) / (2 - param)
    if s == "HAACK":
        th = np.arccos(np.clip(1 - 2 * x / L, -1, 1))
        return R / math.sqrt(math.pi) * np.sqrt(
            np.clip(th - np.sin(2 * th) / 2 + param * np.sin(th) ** 3, 0, None))
    if s == "OGIVE":
        rho = (R * R + L * L) / (2 * R)
        r_t = np.sqrt(np.clip(rho * rho - (L - x) ** 2, 0, None)) + R - rho
        return r_t if param >= 0.999 else param * r_t + (1 - param) * R * x / L
    raise ValueError(shape)


def ogiva(p: dict, ombro_len: float | None = None, ombro_parede: float = 0.8,
          tampa_ombro: bool = False) -> Manifold:
    """Ogiva impressa em pé: ombro em z=[0,S], base da ogiva em z=S, ponta em z=S+L.
    Casca de espessura t medida na NORMAL da parede (como o OpenRocket)."""
    D, t, L = p["D"], p.get("nose_t", 0.8), p["nose_len"]
    S = p["nose_shoulder"] if ombro_len is None else ombro_len
    R = D / 2
    xs = np.linspace(0, L, N_PERFIL)
    rs = raio_ogiva(p["nose_shape"], xs, L, R, p.get("nose_param", 0.0))
    # perfil COMPLETO (espelhado) para o offset não criar pino no eixo
    lado = [(float(r), float(S + L - x)) for x, r in zip(xs, rs)]   # ponta -> base
    completo = [(-r, z) for r, z in reversed(lado)] + lado[1:]
    completo = [(-R, S)] + completo + [(R, S)]
    cs = CrossSection([_ccw(completo)])
    meio = CrossSection.square([R + 5, S + L + 5]).translate([0, -1])  # x >= 0
    ext = Manifold.revolve(cs ^ meio, SEG)
    vazio = Manifold.revolve(cs.offset(-t, JoinType.Round, 2.0, 64) ^ meio, SEG)
    r_om_e = R - p.get("wall", 0.8) - FOLGA_OMBRO
    r_om_i = r_om_e - ombro_parede
    vazio = vazio + tubo(r_om_i, 0.0, S - 1.0, S + t + 1.0)
    casca = ext - vazio
    ombro = tubo(r_om_e, r_om_i, 0.0, S + 0.01)
    partes = [casca, ombro]
    if tampa_ombro:
        partes.append(tubo(r_om_e, 0.0, 0.0, 1.2))       # fundo do ombro (F2: antepara)
    return uniao(partes)


def _aleta(p: dict, R: float, z_te: float, ang: float, u_min: float) -> Manifold:
    """Aleta trapezoidal em pé no plano radial 'ang'. A raiz continua para DENTRO
    da casca até u_min (vira nervura que encosta perto da luva do motor)."""
    root, tip, span = p["fin_root"], p["fin_tip"], p["fin_span"]
    sweep, t = p["fin_sweep"], p["fin_t"]
    z_le = z_te + root
    z_tip_te = z_le - sweep - tip
    if z_tip_te < z_te - 1e-6:
        raise ValueError("aleta com balanço para trás da raiz (não imprime sem suporte)")
    # polígono no plano (u = distância radial ao eixo, v = z)
    poly = [(u_min, z_te), (R + span * 0.0, z_te), (R + span, z_tip_te), (R + span, z_le - sweep),
            (R, z_le), (u_min, z_le)]
    placa = Manifold.extrude(CrossSection([_ccw(poly)]), t).translate([0, 0, -t / 2])
    placa = placa.rotate([90, 0, 0]).rotate([0, 0, math.degrees(ang)])
    # filetes triangulares (catetos ff) nas duas faces, ao longo da raiz externa
    ff = p.get("fin_fillet", 2.0) * 0.75
    partes = [placa]
    for s in (+1, -1):
        tt = t / 2 - 0.05                      # invade a placa: nada de face coincidente
        tri = [(R - 0.4, s * tt), (R + ff, s * tt), (R - 0.4, s * (tt + ff))]
        pr = Manifold.extrude(CrossSection([_ccw(tri)]), root).translate([0, 0, z_te])
        partes.append(pr.rotate([0, 0, math.degrees(ang)]))
    return uniao(partes)


def _guia(R: float, ang: float, z0: float, z1: float, parede: float, cunha: bool) -> tuple[Manifold, Manifold]:
    """Guia (tubinho) para a haste, encostada no corpo; devolve (sólido, furo)."""
    lug_or = LUG_ID / 2 + parede
    rc = R + lug_or - 0.3
    cx, cy = rc * math.cos(ang), rc * math.sin(ang)
    g = tubo(lug_or, 0.0, z0, z1).translate([cx, cy, 0])
    if cunha:
        # cunha de 45 graus embaixo da guia até a parede do corpo (sem suporte)
        h = 2 * lug_or
        base_disco = Manifold.cylinder(0.2, lug_or, lug_or, 48).translate([cx, cy, z0])
        pe = Manifold.cube([0.4, 2 * lug_or * 0.9, 0.2], True).translate(
            [R * math.cos(ang) - 0.2 * math.cos(ang), R * math.sin(ang), z0 - h])
        pe = pe.rotate([0, 0, 0])
        g = g + Manifold.batch_hull([base_disco, pe])
    furo = Manifold.cylinder(z1 - z0 + 4 * lug_or + 2, LUG_ID / 2, LUG_ID / 2, 48).translate(
        [cx, cy, z0 - 2 * lug_or - 1])
    return g, furo


# ---------------------------------------------------------------------------
# lata de aletas (as duas versões: F1 e F2)
# ---------------------------------------------------------------------------
def lata_aletas(p: dict, olhal: bool = False) -> Manifold:
    return lata_partes(p, olhal)["total"]


def lata_partes(p: dict, olhal: bool = False) -> dict:
    """Lata impressa em pé (traseira em z = 0):
    casca 0,8 mm + anel traseiro + anel dianteiro (chanfro 45 graus) + teto cônico
    fechado (batente do tubo de PVC = anel de empuxo, e antepara) + ombro que entra
    no tubo do corpo + aletas com raiz-nervura + guia traseira."""
    D, w = p["D"], p.get("wall", 0.8)
    R = D / 2
    Lfc = p.get("fincan_len", 100.0)
    r_i = R - w
    r_l = LUVA_ID / 2
    c = MOTOR_BARE - FOLGA_CAP                     # 82: onde a borda do PVC encosta
    estrutura = [tubo(R, r_i, 0.0, Lfc)]
    partes = estrutura
    partes.append(tubo(r_i + 0.02, r_l, 0.0, 8.0))                     # anel traseiro
    partes.append(_revolve([(r_l, c - 8.0), (r_i + 0.02, c - 8.0 - (r_i - r_l)),
                            (r_i + 0.02, c), (r_l, c)]))               # anel dianteiro
    e = 1.7                                                            # ~1,2 mm na normal
    partes.append(_revolve([(r_l, c), (0.0, c + r_l), (0.0, c + r_l + e),
                            (r_i + 0.02, c + e), (r_i + 0.02, c)]))    # teto cônico
    r_om = R - w - FOLGA_OMBRO
    sem_corpo = p.get("body_len", 0.0) <= 1.0
    if not sem_corpo:
        zs = Lfc - 4.0                                                 # ombro começa 4 mm dentro
        partes.append(tubo(r_om, r_om - 0.8, zs, Lfc + 15.0))          # ombro de encaixe no tubo
        ra, rb = r_om - 0.8, r_i + 0.02
        partes.append(_revolve([(ra, zs), (rb, zs - (rb - ra)), (rb, zs + 0.6), (ra, zs + 0.6)]))  # prateleira 45 graus
    # sem tubo do corpo, o ombro da OGIVA entra direto no topo da lata (acima do teto cônico)
    if olhal:
        zo = c + r_l + e
        ol = Manifold.cube([3.2, 12.0, 9.0], True).translate([0, 0, zo + 3.5])
        f_ol = Manifold.cylinder(6.0, 2.2, 2.2, 32, True).rotate([0, 90, 0]).translate([0, 0, zo + 4.5])
        partes.append(ol - f_ol)
    n = int(p["fin_n"])
    aletas = [_aleta(p, R, p.get("fin_offset", 0.0), 2 * math.pi * i / n + math.pi / SEG, r_l + 0.3)
              for i in range(n)]
    ang = math.pi / n + math.pi / SEG
    g, furo_g = _guia(R, ang, 0.0, p.get("lug_rear_len", 20.0), p.get("lug_wall", 1.0), cunha=False)
    if sem_corpo:
        # guia dianteira na própria lata (as duas guias na mesma peça: alinhadas por construção)
        z1 = Lfc - p.get("lug_front_top", 5.0)
        g2, furo_g2 = _guia(R, ang, z1 - p.get("lug_front_len", 15.0), z1, p.get("lug_wall", 1.0), cunha=True)
        g = g + g2
        furo_g = furo_g + furo_g2
    # a boca do motor já fica aberta pelos próprios anéis (furo = r_l); subtrair um
    # cilindro de MESMO raio criava faces coincidentes e malha não-manifold no fatiador
    estr = uniao(partes)
    estr_guia = (estr + g) - furo_g
    total = uniao([estr_guia] + aletas) - furo_g
    # partes LÍQUIDAS (sobreposição fica contada uma vez só, na estrutura)
    return {"total": total, "estrutura": estr, "guia": estr_guia - estr,
            "aletas": total - estr_guia}


def tubo_corpo(p: dict, com_guia: bool = True, janela_trava: bool = False) -> Manifold:
    D, w, Lb = p["D"], p.get("wall", 0.8), p["body_len"]
    R = D / 2
    corpo = tubo(R, R - w, 0.0, Lb)
    furos = []
    if com_guia:
        n = int(p["fin_n"])
        z1 = Lb - p.get("lug_front_top", 5.0)
        g, fg = _guia(R, math.pi / n, z1 - p.get("lug_front_len", 15.0), z1,
                      p.get("lug_wall", 1.0), cunha=True)
        corpo = corpo + g
        furos.append(fg)
    if janela_trava:
        # janela onde o braço do servo trava a ogiva (F2) e entalhe de alinhamento oposto
        furos.append(Manifold.cube([6.0, JANELA_LARG, JANELA_ALT], True).translate([R, 0, Lb - JANELA_Z]))
        furos.append(Manifold.cube([4.0, 2.4, 9.0], True).translate([-R, 0, Lb - 4.0]))
    for f in furos:
        corpo = corpo - f
    return corpo


# ---------------------------------------------------------------------------
# F2: berço de eletrônica e pistão
# ---------------------------------------------------------------------------
# posição da trava (F2): a janela fica JANELA_Z abaixo do topo do tubo do corpo; a
# fenda do ombro da ogiva fica na mesma altura quando a ogiva está encaixada
JANELA_Z = 12.0          # mm abaixo do topo do tubo
JANELA_LARG = 7.0        # mm (tangencial)
JANELA_ALT = 5.0         # mm (axial)


def ogiva_f2(p: dict) -> Manifold:
    """Ogiva do F2: ombro longo e ABERTO atrás (o berço entra por trás e a antepara
    dele fecha o ombro), com fenda para o braço do servo e nervura de alinhamento."""
    base = ogiva(p, tampa_ombro=False)
    D, w, S = p["D"], p.get("wall", 0.8), p["nose_shoulder"]
    r_om = D / 2 - w - FOLGA_OMBRO
    # z da fenda (impressão: ombro em z=[0,S]; topo do tubo encosta em z=S)
    zf = S - JANELA_Z
    fenda = Manifold.cube([6.0, JANELA_LARG + 1.0, JANELA_ALT + 1.0], True).translate([r_om, 0, zf])
    # nervura de alinhamento: a 180 graus da fenda, entra num entalhe no topo do tubo
    nerv = Manifold.cube([1.4, 2.0, 8.0], True).translate([-(r_om + 0.5), 0, S - 4.0])
    return (base - fenda) + nerv


def berco_eletronica(p: dict) -> Manifold:
    """Berço do F2 impresso em pé: antepara (fecha o ombro por trás, olhal para o
    cordão) + bandeja deslocada 3 mm do centro (o servo de 3,7 g só cabe assim no
    tubo de 26 mm) + bolso do servo alinhado com a fenda.
    Cotas de catálogo dos módulos — CONFIRA com os seus e ajuste antes de imprimir:
      ESP32-C3 SuperMini 22,5 x 18 x 4 | BMP280 15 x 11,5 | LiPo ~30 x 12-20 x 3-5
      micro servo 3,7 g ~20 x 8,5 x 18 (abas ~27)"""
    D, w, S = p["D"], p.get("wall", 0.8), p["nose_shoulder"]
    r_livre = D / 2 - w - FOLGA_OMBRO - 0.8 - 0.25       # raio interno do ombro menos folga
    L = S + 30.0                                          # sobe 30 mm para dentro da ogiva
    antepara = tubo(r_livre, 0.0, 0.0, 2.0)
    olhal = Manifold.cube([3.2, 10.0, 7.0], True).translate([0, 0, -3.0])
    olhal = olhal - Manifold.cylinder(6.0, 2.0, 2.0, 32, True).rotate([0, 90, 0]).translate([0, 0, -3.5])
    y0 = -3.0
    larg = 2 * math.sqrt(max(r_livre ** 2 - (y0 - 0.8) ** 2, 1.0)) - 1.0
    bandeja = Manifold.cube([larg, 1.6, L], True).translate([0, y0 - 0.8, L / 2 + 2.0])
    # bolso do servo: moldura acima da bandeja, na altura da fenda
    zs = (S - JANELA_Z) - 6.0
    moldura = (Manifold.cube([22.0, 8.0, 14.0], True) - Manifold.cube([20.4, 9.0, 12.4], True)
               ).translate([0, y0 + 4.0, zs + 7.0])
    trilhos = uniao([Manifold.cube([1.2, 3.0, L - 30], True).translate([sx * (larg / 2 - 0.6), y0 + 0.7, 32 + (L - 30) / 2])
                     for sx in (-1, 1)])
    corpo = uniao([antepara, olhal, bandeja, moldura, trilhos])
    # recorta tudo no cilindro livre (nada encosta na parede do ombro)
    return corpo ^ Manifold.cylinder(L + 20, r_livre, r_livre, SEG).translate([0, 0, -10])


def pistao(p: dict) -> Manifold:
    """Disco que a mola empurra (protege o paraquedas e tira a ogiva). Furo para o cordão.
    Perfil único de revolução (disco + saia): nada de união com face coincidente."""
    R = p["D"] / 2 - p.get("wall", 0.8) - 0.35
    corpo = _revolve([(0.0, 0.0), (R, 0.0), (R, 10.0), (R - 0.8, 10.0), (R - 0.8, 2.0), (0.0, 2.0)])
    return corpo - Manifold.cylinder(5.0, 2.5, 2.5, 32).translate([0, 0, -1])


# ---------------------------------------------------------------------------
# exportação e gabaritos
# ---------------------------------------------------------------------------
def exportar(m: Manifold, caminho: Path, material: str = "PLA") -> dict:
    mesh = m.to_mesh()
    v = np.asarray(mesh.vert_properties)[:, :3]
    f = np.asarray(mesh.tri_verts)
    tm = trimesh.Trimesh(vertices=v, faces=f, process=False)   # malha crua do manifold
    caminho.parent.mkdir(parents=True, exist_ok=True)
    tm.export(caminho)
    vol_cm3 = m.volume() / 1000.0
    return {"arquivo": caminho.name, "watertight": bool(tm.is_watertight),
            "volume_cm3": round(vol_cm3, 3), "massa_g": round(vol_cm3 * DENS[material], 2),
            "cg_z_mm": round(float(tm.center_mass[2]), 2),
            "altura_mm": round(float(v[:, 2].max() - v[:, 2].min()), 1),
            "envelope_xy_mm": round(float(2 * np.sqrt((v[:, 0] ** 2 + v[:, 1] ** 2).max())), 1),
            "genus": int(m.genus())}


def _massa_cg(m: Manifold, material: str) -> tuple[float, float]:
    mesh = m.to_mesh()
    v = np.asarray(mesh.vert_properties)[:, :3]
    f = np.asarray(mesh.tri_verts)
    if len(f) == 0:
        return 0.0, 0.0
    tm = trimesh.Trimesh(vertices=v, faces=f, process=False)
    return m.volume() / 1000.0 * DENS[material], float(tm.center_mass[2])


def massas_openrocket(p: dict, foguete: str) -> dict:
    """Massa (g) e CG (mm, medido a partir da FRENTE de cada componente, como o
    OpenRocket usa nas sobrescritas) das peças impressas."""
    mat = p.get("material", "PLA")
    D, w = p["D"], p.get("wall", 0.8)
    out = {}
    L, S = p["nose_len"], p["nose_shoulder"]
    m, cz = _massa_cg(ogiva_f2(p) if foguete == "f2" else ogiva(p), mat)
    out["ogiva"] = {"massa_g": m, "cg_mm": (S + L) - cz}           # z da impressão -> a partir da ponta
    if p["body_len"] > 1:
        tc = tubo_corpo(p, janela_trava=(foguete == "f2"))
        m, cz = _massa_cg(tc, mat)
        out["tubo_corpo"] = {"massa_g": m, "cg_mm": p["body_len"] - cz}   # topo do tubo para cima
    partes = lata_partes(p, olhal=(foguete == "f2"))
    Lfc = p.get("fincan_len", 100.0)
    m, cz = _massa_cg(partes["estrutura"], mat)
    out["lata_estrutura"] = {"massa_g": m, "cg_mm": Lfc - cz}         # inclui ombro, anéis, teto
    m, cz = _massa_cg(partes["aletas"], mat)
    z_le = p.get("fin_offset", 0.0) + p["fin_root"]
    out["aletas"] = {"massa_g": m, "cg_mm": z_le - cz}                # a partir do bordo de ataque da raiz
    m, cz = _massa_cg(partes["guia"], mat)
    out["guia_traseira"] = {"massa_g": m, "cg_mm": p.get("lug_rear_len", 20.0) - cz}
    if foguete == "f2":
        m, cz = _massa_cg(berco_eletronica(p), mat)
        out["berco"] = {"massa_g": m}
        m, cz = _massa_cg(pistao(p), mat)
        out["pistao"] = {"massa_g": m}
    return {k: {kk: round(vv, 3) for kk, vv in v.items()} for k, v in out.items()}


def gabaritos(saida: Path) -> list[dict]:
    """Imprimir ANTES do foguete: testam as folgas reais da impressora com o cano,
    com a haste e entre ombro e tubo. Cada um leva poucos minutos."""
    rel = []
    for idm in (20.3, 20.5, 20.7, 20.9):          # o cano entra com 1 volta de fita crepe
        rel.append(exportar(tubo(idm / 2 + 1.6, idm / 2, 0, 10),
                            saida / f"gab_luva_motor_ID{idm:.1f}_v1.stl"))
    for idg in (6.8, 7.2, 7.6, 8.0):              # guia na haste de 6 mm
        rel.append(exportar(tubo(idg / 2 + 1.0, idg / 2, 0, 15),
                            saida / f"gab_guia_haste6_ID{idg:.1f}_v1.stl"))
    return rel


def gerar_f1(p: dict, saida: Path) -> list[dict]:
    mat = p.get("material", "PLA")
    rel = [exportar(ogiva(p), saida / "F1_ogiva_v1.stl", mat)]
    if p["body_len"] > 1:
        rel.append(exportar(tubo_corpo(p), saida / "F1_tubo_corpo_v1.stl", mat))
    rel.append(exportar(lata_aletas(p), saida / "F1_lata_aletas_v1.stl", mat))
    return rel


def gerar_f2(p: dict, saida: Path) -> list[dict]:
    mat = p.get("material", "PLA")
    rel = [exportar(ogiva_f2(p), saida / "F2_ogiva_baia_v1.stl", mat),
           exportar(tubo_corpo(p, janela_trava=True), saida / "F2_tubo_corpo_v1.stl", mat),
           exportar(lata_aletas(p, olhal=True), saida / "F2_lata_aletas_v1.stl", mat),
           exportar(berco_eletronica(p), saida / "F2_berco_eletronica_v1.stl", mat),
           exportar(pistao(p), saida / "F2_pistao_v1.stl", mat)]
    return rel


if __name__ == "__main__":
    modo = sys.argv[1]
    if modo in ("f1", "f2"):
        params = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
        rel = (gerar_f1 if modo == "f1" else gerar_f2)(params, Path(sys.argv[3]))
        mc = massas_openrocket(params, modo)
        (Path(sys.argv[3]) / "massas_cad.json").write_text(json.dumps(mc, indent=1), encoding="utf-8")
        rel.append({"massas_cad": mc})
    elif modo == "massas":
        params = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
        rel = [massas_openrocket(params, sys.argv[3])]
    elif modo == "gabaritos":
        rel = gabaritos(Path(sys.argv[2]))
    else:
        raise SystemExit("modo: f1 | f2 | gabaritos")
    print(json.dumps(rel, indent=1))
